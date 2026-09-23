"""
HALO Evidence Verifier: Configuration & Safety Thresholds
=========================================================
Protocol: v1.0-FROZEN
Defines paths to frozen authoritative passage corpora (D1, D2),
NLI model settings, safety thresholds, and cryptographic configuration hash.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any
import hashlib
import json


@dataclass
class EvidenceVerifierConfig:
    """Configuration settings for semantic legal evidence verification."""

    # Corpus paths (strictly read-only)
    repo_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    d1_passages_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "dataset_1" / "final" / "companies_act_2013_passages.jsonl"
    )
    d2_passages_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "dataset2" / "canonical" / "passages.jsonl"
    )

    # NLI Model Specifications
    model_name: str = "cross-encoder/nli-deberta-v3-base"
    device: str = "cpu"
    max_sequence_length: int = 512
    chunk_size: int = 384
    chunk_overlap: int = 64
    batch_size: int = 16

    # Initial Development Thresholds (to be calibrated strictly on Dev)
    entailment_min: float = 0.75
    contradiction_min: float = 0.70
    contradiction_max_for_entailment: float = 0.15
    entailment_max_for_contradiction: float = 0.15

    # Multi-Evidence Conflict Thresholds
    conflict_support_min: float = 0.75
    conflict_contradiction_min: float = 0.70

    # Strict Safety Overrides (Symbolic mismatches block SUPPORTED)
    enforce_symbolic_overrides: bool = True

    # Untrusted text safety bounds
    max_claim_text_length: int = 2000
    max_evidence_text_length: int = 10000

    # Passage Selection Bounds
    max_candidate_passages: int = 8

    # Subsystem metadata
    verifier_version: str = "1.0.0"
    schema_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["repo_root"] = str(self.repo_root)
        d["d1_passages_path"] = str(self.d1_passages_path)
        d["d2_passages_path"] = str(self.d2_passages_path)
        return d

    def compute_config_hash(self) -> str:
        """Computes deterministic SHA-256 hash of configuration state."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
