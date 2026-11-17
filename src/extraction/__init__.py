"""
Extraction Module
Handles physical PDF reading (PyMuPDF) and deterministic heuristic parsing.
"""

from .pdf_processor import extract_pages, compute_sha256
from .heuristic_parser import parse_document

__all__ = [
    "extract_pages",
    "compute_sha256",
    "parse_document"
]