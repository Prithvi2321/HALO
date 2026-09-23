"""
HALO Citation Verifier: Existence Verification Tests (Gate CV2)
===============================================================
Protocol: v1.0-FROZEN
Tests resolution of existing statutory sections (D1) and judicial judgments (D2).
Verifies strict separation of Authority Existence from Passage Existence.
"""

from halo.citation_verifier.verifier import verify_citations
from halo.citation_verifier.schemas import ExistenceStatus


def test_existing_statutory_sections_resolve_to_exists():
    """Verify that canonical sections of Companies Act, 2013 resolve to EXISTS."""
    res = verify_citations("Under Section 135(1) of the Companies Act, 2013, CSR expenditure is required.")
    assert res.total_citations == 1
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.canonical_authority_id == "ACT_COMPANIES_2013_SEC_135"
    assert len(c.existence.matched_passage_ids) >= 1
    assert "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1" in c.existence.matched_passage_ids

    # Authority hierarchy separation check
    h = c.existence.hierarchy
    assert h.authority_exists is True
    assert h.section_exists is True
    assert h.subsection_exists is True


def test_existing_judicial_citations_resolve_to_exists():
    """Verify that canonical Supreme Court judgments in D2 resolve to EXISTS."""
    res = verify_citations("The Supreme Court ruled in Bhushan Power & Steel Ltd., [2016] 11 S.C.R. 149, on mining leases.")
    assert res.total_citations >= 1
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert "JUD-SC-2016-2016_11_149_171" in c.canonical_authority_id
    assert len(c.existence.matched_passage_ids) >= 1


def test_authority_existence_separated_from_passage_existence():
    """
    Verify that an authority/section can exist even if passage resolution
    does not provide a specific sub-clause passage.
    """
    res = verify_citations("Under Section 460 of the Companies Act, 2013, the Central Government has condonation powers.")
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.existence.hierarchy.authority_exists is True
    assert c.existence.hierarchy.section_exists is True
