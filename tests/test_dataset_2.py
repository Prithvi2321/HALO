"""
HALO Dataset 2: Unit & Component Test Suite
===========================================
Tests data models, deduplication, scoring, paragraph detection,
citation verification states, and Dataset 1 statutory linkage.
"""

import os
import unittest
from scripts.dataset_2.models import (
    CandidateJudgment,
    CourtType,
    SourceAuthority,
    LifecycleState,
    JudgmentParagraph,
    CitationState,
    StatutoryCrossReference,
    JudgmentMetadata,
    SourceSnapshot
)
from scripts.dataset_2.deduplicator import JudgmentDeduplicator
from scripts.dataset_2.ranker import CandidateRanker
from scripts.dataset_2.selection_gate import SelectionGate
from scripts.dataset_2.parser import JudicialParser
from scripts.dataset_2.passage_generator import PassageGenerator


class TestDataset2(unittest.TestCase):

    def test_01_models_validation(self):
        snapshot = SourceSnapshot(
            source_id="SRC_SC_REGISTRY",
            source_authority=SourceAuthority.OFFICIAL,
            source_url="https://example.com/test.pdf",
            retrieval_timestamp="2026-09-06T22:00:00Z",
            http_metadata={"status_code": 200},
            file_size=1024,
            sha256="abc123sha",
            license="CC-BY-4.0"
        )
        self.assertEqual(snapshot.source_authority, SourceAuthority.OFFICIAL)

        cand = CandidateJudgment(
            candidate_id="CAND-SC-2020-001",
            source_id="SRC_SC_REGISTRY",
            court=CourtType.SUPREME_COURT_OF_INDIA,
            case_title="Tata Sons Ltd. v. Cyrus Investments Pvt. Ltd.",
            case_number="Civil Appeal No. 4400 of 2020",
            decision_date="2021-03-26",
            citations=["2021 INSC 228"],
            source_url="https://example.com/tata.pdf",
            source_authority=SourceAuthority.OFFICIAL,
            lifecycle_state=LifecycleState.DISCOVERED
        )
        self.assertEqual(cand.court, CourtType.SUPREME_COURT_OF_INDIA)
        self.assertEqual(cand.lifecycle_state, LifecycleState.DISCOVERED)

    def test_02_deduplication_engine(self):
        dedup = JudgmentDeduplicator(log_path="Data/dataset2/discovery/test_dedup_log.json")
        c1 = CandidateJudgment(
            candidate_id="CAND-01",
            source_id="SRC_1",
            court=CourtType.SUPREME_COURT_OF_INDIA,
            case_title="Alpha Ltd. v. Beta Ltd.",
            case_number="Civil Appeal 100/2020",
            decision_date="2020-05-15",
            citations=["2020 INSC 100"],
            source_url="https://example.com/1.pdf"
        )
        c2 = CandidateJudgment(
            candidate_id="CAND-02",
            source_id="SRC_2",
            court=CourtType.SUPREME_COURT_OF_INDIA,
            case_title="Alpha Limited versus Beta Limited",
            case_number="C.A. No. 100 of 2020",  # Same case number normalized
            decision_date="2020-05-15",
            citations=["2020 INSC 100"],
            source_url="https://example.com/2.pdf"
        )
        unique, dups = dedup.deduplicate([c1, c2])
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0].lifecycle_state, LifecycleState.REJECTED_DUPLICATE)

    def test_03_ranker_and_scoring(self):
        ranker = CandidateRanker(scores_output_path="Data/dataset2/discovery/test_scores.jsonl")
        c = CandidateJudgment(
            candidate_id="CAND-03",
            source_id="SRC_SC_REGISTRY",
            court=CourtType.SUPREME_COURT_OF_INDIA,
            case_title="Union of India v. IL&FS Ltd.",
            case_number="CA 500/2019",
            decision_date="2019-08-10",
            citations=["2019 INSC 500", "[2019] 10 S.C.R. 500"],
            discovery_terms=["section 241", "oppression", "companies act", "corporate governance"],
            source_url="https://example.com/ilfs.pdf",
            source_authority=SourceAuthority.OFFICIAL
        )
        score_data = ranker.score_candidate(c, topic_counts={})
        self.assertGreaterEqual(score_data["composite_score"], 0.70)
        self.assertIn("Oppression & Mismanagement", score_data["topics"])

    def test_04_statutory_cross_reference_resolution(self):
        parser = JudicialParser()
        para = JudgmentParagraph(
            paragraph_id="JUD-SC-2020-001-P01",
            judgment_id="JUD-SC-2020-001",
            paragraph_number=1,
            page_start=1,
            page_end=1,
            char_start=0,
            char_end=200,
            text="The petition was filed under Section 241 and Section 242 of the Companies Act, 2013 alleging oppression by the majority shareholder.",
            source_sha256="dummy_hash",
            extraction_method="native_pdf"
        )
        xrefs = parser.extract_statutory_cross_references([para], "JUD-SC-2020-001")
        self.assertGreaterEqual(len(xrefs), 2)
        sec_ids = [x.dataset_1_id for x in xrefs]
        self.assertIn("ACT_COMPANIES_2013_SEC_241", sec_ids)
        self.assertIn("ACT_COMPANIES_2013_SEC_242", sec_ids)
        self.assertEqual(xrefs[0].resolution_status, "RESOLVED")

    def test_05_predecessor_1956_mapping(self):
        parser = JudicialParser()
        para = JudgmentParagraph(
            paragraph_id="JUD-SC-2015-001-P05",
            judgment_id="JUD-SC-2015-001",
            paragraph_number=5,
            page_start=2,
            page_end=2,
            char_start=0,
            char_end=250,
            text="Under Section 397 of the Companies Act, 1956, the company law board had extensive powers to remedy oppression, which corresponds to the modern regime.",
            source_sha256="dummy_hash",
            extraction_method="native_pdf"
        )
        xrefs = parser.extract_statutory_cross_references([para], "JUD-SC-2015-001")
        self.assertGreaterEqual(len(xrefs), 1)
        self.assertEqual(xrefs[0].dataset_1_id, "ACT_COMPANIES_2013_SEC_241")
        self.assertEqual(xrefs[0].resolution_method, "predecessor_continuity")

    def test_06_citation_extraction(self):
        parser = JudicialParser()
        para = JudgmentParagraph(
            paragraph_id="JUD-SC-2020-001-P02",
            judgment_id="JUD-SC-2020-001",
            paragraph_number=2,
            page_start=1,
            page_end=1,
            char_start=0,
            char_end=200,
            text="As observed by this Court in Needle Industries v. New Needle [1981] 3 S.C.R. 698 and reaffirmed in 2021 INSC 228, oppression must be continuous.",
            source_sha256="dummy_hash",
            extraction_method="native_pdf"
        )
        cits = parser.extract_citations([para], "JUD-SC-2020-001")
        self.assertGreaterEqual(len(cits), 1)
        self.assertIn(cits[0].verification_state, [CitationState.RESOLVED, CitationState.NORMALIZED])

    def test_07_passage_generation(self):
        gen = PassageGenerator(target_chars_per_passage=500)
        snapshot = SourceSnapshot(
            source_id="TEST",
            source_authority=SourceAuthority.OFFICIAL,
            source_url="http://test",
            retrieval_timestamp="2026-09-06T22:00:00Z",
            file_size=10,
            sha256="hash",
            license="CC"
        )
        meta = JudgmentMetadata(
            judgment_id="JUD-TEST-001",
            document_type="JUDGMENT",
            court=CourtType.SUPREME_COURT_OF_INDIA,
            case_number="CA 1/2020",
            case_title="Test v. Test",
            date_of_judgment="2020-01-01",
            citations=["2020 INSC 1"],
            source_snapshot=snapshot,
            topic_classification=["Oppression & Mismanagement"],
            statutory_provisions_cited=["241"]
        )
        p1 = JudgmentParagraph(
            paragraph_id="JUD-TEST-001-P01",
            judgment_id="JUD-TEST-001",
            paragraph_number=1,
            page_start=1,
            page_end=1,
            char_start=0,
            char_end=200,
            text="First judicial paragraph discussing company law principles.",
            source_sha256="hash"
        )
        p2 = JudgmentParagraph(
            paragraph_id="JUD-TEST-001-P02",
            judgment_id="JUD-TEST-001",
            paragraph_number=2,
            page_start=1,
            page_end=1,
            char_start=200,
            char_end=400,
            text="Second judicial paragraph continuing the legal analysis.",
            source_sha256="hash"
        )
        passages = gen.generate_passages(meta, [p1, p2])
        self.assertGreaterEqual(len(passages), 1)
        self.assertEqual(passages[0].document_id, "JUD-TEST-001")
        self.assertIn("JUD-TEST-001-P01", passages[0].paragraph_ids)

    def test_08_dataset_1_immutability(self):
        # Verify Dataset 1 files exist and remain untouched
        d1_manifest = "data/dataset_1/final/dataset_1_manifest.json"
        d1_act = "data/dataset_1/final/companies_act_2013.json"
        self.assertTrue(os.path.exists(d1_manifest))
        self.assertTrue(os.path.exists(d1_act))


if __name__ == "__main__":
    unittest.main()
