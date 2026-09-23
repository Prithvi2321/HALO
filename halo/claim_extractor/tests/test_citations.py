"""
HALO Claim Extractor: Citation Detection & Association Tests (Gate C6)
=====================================================================
Protocol: v1.0-FROZEN
Tests statutory and judicial citation detection, normalized ID computation,
and proximity association with extracted atomic propositions.
"""

from halo.claim_extractor.citation_detector import LegalCitationDetector
from halo.claim_extractor.extractor import ClaimExtractor


def test_statutory_citation_detection():
    """Verify detection of complex statutory citations with subsections and enactment."""
    detector = LegalCitationDetector()
    text = "Under Section 135(1)(a) of the Companies Act, 2013, companies must form a CSR Committee."
    citations = detector.detect_citations(text)

    assert len(citations) >= 1
    sec_cit = next((c for c in citations if "135(1)(a)" in c.citation_text), None)
    assert sec_cit is not None
    assert sec_cit.citation_type == "STATUTORY"
    assert sec_cit.normalized_id == "ACT_COMPANIES_2013_SEC_135_SUB_1"
    assert text[sec_cit.start_char:sec_cit.end_char] == sec_cit.citation_text



def test_judicial_citation_detection():
    """Verify detection of judicial citations (SCR, SCC, case names)."""
    detector = LegalCitationDetector()
    text = "In Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd., (2018) 1 SCC 353, the Supreme Court ruled."
    citations = detector.detect_citations(text)

    assert len(citations) >= 1
    # Check SCC reporter citation
    scc_cit = next((c for c in citations if "SCC" in c.citation_text), None)
    assert scc_cit is not None
    assert "(2018) 1 SCC 353" in scc_cit.citation_text
    assert scc_cit.citation_type == "JUDICIAL"
    assert text[scc_cit.start_char:scc_cit.end_char] == scc_cit.citation_text


def test_citation_proximity_association():
    """Verify that claims inherit citations from the same sentence or adjacent sentence."""
    extractor = ClaimExtractor()
    text = (
        "Section 135 of the Companies Act, 2013 governs Corporate Social Responsibility. "
        "The board must ensure expenditure of 2% average net profits."
    )
    res = extractor.extract(text, answer_id="ANS_CIT_01")

    assert len(res.claims) == 2
    c1, c2 = res.claims

    # Claim 1 has the explicit citation in the same sentence
    assert len(c1.citation_refs) >= 1
    assert any("Section 135" in cr.citation_text for cr in c1.citation_refs)

    # Claim 2 inherits the citation via proximity (preceding sentence)
    assert len(c2.citation_refs) >= 1
    assert any("Section 135" in cr.citation_text for cr in c2.citation_refs)
