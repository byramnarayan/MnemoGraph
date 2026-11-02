from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Generic interface for all connectors (Databricks, Slack, GitHub, Jira, etc.)."""

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Verify token and service reachability."""
        pass

    @abstractmethod
    async def fetch_users(self) -> list[dict[str, Any]]:
        """Fetch users from the source."""
        pass

    @abstractmethod
    async def fetch_groups(self) -> list[dict[str, Any]]:
        """Fetch groups/teams from the source."""
        pass

    @abstractmethod
    async def fetch_notebooks(self) -> list[dict[str, Any]]:
        """Fetch notebook documents."""
        pass

    @abstractmethod
    async def fetch_files(self) -> list[dict[str, Any]]:
        """Fetch raw files or artifacts."""
        pass

    @abstractmethod
    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetch orchestration jobs."""
        pass

