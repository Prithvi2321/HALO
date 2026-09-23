"""
HALO Claim Extractor Subsystem
==============================
Protocol: v1.0-FROZEN
Decomposes complex, generated legal text into atomic, independently verifiable factual
and legal propositions with exact character spans and controlled classification.

Never determines whether claims are true or false (Gate C9).
"""

from halo.claim_extractor.schemas import (
    ClaimType,
    SourceSpan,
    CitationRef,
    AtomicityMeta,
    ExtractedClaim,
    ClaimExtractionResult,
)
from halo.claim_extractor.config import ClaimExtractorConfig
from halo.claim_extractor.extractor import ClaimExtractor, extract_claims
from halo.claim_extractor.segmenter import LegalSentenceSegmenter, SentenceSegment
from halo.claim_extractor.citation_detector import LegalCitationDetector
from halo.claim_extractor.claim_detector import ClaimCandidateDetector
from halo.claim_extractor.claim_decomposer import ClaimDecomposer, DecomposedProposition
from halo.claim_extractor.claim_classifier import LegalClaimClassifier
from halo.claim_extractor.span_aligner import SpanAligner
from halo.claim_extractor.normalizer import ClaimNormalizer
from halo.claim_extractor.validator import SubsystemValidator
from halo.claim_extractor.exceptions import (
    ClaimExtractorError,
    EmptyAnswerError,
    InvalidInputError,
    SpanAlignmentError,
    SchemaValidationError,
    ClaimDecompositionError,
    UnsupportedFormatError,
    PayloadLimitExceededError,
)

__all__ = [
    "ClaimExtractor",
    "extract_claims",
    "ClaimExtractorConfig",
    "ClaimExtractionResult",
    "ExtractedClaim",
    "ClaimType",
    "CitationRef",
    "SourceSpan",
    "AtomicityMeta",
    "LegalSentenceSegmenter",
    "SentenceSegment",
    "LegalCitationDetector",
    "ClaimCandidateDetector",
    "ClaimDecomposer",
    "DecomposedProposition",
    "LegalClaimClassifier",
    "SpanAligner",
    "ClaimNormalizer",
    "SubsystemValidator",
    "ClaimExtractorError",
    "EmptyAnswerError",
    "InvalidInputError",
    "SpanAlignmentError",
    "SchemaValidationError",
    "ClaimDecompositionError",
    "UnsupportedFormatError",
    "PayloadLimitExceededError",
]
