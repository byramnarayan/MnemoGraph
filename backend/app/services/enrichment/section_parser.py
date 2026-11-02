from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedSection:
    section_type: str  # heading, paragraph, list, code, table, sql
    content: str
    heading: Optional[str] = None
    order_index: int = 0
    source_start: int = 0
    source_end: int = 0


class SectionParser:
    """
    Splits document text into structured sections:
    - headings (#, ##, ###, or uppercase titles)
    - code blocks (``` ... ```)
    - SQL blocks (```sql ... ``` or standalone SELECT/CREATE/INSERT statements)
    - tables (markdown pipe tables | ... |)
    - lists (* -, 1. etc.)
    - paragraphs
    """

    SQL_KEYWORDS = {"select", "insert", "update", "delete", "create", "alter", "drop", "with", "from", "where", "join"}

    def parse(self, text: str) -> List[ParsedSection]:
        if not text:
            return []

        lines = text.splitlines(keepends=True)
        sections: List[ParsedSection] = []

        current_heading: Optional[str] = None
        current_type: Optional[str] = None
        current_lines: List[str] = []
        current_start: int = 0
        current_pos: int = 0
        order_index = 0

        in_code_block = False
        code_fence_lang = ""
        code_block_start = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            line_pos = current_pos
            current_pos += len(line)
            stripped = line.strip()

            # Handle fenced code blocks
            if stripped.startswith("```"):
                if not in_code_block:
                    # Flush previous section if any
                    if current_lines:
                        sections.append(
                            ParsedSection(
                                section_type=current_type or "paragraph",
                                content="".join(current_lines).strip(),
                                heading=current_heading,
                                order_index=order_index,
                                source_start=current_start,
                                source_end=line_pos,
                            )
                        )
                        order_index += 1
                        current_lines = []
                        current_type = None

                    in_code_block = True
                    code_fence_lang = stripped[3:].strip().lower()
                    code_block_start = line_pos
                    current_lines.append(line)
                    i += 1
                    continue
                else:
                    # Closing fence
                    in_code_block = False
                    current_lines.append(line)
                    raw_content = "".join(current_lines).strip()
                    # Determine whether it's SQL or generic code
                    is_sql = code_fence_lang in {"sql", "mysql", "postgresql", "postgres", "sqlite"}
                    if not is_sql:
                        # Inspect inner content for sql keywords
                        inner = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", raw_content)
                        inner = re.sub(r"\n?```$", "", inner).strip()
                        first_word = inner.split()[0].lower() if inner.split() else ""
                        if first_word in self.SQL_KEYWORDS and ("from" in inner.lower() or "table" in inner.lower()):
                            is_sql = True

                    sections.append(
                        ParsedSection(
                            section_type="sql" if is_sql else "code",
                            content=raw_content,
                            heading=current_heading,
                            order_index=order_index,
                            source_start=code_block_start,
                            source_end=current_pos,
                        )
                    )
                    order_index += 1
                    current_lines = []
                    current_type = None
                    code_fence_lang = ""
                    i += 1
                    continue

            if in_code_block:
                current_lines.append(line)
                i += 1
                continue

            # Heading detection (#, ##, ###)
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                if current_lines:
                    sections.append(
                        ParsedSection(
                            section_type=current_type or "paragraph",
                            content="".join(current_lines).strip(),
                            heading=current_heading,
                            order_index=order_index,
                            source_start=current_start,
                            source_end=line_pos,
                        )
                    )
                    order_index += 1
                    current_lines = []
                    current_type = None

                heading_text = heading_match.group(2).strip()
                current_heading = heading_text
                sections.append(
                    ParsedSection(
                        section_type="heading",
                        content=stripped,
                        heading=heading_text,
                        order_index=order_index,
                        source_start=line_pos,
                        source_end=current_pos,
                    )
                )
                order_index += 1
                i += 1
                continue

            # Empty line separator
            if not stripped:
                if current_lines:
                    sections.append(
                        ParsedSection(
                            section_type=current_type or "paragraph",
                            content="".join(current_lines).strip(),
                            heading=current_heading,
                            order_index=order_index,
                            source_start=current_start,
                            source_end=line_pos,
                        )
                    )
                    order_index += 1
                    current_lines = []
                    current_type = None
                i += 1
                continue

            # Table line detection (| col1 | col2 |)
            is_table_line = stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

            # List line detection (*, -, +, or 1., 2.)
            is_list_line = bool(re.match(r"^(\*|-|\+|\d+\.)\s+", stripped))

            # Raw SQL line detection (e.g. standalone SELECT ... FROM ...)
            is_sql_start = False
            first_token = stripped.split()[0].lower() if stripped.split() else ""
            if first_token in {"select", "insert", "create", "alter", "drop", "with"} and not is_table_line and not is_list_line:
                if ("from" in stripped.lower() or "table" in stripped.lower() or "into" in stripped.lower() or ";" in stripped):
                    is_sql_start = True

            target_type = "table" if is_table_line else ("list" if is_list_line else ("sql" if is_sql_start else "paragraph"))

            if current_type is None:
                current_type = target_type
                current_start = line_pos
                current_lines.append(line)
            elif current_type == target_type:
                current_lines.append(line)
            else:
                # Flush type change
                sections.append(
                    ParsedSection(
                        section_type=current_type,
                        content="".join(current_lines).strip(),
                        heading=current_heading,
                        order_index=order_index,
                        source_start=current_start,
                        source_end=line_pos,
                    )
                )
                order_index += 1
                current_type = target_type
                current_start = line_pos
                current_lines = [line]

            i += 1

        # Flush remaining
        if current_lines:
            sections.append(
                ParsedSection(
                    section_type=current_type or "paragraph",
                    content="".join(current_lines).strip(),
                    heading=current_heading,
                    order_index=order_index,
                    source_start=current_start,
                    source_end=current_pos,
                )
            )

        # Filter empty sections
        return [s for s in sections if s.content]

