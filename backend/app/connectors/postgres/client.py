from __future__ import annotations

import logging
from typing import Any
import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    Read-only PostgreSQL database client using async psycopg.
    Enforces read-only transaction state and safe statement timeouts.
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        username: str | None = None,
        password: str = "",
        sslmode: str = "prefer",
        ssl_mode: str | None = None,
        connect_timeout: int = 5,
        statement_timeout_ms: int = 10000,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = username or user
        self.password = password
        self.sslmode = ssl_mode or sslmode
        self.connect_timeout = connect_timeout
        self.statement_timeout_ms = statement_timeout_ms

    def _get_conninfo(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password} sslmode={self.sslmode} "
            f"connect_timeout={self.connect_timeout}"
        )

    async def test_connection(self) -> dict[str, Any]:
        """
        Tests read-only connection, retrieves server version and database name.
        Never returns credentials.
        """
        conninfo = self._get_conninfo()
        try:
            async with await psycopg.AsyncConnection.connect(conninfo) as aconn:
                await aconn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
                async with aconn.cursor() as cur:
                    await cur.execute("SELECT version(), current_database(), current_user;")
                    row = await cur.fetchone()
                    return {
                        "ok": True,
                        "server_version": row[0] if row else "PostgreSQL",
                        "database_name": row[1] if row else self.database,
                        "connected_user": row[2] if row else self.user,
                        "message": "Connection successful (read-only verified)",
                    }
        except Exception as exc:
            logger.warning(f"External PostgreSQL connection test failed: {exc}")
            return {
                "ok": False,
                "server_version": None,
                "database_name": self.database,
                "connected_user": self.user,
                "message": f"Connection failed: {str(exc)}",
            }

    async def execute_read_query(
        self,
        query: str | sql.Composed,
        params: tuple[Any, ...] | None = None,
    ) -> list[tuple[Any, ...]]:
        """
        Executes a parameterized read-only query with strict statement timeout.
        """
        conninfo = self._get_conninfo()
        async with await psycopg.AsyncConnection.connect(conninfo) as aconn:
            await aconn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
            await aconn.execute(f"SET statement_timeout = {self.statement_timeout_ms};")
            async with aconn.cursor() as cur:
                await cur.execute(query, params or ())
                return await cur.fetchall()

    async def fetch_rows_batched(
        self,
        schema: str,
        table: str,
        columns: list[str] | None = None,
        cursor_col: str | None = None,
        cursor_val: Any | None = None,
        batch_size: int = 500,
    ):
        """
        Async generator that yields batches of rows until the table is exhausted.
        """
        current_cursor = cursor_val
        pk_col = cursor_col
        while True:
            batch = await self.fetch_table_rows_batch(
                schema_name=schema,
                table_name=table,
                columns=columns or [],
                pk_column=pk_col,
                cursor_column=cursor_col,
                last_cursor=current_cursor,
                limit=batch_size,
            )
            if not batch:
                break
            yield batch
            if len(batch) < batch_size or not cursor_col:
                break
            current_cursor = batch[-1].get(cursor_col)

    async def fetch_table_rows_batch(
        self,
        schema_name: str,
        table_name: str,
        columns: list[str],
        pk_column: str | None = None,
        cursor_column: str | None = None,
        last_cursor: Any | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Safely fetches a bounded batch of rows using sql.Identifier quoting.
        """
        conninfo = self._get_conninfo()
        col_idents = [sql.Identifier(c) for c in columns] if columns else [sql.SQL("*")]
        tbl_ident = sql.Identifier(schema_name, table_name)

        where_clause = sql.SQL("")
        params: list[Any] = []

        if cursor_column and last_cursor is not None:
            where_clause = sql.SQL("WHERE {} > %s").format(sql.Identifier(cursor_column))
            params.append(last_cursor)

        order_col = cursor_column or pk_column or columns[0] if columns else None
        order_clause = sql.SQL("")
        if order_col:
            order_clause = sql.SQL("ORDER BY {} ASC").format(sql.Identifier(order_col))

        limit_clause = sql.SQL("LIMIT %s")
        params.append(limit)

        query = sql.SQL("SELECT {} FROM {} {} {} {}").format(
            sql.SQL(", ").join(col_idents),
            tbl_ident,
            where_clause,
            order_clause,
            limit_clause,
        )

        async with await psycopg.AsyncConnection.connect(conninfo) as aconn:
            await aconn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
            await aconn.execute(f"SET statement_timeout = {self.statement_timeout_ms};")
            async with aconn.cursor() as cur:
                await cur.execute(query, params)
                desc = cur.description or []
                col_names = [d[0] for d in desc]
                rows = await cur.fetchall()
                return [dict(zip(col_names, r)) for r in rows]

