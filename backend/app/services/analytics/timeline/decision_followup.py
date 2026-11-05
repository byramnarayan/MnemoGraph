from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from pydantic import BaseModel, Field


class DecisionFollowUpSummary(BaseModel):
    decision_id: str
    decision_title: str
    decision_date: str | None = None
    decision_maker: str | None = None
    related_action_title: str | None = None
    action_deployment_date: str | None = None
    affected_scope: str | None = None
    follow_up_days: int = 0
    follow_up_status: str  # "NO_LINKED_INCIDENT_OBSERVED", "FOLLOW_UP_INCOMPLETE", "ACTION_NOT_IMPLEMENTED", "INCIDENT_OBSERVED", "INSUFFICIENT_DATA"
    subsequent_incident_id: str | None = None
    observation_note: str = ""
    evidence_coverage: str = "ADEQUATE"


class DecisionFollowUpClassifier:
    """
    Evaluates historical decision outcomes newest-first, classifying whether subsequent incidents
    occurred within the observation window.
    """

    MIN_OBSERVATION_DAYS = 30

    @classmethod
    def evaluate_decisions(
        cls,
        chains: list[dict[str, Any]],
        now_dt: datetime | None = None,
    ) -> list[DecisionFollowUpSummary]:
        now = now_dt or datetime.now(UTC)
        results: list[DecisionFollowUpSummary] = []
        seen_dids: set[str] = set()

        for c in chains:
            d = c.get("decision", {})
            t = c.get("task", {})
            p = c.get("person", {})
            s = c.get("system", {})
            inc = c.get("incident", {})

            did = d.get("id")
            if not did or did in seen_dids:
                continue
            seen_dids.add(did)

            dec_date_str = d.get("decision_date") or d.get("created_at")
            dec_dt = None
            if dec_date_str:
                try:
                    dec_dt = datetime.fromisoformat(str(dec_date_str).replace("Z", "+00:00"))
                except ValueError:
                    dec_dt = None

            # Calculate follow-up days
            follow_up_days = 0
            if dec_dt:
                diff = now - (dec_dt if dec_dt.tzinfo else dec_dt.replace(tzinfo=UTC))
                follow_up_days = max(0, diff.days)

            # Check action implementation
            has_action = bool(t.get("id"))
            action_completed = t.get("status") == "COMPLETED" or bool(t.get("completion_date"))

            # Check linked incident
            has_subsequent_incident = bool(inc.get("id"))

            # Determine follow-up status
            if has_subsequent_incident:
                status = "INCIDENT_OBSERVED"
                note = f"Linked subsequent incident observed: {inc.get('title') or inc.get('id')}"
            elif not dec_date_str:
                status = "INSUFFICIENT_DATA"
                note = "Decision timestamp is missing from graph records."
            elif has_action and not action_completed:
                status = "ACTION_NOT_IMPLEMENTED"
                note = "Corrective task assigned but implementation not marked completed."
            elif follow_up_days < cls.MIN_OBSERVATION_DAYS:
                status = "FOLLOW_UP_INCOMPLETE"
                note = f"Follow-up period of {follow_up_days} days is below the 30-day confidence threshold."
            else:
                status = "NO_LINKED_INCIDENT_OBSERVED"
                note = f"Zero incidents observed over {follow_up_days} days of monitoring. Note: Does not constitute mathematical proof of prevention."

            results.append(
                DecisionFollowUpSummary(
                    decision_id=str(did),
                    decision_title=str(d.get("title") or did),
                    decision_date=str(dec_date_str) if dec_date_str else None,
                    decision_maker=p.get("name") or p.get("full_name") or d.get("made_by_id"),
                    related_action_title=t.get("title"),
                    action_deployment_date=t.get("completion_date"),
                    affected_scope=s.get("name") or d.get("affected_systems"),
                    follow_up_days=follow_up_days,
                    follow_up_status=status,
                    subsequent_incident_id=inc.get("id"),
                    observation_note=note,
                    evidence_coverage="COMPLETE" if dec_dt and has_action else "PARTIAL",
                )
            )

        # Sort newest decisions first
        results.sort(key=lambda item: item.decision_date or "", reverse=True)
        return results

