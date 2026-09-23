"""
HALO Claim Extractor: Data Schemas & Controlled Enums
=====================================================
Protocol: v1.0-FROZEN
Defines the versioned, auditable data contracts for extracted atomic legal claims.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


class ClaimType(str, Enum):
    """Controlled enum of legal and factual claim types."""
    STATUTORY_PROVISION = "STATUTORY_PROVISION"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    LEGAL_PROHIBITION = "LEGAL_PROHIBITION"
    LEGAL_PERMISSION = "LEGAL_PERMISSION"
    LEGAL_REQUIREMENT = "LEGAL_REQUIREMENT"
    PROCEDURAL_REQUIREMENT = "PROCEDURAL_REQUIREMENT"
    NUMERICAL_REQUIREMENT = "NUMERICAL_REQUIREMENT"
    TEMPORAL_CLAIM = "TEMPORAL_CLAIM"
    AUTHORITY_CLAIM = "AUTHORITY_CLAIM"
    CASE_HOLDING = "CASE_HOLDING"
    DEFINITION = "DEFINITION"
    EXCEPTION = "EXCEPTION"
    SCOPE_CLAIM = "SCOPE_CLAIM"
    FACTUAL_CLAIM = "FACTUAL_CLAIM"
    OTHER = "OTHER"

    @classmethod
    def from_str(cls, value: str) -> "ClaimType":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.OTHER


@dataclass
class SourceSpan:
    """Exact character offset mapping to the original, un-normalized answer text."""
    start_char: int
    end_char: int
    source_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceSpan":
        return cls(
            start_char=int(data["start_char"]),
            end_char=int(data["end_char"]),
            source_text=str(data["source_text"])
        )


@dataclass
class CitationRef:
    """A detected statutory or judicial citation reference with its character offsets."""
    citation_text: str
    start_char: int
    end_char: int
    citation_type: str = "STATUTORY"  # STATUTORY, JUDICIAL, REGULATORY, OTHER
    normalized_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationRef":
        return cls(
            citation_text=str(data["citation_text"]),
            start_char=int(data["start_char"]),
            end_char=int(data["end_char"]),
            citation_type=str(data.get("citation_type", "STATUTORY")),
            normalized_id=data.get("normalized_id")
        )


@dataclass
class AtomicityMeta:
    """Metadata regarding claim atomicity and propositional decomposition."""
    is_atomic: bool = True
    parent_claim_id: Optional[str] = None
    decomposition_type: Optional[str] = None  # CONJOINED_OBLIGATION, THRESHOLD_SPLIT, PROVISO_SPLIT, etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AtomicityMeta":
        return cls(
            is_atomic=bool(data.get("is_atomic", True)),
            parent_claim_id=data.get("parent_claim_id"),
            decomposition_type=data.get("decomposition_type")
        )


@dataclass
class ExtractedClaim:
    """An independently verifiable atomic proposition extracted from a generated legal answer."""
    claim_id: str
    claim_text: str
    claim_type: str
    source_span: SourceSpan
    sentence_index: int
    citation_refs: List[CitationRef] = field(default_factory=list)
    atomicity: AtomicityMeta = field(default_factory=AtomicityMeta)
    extraction_confidence: Optional[float] = None
    normalized_claim_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "source_span": self.source_span.to_dict(),
            "sentence_index": self.sentence_index,
            "citation_refs": [c.to_dict() for c in self.citation_refs],
            "atomicity": self.atomicity.to_dict(),
            "extraction_confidence": self.extraction_confidence,
            "normalized_claim_key": self.normalized_claim_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedClaim":
        ct = data.get("claim_type", "OTHER")
        if isinstance(ct, ClaimType):
            ct_str = ct.value
        else:
            ct_str = ClaimType.from_str(str(ct)).value

        return cls(
            claim_id=str(data["claim_id"]),
            claim_text=str(data["claim_text"]),
            claim_type=ct_str,
            source_span=SourceSpan.from_dict(data["source_span"]),
            sentence_index=int(data["sentence_index"]),
            citation_refs=[CitationRef.from_dict(c) for c in data.get("citation_refs", [])],
            atomicity=AtomicityMeta.from_dict(data.get("atomicity", {})),
            extraction_confidence=data.get("extraction_confidence"),
            normalized_claim_key=data.get("normalized_claim_key")
        )


@dataclass
class ClaimExtractionResult:
    """The complete result payload returned by the Claim Extractor subsystem."""
    success: bool
    answer_id: str
    input_hash: str
    output_hash: str
    claims: List[ExtractedClaim] = field(default_factory=list)
    citations: List[CitationRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.metadata.get("schema_version", "1.0.0"),
            "success": self.success,
            "answer_id": self.answer_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "claim_count": len(self.claims),
            "citation_count": len(self.citations),
            "claims": [c.to_dict() for c in self.claims],
            "citations": [c.to_dict() for c in self.citations],
            "metadata": self.metadata,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaimExtractionResult":
        return cls(
            success=bool(data.get("success", False)),
            answer_id=str(data.get("answer_id", "")),
            input_hash=str(data.get("input_hash", "")),
            output_hash=str(data.get("output_hash", "")),
            claims=[ExtractedClaim.from_dict(c) for c in data.get("claims", [])],
            citations=[CitationRef.from_dict(c) for c in data.get("citations", [])],
            metadata=dict(data.get("metadata", {})),
            errors=list(data.get("errors", [])),
        )

