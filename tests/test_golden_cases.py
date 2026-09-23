"""
Golden Test Suite Covering the 26 Edge Cases from Section 54 of prompt.md.
"""

import os
import json
import pytest

FINAL_DIR = "data/dataset_1/final"


@pytest.fixture(scope="module")
def act_data():
    path = os.path.join(FINAL_DIR, "companies_act_2013.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def versions_data():
    path = os.path.join(FINAL_DIR, "companies_act_2013_versions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def amendments_data():
    path = os.path.join(FINAL_DIR, "companies_act_2013_amendments.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def definitions_data():
    path = os.path.join(FINAL_DIR, "companies_act_2013_definitions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def cross_refs_data():
    path = os.path.join(FINAL_DIR, "companies_act_2013_cross_references.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Case 1: Simple section
def test_case_01_simple_section(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "9"), None)
    assert sec is not None
    assert "Effect of registration" in sec["heading"]
    assert sec["source_page_start"] > 0


# Case 2: Section with subsection
def test_case_02_section_with_subsections(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "1"), None)
    assert sec is not None
    assert len(sec["subsections"]) >= 3
    assert sec["subsections"][0]["subsection_number"] == "1"


# Case 3: Section with clauses
def test_case_03_section_with_clauses(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "2"), None)
    assert sec is not None
    assert len(sec["clauses"]) > 0 or len(sec["subsections"]) > 0


# Case 4: Nested clauses
def test_case_04_nested_clauses(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "4"), None)
    assert sec is not None
    assert any(len(sub["clauses"]) > 0 for sub in sec["subsections"])


# Case 5: Proviso
def test_case_05_provisos(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "135"), None)
    assert sec is not None
    assert len(sec["provisos"]) > 0 or any(len(sub["provisos"]) > 0 for sub in sec["subsections"])


# Case 6: Explanation
def test_case_06_explanations(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "135"), None)
    assert sec is not None
    assert len(sec["explanations"]) > 0 or any(len(sub["explanations"]) > 0 for sub in sec["subsections"])


# Case 7: Definition
def test_case_07_definition(definitions_data):
    assert len(definitions_data) > 0
    terms = [d["term"].lower() for d in definitions_data]
    assert any("company" in t for t in terms)


# Case 8: Schedule
def test_case_08_schedule(act_data):
    assert len(act_data["schedules"]) == 7
    sch1 = act_data["schedules"][0]
    assert sch1["schedule_number"] == "I"
    assert sch1["source_page_start"] == 253


# Case 9: Table
def test_case_09_tables_in_schedule(act_data):
    sch1 = act_data["schedules"][0]
    assert len(sch1["tables"]) > 0


# Case 10: Cross-reference
def test_case_10_cross_reference(cross_refs_data):
    assert len(cross_refs_data) > 0
    assert any("Section 135" in r["target_reference"] for r in cross_refs_data)


# Case 11: Section amendment
def test_case_11_section_amendment(amendments_data):
    amends = [a for a in amendments_data if a["target_section"] == "12"]
    assert len(amends) > 0


# Case 12: Subsection amendment
def test_case_12_subsection_amendment(amendments_data):
    amends = [a for a in amendments_data if a.get("target_subsection") is not None]
    assert len(amends) > 0


# Case 13: Clause insertion
def test_case_13_clause_insertion(amendments_data):
    inserts = [a for a in amendments_data if a["operation"] == "INSERT"]
    assert len(inserts) > 0


# Case 14: Clause deletion
def test_case_14_clause_deletion(amendments_data):
    omits = [a for a in amendments_data if a["operation"] == "OMIT"]
    assert len(omits) > 0


# Case 15: Word substitution
def test_case_15_word_substitution(amendments_data):
    subs = [a for a in amendments_data if a["operation"] == "SUBSTITUTE"]
    assert len(subs) > 0


# Case 16: Delayed commencement
def test_case_16_delayed_commencement(amendments_data):
    assert any(a["effective_date"] != a["enactment_date"] for a in amendments_data)


# Case 17: Repeal
def test_case_17_repeal_section(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "465"), None)
    assert sec is not None
    assert "Repeal" in sec["heading"]


# Case 18: Omission
def test_case_18_omitted_provision(act_data):
    sec = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "267"), None)
    assert sec is not None
    assert sec["status"] == "omitted"


# Case 19: Historical version
def test_case_19_historical_versions(versions_data):
    assert len(versions_data["versions"]) == 3
    tags = [v["version_tag"] for v in versions_data["versions"]]
    assert "v2013_original" in tags
    assert "v2015_amended" in tags
    assert "v2020_amended" in tags


# Case 20: Consolidated version match
def test_case_20_consolidation_report():
    with open("data/dataset_1/validation/consolidation_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)
    assert rep["status"] == "PASS"
    assert rep["matched_provisions"] > 500


# Case 21: OCR / clean text validity
def test_case_21_text_integrity():
    with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)
    assert rep["status"] == "PASS"


# Case 22: Multi-column page / line breaks normalized
def test_case_22_boilerplate_cleaned():
    with open("data/dataset_1/normalized/boilerplate_audit.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert len(audit) > 0


# Case 23: Section spanning multiple pages
def test_case_23_multi_page_section(act_data):
    sec2 = next((s for ch in act_data["chapters"] for s in ch["sections"] if s["section_number"] == "2"), None)
    assert sec2 is not None
    assert sec2["source_page_end"] > sec2["source_page_start"]


# Case 24: Duplicate page check
def test_case_24_duplicate_page_check():
    with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)
    for doc in rep["documents"]:
        assert doc["page_count"] == doc["expected_page_count"]


# Case 25: Missing page check
def test_case_25_missing_page_check():
    with open("data/dataset_1/raw/pages_extracted.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    pages = [p["page_number"] for p in raw["ACT_COMPANIES_2013"]]
    assert pages == list(range(1, 371))


# Case 26: Invalid PDF handling
def test_case_26_pdf_valid():
    with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)
    assert all(d["pdf_valid"] for d in rep["documents"])
