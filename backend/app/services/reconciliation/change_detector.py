from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChangeDetectionResult:
    has_changed: bool
    is_new: bool
    current_hash: str
    previous_hash: Optional[str] = None
    change_type: str = "none"  # "none", "new", "content_changed", "moved"


class ChangeDetector:
    """
    Computes cryptographic checksums (SHA-256) of document content/metadata
    to accurately detect changed, moved, or updated documents.
    """

    @staticmethod
    def compute_hash(content: str | bytes, path: Optional[str] = None) -> str:
        sha = hashlib.sha256()
        if isinstance(content, str):
            sha.update(content.encode("utf-8", errors="replace"))
        else:
            sha.update(content)
        if path:
            sha.update(path.encode("utf-8", errors="replace"))
        return sha.hexdigest()

    def detect_change(
        self,
        current_content: str | bytes,
        stored_hash: Optional[str] = None,
        path: Optional[str] = None,
        stored_path: Optional[str] = None,
    ) -> ChangeDetectionResult:
        current_hash = self.compute_hash(current_content, path)

        if not stored_hash:
            return ChangeDetectionResult(
                has_changed=True,
                is_new=True,
                current_hash=current_hash,
                previous_hash=None,
                change_type="new",
            )

        if path and stored_path and path != stored_path and current_hash == stored_hash:
            return ChangeDetectionResult(
                has_changed=True,
                is_new=False,
                current_hash=current_hash,
                previous_hash=stored_hash,
                change_type="moved",
            )

        if current_hash != stored_hash:
            return ChangeDetectionResult(
                has_changed=True,
                is_new=False,
                current_hash=current_hash,
                previous_hash=stored_hash,
                change_type="content_changed",
            )

        return ChangeDetectionResult(
            has_changed=False,
            is_new=False,
            current_hash=current_hash,
            previous_hash=stored_hash,
            change_type="none",
        )

