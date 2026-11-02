from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ParsedTable:
    headers: List[str]
    rows: List[List[str]]
    raw_text: str
    row_count: int
    col_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "row_count": self.row_count,
            "col_count": self.col_count,
        }


class TableParser:
    """
    Parses Markdown tables (| header1 | header2 |) into structured rows & columns.
    """

    def parse(self, text: str) -> Optional[ParsedTable]:
        if not text or "|" not in text:
            return None

        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]

        if not table_lines:
            return None

        # Parse header
        raw_header = table_lines[0]
        headers = [c.strip() for c in raw_header.strip("|").split("|")]

        # Filter out divider line (e.g., | --- | :---: |)
        data_lines = []
        for line in table_lines[1:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Check if this line is just dashes
            if all(re.match(r"^:?-+:?$", cell) for cell in cells if cell):
                continue
            data_lines.append(cells)

        rows = []
        for cells in data_lines:
            # Normalize length to headers
            row = cells + [""] * (len(headers) - len(cells))
            rows.append(row[: len(headers)])

        return ParsedTable(
            headers=headers,
            rows=rows,
            raw_text=text,
            row_count=len(rows),
            col_count=len(headers),
        )

