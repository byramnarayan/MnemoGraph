from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OntologyEntityMapper:
    """
    Transforms raw PostgreSQL rows into UKGOE Universal Ontology Entities:
    Person, Project, Decision, Incident, Lesson, Task, System, Group, Document.
    """

    @staticmethod
    def map_row_to_entity(
        row: dict[str, Any],
        connector_id: str,
        schema_name: str,
        table_name: str,
        entity_type: str,
        primary_key_cols: list[str],
        text_cols: list[str] | None = None,
        excluded_cols: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Produces a canonical entity payload with properties, deterministic ID, and searchable text.
        """
        excluded = set(excluded_cols or [])
        clean_row = {k: v for k, v in row.items() if k not in excluded}

        # Deterministic primary key value
        if primary_key_cols:
            pk_val = "-".join([str(clean_row.get(c, "unknown")) for c in primary_key_cols])
        else:
            pk_val = str(clean_row.get("id") or clean_row.get("name") or hash(frozenset(clean_row.items())))

        canonical_id = f"pg:{connector_id}:{schema_name}:{table_name}:{pk_val}"

        # Resolve display label
        label = (
            clean_row.get("name")
            or clean_row.get("title")
            or clean_row.get("full_name")
            or clean_row.get("email")
            or f"{table_name} #{pk_val}"
        )

        # Normalize properties based on entity class
        props: dict[str, Any] = {
            "id": canonical_id,
            "source_id": pk_val,
            "connector_id": connector_id,
            "source_table": f"{schema_name}.{table_name}",
            "name": str(label),
            "title": str(label),
        }

        # Class-specific property alignments
        if entity_type == "Person":
            props["full_name"] = clean_row.get("full_name") or clean_row.get("name") or label
            props["email"] = clean_row.get("email") or clean_row.get("contact_email")
            props["role"] = clean_row.get("role") or clean_row.get("title") or "Team Member"
            props["department"] = clean_row.get("department") or clean_row.get("team")
            props["employment_status"] = clean_row.get("status") or clean_row.get("employment_status") or "active"

        elif entity_type == "Decision":
            props["rationale"] = clean_row.get("rationale") or clean_row.get("description") or "Operational alignment."
            props["decision_date"] = str(clean_row.get("decision_date") or clean_row.get("created_at") or "")
            props["status"] = clean_row.get("status") or "approved"
            props["maker"] = clean_row.get("maker") or clean_row.get("decided_by") or clean_row.get("author")

        elif entity_type == "Incident":
            props["severity"] = clean_row.get("severity") or clean_row.get("priority") or "P2"
            props["status"] = clean_row.get("status") or "open"
            props["confirmed_cause"] = clean_row.get("cause") or clean_row.get("root_cause")
            props["description"] = clean_row.get("description") or clean_row.get("summary") or label

        elif entity_type == "Project":
            props["status"] = clean_row.get("status") or "active"
            props["lead"] = clean_row.get("lead") or clean_row.get("owner")
            props["outcome_summary"] = clean_row.get("summary") or clean_row.get("description")

        elif entity_type == "Task":
            props["status"] = clean_row.get("status") or "open"
            props["assigned_to"] = clean_row.get("assignee") or clean_row.get("assigned_to")
            props["due_date"] = str(clean_row.get("due_date") or "")

        elif entity_type == "System":
            props["type"] = clean_row.get("type") or clean_row.get("category") or "Infrastructure Service"
            props["status"] = clean_row.get("status") or "operational"

        # Merge remaining attributes as metadata
        for k, v in clean_row.items():
            if k not in props and v is not None:
                props[k] = str(v) if not isinstance(v, (int, float, bool, list, dict)) else v

        # Construct fluent searchable text chunk
        if text_cols:
            text_parts = [f"{c.replace('_', ' ').title()}: {clean_row.get(c)}" for c in text_cols if clean_row.get(c)]
            searchable_text = f"{entity_type} {label}. " + " | ".join(text_parts)
        else:
            searchable_text = f"{entity_type} '{label}' from {schema_name}.{table_name}. " + ", ".join(
                [f"{k}: {v}" for k, v in list(props.items())[:8]]
            )

        return {
            "entity_id": canonical_id,
            "entity_class": entity_type,
            "label": str(label),
            "properties": props,
            "searchable_text": searchable_text,
            "raw_payload": clean_row,
            "pk_value": pk_val,
        }

