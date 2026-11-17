import json
import os
from pathlib import Path
from .okf_templates import generate_frontmatter

def render_markdown_table(table_data: dict) -> str:
    """
    Converts a JSON table dictionary (with row_index and col_index) 
    into a standard Markdown pipe table.
    """
    if not table_data.get("rows"):
        return ""
        
    rows = table_data["rows"]
    # Sort rows to ensure correct physical order
    rows.sort(key=lambda r: r.get("row_index", 0))
    
    md_table = []
    for i, row in enumerate(rows):
        # Sort cells left-to-right
        cells = sorted(row.get("cells", []), key=lambda c: c.get("col_index", 0))
        # Strip newlines from cell text to prevent markdown table breaks
        row_text = "| " + " | ".join(c.get("text", "").replace("\n", " ") for c in cells) + " |"
        md_table.append(row_text)
        
        # Insert Markdown table separator immediately after the header row
        if i == 0:
            sep = "| " + " | ".join("---" for _ in cells) + " |"
            md_table.append(sep)
            
    return "\n".join(md_table) + "\n\n"

def generate_markdown(tender_document: dict) -> str:
    """
    Orchestrates the conversion of a validated TenderDocument JSON 
    into a complete OKF Markdown string.
    """
    metadata = tender_document.get("document_metadata", {})
    clauses = tender_document.get("clauses", [])
    
    # Dynamically determine the PDF page range for the frontmatter
    all_pages = set()
    for clause in clauses:
        for frag in clause.get("fragments", []):
            all_pages.add(frag["pdf_page"])
    
    pdf_pages_str = ""
    if all_pages:
        min_p, max_p = min(all_pages), max(all_pages)
        pdf_pages_str = f"{min_p}-{max_p}" if min_p != max_p else str(min_p)
        
    # Dynamically determine the Clause range
    clause_ids = [c["clause_id"] for c in clauses if c.get("clause_id")]
    clause_range = f"{clause_ids[0]}-{clause_ids[-1]}" if clause_ids else ""

    # Assemble Extra Fields for Frontmatter
    extra_fields = {
        "tender_no": "BMRCL/Phase-3/JPN-MRS/Demolition/DLN-P1/2026/157", # Standardized for DLN-P1
        "clause_range": clause_range,
        "pdf_pages": pdf_pages_str,
        "tags": [
            "bmrcl", 
            "government-procurement", 
            "public-tender", 
            metadata.get("title", "").lower().replace(" ", "-")
        ],
        "relations": [{"type": "belongs_to", "target": "index.md"}]
    }
    
    md_lines = []
    
    # 1. Frontmatter
    md_lines.append(generate_frontmatter(metadata, **extra_fields))
    
    # 2. Main Title
    title = metadata.get("title", "Section")
    md_lines.append(f"\n# {title}\n")
    
    # 3. Clauses and Fragments
    for clause in clauses:
        # Parent clauses get H2 (##), Sub-clauses get H3 (###)
        level = "###" if clause.get("parent_clause") else "##"
        c_id = clause.get("clause_id", "")
        heading = clause.get("heading_line")
        
        if heading:
            md_lines.append(f"\n{level} Clause {c_id} — {heading}\n")
        else:
            md_lines.append(f"\n{level} Clause {c_id}\n")
            
        # Compile source attribution
        pages = sorted(list(set(f["pdf_page"] for f in clause.get("fragments", []))))
        if pages:
            p_str = ", ".join(map(str, pages))
            md_lines.append(f"<!-- Source: PDF page {p_str} -->\n")
            
        # Print Text Fragments
        for frag in clause.get("fragments", []):
            md_lines.append(f"{frag['text']}\n")
            
        # Print Markdown Tables
        for table in clause.get("tables", []):
            md_lines.append(render_markdown_table(table))
            
    return "\n".join(md_lines)

def process_and_save(tender_document: dict, output_base_dir: str = "data/OKF_bundle") -> str:
    """
    Main entrypoint for the generation module.
    Takes the JSON dictionary, generates the OKF Markdown, and writes it to the correct directory.
    """
    md_content = generate_markdown(tender_document)
    metadata = tender_document.get("document_metadata", {})
    
    vol = metadata.get("volume", 1)
    sec = metadata.get("section", "UNKNOWN")
    
    # Establish directory structure: data/OKF_bundle/Technical/Vol1/
    output_dir = Path(output_base_dir) / "Technical" / f"Vol{vol}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / f"sec{sec}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    return str(file_path)