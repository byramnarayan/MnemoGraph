from __future__ import annotations

import csv
import io
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import docx
import pypdf

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocumentResult:
    text: str
    structuredness: str  # "STRUCTURED" | "SEMI_STRUCTURED" | "UNSTRUCTURED"
    format: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tables: list[dict[str, Any]] = field(default_factory=list)
    code_blocks: list[dict[str, Any]] = field(default_factory=list)
    inferred_fields: dict[str, Any] = field(default_factory=dict)


class DocumentParser:
    """
    Universal Structure Parser (UKGOE Step 1.1):
    1. Identifies physical format: PDF, DOCX, MD, JSON, CSV, plain text.
    2. Extracts raw text, tables, code blocks, and metadata.
    3. Types data as STRUCTURED, SEMI_STRUCTURED, or UNSTRUCTURED.
    4. Infers semantic field mappings from keys/headers without pre-defined schemas.
    """

    # Semantic keyword patterns for field inference
    PERSON_PATTERNS = re.compile(r"^(assigned_to|assignee|owner|lead|author|manager|created_by|reporter|driver)$", re.IGNORECASE)
    GROUP_PATTERNS = re.compile(r"^(team|group|department|dept|division|squad|unit)$", re.IGNORECASE)
    DATE_PATTERNS = re.compile(r"^(start_date|end_date|due_date|target_date|created_at|resolution_date|decision_date)$", re.IGNORECASE)
    STATUS_PATTERNS = re.compile(r"^(status|state|outcome|stage)$", re.IGNORECASE)
    SEVERITY_PATTERNS = re.compile(r"^(severity|priority|impact_level|risk_level)$", re.IGNORECASE)
    CAUSE_PATTERNS = re.compile(r"^(root_cause|confirmed_cause|initial_cause|reason|cause)$", re.IGNORECASE)

    @classmethod
    def parse_file(
        cls,
        filename: str,
        file_bytes: bytes,
        mime_type: str | None = None,
    ) -> ParsedDocumentResult:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        metadata: dict[str, Any] = {"filename": filename, "extension": ext, "bytes": len(file_bytes)}
        tables: list[dict[str, Any]] = []
        code_blocks: list[dict[str, Any]] = []
        inferred_fields: dict[str, Any] = {}
        structuredness = "UNSTRUCTURED"
        text = ""

        try:
            # 1. JSON (STRUCTURED)
            if ext == "json":
                structuredness = "STRUCTURED"
                mime = "application/json"
                raw_str = file_bytes.decode("utf-8", errors="replace")
                parsed_json = json.loads(raw_str)
                text = json.dumps(parsed_json, indent=2)
                metadata["format"] = mime
                inferred_fields = cls._infer_fields_from_json(parsed_json)

            # 2. CSV (STRUCTURED)
            elif ext == "csv":
                structuredness = "STRUCTURED"
                mime = "text/csv"
                metadata["format"] = mime
                raw_str = file_bytes.decode("utf-8", errors="replace")
                text, tables, inferred_fields = cls._parse_csv(raw_str)

            # 3. Markdown (SEMI-STRUCTURED / UNSTRUCTURED)
            elif ext in ["md", "markdown"]:
                raw_str = file_bytes.decode("utf-8", errors="replace")
                text, tables, code_blocks, is_semi, inferred_fields = cls._parse_markdown(raw_str)
                structuredness = "SEMI_STRUCTURED" if is_semi else "UNSTRUCTURED"
                metadata["format"] = "text/markdown"

            # 4. PDF
            elif ext == "pdf":
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                num_pages = len(reader.pages)
                metadata["pages"] = num_pages
                metadata["format"] = "application/pdf"
                extracted_pages = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted_pages.append(f"--- Page {idx + 1} ---\n{page_text}")
                text = "\n\n".join(extracted_pages)
                # Check for table or key-value structures
                structuredness = "SEMI_STRUCTURED" if ("|" in text or ":" in text[:300]) else "UNSTRUCTURED"

            # 5. DOCX
            elif ext in ["docx", "doc"]:
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                for t_idx, table in enumerate(doc.tables):
                    table_rows = []
                    for row in table.rows:
                        row_cells = [cell.text.strip() for cell in row.cells]
                        if any(row_cells):
                            table_rows.append(row_cells)
                    if table_rows:
                        tables.append({"table_index": t_idx, "rows": table_rows})
                        paragraphs.append("\n".join([" | ".join(r) for r in table_rows]))
                text = "\n\n".join(paragraphs)
                metadata["format"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                structuredness = "SEMI_STRUCTURED" if tables else "UNSTRUCTURED"

            # 6. Fallback Plain Text / Code
            else:
                text = file_bytes.decode("utf-8", errors="replace")
                metadata["format"] = mime_type or "text/plain"
                structuredness = "SEMI_STRUCTURED" if (":" in text[:200] and "\n" in text[:200]) else "UNSTRUCTURED"

        except Exception as e:
            logger.error(f"Error parsing file '{filename}': {e}", exc_info=True)
            text = file_bytes.decode("utf-8", errors="replace")
            metadata["format"] = mime_type or "application/octet-stream"
            metadata["parse_error"] = str(e)

        return ParsedDocumentResult(
            text=text.strip(),
            structuredness=structuredness,
            format=metadata.get("format", "text/plain"),
            metadata=metadata,
            tables=tables,
            code_blocks=code_blocks,
            inferred_fields=inferred_fields,
        )

    @classmethod
    def _infer_fields_from_json(cls, data: Any) -> dict[str, Any]:
        inferred = {}
        target = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else data

        if isinstance(target, dict):
            for k, v in target.items():
                if cls.PERSON_PATTERNS.match(k):
                    inferred["inferred_person"] = v
                elif cls.GROUP_PATTERNS.match(k):
                    inferred["inferred_group"] = v
                elif cls.DATE_PATTERNS.match(k):
                    inferred["inferred_date"] = v
                elif cls.STATUS_PATTERNS.match(k):
                    inferred["inferred_status"] = v
                elif cls.SEVERITY_PATTERNS.match(k):
                    inferred["inferred_severity"] = v
                elif cls.CAUSE_PATTERNS.match(k):
                    inferred["inferred_cause"] = v
        return inferred

    @classmethod
    def _parse_csv(cls, raw_str: str) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        f = io.StringIO(raw_str)
        reader = csv.reader(f)
        rows = list(reader)
        tables = []
        inferred = {}
        if rows:
            headers = [h.strip() for h in rows[0]]
            tables.append({"headers": headers, "rows": rows[1:]})
            for h in headers:
                if cls.PERSON_PATTERNS.match(h):
                    inferred["inferred_person_field"] = h
                elif cls.STATUS_PATTERNS.match(h):
                    inferred["inferred_status_field"] = h
                elif cls.DATE_PATTERNS.match(h):
                    inferred["inferred_date_field"] = h
        return raw_str, tables, inferred

    @classmethod
    def _parse_markdown(cls, text: str) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], bool, dict[str, Any]]:
        code_blocks = []
        tables = []
        inferred = {}
        is_semi = False

        # Extract code blocks
        code_pattern = re.compile(r"```([a-zA-Z0-9_\-]+)?\n(.*?)```", re.DOTALL)
        for m in code_pattern.finditer(text):
            is_semi = True
            code_blocks.append({"language": m.group(1) or "text", "content": m.group(2).strip()})

        # Extract markdown tables
        lines = text.split("\n")
        current_table = []
        for line in lines:
            if "|" in line:
                current_table.append([cell.strip() for cell in line.strip().split("|")[1:-1]])
                is_semi = True
            elif current_table:
                if len(current_table) > 1:
                    tables.append({"headers": current_table[0], "rows": current_table[2:] if len(current_table) > 2 else []})
                current_table = []

        # Check for key-value frontmatter or headers
        if text.startswith("---") or re.search(r"^[A-Za-z0-9_\-\s]{2,25}:\s+.+", text, re.MULTILINE):
            is_semi = True

        return text, tables, code_blocks, is_semi, inferred
