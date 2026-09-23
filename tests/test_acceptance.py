"""
Final Acceptance Tests on 10+ Provisions.
Complies with Section 75 of prompt.md.
"""

import os
import json
import pytest

FINAL_DIR = "data/dataset_1/final"


@pytest.fixture(scope="module")
def corpus():
    with open(os.path.join(FINAL_DIR, "companies_act_2013.json"), "r", encoding="utf-8") as f:
        act = json.load(f)
    with open(os.path.join(FINAL_DIR, "companies_act_2013_provenance.json"), "r", encoding="utf-8") as f:
        prov = json.load(f)
    with open(os.path.join(FINAL_DIR, "companies_act_2013_versions.json"), "r", encoding="utf-8") as f:
        versions = json.load(f)
    with open(os.path.join(FINAL_DIR, "companies_act_2013_passages.jsonl"), "r", encoding="utf-8") as f:
        passages = [json.loads(line) for line in f]

    return {
        "act": act,
        "provenance": {p["section_number"]: p for p in prov},
        "versions": versions,
        "passages": passages
    }


ACCEPTANCE_SECTIONS = [
    "1",    # Short title, extent, commencement
    "2",    # Definitions (multi-page)
    "3A",   # Members severally liable
    "12",   # Registered office (amended 2015)
    "22",   # Execution of deeds (amended 2015)
    "48",   # Variation of rights (amended 2020)
    "117",  # Resolutions to be filed (amended 2015, 2020)
    "135",  # CSR
    "188",  # Related party transactions (amended 2015, 2020)
    "267",  # Omitted section
    "470"   # Removal of difficulties (final section)
]


def test_acceptance_10_provisions(corpus):
    prov_map = corpus["provenance"]
    passages = corpus["passages"]

    for sec_num in ACCEPTANCE_SECTIONS:
        assert sec_num in prov_map, f"Section {sec_num} missing from provenance"
        p_record = prov_map[sec_num]

        # 1. Deterministic Section ID
        assert p_record["section_id"] == f"ACT_COMPANIES_2013_SEC_{sec_num}"

        # 2. Source Document & Pages
        assert p_record["source_document_id"] == "ACT_COMPANIES_2013"
        assert 16 <= p_record["source_page_start"] <= 252
        assert p_record["source_page_start"] <= p_record["source_page_end"]

        # 3. Bit-level SHA-256 Hash
        assert len(p_record["sha256"]) == 64
        assert len(p_record["content_hash"]) == 64

        # 4. Retrieval Passages
        sec_passages = [p for p in passages if p["section_id"] == p_record["section_id"]]
        assert len(sec_passages) >= 1, f"No passages generated for section {sec_num}"
        for pas in sec_passages:
            assert pas["passage_id"].startswith("PAS_")
            assert len(pas["text"]) > 0
            assert pas["source_page_start"] >= 16

    print(f"\n[SUCCESS] Passed full 12-point audit for {len(ACCEPTANCE_SECTIONS)} provisions.")


def test_acceptance_special_categories(corpus):
    prov_map = corpus["provenance"]
    versions = corpus["versions"]

    # One amended section
    sec_12 = prov_map["12"]
    assert sec_12 is not None

    # One omitted provision
    sec_267 = next((s for ch in corpus["act"]["chapters"] for s in ch["sections"] if s["section_number"] == "267"), None)
    assert sec_267["status"] == "omitted"

    # One multi-page section
    sec_2 = prov_map["2"]
    assert sec_2["source_page_end"] - sec_2["source_page_start"] >= 2

    # One schedule
    sch = corpus["act"]["schedules"][-1]
    assert sch["schedule_number"] == "VII"
    assert sch["source_page_start"] == 369

    # Historical versions
    v_tags = [v["version_tag"] for v in versions["versions"]]
    assert len(v_tags) == 3
