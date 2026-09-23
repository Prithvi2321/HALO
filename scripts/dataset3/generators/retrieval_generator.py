"""
Retrieval Benchmark Generators for HALO Dataset 3
=================================================
Implements:
  - D3-A: Direct Statutory & Case Retrieval (Exact & Interpreted)
  - D3-B: Paraphrased & Semantic Retrieval
  - D3-C: Hard Negative Retrieval
"""

import re
from typing import List, Dict, Any
from ..models import RetrievalRecord
from ..evidence_loader import get_corpus
from ..split_manager import get_split_manager


class RetrievalGenerator:
    def __init__(self):
        self.corpus = get_corpus()
        self.split_mgr = get_split_manager()

    def generate_all(self) -> List[RetrievalRecord]:
        records: List[RetrievalRecord] = []
        rec_idx = 1

        print("[*] [RetrievalGenerator] Generating D3-A: Direct Statutory & Case Retrieval...")
        d3_a_records = self._generate_d3_a(start_idx=rec_idx)
        records.extend(d3_a_records)
        rec_idx += len(d3_a_records)
        print(f"    [+] Generated {len(d3_a_records)} D3-A records.")

        print("[*] [RetrievalGenerator] Generating D3-B: Paraphrased & Semantic Retrieval...")
        d3_b_records = self._generate_d3_b(start_idx=rec_idx)
        records.extend(d3_b_records)
        rec_idx += len(d3_b_records)
        print(f"    [+] Generated {len(d3_b_records)} D3-B records.")

        print("[*] [RetrievalGenerator] Generating D3-C: Hard Negative Retrieval...")
        d3_c_records = self._generate_d3_c(start_idx=rec_idx)
        records.extend(d3_c_records)
        rec_idx += len(d3_c_records)
        print(f"    [+] Generated {len(d3_c_records)} D3-C records.")

        return records

    # -------------------------------------------------------------------------
    # D3-A: Direct Statutory & Case Retrieval
    # -------------------------------------------------------------------------
    def _generate_d3_a(self, start_idx: int) -> List[RetrievalRecord]:
        records = []
        idx = start_idx

        # 1. Statutory Provisions (Dataset 1)
        for sec_id, sec in sorted(self.corpus.d1_sections.items()):
            sec_num = sec["section_number"]
            heading = sec.get("heading", "")
            can_text = sec.get("canonical_text", "")
            sec_passages = self.corpus.d1_section_passages.get(sec_id, [])
            if not sec_passages:
                continue

            primary_pas = sec_passages[0]
            pid = primary_pas["passage_id"]
            split = self.split_mgr.get_section_split(sec_id)

            # Query Template 1: Direct statutory lookup
            q1 = f"What does Section {sec_num} of the Companies Act, 2013 prescribe regarding {heading.lower()}?"
            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-A",
                query=q1,
                query_type="STATUTORY_LOOKUP",
                difficulty="easy",
                source_scope=["dataset1"],
                positive_evidence_ids=[sec_id],
                relevant_document_ids=["ACT_COMPANIES_2013"],
                relevant_passage_ids=[p["passage_id"] for p in sec_passages[:2]],
                dataset_source="dataset1",
                evidence_text=primary_pas.get("canonical_text", "")[:400],
                evidence_type="statute",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

            # Query Template 2: Substantive requirement query for major sections
            if any(kw in heading.lower() for kw in ["director", "audit", "share", "meeting", "penalty", "resolution", "csr", "merger", "oppression"]):
                q2 = f"Under the Companies Act, 2013, what are the statutory obligations and legal requirements concerning {heading.lower()}?"
                records.append(RetrievalRecord(
                    query_id=f"D3_RET_{idx:06d}",
                    benchmark_family="D3-A",
                    query=q2,
                    query_type="STATUTORY_INTERPRETATION",
                    difficulty="medium",
                    source_scope=["dataset1"],
                    positive_evidence_ids=[sec_id],
                    relevant_document_ids=["ACT_COMPANIES_2013"],
                    relevant_passage_ids=[pid],
                    dataset_source="dataset1",
                    evidence_text=primary_pas.get("canonical_text", "")[:400],
                    evidence_type="statute",
                    annotation_status="VALIDATED",
                    split=split
                ))
                idx += 1

            if len(records) >= 170:
                break

        # 2. Judicial Holdings (Dataset 2)
        for j_id, j in sorted(self.corpus.d2_judgments.items()):
            case_title = j.get("case_title", "")
            court = j.get("court", "").replace("_", " ").title()
            citations = j.get("citations", [])
            cit_str = citations[0] if citations else "the judgment"
            j_passages = self.corpus.d2_judgment_passages.get(j_id, [])
            if not j_passages:
                continue

            primary_pas = j_passages[0]
            pid = primary_pas["passage_id"]
            split = self.split_mgr.get_judgment_split(j_id)
            topics = j.get("topic_classification", ["Corporate Law"])
            topic_str = topics[0] if topics else "Corporate Law"

            q_case = f"What was held by the {court} in {case_title} regarding {topic_str.lower()}?"
            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-A",
                query=q_case,
                query_type="CASE_HOLDING",
                difficulty="medium",
                source_scope=["dataset2"],
                positive_evidence_ids=[j_id],
                relevant_document_ids=[j_id],
                relevant_passage_ids=[p["passage_id"] for p in j_passages[:2]],
                dataset_source="dataset2",
                evidence_text=primary_pas.get("text", "")[:400],
                evidence_type="judgment",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

        return records

    # -------------------------------------------------------------------------
    # D3-B: Paraphrased & Semantic Retrieval
    # -------------------------------------------------------------------------
    def _generate_d3_b(self, start_idx: int) -> List[RetrievalRecord]:
        records = []
        idx = start_idx

        # Handcrafted high-value legal semantic equivalences mapped directly to Dataset 1 & 2
        semantic_pairs = [
            # Oppression & Mismanagement
            {
                "query": "What judicial remedies exist when controlling shareholders conduct business prejudicially against minority stakeholders?",
                "sec_id": "ACT_COMPANIES_2013_SEC_241",
                "topics": ["oppression and mismanagement", "tribunal application"]
            },
            {
                "query": "What relief can the NCLT grant to terminate an oppressive agreement entered into by board members?",
                "sec_id": "ACT_COMPANIES_2013_SEC_242",
                "topics": ["powers of tribunal", "relief against mismanagement"]
            },
            # CSR & Philanthropy
            {
                "query": "Which corporate entities are statutorily required to allocate earnings towards social development initiatives?",
                "sec_id": "ACT_COMPANIES_2013_SEC_135",
                "topics": ["corporate social responsibility", "mandatory spend"]
            },
            # Registration of Charges
            {
                "query": "What consequences follow if a corporate debtor fails to notify encumbrances or security interests to the government registry?",
                "sec_id": "ACT_COMPANIES_2013_SEC_86",
                "topics": ["punishment for contravention", "failure to register charges"]
            },
            # Independent Directors
            {
                "query": "What qualifications and integrity criteria must an outside non-executive board member satisfy to maintain disinterested status?",
                "sec_id": "ACT_COMPANIES_2013_SEC_149",
                "topics": ["independent directors", "criteria of independence"]
            },
            # Related Party Transactions
            {
                "query": "When does a contract between an enterprise and its affiliated entities require formal audit committee and shareholder sanction?",
                "sec_id": "ACT_COMPANIES_2013_SEC_188",
                "topics": ["related party transactions", "board approval"]
            },
            # Disqualification of Directors
            {
                "query": "Under what statutory conditions is an individual debarred from serving on a corporate board for default in financial statement filings?",
                "sec_id": "ACT_COMPANIES_2013_SEC_164",
                "topics": ["disqualifications for appointment of director"]
            },
            # Vacation of Office
            {
                "query": "When is a director deemed to have automatically surrendered their directorship due to continuous absence from board meetings?",
                "sec_id": "ACT_COMPANIES_2013_SEC_167",
                "topics": ["vacation of office of director"]
            },
            # Fraud & Serious Fraud Investigation
            {
                "query": "What statutory powers allow central investigators to probe affairs of a corporation involving deceit and injury to public interest?",
                "sec_id": "ACT_COMPANIES_2013_SEC_212",
                "topics": ["investigation into affairs of company by sfio"]
            },
            {
                "query": "What criminal and monetary punishment is imposed for acts of deception or concealment resulting in wrongful gain under company law?",
                "sec_id": "ACT_COMPANIES_2013_SEC_447",
                "topics": ["punishment for fraud"]
            },
            # Share Capital & Reduction
            {
                "query": "How may a company limited by shares extinguish or diminish paid-up capital subject to judicial confirmation?",
                "sec_id": "ACT_COMPANIES_2013_SEC_66",
                "topics": ["reduction of share capital"]
            },
            # Auditor Duties & Resignation
            {
                "query": "What procedural notifications must an independent statutory auditor file upon relinquishing their professional audit mandate before term completion?",
                "sec_id": "ACT_COMPANIES_2013_SEC_140",
                "topics": ["removal, resignation of auditor"]
            },
            # Execution of Deeds & Common Seal
            {
                "query": "Can a modern commercial firm bind itself through executed deeds without affixing an official mechanical stamp?",
                "sec_id": "ACT_COMPANIES_2013_SEC_22",
                "topics": ["execution of bills of exchange", "common seal optionality"]
            },
            # Producer Companies
            {
                "query": "What are the permissible corporate objectives for forming an agricultural cooperative producer entity under company legislation?",
                "sec_id": "ACT_COMPANIES_2013_SEC_378B",
                "topics": ["objects of producer company"]
            }
        ]

        # Generate semantic records across the curated list plus programmatic semantic paraphrases
        for p_info in semantic_pairs:
            sec_id = p_info["sec_id"]
            sec = self.corpus.get_d1_section(sec_id)
            if not sec:
                continue
            sec_passages = self.corpus.d1_section_passages.get(sec_id, [])
            if not sec_passages:
                continue
            split = self.split_mgr.get_section_split(sec_id)

            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-B",
                query=p_info["query"],
                query_type="PARAPHRASED_SEMANTIC",
                difficulty="medium",
                source_scope=["dataset1"],
                positive_evidence_ids=[sec_id],
                relevant_document_ids=["ACT_COMPANIES_2013"],
                relevant_passage_ids=[sec_passages[0]["passage_id"]],
                dataset_source="dataset1",
                evidence_text=sec_passages[0].get("canonical_text", "")[:400],
                evidence_type="statute",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

        # Extend with judicial semantic reformulations
        for j_id, j in sorted(self.corpus.d2_judgments.items()):
            case_title = j.get("case_title", "")
            j_passages = self.corpus.d2_judgment_passages.get(j_id, [])
            if not j_passages:
                continue
            split = self.split_mgr.get_judgment_split(j_id)
            topics = j.get("topic_classification", [])
            t_str = topics[0] if topics else "statutory interpretation"

            # Create conceptual natural language query
            q_semantic = f"In the judicial dispute involving {case_title.split(' v. ')[0]}, how did the bench rule on principles of {t_str.lower()}?"
            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-B",
                query=q_semantic,
                query_type="PARAPHRASED_SEMANTIC",
                difficulty="hard",
                source_scope=["dataset2"],
                positive_evidence_ids=[j_id],
                relevant_document_ids=[j_id],
                relevant_passage_ids=[j_passages[0]["passage_id"]],
                dataset_source="dataset2",
                evidence_text=j_passages[0].get("text", "")[:400],
                evidence_type="judgment",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

        # Extend with conceptual statutory inquiries to reach 100 records
        for sec_id, sec in sorted(self.corpus.d1_sections.items()):
            if len(records) >= 100:
                break
            heading = sec.get("heading", "")
            passages = self.corpus.d1_section_passages.get(sec_id, [])
            if not passages or len(heading) < 5:
                continue
            split = self.split_mgr.get_section_split(sec_id)
            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-B",
                query=f"Under Indian company law jurisprudence, what are the overarching statutory mandates and compliance mechanisms regarding {heading.lower()}?",
                query_type="PARAPHRASED_SEMANTIC",
                difficulty="medium",
                source_scope=["dataset1"],
                positive_evidence_ids=[sec_id],
                relevant_document_ids=["ACT_COMPANIES_2013"],
                relevant_passage_ids=[passages[0]["passage_id"]],
                dataset_source="dataset1",
                evidence_text=passages[0].get("canonical_text", "")[:400],
                evidence_type="statute",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

        return records

    # -------------------------------------------------------------------------
    # D3-C: Hard Negative Retrieval
    # -------------------------------------------------------------------------
    def _generate_d3_c(self, start_idx: int) -> List[RetrievalRecord]:
        records = []
        idx = start_idx

        # Hard negative pairs: positive section vs authentic adjacent/confounding section
        confounding_pairs = [
            # Vacation of office (167) vs Disqualification of directors (164)
            {
                "query": "Which provision governs the automatic vacation of office by a director who absents himself from all Board meetings held during a twelve-month period?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_167",
                "neg_sec": "ACT_COMPANIES_2013_SEC_164",
                "reason": "Section 164 deals with pre-appointment or annual disqualification, while Section 167 specifically triggers automatic vacation during tenure for absence."
            },
            # Penalty for contravention of charges (86) vs Duty to register charges (77)
            {
                "query": "What specific monetary fines are imposed on a company and its officers in default for failing to register a charge created on its property?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_86",
                "neg_sec": "ACT_COMPANIES_2013_SEC_77",
                "reason": "Section 77 establishes the 30-day registration duty, but the penal fine amounts (up to 5 lakh rupees) are codified in Section 86."
            },
            # CSR Obligations (135) vs Board Report CSR Disclosures (134)
            {
                "query": "What financial thresholds of net worth, turnover, or net profit mandate the establishment of a Corporate Social Responsibility committee?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_135",
                "neg_sec": "ACT_COMPANIES_2013_SEC_134",
                "reason": "Section 134(3)(o) references CSR disclosures in directors' reports, but the 500 cr / 1000 cr / 5 cr eligibility thresholds exist exclusively in Section 135(1)."
            },
            # Oppression & Mismanagement application (241) vs Powers of Tribunal (242)
            {
                "query": "What specific remedial orders may the Tribunal issue to regulate the future conduct of a company suffering from oppressive conduct?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_242",
                "neg_sec": "ACT_COMPANIES_2013_SEC_241",
                "reason": "Section 241 specifies who can apply for relief, whereas Section 242 details the substantive catalogue of orders the Tribunal can enact."
            },
            # General Fraud Punishment (447) vs Misstatement in Prospectus (34/35)
            {
                "query": "What is the overarching punishment of imprisonment and fine for any corporate fraud involving sums of at least ten lakh rupees or one percent of turnover?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_447",
                "neg_sec": "ACT_COMPANIES_2013_SEC_34",
                "reason": "Section 34 imposes criminal liability for misstatements in prospectus by referring to Section 447, but the term of imprisonment (6 months to 10 years) is set in Section 447."
            },
            # Appointment of Auditors (139) vs Removal/Resignation of Auditors (140)
            {
                "query": "What special resolution and central government approval is required to remove a statutory auditor prior to the expiration of their five-year tenure?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_140",
                "neg_sec": "ACT_COMPANIES_2013_SEC_139",
                "reason": "Section 139 governs initial and reappointment tenure, while premature dismissal is strictly governed by Section 140(1)."
            },
            # Prohibition of Insider Trading (repealed/transferred) vs Related Party (188)
            {
                "query": "What requirements govern entering into a contract with an associate or subsidiary company for the lease of property exceeding prescribed thresholds?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_188",
                "neg_sec": "ACT_COMPANIES_2013_SEC_185",
                "reason": "Section 185 restricts loans to directors, whereas Section 188 explicitly regulates commercial leasing contracts with related corporate entities."
            },
            # Registered Office Change (12) vs Alteration of Memorandum (13)
            {
                "query": "What procedure applies when a company changes its registered office outside the local limits of any city, town or village but within the same State?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_12",
                "neg_sec": "ACT_COMPANIES_2013_SEC_13",
                "reason": "Section 13 governs alteration of the domicile clause across State boundaries, whereas intra-state relocation outside local limits is governed by Section 12(5)."
            },
            # Compounding of Offences (441) vs Adjudication of Penalties (454)
            {
                "query": "Which forum possesses statutory power to compound non-imprisonment corporate offences punishable with fine only up to twenty-five lakh rupees?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_441",
                "neg_sec": "ACT_COMPANIES_2013_SEC_454",
                "reason": "Section 454 governs in-house adjudication of civil penalties by Adjudicating Officers, while criminal compounding is exercised by the Regional Director under Section 441."
            },
            # Investigation into affairs (210) vs Serious Fraud Investigation (212)
            {
                "query": "Under what circumstances may the Central Government assign the investigation into a company's affairs specifically to the Serious Fraud Investigation Office?",
                "pos_sec": "ACT_COMPANIES_2013_SEC_212",
                "neg_sec": "ACT_COMPANIES_2013_SEC_210",
                "reason": "Section 210 provides general inspection powers to ROC inspectors, whereas Section 212 exclusively governs SFIO assignment on grounds of public interest or complexity."
            }
        ]

        for p_info in confounding_pairs:
            pos_sec_id = p_info["pos_sec"]
            neg_sec_id = p_info["neg_sec"]
            pos_sec = self.corpus.get_d1_section(pos_sec_id)
            neg_sec = self.corpus.get_d1_section(neg_sec_id)
            if not pos_sec or not neg_sec:
                continue

            pos_passages = self.corpus.d1_section_passages.get(pos_sec_id, [])
            neg_passages = self.corpus.d1_section_passages.get(neg_sec_id, [])
            if not pos_passages or not neg_passages:
                continue

            split = self.split_mgr.get_section_split(pos_sec_id)

            records.append(RetrievalRecord(
                query_id=f"D3_RET_{idx:06d}",
                benchmark_family="D3-C",
                query=p_info["query"],
                query_type="HARD_NEGATIVE",
                difficulty="hard",
                source_scope=["dataset1"],
                positive_evidence_ids=[pos_sec_id],
                relevant_document_ids=["ACT_COMPANIES_2013"],
                relevant_passage_ids=[pos_passages[0]["passage_id"]],
                hard_negative_passage_ids=[neg_passages[0]["passage_id"]],
                negative_reason=p_info["reason"],
                dataset_source="dataset1",
                evidence_text=pos_passages[0].get("canonical_text", "")[:400],
                evidence_type="statute",
                annotation_status="VALIDATED",
                split=split
            ))
            idx += 1

        # Synthesize additional hard negatives from adjacent sections within each chapter
        for ch in self.corpus.d1_act.get("chapters", []):
            sec_list = ch.get("sections", [])
            if len(sec_list) >= 2:
                for i in range(len(sec_list) - 1):
                    s1 = sec_list[i]
                    s2 = sec_list[i + 1]
                    s1_id = s1["section_id"]
                    s2_id = s2["section_id"]
                    s1_pass = self.corpus.d1_section_passages.get(s1_id, [])
                    s2_pass = self.corpus.d1_section_passages.get(s2_id, [])
                    if not s1_pass or not s2_pass:
                        continue

                    split = self.split_mgr.get_section_split(s1_id)
                    q = f"Which provision under Chapter {ch.get('chapter_number')} specifically regulates {s1.get('heading', '').lower()} rather than {s2.get('heading', '').lower()}?"
                    records.append(RetrievalRecord(
                        query_id=f"D3_RET_{idx:06d}",
                        benchmark_family="D3-C",
                        query=q,
                        query_type="HARD_NEGATIVE",
                        difficulty="hard",
                        source_scope=["dataset1"],
                        positive_evidence_ids=[s1_id],
                        relevant_document_ids=["ACT_COMPANIES_2013"],
                        relevant_passage_ids=[s1_pass[0]["passage_id"]],
                        hard_negative_passage_ids=[s2_pass[0]["passage_id"]],
                        negative_reason=f"Adjacent provision in Chapter {ch.get('chapter_number')} covering {s2.get('heading')} rather than {s1.get('heading')}.",
                        dataset_source="dataset1",
                        evidence_text=s1_pass[0].get("canonical_text", "")[:400],
                        evidence_type="statute",
                        annotation_status="VALIDATED",
                        split=split
                    ))
                    idx += 1
                    if len(records) >= 100:
                        break
            if len(records) >= 100:
                break

        return records
