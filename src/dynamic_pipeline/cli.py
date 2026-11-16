import click
import json
import logging
from pathlib import Path

# Adjusting imports for a proper Python package layout
from .state_manager import StateManager
from .extraction import pdf_reader, heuristic_parser
from .schema import TenderDocument
from .generation import okf_generator

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@click.group()
def main():
    """BMRCL Tender Document Ingestion Pipeline."""
    pass

@main.command()
@click.option('--pdf', required=True, type=click.Path(exists=True), help='Path to the tender PDF file.')
@click.option('--volume', required=True, type=int, help='Volume number (e.g., 1)')
@click.option('--section', required=True, type=str, help='Section letter/identifier (e.g., "B")')
@click.option('--title', required=True, type=str, help='Document title')
@click.option('--out-json', default='data/parsed_json', type=click.Path(), help='Output dir for validated JSON')
@click.option('--out-okf', default='data/OKF_bundle', type=click.Path(), help='Output dir for OKF markdown')
@click.option('--force', is_flag=True, help='Force re-extraction even if already processed')
def process(pdf, volume, section, title, out_json, out_okf, force):
    """Run the end-to-end deterministic extraction and OKF generation."""
    
    state = StateManager()
    pdf_path = str(Path(pdf).resolve())
    
    logging.info(f"Computing SHA-256 for {pdf}...")
    file_hash = pdf_reader.compute_sha256(pdf_path)
    
    # Check state to avoid redundant work unless --force is used
    current_status = state.get_status(file_hash)
    if current_status == 'okf_generated' and not force:
        logging.info(f"Document {file_hash} already fully processed. Use --force to override.")
        return

    state.register_document(source_sha256=file_hash, source_path=pdf_path, volume=volume)

    # 1. Extraction (Pure Code)
    logging.info("Step 1: Extracting text and coordinates via PyMuPDF...")
    try:
        pages_data = pdf_reader.extract_pages(pdf_path)
    except Exception as e:
        state.update_status(file_hash, 'failed', str(e))
        logging.error(f"Extraction failed: {e}")
        return

    # 2. Heuristic Parsing (Pure Code)
    logging.info("Step 2: Applying heuristic regex rules...")
    doc_meta = {
        "source_id": f"bmrcl-volume-{volume}",
        "source_path": pdf_path,
        "source_sha256": file_hash,
        "volume": volume,
        "section": section,
        "title": title,
        "extraction_method": "pure_heuristic_regex",
        "review_status": "pending_manual_review"
    }
    
    try:
        raw_dict = heuristic_parser.parse_document(pages_data, doc_meta)
    except Exception as e:
        state.update_status(file_hash, 'failed', str(e))
        logging.error(f"Heuristic parsing failed: {e}")
        return

    # 3. Pydantic Validation Gate
    logging.info("Step 3: Validating structure against Pydantic schema...")
    try:
        validated_doc = TenderDocument(**raw_dict)
    except Exception as e:
        state.update_status(file_hash, 'failed', str(e))
        logging.error(f"Schema validation failed: {e}")
        return
        
    state.update_status(file_hash, 'extracted')

    # Save Intermediate JSON
    out_json_dir = Path(out_json) / f"Vol{volume}"
    out_json_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_json_dir / f"sec{section}.json"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(validated_doc.model_dump_json(indent=2))
    logging.info(f"Saved validated JSON to {json_path}")

    # 4. OKF Generation
    logging.info("Step 4: Generating OKF Markdown bundle...")
    try:
        md_file_path = okf_generator.process_and_save(
            validated_doc.model_dump(), 
            output_base_dir=out_okf
        )
        state.update_status(file_hash, 'okf_generated')
        logging.info(f"Successfully generated OKF Markdown at {md_file_path}")
    except Exception as e:
        state.update_status(file_hash, 'failed', str(e))
        logging.error(f"OKF generation failed: {e}")
        return
        
if __name__ == '__main__':
    main()
