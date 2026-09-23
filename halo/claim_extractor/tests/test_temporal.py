"""
HALO Claim Extractor: Temporal Preservation Tests (Gate C5)
==========================================================
Protocol: v1.0-FROZEN
Tests exact preservation of temporal markers (w.e.f., dates, amendments, repeals)
and verifies that historical vs prevailing statutory assertions are captured without drift.
"""

from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.schemas import ClaimType


def test_wef_and_enactment_dates():
    """Verify that 'w.e.f.' and statutory commencement dates are strictly preserved."""
    extractor = ClaimExtractor()
    text = "Section 135 of the Companies Act, 2013 came into force w.e.f. 01.04.2014 across India."
    res = extractor.extract(text, answer_id="ANS_TEMP_01")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "w.e.f. 01.04.2014" in claim.claim_text
    assert claim.claim_type == ClaimType.TEMPORAL_CLAIM.value
    assert text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text


def test_repeal_and_supersession_claims():
    """Verify that assertions regarding repealed or amended statutes are preserved."""
    extractor = ClaimExtractor()
    text = "Section 77 of the Companies Act, 1956 was repealed by the 2013 Act."
    res = extractor.extract(text, answer_id="ANS_TEMP_02")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "repealed by the 2013 Act" in claim.claim_text
    assert claim.claim_type == ClaimType.TEMPORAL_CLAIM.value
    assert text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text


def test_temporal_relative_clauses():
    """Verify preservation of relative temporal phrases such as 'prior to repeal'."""
    extractor = ClaimExtractor()
    text = "Any transaction registered prior to the 2020 amendment remains valid under prevailing law."
    res = extractor.extract(text, answer_id="ANS_TEMP_03")

    assert len(res.claims) == 1
    claim = res.claims[0]
    assert "prior to the 2020 amendment" in claim.claim_text
    assert claim.claim_type == ClaimType.TEMPORAL_CLAIM.value
