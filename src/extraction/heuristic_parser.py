
import re
from typing import List, Dict, Any


# Numbered clauses such as:
# 3. Tender submission...
# 13.0 General Conditions
# 13.1 Definitions
# 13.4.1 Sub-clause
CLAUSE_PATTERN = re.compile(
    r"^[ \t]*(?P<id>\d+\.(?:\d+(?:\.\d+){0,2})?)"
    r"(?=[ \t]+|$)",
    re.MULTILINE,
)

DATE_PATTERN = re.compile(
    r"^\d{1,2}\.\d{1,2}\.\d{4}$"
)

HEADER_FOOTER_PATTERN = re.compile(
    r"("
    r"BMRCL/Phase-\d+"
    r"|Bangalore Metro Rail Corporation Ltd"
    r"|Section Page \d+ of \d+"
    r"|Instructions to Tenderers \(ITT\)"
    r")",
    re.IGNORECASE,
)


def is_date(value: str) -> bool:
    """Return True when a candidate clause ID is a date."""
    return bool(DATE_PATTERN.fullmatch(value.strip()))


def get_parent_clause(clause_id: str):
    """Determine the parent of a hierarchical clause."""

    parts = clause_id.rstrip(".").split(".")

    if len(parts) == 1:
        return None

    if len(parts) == 2:
        if parts[1] == "0":
            return None
        return f"{parts[0]}.0"

    return ".".join(parts[:-1])


def split_numbered_text(text: str):
    """
    Split text when multiple numbered paragraphs are
    present inside one PDF text block.

    The original block bounding box is retained for each
    resulting part, so coordinates are block-level only.
    """

    matches = [
        match
        for match in CLAUSE_PATTERN.finditer(text)
        if not is_date(match.group("id"))
    ]

    if not matches:
        return [(None, text)]

    results = []

    first_start = matches[0].start()

    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            results.append((None, preamble))

    for index, match in enumerate(matches):
        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        part = text[start:end].strip()

        if part:
            results.append((match.group("id"), part))

    return results


def parse_document(
    pages_data: List[Any],
    document_meta: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Extract numbered clauses from PDF text blocks.

    Ambiguous blocks are retained as unmapped text
    for manual review rather than being incorrectly
    assigned to unrelated clauses.
    """

    clauses_dict = {}
    unmapped_text = []

    def add_unmapped(page_num, bbox, text, reason):
        unmapped_text.append({
            "pdf_page": page_num,
            "bbox": bbox,
            "text": text,
            "reason": reason,
        })

    for page in pages_data:

        page_num = page.page_number

        for block in page.text_blocks:

            text = block["text"].strip()
            bbox = block["bbox"]

            if not text:
                continue

            y0 = bbox[1]
            y1 = bbox[3]

            # Preserve potential headers and footers
            # instead of discarding their content.
            if (
                y0 < 65
                or y1 > 760
                or HEADER_FOOTER_PATTERN.search(text)
            ):
                add_unmapped(
                    page_num,
                    bbox,
                    text,
                    "Possible header, footer or administrative text",
                )
                continue

            # Process each independently numbered paragraph.
            segments = split_numbered_text(text)

            for clause_id, segment_text in segments:

                if clause_id is None:

                    add_unmapped(
                        page_num,
                        bbox,
                        segment_text,
                        "Unclassified text or possible table content",
                    )

                    continue

                parent_clause = get_parent_clause(clause_id)

                first_line = segment_text.split("\n")[0].strip()

                if clause_id not in clauses_dict:

                    clauses_dict[clause_id] = {
                        "clause_id": clause_id,
                        "parent_clause": parent_clause,
                        "heading_line": first_line,
                        "review_status": "pending_manual_review",
                        "fragments": [],
                        "tables": [],
                    }

                clauses_dict[clause_id]["fragments"].append({
                    "pdf_page": page_num,
                    "bbox": bbox,
                    "text": segment_text,
                })

    return {
        "document_metadata": document_meta,
        "clauses": list(clauses_dict.values()),
        "unmapped_text": unmapped_text,
    }
