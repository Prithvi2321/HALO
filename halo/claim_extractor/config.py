"""
HALO Claim Extractor: Configuration
====================================
Protocol: v1.0-FROZEN
Configures extraction parameters, safety thresholds, and citation association policies.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ClaimExtractorConfig:
    """Configuration parameters for the HALO Claim Extractor subsystem."""
    schema_version: str = "1.0.0"
    extractor_version: str = "1.0.0"
    max_answer_length: int = 15000
    max_claim_count: int = 100
    max_citation_count: int = 50
    decompose_compound_claims: bool = True
    citation_proximity_strategy: str = "same_sentence_then_adjacent"  # "same_sentence", "same_sentence_then_adjacent", "global"
    preserve_modality: bool = True
    preserve_numerics: bool = True
    preserve_temporals: bool = True
    strict_span_integrity: bool = True
    allow_empty_claims_on_non_legal: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaimExtractorConfig":
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            extractor_version=data.get("extractor_version", "1.0.0"),
            max_answer_length=int(data.get("max_answer_length", 15000)),
            max_claim_count=int(data.get("max_claim_count", 100)),
            max_citation_count=int(data.get("max_citation_count", 50)),
            decompose_compound_claims=bool(data.get("decompose_compound_claims", True)),
            citation_proximity_strategy=str(data.get("citation_proximity_strategy", "same_sentence_then_adjacent")),
            preserve_modality=bool(data.get("preserve_modality", True)),
            preserve_numerics=bool(data.get("preserve_numerics", True)),
            preserve_temporals=bool(data.get("preserve_temporals", True)),
            strict_span_integrity=bool(data.get("strict_span_integrity", True)),
            allow_empty_claims_on_non_legal=bool(data.get("allow_empty_claims_on_non_legal", True)),
        )
