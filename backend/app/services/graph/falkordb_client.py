from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import falkordb
from falkordb import FalkorDB

from app.core.config import settings

logger = logging.getLogger(__name__)


class FalkorDBClient:
    """Manages FalkorDB connections and query execution."""

    def __init__(self, url: str | None = None, graph_name: str | None = None):
        self.url = url or settings.falkordb_url
        self.graph_name = graph_name or settings.falkordb_graph_name

        parsed = urlparse(self.url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6379
        self.username = parsed.username
        self.password = parsed.password

        self._client: FalkorDB | None = None
        self._graph = None

    def get_graph(self):
        if not self._client:
            # FalkorDB.from_url natively supports both local and FalkorDB Cloud:
            # e.g., falkors://default:password@eu-west-1.cloud.falkordb.com:port
            # or falkordb://localhost:6379
            try:
                self._client = FalkorDB.from_url(self.url)
            except Exception:
                kwargs: dict[str, Any] = {"host": self.host, "port": self.port}
                if self.username:
                    kwargs["username"] = self.username
                if self.password:
                    kwargs["password"] = self.password
                self._client = FalkorDB(**kwargs)

            self._graph = self._client.select_graph(self.graph_name)
        return self._graph

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[list[Any]]:
        g = self.get_graph()
        try:
            res = g.query(cypher, params or {})
            return res.result_set
        except Exception as e:
            logger.error(f"FalkorDB query error: {e} | Cypher: {cypher}")
            raise

