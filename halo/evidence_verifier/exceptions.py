"""
HALO Evidence Verifier: Error Hierarchy & Machine-Readable Codes
================================================================
Protocol: v1.0-FROZEN
Defines structured exception types for input validation, corpus access,
NLI inference, gate violations, and truth-label leakage prevention.
"""

from typing import Optional, Dict, Any


class EvidenceVerifierError(Exception):
    """Base exception for all Evidence Verifier subsystem errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class InvalidInputError(EvidenceVerifierError):
    """Raised when input claim or answer payload violates format, length, or sanitization rules."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="INVALID_INPUT", details=details)


class MalformedEvidenceError(EvidenceVerifierError):
    """Raised when an evidence passage record has missing, empty, or corrupt content."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="MALFORMED_EVIDENCE", details=details)


class CorpusAccessError(EvidenceVerifierError):
    """Raised when canonical passage lookup fails due to I/O or index corruption."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CORPUS_ACCESS_ERROR", details=details)


class NLIInferenceError(EvidenceVerifierError):
    """Raised when NLI model initialization, label mapping, or inference fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="NLI_INFERENCE_ERROR", details=details)


class DirectionViolationError(EvidenceVerifierError):
    """Raised when the NLI pair direction violates (Premise=Evidence, Hypothesis=Claim)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="DIRECTION_VIOLATION", details=details)


class TruthLabelLeakageError(EvidenceVerifierError):
    """Raised when forbidden ground-truth labels or test split data are detected during inference."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="TRUTH_LABEL_LEAKAGE", details=details)


class CitationNotVerifiedError(EvidenceVerifierError):
    """Raised when evidence verification is requested on a citation not marked as verified/exists."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CITATION_NOT_VERIFIED", details=details)
