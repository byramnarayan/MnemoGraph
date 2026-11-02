from __future__ import annotations

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReindexTask:
    document_id: str
    reason: str  # content_changed, moved, new
    priority: int = 1


class ReindexQueue:
    """
    In-memory / transactional reindex task queue tracking documents needing vector
    re-indexing or graph re-enrichment.
    """

    def __init__(self):
        self._tasks: List[ReindexTask] = []

    def enqueue(self, document_id: str, reason: str = "content_changed", priority: int = 1) -> None:
        self._tasks.append(ReindexTask(document_id=document_id, reason=reason, priority=priority))
        logger.info(f"Enqueued document {document_id} for reindexing ({reason})")

    def drain(self) -> List[ReindexTask]:
        tasks = list(self._tasks)
        self._tasks.clear()
        return tasks

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

