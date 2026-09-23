"""
Python Test Runner using standard library unittest.
Executes the Golden Test Suite and Section 75 Acceptance Tests.
"""

import os
import sys
import unittest
import json

FINAL_DIR = "data/dataset_1/final"


class TestGoldenCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FINAL_DIR, "companies_act_2013.json"), "r", encoding="utf-8") as f:
            cls.act_data = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_versions.json"), "r", encoding="utf-8") as f:
            cls.versions_data = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_amendments.json"), "r", encoding="utf-8") as f:
            cls.amendments_data = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_definitions.json"), "r", encoding="utf-8") as f:
            cls.definitions_data = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_cross_references.json"), "r", encoding="utf-8") as f:
            cls.cross_refs_data = json.load(f)

    def test_case_01_simple_section(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "9"), None)
        self.assertIsNotNone(sec)
        self.assertIn("Effect of registration", sec["heading"])
        self.assertGreater(sec["source_page_start"], 0)

    def test_case_02_section_with_subsections(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "1"), None)
        self.assertIsNotNone(sec)
        self.assertGreaterEqual(len(sec["subsections"]), 3)
        self.assertEqual(sec["subsections"][0]["subsection_number"], "1")

    def test_case_03_section_with_clauses(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "2"), None)
        self.assertIsNotNone(sec)
        self.assertTrue(len(sec["clauses"]) > 0 or len(sec["subsections"]) > 0)

    def test_case_04_nested_clauses(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "4"), None)
        self.assertIsNotNone(sec)
        self.assertTrue(any(len(sub["clauses"]) > 0 for sub in sec["subsections"]))

    def test_case_05_provisos(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "135"), None)
        self.assertIsNotNone(sec)
        self.assertTrue(len(sec["provisos"]) > 0 or any(len(sub["provisos"]) > 0 for sub in sec["subsections"]))

    def test_case_06_explanations(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "135"), None)
        self.assertIsNotNone(sec)
        self.assertTrue(len(sec["explanations"]) > 0 or any(len(sub["explanations"]) > 0 for sub in sec["subsections"]))

    def test_case_07_definition(self):
        self.assertGreater(len(self.definitions_data), 0)
        terms = [d["term"].lower() for d in self.definitions_data]
        self.assertTrue(any("company" in t for t in terms))

    def test_case_08_schedule(self):
        self.assertEqual(len(self.act_data["schedules"]), 7)
        sch1 = self.act_data["schedules"][0]
        self.assertEqual(sch1["schedule_number"], "I")
        self.assertEqual(sch1["source_page_start"], 253)

    def test_case_09_tables_in_schedule(self):
        sch1 = self.act_data["schedules"][0]
        self.assertGreater(len(sch1["tables"]), 0)

    def test_case_10_cross_reference(self):
        self.assertGreater(len(self.cross_refs_data), 0)
        self.assertTrue(any("Section 135" in r["target_reference"] for r in self.cross_refs_data))

    def test_case_11_section_amendment(self):
        amends = [a for a in self.amendments_data if a["target_section"] == "12"]
        self.assertGreater(len(amends), 0)

    def test_case_12_subsection_amendment(self):
        amends = [a for a in self.amendments_data if a.get("target_subsection") is not None]
        self.assertGreater(len(amends), 0)

    def test_case_13_clause_insertion(self):
        inserts = [a for a in self.amendments_data if a["operation"] == "INSERT"]
        self.assertGreater(len(inserts), 0)

    def test_case_14_clause_deletion(self):
        omits = [a for a in self.amendments_data if a["operation"] == "OMIT"]
        self.assertGreater(len(omits), 0)

    def test_case_15_word_substitution(self):
        subs = [a for a in self.amendments_data if a["operation"] == "SUBSTITUTE"]
        self.assertGreater(len(subs), 0)

    def test_case_16_delayed_commencement(self):
        self.assertTrue(any(a["effective_date"] != a["enactment_date"] for a in self.amendments_data))

    def test_case_17_repeal(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "465"), None)
        self.assertIsNotNone(sec)
        self.assertIn("Repeal", sec["heading"])

    def test_case_18_omission(self):
        sec = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "267"), None)
        self.assertIsNotNone(sec)
        self.assertEqual(sec["status"], "omitted")

    def test_case_19_historical_versions(self):
        self.assertEqual(len(self.versions_data["versions"]), 3)
        tags = [v["version_tag"] for v in self.versions_data["versions"]]
        self.assertIn("v2013_original", tags)
        self.assertIn("v2015_amended", tags)
        self.assertIn("v2020_amended", tags)

    def test_case_20_consolidation_report(self):
        with open("data/dataset_1/validation/consolidation_report.json", "r", encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["status"], "PASS")
        self.assertGreater(rep["matched_provisions"], 500)

    def test_case_21_text_integrity(self):
        with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["status"], "PASS")

    def test_case_22_boilerplate_cleaned(self):
        with open("data/dataset_1/normalized/boilerplate_audit.json", "r", encoding="utf-8") as f:
            audit = json.load(f)
        self.assertGreater(len(audit), 0)

    def test_case_23_multi_page_section(self):
        sec2 = next((s for ch in self.act_data["chapters"] for s in ch["sections"] if s["section_number"] == "2"), None)
        self.assertIsNotNone(sec2)
        self.assertGreater(sec2["source_page_end"], sec2["source_page_start"])

    def test_case_24_duplicate_page_check(self):
        with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
            rep = json.load(f)
        for doc in rep["documents"]:
            self.assertEqual(doc["page_count"], doc["expected_page_count"])

    def test_case_25_missing_page_check(self):
        with open("data/dataset_1/raw/pages_extracted.json", "r", encoding="utf-8") as f:
            raw = json.load(f)
        pages = [p["page_number"] for p in raw["ACT_COMPANIES_2013"]]
        self.assertEqual(pages, list(range(1, 371)))

    def test_case_26_pdf_valid(self):
        with open("data/dataset_1/validation/pdf_integrity_report.json", "r", encoding="utf-8") as f:
            rep = json.load(f)
        self.assertTrue(all(d["pdf_valid"] for d in rep["documents"]))

    def test_case_27_editorial_markers_and_footnotes(self):
        with open("data/dataset_1/normalized/statutory_footnotes.json", "r", encoding="utf-8") as f:
            fns = json.load(f)
        self.assertGreater(len(fns), 500)
        with open("data/dataset_1/structured/structured_act.json", "r", encoding="utf-8") as f:
            act = json.load(f)
        sec_12 = next(s for s in act["sections"] if s["section_number"] == "12")
        self.assertGreater(len(sec_12["editorial_markers"]), 0)
        self.assertGreater(len(sec_12["footnotes"]), 0)
        self.assertIn("3[within thirty days of its incorporation]", sec_12["text"])
        self.assertIn("within thirty days of its incorporation", sec_12["canonical_text"])
        self.assertNotIn("3[within thirty days", sec_12["canonical_text"])

    def test_case_28_explicit_temporal_lifecycle(self):
        with open("data/dataset_1/structured/structured_act.json", "r", encoding="utf-8") as f:
            act = json.load(f)
        sec_12 = next(s for s in act["sections"] if s["section_number"] == "12")
        self.assertEqual(sec_12["enactment_date"], "2013-08-29")
        self.assertIsNotNone(sec_12["commencement_date"])
        self.assertEqual(sec_12["enforcement_status"], "IN_FORCE")
        sec_267 = next(s for s in act["sections"] if s["section_number"] == "267")
        self.assertEqual(sec_267["enforcement_status"], "OMITTED")

    def test_case_29_freeze_manifest_lineage(self):
        manifest_path = "data/dataset_1/final/freeze_manifest.json"
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            mf = json.load(f)
        self.assertEqual(mf["status"], "CANDIDATE-FROZEN / PENDING FINAL QA")
        self.assertEqual(len(mf["source_pdf_hashes"]), 3)
        for doc_id, h in mf["source_pdf_hashes"].items():
            self.assertEqual(len(h), 64)
        for key in ["raw_pages_sha256", "normalized_pages_sha256", "canonical_act_sha256", "passages_jsonl_sha256", "provenance_sha256", "amendments_sha256", "versions_sha256"]:
            self.assertEqual(len(mf[key]), 64, f"Hash {key} invalid")

    def test_case_30_deterministic_rebuild(self):
        rebuild_path = "data/dataset_1/qa/deterministic_rebuild_results.json"
        self.assertTrue(os.path.exists(rebuild_path))
        with open(rebuild_path, "r", encoding="utf-8") as f:
            res = json.load(f)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["discrepancies_count"], 0)

    def test_case_31_golden_sections_audit(self):
        audit_path = "data/dataset_1/qa/audit_results.json"
        self.assertTrue(os.path.exists(audit_path))
        with open(audit_path, "r", encoding="utf-8") as f:
            res = json.load(f)
        self.assertEqual(res["golden_sections"]["status"], "PASS")
        for s_num in ["12", "22", "48", "54", "76A", "117", "135", "188", "267", "470"]:
            self.assertEqual(res["golden_sections"]["sections"][s_num]["status"], "PASS")

    def test_case_32_master_dataset_manifest(self):
        m_path = "data/dataset_1/final/dataset_1_manifest.json"
        self.assertTrue(os.path.exists(m_path))
        with open(m_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        self.assertIn(m["status"], ["FROZEN", "CANDIDATE-FROZEN / PENDING FINAL QA"])
        self.assertTrue(m["validation"]["automated_tests_passed"])
        self.assertEqual(m["validation"]["critical_issues"], 0)

    def test_case_33_human_review_queue(self):
        q_path = "data/dataset_1/qa/human_review_queue.jsonl"
        self.assertTrue(os.path.exists(q_path))
        with open(q_path, "r", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]
        self.assertTrue(all(item["severity"] in ["LOW", "MEDIUM"] for item in items))


class TestAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FINAL_DIR, "companies_act_2013.json"), "r", encoding="utf-8") as f:
            cls.act = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_provenance.json"), "r", encoding="utf-8") as f:
            prov = json.load(f)
            cls.prov_map = {p["section_number"]: p for p in prov}
        with open(os.path.join(FINAL_DIR, "companies_act_2013_versions.json"), "r", encoding="utf-8") as f:
            cls.versions = json.load(f)
        with open(os.path.join(FINAL_DIR, "companies_act_2013_passages.jsonl"), "r", encoding="utf-8") as f:
            cls.passages = [json.loads(line) for line in f]

    def test_acceptance_10_provisions(self):
        sections_to_test = ["1", "2", "3A", "12", "22", "48", "117", "135", "188", "267", "470"]
        for sec_num in sections_to_test:
            self.assertIn(sec_num, self.prov_map, f"Section {sec_num} missing from provenance")
            p_record = self.prov_map[sec_num]
            self.assertEqual(p_record["section_id"], f"ACT_COMPANIES_2013_SEC_{sec_num}")
            self.assertEqual(p_record["source_document_id"], "ACT_COMPANIES_2013")
            self.assertTrue(16 <= p_record["source_page_start"] <= 252)
            self.assertTrue(p_record["source_page_start"] <= p_record["source_page_end"])
            self.assertEqual(len(p_record["sha256"]), 64)
            self.assertEqual(len(p_record["content_hash"]), 64)

            sec_passages = [p for p in self.passages if p["section_id"] == p_record["section_id"]]
            self.assertGreaterEqual(len(sec_passages), 1)

    def test_acceptance_special_cases(self):
        # Section 12 amended
        self.assertIsNotNone(self.prov_map.get("12"))
        # Section 267 omitted
        sec_267 = next((s for ch in self.act["chapters"] for s in ch["sections"] if s["section_number"] == "267"), None)
        self.assertEqual(sec_267["status"], "omitted")
        # Section 2 multi-page (spans multiple pages)
        sec_2 = self.prov_map["2"]
        self.assertGreaterEqual(sec_2["source_page_end"] - sec_2["source_page_start"], 2)
        # Schedule VII
        sch = self.act["schedules"][-1]
        self.assertEqual(sch["schedule_number"], "VII")
        self.assertEqual(sch["source_page_start"], 369)
        # 3 versions
        self.assertEqual(len(self.versions["versions"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
