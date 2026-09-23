"""
HALO Citation Verifier: Configuration & Safety Thresholds
=========================================================
Protocol: v1.0-FROZEN
Defines paths to frozen authoritative corpora (D1, D2), matching thresholds,
and inviolable safety parameters.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CitationVerifierConfig:
    """Configuration settings for citation existence and metadata verification."""

    # Corpus paths (strictly read-only)
    repo_root: Path = Path(__file__).resolve().parent.parent.parent
    d1_act_path: Path = repo_root / "data" / "dataset_1" / "final" / "companies_act_2013.json"
    d1_passages_path: Path = repo_root / "data" / "dataset_1" / "final" / "companies_act_2013_passages.jsonl"

    d2_judgments_path: Path = repo_root / "data" / "dataset2" / "canonical" / "judgments.jsonl"
    d2_passages_path: Path = repo_root / "data" / "dataset2" / "canonical" / "passages.jsonl"
    d2_paragraphs_path: Path = repo_root / "data" / "dataset2" / "canonical" / "paragraphs.jsonl"

    # Fuzzy matching threshold (0.0 to 1.0)
    fuzzy_match_threshold: float = 0.85

    # Safety: FUZZY_CANDIDATE strictly barred from emitting EXISTS
    allow_fuzzy_exists: bool = False

    # Default statutory context for ambiguous bare sections in corporate law domain
    default_act_context: str = "Companies Act, 2013"

    # Untrusted text safety bounds
    max_citation_text_length: int = 500
    max_citations_per_answer: int = 100

    # Subsystem metadata
    verifier_version: str = "1.0.0"
    schema_version: str = "1.0.0"
