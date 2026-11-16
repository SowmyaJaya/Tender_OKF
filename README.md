## Project Folder Structure

Tender_Ingestion_Pipeline/
├── .gitignore
├── pyproject.toml
├── README.md
│
├── tests/
│   ├── test_extraction.py         # Test regex matching and bbox coordinates
│   ├── test_schema_validation.py  # Test that dicts pass Pydantic validation
│   └── test_okf_generator.py      # Test markdown and YAML formatting
│
├── data/                          # Ignored in version control
│   ├── BMRCL_TenderData/          # Raw input PDFs
│   ├── parsed_json/               # Pydantic-validated JSON outputs
│   └── OKF_bundle/                # Final Markdown and YAML outputs
│
└── src/
    └── dynamic_pipeline/
        ├── __init__.py
        ├── cli.py                 # Your central Click command runner
        ├── state_manager.py       # SQLite database tracker (optional but recommended)
        ├── schema.py              # The Pydantic classes defining your exact data structures
        │
        ├── extraction/            # Module 1: PDF to JSON
        │   ├── __init__.py
        │   ├── pdf_processor.py   # Extracts raw text and bboxes via PyMuPDF
        │   └── heuristic_parser.py# Groups blocks into clauses using regex and outputs JSON
        │
        └── generation/            # Module 2: JSON to OKF & Wiki
            ├── __init__.py
            ├── okf_generator.py   # Converts JSON clauses and tables into Markdown
            ├── okf_templates.py   # Generates OKF v0.2 frontmatter block (YAML)
            └── wiki_linker.py     # Uses LLM to rewrite text with Obsidian [[Wiki Links]]
