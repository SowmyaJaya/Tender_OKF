
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

from datetime import datetime, timezone
from pathlib import Path

import pymupdf as fitz


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

PDF_DIR = (
    ROOT_DIR
    / "data"
    / "BMRCL_TenderData"
    / "Tender_Documents"
)

ADDENDUM_DIR = (
    ROOT_DIR
    / "data"
    / "BMRCL_TenderData"
    / "Addendum_Corrigendum"
)

OUTPUT_DIR = (
    ROOT_DIR
    / "data"
    / "parsed_json"
    / "sections"
)


# ============================================================
# ORIGINAL TENDER VOLUMES
# All ranges are physical PDF page numbers (starting at 1).
# ============================================================

MANIFEST = {
    1: {
        "pdf": "Vol1DLNP1.pdf",
        "sections": [
            ("front", "Front Matter", 1, 6),
            ("A", "Notice Inviting Tender", 7, 8),
            ("online_bid", "Online Bid Instructions", 9, 9),
            ("B", "Instructions to Tenderers", 10, 25),
            ("C", "Eligibility Qualification Criteria", 26, 36),
            ("D", "Letter of Technical Bid", 37, 65),
            ("E", "General Conditions of Contract", 66, 143),
            ("F", "Special Conditions of Contract", 144, 145),
            ("G", "Contract Forms", 146, 156),
        ],
    },

    2: {
        "pdf": "Vol2DLNP1.pdf",
        "sections": [
            ("front", "Front Matter", 1, 4),
            ("part1", "General", 5, 8),
            ("part2", "Engineering Controls", 9, 14),
            ("part3", "Scope of Work", 15, 19),
            ("annexures", "Annexures", 20, 22),
            ("part4", "Technical Specifications", 23, 40),
        ],
    },

    3: {
        "pdf": "Vol3DLNP1.pdf",
        "sections": [
            ("front", "Front Matter", 1, 7),
            ("part1", "SHE Management", 8, 30),
            ("part2", "Safety", 31, 63),
            ("part3", "Occupational Health", 64, 72),
            ("part4", "Environmental Management", 73, 79),
            ("part5", "Penalty and Awards", 80, 87),
            ("appendices", "SHE Appendices", 88, 118),
        ],
    },

    4: {
        "pdf": "Vol4DLNP1.pdf",
        "sections": [
            ("front", "Front Matter", 1, 2),
            ("J", "Financial Document", 3, 10),
        ],
    },
}


# ============================================================
# ADDENDUM AND CORRIGENDUM SOURCE FILES
# ============================================================

AMENDMENTS = {
    1: "DLN_P1_AandC1_157.PDF",
    2: "AandC2_DLN_P1_157.PDF",
    3: "AandC3_DLN_P1_157.PDF",
}


# ============================================================
# SOURCE-SPECIFIC AMENDMENT REGIONS
#
# Format:
# (
#   pdf_page,
#   reference,
#   top, bottom,
#   left, middle, right,
#   target,
#   description
# )
#
# Coordinates are approximate PDF points.
# They must be validated against the original scans.
# ============================================================

