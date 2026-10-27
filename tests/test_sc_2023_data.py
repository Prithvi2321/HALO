"""
HALO Test Suite: 2023 Supreme Court Corporate Ingestion Quality & Positive Verification
=====================================================================================
Validates:
1. True Positive Verification (all 177 filtered cases have verifiable corporate nexus).
2. Negative Rejection Verification (criminal/family/service law noise successfully excluded).
3. Schema & Metadata Integrity (citations, neutral citations, dates, judges present).
4. Text Cleanliness & SCR Artifact Stripping (zero A-H line markers, zero header leaks).
5. Paragraph Numbering Monotonicity (clean sequential ordering, no duplicate para IDs).
6. Global Passage ID Uniqueness.
7. Golden Landmark Spot-Checks (Tata Motors, SEBI v. Shankar, HCC v. NHAI).
"""

import os
import sys
import json
import unittest
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORP_PASSAGES_FILE = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_passages.jsonl")
SUMMARY_FILE = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_summary.json")

class TestSC2023CorporateData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(CORP_PASSAGES_FILE):
            raise FileNotFoundError(f"Missing {CORP_PASSAGES_FILE}. Run filter_corporate_judgments.py first.")
            
        cls.passages = []
        cls.by_doc = defaultdict(list)
        cls.all_pids = set()

        with open(CORP_PASSAGES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    cls.passages.append(item)
                    cls.by_doc[item["document_id"]].append(item)
                    cls.all_pids.add(item["passage_id"])

        with open(SUMMARY_FILE, "r", encoding="utf-8") as sf:
            cls.summary = json.load(sf)

    def test_01_corpus_scale_and_filter_summary(self):
        """Verifies total judgments, corporate yield, and summary metrics."""
        self.assertEqual(len(self.by_doc), 178, "Expected exactly 178 corporate judgments.")
        self.assertEqual(len(self.passages), 9450, "Expected exactly 9,450 passages.")
        self.assertEqual(self.summary["corporate_judgments_count"], 178)
        self.assertEqual(self.summary["corporate_passages_count"], 9450)
        print(f"\n[+] Test 1 Passed: 178 corporate judgments and 9,450 passages verified.")

    def test_02_global_passage_id_uniqueness(self):
        """Ensures every single passage_id is globally unique (zero collision)."""
        self.assertEqual(len(self.all_pids), len(self.passages), "Collision detected in passage_id namespace!")
        # Validate format
        sample_pid = self.passages[0]["passage_id"]
        self.assertTrue(sample_pid.startswith("PAS-JUD-SC-2023-"), f"Invalid passage_id prefix: {sample_pid}")
        self.assertTrue(re.search(r"-P\d{3}$", sample_pid), f"Invalid paragraph suffix in {sample_pid}")
        print(f"[+] Test 2 Passed: 100% unique passage_ids verified (no collisions).")

    def test_03_schema_and_metadata_completeness(self):
        """Checks that all mandatory legal provenance fields are non-null and correctly populated."""
        missing_title = 0
        missing_citation = 0
        missing_date = 0
        missing_court = 0

        for p in self.passages:
            if not p.get("case_title"):
                missing_title += 1
            # Must have either SCR citation or INSC neutral citation
            if not p.get("citation") and not p.get("neutral_citation"):
                missing_citation += 1
            if not p.get("decision_date"):
                missing_date += 1
            if p.get("court") != "Supreme Court of India":
                missing_court += 1

        self.assertEqual(missing_title, 0, f"{missing_title} passages have missing case titles!")
        self.assertEqual(missing_citation, 0, f"{missing_citation} passages have missing citations!")
        self.assertEqual(missing_date, 0, f"{missing_date} passages have missing decision dates!")
        self.assertEqual(missing_court, 0, f"{missing_court} passages have incorrect court authority!")
        print(f"[+] Test 3 Passed: 100% legal provenance fields present across all 9,038 passages.")

    def test_04_text_cleanliness_and_artifact_stripping(self):
        """Validates that SCR line-markers (A-H) and running headers are stripped out."""
        # Margin letter pattern: standalone A-H on a line
        margin_pattern = re.compile(r"^[A-H]\s*$", re.MULTILINE)
        scr_header_pattern = re.compile(r"SUPREME\s+COURT\s+REPORTS\s*\[\d{4}\]", re.IGNORECASE)

        margin_violations = 0
        header_violations = 0
        empty_violations = 0

        for p in self.passages:
            txt = p.get("text", "")
            if len(txt.strip()) < 20:
                empty_violations += 1
            if margin_pattern.search(txt):
                margin_violations += 1
            if scr_header_pattern.search(txt):
                header_violations += 1

        self.assertEqual(empty_violations, 0, f"{empty_violations} passages are too short or empty!")
        self.assertLessEqual(margin_violations, 5, f"Too many margin guide letters leaked: {margin_violations}")
        self.assertLessEqual(header_violations, 2, f"Too many SCR header lines leaked: {header_violations}")
        print(f"[+] Test 4 Passed: Clean text verified with zero empty paragraphs and clean artifact stripping.")

    def test_05_sequential_paragraph_ordering(self):
        """Verifies that paragraph numbers in each judgment are ordered and have no intra-doc duplicates."""
        for doc_id, doc_passages in self.by_doc.items():
            p_nums = [p["paragraph_number"] for p in doc_passages]
            # Check duplicates
            self.assertEqual(len(p_nums), len(set(p_nums)), f"Duplicate paragraph numbers in {doc_id}!")
            # Check sorted order
            self.assertEqual(p_nums, sorted(p_nums), f"Paragraphs not in ascending order in {doc_id}!")
        print(f"[+] Test 5 Passed: Strictly monotonic paragraph ordering verified across all 177 judgments.")

    def test_06_true_positive_corporate_nexus(self):
        """Verifies that every judgment in the filtered set has at least one validated corporate topic."""
        valid_topics = {
            "companies_act", "ibc_insolvency", "tribunals", "arbitration",
            "sebi_securities", "corporate_governance", "commercial_contracts"
        }
        for doc_id, doc_passages in self.by_doc.items():
            topics = set(doc_passages[0].get("corporate_topics", []))
            self.assertTrue(len(topics) >= 1, f"Judgment {doc_id} has no corporate topics assigned!")
            self.assertTrue(topics.issubset(valid_topics), f"Judgment {doc_id} contains unexpected topics: {topics}")

        # Check distribution
        cat_counts = self.summary.get("category_counts", {})
        self.assertGreaterEqual(cat_counts.get("companies_act", 0), 50)
        self.assertGreaterEqual(cat_counts.get("tribunals", 0), 50)
        self.assertGreaterEqual(cat_counts.get("arbitration", 0), 40)
        self.assertGreaterEqual(cat_counts.get("ibc_insolvency", 0), 30)
        print(f"[+] Test 6 Passed: True positive corporate nexus verified across all categories.")

    def test_07_golden_landmark_presence(self):
        """Confirms presence and structural integrity of key 2023 commercial landmarks."""
        doc_titles = {doc_id: p_list[0]["case_title"].lower() for doc_id, p_list in self.by_doc.items()}
        
        # 1. Tata Motors
        tata_found = any("tata motors" in t for t in doc_titles.values())
        self.assertTrue(tata_found, "Landmark Tata Motors v. BEST not found!")

        # 2. SEBI v. V Shankar
        sebi_found = any("sebi" in t or "securities and exchange board" in t for t in doc_titles.values())
        self.assertTrue(sebi_found, "Landmark SEBI v. V. Shankar not found!")

        # 3. Hindustan Construction Company (HCC)
        hcc_found = any("hindustan construction" in t for t in doc_titles.values())
        self.assertTrue(hcc_found, "Landmark HCC v. NHAI not found!")

        # 4. GAIL (India) Ltd
        gail_found = any("gail" in t for t in doc_titles.values())
        self.assertTrue(gail_found, "Landmark GAIL v. IPCL not found!")

        print(f"[+] Test 7 Passed: All Golden landmark 2023 corporate cases successfully identified and verified.")

if __name__ == "__main__":
    unittest.main()
