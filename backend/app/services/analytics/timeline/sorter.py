from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    event_id: str
    event_type: str  # "DECISION_RECORDED", "ACTION_ASSIGNED", "ACTION_DEPLOYED", "INCIDENT_START", "INCIDENT_RESOLVED"
    entity_id: str
    entity_name: str
    timestamp_str: str | None = None
    parsed_timestamp: datetime | None = None
    actor_id: str | None = None
    actor_name: str | None = None
    affected_scope: str | None = None
    relation_semantics: str = "TEMPORAL_SEQUENCE"  # "CAUSAL_PROVEN" vs "TEMPORAL_SEQUENCE"
    details: dict[str, Any] = Field(default_factory=dict)


class ChronologicalTimelineSorter:
    """
    Normalizes multi-hop extraction into a verified chronological event sequence.
    """

    @classmethod
    def _parse_time(cls, val: Any) -> datetime | None:
        if not val or not isinstance(val, str):
            return None
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(val.strip(), fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def assemble_events(cls, raw_chains: list[dict[str, Any]]) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        seen_events: set[str] = set()

        for c in raw_chains:
            d = c.get("decision", {})
            t = c.get("task", {})
            p = c.get("person", {})
            a = c.get("assignee", {})
            s = c.get("system", {})
            inc = c.get("incident", {})

            # 1. Decision Event
            if d and d.get("id"):
                did = str(d.get("id"))
                if f"dec_{did}" not in seen_events:
                    seen_events.add(f"dec_{did}")
                    raw_dt = d.get("decision_date") or d.get("created_at")
                    events.append(
                        TimelineEvent(
                            event_id=f"dec_{did}",
                            event_type="DECISION_RECORDED",
                            entity_id=did,
                            entity_name=str(d.get("title") or did),
                            timestamp_str=str(raw_dt) if raw_dt else None,
                            parsed_timestamp=cls._parse_time(raw_dt),
                            actor_id=p.get("id") or d.get("made_by_id"),
                            actor_name=p.get("name") or p.get("full_name"),
                            affected_scope=s.get("name") or d.get("affected_systems"),
                            relation_semantics="TEMPORAL_SEQUENCE",
                            details=d,
                        )
                    )

            # 2. Action / Task Assigned Event
            if t and t.get("id"):
                tid = str(t.get("id"))
                if f"task_{tid}" not in seen_events:
                    seen_events.add(f"task_{tid}")
                    raw_dt = t.get("completion_date") or t.get("due_date") or t.get("created_at")
                    events.append(
                        TimelineEvent(
                            event_id=f"task_{tid}",
                            event_type="ACTION_DEPLOYED" if t.get("status") == "COMPLETED" else "ACTION_ASSIGNED",
                            entity_id=tid,
                            entity_name=str(t.get("title") or tid),
                            timestamp_str=str(raw_dt) if raw_dt else None,
                            parsed_timestamp=cls._parse_time(raw_dt),
                            actor_id=a.get("id") or t.get("assigned_to_id"),
                            actor_name=a.get("name") or a.get("full_name"),
                            affected_scope=s.get("name"),
                            relation_semantics="TEMPORAL_SEQUENCE",
                            details=t,
                        )
                    )

            # 3. Incident Event
            if inc and inc.get("id"):
                iid = str(inc.get("id"))
                if f"inc_{iid}" not in seen_events:
                    seen_events.add(f"inc_{iid}")
                    raw_dt = inc.get("start_datetime") or inc.get("created_at")
                    is_causal = bool(inc.get("confirmed_cause") or inc.get("is_recurrence"))
                    events.append(
                        TimelineEvent(
                            event_id=f"inc_{iid}",
                            event_type="INCIDENT_START",
                            entity_id=iid,
                            entity_name=str(inc.get("title") or iid),
                            timestamp_str=str(raw_dt) if raw_dt else None,
                            parsed_timestamp=cls._parse_time(raw_dt),
                            affected_scope=s.get("name") or inc.get("affected_systems"),
                            relation_semantics="CAUSAL_PROVEN" if is_causal else "TEMPORAL_SEQUENCE",
                            details=inc,
                        )
                    )

        # Sort chronologically by parsed timestamp; unknown times put at end
        events.sort(key=lambda ev: (ev.parsed_timestamp is None, ev.parsed_timestamp or datetime.max))
        return events

