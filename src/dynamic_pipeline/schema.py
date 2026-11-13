from pydantic import BaseModel, Field
from typing import List, Optional

# --- Sub-Models ---

class TextFragment(BaseModel):
    pdf_page: int
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[x0, y0, x1, y1]")
    text: str

class TableCell(BaseModel):
    col_index: int
    bbox: List[float]
    text: str

class TableRow(BaseModel):
    row_index: int
    cells: List[TableCell]

class TableData(BaseModel):
    table_id: str
    pdf_page: int
    table_bbox: List[float]
    rows: List[TableRow]

class UnmappedText(BaseModel):
    pdf_page: int
    bbox: List[float]
    text: str
    reason: str

# --- Core Clause Model ---

class TenderClause(BaseModel):
    clause_id: str
    parent_clause: Optional[str] = None
    heading_line: Optional[str] = None
    review_status: str = "pending_manual_review"
    fragments: List[TextFragment]
    tables: List[TableData] = []

# --- Root Document Model ---

class DocumentMetadata(BaseModel):
    source_id: str
    source_path: str
    source_sha256: str
    volume: int
    section: str
    title: str
    extraction_method: str
    review_status: str = "pending_manual_review"

class TenderDocument(BaseModel):
    document_metadata: DocumentMetadata
    clauses: List[TenderClause]
    unmapped_text: List[UnmappedText] = []