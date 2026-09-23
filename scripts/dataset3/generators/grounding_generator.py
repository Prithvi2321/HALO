"""
Grounded Answer Benchmark Generator for HALO Dataset 3 (D3-D)
=============================================================
Creates evaluation records with atomic acceptable points and negative claim boundaries.
"""

from typing import List
from ..models import GroundingRecord
from ..evidence_loader import get_corpus


class GroundingGenerator:
    def __init__(self):
        self.corpus = get_corpus()

    def generate_all(self) -> List[GroundingRecord]:
        records: List[GroundingRecord] = []
        idx = 1

        print("[*] [GroundingGenerator] Generating D3-D: Grounded Answer Benchmark...")

        grounding_data = [
            # 1. Section 135 - CSR
            {
                "query": "What are the eligibility criteria and minimum expenditure requirements for Corporate Social Responsibility under Section 135?",
                "gold_answer": "Under Section 135(1) of the Companies Act, 2013, every company having a net worth of rupees 500 crore or more, or turnover of rupees 1,000 crore or more, or net profit of rupees 5 crore or more during the immediately preceding financial year must constitute a CSR Committee. Under Section 135(5), the Board must ensure that the company spends, in every financial year, at least two per cent of the average net profits made during the three immediately preceding financial years in pursuance of its CSR Policy.",
                "points": [
                    "Net worth of rupees 500 crore or more",
                    "Turnover of rupees 1,000 crore or more",
                    "Net profit of rupees 5 crore or more during immediately preceding financial year",
                    "Mandatory spend of at least 2% of average net profits of preceding three financial years"
                ],
                "unacceptable": [
                    "CSR spend is optional for companies above 1,000 crore turnover",
                    "Threshold is based on paid-up capital of 100 crore",
                    "Expenditure requirement is 5% of net profit"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_135",
                "source": "dataset1",
                "difficulty": "medium"
            },
            # 2. Section 86 - Penalty for Failure to Register Charge
            {
                "query": "What are the statutory penalties for defaulting in registering a charge under Chapter VI of the Companies Act, 2013?",
                "gold_answer": "Under Section 86(1) of the Companies Act, 2013, if any company defaults in complying with any provisions of Chapter VI regarding registration of charges, the company is liable to a penalty of five lakh rupees and every officer of the company who is in default is liable to a penalty of fifty thousand rupees. Under Section 86(2), willfully furnishing false information triggers liability for fraud under Section 447.",
                "points": [
                    "Company penalty of five lakh rupees (₹5,00,000)",
                    "Officer in default penalty of fifty thousand rupees (₹50,000)",
                    "Willfully furnishing false information triggers action under Section 447"
                ],
                "unacceptable": [
                    "Company penalty is ten lakh rupees",
                    "Officers are exempted from monetary penalty",
                    "Offence results in mandatory minimum 3 years imprisonment"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_86",
                "source": "dataset1",
                "difficulty": "easy"
            },
            # 3. Section 149 - Independent Directors Criteria
            {
                "query": "What pecuniary relationship restrictions apply to an independent director under Section 149(6)?",
                "gold_answer": "Under Section 149(6)(c) of the Companies Act, 2013, an independent director must not have or have had any pecuniary relationship, other than remuneration as such director or having transaction not exceeding ten per cent of his total income or such amount as may be prescribed, with the company, its holding, subsidiary or associate company, or their promoters or directors, during the two immediately preceding financial years or during the current financial year.",
                "points": [
                    "No pecuniary relationship other than permissible director remuneration",
                    "Exemption for transactions not exceeding ten per cent of total income",
                    "Restriction covers company, holding, subsidiary, associate, and their promoters/directors",
                    "Applies during two immediately preceding financial years and current financial year"
                ],
                "unacceptable": [
                    "Directors can hold any commercial relationship with holding company up to 50%",
                    "Restriction applies only to the current financial year"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_149",
                "source": "dataset1",
                "difficulty": "hard"
            },
            # 4. Section 241/242 - Oppression and Mismanagement Relief
            {
                "query": "What specific conditions must be shown to obtain relief from the Tribunal under Section 241 and 242 for oppression and mismanagement?",
                "gold_answer": "Under Section 241, an applicant member must establish that the company's affairs have been or are being conducted in a manner prejudicial to public interest, or oppressive to any member or members, or prejudicial to the interests of the company. Under Section 242(1)(b), the Tribunal must be satisfied that winding up the company would unfairly prejudice such members, but that the facts otherwise justify making a winding-up order on just and equitable grounds.",
                "points": [
                    "Affairs conducted in manner prejudicial to public interest or oppressive to members",
                    "Winding up the company would unfairly prejudice the oppressed members",
                    "Facts justify making a winding up order on just and equitable grounds"
                ],
                "unacceptable": [
                    "Tribunal will always wind up the company whenever oppression is claimed",
                    "Only majority shareholders holding 75% can apply under Section 241"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_241",
                "source": "dataset1",
                "difficulty": "hard"
            },
            # 5. Section 22 - Execution of Deeds without Common Seal
            {
                "query": "How can a company legally execute deeds, bills of exchange, and contracts under Section 22 if it does not maintain a common seal?",
                "gold_answer": "Pursuant to the amendment by Act 21 of 2015 to Section 22(2) and its proviso, a company may execute a deed under its common seal, if any. Where the company does not have a common seal, the authorization may be signed by two directors, or by a director and the Company Secretary, wherever the company has appointed a Company Secretary.",
                "points": [
                    "Common seal is optional ('under its common seal, if any')",
                    "In absence of seal, execution may be signed by two directors",
                    "Alternatively, execution may be signed by one director and the Company Secretary"
                ],
                "unacceptable": [
                    "Every Indian company is mandatorily required to maintain a physical common seal",
                    "A deed without a common seal is void ab initio regardless of director signatures"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_22",
                "source": "dataset1",
                "difficulty": "easy"
            },
            # 6. Section 188 - Related Party Transactions Approval
            {
                "query": "When is prior shareholder approval required for related party transactions under Section 188?",
                "gold_answer": "Under Section 188(1) second proviso, no contract or arrangement exceeding prescribed monetary thresholds or in the case of a company having paid-up capital not less than prescribed limits shall be entered into except with the prior approval of the company by resolution. Under the third proviso, prior approval does not apply to transactions entered into in the ordinary course of business on an arm's length basis.",
                "points": [
                    "Prior resolution of shareholders required for transactions exceeding prescribed limits",
                    "Exemption for transactions in the ordinary course of business",
                    "Exemption requires the transaction to be on an arm's length basis"
                ],
                "unacceptable": [
                    "All related party transactions require prior central government approval",
                    "Arm's length transactions still require mandatory shareholder resolution"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_188",
                "source": "dataset1",
                "difficulty": "medium"
            },
            # 7. Section 76A - Punishment for Illegal Deposits
            {
                "query": "What are the criminal and monetary consequences for accepting deposits in violation of Section 73 or 76?",
                "gold_answer": "Under Section 76A, where a company accepts or invites deposits in contravention of Section 73 or 76, the company is punishable with a fine of not less than one crore rupees or twice the amount of deposit accepted, whichever is lower, which may extend to ten crore rupees. Every officer in default is punishable with imprisonment which may extend to seven years and with fine not less than twenty-five lakh rupees up to two crore rupees.",
                "points": [
                    "Company fine not less than one crore rupees or twice deposit amount (up to ten crore rupees)",
                    "Officer in default imprisonment up to seven years",
                    "Officer in default fine not less than twenty-five lakh rupees up to two crore rupees"
                ],
                "unacceptable": [
                    "Illegal deposits are non-cognizable civil infractions without imprisonment",
                    "Company fine cannot exceed ten lakh rupees"
                ],
                "sec_id": "ACT_COMPANIES_2013_SEC_76A",
                "source": "dataset1",
                "difficulty": "medium"
            },
            # 8. Judicial Case - Tata Consultancy Services v. Vishal Ghisulal Jain
            {
                "query": "What was the Supreme Court's ruling in Tata Consultancy Services Limited v. Vishal Ghisulal Jain regarding NCLT's jurisdiction over contractual termination?",
                "gold_answer": "In Tata Consultancy Services Limited v. Vishal Ghisulal Jain, the Supreme Court held that the NCLT does not have jurisdiction under Section 60(5)(c) of the IBC to adjudicate upon contractual disputes arising outside the insolvency process or restrain termination of a commercial contract that is based on pre-insolvency contractual defaults, unless the termination is solely motivated by the initiation of CIRP.",
                "points": [
                    "NCLT cannot adjudicate purely contractual disputes under Section 60(5)(c)",
                    "Termination based on grounds independent of the insolvency process is valid",
                    "NCLT cannot restrain termination unless termination is solely motivated by the commencement of CIRP"
                ],
                "unacceptable": [
                    "NCLT possesses unlimited power to stay all contractual terminations during moratorium",
                    "Section 14 of IBC nullifies all termination clauses permanently"
                ],
                "judgment_id": "JUD-SC-2021-2021_10_1080_1103",
                "source": "dataset2",
                "difficulty": "hard"
            },
            # 9. Judicial Case - Mobilox Innovations v. Kirusa Software
            {
                "query": "What standard of 'pre-existing dispute' did the Supreme Court establish in Mobilox Innovations v. Kirusa Software?",
                "gold_answer": "In Mobilox Innovations v. Kirusa Software, the Supreme Court established that the adjudicating authority under Section 9 of the IBC must reject an application if a genuine, non-frivolous pre-existing dispute exists prior to the demand notice. The court held that the Tribunal must not examine the merits of the dispute or whether the defence is likely to succeed, but merely verify that the dispute is not spurious, hypothetical, or illusory.",
                "points": [
                    "Adjudicating authority must reject Section 9 application if a pre-existing dispute exists",
                    "Dispute must exist prior to the receipt of the demand notice under Section 8",
                    "Tribunal does not decide the merits of the dispute",
                    "Plausible contention that requires further investigation suffices; defence must not be spurious"
                ],
                "unacceptable": [
                    "Tribunal must conduct a full evidentiary trial to decide who owes the debt",
                    "A dispute raised for the first time in response to the Section 8 notice constitutes a pre-existing dispute"
                ],
                "judgment_id": "JUD-SC-2017-2017_10_1006_1072",
                "source": "dataset2",
                "difficulty": "hard"
            },
            # 10. Judicial Case - Bhushan Power & Steel v. S.L. Seal
            {
                "query": "What did the Supreme Court hold in Bhushan Power & Steel v. S.L. Seal regarding the effect of Section 10A of the amended MMDR Act on state recommendations?",
                "gold_answer": "In Bhushan Power & Steel Limited v. S.L. Seal, the Supreme Court held that prior recommendation letters issued by a State Government to the Central Government did not constitute a 'Letter of Intent' within the meaning of Section 10A(2)(c) of the amended MMDR Act, 2015. Consequently, all pending mining lease applications where previous Central Government approval had not been finalized stood lapsed and ineligible under Section 10A(1).",
                "points": [
                    "State Government recommendation does not constitute a Letter of Intent under Section 10A(2)(c)",
                    "Previous approval of Central Government was mandatory to create vested rights",
                    "Pending applications without finalized Central Government approval lapsed under amended Section 10A"
                ],
                "unacceptable": [
                    "State recommendation permanently vests a legal entitlement to execute a mining lease",
                    "The 2015 Amendment Act protected all informal MoUs entered into by State authorities"
                ],
                "judgment_id": "JUD-SC-2016-2016_11_149_171",
                "source": "dataset2",
                "difficulty": "hard"
            }
        ]

        for item in grounding_data:
            if item["source"] == "dataset1":
                sec_id = item["sec_id"]
                passages = self.corpus.d1_section_passages.get(sec_id, [])
                req_pids = [passages[0]["passage_id"]] if passages else [f"PAS_{sec_id}"]
            else:
                j_id = item["judgment_id"]
                passages = self.corpus.d2_judgment_passages.get(j_id, [])
                req_pids = [passages[0]["passage_id"]] if passages else [f"PAS-{j_id}-P001"]

            records.append(GroundingRecord(
                query_id=f"D3_GROUND_{idx:06d}",
                benchmark_family="D3-D",
                query=item["query"],
                gold_answer=item["gold_answer"],
                acceptable_answer_points=item["points"],
                unacceptable_claims=item["unacceptable"],
                required_evidence_ids=req_pids,
                source_dataset=item["source"],
                difficulty=item["difficulty"],
                split="test"
            ))
            idx += 1

        # Synthesize additional grounded records to reach target volume (100 records)
        for sec_id, sec in sorted(self.corpus.d1_sections.items()):
            sec_num = sec["section_number"]
            heading = sec.get("heading", "")
            can_text = sec.get("canonical_text", "")
            passages = self.corpus.d1_section_passages.get(sec_id, [])
            if not passages or len(can_text) < 150:
                continue

            # Synthesize grounded QA based on clean statutory provisions
            q = f"What are the statutory provisions governing {heading.lower()} under Section {sec_num} of the Companies Act, 2013?"
            first_sent = can_text.split(".")[0] + "."
            second_sent = can_text.split(".")[1] + "." if "." in can_text[len(first_sent):] else first_sent

            records.append(GroundingRecord(
                query_id=f"D3_GROUND_{idx:06d}",
                benchmark_family="D3-D",
                query=q,
                gold_answer=f"Under Section {sec_num} ({heading}) of the Companies Act, 2013: {first_sent.strip()} {second_sent.strip()}",
                acceptable_answer_points=[
                    f"Core mandate of Section {sec_num} regarding {heading.lower()}",
                    f"Compliance terms as codified in {first_sent.strip()[:100]}"
                ],
                unacceptable_claims=[
                    f"Section {sec_num} does not apply to registered companies",
                    f"Section {sec_num} has been repealed by the 2015 Amendment Act"
                ],
                required_evidence_ids=[passages[0]["passage_id"]],
                source_dataset="dataset1",
                difficulty="medium",
                split="test"
            ))
            idx += 1
            if len(records) >= 100:
                break

        print(f"    [+] Generated {len(records)} D3-D Grounded Answer records.")
        return records
