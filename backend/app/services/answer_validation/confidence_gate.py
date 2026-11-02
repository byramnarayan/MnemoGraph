from __future__ import annotations

from typing import List


class ConfidenceGate:
    """
    Evaluates confidence thresholds and gates weak/unsupported answers.
    """

    MIN_CONFIDENCE_THRESHOLD = 0.55
    MIN_SOURCE_COUNT = 1

    @classmethod
    def evaluate(
        cls,
        confidence_score: float,
        source_count: int,
        has_grounding: bool,
    ) -> bool:
        if not has_grounding:
            return False
        if source_count < cls.MIN_SOURCE_COUNT:
            return False
        if confidence_score < cls.MIN_CONFIDENCE_THRESHOLD:
            return False
        return True

