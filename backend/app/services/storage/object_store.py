from abc import ABC, abstractmethod


class BaseObjectStore(ABC):
    @abstractmethod
    async def put_object(self, key: str, data: bytes, content_type: str = "text/plain") -> str:
        """Store bytes and return storage key or path."""
        pass

    @abstractmethod
    async def get_object(self, key: str) -> bytes:
        """Retrieve stored bytes."""
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> None:
        """Delete stored object."""
        pass

