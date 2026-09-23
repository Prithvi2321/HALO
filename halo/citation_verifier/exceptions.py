"""
HALO Citation Verifier: Error Hierarchy & Machine-Readable Codes
================================================================
Protocol: v1.0-FROZEN
Defines structured exception types for citation parsing, corpus lookup,
ambiguity handling, and Gate CV9 enforcement.
"""

from typing import Optional, Dict, Any


class CitationVerifierError(Exception):
    """Base exception for all Citation Verifier subsystem errors."""
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
            "details": self.details
        }


class InvalidInputError(CitationVerifierError):
    """Raised when input answer or claims payload is invalid."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="INVALID_INPUT", details=details)


class MalformedCitationError(CitationVerifierError):
    """Raised when citation text violates legal syntax or contains corrupt characters."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="MALFORMED_CITATION", details=details)


class CorpusLookupError(CitationVerifierError):
    """Raised when corpus index lookup encounters an unrecoverable system failure."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CORPUS_LOOKUP_ERROR", details=details)


class AmbiguousCitationError(CitationVerifierError):
    """Raised when a citation matches multiple conflicting authorities."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="AMBIGUOUS_CITATION", details=details)


class AuthorityNotFoundError(CitationVerifierError):
    """Raised when an authority is affirmatively missing from the corpus."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHORITY_NOT_FOUND", details=details)


class MetadataMismatchError(CitationVerifierError):
    """Raised when citation metadata conflicts with the canonical record."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="METADATA_MISMATCH", details=details)


class EvidenceLeakageViolationError(CitationVerifierError):
    """Raised when the verifier attempts to emit truth/evidence-support verdicts (Gate CV9 violation)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="EVIDENCE_LEAKAGE_VIOLATION", details=details)
