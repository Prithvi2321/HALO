"""
HALO Claim Extractor: Custom Exceptions
=======================================
Protocol: v1.0-FROZEN
Defines structured, machine-readable exceptions for the Claim Extraction subsystem.
"""

from typing import Dict, Any, Optional


class ClaimExtractorError(Exception):
    """Base exception for all Claim Extractor errors."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class EmptyAnswerError(ClaimExtractorError):
    """Raised when input text is empty, whitespace-only, or non-string."""
    def __init__(self, message: str = "Input answer text is empty or contains only whitespace.", details: Optional[Dict[str, Any]] = None):
        super().__init__("EMPTY_ANSWER", message, details)


class InvalidInputError(ClaimExtractorError):
    """Raised when input answer is not a valid string or fails type validation."""
    def __init__(self, message: str = "Invalid input provided to claim extractor.", details: Optional[Dict[str, Any]] = None):
        super().__init__("INVALID_INPUT", message, details)


class SpanAlignmentError(ClaimExtractorError):
    """Raised when an extracted claim's character span does not match the source text."""
    def __init__(self, message: str = "Claim span does not match source answer.", details: Optional[Dict[str, Any]] = None):
        super().__init__("SPAN_ALIGNMENT_ERROR", message, details)


class SchemaValidationError(ClaimExtractorError):
    """Raised when an extracted claim fails schema or enum validation."""
    def __init__(self, message: str = "Claim output failed schema validation.", details: Optional[Dict[str, Any]] = None):
        super().__init__("SCHEMA_VALIDATION_ERROR", message, details)


class ClaimDecompositionError(ClaimExtractorError):
    """Raised when compound claim decomposition fails catastrophically."""
    def __init__(self, message: str = "Failed to decompose compound sentence into atomic propositions.", details: Optional[Dict[str, Any]] = None):
        super().__init__("CLAIM_DECOMPOSITION_ERROR", message, details)


class UnsupportedFormatError(ClaimExtractorError):
    """Raised when input data format or payload structure is unsupported."""
    def __init__(self, message: str = "Unsupported format received by claim extractor.", details: Optional[Dict[str, Any]] = None):
        super().__init__("UNSUPPORTED_FORMAT", message, details)


class PayloadLimitExceededError(ClaimExtractorError):
    """Raised when input length, claim count, or citation count exceeds configured limits."""
    def __init__(self, message: str = "Input payload exceeds configured safety limits.", details: Optional[Dict[str, Any]] = None):
        super().__init__("PAYLOAD_LIMIT_EXCEEDED", message, details)
