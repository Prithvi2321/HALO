"""
HALO Claim Extractor: Modality Preservation Tests (Gate C3)
==========================================================
Protocol: v1.0-FROZEN
Tests exact preservation of modal force (shall, must, may, cannot, is prohibited from)
and verifies that deontic legal distinctions are maintained without mutation.
"""

from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.schemas import ClaimType


def test_mandatory_modality_preservation():
    """Verify that mandatory modal verbs ('shall', 'must') are strictly preserved and classified."""
    extractor = ClaimExtractor()
    text = "The Board of Directors shall constitute a Corporate Social Responsibility Committee."
    res = extractor.extract(text, answer_id="ANS_MOD_01")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "shall constitute" in claim.claim_text
    assert claim.claim_type == ClaimType.LEGAL_OBLIGATION.value
    assert text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text


def test_prohibitive_modality_preservation():
    """Verify that prohibitive modal phrases ('shall not', 'cannot', 'is prohibited') are classified."""
    extractor = ClaimExtractor()
    text = "No company shall make any contribution to any political party directly or indirectly."
    res = extractor.extract(text, answer_id="ANS_MOD_02")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "No company shall make" in claim.claim_text
    assert claim.claim_type == ClaimType.LEGAL_PROHIBITION.value


def test_permissive_modality_preservation():
    """Verify that permissive modal verbs ('may', 'is permitted to') are preserved and classified."""
    extractor = ClaimExtractor()
    text = "A company may contribute to bona fide charitable funds with prior approval."
    res = extractor.extract(text, answer_id="ANS_MOD_03")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "may contribute" in claim.claim_text
    assert claim.claim_type == ClaimType.LEGAL_PERMISSION.value


def test_no_modal_drift_across_spans():
    """Ensure character offsets accurately capture the precise modal phrasing."""
    extractor = ClaimExtractor()
    text = (
        "Section 179 mandates board consent; "
        "directors cannot sanction loans without unanimous approval; "
        "the company may seek shareholder ratification."
    )
    res = extractor.extract(text, answer_id="ANS_MOD_04")

    assert len(res.claims) == 3
    # Check claim types reflect distinct deontic modalities
    types = [c.claim_type for c in res.claims]
    assert ClaimType.LEGAL_PROHIBITION.value in types
    assert ClaimType.LEGAL_PERMISSION.value in types

    # Check 100% span integrity
    for c in res.claims:
        assert text[c.source_span.start_char:c.source_span.end_char] == c.source_span.source_text
