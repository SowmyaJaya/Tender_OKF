## Project Folder Structure

Tender_Ingestion_Pipeline/
├── .gitignore
├── pyproject.toml
├── auto_ingest.py                 #runs continuously on the server. bridge between the user's file upload and pipeline
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





### CLI EXECUTION REFERENCE TABLE
The BMRCL tender is highly segmented, especially across Volumes 2 and 3, and includes Addendums and Financial documents. To automate the ingestion of this exact structure, here is your comprehensive CLI execution reference table.

| Document / Sub-Part | `--pdf` (Expected Source Path) | `--volume` | `--section` | `--title` |
| --- | --- | --- | --- | --- |
| **Volume 1: Technical Documents** |  |  |  |  |
| Notice Inviting Tender | `data/BMRCL_TenderData/Vol1_SecA.pdf` | `1` | `A` | `"Notice Inviting Tender (NIT)"` |
| Instructions to Tenderers | `data/BMRCL_TenderData/Vol1_SecB.pdf` | `1` | `B` | `"Instructions to Tenderers (ITT)"` |
| Eligibility & Qualification | `data/BMRCL_TenderData/Vol1_SecC.pdf` | `1` | `C` | `"Eligibility cum Qualification Criteria (EQC)"` |
| Letter of Technical Bid | `data/BMRCL_TenderData/Vol1_SecD.pdf` | `1` | `D` | `"Letter of Technical Bid"` |
| General Conditions | `data/BMRCL_TenderData/Vol1_SecE.pdf` | `1` | `E` | `"General Conditions of Contract (GCC)"` |
| Special Conditions | `data/BMRCL_TenderData/Vol1_SecF.pdf` | `1` | `F` | `"Special Conditions of Contract (SCC)"` |
| Contract Forms | `data/BMRCL_TenderData/Vol1_SecG.pdf` | `1` | `G` | `"Contract Forms"` |
| **Volume 2: Technical Specifications** |  |  |  |  |
| Tech Specs Part 1 | `data/BMRCL_TenderData/Vol2_Part1.pdf` | `2` | `part1` | `"Technical Specifications - Part 1"` |
| Tech Specs Part 2 | `data/BMRCL_TenderData/Vol2_Part2.pdf` | `2` | `part2` | `"Technical Specifications - Part 2"` |
| Tech Specs Part 3 | `data/BMRCL_TenderData/Vol2_Part3.pdf` | `2` | `part3` | `"Technical Specifications - Part 3"` |
| Tech Specs Part 4A | `data/BMRCL_TenderData/Vol2_Part4A.pdf` | `2` | `part4A` | `"Technical Specifications - Part 4A"` |
| Tech Specs Part 4B | `data/BMRCL_TenderData/Vol2_Part4B.pdf` | `2` | `part4B` | `"Technical Specifications - Part 4B"` |
| **Volume 3: SHE Manual** |  |  |  |  |
| SHE Manual Part 1 | `data/BMRCL_TenderData/Vol3_Part1.pdf` | `3` | `part1` | `"SHE Manual - Part 1"` |
| SHE Manual Part 2 | `data/BMRCL_TenderData/Vol3_Part2.pdf` | `3` | `part2` | `"SHE Manual - Part 2"` |
| SHE Manual Part 3 | `data/BMRCL_TenderData/Vol3_Part3.pdf` | `3` | `part3` | `"SHE Manual - Part 3"` |
| SHE Manual Part 4 | `data/BMRCL_TenderData/Vol3_Part4.pdf` | `3` | `part4` | `"SHE Manual - Part 4"` |
| SHE Manual Part 5 | `data/BMRCL_TenderData/Vol3_Part5.pdf` | `3` | `part5` | `"SHE Manual - Part 5"` |
| SHE Appendices & Forms | `data/BMRCL_TenderData/Vol3_Appendices.pdf` | `3` | `appendices_instructions_forms` | `"SHE Appendices, Instructions & Forms"` |
| **Volume 4: Financial** |  |  |  |  |
| Financial Bid | `data/BMRCL_TenderData/Vol4_SecJ.pdf` | `4` | `J` | `"Financial Document (Pricing Document)"` |
| **Addendums & Corrigendum** |  |  |  |  |
| Addendum 1 | `data/BMRCL_TenderData/Addendum_1.pdf` | `0` | `A_and_C1` | `"Addendum and Corrigendum 1"` |
| Addendum 2 | `data/BMRCL_TenderData/Addendum_2.pdf` | `0` | `A_and_C2` | `"Addendum and Corrigendum 2"` |
| Addendum 3 | `data/BMRCL_TenderData/Addendum_3.pdf` | `0` | `A_and_C3` | `"Addendum and Corrigendum 3"` |
