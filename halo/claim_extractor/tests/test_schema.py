"""
HALO Claim Extractor: Schema & Enum Tests (Gate C1)
==================================================
Protocol: v1.0-FROZEN
Tests schema compliance, 15-member controlled ClaimType enum, dataclass
integrity, and JSON round-trip serialization.
"""

import pytest
from halo.claim_extractor.schemas import (
    ClaimType,
    SourceSpan,
    CitationRef,
    AtomicityMeta,
    ExtractedClaim,
    ClaimExtractionResult,
)
from halo.claim_extractor.exceptions import SchemaValidationError


def test_claim_type_enum_completeness():
    """Verify all 15 controlled claim types are present."""
    expected_members = {
        "STATUTORY_PROVISION",
        "LEGAL_OBLIGATION",
        "LEGAL_PROHIBITION",
        "LEGAL_PERMISSION",
        "LEGAL_REQUIREMENT",
        "PROCEDURAL_REQUIREMENT",
        "NUMERICAL_REQUIREMENT",
        "TEMPORAL_CLAIM",
        "AUTHORITY_CLAIM",
        "CASE_HOLDING",
        "DEFINITION",
        "EXCEPTION",
        "SCOPE_CLAIM",
        "FACTUAL_CLAIM",
        "OTHER",
    }
    actual_members = {t.value for t in ClaimType}
    assert actual_members == expected_members, f"Enum mismatch: {actual_members ^ expected_members}"
    assert len(ClaimType) == 15


def test_claim_type_from_str():
    """Verify case-insensitive lookup and graceful fallback to OTHER on invalid types."""
    assert ClaimType.from_str("statutory_provision") == ClaimType.STATUTORY_PROVISION
    assert ClaimType.from_str("LEGAL_OBLIGATION") == ClaimType.LEGAL_OBLIGATION
    assert ClaimType.from_str("other") == ClaimType.OTHER
    assert ClaimType.from_str("UNSUPPORTED_RANDOM_TYPE") == ClaimType.OTHER



def test_source_span_serialization():
    """Verify SourceSpan creation and round-trip dictionary serialization."""
    span = SourceSpan(start_char=10, end_char=35, source_text="mandatory CSR expenditure")
    d = span.to_dict()
    assert d == {"start_char": 10, "end_char": 35, "source_text": "mandatory CSR expenditure"}

    reconstructed = SourceSpan.from_dict(d)
    assert reconstructed == span


def test_citation_ref_serialization():
    """Verify CitationRef creation and round-trip dictionary serialization."""
    cit = CitationRef(
        citation_text="Section 135(1) of the Companies Act, 2013",
        start_char=0,
        end_char=41,
        citation_type="STATUTORY",
        normalized_id="COMPANIES_ACT_2013_SEC_135_1"
    )
    d = cit.to_dict()
    assert d["citation_text"] == "Section 135(1) of the Companies Act, 2013"
    assert d["citation_type"] == "STATUTORY"
    assert d["normalized_id"] == "COMPANIES_ACT_2013_SEC_135_1"

    reconstructed = CitationRef.from_dict(d)
    assert reconstructed == cit


def test_atomicity_meta_serialization():
    """Verify AtomicityMeta round-trip serialization."""
    meta = AtomicityMeta(
        is_atomic=True,
        parent_claim_id="ANS_001_S01",
        decomposition_type="SEMICOLON_SPLIT"
    )
    d = meta.to_dict()
    assert d["is_atomic"] is True
    assert d["parent_claim_id"] == "ANS_001_S01"
    assert d["decomposition_type"] == "SEMICOLON_SPLIT"

    reconstructed = AtomicityMeta.from_dict(d)
    assert reconstructed == meta


def test_extracted_claim_serialization():
    """Verify ExtractedClaim full round-trip serialization."""
    span = SourceSpan(start_char=0, end_char=60, source_text="Section 135(1) mandates a CSR Committee for eligible firms.")
    cit = CitationRef(citation_text="Section 135(1)", start_char=0, end_char=14)
    meta = AtomicityMeta(is_atomic=True)

    claim = ExtractedClaim(
        claim_id="ANS_001_C001",
        claim_text="Section 135(1) mandates a CSR Committee for eligible firms.",
        claim_type=ClaimType.LEGAL_OBLIGATION.value,
        source_span=span,
        sentence_index=0,
        citation_refs=[cit],
        atomicity=meta,
        extraction_confidence=None,
        normalized_claim_key="obligation:section 135(1) mandates a csr committee"
    )

    d = claim.to_dict()
    assert d["claim_id"] == "ANS_001_C001"
    assert d["claim_type"] == "LEGAL_OBLIGATION"
    assert d["source_span"]["start_char"] == 0
    assert len(d["citation_refs"]) == 1

    reconstructed = ExtractedClaim.from_dict(d)
    assert reconstructed.claim_id == claim.claim_id
    assert reconstructed.claim_type == claim.claim_type
    assert reconstructed.source_span == claim.source_span
    assert reconstructed.citation_refs == claim.citation_refs


def test_claim_extraction_result_roundtrip():
    """Verify ClaimExtractionResult full round-trip serialization."""
    span = SourceSpan(start_char=0, end_char=45, source_text="Section 135(1) applies to qualifying companies.")
    claim = ExtractedClaim(
        claim_id="ANS_TEST_C001",
        claim_text="Section 135(1) applies to qualifying companies.",
        claim_type=ClaimType.SCOPE_CLAIM.value,
        source_span=span,
        sentence_index=0
    )

    res = ClaimExtractionResult(
        success=True,
        answer_id="ANS_TEST",
        input_hash="abc123hash",
        output_hash="def456hash",
        claims=[claim],
        citations=[],
        metadata={"run_id": "RUN_12345", "model": "qwen3.8-27b", "timestamp_utc": "2026-09-17T12:00:00Z"},
        errors=[]
    )

    d = res.to_dict()
    assert d["success"] is True
    assert d["claim_count"] == 1
    assert len(d["claims"]) == 1

    reconstructed = ClaimExtractionResult.from_dict(d)
    assert reconstructed.success == res.success
    assert reconstructed.answer_id == res.answer_id
    assert reconstructed.input_hash == res.input_hash
    assert reconstructed.output_hash == res.output_hash
    assert len(reconstructed.claims) == 1
    assert reconstructed.claims[0].claim_id == claim.claim_id