AMENDMENT_ROW_REGIONS = {
    1: [
        (
            1, "NIT Key Details 5",
            242, 267, 151, 478, 814,
            "Volume 1 / Section A",
            "Tender document availability",
        ),
        (
            1, "NIT Key Details 10",
            267, 302, 151, 478, 814,
            "Volume 1 / Section A",
            "Online tender submission",
        ),
        (
            1, "NIT Key Details 11",
            302, 329, 151, 478, 814,
            "Volume 1 / Section A",
            "Technical bid opening",
        ),
        (
            1, "NIT Key Details 12",
            329, 489, 151, 478, 814,
            "Volume 1 / Section A",
            "Physical EMD submission",
        ),
    ],

    2: [
        (
            1, "GCC 12.3.1 (iii) c",
            238, 429, 167, 495, 829,
            "Volume 1 / Section E",
            "Minor-value quantity variation",
        ),
        (
            1, "Contract Data 14",
            429, 506, 167, 495, 829,
            "Volume 1 / Section E",
            "Price variation",
        ),
        (
            2, "SCC Clauses 4-8",
            210, 506, 164, 490, 822,
            "Volume 1 / Section F",
            "SCC inserted clauses, first part",
        ),
        (
            3, "SCC Clauses 9-10",
            173, 280, 169, 495, 829,
            "Volume 1 / Section F",
            "SCC inserted clauses, continuation",
        ),
    ],

    3: [
        (
            1, "NIT Key Details 5",
            220, 249, 171, 498, 818,
            "Volume 1 / Section A",
            "Tender document availability",
        ),
        (
            1, "NIT Key Details 10",
            249, 281, 171, 498, 818,
            "Volume 1 / Section A",
            "Online tender submission",
        ),
        (
            1, "NIT Key Details 11",
            281, 307, 171, 498, 818,
            "Volume 1 / Section A",
            "Technical bid opening",
        ),
        (
            1, "NIT Key Details 12",
            307, 470, 171, 498, 818,
            "Volume 1 / Section A",
            "Physical EMD submission",
        ),
    ],
}


# ============================================================
# REGEX PATTERNS
# ============================================================

CLAUSE_RE = re.compile(
    r"^\s*(\d{1,3}(?:\.\d{1,3}){0,3}\.?)\s+(\S.*)$"
)

TIME_RE = re.compile(
    r"^\d{1,2}\.\d{2}"
    r"(?:\s*(?:AM|PM|Hrs)\b|\.\d{4}\b)",
    re.IGNORECASE,
)

DATE_RE = re.compile(
    r"^\d{1,2}\.\d{1,2}\.\d{4}$"
)


# ============================================================
# BASIC UTILITIES
# ============================================================

def file_hash(path):
    """Calculate SHA256 of an original PDF."""

    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def bbox_values(rect):
    """Convert a PDF rectangle into JSON coordinates."""

    return [
        round(float(value), 2)
        for value in rect
    ]


