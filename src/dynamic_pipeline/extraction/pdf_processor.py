import fitz  # PyMuPDF
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class PageData:
    page_number: int        # 1-indexed (matches pdf_page in JSON)
    rotation: int           # degrees: 0, 90, 180, 270
    text_blocks: List[Dict[str, Any]] # list of dicts with bbox, text, block_number
    raw_text: str

def compute_sha256(pdf_path: str) -> str:
    """
    Computes the SHA-256 hash of a file for deterministic traceability.
    Reads in chunks to handle large PDFs efficiently.
    """
    sha256_hash = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        # Read in 4K chunks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_pages(pdf_path: str) -> List[PageData]:
    """
    Reads a PDF and extracts text blocks, bounding boxes, and rotation data.
    Ensures blocks are sorted in human reading order (top-to-bottom, left-to-right).
    """
    pages_data = []
    doc = fitz.open(pdf_path)
    
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1
        rotation = page.rotation
        
        # Raw string extraction for fallback/reference
        raw_text = page.get_text("text")
        
        # Extract structured text blocks
        # get_text("blocks") returns tuples: (x0, y0, x1, y1, text, block_no, block_type)
        raw_blocks = page.get_text("blocks")
        
        text_blocks = []
        for block in raw_blocks:
            # block_type == 0 strictly denotes text (1 is for images)
            if len(block) >= 7 and block[6] == 0:
                # Extract and format the bounding box coordinates [x0, y0, x1, y1]
                bbox = [
                    float(block[0]), 
                    float(block[1]), 
                    float(block[2]), 
                    float(block[3])
                ]
                text = block[4].strip()
                block_number = int(block[5])
                
                # Skip empty blocks or pure whitespace
                if text:
                    text_blocks.append({
                        "block_number": block_number,
                        "bbox": bbox,
                        "text": text
                    })
        
        # CRITICAL: Sort blocks for the heuristic parser.
        # Primary sort: Y-coordinate (top-to-bottom). We round to nearest integer to handle slight baseline shifts.
        # Secondary sort: X-coordinate (left-to-right).
        text_blocks.sort(key=lambda b: (round(b["bbox"][1], 0), round(b["bbox"][0], 0)))
        
        # Re-index the block_numbers after sorting so they represent the true visual order
        for idx, block in enumerate(text_blocks):
            block["block_number"] = idx
            
        pages_data.append(PageData(
            page_number=page_num,
            rotation=rotation,
            text_blocks=text_blocks,
            raw_text=raw_text
        ))
        
    doc.close()
    return pages_data
