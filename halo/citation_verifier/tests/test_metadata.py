"""
HALO Citation Verifier: Metadata Mismatch Tests (Gate CV4)
==========================================================
Protocol: v1.0-FROZEN
Tests detection of metadata discrepancies: court mismatches, year mismatches,
act enactment year errors, and subsection variations.
"""

from halo.citation_verifier.verifier import verify_citations
from halo.citation_verifier.schemas import MetadataStatus, ExistenceStatus


def test_court_mismatch_detected():
    """Verify detection when Supreme Court judgment is falsely attributed to NCLAT."""
    cit_dict = {
        "case_name": "Bhushan Power & Steel Ltd.",
        "citation_number": "[2016] 11 S.C.R. 149",
        "court": "NCLAT",
        "year": "2016"
    }
    res = verify_citations({"answer_id": "TEST_META_01", "citation": cit_dict})
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.metadata.status == MetadataStatus.MISMATCH.value
    assert "court_mismatch" in c.metadata.mismatches


def test_year_mismatch_detected():
    """Verify detection when decision year conflicts with canonical record."""
    cit_dict = {
        "case_name": "Tata Consultancy Services Limited v. Vishal Ghisulal Jain",
        "citation_number": "[2021] 10 S.C.R. 1080",
        "court": "SUPREME_COURT_OF_INDIA",
        "year": "2010"  # Real year is 2021
    }
    res = verify_citations({"answer_id": "TEST_META_02", "citation": cit_dict})
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.metadata.status == MetadataStatus.MISMATCH.value
    assert "year_mismatch" in c.metadata.mismatches


def test_act_enactment_year_mismatch():
    """Verify detection when statute enactment year is mutated (Companies Act, 2018)."""
    res = verify_citations("Under Section 1 of the Companies Act, 2018, the short title is set forth.")
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.metadata.status == MetadataStatus.MISMATCH.value
    assert "act_year_mismatch" in c.metadata.mismatches


def test_all_metadata_matching():
    """Verify that accurate metadata yields MetadataStatus.MATCH."""
    cit_dict = {
        "case_name": "Mobilox Innovations Private Limited v. Kirusa Software Private Limited",
        "citation_number": "[2017] 10 S.C.R. 1006",
        "court": "SUPREME_COURT_OF_INDIA",
        "year": "2017"
    }
    res = verify_citations({"answer_id": "TEST_META_03", "citation": cit_dict})
    c = res.citation_results[0]
    assert c.existence.status == ExistenceStatus.EXISTS.value
    assert c.metadata.status == MetadataStatus.MATCH.value
    assert len(c.metadata.mismatches) == 0
