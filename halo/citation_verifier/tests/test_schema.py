"""
HALO Citation Verifier: Schema & Enum Tests (Gate CV1)
======================================================
Protocol: v1.0-FROZEN
Tests schema compliance, controlled enums (ExistenceStatus, MetadataStatus,
AuthorityType, MatchConfidenceTier), AuthorityHierarchy separation, and JSON round-trips.
"""

from halo.citation_verifier.schemas import (
    ExistenceStatus,
    MetadataStatus,
    AuthorityType,
    MatchConfidenceTier,
    AuthorityHierarchy,
    ParsedCitation,
    MetadataFieldDiff,
    ExistenceResult,
    MetadataResult,
    CitationVerificationRecord,
    CitationVerificationResult,
)


def test_existence_status_enum():
    """Verify ExistenceStatus controlled enum members."""
    expected = {"EXISTS", "NOT_FOUND", "AMBIGUOUS", "MALFORMED", "UNRESOLVED"}
    actual = {s.value for s in ExistenceStatus}
    assert actual == expected
    assert ExistenceStatus.from_str("exists") == ExistenceStatus.EXISTS
    assert ExistenceStatus.from_str("not_found") == ExistenceStatus.NOT_FOUND
    assert ExistenceStatus.from_str("UNKNOWN_STATUS") == ExistenceStatus.UNRESOLVED


def test_metadata_status_enum():
    """Verify MetadataStatus controlled enum members."""
    expected = {"MATCH", "PARTIAL_MATCH", "MISMATCH", "UNRESOLVED"}
    actual = {s.value for s in MetadataStatus}
    assert actual == expected
    assert MetadataStatus.from_str("match") == MetadataStatus.MATCH
    assert MetadataStatus.from_str("mismatch") == MetadataStatus.MISMATCH


def test_authority_type_enum():
    """Verify AuthorityType controlled enum members."""
    expected = {"STATUTE", "CASE", "JUDGMENT", "CONSTITUTION", "REGULATION", "UNKNOWN"}
    actual = {a.value for a in AuthorityType}
    assert actual == expected


def test_authority_hierarchy_serialization():
    """Verify AuthorityHierarchy separates authority, section, subsection, and passages."""
    h = AuthorityHierarchy(
        authority_exists=True,
        section_exists=True,
        subsection_exists=False,
        matched_passage_ids=["PAS_ACT_COMPANIES_2013_SEC_135"],
        details={"heading": "Corporate Social Responsibility"}
    )
    d = h.to_dict()
    assert d["authority_exists"] is True
    assert d["section_exists"] is True
    assert d["subsection_exists"] is False
    assert len(d["matched_passage_ids"]) == 1

    reconstructed = AuthorityHierarchy.from_dict(d)
    assert reconstructed == h


def test_parsed_citation_serialization():
    """Verify ParsedCitation serialization and deserialization."""
    parsed = ParsedCitation(
        citation_text="Section 135(1) of the Companies Act, 2013",
        authority_type=AuthorityType.STATUTE.value,
        act_name="Companies Act, 2013",
        section="135",
        subsection="1"
    )
    d = parsed.to_dict()
    assert d["act_name"] == "Companies Act, 2013"
    assert d["section"] == "135"

    reconstructed = ParsedCitation.from_dict(d)
    assert reconstructed == parsed


def test_citation_verification_record_roundtrip():
    """Verify CitationVerificationRecord serialization roundtrip."""
    h = AuthorityHierarchy(authority_exists=True, section_exists=True)
    exist_res = ExistenceResult(
        status=ExistenceStatus.EXISTS.value,
        confidence_tier=MatchConfidenceTier.EXACT_MATCH.value,
        canonical_authority_id="ACT_COMPANIES_2013_SEC_135",
        matched_passage_ids=["PAS_ACT_COMPANIES_2013_SEC_135_SUB_1"],
        hierarchy=h,
        explanation="Section 135 exists."
    )
    meta_res = MetadataResult(
        status=MetadataStatus.MATCH.value,
        fields={"section": MetadataFieldDiff("section", "135", "135", True)},
        explanation="Section matches."
    )

    rec = CitationVerificationRecord(
        citation_id="ANS_001_CIT001",
        claim_ids=["ANS_001_C001"],
        citation_text="Section 135(1)",
        start_char=0,
        end_char=14,
        existence=exist_res,
        metadata=meta_res,
        verification_tier="EXISTENCE",
        authority_type=AuthorityType.STATUTE.value,
        canonical_authority_id="ACT_COMPANIES_2013_SEC_135",
        source_corpus="D1_STATUTORY",
        explanation="Verified.",
        input_hash="hash_in",
        output_hash="hash_out"
    )

    d = rec.to_dict()
    assert d["citation_id"] == "ANS_001_CIT001"
    assert d["existence"]["status"] == "EXISTS"

    reconstructed = CitationVerificationRecord.from_dict(d)
    assert reconstructed.citation_id == rec.citation_id
    assert reconstructed.existence.status == rec.existence.status
    assert reconstructed.existence.hierarchy.authority_exists is True
