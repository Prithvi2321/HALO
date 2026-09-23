"""
HALO Evidence Verifier Subsystem
================================
Protocol: v1.0-FROZEN
Production / research-grade evidence verification for AI-assisted legal research.
Determines semantic evidence relationship between authoritative legal passages
and generated atomic legal claims:
- SUPPORTED
- CONTRADICTED
- PARTIALLY_SUPPORTED
- NEUTRAL
- CONFLICTED
- UNRESOLVED
"""

from .config import EvidenceVerifierConfig
from .schemas import (
    EvidenceVerdictStatus,
    CheckStatus,
    NumericalMismatchType,
    ModalityType,
    ClaimAtomicity,
    NLILabel,
    NLIProbabilities,
    NLIPairResult,
    NumericalCheckResult,
    ModalityCheckResult,
    NegationCheckResult,
    EvidenceItem,
    AggregationSummary,
    ModelProvenance,
    EvidenceVerdict,
    EvidenceVerificationResult,
    CitationReferenceInput,
    ClaimVerificationInput,
)
from .exceptions import (
    EvidenceVerifierError,
    InvalidInputError,
    MalformedEvidenceError,
    CorpusAccessError,
    NLIInferenceError,
    DirectionViolationError,
    TruthLabelLeakageError,
    CitationNotVerifiedError,
)
from .verifier import EvidenceVerifier

__all__ = [
    "EvidenceVerifier",
    "EvidenceVerifierConfig",
    "EvidenceVerdictStatus",
    "CheckStatus",
    "NumericalMismatchType",
    "ModalityType",
    "ClaimAtomicity",
    "NLILabel",
    "NLIProbabilities",
    "NLIPairResult",
    "NumericalCheckResult",
    "ModalityCheckResult",
    "NegationCheckResult",
    "EvidenceItem",
    "AggregationSummary",
    "ModelProvenance",
    "EvidenceVerdict",
    "EvidenceVerificationResult",
    "CitationReferenceInput",
    "ClaimVerificationInput",
    "EvidenceVerifierError",
    "InvalidInputError",
    "MalformedEvidenceError",
    "CorpusAccessError",
    "NLIInferenceError",
    "DirectionViolationError",
    "TruthLabelLeakageError",
    "CitationNotVerifiedError",
]
