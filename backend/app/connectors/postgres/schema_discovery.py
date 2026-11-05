from __future__ import annotations

import logging
from typing import Any
from app.connectors.postgres.client import PostgresClient

logger = logging.getLogger(__name__)

SYSTEM_SCHEMAS = {
    "pg_catalog",
    "information_schema",
    "pg_toast",
    "pg_temp_1",
    "pg_toast_temp_1",
}


class PostgresSchemaDiscovery:
    """
    Discovers non-system schemas, tables, columns, primary keys, and foreign keys.
    Auto-suggests universal ontology entity types based on table naming conventions.
    """

    def __init__(self, client: PostgresClient):
        self.client = client

    async def discover_schemas_and_tables(self) -> list[dict[str, Any]]:
        """
        Discovers all user-accessible schemas, tables, and column metadata.
        """
        # 1. Fetch tables
        table_query = """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_schema, table_name;
        """
        table_rows = await self.client.execute_read_query(table_query)

        # 2. Fetch columns
        col_query = """
        SELECT table_schema, table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name, ordinal_position;
        """
        col_rows = await self.client.execute_read_query(col_query)

        # 3. Fetch Primary Keys
        pk_query = """
        SELECT kcu.table_schema, kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema NOT IN ('pg_catalog', 'information_schema');
        """
        pk_rows = await self.client.execute_read_query(pk_query)

        # Group PKs by (schema, table)
        pk_map: dict[tuple[str, str], list[str]] = {}
        for r in pk_rows:
            key = (r[0], r[1])
            pk_map.setdefault(key, []).append(r[2])

        # Group columns by (schema, table)
        col_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for r in col_rows:
            key = (r[0], r[1])
            col_map.setdefault(key, []).append({
                "name": r[2],
                "data_type": r[3],
                "is_nullable": r[4] == "YES",
            })

        # Assemble table summaries
        results: list[dict[str, Any]] = []
        for r in table_rows:
            schema, name, t_type = r[0], r[1], r[2]
            key = (schema, name)
            cols = col_map.get(key, [])
            pks = pk_map.get(key, [])
            
            # Detect candidate cursor column (timestamp or incremental id)
            cursor_col = None
            for c in cols:
                cname = c["name"].lower()
                if cname in ("updated_at", "last_modified", "modified_at", "created_at", "timestamp"):
                    cursor_col = c["name"]
                    break
            if not cursor_col and pks:
                cursor_col = pks[0]

            entity_suggestion = self._suggest_entity_type(name, [c["name"] for c in cols])

            results.append({
                "schema_name": schema,
                "table_name": name,
                "full_name": f"{schema}.{name}",
                "table_type": t_type,
                "columns": cols,
                "primary_keys": pks,
                "suggested_cursor": cursor_col,
                "suggested_cursor_col": cursor_col,
                "suggested_entity_type": entity_suggestion,
            })

        return results

    @staticmethod
    def _suggest_entity_type(table_name: str, column_names: list[str]) -> str:
        """
        Suggests matching UKGOE Universal Class:
        Person, Project, Decision, Incident, Lesson, Task, System, Group, Document
        """
        t = table_name.lower()
        cols = {c.lower() for c in column_names}

        if any(k in t for k in ("decision", "change", "rfc", "proposal", "architecture_decision")):
            return "Decision"
        if any(k in t for k in ("incident", "outage", "ticket", "issue", "alert", "error_log")):
            return "Incident"
        if any(k in t for k in ("lesson", "postmortem", "retrospective", "review")):
            return "Lesson"
        if any(k in t for k in ("project", "initiative", "program", "epic")):
            return "Project"
        if any(k in t for k in ("task", "action", "todo", "sprint_task")):
            return "Task"
        if any(k in t for k in ("system", "service", "cluster", "server", "router", "device", "gateway")):
            return "System"
        if any(k in t for k in ("team", "group", "department", "org")):
            return "Group"
        if any(k in t for k in ("user", "person", "employee", "member", "staff", "engineer")):
            return "Person"
        return "Document"

