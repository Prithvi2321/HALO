"""
HALO Citation Verifier: Data Schemas & Controlled Enums
=======================================================
Protocol: v1.0-FROZEN
Defines versioned, auditable data contracts for legal citation verification.
Strictly separates citation existence and metadata verification from evidence support.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


class ExistenceStatus(str, Enum):
    """Tier 1: Whether the cited legal authority exists in the authoritative legal corpus."""
    EXISTS = "EXISTS"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    MALFORMED = "MALFORMED"
    UNRESOLVED = "UNRESOLVED"

    @classmethod
    def from_str(cls, value: str) -> "ExistenceStatus":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.UNRESOLVED


class MetadataStatus(str, Enum):
    """Tier 2: Whether citation metadata aligns with the authoritative canonical record."""
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    UNRESOLVED = "UNRESOLVED"

    @classmethod
    def from_str(cls, value: str) -> "MetadataStatus":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.UNRESOLVED


class AuthorityType(str, Enum):
    """Classification of the cited legal source."""
    STATUTE = "STATUTE"
    CASE = "CASE"
    JUDGMENT = "JUDGMENT"
    CONSTITUTION = "CONSTITUTION"
    REGULATION = "REGULATION"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, value: str) -> "AuthorityType":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.UNKNOWN


class MatchConfidenceTier(str, Enum):
    """Confidence tier of corpus match. FUZZY_CANDIDATE is strictly barred from emitting EXISTS."""
    EXACT_MATCH = "EXACT_MATCH"
    NORMALIZED_MATCH = "NORMALIZED_MATCH"
    FUZZY_CANDIDATE = "FUZZY_CANDIDATE"
    NO_MATCH = "NO_MATCH"


@dataclass
class AuthorityHierarchy:
    """
    Separation of Authority Existence from Passage Existence.
    Authority -> Section -> Subsection -> Passage Resolution.
    """
    authority_exists: bool = False
    section_exists: bool = False
    subsection_exists: bool = False
    matched_passage_ids: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorityHierarchy":
        return cls(
            authority_exists=bool(data.get("authority_exists", False)),
            section_exists=bool(data.get("section_exists", False)),
            subsection_exists=bool(data.get("subsection_exists", False)),
            matched_passage_ids=list(data.get("matched_passage_ids", [])),
            details=dict(data.get("details", {}))
        )


@dataclass
class ParsedCitation:
    """Structured breakdown of extracted citation components."""
    citation_text: str
    authority_type: str = AuthorityType.UNKNOWN.value
    act_name: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    clause: Optional[str] = None
    case_title: Optional[str] = None
    court: Optional[str] = None
    year: Optional[str] = None
    reporter: Optional[str] = None
    volume: Optional[str] = None
    page: Optional[str] = None
    paragraph: Optional[str] = None
    asserted_heading: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedCitation":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MetadataFieldDiff:
    """Detailed comparison of an individual citation metadata field against canonical record."""
    field_name: str
    cited_value: Optional[str]
    canonical_value: Optional[str]
    matches: bool
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetadataFieldDiff":
        return cls(
            field_name=str(data["field_name"]),
            cited_value=data.get("cited_value"),
            canonical_value=data.get("canonical_value"),
            matches=bool(data.get("matches", False)),
            notes=data.get("notes")
        )


@dataclass
class ExistenceResult:
    """Results of Tier 1: Existence verification against authoritative corpus."""
    status: str
    confidence_tier: str
    canonical_authority_id: Optional[str] = None
    matched_passage_ids: List[str] = field(default_factory=list)
    candidate_authority_ids: List[str] = field(default_factory=list)
    hierarchy: AuthorityHierarchy = field(default_factory=AuthorityHierarchy)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "confidence_tier": self.confidence_tier,
            "canonical_authority_id": self.canonical_authority_id,
            "matched_passage_ids": self.matched_passage_ids,
            "candidate_authority_ids": self.candidate_authority_ids,
            "hierarchy": self.hierarchy.to_dict(),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExistenceResult":
        return cls(
            status=str(data.get("status", ExistenceStatus.UNRESOLVED.value)),
            confidence_tier=str(data.get("confidence_tier", MatchConfidenceTier.NO_MATCH.value)),
            canonical_authority_id=data.get("canonical_authority_id"),
            matched_passage_ids=list(data.get("matched_passage_ids", [])),
            candidate_authority_ids=list(data.get("candidate_authority_ids", [])),
            hierarchy=AuthorityHierarchy.from_dict(data.get("hierarchy", {})),
            explanation=str(data.get("explanation", ""))
        )


@dataclass
class MetadataResult:
    """Results of Tier 2: Metadata verification against authoritative corpus."""
    status: str
    fields: Dict[str, MetadataFieldDiff] = field(default_factory=dict)
    mismatches: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "mismatches": self.mismatches,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetadataResult":
        raw_fields = data.get("fields", {})
        parsed_fields = {k: MetadataFieldDiff.from_dict(v) for k, v in raw_fields.items()}
        return cls(
            status=str(data.get("status", MetadataStatus.UNRESOLVED.value)),
            fields=parsed_fields,
            mismatches=list(data.get("mismatches", [])),
            explanation=str(data.get("explanation", ""))
        )


@dataclass
class CitationVerificationRecord:
    """Complete verification record for a single citation reference occurrence."""
    citation_id: str
    claim_ids: List[str]
    citation_text: str
    start_char: int
    end_char: int
    existence: ExistenceResult
    metadata: MetadataResult
    verification_tier: str
    authority_type: str
    canonical_authority_id: Optional[str]
    source_corpus: str
    explanation: str
    input_hash: str
    output_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "claim_ids": self.claim_ids,
            "citation_text": self.citation_text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "existence": self.existence.to_dict(),
            "metadata": self.metadata.to_dict(),
            "verification_tier": self.verification_tier,
            "authority_type": self.authority_type,
            "canonical_authority_id": self.canonical_authority_id,
            "source_corpus": self.source_corpus,
            "explanation": self.explanation,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationVerificationRecord":
        return cls(
            citation_id=str(data["citation_id"]),
            claim_ids=list(data.get("claim_ids", [])),
            citation_text=str(data["citation_text"]),
            start_char=int(data["start_char"]),
            end_char=int(data["end_char"]),
            existence=ExistenceResult.from_dict(data["existence"]),
            metadata=MetadataResult.from_dict(data["metadata"]),
            verification_tier=str(data.get("verification_tier", "EXISTENCE")),
            authority_type=str(data.get("authority_type", AuthorityType.UNKNOWN.value)),
            canonical_authority_id=data.get("canonical_authority_id"),
            source_corpus=str(data.get("source_corpus", "UNKNOWN")),
            explanation=str(data.get("explanation", "")),
            input_hash=str(data.get("input_hash", "")),
            output_hash=str(data.get("output_hash", "")),
        )


@dataclass
class CitationVerificationResult:
    """Top-level versioned payload returned by the Citation Verifier subsystem."""
    success: bool
    answer_id: str
    input_hash: str
    output_hash: str
    total_citations: int
    citation_results: List[CitationVerificationRecord] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.metadata.get("schema_version", "1.0.0"),
            "success": self.success,
            "answer_id": self.answer_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "total_citations": self.total_citations,
            "citation_results": [c.to_dict() for c in self.citation_results],
            "metrics": self.metrics,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationVerificationResult":
        return cls(
            success=bool(data.get("success", False)),
            answer_id=str(data.get("answer_id", "")),
            input_hash=str(data.get("input_hash", "")),
            output_hash=str(data.get("output_hash", "")),
            total_citations=int(data.get("total_citations", len(data.get("citation_results", [])))),
            citation_results=[CitationVerificationRecord.from_dict(c) for c in data.get("citation_results", [])],
            metrics=dict(data.get("metrics", {})),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {}))
        )
