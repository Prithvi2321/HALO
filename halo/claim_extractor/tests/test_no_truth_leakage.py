"""
HALO Claim Extractor: Epistemic Neutrality Tests (Gate C9 - No Truth Leakage)
============================================================================
Protocol: v1.0-FROZEN
Tests that the Claim Extractor NEVER evaluates truth, falsity, or verification status.
Ensures zero leakage of SUPPORTED, CONTRADICTED, HALLUCINATED, CORRECT, or INCORRECT.
"""

import pytest
from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.validator import SubsystemValidator
from halo.claim_extractor.config import ClaimExtractorConfig
from halo.claim_extractor.schemas import ExtractedClaim, SourceSpan
from halo.claim_extractor.exceptions import SchemaValidationError


def test_extractor_produces_no_truth_labels():
    """Verify that normal extraction produces zero truth verification fields."""
    extractor = ClaimExtractor()
    text = "Section 135 mandates CSR for companies meeting net worth of ₹500 crore."
    res = extractor.extract(text, answer_id="ANS_C9_01")

    forbidden = {"SUPPORTED", "CONTRADICTED", "HALLUCINATED", "CORRECT", "INCORRECT"}
    for claim in res.claims:
        d = claim.to_dict()
        # Verify no truth fields exist in the serialized dictionary
        assert "expected_status" not in d
        assert "verification_status" not in d
        assert "is_supported" not in d
        assert "is_hallucination" not in d

        # Ensure no field value contains forbidden verification labels
        for k, v in d.items():
            if isinstance(v, str):
                assert v.upper() not in forbidden


def test_validator_rejects_injected_truth_labels():
    """Verify that SubsystemValidator actively catches and rejects any injected truth label."""
    validator = SubsystemValidator()
    config = ClaimExtractorConfig()

    span = SourceSpan(0, 30, "Section 135 mandates CSR.")
    leaked_claim = ExtractedClaim(
        claim_id="ANS_C9_02_C01",
        claim_text="Section 135 mandates CSR.",
        claim_type="LEGAL_OBLIGATION",
        source_span=span,
        sentence_index=0,
        normalized_claim_key="SUPPORTED"  # Maliciously or accidentally injected truth label
    )

    with pytest.raises(SchemaValidationError) as excinfo:
        validator.validate_claims([leaked_claim], config)

    assert "Gate C9 Violation" in str(excinfo.value)
