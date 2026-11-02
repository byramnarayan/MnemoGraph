from __future__ import annotations

import io
import json
import logging
from typing import BinaryIO

import docx
import pypdf

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Extracts text and metadata from uploaded document files.
    Supports: .txt, .md, .pdf, .docx, .json, .csv
    """

    @staticmethod
    def parse_file(filename: str, file_bytes: bytes, mime_type: str | None = None) -> tuple[str, dict[str, any]]:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        text = ""
        metadata: dict[str, any] = {"filename": filename, "extension": ext, "bytes": len(file_bytes)}

        try:
            if ext in ["txt", "md", "markdown", "log", "rst"]:
                text = file_bytes.decode("utf-8", errors="replace")
                metadata["format"] = "text/markdown"

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

            elif ext in ["docx", "doc"]:
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                # Also include table contents if any
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            paragraphs.append(row_text)
                text = "\n\n".join(paragraphs)
                metadata["format"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            elif ext == "json":
                parsed_json = json.loads(file_bytes.decode("utf-8", errors="replace"))
                text = json.dumps(parsed_json, indent=2)
                metadata["format"] = "application/json"

            elif ext == "csv":
                text = file_bytes.decode("utf-8", errors="replace")
                metadata["format"] = "text/csv"

            else:
                # Default fallback: try UTF-8 decoding
                text = file_bytes.decode("utf-8", errors="replace")
                metadata["format"] = mime_type or "application/octet-stream"

        except Exception as e:
            logger.error(f"Error parsing file {filename}: {e}", exc_info=True)
            text = file_bytes.decode("utf-8", errors="replace")

        return text.strip(), metadata

