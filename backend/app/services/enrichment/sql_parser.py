from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParsedSQL:
    query_intent: str  # SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, UNKNOWN
    tables: List[str] = field(default_factory=list)
    schemas: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    raw_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_intent": self.query_intent,
            "tables": self.tables,
            "schemas": self.schemas,
            "columns": self.columns,
            "raw_query": self.raw_query,
        }


class SQLParser:
    """
    Practical regex-based SQL parser extracting:
    - query intent (SELECT, INSERT, UPDATE, DELETE, CREATE, etc.)
    - table names and schemas (e.g. catalog.schema.table or from users)
    - referenced columns
    """

    # Matches table references after FROM, JOIN, INTO, UPDATE, TABLE
    TABLE_PATTERN = re.compile(
        r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z0-9_\.\`\"\[\]]+)",
        re.IGNORECASE,
    )

    # Basic intent keywords
    INTENTS = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH", "MERGE"]

    def parse(self, text: str) -> Optional[ParsedSQL]:
        if not text:
            return None

        clean_text = text.strip()
        # Strip markdown fence if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text).strip()

        words = clean_text.split()
        if not words:
            return None

        # Determine primary intent
        intent = "UNKNOWN"
        for w in words:
            clean_w = re.sub(r"[^A-Za-z]", "", w).upper()
            if clean_w in self.INTENTS:
                intent = clean_w
                break

        # Extract table references
        raw_tables = self.TABLE_PATTERN.findall(clean_text)
        tables: List[str] = []
        schemas: List[str] = []

        for t in raw_tables:
            # Clean symbols ` " [ ] ( ) ; ,
            cleaned = re.sub(r"[\`\"\[\]\(\);,]", "", t).strip()
            if not cleaned or cleaned.upper() in {"SELECT", "WHERE", "GROUP", "ORDER", "ON", "VALUES"}:
                continue

            parts = cleaned.split(".")
            if len(parts) >= 2:
                schema_part = parts[-2]
                table_part = parts[-1]
                if schema_part not in schemas:
                    schemas.append(schema_part)
                if table_part not in tables:
                    tables.append(table_part)
            else:
                if parts[0] not in tables:
                    tables.append(parts[0])

        # Extract basic column names from SELECT clause if applicable
        columns: List[str] = []
        select_match = re.search(r"\bSELECT\s+(.+?)\s+\bFROM\b", clean_text, re.IGNORECASE | re.DOTALL)
        if select_match:
            raw_cols = select_match.group(1).split(",")
            for c in raw_cols:
                c_clean = c.strip()
                # If aliased e.g. "col AS c", pick alias or name
                as_match = re.search(r"\bAS\s+([a-zA-Z0-9_]+)", c_clean, re.IGNORECASE)
                if as_match:
                    col_name = as_match.group(1)
                else:
                    tokens = c_clean.split()
                    col_name = tokens[-1] if tokens else ""
                col_name = re.sub(r"[\`\"\[\]\(\);,]", "", col_name)
                if col_name and col_name != "*" and len(col_name) < 60 and col_name not in columns:
                    columns.append(col_name)

        return ParsedSQL(
            query_intent=intent,
            tables=tables,
            schemas=schemas,
            columns=columns[:20],
            raw_query=clean_text,
        )

