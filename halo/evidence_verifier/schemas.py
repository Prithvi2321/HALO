"""
HALO Evidence Verifier: Data Schemas & Controlled Enums
======================================================
Protocol: v1.0-FROZEN
Defines immutable, versioned, auditable data contracts for legal evidence verification.
Answers strictly: "Does the authoritative legal passage provide sufficient semantic evidence
for the generated atomic claim?"
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import hashlib


class EvidenceVerdictStatus(str, Enum):
    """Primary evidence verification verdict status."""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NEUTRAL = "NEUTRAL"
    CONFLICTED = "CONFLICTED"
    UNRESOLVED = "UNRESOLVED"

    @classmethod
    def from_str(cls, value: str) -> "EvidenceVerdictStatus":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.UNRESOLVED


class CheckStatus(str, Enum):
    """Evaluation status for symbolic/rule-grounded checks."""
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"

    @classmethod
    def from_str(cls, value: str) -> "CheckStatus":
        try:
            return cls(value.strip().upper())
        except (ValueError, AttributeError):
            return cls.NOT_APPLICABLE


class NumericalMismatchType(str, Enum):
    """Categorization of detected numerical discrepancies."""
    AMOUNT_CHANGE = "AMOUNT_CHANGE"
    PERCENTAGE_CHANGE = "PERCENTAGE_CHANGE"
    COUNT_CHANGE = "COUNT_CHANGE"
    DURATION_CHANGE = "DURATION_CHANGE"
    DATE_CHANGE = "DATE_CHANGE"
    THRESHOLD_CHANGE = "THRESHOLD_CHANGE"
    SECTION_NUMBER_CHANGE = "SECTION_NUMBER_CHANGE"
    ORDINAL_CHANGE = "ORDINAL_CHANGE"
    NONE = "NONE"


class ModalityType(str, Enum):
    """Categorization of legal deontic modality."""
    MANDATORY = "MANDATORY"
    PROHIBITED = "PROHIBITED"
    PERMITTED = "PERMITTED"
    DISCRETIONARY = "DISCRETIONARY"
    OPTIONAL = "OPTIONAL"
    CAPABILITY = "CAPABILITY"
    CONDITIONAL = "CONDITIONAL"
    NONE = "NONE"


class ClaimAtomicity(str, Enum):
    """Atomicity status of evaluated claim."""
    ATOMIC = "ATOMIC"
    COMPOUND = "COMPOUND"
    UNKNOWN = "UNKNOWN"


class NLILabel(str, Enum):
    """3-way cross-encoder NLI output labels."""
    CONTRADICTION = "contradiction"
    ENTAILMENT = "entailment"
    NEUTRAL = "neutral"


@dataclass
class NLIProbabilities:
    """
    Normalized probability distribution across NLI classes.
    Note: These are normalized model probability scores, NOT proof of legal truth.
    """
    contradiction: float
    entailment: float
    neutral: float

    @property
    def contradiction_probability(self) -> float:
        return self.contradiction

    @property
    def entailment_probability(self) -> float:
        return self.entailment

    @property
    def neutral_probability(self) -> float:
        return self.neutral

    def to_dict(self) -> Dict[str, float]:
        return {
            "contradiction": round(self.contradiction, 6),
            "entailment": round(self.entailment, 6),
            "neutral": round(self.neutral, 6),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NLIProbabilities":
        return cls(
            contradiction=float(d.get("contradiction", 0.0)),
            entailment=float(d.get("entailment", 0.0)),
            neutral=float(d.get("neutral", 0.0)),
        )


@dataclass
class NLIPairResult:
    """Result of cross-encoder inference on a (Premise, Hypothesis) pair."""
    claim_id: str
    passage_id: str
    premise_text: str
    hypothesis_text: str
    probabilities: NLIProbabilities
    predicted_label: str
    model_name: str
    model_version: str
    inference_timestamp: str
    input_hash: str
    chunks_evaluated: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "passage_id": self.passage_id,
            "premise_text": self.premise_text,
            "hypothesis_text": self.hypothesis_text,
            "probabilities": self.probabilities.to_dict(),
            "predicted_label": self.predicted_label,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": self.inference_timestamp,
            "input_hash": self.input_hash,
            "chunks_evaluated": self.chunks_evaluated,
        }


@dataclass
class NumericalCheckResult:
    """Result of deterministic numerical consistency audit."""
    status: str = CheckStatus.NOT_APPLICABLE.value
    mismatch_type: str = NumericalMismatchType.NONE.value
    claim_values: List[str] = field(default_factory=list)
    evidence_values: List[str] = field(default_factory=list)
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NumericalCheckResult":
        return cls(
            status=d.get("status", CheckStatus.NOT_APPLICABLE.value),
            mismatch_type=d.get("mismatch_type", NumericalMismatchType.NONE.value),
            claim_values=list(d.get("claim_values", [])),
            evidence_values=list(d.get("evidence_values", [])),
            details=str(d.get("details", "")),
        )


@dataclass
class ModalityCheckResult:
    """Result of deterministic deontic modality audit."""
    status: str = CheckStatus.NOT_APPLICABLE.value
    claim_modality: str = ModalityType.NONE.value
    evidence_modality: str = ModalityType.NONE.value
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModalityCheckResult":
        return cls(
            status=d.get("status", CheckStatus.NOT_APPLICABLE.value),
            claim_modality=d.get("claim_modality", ModalityType.NONE.value),
            evidence_modality=d.get("evidence_modality", ModalityType.NONE.value),
            details=str(d.get("details", "")),
        )


@dataclass
class NegationCheckResult:
    """Result of deterministic polarity / negation audit."""
    status: str = CheckStatus.NOT_APPLICABLE.value
    claim_polarity: str = "AFFIRMATIVE"
    evidence_polarity: str = "AFFIRMATIVE"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NegationCheckResult":
        return cls(
            status=d.get("status", CheckStatus.NOT_APPLICABLE.value),
            claim_polarity=d.get("claim_polarity", "AFFIRMATIVE"),
            evidence_polarity=d.get("evidence_polarity", "AFFIRMATIVE"),
            details=str(d.get("details", "")),
        )


@dataclass
class EvidenceItem:
    """Individual candidate evidence passage evaluation."""
    passage_id: str
    source: str
    dataset: str
    authority_id: Optional[str]
    section_id: Optional[str]
    text: str
    text_hash: str
    nli: NLIProbabilities
    numerical_check: NumericalCheckResult
    modality_check: ModalityCheckResult
    negation_check: NegationCheckResult
    local_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "source": self.source,
            "dataset": self.dataset,
            "authority_id": self.authority_id,
            "section_id": self.section_id,
            "text": self.text,
            "text_hash": self.text_hash,
            "nli": self.nli.to_dict(),
            "numerical_check": self.numerical_check.to_dict(),
            "modality_check": self.modality_check.to_dict(),
            "negation_check": self.negation_check.to_dict(),
            "local_status": self.local_status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceItem":
        return cls(
            passage_id=str(d.get("passage_id", "")),
            source=str(d.get("source", "")),
            dataset=str(d.get("dataset", "")),
            authority_id=d.get("authority_id"),
            section_id=d.get("section_id"),
            text=str(d.get("text", "")),
            text_hash=str(d.get("text_hash", "")),
            nli=NLIProbabilities.from_dict(d.get("nli", {})),
            numerical_check=NumericalCheckResult.from_dict(d.get("numerical_check", {})),
            modality_check=ModalityCheckResult.from_dict(d.get("modality_check", {})),
            negation_check=NegationCheckResult.from_dict(d.get("negation_check", {})),
            local_status=str(d.get("local_status", EvidenceVerdictStatus.UNRESOLVED.value)),
        )


@dataclass
class AggregationSummary:
    """Multi-evidence aggregation breakdown for a claim."""
    support_count: int = 0
    contradiction_count: int = 0
    neutral_count: int = 0
    unresolved_count: int = 0
    conflict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AggregationSummary":
        return cls(
            support_count=int(d.get("support_count", 0)),
            contradiction_count=int(d.get("contradiction_count", 0)),
            neutral_count=int(d.get("neutral_count", 0)),
            unresolved_count=int(d.get("unresolved_count", 0)),
            conflict=bool(d.get("conflict", False)),
        )


@dataclass
class ModelProvenance:
    """Detailed model and environment provenance metadata."""
    name: str
    revision: Optional[str] = None
    model_hash: Optional[str] = None
    tokenizer_hash: Optional[str] = None
    torch_version: Optional[str] = None
    transformers_version: Optional[str] = None
    device: str = "cpu"
    dtype: str = "float32"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelProvenance":
        return cls(
            name=str(d.get("name", "")),
            revision=d.get("revision"),
            model_hash=d.get("model_hash"),
            tokenizer_hash=d.get("tokenizer_hash"),
            torch_version=d.get("torch_version"),
            transformers_version=d.get("transformers_version"),
            device=str(d.get("device", "cpu")),
            dtype=str(d.get("dtype", "float32")),
        )


@dataclass
class CitationReferenceInput:
    """Input citation reference from Citation Verifier upstream."""
    citation_id: str
    passage_id: Optional[str] = None
    verification_status: str = "UNRESOLVED"  # EXISTS, NOT_FOUND, UNRESOLVED, etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CitationReferenceInput":
        return cls(
            citation_id=str(d.get("citation_id", "")),
            passage_id=d.get("passage_id"),
            verification_status=str(d.get("verification_status", "UNRESOLVED")),
        )


@dataclass
class ClaimVerificationInput:
    """Input contract for claim evidence verification."""
    answer_id: str
    claim_id: str
    claim_text: str
    claim_atomicity: str = ClaimAtomicity.ATOMIC.value
    citation_refs: List[CitationReferenceInput] = field(default_factory=list)
    subclaims: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_atomicity": self.claim_atomicity,
            "citation_refs": [ref.to_dict() for ref in self.citation_refs],
            "subclaims": self.subclaims,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClaimVerificationInput":
        refs = [CitationReferenceInput.from_dict(r) for r in d.get("citation_refs", [])]
        return cls(
            answer_id=str(d.get("answer_id", "")),
            claim_id=str(d.get("claim_id", "")),
            claim_text=str(d.get("claim_text", "")),
            claim_atomicity=str(d.get("claim_atomicity", ClaimAtomicity.ATOMIC.value)),
            citation_refs=refs,
            subclaims=list(d.get("subclaims", [])),
        )


@dataclass
class EvidenceVerdict:
    """Complete, auditable evidence verdict for a single atomic legal claim."""
    claim_id: str
    claim_text: str
    status: str
    evidence_items: List[EvidenceItem]
    best_evidence_id: Optional[str]
    best_evidence: Optional[Dict[str, Any]]
    nli: Optional[NLIProbabilities]
    numerical_check: NumericalCheckResult
    modality_check: ModalityCheckResult
    negation_check: NegationCheckResult
    aggregation: AggregationSummary
    claim_atomicity: str
    decision_reason: str
    model: ModelProvenance
    config_hash: str
    input_hash: str
    output_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "status": self.status,
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "best_evidence_id": self.best_evidence_id,
            "best_evidence": self.best_evidence,
            "nli": self.nli.to_dict() if self.nli else None,
            "numerical_check": self.numerical_check.to_dict(),
            "modality_check": self.modality_check.to_dict(),
            "negation_check": self.negation_check.to_dict(),
            "aggregation": self.aggregation.to_dict(),
            "claim_atomicity": self.claim_atomicity,
            "decision_reason": self.decision_reason,
            "model": self.model.to_dict(),
            "config_hash": self.config_hash,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
        }

    def compute_output_hash(self) -> str:
        data = self.to_dict()
        data["output_hash"] = ""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceVerdict":
        raw_items = d.get("evidence_items", [])
        evidence_items = [EvidenceItem.from_dict(item) for item in raw_items]
        raw_nli = d.get("nli")
        nli = NLIProbabilities.from_dict(raw_nli) if raw_nli else None
        return cls(
            claim_id=str(d["claim_id"]),
            claim_text=str(d["claim_text"]),
            status=str(d.get("status", EvidenceVerdictStatus.UNRESOLVED.value)),
            evidence_items=evidence_items,
            best_evidence_id=d.get("best_evidence_id"),
            best_evidence=d.get("best_evidence"),
            nli=nli,
            numerical_check=NumericalCheckResult.from_dict(d.get("numerical_check", {})),
            modality_check=ModalityCheckResult.from_dict(d.get("modality_check", {})),
            negation_check=NegationCheckResult.from_dict(d.get("negation_check", {})),
            aggregation=AggregationSummary.from_dict(d.get("aggregation", {})),
            claim_atomicity=str(d.get("claim_atomicity", ClaimAtomicity.ATOMIC.value)),
            decision_reason=str(d.get("decision_reason", "")),
            model=ModelProvenance.from_dict(d.get("model", {})),
            config_hash=str(d.get("config_hash", "")),
            input_hash=str(d.get("input_hash", "")),
            output_hash=str(d.get("output_hash", "")),
        )


@dataclass
class EvidenceVerificationResult:
    """Subsystem output payload representing evidence verification of an answer payload."""
    schema_version: str
    success: bool
    answer_id: str
    input_hash: str
    output_hash: str
    total_claims: int
    verdicts: List[EvidenceVerdict]
    metrics: Dict[str, Any]
    errors: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "success": self.success,
            "answer_id": self.answer_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "total_claims": self.total_claims,
            "verdicts": [v.to_dict() for v in self.verdicts],
            "metrics": self.metrics,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    def compute_output_hash(self) -> str:
        data = self.to_dict()
        data["output_hash"] = ""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceVerificationResult":
        return cls(
            schema_version=str(d.get("schema_version", "1.0.0")),
            success=bool(d.get("success", False)),
            answer_id=str(d.get("answer_id", "")),
            input_hash=str(d.get("input_hash", "")),
            output_hash=str(d.get("output_hash", "")),
            total_claims=int(d.get("total_claims", 0)),
            verdicts=[EvidenceVerdict.from_dict(v) for v in d.get("verdicts", [])],
            metrics=dict(d.get("metrics", {})),
            errors=list(d.get("errors", [])),
            metadata=dict(d.get("metadata", {})),
        )
