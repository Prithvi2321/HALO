"""
Citation Verification & Passage Fabrication Benchmark Generators (D3-E, D3-F, D3-G)
===================================================================================
Covers:
  - D3-E: Citation Existence Benchmark (Authentic, Fabricated Case, Fabricated Citation, Non-Existent Para)
  - D3-F: Citation Metadata Mismatch (Citation Swap, Wrong Court, Wrong Date)
  - D3-G: Passage-Level Fabrication Benchmark (Authentic Passage, Fabricated Proposition)
"""

import random
from typing import List, Dict, Any
from ..models import CitationVerificationRecord, PassageVerificationRecord
from ..evidence_loader import get_corpus


class VerificationGenerator:
    def __init__(self, seed: int = 42):
        self.corpus = get_corpus()
        self.rng = random.Random(seed)

    def generate_all(self) -> Dict[str, List[Any]]:
        print("[*] [VerificationGenerator] Generating D3-E: Citation Existence Benchmark...")
        d3_e = self._generate_d3_e()
        print(f"    [+] Generated {len(d3_e)} D3-E records.")

        print("[*] [VerificationGenerator] Generating D3-F: Citation Metadata Mismatch Benchmark...")
        d3_f = self._generate_d3_f()
        print(f"    [+] Generated {len(d3_f)} D3-F records.")

        print("[*] [VerificationGenerator] Generating D3-G: Passage-Level Fabrication Benchmark...")
        d3_g = self._generate_d3_g()
        print(f"    [+] Generated {len(d3_g)} D3-G records.")

        return {
            "d3_e": d3_e,
            "d3_f": d3_f,
            "d3_g": d3_g
        }

    # -------------------------------------------------------------------------
    # D3-E: Citation Existence Benchmark
    # -------------------------------------------------------------------------
    def _generate_d3_e(self) -> List[CitationVerificationRecord]:
        records: List[CitationVerificationRecord] = []
        idx = 1

        all_judgments = list(self.corpus.d2_judgments.values())

        # Category 1: Authentic Citations (40 records) -> SUPPORTED
        for j in all_judgments[:40]:
            j_id = j["judgment_id"]
            title = j.get("case_title", "Unknown Case")
            court = j.get("court", "Supreme Court of India")
            date = j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01"
            cits = self.corpus.get_d2_citations_for_judgment(j_id)
            cit_str = cits[0]["normalized_citation"] if cits else f"[{date[:4]}] INSC {idx}"
            passages = self.corpus.get_d2_passages_for_judgment(j_id)
            para_num = "1"
            if passages:
                para_ids = passages[0].get("paragraph_ids", [])
                if para_ids:
                    para_num = para_ids[0].split("-P")[-1].lstrip("0") or "1"

            claim = f"In {title}, {cit_str}, the {court} laid down key principles under company law."
            records.append(CitationVerificationRecord(
                test_id=f"D3_CIT_{idx:06d}",
                benchmark_family="D3-E",
                claim=claim,
                cited_case_name=title,
                cited_citation=cit_str,
                cited_court=court,
                cited_date=date,
                cited_paragraph=para_num,
                expected_verification_status="SUPPORTED",
                failure_type="AUTHENTIC_RECORD",
                real_source_ids=[j_id],
                metadata_discrepancy_details=None,
                difficulty="easy"
            ))
            idx += 1

        # Category 2: Fabricated Cases (20 records) -> REJECTED
        fabricated_cases = [
            ("Rameshwar Ispat Pvt Ltd v. Union of India", "(2019) 14 SCC 982", "Supreme Court of India", "2019-04-12"),
            ("Bharat Heavy Engineering v. Global Finance Ltd", "2021 Comp Cas 441 (NCLAT)", "NCLAT New Delhi", "2021-08-19"),
            ("Sunil Aggarwal v. ROC Maharashtra", "(2020) 8 SCC 771", "Supreme Court of India", "2020-03-15"),
            ("TechVenture Logistics Ltd v. Apex Infotech", "2018 SCC OnLine NCLAT 902", "NCLAT New Delhi", "2018-11-20"),
            ("Kavita Singhania v. Northern Minerals Ltd", "(2022) 5 SCC 319", "Supreme Court of India", "2022-01-28"),
            ("Heritage Textiles Ltd v. State Bank of Patiala", "(2017) 11 SCC 604", "Supreme Court of India", "2017-06-14"),
            ("Vikas Pharma Ltd v. Serious Fraud Investigation Office", "2023 Comp Cas 112 (Del)", "High Court of Delhi", "2023-05-10"),
            ("Zenith Power Transmission v. Registrar of Companies", "(2016) 16 SCC 890", "Supreme Court of India", "2016-09-22"),
            ("Ananya Polymers Ltd v. Blue Chip Investments", "2020 SCC OnLine NCLAT 121", "NCLAT New Delhi", "2020-02-18"),
            ("Aditya Infrastructure Ltd v. Standard Chartered", "(2015) 12 SCC 450", "Supreme Court of India", "2015-10-09"),
            ("Omkar Marine Services v. Union of India", "(2021) 18 SCC 205", "Supreme Court of India", "2021-07-23"),
            ("Dhanraj Cotton Mills v. NCLT Mumbai Bench", "2019 Comp Cas 831 (Bom)", "High Court of Bombay", "2019-12-04"),
            ("Pravin Mehta v. Diamond Harbour Securities Ltd", "(2022) 9 SCC 114", "Supreme Court of India", "2022-09-17"),
            ("Alok Global Trading Ltd v. ROC Gujarat", "2018 SCC OnLine Guj 445", "High Court of Gujarat", "2018-04-30"),
            ("Suresh Chandra v. National Steels Corporation", "(2019) 17 SCC 512", "Supreme Court of India", "2019-11-11"),
            ("Navkar Synthetics Pvt Ltd v. Axis Bank Ltd", "2022 Comp Cas 601 (NCLAT)", "NCLAT New Delhi", "2022-03-08"),
            ("Deepak Fertilizer Holdings v. Official Liquidator", "(2014) 15 SCC 301", "Supreme Court of India", "2014-08-16"),
            ("Vanguard Real Estate Ltd v. ROC Chennai", "2021 SCC OnLine Mad 789", "High Court of Madras", "2021-06-25"),
            ("Prestige Autocars v. ICICI Bank Ltd", "(2023) 4 SCC 882", "Supreme Court of India", "2023-02-14"),
            ("Kailash Agro Products Ltd v. Union of India", "2017 Comp Cas 329 (NCLAT)", "NCLAT New Delhi", "2017-12-19")
        ]
        for name, cit, court, date in fabricated_cases:
            claim = f"As firmly held in {name}, {cit}, the tribunal has inherent power to grant unconditional interim stay on CIRP."
            records.append(CitationVerificationRecord(
                test_id=f"D3_CIT_{idx:06d}",
                benchmark_family="D3-E",
                claim=claim,
                cited_case_name=name,
                cited_citation=cit,
                cited_court=court,
                cited_date=date,
                cited_paragraph="14",
                expected_verification_status="REJECTED",
                failure_type="FABRICATED_CASE",
                real_source_ids=[],
                metadata_discrepancy_details=f"The case '{name}' does not exist in the authoritative judicial corpus or official law reporters.",
                difficulty="medium"
            ))
            idx += 1

        # Category 3: Fabricated Citations for Real Cases (20 records) -> FLAGGED
        for i, j in enumerate(all_judgments[20:40]):
            j_id = j["judgment_id"]
            title = j.get("case_title", "Unknown Case")
            court = j.get("court", "Supreme Court of India")
            date = j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01"
            fake_cit = f"(2035) {90 + i} SCC {1000 + i * 37}"

            claim = f"According to {title}, reported at {fake_cit}, corporate veil cannot be pierced without established fraud."
            records.append(CitationVerificationRecord(
                test_id=f"D3_CIT_{idx:06d}",
                benchmark_family="D3-E",
                claim=claim,
                cited_case_name=title,
                cited_citation=fake_cit,
                cited_court=court,
                cited_date=date,
                cited_paragraph="5",
                expected_verification_status="FLAGGED",
                failure_type="FABRICATED_CITATION",
                real_source_ids=[j_id],
                metadata_discrepancy_details=f"The case '{title}' is genuine, but the citation '{fake_cit}' is completely fictitious and unindexed.",
                difficulty="hard"
            ))
            idx += 1

        # Category 4: Non-Existent Paragraphs in Real Cases (20 records) -> REJECTED
        for i, j in enumerate(all_judgments[10:30]):
            j_id = j["judgment_id"]
            title = j.get("case_title", "Unknown Case")
            court = j.get("court", "Supreme Court of India")
            date = j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01"
            cits = self.corpus.get_d2_citations_for_judgment(j_id)
            cit_str = cits[0]["normalized_citation"] if cits else f"(2020) {i+1} SCC 100"
            passages = self.corpus.get_d2_passages_for_judgment(j_id)
            actual_max_para = len(passages) + 5
            ghost_para = str(actual_max_para + 450 + i * 15)

            claim = f"In {title}, {cit_str}, at paragraph {ghost_para}, the court observed that minority shareholder consent is strictly mandatory."
            records.append(CitationVerificationRecord(
                test_id=f"D3_CIT_{idx:06d}",
                benchmark_family="D3-E",
                claim=claim,
                cited_case_name=title,
                cited_citation=cit_str,
                cited_court=court,
                cited_date=date,
                cited_paragraph=ghost_para,
                expected_verification_status="REJECTED",
                failure_type="NON_EXISTENT_PARAGRAPH",
                real_source_ids=[j_id],
                metadata_discrepancy_details=f"Judgment '{title}' contains approximately {actual_max_para} paragraphs; cited paragraph {ghost_para} does not exist.",
                difficulty="adversarial"
            ))
            idx += 1

        return records

    # -------------------------------------------------------------------------
    # D3-F: Citation Metadata Mismatch
    # -------------------------------------------------------------------------
    def _generate_d3_f(self) -> List[CitationVerificationRecord]:
        records: List[CitationVerificationRecord] = []
        idx = 1
        all_judgments = list(self.corpus.d2_judgments.values())
        n = len(all_judgments)

        # 1. Citation Swaps (35 records) -> FLAGGED
        for i in range(35):
            j1 = all_judgments[i % n]
            j2 = all_judgments[(i + 7) % n]

            j1_id = j1["judgment_id"]
            j1_title = j1.get("case_title", "")
            j1_court = j1.get("court", "")
            j1_date = j1.get("date_of_judgment") or j1.get("decision_date") or "2020-01-01"

            j2_cits = self.corpus.get_d2_citations_for_judgment(j2["judgment_id"])
            swapped_cit = j2_cits[0]["normalized_citation"] if j2_cits else "(2019) 1 SCC 1"

            claim = f"In {j1_title}, reported at {swapped_cit}, the court settled the interpretation of Section 241."
            records.append(CitationVerificationRecord(
                test_id=f"D3_META_{idx:06d}",
                benchmark_family="D3-F",
                claim=claim,
                cited_case_name=j1_title,
                cited_citation=swapped_cit,
                cited_court=j1_court,
                cited_date=j1_date,
                cited_paragraph="8",
                expected_verification_status="FLAGGED",
                failure_type="CITATION_SWAP",
                real_source_ids=[j1_id, j2["judgment_id"]],
                metadata_discrepancy_details=f"Citation '{swapped_cit}' actually belongs to '{j2.get('case_title')}', not '{j1_title}'.",
                difficulty="hard"
            ))
            idx += 1

        # 2. Wrong Court Attributions (35 records) -> FLAGGED
        courts_cycle = [
            "High Court of Delhi",
            "Supreme Court of India",
            "National Company Law Appellate Tribunal (NCLAT)",
            "High Court of Bombay",
            "High Court of Madras"
        ]
        for i in range(35):
            j = all_judgments[(i + 12) % n]
            j_id = j["judgment_id"]
            title = j.get("case_title", "")
            real_court = j.get("court", "")
            date = j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01"
            cits = self.corpus.get_d2_citations_for_judgment(j_id)
            cit_str = cits[0]["normalized_citation"] if cits else f"[2021] INSC {i}"

            wrong_court = courts_cycle[i % len(courts_cycle)]
            if wrong_court.lower() in real_court.lower():
                wrong_court = "High Court of Calcutta"

            claim = f"The {wrong_court} in {title} ({cit_str}) ruled on director duties under Section 166."
            records.append(CitationVerificationRecord(
                test_id=f"D3_META_{idx:06d}",
                benchmark_family="D3-F",
                claim=claim,
                cited_case_name=title,
                cited_citation=cit_str,
                cited_court=wrong_court,
                cited_date=date,
                cited_paragraph="12",
                expected_verification_status="FLAGGED",
                failure_type="WRONG_COURT",
                real_source_ids=[j_id],
                metadata_discrepancy_details=f"Judgment was rendered by '{real_court}', not '{wrong_court}'.",
                difficulty="medium"
            ))
            idx += 1

        # 3. Wrong Date Attributions (30 records) -> FLAGGED
        for i in range(30):
            j = all_judgments[(i + 25) % n]
            j_id = j["judgment_id"]
            title = j.get("case_title", "")
            real_court = j.get("court", "")
            real_date = str(j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01")
            cits = self.corpus.get_d2_citations_for_judgment(j_id)
            cit_str = cits[0]["normalized_citation"] if cits else f"[2019] INSC {i}"

            year = int(real_date[:4]) if real_date[:4].isdigit() else 2020
            shifted_year = year - 12 if year > 2015 else year + 9
            wrong_date = f"{shifted_year}-05-20"

            claim = f"On {wrong_date}, in {title}, the court declared the resolution plan compliant with Section 30(2)."
            records.append(CitationVerificationRecord(
                test_id=f"D3_META_{idx:06d}",
                benchmark_family="D3-F",
                claim=claim,
                cited_case_name=title,
                cited_citation=cit_str,
                cited_court=real_court,
                cited_date=wrong_date,
                cited_paragraph="4",
                expected_verification_status="FLAGGED",
                failure_type="WRONG_DATE",
                real_source_ids=[j_id],
                metadata_discrepancy_details=f"The actual decision date for '{title}' is {real_date}, but the claim asserts {wrong_date}.",
                difficulty="medium"
            ))
            idx += 1

        return records

    # -------------------------------------------------------------------------
    # D3-G: Passage-Level Fabrication Benchmark
    # -------------------------------------------------------------------------
    def _generate_d3_g(self) -> List[PassageVerificationRecord]:
        records: List[PassageVerificationRecord] = []
        idx = 1

        all_passages = list(self.corpus.d2_passages.values())
        all_judgments = self.corpus.d2_judgments

        fab_props = [
            "The court held that directors cannot be held personally liable for any fraudulent misfeasance under Section 447",
            "The bench declared that board resolutions can be passed without any notice or explanatory statement to shareholders",
            "The tribunal held that private limited companies are completely exempt from maintaining books of account",
            "The judgment held that secured financial creditors have zero priority over unsecured creditors during liquidation",
            "The court ruled that an audit report signed by a disqualified auditor remains fully valid and legally binding",
            "The bench held that compounding of corporate offences is prohibited in all circumstances under the Companies Act",
            "The court declared that all registered charges are void ab initio if not registered within 24 hours",
            "The court ruled that a single minority shareholder holding 1 share has absolute right to unilaterally block any merger",
            "The bench held that independent directors are legally entitled to receive 50% profit commission without board approval",
            "The court held that National Company Law Tribunal has no jurisdiction whatsoever to entertain claims of oppression"
        ]

        for pas in all_passages:
            doc_id = pas.get("document_id")
            if not doc_id or doc_id not in all_judgments:
                continue
            j = all_judgments[doc_id]
            title = j.get("case_title", "")
            cits = self.corpus.get_d2_citations_for_judgment(doc_id)
            cit_str = cits[0]["normalized_citation"] if cits else "(2021) SCC OnLine SC 100"
            pas_text = pas.get("text") or pas.get("passage_text") or ""
            if len(pas_text) < 50:
                continue

            prop = fab_props[(idx - 1) % len(fab_props)]
            claim = f"In {title} ({cit_str}, passage {pas['passage_id']}), the court established that {prop.lower()}."

            records.append(PassageVerificationRecord(
                test_id=f"D3_PAS_{idx:06d}",
                benchmark_family="D3-G",
                claim=claim,
                cited_case_name=title,
                cited_citation=cit_str,
                cited_court=j.get("court", "Supreme Court of India"),
                cited_date=str(j.get("date_of_judgment") or j.get("decision_date") or "2020-01-01"),
                cited_passage_id=pas["passage_id"],
                cited_passage_text=pas_text[:400],
                fabricated_proposition=prop,
                expected_verification_status="PASSAGE_UNSUPPORTED",
                failure_type="UNSUPPORTED_PROPOSITION",
                real_source_ids=[doc_id, pas["passage_id"]],
                difficulty="adversarial"
            ))
            idx += 1
            if len(records) >= 100:
                break

        return records
