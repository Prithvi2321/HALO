"""
Independent Legal Verification Benchmark Builder (110+ Items)
=============================================================
Role     : Independent External Legal AI Evaluation Auditor & Benchmarking Specialist
           (Authored independently from the core HALO verifier development team to prevent
            developer bias, rule overfitting, and regular expression leakage).
Protocol : INDEPENDENT-TEST-v1.0
Target   : 110+ authoritative test verification cases covering positive controls, factual
           inversions, numerical alterations, modality shifts, citation existence/metadata traps,
           temporal amendments, compound propositions, and fail-closed refusal probes.
Corpora  : Strictly grounded in Dataset 1 (Companies Act 2013) and Dataset 2 (SC/NCLAT Judgments).
"""

import os
import sys
import json
import hashlib
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
D1_PASSAGES = os.path.join(BASE_DIR, "data", "dataset_1", "final", "companies_act_2013_passages.jsonl")
D2_PASSAGES = os.path.join(BASE_DIR, "data", "dataset2", "canonical", "passages.jsonl")
OUTPUT_DIR = os.path.join(BASE_DIR, "halo_datasets", "independent_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "independent_test_110.jsonl")
RECEIPT_FILE = os.path.join(OUTPUT_DIR, "independent_test_freeze_receipt.json")
AUDIT_REPORT = os.path.join(OUTPUT_DIR, "INDEPENDENT_TEST_BENCHMARK_AUDIT_REPORT.md")


def compute_content_hash(record: Dict[str, Any]) -> str:
    canonical_keys = [
        "id", "query", "generated_claim", "citation", "expected_status",
        "authoritative_passage_id", "evidence_passage", "verification_tier",
        "difficulty", "source", "source_dataset", "case_type", "mutation_type",
        "mutation_details", "expected_behavior", "explanation"
    ]
    payload = {k: record.get(k) for k in canonical_keys}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_corpora():
    d1_map = {}
    if os.path.exists(D1_PASSAGES):
        with open(D1_PASSAGES, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    d1_map[r["passage_id"]] = r

    d2_map = {}
    if os.path.exists(D2_PASSAGES):
        with open(D2_PASSAGES, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    d2_map[r["passage_id"]] = r

    return d1_map, d2_map


def build_independent_benchmark(d1_map: Dict[str, Any], d2_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases = []

    # Helper to fetch authentic snippet
    def get_ev(pid: str, ds: str) -> str:
        if ds == "D1":
            return d1_map.get(pid, {}).get("text", "")[:400]
        elif ds == "D2":
            return d2_map.get(pid, {}).get("text", "")[:400]
        return ""

    # =========================================================================
    # 1. POSITIVE CONTROLS (SUPPORTED - 26 cases)
    # Ensuring genuine legal answers are ACCEPTED without over-refusal
    # =========================================================================
    pos_defs = [
        ("IND_POS_001", "What is the notice requirement for general meetings under Section 101?",
         "A general meeting of a company may be called by giving not less than twenty-one clear days notice in writing or electronically.",
         {"act": "Companies Act, 2013", "section": "101", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_101_SUB_1", "D1", "Section 101(1) explicitly prescribes 21 clear days notice."),
        ("IND_POS_002", "What is the minimum number of directors required for a private company?",
         "Every private company must have a minimum of two directors under Section 149(1).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Section 149(1)(a) requires minimum 2 directors for private company."),
        ("IND_POS_003", "What is the minimum number of directors for a public company?",
         "Every public company shall have a minimum of three directors under Section 149(1).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Section 149(1)(a) mandates minimum 3 directors for public company."),
        ("IND_POS_004", "Can a member appoint a proxy under Section 105?",
         "Any member entitled to attend and vote is entitled to appoint another person as a proxy to attend and vote on their behalf.",
         {"act": "Companies Act, 2013", "section": "105", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_105_SUB_1", "D1", "Section 105(1) establishes statutory right to appoint proxy."),
        ("IND_POS_005", "What is the quorum for a board meeting under Section 173?",
         "The quorum for a board meeting is one-third of its total strength or two directors, whichever is higher.",
         {"act": "Companies Act, 2013", "section": "173", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_174_SUB_1", "D1", "Section 174(1) defines quorum as 1/3 or 2 directors."),
        ("IND_POS_006", "What is the statutory threshold for constitution of CSR committee?",
         "Companies having a net worth of ₹500 crore or more, turnover of ₹1000 crore or more, or net profit of ₹5 crore or more must constitute a CSR Committee.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", "D1", "Section 135(1) establishes CSR monetary thresholds."),
        ("IND_POS_007", "How much must companies spend on CSR activities?",
         "The Board shall ensure that the company spends at least 2% of the average net profits made during the three immediately preceding financial years.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "5"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_5", "D1", "Section 135(5) mandates spending at least 2% of average net profits."),
        ("IND_POS_008", "What is the penalty for fraud under Section 447?",
         "Fraud involving at least ten lakh rupees or one percent of turnover is punishable with imprisonment not less than six months.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447", "D1", "Section 447 prescribes mandatory minimum 6 months imprisonment."),
        ("IND_POS_009", "Who can apply for relief in cases of oppression and mismanagement?",
         "Members possessing not less than one-tenth of issued share capital or not less than one hundred members may apply under Section 241/244.",
         {"act": "Companies Act, 2013", "section": "244", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_244_SUB_1", "D1", "Section 244(1) sets forth eligibility thresholds for section 241."),
        ("IND_POS_010", "What governs the signing of financial statements under Section 134?",
         "Financial statements shall be approved by the Board and signed on behalf of the Board by at least the chairperson or two directors.",
         {"act": "Companies Act, 2013", "section": "134", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_134_SUB_1", "D1", "Section 134(1) governs authorization and signing of financial statements."),
        ("IND_POS_011", "Can directors participate in board meetings through video conferencing?",
         "Participation of directors in board meetings may be either in person or through video conferencing under Section 173(2).",
         {"act": "Companies Act, 2013", "section": "173", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_173_SUB_2", "D1", "Section 173(2) permits electronic participation."),
        ("IND_POS_012", "What is the maximum number of directors a company can have without special resolution?",
         "A company may have a maximum of fifteen directors under Section 149(1).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Section 149(1)(b) establishes maximum of 15 directors."),
        ("IND_POS_013", "How can a company increase the number of directors beyond fifteen?",
         "A company may appoint more than fifteen directors after passing a special resolution under Section 149(1).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Section 149(1) proviso allows exceeding 15 directors by special resolution."),
        ("IND_POS_014", "What is the maximum term for an independent director?",
         "An independent director shall hold office for a term up to five consecutive years on the Board.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "10"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_10", "D1", "Section 149(10) limits term to 5 consecutive years."),
        ("IND_POS_015", "Are independent directors entitled to stock options?",
         "An independent director shall not be entitled to any stock option under Section 149(9).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "9"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_9", "D1", "Section 149(9) expressly prohibits stock options for independent directors."),
        ("IND_POS_016", "What is the disqualification for non-filing of financial statements?",
         "A director who has failed to file financial statements for continuous three financial years is disqualified under Section 164(2).",
         {"act": "Companies Act, 2013", "section": "164", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_164_SUB_2", "D1", "Section 164(2)(a) disqualifies directors for 3 years non-filing."),
        ("IND_POS_017", "What did the Supreme Court hold in Mobilox Innovations regarding operational debt?",
         "In Mobilox Innovations v. Kirusa Software, the Supreme Court held that the adjudicating authority must reject Section 9 applications if a genuine pre-existing dispute exists.",
         {"case_name": "Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd.", "citation": "[2017] 10 S.C.R. 1006"}, "PAS-JUD-SC-2017-2017_10_1006_1072-P001", "D2", "Supreme Court established the pre-existing dispute test for IBC Section 9."),
        ("IND_POS_018", "What is the role of RP under IBC as held in Swiss Ribbons?",
         "In Swiss Ribbons v. Union of India, the Supreme Court clarified that the Resolution Professional is merely a facilitator and not an adjudicator.",
         {"case_name": "Swiss Ribbons Pvt. Ltd. v. Union of India", "citation": "[2019] 2 S.C.R. 731"}, "PAS-JUD-SC-2019-2019_2_731_824-P001", "D2", "Swiss Ribbons affirmed the non-adjudicatory role of the RP."),
        ("IND_POS_019", "What is the time period within which a company must hold its first AGM?",
         "A company shall hold its first annual general meeting within nine months from the closing of the first financial year.",
         {"act": "Companies Act, 2013", "section": "96", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_96_SUB_1", "D1", "Section 96(1) provides 9-month timeframe for first AGM."),
        ("IND_POS_020", "What is the interval between two annual general meetings?",
         "Not more than fifteen months shall elapse between the date of one annual general meeting and that of the next.",
         {"act": "Companies Act, 2013", "section": "96", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_96_SUB_1", "D1", "Section 96(1) mandates maximum 15-month gap between AGMs."),
        ("IND_POS_021", "Can a company buy back its own shares under Section 68?",
         "A company may purchase its own shares or securities out of its free reserves, securities premium account, or proceeds of issue.",
         {"act": "Companies Act, 2013", "section": "68", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_68_SUB_1", "D1", "Section 68(1) defines statutory sources for share buyback."),
        ("IND_POS_022", "What is the debt-equity ratio limit post-buyback under Section 68?",
         "The ratio of the aggregate of debts owed by the company shall not be more than twice the paid-up capital and free reserves after buy-back.",
         {"act": "Companies Act, 2013", "section": "68", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_68_SUB_2", "D1", "Section 68(2)(d) enforces 2:1 debt-equity ceiling post buy-back."),
        ("IND_POS_023", "Who can be appointed as an auditor under Section 141?",
         "A person shall be eligible for appointment as an auditor only if he is a chartered accountant in practice.",
         {"act": "Companies Act, 2013", "section": "141", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_141_SUB_1", "D1", "Section 141(1) specifies chartered accountant qualification for auditor."),
        ("IND_POS_024", "What constitutes an ordinary resolution under Section 114?",
         "A resolution is an ordinary resolution when the votes cast in favor exceed the votes cast against by members.",
         {"act": "Companies Act, 2013", "section": "114", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_114_SUB_1", "D1", "Section 114(1) defines ordinary resolution simple majority."),
        ("IND_POS_025", "What majority is required for a special resolution under Section 114?",
         "The votes cast in favor of the resolution must be not less than three times the number of votes cast against it.",
         {"act": "Companies Act, 2013", "section": "114", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_114_SUB_2", "D1", "Section 114(2) mandates 3:1 three-fourths majority for special resolution."),
        ("IND_POS_026", "Does Section 430 oust civil court jurisdiction?",
         "No civil court shall have jurisdiction to entertain any suit or proceeding in respect of any matter which the Tribunal or Appellate Tribunal is empowered to determine.",
         {"act": "Companies Act, 2013", "section": "430"}, "PAS_ACT_COMPANIES_2013_SEC_430", "D1", "Section 430 explicitly ousts civil court jurisdiction."),
    ]

    for cid, q, clm, cit, pid, ds, exp in pos_defs:
        ev = get_ev(pid, ds)
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "SUPPORTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "PASSAGE_SUPPORT",
            "difficulty": "medium", "source": "Companies Act, 2013" if ds == "D1" else "Supreme Court of India",
            "source_dataset": ds, "case_type": "passage_support", "mutation_type": None, "mutation_details": None,
            "expected_behavior": "ACCEPT", "explanation": exp
        })

    # =========================================================================
    # 2. FACTUAL INVERSIONS & SUBSTANTIVE CONTRADICTIONS (24 cases)
    # Testing NLI engine & Governor fail-closed on substantive legal falsehoods
    # =========================================================================
    neg_defs = [
        ("IND_NEG_001", "Can a proxy speak at a general meeting under Section 105?",
         "A proxy appointed under Section 105 has the full statutory right to speak and debate at any general meeting.",
         {"act": "Companies Act, 2013", "section": "105", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_105_SUB_1", "D1", "Contradicted: Section 105(1) states a proxy shall not have the right to speak at such meeting."),
        ("IND_NEG_002", "Can a proxy vote on a show of hands under Section 105?",
         "A proxy is entitled to vote both on a show of hands and on a poll.",
         {"act": "Companies Act, 2013", "section": "105", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_105_SUB_1", "D1", "Contradicted: Section 105(1) states a proxy is not entitled to vote except on a poll."),
        ("IND_NEG_003", "Can an independent director receive stock options under Section 149?",
         "Section 149(9) entitles independent directors to receive equity stock options as part of standard compensation.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "9"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_9", "D1", "Contradicted: Section 149(9) explicitly forbids stock options for independent directors."),
        ("IND_NEG_004", "Can civil courts grant injunctions on matters within NCLT power under Section 430?",
         "Civil courts retain concurrent jurisdiction to grant injunctions on any matter pending before the NCLT under Section 430.",
         {"act": "Companies Act, 2013", "section": "430"}, "PAS_ACT_COMPANIES_2013_SEC_430", "D1", "Contradicted: Section 430 bars civil courts from granting injunctions on NCLT matters."),
        ("IND_NEG_005", "Can a company advance loans to its directors freely under Section 185?",
         "Section 185 allows a company to advance loans to any director without restrictions or shareholder approvals.",
         {"act": "Companies Act, 2013", "section": "185", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_185_SUB_1", "D1", "Contradicted: Section 185 prohibits or strictly conditions loans to directors."),
        ("IND_NEG_006", "Is a special resolution required for ordinary director appointment?",
         "Under Section 152(2), all directors must be appointed by a special resolution passed by a three-fourths majority.",
         {"act": "Companies Act, 2013", "section": "152", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_152_SUB_2", "D1", "Contradicted: Section 152(2) requires appointment in general meeting by ordinary resolution."),
        ("IND_NEG_007", "Can private companies issue bearer share warrants under Section 46?",
         "Private limited companies have statutory authorization to issue bearer share warrants to undisclosed holders.",
         {"act": "Companies Act, 2013", "section": "46", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_46_SUB_1", "D1", "Contradicted: Bearer share warrants are prohibited under the 2013 Act."),
        ("IND_NEG_008", "What did Mobilox Innovations hold regarding operational creditor applications?",
         "In Mobilox Innovations, the Supreme Court ruled that operational creditors may initiate CIRP even when a genuine pre-existing dispute is demonstrated.",
         {"case_name": "Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd.", "citation": "[2017] 10 S.C.R. 1006"}, "PAS-JUD-SC-2017-2017_10_1006_1072-P001", "D2", "Contradicted: Mobilox held that pre-existing dispute mandates rejection of Section 9 petition."),
        ("IND_NEG_009", "Can an auditor be appointed for more than five continuous years as an individual?",
         "An individual auditor may be continuously appointed for fifteen consecutive years under Section 139(2).",
         {"act": "Companies Act, 2013", "section": "139", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_139_SUB_2", "D1", "Contradicted: Section 139(2) restricts individual auditor to one term of 5 consecutive years."),
        ("IND_NEG_010", "Can a private company have fifty directors without passing any resolution?",
         "Under Section 149(1), any private company can appoint fifty directors without passing a special resolution.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Contradicted: Section 149(1) caps board at 15 directors; special resolution is mandatory to exceed."),
        ("IND_NEG_011", "Is board approval required for political contributions under Section 182?",
         "A company may make political contributions solely on the personal authorization of the Managing Director without any board resolution.",
         {"act": "Companies Act, 2013", "section": "182", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_182_SUB_1", "D1", "Contradicted: Section 182(1) requires a resolution passed at a meeting of the Board."),
        ("IND_NEG_012", "Can a director vote on a contract where he is interested under Section 184?",
         "An interested director may actively participate and cast his vote on any contract in which he is interested under Section 184(2).",
         {"act": "Companies Act, 2013", "section": "184", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_184_SUB_2", "D1", "Contradicted: Section 184(2) bars an interested director from participating or voting."),
        ("IND_NEG_013", "Does Section 169 allow removal of a director appointed by the Tribunal?",
         "A company may remove a director appointed by the Tribunal under Section 242 by passing an ordinary resolution under Section 169.",
         {"act": "Companies Act, 2013", "section": "169", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_169_SUB_1", "D1", "Contradicted: Section 169(1) proviso explicitly excludes directors appointed by the Tribunal."),
        ("IND_NEG_014", "Can a body corporate be appointed as a director under Section 149?",
         "A body corporate, association or firm may be appointed as a director of a company under Section 149(1).",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "D1", "Contradicted: Section 149(1) provides only an individual shall be appointed as a director."),
        ("IND_NEG_015", "Is filing an annual return optional under Section 92?",
         "Filing of the annual return with the Registrar under Section 92 is purely voluntary for private limited companies.",
         {"act": "Companies Act, 2013", "section": "92", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_92_SUB_1", "D1", "Contradicted: Section 92(1) mandates every company shall prepare and file an annual return."),
        ("IND_NEG_016", "Can shares be issued at a discount under Section 53?",
         "A company may freely issue shares at a substantial discount in its initial public offering under Section 53.",
         {"act": "Companies Act, 2013", "section": "53", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_53_SUB_1", "D1", "Contradicted: Section 53(1) explicitly prohibits issue of shares at a discount (except sweat equity)."),
        ("IND_NEG_017", "Does an unlisted public company require an audit committee under Section 177 regardless of capital?",
         "Every company regardless of its paid-up capital or public listing is exempt from constituting an Audit Committee under Section 177.",
         {"act": "Companies Act, 2013", "section": "177", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_177_SUB_1", "D1", "Contradicted: Section 177(1) mandates audit committee for listed and prescribed public companies."),
        ("IND_NEG_018", "Does the moratorium under IBC Section 14 protect personal guarantors of corporate debtors?",
         "In State Bank of India v. V. Ramakrishnan, the Supreme Court held that the IBC Section 14 moratorium applies equally to protect personal guarantors.",
         {"case_name": "State Bank of India v. V. Ramakrishnan", "citation": "[2018] 9 S.C.R. 810"}, "PAS-JUD-SC-2018-2018_9_810_835-P001", "D2", "Contradicted: Supreme Court held Section 14 moratorium does NOT apply to personal guarantors."),
        ("IND_NEG_019", "Can a one person company have fifty members under Section 2(62)?",
         "A One Person Company may have up to fifty members registered under Section 2(62).",
         {"act": "Companies Act, 2013", "section": "2", "subsection": "62"}, "PAS_ACT_COMPANIES_2013_SEC_2_SUB_62", "D1", "Contradicted: Section 2(62) defines OPC as a company which has only one person as a member."),
        ("IND_NEG_020", "Are private companies required to have a minimum paid-up capital of ₹50 lakh under Section 2(68)?",
         "Section 2(68) prescribes a mandatory minimum paid-up share capital of ₹50 lakh for incorporating a private company.",
         {"act": "Companies Act, 2013", "section": "2", "subsection": "68"}, "PAS_ACT_COMPANIES_2013_SEC_2_SUB_68", "D1", "Contradicted: Minimum paid-up capital requirement was omitted by the 2015 amendment."),
        ("IND_NEG_021", "Can Section 8 companies pay dividends to their members?",
         "Section 8 companies are legally required to distribute at least 50% of their net profits as dividends to shareholders.",
         {"act": "Companies Act, 2013", "section": "8", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_8_SUB_1", "D1", "Contradicted: Section 8(1)(c) prohibits payment of any dividend to members of a Section 8 company."),
        ("IND_NEG_022", "Can a company alter its articles without a special resolution under Section 14?",
         "A company may alter its articles of association by passing a simple board resolution under Section 14.",
         {"act": "Companies Act, 2013", "section": "14", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_14_SUB_1", "D1", "Contradicted: Section 14(1) mandates a special resolution of shareholders to alter articles."),
        ("IND_NEG_023", "Does a company have unlimited time to register charges under Section 77?",
         "Under Section 77, registration of charges with the Registrar is entirely optional and has no statutory time limit.",
         {"act": "Companies Act, 2013", "section": "77", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_77_SUB_1", "D1", "Contradicted: Section 77(1) prescribes duty to register charge within thirty days."),
        ("IND_NEG_024", "Can interim dividend be declared without board approval under Section 123?",
         "The Chief Executive Officer may independently declare interim dividends without obtaining approval from the Board under Section 123.",
         {"act": "Companies Act, 2013", "section": "123", "subsection": "3"}, "PAS_ACT_COMPANIES_2013_SEC_123_SUB_3", "D1", "Contradicted: Section 123(3) provides interim dividend may be declared by the Board of Directors."),
    ]

    for cid, q, clm, cit, pid, ds, exp in neg_defs:
        ev = get_ev(pid, ds)
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "PASSAGE_SUPPORT",
            "difficulty": "medium", "source": "Companies Act, 2013" if ds == "D1" else "Supreme Court of India",
            "source_dataset": ds, "case_type": "passage_support", "mutation_type": "FACTUAL_CONTRADICTION",
            "mutation_details": {"type": "SEMANTIC_INVERSION"}, "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 3. NUMERICAL & QUANTITATIVE MUTATIONS (18 cases)
    # Testing deterministic symbolic numerical checker
    # =========================================================================
    num_defs = [
        ("IND_NUM_001", "What is the notice period for a general meeting under Section 101?",
         "A general meeting may be called by giving not less than 7 clear days notice.",
         {"act": "Companies Act, 2013", "section": "101", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_101_SUB_1", "21 clear days", "7 clear days", "Section 101(1) requires 21 clear days, not 7 days."),
        ("IND_NUM_002", "What is the CSR net worth threshold under Section 135?",
         "A company having net worth of ₹50 crore or more must constitute a CSR Committee.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", "₹500 crore", "₹50 crore", "Section 135(1) threshold is ₹500 crore, not ₹50 crore."),
        ("IND_NUM_003", "What is the CSR turnover threshold under Section 135?",
         "A company having turnover of ₹100 crore or more must constitute a CSR Committee.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", "₹1000 crore", "₹100 crore", "Section 135(1) threshold is ₹1000 crore, not ₹100 crore."),
        ("IND_NUM_004", "What is the CSR net profit threshold under Section 135?",
         "A company having net profit of ₹50 lakh or more must constitute a CSR Committee.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", "₹5 crore", "₹50 lakh", "Section 135(1) threshold is ₹5 crore, not ₹50 lakh."),
        ("IND_NUM_005", "What percentage of net profit must be spent on CSR?",
         "Companies must spend at least 10% of average net profits on CSR under Section 135(5).",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "5"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_5", "2%", "10%", "Section 135(5) mandates 2%, not 10%."),
        ("IND_NUM_006", "What is the minimum fraud amount under Section 447?",
         "Section 447 fraud provisions apply when the amount involved is at least ₹50 lakh.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447", "₹10 lakh", "₹50 lakh", "Section 447 threshold is ₹10 lakh, not ₹50 lakh."),
        ("IND_NUM_007", "What is the minimum imprisonment term under Section 447?",
         "Fraud under Section 447 is punishable with imprisonment for a term which shall not be less than three years.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447", "six months", "three years", "Section 447 minimum imprisonment is 6 months, not 3 years."),
        ("IND_NUM_008", "What is the maximum number of directors under Section 149 without special resolution?",
         "A company may have a maximum of twenty-five directors without special resolution.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "15 directors", "25 directors", "Section 149(1) caps at 15 directors, not 25."),
        ("IND_NUM_009", "What is the minimum number of independent directors for listed companies?",
         "Every listed public company shall have at least one-half independent directors.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "4"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_4", "one-third", "one-half", "Section 149(4) mandates at least one-third, not one-half."),
        ("IND_NUM_010", "What is the maximum term for an independent director under Section 149?",
         "An independent director may hold office for a single term of up to ten consecutive years.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "10"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_10", "five consecutive years", "ten consecutive years", "Section 149(10) specifies 5 consecutive years, not 10."),
        ("IND_NUM_011", "What is the board meeting quorum under Section 174?",
         "The quorum for a meeting of the Board of Directors shall be one-half of its total strength.",
         {"act": "Companies Act, 2013", "section": "174", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_174_SUB_1", "one-third", "one-half", "Section 174(1) quorum is one-third, not one-half."),
        ("IND_NUM_012", "What is the share capital threshold to apply under Section 244 for oppression?",
         "Members holding not less than 25% of the issued share capital may apply under Section 244.",
         {"act": "Companies Act, 2013", "section": "244", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_244_SUB_1", "one-tenth (10%)", "25%", "Section 244(1) threshold is one-tenth (10%), not 25%."),
        ("IND_NUM_013", "What is the member head count threshold under Section 244?",
         "Not less than five hundred members must join the petition under Section 244.",
         {"act": "Companies Act, 2013", "section": "244", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_244_SUB_1", "one hundred members", "five hundred members", "Section 244(1) requirement is 100 members, not 500."),
        ("IND_NUM_014", "What is the post-buyback debt-equity ceiling under Section 68?",
         "The ratio of debts shall not exceed four times the paid-up capital and free reserves after buy-back.",
         {"act": "Companies Act, 2013", "section": "68", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_68_SUB_2", "two times (2:1)", "four times (4:1)", "Section 68(2)(d) prescribes 2:1 ceiling, not 4:1."),
        ("IND_NUM_015", "What is the maximum interval between two AGMs under Section 96?",
         "Not more than twenty-four months shall elapse between two annual general meetings.",
         {"act": "Companies Act, 2013", "section": "96", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_96_SUB_1", "fifteen months", "twenty-four months", "Section 96(1) interval is 15 months, not 24 months."),
        ("IND_NUM_016", "What is the timeframe for holding the first AGM under Section 96?",
         "The first annual general meeting must be held within eighteen months from incorporation.",
         {"act": "Companies Act, 2013", "section": "96", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_96_SUB_1", "nine months", "eighteen months", "Section 96(1) timeframe is 9 months, not 18 months."),
        ("IND_NUM_017", "What is the timeframe to register charges under Section 77?",
         "A company must register created charges with the Registrar within 90 days.",
         {"act": "Companies Act, 2013", "section": "77", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_77_SUB_1", "thirty days", "90 days", "Section 77(1) deadline is 30 days, not 90 days."),
        ("IND_NUM_018", "What majority is required for a special resolution under Section 114?",
         "A special resolution requires votes cast in favor to be not less than five times votes against.",
         {"act": "Companies Act, 2013", "section": "114", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_114_SUB_2", "three times", "five times", "Section 114(2) requires three times, not five times."),
    ]

    for cid, q, clm, cit, pid, orig, mut, exp in num_defs:
        ev = get_ev(pid, "D1")
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "PASSAGE_SUPPORT",
            "difficulty": "hard", "source": "Companies Act, 2013", "source_dataset": "D1",
            "case_type": "numerical_mutation", "mutation_type": "QUANTITATIVE_MUTATION",
            "mutation_details": {"original_value": orig, "mutated_value": mut},
            "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 4. DEONTIC MODALITY SHIFTS (12 cases)
    # Testing deterministic modality checker (shall -> may, mandatory -> discretionary)
    # =========================================================================
    mod_defs = [
        ("IND_MOD_001", "Is CSR spending mandatory or discretionary under Section 135?",
         "The Board may, at its sole discretion, decide whether or not to spend 2% on CSR activities.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "5"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_5", "MANDATORY_TO_DISCRETIONARY", "Section 135(5) uses 'shall ensure', making CSR spending mandatory, not discretionary."),
        ("IND_MOD_002", "Is having a registered office mandatory under Section 12?",
         "A company may optionally choose to establish a registered office if business demands.",
         {"act": "Companies Act, 2013", "section": "12", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_12_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 12(1) uses 'shall have a registered office'."),
        ("IND_MOD_003", "Is convening an AGM mandatory for companies under Section 96?",
         "Every company may hold an annual general meeting if shareholders request one.",
         {"act": "Companies Act, 2013", "section": "96", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_96_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 96(1) states every company 'shall in each year hold' an AGM."),
        ("IND_MOD_004", "Is notice of board meetings mandatory under Section 173?",
         "Notice of a board meeting may be given if convenient, but failure to notify directors is legally permitted.",
         {"act": "Companies Act, 2013", "section": "173", "subsection": "3"}, "PAS_ACT_COMPANIES_2013_SEC_173_SUB_3", "MANDATORY_TO_DISCRETIONARY", "Section 173(3) mandates not less than 7 days notice shall be given."),
        ("IND_MOD_005", "Are companies required to file annual returns under Section 92?",
         "Preparation and filing of an annual return with the Registrar is purely discretionary.",
         {"act": "Companies Act, 2013", "section": "92", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_92_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 92(1) prescribes every company 'shall prepare' an annual return."),
        ("IND_MOD_006", "Is board resolution mandatory for related party transactions under Section 188?",
         "A company may enter into related party transactions without board consent if the CEO approves.",
         {"act": "Companies Act, 2013", "section": "188", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_188_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 188(1) requires consent of Board given by resolution."),
        ("IND_MOD_007", "Can an interested director choose to vote under Section 184?",
         "An interested director may participate in discussions and vote if he provides verbal disclosure.",
         {"act": "Companies Act, 2013", "section": "184", "subsection": "2"}, "PAS_ACT_COMPANIES_2013_SEC_184_SUB_2", "PROHIBITION_TO_PERMISSION", "Section 184(2) mandates director shall not participate or vote."),
        ("IND_MOD_008", "Is woman director appointment mandatory for prescribed companies?",
         "Prescribed public companies may optionally appoint a woman director if suitable candidates exist.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Second proviso to Section 149(1) mandates such class of companies 'shall have at least one woman director'."),
        ("IND_MOD_009", "Is filing financial statements with ROC mandatory under Section 137?",
         "Filing copies of financial statements with the Registrar may be omitted if shareholders consent.",
         {"act": "Companies Act, 2013", "section": "137", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_137_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 137(1) mandates a copy of financial statements 'shall be filed'."),
        ("IND_MOD_010", "Is minimum 6 months imprisonment for Section 447 fraud mandatory?",
         "Courts have discretion to waive imprisonment entirely for corporate fraud under Section 447.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447", "MANDATORY_TO_DISCRETIONARY", "Section 447 specifies imprisonment 'shall not be less than six months'."),
        ("IND_MOD_011", "Is an ordinary resolution mandatory for director removal under Section 169?",
         "A company may remove a director informally without passing any shareholder resolution.",
         {"act": "Companies Act, 2013", "section": "169", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_169_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 169(1) mandates removal 'by ordinary resolution'."),
        ("IND_MOD_012", "Is signing of financial statements mandatory under Section 134?",
         "Financial statements may be issued publicly unsigned if certified by an accountant.",
         {"act": "Companies Act, 2013", "section": "134", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_134_SUB_1", "MANDATORY_TO_DISCRETIONARY", "Section 134(1) states financial statements 'shall be signed' before submission."),
    ]

    for cid, q, clm, cit, pid, mtype, exp in mod_defs:
        ev = get_ev(pid, "D1")
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "PASSAGE_SUPPORT",
            "difficulty": "medium", "source": "Companies Act, 2013", "source_dataset": "D1",
            "case_type": "modality_mutation", "mutation_type": "DEONTIC_MODALITY_SHIFT",
            "mutation_details": {"shift_type": mtype}, "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 5. CITATION EXISTENCE TRAPS (10 cases)
    # Tier 1 verification of non-existent sections and phantom enactments
    # =========================================================================
    exist_defs = [
        ("IND_EXT_001", "What regulates quantum computing in Indian corporate boards?",
         "Section 492 of the Companies Act, 2013 mandates quantum encryption for board voting.",
         {"act": "Companies Act, 2013", "section": "492"}, "Companies Act 2013 ends at Section 470; Section 492 is fabricated."),
        ("IND_EXT_002", "What is Section 888 of the Companies Act?",
         "Section 888 establishes a specialized cyber tribunal for e-commerce fraud.",
         {"act": "Companies Act, 2013", "section": "888"}, "Section 888 does not exist in Indian corporate law."),
        ("IND_EXT_003", "What governs algorithmic corporate liability under Section 512?",
         "Section 512 imposes strict liability on corporate AI models.",
         {"act": "Companies Act, 2013", "section": "512"}, "Section 512 exceeds maximum section count (470)."),
        ("IND_EXT_004", "What does the National Corporate Blockchain Enactment, 2025 prescribe?",
         "Section 10 of the National Corporate Blockchain Enactment requires digital share tokens.",
         {"act": "National Corporate Blockchain Enactment, 2025", "section": "10"}, "The cited statute is completely fabricated."),
        ("IND_EXT_005", "What did the Supreme Court hold in Cyberdyne Robotics v. Union of India, 2024 INSC 777?",
         "The Supreme Court declared corporate AI entities possess fundamental rights.",
         {"case_name": "Cyberdyne Robotics v. Union of India", "citation": "2024 INSC 777"}, "Case citation is non-existent."),
        ("IND_EXT_006", "What is Section 620 of the Companies Act, 2013?",
         "Section 620 governs registration of synthetic digital subsidiaries.",
         {"act": "Companies Act, 2013", "section": "620"}, "Section 620 is fabricated (Act has 470 sections)."),
        ("IND_EXT_007", "What section governs interplanetary trade under the Companies Act?",
         "Section 485 sets licensing norms for extraterrestrial commercial entities.",
         {"act": "Companies Act, 2013", "section": "485"}, "Section 485 is non-existent."),
        ("IND_EXT_008", "What does Section 710 prescribe?",
         "Section 710 provides penalties for failure to register carbon credit swaps.",
         {"act": "Companies Act, 2013", "section": "710"}, "Section 710 does not exist."),
        ("IND_EXT_009", "What is the Digital Corporate Governance Act, 2026?",
         "Under Section 3 of the Digital Corporate Governance Act, smart contracts supersede board minutes.",
         {"act": "Digital Corporate Governance Act, 2026", "section": "3"}, "Fabricated statutory enactment."),
        ("IND_EXT_010", "What did Supreme Court rule in Future Alpha v. SEBI, [2025] 15 S.C.R. 999?",
         "The court exempted algorithmic funds from insider trading scrutiny.",
         {"case_name": "Future Alpha v. SEBI", "citation": "[2025] 15 S.C.R. 999"}, "Fabricated judicial citation."),
    ]

    for cid, q, clm, cit, exp in exist_defs:
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "FABRICATED_CITATION",
            "authoritative_passage_id": "NONE", "evidence_passage": "", "verification_tier": "EXISTENCE",
            "difficulty": "easy", "source": "FABRICATED", "source_dataset": "D1",
            "case_type": "citation_existence", "mutation_type": "CITATION_FABRICATION",
            "mutation_details": {"fabricated_element": cit.get("section") or cit.get("act") or cit.get("citation")},
            "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 6. CITATION METADATA MISMATCHES (8 cases)
    # Tier 2 verification of forum, court, year, and heading mismatches
    # =========================================================================
    meta_defs = [
        ("IND_MET_001", "What is Section 135 titled?",
         "Section 135 of the Companies Act, 2013 is titled 'Voluntary Winding Up of Companies'.",
         {"act": "Companies Act, 2013", "section": "135"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1", "Section 135 is titled 'Corporate Social Responsibility', not 'Voluntary Winding Up'."),
        ("IND_MET_002", "What is Section 149 titled?",
         "Section 149 of the Companies Act, 2013 is titled 'Appointment of Statutory Auditors'.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1", "Section 149 is titled 'Company to have Board of Directors'; auditors are in Section 139."),
        ("IND_MET_003", "What court decided Mobilox Innovations?",
         "The National Green Tribunal decided Mobilox Innovations v. Kirusa Software.",
         {"case_name": "Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd.", "citation": "[2017] 10 S.C.R. 1006", "court": "NGT"}, "PAS-JUD-SC-2017-2017_10_1006_1072-P001", "Mobilox Innovations was decided by the Supreme Court of India, not NGT."),
        ("IND_MET_004", "What year was Swiss Ribbons decided?",
         "In Swiss Ribbons v. Union of India, [1995] 2 S.C.R. 731, the Supreme Court upheld the IBC in 1995.",
         {"case_name": "Swiss Ribbons Pvt. Ltd. v. Union of India", "citation": "[1995] 2 S.C.R. 731", "year": "1995"}, "PAS-JUD-SC-2019-2019_2_731_824-P001", "Swiss Ribbons was decided in 2019, not 1995 (IBC did not exist in 1995)."),
        ("IND_MET_005", "What is Section 447 titled?",
         "Section 447 of the Companies Act, 2013 is titled 'Power of Central Government to appoint inspectors'.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447", "Section 447 is titled 'Punishment for fraud'."),
        ("IND_MET_006", "What is Section 188 titled?",
         "Section 188 of the Companies Act, 2013 is titled 'Prohibition of insider trading in securities'.",
         {"act": "Companies Act, 2013", "section": "188", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_188_SUB_1", "Section 188 is titled 'Related party transactions'."),
        ("IND_MET_007", "What court decided Essar Steel v. Satish Kumar Gupta?",
         "The Delhi District Consumer Forum delivered the landmark insolvency ruling in Essar Steel.",
         {"case_name": "Committee of Creditors of Essar Steel v. Satish Kumar Gupta", "court": "DISTRICT_CONSUMER_FORUM"}, "PAS-JUD-SC-2020-2020_8_531_662-P001", "Essar Steel was decided by the Supreme Court of India."),
        ("IND_MET_008", "What is Section 408 titled?",
         "Section 408 is titled 'Special Courts for summary trial'.",
         {"act": "Companies Act, 2013", "section": "408"}, "PAS_ACT_COMPANIES_2013_SEC_408", "Section 408 is titled 'Constitution of National Company Law Tribunal'; special courts are Section 435."),
    ]

    for cid, q, clm, cit, pid, exp in meta_defs:
        ev = get_ev(pid, "D1" if "PAS_ACT" in pid else "D2")
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "METADATA",
            "difficulty": "medium", "source": "Companies Act, 2013" if "PAS_ACT" in pid else "Supreme Court of India",
            "source_dataset": "D1" if "PAS_ACT" in pid else "D2", "case_type": "citation_metadata",
            "mutation_type": "METADATA_MUTATION", "mutation_details": {"metadata_error": exp},
            "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 7. TEMPORAL AMENDMENTS & REPEAL TRACKING (8 cases)
    # Tier 3 chronological validity and amendment awareness
    # =========================================================================
    temp_defs = [
        ("IND_TMP_001", "What is the mandatory minimum capital for incorporating a private company today?",
         "Every private company incorporated in 2026 must have a minimum paid-up share capital of ₹1,00,000 under Section 2(68).",
         {"act": "Companies Act, 2013", "section": "2", "subsection": "68"}, "PAS_ACT_COMPANIES_2013_SEC_2_SUB_68", "The ₹1 lakh minimum paid-up capital requirement was omitted by the Companies (Amendment) Act, 2015."),
        ("IND_TMP_002", "What is the mandatory minimum capital for public companies under Section 2(71)?",
         "A public company incorporated today is required to have a minimum paid-up capital of ₹5,00,000.",
         {"act": "Companies Act, 2013", "section": "2", "subsection": "71"}, "PAS_ACT_COMPANIES_2013_SEC_2_SUB_71", "The ₹5 lakh minimum capital requirement was omitted by the 2015 amendment."),
        ("IND_TMP_003", "Does the Company Law Board (CLB) still adjudicate company disputes today?",
         "All petitions for oppression and mismanagement in 2026 must be filed before the Company Law Board under Section 10E.",
         {"act": "Companies Act, 1956", "section": "10E"}, "PAS_ACT_COMPANIES_2013_SEC_434_SUB_1", "The CLB was dissolved and replaced by NCLT under Section 408/434 w.e.f. June 1, 2016."),
        ("IND_TMP_004", "Can a company commence business without filing a declaration under Section 10A?",
         "A company incorporated after 2018 may commence business immediately without any director filing a declaration of paid-up capital.",
         {"act": "Companies Act, 2013", "section": "10A", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_10A_SUB_1", "Section 10A (inserted in 2018) mandates filing a declaration within 180 days prior to commencement."),
        ("IND_TMP_005", "Are corporate winding-up petitions filed before High Courts in 2026?",
         "High Courts maintain original company jurisdiction for winding up under the 1956 Act in 2026.",
         {"act": "Companies Act, 1956", "section": "433"}, "PAS_ACT_COMPANIES_2013_SEC_434_SUB_1", "High Court company jurisdiction was transferred to NCLT under Section 434."),
        ("IND_TMP_006", "Is a common seal mandatory for all companies under Section 9?",
         "Every company incorporated under the Act must have a common seal to execute contracts legally.",
         {"act": "Companies Act, 2013", "section": "9"}, "PAS_ACT_COMPANIES_2013_SEC_9", "Mandatory common seal was made optional by the Companies (Amendment) Act, 2015."),
        ("IND_TMP_007", "Was Section 135 CSR penal provision decriminalized?",
         "Officers of a company failing to spend CSR funds are subject to mandatory criminal imprisonment under Section 135.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "7"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_7", "Criminal imprisonment in Section 135 was replaced by monetary civil penalties by the 2020 Amendment Act."),
        ("IND_TMP_008", "Does the Companies Act 1956 govern current board appointments?",
         "Appointment of managing directors is governed by Section 269 of the Companies Act, 1956 today.",
         {"act": "Companies Act, 1956", "section": "269"}, "PAS_ACT_COMPANIES_2013_SEC_196_SUB_1", "1956 Act is repealed; governed by Section 196 of the 2013 Act."),
    ]

    for cid, q, clm, cit, pid, exp in temp_defs:
        ev = get_ev(pid, "D1")
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "TEMPORAL",
            "difficulty": "hard", "source": "Companies Act, 2013 (Amended)", "source_dataset": "D1",
            "case_type": "temporal_verification", "mutation_type": "TEMPORAL_MUTATION",
            "mutation_details": {"temporal_error": exp}, "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 8. COMPOUND CLAIMS (PARTIALLY_SUPPORTED - 6 cases)
    # Testing atomic claim splitting where one clause is valid and one is false
    # =========================================================================
    comp_defs = [
        ("IND_CMP_001", "What are the rules regarding proxies under Section 105?",
         "A member may appoint a proxy to attend and vote on a poll, and that proxy has the statutory right to speak during general debates.",
         {"act": "Companies Act, 2013", "section": "105", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_105_SUB_1",
         "Clause 1 (appoint proxy) is supported; Clause 2 (right to speak) is contradicted by Section 105(1)."),
        ("IND_CMP_002", "What is the board composition under Section 149?",
         "A public company must have at least three directors, and all directors must be independent directors.",
         {"act": "Companies Act, 2013", "section": "149", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_149_SUB_1",
         "Clause 1 (min 3 directors) is supported; Clause 2 (all independent) is contradicted (only 1/3 required)."),
        ("IND_CMP_003", "What are the CSR expenditure mandates under Section 135?",
         "Prescribed companies must spend at least 2% of average net profits on CSR, and unspent funds may be paid out as director bonuses.",
         {"act": "Companies Act, 2013", "section": "135", "subsection": "5"}, "PAS_ACT_COMPANIES_2013_SEC_135_SUB_5",
         "Clause 1 (2% spend) is supported; Clause 2 (director bonuses) is contradicted."),
        ("IND_CMP_004", "What governs general meeting notice under Section 101?",
         "A general meeting requires 21 clear days notice, and notice can only be delivered by personal hand delivery.",
         {"act": "Companies Act, 2013", "section": "101", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_101_SUB_1",
         "Clause 1 (21 clear days) is supported; Clause 2 (only hand delivery) is contradicted (electronic mode is permitted)."),
        ("IND_CMP_005", "What is the penalty for fraud under Section 447?",
         "Fraud involving ₹10 lakh is punishable with imprisonment not less than 6 months, and courts may substitute community service for imprisonment.",
         {"act": "Companies Act, 2013", "section": "447"}, "PAS_ACT_COMPANIES_2013_SEC_447",
         "Clause 1 (6 months min) is supported; Clause 2 (community service substitution) is contradicted."),
        ("IND_CMP_006", "What is the quorum for board meetings under Section 174?",
         "The quorum is one-third of total strength or two directors, and interested directors can always count towards the quorum.",
         {"act": "Companies Act, 2013", "section": "174", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_174_SUB_1",
         "Clause 1 (1/3 or 2) is supported; Clause 2 (interested directors count) is contradicted by Section 174(3)."),
    ]

    for cid, q, clm, cit, pid, exp in comp_defs:
        ev = get_ev(pid, "D1")
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "PARTIALLY_SUPPORTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "PASSAGE_SUPPORT",
            "difficulty": "hard", "source": "Companies Act, 2013", "source_dataset": "D1",
            "case_type": "compound_claim", "mutation_type": "COMPOUND_MUTATION",
            "mutation_details": {"compound_split": exp}, "expected_behavior": "QUALIFY", "explanation": exp
        })

    # =========================================================================
    # 9. DOCTRINAL & FORUM CONFLICT DETECTION (6 cases)
    # Testing conflict detector between statutory norms and judicial precedents
    # =========================================================================
    conf_defs = [
        ("IND_CNF_001", "Does IBC Section 14 moratorium apply to personal guarantors?",
         "The statutory moratorium under Section 14 of the IBC stays all debt enforcement against personal guarantors.",
         {"act": "IBC, 2016", "section": "14"}, "PAS-JUD-SC-2018-2018_9_810_835-P001", "D2",
         "Doctrinal Conflict: Statute Section 14 was qualified by Supreme Court in SBI v. V. Ramakrishnan holding personal guarantors are excluded."),
        ("IND_CNF_002", "Can High Courts stay NCLT proceedings under supervisory jurisdiction?",
         "High Courts retain inherent Article 227 supervisory power to stay ordinary NCLT insolvency proceedings.",
         {"act": "Companies Act, 2013", "section": "430"}, "PAS_ACT_COMPANIES_2013_SEC_430", "D1",
         "Forum Hierarchy: Section 430 explicitly ousts civil court jurisdiction; Supreme Court in Embassy Property Developments established jurisdictional boundaries."),
        ("IND_CNF_003", "Does Section 188 arm's length exception apply to related party transactions?",
         "Every related party transaction requires board approval even if entered into in ordinary course of business on arm's length basis.",
         {"act": "Companies Act, 2013", "section": "188", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_188_SUB_1", "D1",
         "Statutory Proviso: Third proviso to Section 188(1) explicitly exempts transactions in ordinary course on arm's length basis."),
        ("IND_CNF_004", "Can NCLT adjudicate contractual disputes independent of insolvency?",
         "In Tata Consultancy Services v. Vishal Ghisulal Jain, Supreme Court affirmed NCLT has general jurisdiction to try all contractual breaches.",
         {"case_name": "TCS v. Vishal Ghisulal Jain", "citation": "[2021] 10 S.C.R. 1080"}, "PAS-JUD-SC-2021-2021_10_1080_1103-P001", "D2",
         "Judicial Precedent: Supreme Court held NCLT jurisdiction under Section 60(5)(c) IBC cannot usurp contractual remedies outside insolvency nexus."),
        ("IND_CNF_005", "Does commercial wisdom of CoC override judicial review under IBC?",
         "The adjudicating authority may substitute its commercial judgment for the business decision of the Committee of Creditors.",
         {"case_name": "K. Sashidhar v. Indian Overseas Bank", "citation": "[2019] 12 S.C.R. 257"}, "PAS-JUD-SC-2019-2019_12_257_317-P001", "D2",
         "Doctrinal Precedent: Supreme Court held commercial wisdom of CoC is non-justiciable under IBC."),
        ("IND_CNF_006", "Is NCLT bound by technical rules of Evidence Act under Section 424?",
         "The Tribunal is strictly bound by the procedural shackles and technical rules of the Indian Evidence Act, 1872 under Section 424.",
         {"act": "Companies Act, 2013", "section": "424", "subsection": "1"}, "PAS_ACT_COMPANIES_2013_SEC_424_SUB_1", "D1",
         "Statutory Exception: Section 424(1) states Tribunal shall not be bound by procedure laid down by CPC or Evidence Act, but guided by natural justice."),
    ]

    for cid, q, clm, cit, pid, ds, exp in conf_defs:
        ev = get_ev(pid, ds)
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": pid, "evidence_passage": ev, "verification_tier": "CONFLICT",
            "difficulty": "hard", "source": "Statute / Judicial Conflict", "source_dataset": ds,
            "case_type": "conflict_detection", "mutation_type": "DOCTRINAL_DIVERGENCE",
            "mutation_details": {"conflict_explanation": exp}, "expected_behavior": "REJECT", "explanation": exp
        })

    # =========================================================================
    # 10. FAIL-CLOSED REFUSAL PROBES (6 cases)
    # Provoking governor fail-closed quarantine on zero-evidence / out-of-domain claims
    # =========================================================================
    fail_defs = [
        ("IND_FCL_001", "What is the penalty for murder in company boardrooms?",
         "Section 302 of the Indian Penal Code mandates death penalty or life imprisonment for corporate board murders.",
         {"act": "Indian Penal Code", "section": "302"}, "Out of domain: Indian Penal Code criminal murder is outside corporate commercial corpus."),
        ("IND_FCL_002", "What are the patent term limits under the Patents Act, 1970?",
         "Under Section 53 of the Patents Act, 1970, the term of every patent shall be twenty years from filing.",
         {"act": "Patents Act, 1970", "section": "53"}, "Out of domain: Patents Act intellectual property is outside corporate commercial corpus."),
        ("IND_FCL_003", "What is the statutory speed limit for corporate delivery drones?",
         "Section 45 of the Autonomous Commercial Delivery Code limits drone speed to 40 km/h.",
         {"act": "Autonomous Commercial Delivery Code", "section": "45"}, "Zero evidence: Fabricated enactment outside any authentic corpus."),
        ("IND_FCL_004", "What is the air pollution emission threshold under the Air Act for corporate headquarters?",
         "Section 37 of the Air (Prevention and Control of Pollution) Act mandates corporate chimney audits.",
         {"act": "Air Pollution Act", "section": "37"}, "Out of domain: Environmental air pollution statutes outside corporate benchmark."),
        ("IND_FCL_005", "What is the statutory exchange rate for corporate lunar real estate?",
         "Corporate lunar leases under Section 19 of the Space Commerce Accord require gold-pegged payments.",
         {"act": "Space Commerce Accord", "section": "19"}, "Zero evidence: Fabricated celestial commercial jurisdiction."),
        ("IND_FCL_006", "What is the tariff rate on maritime shipping containers under Customs Act Section 12?",
         "Section 12 of the Customs Act mandates 15% standard basic customs duty on all imported containers.",
         {"act": "Customs Act, 1962", "section": "12"}, "Out of domain: Customs tariff legislation outside corporate commercial corpus."),
    ]

    for cid, q, clm, cit, exp in fail_defs:
        cases.append({
            "id": cid, "query": q, "generated_claim": clm, "citation": cit, "expected_status": "CONTRADICTED",
            "authoritative_passage_id": "NONE", "evidence_passage": "", "verification_tier": "FAIL_CLOSED",
            "difficulty": "easy", "source": "OUT_OF_DOMAIN", "source_dataset": "NONE",
            "case_type": "fail_closed_cases", "mutation_type": "OUT_OF_DOMAIN_PROBE",
            "mutation_details": {"probe_reason": exp}, "expected_behavior": "REJECT", "explanation": exp
        })

    # Compute content hashes for all cases
    for case in cases:
        case["content_hash"] = compute_content_hash(case)

    return cases


def main():
    print("=" * 80)
    print("  BUILDING INDEPENDENT LEGAL VERIFICATION TEST SUITE (110+ ITEMS)")
    print("  Authored by: Independent External Legal AI Evaluation Auditor")
    print("=" * 80)

    d1_map, d2_map = load_corpora()
    print(f"[*] Loaded corpora: {len(d1_map)} D1 passages, {len(d2_map)} D2 passages.")

    cases = build_independent_benchmark(d1_map, d2_map)
    print(f"[*] Successfully constructed {len(cases)} independent test verification cases.")

    # Breakdown by category
    cat_counts = {}
    status_counts = {}
    for c in cases:
        cat = c["case_type"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        st = c["expected_status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    print("\n[+] Breakdown by Category:")
    for cat, count in sorted(cat_counts.items()):
        print(f"    {cat:<26}: {count:>3} cases ({count/len(cases)*100:.1f}%)")

    print("\n[+] Breakdown by Expected Status:")
    for st, count in sorted(status_counts.items()):
        print(f"    {st:<26}: {count:>3} cases ({count/len(cases)*100:.1f}%)")

    # Write output JSONL
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n[+] Saved independent benchmark to: {OUTPUT_FILE}")

    # Compute master SHA-256
    h = hashlib.sha256()
    with open(OUTPUT_FILE, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    master_sha256 = h.hexdigest()
    print(f"[+] Master SHA-256 Digest: {master_sha256}")

    # Freeze Receipt
    receipt = {
        "benchmark_id": "HALO_INDEPENDENT_VERIFICATION_TEST_110",
        "author": "Independent External Legal Evaluation Auditor & Benchmark Specialist",
        "role_distinction": "Authored independently from core verifier pipeline development team",
        "protocol": "INDEPENDENT-TEST-v1.0",
        "case_count": len(cases),
        "categories": cat_counts,
        "status_distribution": status_counts,
        "master_sha256": master_sha256,
        "file_path": OUTPUT_FILE,
        "source_corpora": {
            "d1_companies_act_passages": len(d1_map),
            "d2_judicial_passages": len(d2_map),
        }
    }
    with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print(f"[+] Saved freeze receipt to: {RECEIPT_FILE}")

    # Generate Audit Report Markdown
    with open(AUDIT_REPORT, "w", encoding="utf-8") as f:
        f.write("# HALO Independent Verification Test Suite: Audit & Certification Report\n\n")
        f.write("**Role**: Independent External Legal Evaluation Auditor & Benchmarking Specialist  \n")
        f.write("**Methodological Distinction**: Authored independently from the developers of the verification modules to prevent experimenter bias, test set contamination, and threshold overfitting.  \n")
        f.write(f"**Total Verification Items**: **{len(cases)} items** (exceeding 100+ mandate)  \n")
        f.write(f"**Master SHA-256 Digest**: `{master_sha256}`  \n")
        f.write(f"**Receipt Path**: [`{RECEIPT_FILE}`](file:///{RECEIPT_FILE.replace(chr(92), '/')})  \n\n")
        f.write("## 1. Category Distribution Breakdown\n\n")
        f.write("| Category | Case Count | Proportion | Methodological Evaluative Objective |\n")
        f.write("| :--- | :---: | :---: | :--- |\n")
        f.write(f"| **passage_support (Positive Controls)** | 26 | 22.8% | Genuine legal answers requiring ACCEPT without false over-refusal |\n")
        f.write(f"| **passage_support (Factual Inversions)** | 24 | 21.1% | Direct substantive contradictions requiring fail-closed REJECT |\n")
        f.write(f"| **numerical_mutation** | 18 | 15.8% | Quantitative threshold mutations (days, fines, rupees, percentages) |\n")
        f.write(f"| **modality_mutation** | 12 | 10.5% | Deontic shifts altering mandatory 'shall' into discretionary 'may' |\n")
        f.write(f"| **citation_existence** | 10 | 8.8% | Tier 1 phantom sections (e.g. Sec 999, 888) and fake statutes |\n")
        f.write(f"| **citation_metadata** | 8 | 7.0% | Tier 2 court mismatches (SC vs NGT) and section heading errors |\n")
        f.write(f"| **temporal_verification** | 8 | 7.0% | 2015/2020 amendments, omitted capital requirements, 1956 repeals |\n")
        f.write(f"| **compound_claim** | 6 | 5.3% | Multi-proposition statements requiring QUALIFY under proposition split |\n")
        f.write(f"| **conflict_detection** | 6 | 5.3% | Doctrinal tensions between statutory text and judicial precedents |\n")
        f.write(f"| **fail_closed_cases** | 6 | 5.3% | Negative probes on out-of-domain criminal statutes & zero-evidence |\n")
        f.write(f"| **TOTAL** | **{len(cases)}** | **100.0%** | Full Independent Benchmark Suite |\n\n")
        f.write("## 2. Status Distribution Audit\n\n")
        f.write("| Expected Epistemic Status | Count | Proportion | Target Governor Action |\n")
        f.write("| :--- | :---: | :---: | :--- |\n")
        for st, count in sorted(status_counts.items()):
            action = "ACCEPT" if st == "SUPPORTED" else ("QUALIFY" if st == "PARTIALLY_SUPPORTED" else "REJECT")
            f.write(f"| `{st}` | {count} | {count/len(cases)*100:.1f}% | `{action}` |\n")
        f.write("\n")
    print(f"[+] Saved audit report to: {AUDIT_REPORT}")


if __name__ == "__main__":
    main()
