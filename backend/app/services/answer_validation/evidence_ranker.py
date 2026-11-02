from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RankedEvidence:
    document_id: str
    text: str
    relevance_score: float
    source_url: str = ""
    title: str = ""


class EvidenceRanker:
    """
    Ranks, re-orders, and deduplicates evidence chunks based on hybrid score,
    keyword density, and citation authority.
    """

    def rank(
        self,
        query: str,
        evidence_chunks: List[Dict[str, Any]],
        max_evidence: int = 5,
    ) -> List[RankedEvidence]:
        if not evidence_chunks:
            return []

        query_terms = set(query.lower().split())
        seen_texts = set()
        ranked_list: List[RankedEvidence] = []

        for item in evidence_chunks:
            text = (item.get("text") or item.get("content") or "").strip()
            if not text:
                continue

            # Deduplication by first 80 chars
            dedup_key = text[:80].lower()
            if dedup_key in seen_texts:
                continue
            seen_texts.add(dedup_key)

            base_score = float(item.get("score") or item.get("confidence") or 0.5)

            # Keyword density boost
            text_lower = text.lower()
            term_matches = sum(1 for term in query_terms if term in text_lower)
            density_bonus = min(0.3, term_matches * 0.05)
            final_score = min(1.0, base_score + density_bonus)

            ranked_list.append(
                RankedEvidence(
                    document_id=item.get("document_id") or "",
                    text=text,
                    relevance_score=round(final_score, 3),
                    source_url=item.get("source_url") or "",
                    title=item.get("title") or "",
                )
            )

        # Sort descending by score
        ranked_list.sort(key=lambda x: x.relevance_score, reverse=True)
        return ranked_list[:max_evidence]

