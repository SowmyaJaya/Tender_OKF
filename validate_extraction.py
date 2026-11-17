
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = DATA / "parsed_json" / "sections"
SOURCES = DATA / "BMRCL_TenderData"

VOLUME_FILES = {
    1: "Vol1DLNP1.pdf",
    2: "Vol2DLNP1.pdf",
    3: "Vol3DLNP1.pdf",
    4: "Vol4DLNP1.pdf",
}

AMENDMENT_FILES = {
    1: "DLN_P1_AandC1_157.PDF",
    2: "AandC2_DLN_P1_157.PDF",
    3: "AandC3_DLN_P1_157.PDF",
}


def source_path(metadata):
    amendment = metadata.get("amendment_number")

    if amendment is not None:
        return (
            SOURCES
            / "Addendum_Corrigendum"
            / AMENDMENT_FILES[int(amendment)]
        )

    volume = metadata.get("volume")

    return (
        SOURCES
        / "Tender_Documents"
        / VOLUME_FILES[int(volume)]
    )


def validate_file(path):
    issues = []
    notes = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return [f"Invalid JSON: {error}"], []

    metadata = data.get("document_metadata", {})
    pages = data.get("pages", [])
    checks = data.get("quality_checks", {})

    source = source_path(metadata)

    if not source.exists():
        issues.append(f"Original PDF missing: {source}")
        return issues, notes

    expected_count = checks.get("source_pages_expected")

    if expected_count != len(pages):
        issues.append(
            f"Page count mismatch: expected {expected_count}, "
            f"extracted {len(pages)}"
        )

    with pymupdf.open(source) as pdf:
        for page_data in pages:
            page_number = page_data.get("pdf_page")

            if not isinstance(page_number, int):
                issues.append("Invalid PDF page number")
                continue

            if not 1 <= page_number <= len(pdf):
                issues.append(
                    f"Page {page_number}: outside original PDF"
                )
                continue

            original = pdf[page_number - 1]

            raw_text = page_data.get("raw_text", "")

            if not raw_text.strip():
                images = len(original.get_images(full=True))
                drawings = len(original.get_drawings())

                issues.append(
                    f"Page {page_number}: no extracted text; "
                    f"images={images}, drawings={drawings}"
                )

            if page_data.get("ocr_error"):
                issues.append(
                    f"Page {page_number}: OCR error: "
                    f"{page_data['ocr_error']}"
                )

            for table in page_data.get("tables", []):
                if not table.get("rows"):
                    notes.append(
                        f"Page {page_number}: empty detected table"
                    )

    if not pages:
        issues.append("No extracted pages")

    clauses = data.get("candidate_clauses", [])

    if len(pages) >= 10 and not clauses:
        notes.append(
            "Long section with no detected candidate clauses"
        )

    for change in data.get("amendment_changes", []):
        reference = change.get("target_reference", "Unknown")

        if change.get("ocr_errors"):
            issues.append(
                f"{reference}: OCR execution issue"
            )

        if change.get("review_notes"):
            notes.append(
                f"{reference}: manual review required"
            )

        if not change.get("replacement", {}).get("text", "").strip():
            issues.append(
                f"{reference}: empty replacement text"
            )

    return issues, notes


def main():
    files = sorted(OUTPUT.glob("*.json"))
    report = []

    report.append("TENDER EXTRACTION VALIDATION REPORT")
    report.append("=" * 50)
    report.append(f"JSON files found: {len(files)}")
    report.append("")

    total_issues = 0
    total_notes = 0

    if len(files) != 27:
        report.append(
            f"WARNING: Expected 27 JSON files, found {len(files)}"
        )

    for path in files:
        try:
            issues, notes = validate_file(path)
        except Exception as error:
            issues, notes = [f"Validation failed: {error}"], []

        total_issues += len(issues)
        total_notes += len(notes)

        status = "CHECK" if issues or notes else "STRUCTURE OK"

        report.append(f"{path.name}: {status}")

        for issue in issues:
            report.append(f"  ISSUE: {issue}")

        for note in notes:
            report.append(f"  REVIEW: {note}")

    report.append("")
    report.append(f"Total issues: {total_issues}")
    report.append(f"Total review notes: {total_notes}")

    report.append("")
    report.append(
        "IMPORTANT: Structural checks do not establish "
        "complete or accurate extraction."
    )
    report.append(
        "Clauses, tables, dates, and contractual amendments "
        "must be compared against original PDF pages."
    )

    output = ROOT / "validation_report.txt"

    output.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print("\n".join(report))
    print(f"\nReport saved: {output}")


if __name__ == "__main__":
    main()
