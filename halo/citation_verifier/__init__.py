"""
HALO Citation Verifier Subsystem
================================
Protocol: v1.0-FROZEN
Exports core verification interfaces, configs, and schema models.
"""

from halo.citation_verifier.verifier import CitationVerifier, verify_citations
from halo.citation_verifier.config import CitationVerifierConfig
from halo.citation_verifier.corpus_index import CorpusIndex
from halo.citation_verifier.parser import CitationParser
from halo.citation_verifier.normalizer import CitationNormalizer
from halo.citation_verifier.schemas import (
    ExistenceStatus,
    MetadataStatus,
    AuthorityType,
    MatchConfidenceTier,
    AuthorityHierarchy,
    ParsedCitation,
    MetadataFieldDiff,
    ExistenceResult,
    MetadataResult,
    CitationVerificationRecord,
    CitationVerificationResult,
)
from halo.citation_verifier.exceptions import (
    CitationVerifierError,
    InvalidInputError,
    MalformedCitationError,
    CorpusLookupError,
    AmbiguousCitationError,
    AuthorityNotFoundError,
    MetadataMismatchError,
    EvidenceLeakageViolationError,
)

__all__ = [
    "CitationVerifier",
    "verify_citations",
    "CitationVerifierConfig",
    "CorpusIndex",
    "CitationParser",
    "CitationNormalizer",
    "ExistenceStatus",
    "MetadataStatus",
    "AuthorityType",
    "MatchConfidenceTier",
    "AuthorityHierarchy",
    "ParsedCitation",
    "MetadataFieldDiff",
    "ExistenceResult",
    "MetadataResult",
    "CitationVerificationRecord",
    "CitationVerificationResult",
    "CitationVerifierError",
    "InvalidInputError",
    "MalformedCitationError",
    "CorpusLookupError",
    "AmbiguousCitationError",
    "AuthorityNotFoundError",
    "MetadataMismatchError",
    "EvidenceLeakageViolationError",
]
