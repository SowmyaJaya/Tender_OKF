import re
from typing import List, Dict, Any

def parse_document(pages_data: List[Any], document_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies deterministic regex and geometric heuristics to extracted PDF pages.
    Groups text blocks into clauses, sub-clauses, and quarantines headers/footers.
    Outputs a dictionary ready to be validated by the TenderDocument Pydantic model.
    """
    clauses_dict = {}
    unmapped_text = []
    
    # Matches "13.0", "13.1", "13.4.1", etc. and captures the major number for parent linking.
    # re.DOTALL ensures the match group captures the rest of a multi-line block.
    clause_pattern = re.compile(r"^\s*((\d+)\.\d+(?:\.\d+)?)\s*(.*)", flags=re.DOTALL)
    
    # Matches common noise text in BMRCL tenders
    header_footer_pattern = re.compile(
        r"(BMRCL/Phase-\d+|Bangalore Metro Rail Corporation Ltd|Section Page \d+ of \d+|Instructions to Tenderers \(ITT\))", 
        re.IGNORECASE
    )
    
    current_clause_id = None
    current_parent_id = None
    
    for page in pages_data:
        page_num = page.page_number
        
        for block in page.text_blocks:
            text = block["text"].strip()
            bbox = block["bbox"]
            y0, y1 = bbox[1], bbox[3]
            
            # ---------------------------------------------------------
            # Rule 1: Quarantine Headers, Footers, and Administrative Noise
            # ---------------------------------------------------------
            # If the text is at the extreme top/bottom margins, or matches known footer regex
            if y0 < 65 or y1 > 760 or header_footer_pattern.search(text):
                unmapped_text.append({
                    "pdf_page": page_num,
                    "bbox": bbox,
                    "text": text,
                    "reason": "Page header, footer or booklet page number"
                })
                continue
                
            # Skip completely empty blocks that survived stripping
            if not text:
                continue

            # ---------------------------------------------------------
            # Rule 2: Clause and Sub-clause Detection
            # ---------------------------------------------------------
            match = clause_pattern.match(text)
            
            if match:
                clause_id = match.group(1).strip()
                major_id = match.group(2).strip()
                
                # Determine Parent-Child Relationship
                if clause_id.endswith(".0"):
                    # E.g., "13.0" -> This is a root clause
                    current_parent_id = None
                    heading_line = text.split('\n')[0].strip() # First line is the heading
                else:
                    # E.g., "13.4.1" -> Parent is "13.0"
                    current_parent_id = f"{major_id}.0"
                    heading_line = None
                    
                current_clause_id = clause_id
                
                # Initialize new clause if not already created
                if current_clause_id not in clauses_dict:
                    clauses_dict[current_clause_id] = {
                        "clause_id": current_clause_id,
                        "parent_clause": current_parent_id,
                        "heading_line": heading_line,
                        "review_status": "pending_manual_review",
                        "fragments": [],
                        "tables": []
                    }
                
                # Always append the text block to fragments to preserve its exact bbox and text
                clauses_dict[current_clause_id]["fragments"].append({
                    "pdf_page": page_num,
                    "bbox": bbox,
                    "text": text
                })
                
            else:
                # ---------------------------------------------------------
                # Rule 3: Append to Active Clause or Quarantine Preamble
                # ---------------------------------------------------------
                if current_clause_id:
                    clauses_dict[current_clause_id]["fragments"].append({
                        "pdf_page": page_num,
                        "bbox": bbox,
                        "text": text
                    })
                else:
                    # Text encountered before any clause boundary (e.g., Preamble/Intro text)
                    unmapped_text.append({
                        "pdf_page": page_num,
                        "bbox": bbox,
                        "text": text,
                        "reason": "Preamble or orphaned text before first clause"
                    })
                    
    # Return the dictionary formatted exactly as the schema expects
    return {
        "document_metadata": document_meta,
        "clauses": list(clauses_dict.values()),
        "unmapped_text": unmapped_text
    }
Analyzing
