"""
HALO Claim Extractor: Numerical Integrity Tests (Gate C4)
=========================================================
Protocol: v1.0-FROZEN
Tests exact preservation of monetary thresholds (₹500 crore), percentages (2%),
ratios, days (21 clear days), and director counts without rounding or token loss.
"""

from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.schemas import ClaimType


def test_monetary_and_percentage_thresholds():
    """Verify that rupee thresholds and percentage requirements are preserved byte-for-byte."""
    extractor = ClaimExtractor()
    text = (
        "Every company having net worth of ₹500 crore or more, or turnover of ₹1,000 crore or more, "
        "shall spend at least 2% of average net profits on CSR."
    )
    res = extractor.extract(text, answer_id="ANS_NUM_01")

    assert len(res.claims) >= 1
    claim = res.claims[0]
    assert "₹500 crore" in claim.claim_text
    assert "₹1,000 crore" in claim.claim_text
    assert "2%" in claim.claim_text
    assert claim.claim_type == ClaimType.NUMERICAL_REQUIREMENT.value

    # Byte-level span verification
    assert text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text


def test_time_duration_and_notice_thresholds():
    """Verify preservation of explicit day/period thresholds."""
    extractor = ClaimExtractor()
    text = "An annual general meeting must be called by giving not less than 21 clear days notice in writing."
    res = extractor.extract(text, answer_id="ANS_NUM_02")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "21 clear days" in claim.claim_text
    assert claim.claim_type == ClaimType.NUMERICAL_REQUIREMENT.value
    assert text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text


def test_director_count_thresholds():
    """Verify director quota thresholds are preserved and classified as numerical requirements."""
    extractor = ClaimExtractor()
    text = "Every public company shall have a minimum of 3 directors and a maximum of 15 directors."
    res = extractor.extract(text, answer_id="ANS_NUM_03")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "3 directors" in claim.claim_text
    assert "15 directors" in claim.claim_text
    assert claim.claim_type == ClaimType.NUMERICAL_REQUIREMENT.value
