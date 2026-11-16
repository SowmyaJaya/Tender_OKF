import yaml
from typing import Dict, Any

def generate_frontmatter(metadata: Dict[str, Any], **kwargs) -> str:
    """
    Generates a strict OKF v0.2 compliant YAML frontmatter block.
    Maps DocumentMetadata and dynamic parameters into the required OKF schema.
    """
    # Base OKF requirements
    frontmatter = {
        "type": "tender_section",
        "title": metadata.get("title", "Unknown Section"),
        "status": "source-derived",
        "source_document": metadata.get("source_path", "").split("/")[-1],
        "source_sha256": metadata.get("source_sha256", ""),
        "tender_no": kwargs.get("tender_no", "UNKNOWN_TENDER"),
        "section": metadata.get("section", ""),
        "volume": metadata.get("volume", "")
    }

    # Add dynamic range variables
    if "clause_range" in kwargs:
        frontmatter["clause_range"] = kwargs["clause_range"]
    if "pdf_pages" in kwargs:
        frontmatter["pdf_pages"] = kwargs["pdf_pages"]

    # Add tags and relations
    frontmatter["tags"] = kwargs.get("tags", ["bmrcl", "tender"])
    frontmatter["relations"] = kwargs.get("relations", [{"type": "belongs_to", "target": "index.md"}])

    # Convert dictionary to YAML string, preserving order and formatting
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    
    return f"---\n{yaml_str}---\n"
Building python script to assemble document markdown