def save_json(data, path):
    """Write extraction results as UTF-8 JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    checks = data["quality_checks"]

    print(
        f"OK {path.name} | "
        f"{checks['source_pages_extracted']} pages | "
        f"{checks['total_detected_tables']} tables | "
        f"{checks['total_candidate_clauses']} candidate clauses | "
        f"OCR pages {len(checks['ocr_pages'])}"
    )

    if checks["pages_with_no_text"]:
        print(
            "  WARNING: No extracted text on pages:",
            checks["pages_with_no_text"],
        )

    if checks["ocr_errors"]:
        print(
            "  WARNING: OCR execution errors:",
            checks["ocr_errors"],
        )

    if checks.get("change_ocr_errors"):
        print(
            "  WARNING: Amendment OCR issues:",
            len(checks["change_ocr_errors"]),
        )

    if checks.get("change_review_notes"):
        print(
            "  REVIEW: Amendment review notes:",
            len(checks["change_review_notes"]),
        )


# ============================================================
# TESSERACT DETECTION
# ============================================================

def find_tesseract():
    """
    Find Tesseract on Windows or other systems.
    """

    executable = shutil.which("tesseract")

    if executable:
        return executable

    windows_path = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if windows_path.exists():
        return str(windows_path)

    return None


def configure_tesseract():
    """
    Configure the environment for PyMuPDF OCR.
    """

    import os

    executable = find_tesseract()

    if executable is None:
        raise RuntimeError(
            "Tesseract OCR not found. "
            "Install Tesseract or add it to PATH."
        )

    tessdata = Path(executable).parent / "tessdata"

    if tessdata.exists():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)

    return executable


# ============================================================
# ORIGINAL PDF TABLE EXTRACTION
# ============================================================

def extract_tables(page):
    """
    Extract vector-based tables from a PDF page.

    Scanned amendment tables are processed separately
    through cropped OCR regions.
    """

    tables = []

    try:
        detected = page.find_tables(
            strategy="lines"
        )

        for index, table in enumerate(
            detected.tables,
            start=1,
        ):

            rows = []

            for row_number, row in enumerate(
                table.rows
            ):

                cells = []

                for column_number, cell in enumerate(
                    row.cells
                ):

                    if cell is None:
                        cells.append({
                            "column": column_number,
                            "text": "",
                            "bbox": None,
                        })
                        continue

                    rect = fitz.Rect(cell)

                    cell_text = page.get_text(
                        "text",
                        clip=rect,
                        sort=True,
                    ).strip()

                    cells.append({
                        "column": column_number,
                        "text": cell_text,
                        "bbox": bbox_values(rect),
                    })

                rows.append({
                    "row_index": row_number,
                    "cells": cells,
                })

            tables.append({
                "table_id": (
                    f"page{page.number + 1}_table{index}"
                ),
                "pdf_page": page.number + 1,
                "bbox": bbox_values(table.bbox),
                "rows": rows,
                "review_status": "pending_manual_review",
            })

    except Exception as error:
        print(
            f"  Table detection warning, "
            f"page {page.number + 1}: {error}"
        )

    return tables


# ============================================================
# OCR A SPECIFIC REGION OF AN ORIGINAL PDF
# ============================================================

def ocr_source_region(
    page,
    rectangle,
    dpi=300,
    tesseract_executable=None,
):
    """
    Render one crop of the original PDF and OCR it.

    Returns:
        text, error

    A blank OCR result is not automatically an error,
    because some original cells may legitimately be empty.
    """

    region = fitz.Rect(rectangle) & page.rect

    if (
        region.is_empty
        or region.width < 3
        or region.height < 3
    ):
        return "", "Invalid or empty crop region"

    executable = (
        tesseract_executable
        or find_tesseract()
    )

    if not executable:
        return "", "Tesseract executable not found"

    with tempfile.TemporaryDirectory(
        prefix="tender_ocr_"
    ) as folder:

        image_path = Path(folder) / "region.png"

        page.get_pixmap(
            clip=region,
            dpi=dpi,
            alpha=False,
        ).save(str(image_path))

        try:
            process = subprocess.run(
                [
                    executable,
                    str(image_path),
                    "stdout",
                    "-l", "eng",
                    "--psm", "6",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )

        except (
            OSError,
            subprocess.TimeoutExpired,
        ) as error:
            return "", str(error)

        if process.returncode != 0:
            return (
                "",
                process.stderr.strip()
                or "Tesseract failed",
            )

        return process.stdout.strip(), None


# ============================================================
# PAGE-WISE ORIGINAL PDF EXTRACTION
# ============================================================

def extract_page(page, use_ocr=False):
    """
    Extract raw text, blocks, lines, tables, and geometry.

    OCR is attempted when a page has no selectable text.
    """

    native_text = page.get_text(
        "text",
        sort=True,
    )

    textpage = None
    ocr_used = False
    ocr_error = None

    if use_ocr and not native_text.strip():

        try:
            textpage = page.get_textpage_ocr(
                language="eng",
                dpi=250,
                full=True,
            )

            ocr_used = True

        except Exception as error:
            ocr_error = str(error)

    options = {}

    if textpage is not None:
        options["textpage"] = textpage

    raw_text = page.get_text(
        "text",
        sort=not ocr_used,
        **options,
    )

    text_blocks = []

    for block in page.get_text(
        "blocks",
        sort=not ocr_used,
        **options,
    ):

        if len(block) < 7 or block[6] != 0:
            continue

        text = str(block[4]).strip()

        if text:
            text_blocks.append({
                "block_number": block[5],
                "bbox": bbox_values(block[:4]),
                "text": text,
            })

    lines = []

    page_dict = page.get_text(
        "dict",
        sort=not ocr_used,
        **options,
    )

    for block in page_dict.get("blocks", []):

        for line in block.get("lines", []):

            line_text = "".join(
                span.get("text", "")
                for span in line.get("spans", [])
            ).strip()

            if line_text:
                lines.append({
                    "bbox": bbox_values(line["bbox"]),
                    "text": line_text,
                })

    lines.sort(
        key=lambda item: (
            item["bbox"][1],
            item["bbox"][0],
        )
    )

    return {
        "pdf_page": page.number + 1,
        "width": round(page.rect.width, 2),
        "height": round(page.rect.height, 2),
        "raw_text": raw_text,
        "text_blocks": text_blocks,
        "lines": lines,
        "tables": extract_tables(page),
        "is_scanned": not bool(native_text.strip()),
        "needs_ocr": not bool(raw_text.strip()),
        "ocr_used": ocr_used,
        "ocr_error": ocr_error,
    }


# ============================================================
# CANDIDATE CLAUSE DETECTION
# ============================================================

def detect_clauses(pages):
    """
    Detect potential numbered clauses.

    Do not treat them as verified tender clauses.
    """

    clauses = []

    for page in pages:

        table_boxes = [
            table["bbox"]
            for table in page["tables"]
        ]

        for line in page["lines"]:

            text = line["text"].strip()
            bbox = line["bbox"]

            if not text:
                continue

            if TIME_RE.match(text):
                continue

            match = CLAUSE_RE.match(text)

            if not match:
                continue

            clause_id = match.group(1)

            if DATE_RE.fullmatch(clause_id):
                continue

            center_x = (
                bbox[0] + bbox[2]
            ) / 2

            center_y = (
                bbox[1] + bbox[3]
            ) / 2

            inside_table = any(
                rect[0] <= center_x <= rect[2]
                and rect[1] <= center_y <= rect[3]
                for rect in table_boxes
            )

            if inside_table:
                continue

            clauses.append({
                "clause_id": clause_id,
                "heading_line": text,
                "pdf_page": page["pdf_page"],
                "bbox": bbox,
                "review_status": "candidate_needs_review",
            })

    return clauses


# ============================================================
# EXTRACT ONE SECTION
# ============================================================

def extract_document(
    pdf_path,
    volume,
    section,
    title,
    start_page,
    end_page,
    use_ocr=False,
):
    """Extract a selected range from an original PDF."""

    with fitz.open(pdf_path) as document:

        if not (
            1 <= start_page <= end_page <= len(document)
        ):
            raise ValueError(
                f"Invalid PDF range: "
                f"{start_page}-{end_page}"
            )

        pages = [
            extract_page(
                document[index],
                use_ocr=use_ocr,
            )
            for index in range(
                start_page - 1,
                end_page,
            )
        ]

    clauses = detect_clauses(pages)

    return {
        "document_metadata": {
            "source_id": pdf_path.stem,
            "source_path": str(pdf_path.resolve()),
            "source_sha256": file_hash(pdf_path),
            "volume": volume,
            "section": section,
            "title": title,
            "start_pdf_page": start_page,
            "end_pdf_page": end_page,
            "extraction_method": (
                "PyMuPDF with optional Tesseract OCR"
            ),
            "review_status": "pending_manual_review",
            "extracted_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
        },

        "pages": pages,

        "candidate_clauses": clauses,

        "quality_checks": {
            "source_pages_expected": (
                end_page - start_page + 1
            ),
            "source_pages_extracted": len(pages),
            "scanned_pages": [
                p["pdf_page"]
                for p in pages
                if p["is_scanned"]
            ],
            "ocr_pages": [
                p["pdf_page"]
                for p in pages
                if p["ocr_used"]
            ],
            "pages_with_no_text": [
                p["pdf_page"]
                for p in pages
                if p["needs_ocr"]
            ],
            "ocr_errors": [
                {
                    "pdf_page": p["pdf_page"],
                    "error": p["ocr_error"],
                }
                for p in pages
                if p["ocr_error"]
            ],
            "total_detected_tables": sum(
                len(p["tables"])
                for p in pages
            ),
            "total_candidate_clauses": len(clauses),
            "notes": [
                "Extracted from original PDF.",
                "Page coordinates preserved.",
                "Clauses are unverified candidates.",
                "Tables and OCR need manual review.",
                "Output is not yet ingestion-ready.",
            ],
        },
    }


# ============================================================
# AMENDMENT COMPARISON COLUMN EXTRACTION
# ============================================================

def read_amendment_change_regions(
    pdf_path,
    number,
    tesseract_executable=None,
):
    """
    Extract existing and replacement wording separately.

    Distinguishes execution errors from review notes
    about possibly blank original cells.
    """

    changes = []

    regions = AMENDMENT_ROW_REGIONS.get(
        number, []
    )

    with fitz.open(pdf_path) as document:

        for (
            page_num,
            reference,
            top,
            bottom,
            left,
            middle,
            right,
            target,
            description,
        ) in regions:

            if not 1 <= page_num <= len(document):
                print(
                    "WARNING: Unavailable page:",
                    number,
                    page_num,
                )
                continue

            page = document[page_num - 1]

            existing_bbox = [
                left + 3,
                top + 1,
                middle - 3,
                bottom - 1,
            ]

            replacement_bbox = [
                middle + 3,
                top + 1,
                right - 3,
                bottom - 1,
            ]

            existing_text, existing_error = (
                ocr_source_region(
                    page,
                    existing_bbox,
                    tesseract_executable=tesseract_executable,
                )
            )

            replacement_text, replacement_error = (
                ocr_source_region(
                    page,
                    replacement_bbox,
                    tesseract_executable=tesseract_executable,
                )
            )

            execution_errors = [
                error
                for error in (
                    existing_error,
                    replacement_error,
                )
                if error
            ]

            review_notes = []

            is_new_scc_entry = (
                number == 2
                and reference in (
                    "SCC Clauses 4-8",
                    "SCC Clauses 9-10",
                )
            )

            # An empty original column for newly inserted
            # SCC clauses may be intentional.
            # It must still be checked against the PDF.
            if not existing_text:

                if is_new_scc_entry:
                    review_notes.append(
                        "Existing text is empty. "
                        "This may be a newly added SCC clause; "
                        "confirm against original PDF."
                    )

                else:
                    review_notes.append(
                        "Existing-column text is empty. "
                        "Verify whether OCR missed the content."
                    )

            if not replacement_text:
                review_notes.append(
                    "Replacement-column text is empty. "
                    "Check the original PDF."
                )

            if (
                number == 2
                and reference == "Contract Data 14"
            ):
                review_notes.append(
                    "Verify GCC subclause numbers and "
                    "the exact price-variation wording."
                )

            if (
                number == 2
                and reference.startswith("SCC Clauses")
            ):
                review_notes.append(
                    "Verify individual SCC clause numbers "
                    "and deleted provisions."
                )

            changes.append({
                "amendment_number": number,
                "target": target,
                "target_reference": reference,
                "description": description,
                "source_pdf_page": page_num,

                "existing": {
                    "text": existing_text,
                    "bbox": existing_bbox,
                },

                "replacement": {
                    "text": replacement_text,
                    "bbox": replacement_bbox,
                },

                "ocr_errors": execution_errors,
                "review_notes": review_notes,
                "review_status": "pending_manual_review",
                "automatically_applied": False,
            })

    return changes


# ============================================================
# EXTRACT ALL ORIGINAL VOLUME SECTIONS
# ============================================================

def extract_volumes(args):

    for volume, config in MANIFEST.items():

        if (
            args.volume is not None
            and volume != args.volume
        ):
            continue

        pdf_path = PDF_DIR / config["pdf"]

        if not pdf_path.exists():
            print("WARNING: Missing PDF:", pdf_path)
            continue

        for section, title, start, end in config["sections"]:

            if args.section:
                if section.lower() != args.section.lower():
                    continue

            result = extract_document(
                pdf_path=pdf_path,
                volume=volume,
                section=section,
                title=title,
                start_page=start,
                end_page=end,
                use_ocr=args.ocr,
            )

            output = OUTPUT_DIR / (
                f"vol{volume}_{section}.json"
            )

            save_json(result, output)


# ============================================================
# EXTRACT ADDENDUM / CORRIGENDUM FILES
# ============================================================

def extract_addendums(args):

    executable = (
        configure_tesseract()
        if args.ocr
        else None
    )

    for number, filename in AMENDMENTS.items():

        pdf_path = ADDENDUM_DIR / filename

        if not pdf_path.exists():
            print(
                "WARNING: Missing amendment:",
                pdf_path,
            )
            continue

        with fitz.open(pdf_path) as document:
            page_count = len(document)

        result = extract_document(
            pdf_path=pdf_path,
            volume=None,
            section=f"AandC{number}",
            title=f"Addendum and Corrigendum {number}",
            start_page=1,
            end_page=page_count,
            use_ocr=args.ocr,
        )

        metadata = result["document_metadata"]

        metadata["document_type"] = (
            "addendum_corrigendum"
        )

        metadata["amendment_number"] = number

        if args.ocr:
            changes = read_amendment_change_regions(
                pdf_path,
                number,
                tesseract_executable=executable,
            )
        else:
            changes = []
            print(
                f"WARNING: Amendment {number} "
                "requires --ocr for comparison columns."
            )

        result["amendment_changes"] = changes

        checks = result["quality_checks"]

        checks["change_entries"] = len(changes)

        # Actual OCR execution errors.
        checks["change_ocr_errors"] = [
            {
                "reference": change["target_reference"],
                "errors": change["ocr_errors"],
            }
            for change in changes
            if change["ocr_errors"]
        ]

        # Separate manual-review items.
        checks["change_review_notes"] = [
            {
                "reference": change["target_reference"],
                "notes": change["review_notes"],
            }
            for change in changes
            if change["review_notes"]
        ]

        checks["notes"].extend([
            "Amendment columns were extracted "
            "from approximate source-specific regions.",
            "Blank original cells do not automatically "
            "represent an OCR failure.",
            "All changes require manual validation.",
            "Amendments have not been automatically applied.",
        ])

        output = OUTPUT_DIR / (
            f"addendum_corrigendum_{number}.json"
        )

        save_json(result, output)

        print(
            f"  Comparison regions: {len(changes)}"
        )


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Extract tender volumes and amendments "
            "section-wise from original PDFs"
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--list",
        action="store_true",
        help="Display all mapped documents and sections",
    )

    group.add_argument(
        "--all",
        action="store_true",
        help="Extract all four volumes and all amendments",
    )

    group.add_argument(
        "--addenda",
        action="store_true",
        help="Extract Addendum/Corrigendum 1, 2 and 3",
    )

    group.add_argument(
        "--volume",
        type=int,
        choices=[1, 2, 3, 4],
        help="Extract one volume",
    )

    parser.add_argument(
        "--section",
        help="Specific section of selected volume",
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Enable OCR for scanned PDF pages",
    )

    args = parser.parse_args()

    if args.section and args.volume is None:
        parser.error(
            "--section requires --volume"
        )

    if args.list:

        for volume, config in MANIFEST.items():

            print(f"\nVolume {volume}")

            for code, title, start, end in config["sections"]:
                print(
                    f"  {code}: {title} "
                    f"(pages {start}-{end})"
                )

        print("\nAddendum and Corrigendum")

        for number, filename in AMENDMENTS.items():
            print(f"  {number}: {filename}")

        return

    if args.ocr:
        executable = configure_tesseract()
        print("Tesseract:", executable)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if args.all or args.volume is not None:
        extract_volumes(args)

    if args.all or args.addenda:
        extract_addendums(args)

    print(
        "\nExtraction completed. "
        "Review JSON against original PDFs "
        "before ingestion."
    )


if __name__ == "__main__":
    main()
