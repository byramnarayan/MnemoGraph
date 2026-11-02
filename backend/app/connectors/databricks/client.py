from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DatabricksClient:
    """Async client wrapper for Databricks REST API (Workspace, SCIM, Jobs, Clusters)."""

    def __init__(self, host: str, token: str, workspace_id: str | None = None):
        self.host = host.rstrip("/")
        self.token = token.strip()
        self.workspace_id = workspace_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "Enterprise-Memory-Connector/1.0",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.host}{path}"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
            )
            if response.status_code >= 400:
                logger.warning(
                    f"Databricks API error [{response.status_code}] on {path}: {response.text}"
                )
                response.raise_for_status()
            if response.content:
                return response.json()
            return {}

    async def get_current_user(self) -> dict[str, Any]:
        """Fetch current authenticated caller identity."""
        try:
            return await self._request("GET", "/api/2.0/preview/scim/v2/Me")
        except Exception:
            # Fallback for alternative SCIM paths
            return await self._request("GET", "/api/2.0/scim/v2/Me")

    async def get_workspace_status(self) -> dict[str, Any]:
        """Verify workspace status and root access."""
        return await self._request("GET", "/api/2.0/workspace/get-status", params={"path": "/"})

    async def list_workspace_items(self, path: str = "/") -> list[dict[str, Any]]:
        """List folders, notebooks, and files in a workspace directory recursively."""
        items: list[dict[str, Any]] = []
        try:
            res = await self._request("GET", "/api/2.0/workspace/list", params={"path": path})
            objects = res.get("objects", [])
            for obj in objects:
                items.append(obj)
                if obj.get("object_type") == "DIRECTORY" and path != obj.get("path"):
                    sub_items = await self.list_workspace_items(obj.get("path"))
                    items.extend(sub_items)
        except Exception as e:
            logger.debug(f"Could not list workspace path {path}: {e}")
        return items

    async def export_notebook(self, path: str, format_type: str = "SOURCE") -> str:
        """Export notebook contents as plain text source code or HTML."""
        res = await self._request(
            "GET",
            "/api/2.0/workspace/export",
            params={"path": path, "format": format_type, "direct_download": "false"},
        )
        content_b64 = res.get("content", "")
        if content_b64:
            try:
                return base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                return content_b64
        return ""

    async def list_users(self) -> list[dict[str, Any]]:
        """List enterprise users via SCIM."""
        try:
            res = await self._request("GET", "/api/2.0/preview/scim/v2/Users")
            return res.get("Resources", [])
        except Exception:
            try:
                res = await self._request("GET", "/api/2.0/scim/v2/Users")
                return res.get("Resources", [])
            except Exception:
                return []

    async def list_groups(self) -> list[dict[str, Any]]:
        """List user groups/teams via SCIM."""
        try:
            res = await self._request("GET", "/api/2.0/preview/scim/v2/Groups")
            return res.get("Resources", [])
        except Exception:
            try:
                res = await self._request("GET", "/api/2.0/scim/v2/Groups")
                return res.get("Resources", [])
            except Exception:
                return []

    async def list_jobs(self) -> list[dict[str, Any]]:
        """List Databricks workflows and jobs."""
        try:
            res = await self._request("GET", "/api/2.1/jobs/list", params={"limit": 100})
            return res.get("jobs", [])
        except Exception:
            return []

    async def list_clusters(self) -> list[dict[str, Any]]:
        """List compute clusters."""
        try:
            res = await self._request("GET", "/api/2.0/clusters/list")
            return res.get("clusters", [])
        except Exception:
            return []

    async def list_sql_warehouses(self) -> list[dict[str, Any]]:
        """List SQL Warehouses / SQL Endpoints (/api/2.0/sql/warehouses)."""
        try:
            res = await self._request("GET", "/api/2.0/sql/warehouses")
            return res.get("warehouses", [])
        except Exception as e:
            logger.warning(f"Failed to fetch SQL warehouses: {e}")
            return []

    async def list_catalogs(self) -> list[dict[str, Any]]:
        """List Unity Catalogs or metastore schemas (/api/2.1/unity-catalog/catalogs)."""
        try:
            res = await self._request("GET", "/api/2.1/unity-catalog/catalogs")
            return res.get("catalogs", [])
        except Exception:
            return []

    async def list_schemas(self, catalog_name: str = "main") -> list[dict[str, Any]]:
        """List schemas under catalog."""
        try:
            res = await self._request("GET", "/api/2.1/unity-catalog/schemas", params={"catalog_name": catalog_name})
            return res.get("schemas", [])
        except Exception:
            return []

    async def list_tables(self, catalog_name: str = "main", schema_name: str = "default") -> list[dict[str, Any]]:
        """List tables under catalog and schema."""
        try:
            res = await self._request(
                "GET",
                "/api/2.1/unity-catalog/tables",
                params={"catalog_name": catalog_name, "schema_name": schema_name},
            )
            return res.get("tables", [])
        except Exception as e:
            logger.debug(f"Could not list UC tables for {catalog_name}.{schema_name}: {e}")
            return []

