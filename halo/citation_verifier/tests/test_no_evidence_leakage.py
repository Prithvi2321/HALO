"""
HALO Citation Verifier: Epistemic Neutrality Tests (Gate CV9 - No Evidence Support Leakage)
===========================================================================================
Protocol: v1.0-FROZEN
Tests that the Citation Verifier NEVER evaluates whether a citation supports or contradicts
a claim proposition. Enforces zero emission of SUPPORTED, CONTRADICTED, or HALLUCINATED.
"""

import pytest
from halo.citation_verifier.verifier import verify_citations
from halo.citation_verifier.validator import SubsystemValidator
from halo.citation_verifier.schemas import (
    CitationVerificationRecord,
    ExistenceResult,
    MetadataResult,
    ExistenceStatus,
    MetadataStatus,
    MatchConfidenceTier
)
from halo.citation_verifier.exceptions import EvidenceLeakageViolationError


def test_no_evidence_support_verdicts_emitted():
    """Verify that normal verification output contains zero evidence support labels."""
    res = verify_citations("Section 135 mandates CSR for companies meeting net worth of ₹500 crore.")

    forbidden = {"SUPPORTED", "CONTRADICTED", "HALLUCINATED", "CORRECT", "INCORRECT", "PARTIALLY_SUPPORTED"}

    for c in res.citation_results:
        d = c.to_dict()
        # Verify no evidence verification fields exist
        assert "evidence_status" not in d
        assert "is_supported" not in d
        assert "is_hallucination" not in d

        # Verify no string value equals forbidden truth verdicts
        for k, v in d.items():
            if isinstance(v, str):
                assert v.upper() not in forbidden


def test_validator_rejects_injected_truth_labels():
    """Verify that SubsystemValidator raises EvidenceLeakageViolationError on injected truth labels."""
    validator = SubsystemValidator()

    exist_res = ExistenceResult(
        status=ExistenceStatus.EXISTS.value,
        confidence_tier=MatchConfidenceTier.EXACT_MATCH.value
    )
    meta_res = MetadataResult(status=MetadataStatus.MATCH.value)

    leaked_record = CitationVerificationRecord(
        citation_id="ANS_LEAK_CIT01",
        claim_ids=["ANS_01_C01"],
        citation_text="Section 135",
        start_char=0,
        end_char=11,
        existence=exist_res,
        metadata=meta_res,
        verification_tier="EXISTENCE",
        authority_type="STATUTE",
        canonical_authority_id="ACT_COMPANIES_2013_SEC_135",
        source_corpus="D1_STATUTORY",
        explanation="SUPPORTED",  # Injected forbidden truth label
        input_hash="hash_in",
        output_hash="hash_out"
    )

    with pytest.raises(EvidenceLeakageViolationError) as excinfo:
        validator.audit_no_evidence_leakage([leaked_record])

    assert "Gate CV9 Violation" in str(excinfo.value)
