"""
HALO Citation Verifier: Fabricated Citation Detection Tests (Gate CV3)
=====================================================================
Protocol: v1.0-FROZEN
Tests detection of fabricated Acts, non-existent statutory sections,
fabricated judicial cases, and out-of-bounds paragraphs.
Verifies that canonical lookup is performed rather than hard-coded numeric bounds.
"""

from halo.citation_verifier.verifier import verify_citations
from halo.citation_verifier.schemas import ExistenceStatus, MetadataStatus


def test_fabricated_act_detected():
    """Verify that a completely fabricated statute is flagged as NOT_FOUND."""
    res = verify_citations("Under Section 12 of the Indian Corporate Metaverse and Blockchain Act, 2024, token sales require approval.")
    assert res.total_citations == 1
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.NOT_FOUND.value
    assert "Indian Corporate Metaverse and Blockchain Act, 2024" in c.existence.explanation
    assert c.canonical_authority_id is None


def test_fabricated_ai_code_detected():
    """Verify detection of another synthetic adversarial Act."""
    res = verify_citations("Pursuant to Section 5 of the Artificial Intelligence Commercial Code, 2025, neural weights must be registered.")
    assert res.total_citations == 1
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.NOT_FOUND.value


def test_nonexistent_section_via_canonical_lookup():
    """
    Verify that non-existent sections in Companies Act, 2013 are NOT_FOUND
    via canonical corpus querying, not by hardcoded numeric limits.
    """
    # Section 480 does not exist in D1
    res = verify_citations("Section 480 of the Companies Act, 2013 sets forth registration of decentralized entities.")
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.NOT_FOUND.value
    assert "Section 480 not found" in c.existence.explanation

    # Section 600 does not exist in D1
    res2 = verify_citations("Section 600 of the Companies Act, 2013 governs foreign sovereign mergers.")
    c2 = res2.citation_results[0]
    assert c2.existence.status == ExistenceStatus.NOT_FOUND.value


def test_fabricated_judicial_case_detected():
    """Verify that synthetic case citations not present in D2 are flagged as NOT_FOUND."""
    res = verify_citations("In Zenith Corporate Robotics v. UOI, 2025 INSC 888, the Supreme Court ruled on autonomous board quorum.")
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.NOT_FOUND.value
    assert c.canonical_authority_id is None


def test_impossible_paragraph_bounds_detected():
    """Verify that paragraph numbers exceeding judgment length are detected as MISMATCH."""
    cit_dict = {
        "case_name": "Bhushan Power & Steel Ltd.",
        "citation_number": "[2016] 11 S.C.R. 149",
        "paragraph": "999"
    }
    res = verify_citations({"answer_id": "TEST_PARA", "citation": cit_dict})
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value  # Authority exists
    assert c.metadata.status == MetadataStatus.MISMATCH.value  # But paragraph 999 does not exist
    assert "paragraph_out_of_bounds" in c.metadata.mismatches
