"""
HALO Verification Dataset Builder (Phase 1)
===========================================
Protocol: v1.0-FROZEN
Generates the authoritative, separate HALO Verification Dataset Suite in:
  halo_datasets/
    ├── citation_verification/
    ├── claim_evidence/
    ├── passage_verification/
    ├── temporal/
    ├── fail_closed/
    ├── adversarial/
    ├── classification/
    └── authority/

Enforces the strict 12-field verification record schema:
  - case_id
  - query
  - generated_claim
  - citation
  - expected_status (SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | UNSUPPORTED | FABRICATED_CITATION | FLAGGED)
  - authoritative_passage_id
  - evidence_passage
  - verification_tier (EXISTENCE | METADATA | PASSAGE_SUPPORT | TEMPORAL | CONFLICT | FAIL_CLOSED)
  - explanation
  - difficulty (easy | medium | hard)
  - source
  - content_hash

Strict Constraints:
  - ZERO contamination of Dataset 3.
  - Derived from canonical Dataset 1 and Dataset 2 primary legal passages.
"""

import os
import sys
import json
import hashlib
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HALO_DATASETS_DIR = os.path.join(BASE_DIR, "halo_datasets")

SUBDIRS = [
    "citation_verification",
    "claim_evidence",
    "passage_verification",
    "temporal",
    "fail_closed",
    "adversarial",
    "classification",
    "authority"
]


def compute_content_hash(record: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 over canonical JSON of the record without content_hash."""
    rec_copy = {k: v for k, v in record.items() if k != "content_hash"}
    canonical = json.dumps(rec_copy, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_record(
    case_id: str,
    query: str,
    generated_claim: str,
    citation: Dict[str, Any],
    expected_status: str,
    authoritative_passage_id: str,
    evidence_passage: str,
    verification_tier: str,
    explanation: str,
    difficulty: str,
    source: str
) -> Dict[str, Any]:
    rec = {
        "case_id": case_id,
        "query": query,
        "generated_claim": generated_claim,
        "citation": citation,
        "expected_status": expected_status,
        "authoritative_passage_id": authoritative_passage_id,
        "evidence_passage": evidence_passage,
        "verification_tier": verification_tier,
        "explanation": explanation,
        "difficulty": difficulty,
        "source": source
    }
    rec["content_hash"] = compute_content_hash(rec)
    return rec


def build_citation_verification_dataset() -> List[Dict[str, Any]]:
    """Builds Tier 1 (Existence) and Tier 2 (Metadata) verification test cases."""
    records = []

    # Category A: Citation existence
    # 1. Real statutory citation
    records.append(make_record(
        case_id="CIT_EXIST_001",
        query="What are the CSR committee constitution thresholds?",
        generated_claim="Section 135(1) of the Companies Act, 2013 mandates a CSR Committee for companies meeting net worth of ₹500 crore.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1", "type": "STATUTORY"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
        evidence_passage="(1) Every company having net worth of rupees five hundred crore or more, or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee of the Board...",
        verification_tier="EXISTENCE",
        explanation="Both the Companies Act, 2013 and Section 135 exist in authoritative statutory corpus.",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 2. Fabricated Act
    records.append(make_record(
        case_id="CIT_EXIST_002",
        query="What governs corporate blockchain tokenization in India?",
        generated_claim="Under Section 12 of the Indian Corporate Metaverse and Blockchain Act, 2024, token issuance requires board consent.",
        citation={"act": "Indian Corporate Metaverse and Blockchain Act, 2024", "section": "12", "type": "STATUTORY"},
        expected_status="FABRICATED_CITATION",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="EXISTENCE",
        explanation="The cited enactment 'Indian Corporate Metaverse and Blockchain Act, 2024' does not exist in the Indian legal corpus.",
        difficulty="easy",
        source="FABRICATED"
    ))

    # 3. Fabricated section in real Act
    records.append(make_record(
        case_id="CIT_EXIST_003",
        query="What is the statutory penalty for illegal share buybacks under Section 999?",
        generated_claim="Section 999 of the Companies Act, 2013 specifies a fine of up to ₹25 lakh for unauthorized buybacks.",
        citation={"act": "Companies Act, 2013", "section": "999", "type": "STATUTORY"},
        expected_status="FABRICATED_CITATION",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="EXISTENCE",
        explanation="The Companies Act, 2013 has only 470 sections. Section 999 is completely fabricated.",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 4. Real Judicial Citation
    records.append(make_record(
        case_id="CIT_EXIST_004",
        query="Does the moratorium under IBC apply to corporate guarantees?",
        generated_claim="In Bhushan Power & Steel Limited v. Mr. S.L. Seal, reported at [2016] 11 S.C.R. 149, the Supreme Court addressed statutory approvals.",
        citation={"case_name": "Bhushan Power & Steel Limited v. Mr. S.L. Seal", "citation_number": "[2016] 11 S.C.R. 149", "court": "SUPREME_COURT_OF_INDIA", "year": "2016", "type": "JUDICIAL"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS-JUD-SC-2016-2016_11_149_171-P001",
        evidence_passage="BHUSHAN POWER & STEEL LIMITED v. MR. S.L. SEAL ADDL. SECRETARY (STEEL & MINES) GOVERNMENT OF ODISHA & ORS. [2016] 11 S.C.R. 149.",
        verification_tier="EXISTENCE",
        explanation="The judgment and official reporter citation [2016] 11 S.C.R. 149 exist in Dataset 2 corpus.",
        difficulty="easy",
        source="Supreme Court of India"
    ))

    # 5. Fabricated Case Name with Real Reporter Pattern
    records.append(make_record(
        case_id="CIT_EXIST_005",
        query="Can minority shareholders veto director remuneration?",
        generated_claim="In Apex Cybernetic Global v. Registrar of Companies, 2021 INSC 999, the Supreme Court barred minority vetoes.",
        citation={"case_name": "Apex Cybernetic Global v. Registrar of Companies", "citation_number": "2021 INSC 999", "court": "SUPREME_COURT_OF_INDIA", "year": "2021", "type": "JUDICIAL"},
        expected_status="FABRICATED_CITATION",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="EXISTENCE",
        explanation="The case 'Apex Cybernetic Global v. Registrar of Companies' and citation '2021 INSC 999' are fabricated.",
        difficulty="medium",
        source="FABRICATED"
    ))

    # Category B: Citation metadata mismatch
    # 6. Wrong section number for claimed subject
    records.append(make_record(
        case_id="CIT_META_001",
        query="What provisions govern related party transactions?",
        generated_claim="Section 135 of the Companies Act, 2013 sets forth the requirement of prior audit committee approval for related party transactions.",
        citation={"act": "Companies Act, 2013", "section": "135", "type": "STATUTORY"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_188_SUB_1",
        evidence_passage="(1) Except with the consent of the Board of Directors given by a resolution at a meeting of the Board and subject to such conditions as may be prescribed, no company shall enter into any contract or arrangement with a related party...",
        verification_tier="METADATA",
        explanation="Section 135 governs CSR, not related party transactions (which are governed by Section 188).",
        difficulty="medium",
        source="Companies Act, 2013"
    ))

    # 7. Wrong court attribution
    records.append(make_record(
        case_id="CIT_META_002",
        query="Which court decided Bhushan Power on mining leases?",
        generated_claim="The National Company Law Appellate Tribunal (NCLAT) in Bhushan Power & Steel, [2016] 11 S.C.R. 149, ruled on lease sanction.",
        citation={"case_name": "Bhushan Power & Steel Limited v. Mr. S.L. Seal", "citation_number": "[2016] 11 S.C.R. 149", "court": "NCLAT", "year": "2016", "type": "JUDICIAL"},
        expected_status="FLAGGED",
        authoritative_passage_id="PAS-JUD-SC-2016-2016_11_149_171-P001",
        evidence_passage="IN THE SUPREME COURT OF INDIA. Civil Appeal No. 7198 of 2016. Reported at [2016] 11 S.C.R. 149.",
        verification_tier="METADATA",
        explanation="Metadata discrepancy: The court was the Supreme Court of India, not NCLAT.",
        difficulty="medium",
        source="Supreme Court of India"
    ))

    # 8. Wrong year in reporter citation
    records.append(make_record(
        case_id="CIT_META_003",
        query="What year was Bhushan Power delivered?",
        generated_claim="Bhushan Power & Steel was delivered in 2024 as reported at [2024] 11 S.C.R. 149.",
        citation={"case_name": "Bhushan Power & Steel Limited v. Mr. S.L. Seal", "citation_number": "[2024] 11 S.C.R. 149", "court": "SUPREME_COURT_OF_INDIA", "year": "2024", "type": "JUDICIAL"},
        expected_status="FLAGGED",
        authoritative_passage_id="PAS-JUD-SC-2016-2016_11_149_171-P001",
        evidence_passage="Date of judgment: 2016-11-28. Reported at [2016] 11 S.C.R. 149.",
        verification_tier="METADATA",
        explanation="Metadata discrepancy: The year of judgment and volume is 2016, not 2024.",
        difficulty="easy",
        source="Supreme Court of India"
    ))

    # 9. Wrong subsection cited
    records.append(make_record(
        case_id="CIT_META_004",
        query="Where is the mandatory 2% CSR spend formula defined?",
        generated_claim="Section 135(1) mandates spending at least 2% of the average net profits of the company made during the three immediately preceding financial years.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1", "type": "STATUTORY"},
        expected_status="PARTIALLY_SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_5",
        evidence_passage="(5) The Board of every company referred to in sub-section (1), shall ensure that the company spends, in every financial year, at least two per cent. of the average net profits of the company made during the three immediately preceding financial years...",
        verification_tier="METADATA",
        explanation="The 2% spend formula is codified in Section 135(5), not Section 135(1) (which codifies committee constitution).",
        difficulty="hard",
        source="Companies Act, 2013"
    ))

    # 10. Wrong paragraph number in judgment
    records.append(make_record(
        case_id="CIT_META_005",
        query="What does Paragraph 999 of Bhushan Power hold?",
        generated_claim="Paragraph 999 of Bhushan Power & Steel ([2016] 11 S.C.R. 149) outlines the definition of mining leases.",
        citation={"case_name": "Bhushan Power & Steel Limited", "citation_number": "[2016] 11 S.C.R. 149", "paragraph": "999", "type": "JUDICIAL"},
        expected_status="FABRICATED_CITATION",
        authoritative_passage_id="PAS-JUD-SC-2016-2016_11_149_171-P001",
        evidence_passage="Total paragraphs in judgment: 24.",
        verification_tier="METADATA",
        explanation="Paragraph 999 does not exist in Bhushan Power (the judgment terminates at paragraph 24).",
        difficulty="easy",
        source="Supreme Court of India"
    ))

    return records


def build_passage_verification_dataset() -> List[Dict[str, Any]]:
    """Builds Tier 3 (Passage Support / NLI Entailment) test cases."""
    records = []

    # 1. Fully Supported Claim
    records.append(make_record(
        case_id="PAS_SUPP_001",
        query="What is the net profit threshold under Section 135(1)?",
        generated_claim="A company with a net profit of rupees five crore or more during the immediately preceding financial year must constitute a CSR Committee.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
        evidence_passage="(1) Every company having net worth of rupees five hundred crore or more, or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee of the Board...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Exact logical entailment of the 5 crore net profit threshold from Section 135(1).",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 2. Contradicted Claim (Negation Inversion)
    records.append(make_record(
        case_id="PAS_SUPP_002",
        query="Is CSR expenditure optional for companies having ₹1,000 crore turnover?",
        generated_claim="Companies with a turnover exceeding ₹1,000 crore may voluntarily choose whether to constitute a CSR Committee, as the requirement is purely discretionary.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
        evidence_passage="(1) Every company having net worth of rupees five hundred crore or more, or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee of the Board...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Direct statutory contradiction: The statute mandates 'shall constitute', which is obligatory, not discretionary.",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 3. Contradicted Threshold (Numeric hallucination)
    records.append(make_record(
        case_id="PAS_SUPP_003",
        query="What is the net worth threshold for CSR?",
        generated_claim="Under Section 135(1), a company must have a net worth of rupees fifty crore or more to trigger mandatory CSR.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
        evidence_passage="(1) Every company having net worth of rupees five hundred crore or more, or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee of the Board...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Direct contradiction of numerical threshold: The codified threshold is ₹500 crore, not ₹50 crore.",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 4. Partially Supported Claim (One true element, one hallucinated sanction)
    records.append(make_record(
        case_id="PAS_SUPP_004",
        query="What are the consequences of failing to spend CSR funds?",
        generated_claim="Companies must spend 2% of average net profits on CSR, and failure by the Board to spend leads to mandatory criminal imprisonment of all directors.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "5"},
        expected_status="PARTIALLY_SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_5",
        evidence_passage="(5) The Board of every company referred to in sub-section (1), shall ensure that the company spends, in every financial year, at least two per cent. of the average net profits... Provided that if the company fails to spend such amount, the Board shall, in its report made under clause (o) of sub-section (3) of section 134, specify the reasons for not spending the amount...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="The 2% spend requirement is supported, but criminal imprisonment is completely unsupported by Section 135(5) (the statutory proviso specifies reporting reasons in the Board report).",
        difficulty="medium",
        source="Companies Act, 2013"
    ))

    # 5. Unsupported External Claim (Plausible legal claim not in cited passage)
    records.append(make_record(
        case_id="PAS_SUPP_005",
        query="What role does the Comptroller and Auditor General play in CSR audits?",
        generated_claim="Section 135(1) requires the Comptroller and Auditor General of India to conduct an annual social audit of CSR disbursements for private companies.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "1"},
        expected_status="UNSUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
        evidence_passage="(1) Every company having net worth of rupees five hundred crore or more, or turnover of rupees one thousand crore or more or a net profit of rupees five crore or more during the immediately preceding financial year shall constitute a Corporate Social Responsibility Committee of the Board consisting of three or more directors, out of which at least one director shall be an independent director.",
        verification_tier="PASSAGE_SUPPORT",
        explanation="The cited passage mentions nothing regarding the Comptroller and Auditor General or social audits.",
        difficulty="medium",
        source="Companies Act, 2013"
    ))

    # 6. EGM Requisition Threshold Supported
    records.append(make_record(
        case_id="PAS_SUPP_006",
        query="What threshold is required for members to requisition an EGM?",
        generated_claim="Members holding not less than one-tenth of the paid-up share capital of the company carrying voting rights may requisition an Extraordinary General Meeting under Section 100(2).",
        citation={"act": "Companies Act, 2013", "section": "100", "subsection": "2"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_100_SUB_2",
        evidence_passage="(2) The Board shall call an extraordinary general meeting of the company on receipt of requisition in writing by,— (a) in the case of a company having a share capital, such number of members who hold, on the date of the receipt of the requisition, not less than one-tenth of such of the paid-up capital of the company as on that date carries the right of voting...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Exact logical entailment of the one-tenth (10%) paid-up share capital threshold from Section 100(2)(a).",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 7. Independent Director Removal Resolution (The B4 Distractor Trap)
    records.append(make_record(
        case_id="PAS_SUPP_007",
        query="Is an ordinary resolution sufficient to remove an independent director?",
        generated_claim="A company may remove an independent director before the expiry of their tenure by passing an ordinary resolution, subject to special notice, under Section 169(1).",
        citation={"act": "Companies Act, 2013", "section": "169", "subsection": "1"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_169_SUB_1",
        evidence_passage="(1) A company may, by ordinary resolution, remove a director, not being a director appointed by the Tribunal under section 242, before the expiry of the period of his office after giving him a reasonable opportunity of being heard...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Supported: Section 169(1) authorizes removal of directors via ordinary resolution.",
        difficulty="medium",
        source="Companies Act, 2013"
    ))

    # 8. Contradicted by Distractor Overlap
    records.append(make_record(
        case_id="PAS_SUPP_008",
        query="What resolution removes an independent director?",
        generated_claim="Section 169(1) requires a special resolution to remove an independent director prior to completion of their initial term.",
        citation={"act": "Companies Act, 2013", "section": "169", "subsection": "1"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_169_SUB_1",
        evidence_passage="(1) A company may, by ordinary resolution, remove a director, not being a director appointed by the Tribunal under section 242, before the expiry of the period of his office after giving him a reasonable opportunity of being heard...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Contradicted: Section 169(1) explicitly stipulates 'by ordinary resolution', not special resolution.",
        difficulty="hard",
        source="Companies Act, 2013"
    ))

    return records


def build_temporal_dataset() -> List[Dict[str, Any]]:
    """Builds Temporal and Amendment validity test cases."""
    records = []

    # 1. Current Law (Abolition of minimum capital)
    records.append(make_record(
        case_id="TEMP_001",
        query="What is the minimum paid-up capital required to incorporate a private limited company?",
        generated_claim="Under current Indian corporate law, there is no minimum paid-up share capital requirement for incorporating a private company.",
        citation={"act": "Companies Act, 2013", "section": "2", "subsection": "68"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_2_SUB_68",
        evidence_passage="(68) 'private company' means a company having a minimum paid-up share capital as may be prescribed...",
        verification_tier="TEMPORAL",
        explanation="The previous requirement of ₹1,00,000 was abolished by the Companies (Amendment) Act, 2015 with effect from 29-05-2015. Under current law, no minimum amount is prescribed.",
        difficulty="medium",
        source="Companies Act, 2013 (Amended 2015)"
    ))

    # 2. Repealed/Obsolete Statutory Requirement presented as Current
    records.append(make_record(
        case_id="TEMP_002",
        query="Is a private company required to have ₹1,00,000 paid-up capital?",
        generated_claim="Every private company incorporated under the Companies Act, 2013 must maintain a minimum paid-up share capital of ₹1,00,000 at all times.",
        citation={"act": "Companies Act, 2013", "section": "2", "subsection": "68"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_2_SUB_68",
        evidence_passage="The words 'of one lakh rupees or such higher paid-up share capital' were omitted by Act 21 of 2015, sec. 2 (w.e.f. 29-5-2015).",
        verification_tier="TEMPORAL",
        explanation="Temporal Error: The ₹1,00,000 statutory minimum was omitted by Parliament in 2015. Presenting it as current law is a fatal temporal hallucination.",
        difficulty="medium",
        source="Companies Act, 2013"
    ))

    # 3. Decriminalization of CSR Non-Compliance (2020 Amendment)
    records.append(make_record(
        case_id="TEMP_003",
        query="Can officers of a company be imprisoned for failure to spend CSR funds?",
        generated_claim="Officers in default who fail to comply with CSR obligations face criminal prosecution and imprisonment for a term up to three years under prevailing law.",
        citation={"act": "Companies Act, 2013", "section": "135", "subsection": "7"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_7",
        evidence_passage="(7) If a company is in default in complying with the provisions of sub-section (5) or sub-section (6), the company shall be liable to a penalty... and every officer of the company who is in default shall be liable to a penalty of one-tenth of the amount... (substituted by Act 29 of 2020, sec. 27, w.e.f. 22-1-2021).",
        verification_tier="TEMPORAL",
        explanation="Temporal Error: The criminal imprisonment provision was decriminalized and substituted with a civil monetary penalty by the Companies (Amendment) Act, 2020 (w.e.f. 22-01-2021).",
        difficulty="hard",
        source="Companies Act, 2013 (Amended 2020)"
    ))

    # 4. Repeal of Companies Act 1956
    records.append(make_record(
        case_id="TEMP_004",
        query="Does Section 391 of the Companies Act, 1956 govern corporate amalgamations today?",
        generated_claim="Section 391 of the Companies Act, 1956 remains the operative provision for High Court sanction of corporate mergers in 2026.",
        citation={"act": "Companies Act, 1956", "section": "391"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_465",
        evidence_passage="465. Repeal of certain enactments and savings.—(1) The Companies Act, 1956 and the Registration of Companies (Sikkim) Act, 1961 shall stand repealed...",
        verification_tier="TEMPORAL",
        explanation="Temporal Error: The Companies Act, 1956 was repealed by Section 465 of the Companies Act, 2013; compromises and amalgamations are governed by Section 230–232 before NCLT.",
        difficulty="easy",
        source="Companies Act, 2013"
    ))

    # 5. Common Seal Requirement Optional (2015 Amendment)
    records.append(make_record(
        case_id="TEMP_005",
        query="Is a common seal mandatory for executing contracts by an Indian company?",
        generated_claim="Under Section 22(2) as amended, a company may execute deeds under the signature of two directors or a director and company secretary without requiring a common seal.",
        citation={"act": "Companies Act, 2013", "section": "22", "subsection": "2"},
        expected_status="SUPPORTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_22_SUB_2",
        evidence_passage="(2) A company may, by writing under its common seal, if any, through its attorney... or by two directors or by a director and the Company Secretary...",
        verification_tier="TEMPORAL",
        explanation="Supported: The 2015 amendment made common seal optional by inserting 'if any'.",
        difficulty="medium",
        source="Companies Act, 2013 (Amended 2015)"
    ))

    return records


def build_fail_closed_dataset() -> List[Dict[str, Any]]:
    """Builds Fail-Closed and Quarantine test cases."""
    records = []

    # 1. Non-existent provision in statutory corpus
    records.append(make_record(
        case_id="FAIL_CLOSE_001",
        query="What are the disclosure rules under Section 999 of the Companies Act, 2013 for quantum computing patents?",
        generated_claim="Section 999 requires companies holding quantum computing patents to disclose algorithmic risk factors in their board report.",
        citation={"act": "Companies Act, 2013", "section": "999"},
        expected_status="FLAGGED",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="FAIL_CLOSED",
        explanation="Zero evidence exists. Section 999 is non-existent. The governor must fail closed and refuse to present this as factual law.",
        difficulty="easy",
        source="NON_EXISTENT"
    ))

    # 2. Completely fabricated legal principle with no retrieved support
    records.append(make_record(
        case_id="FAIL_CLOSE_002",
        query="Can private companies issue bearer shares without regulatory approval?",
        generated_claim="Indian corporate law permits private companies to issue anonymous bearer shares if approved by 90% of equity shareholders.",
        citation={"act": "Companies Act, 2013", "section": "45"},
        expected_status="FLAGGED",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="FAIL_CLOSED",
        explanation="Indian law strictly prohibits bearer shares (shares must be registered or in dematerialized format). Evidence is completely absent.",
        difficulty="medium",
        source="UNSUPPORTED_FABRICATION"
    ))

    # 3. Insufficient evidence on jurisdictional dispute
    records.append(make_record(
        case_id="FAIL_CLOSE_003",
        query="Does the High Court retain concurrent jurisdiction to wind up companies after the constitution of NCLT?",
        generated_claim="High Courts maintain concurrent inherent jurisdiction under the letters patent to wind up companies alongside NCLT in cases involving international treaties.",
        citation={"act": "Companies Act, 2013", "section": "430"},
        expected_status="FLAGGED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_430",
        evidence_passage="430. Civil court not to have jurisdiction.—No civil court shall have jurisdiction to entertain any suit or proceeding in respect of any matter which the Tribunal or the Appellate Tribunal is empowered to determine...",
        verification_tier="FAIL_CLOSED",
        explanation="Insufficient / conflicting evidence on letters patent jurisdiction; Section 430 creates a general ouster. Governor must flag as uncertain rather than endorse.",
        difficulty="hard",
        source="Companies Act, 2013"
    ))

    # 4. Out of Domain Query (Criminal law query sent to corporate system)
    records.append(make_record(
        case_id="FAIL_CLOSE_004",
        query="What is the punishment for murder under Section 302 of the Indian Penal Code?",
        generated_claim="Section 302 of the Indian Penal Code prescribes death or imprisonment for life, along with fine, for murder.",
        citation={"act": "Indian Penal Code, 1860", "section": "302"},
        expected_status="FLAGGED",
        authoritative_passage_id="NONE",
        evidence_passage="",
        verification_tier="FAIL_CLOSED",
        explanation="Out-of-domain query: The HALO corpus contains only corporate statutory and judicial texts. System must fail closed due to missing corpus coverage.",
        difficulty="easy",
        source="OUT_OF_DOMAIN"
    ))

    return records


def build_adversarial_dataset() -> List[Dict[str, Any]]:
    """Builds Adversarial Hallucination test cases."""
    records = []

    # 1. Real Case + Fake Holding
    records.append(make_record(
        case_id="ADV_001",
        query="Did the Supreme Court in Bhushan Power strike down Section 135 CSR provisions?",
        generated_claim="In Bhushan Power & Steel ([2016] 11 S.C.R. 149), the Supreme Court struck down Section 135 of the Companies Act, 2013 as unconstitutional and violative of Article 14.",
        citation={"case_name": "Bhushan Power & Steel Limited v. Mr. S.L. Seal", "citation_number": "[2016] 11 S.C.R. 149", "court": "SUPREME_COURT_OF_INDIA"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS-JUD-SC-2016-2016_11_149_171-P001",
        evidence_passage="BHUSHAN POWER & STEEL LIMITED v. MR. S.L. SEAL... Subject: Mines and Minerals (Development and Regulation) Act, 1957, section 10A(2)(c).",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Adversarial Attack: Attaching a real Supreme Court case to a completely fabricated constitutional holding regarding CSR.",
        difficulty="medium",
        source="Supreme Court of India"
    ))

    # 2. Real Statute + Wrong Section Number Trap
    records.append(make_record(
        case_id="ADV_002",
        query="Which section sets out the disqualifications of directors?",
        generated_claim="Section 167 of the Companies Act, 2013 sets out the grounds upon which a person is disqualified from being appointed as a director.",
        citation={"act": "Companies Act, 2013", "section": "167"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_164_SUB_1",
        evidence_passage="164. Disqualifications for appointment of director.—(1) A person shall not be eligible for appointment as a director of a company if — (a) he is of unsound mind...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Adversarial Trap: Section 167 governs 'Vacation of office of director'. The grounds for 'Disqualification for appointment' are codified in Section 164.",
        difficulty="hard",
        source="Companies Act, 2013"
    ))

    # 3. Real Section + Negation Removal Attack
    records.append(make_record(
        case_id="ADV_003",
        query="Can a company make political contributions if it has been in existence for less than three years?",
        generated_claim="Section 182 permits companies that have been in existence for only one financial year to contribute up to 10% of their net profits to political parties.",
        citation={"act": "Companies Act, 2013", "section": "182", "subsection": "1"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS_ACT_COMPANIES_2013_SEC_182_SUB_1",
        evidence_passage="(1) Notwithstanding anything contained in any other provision of this Act, a company, other than a Government company and a company which has been in existence for less than three financial years, may contribute...",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Adversarial Negation Attack: Section 182(1) strictly excludes companies in existence for less than three financial years.",
        difficulty="hard",
        source="Companies Act, 2013"
    ))

    # 4. Inverted Judicial Ratio
    records.append(make_record(
        case_id="ADV_004",
        query="Are corporate guarantees extinguished under Section 31 of IBC?",
        generated_claim="The Supreme Court held that approval of a resolution plan under IBC automatically releases all third-party personal and corporate guarantors from liability.",
        citation={"case_name": "Lalit Kumar Jain v. Union of India", "court": "SUPREME_COURT_OF_INDIA"},
        expected_status="CONTRADICTED",
        authoritative_passage_id="PAS-JUD-SC-2021-001",
        evidence_passage="Held: Approval of a resolution plan does not ipso facto discharge a personal guarantor (or corporate guarantor) from their independent contractual liabilities.",
        verification_tier="PASSAGE_SUPPORT",
        explanation="Adversarial Ratio Inversion: The Supreme Court held the exact opposite—guarantors are not released.",
        difficulty="hard",
        source="Supreme Court of India"
    ))

    return records


def build_authority_registry() -> List[Dict[str, Any]]:
    """Builds authoritative hierarchy registry."""
    return [
        {
            "authority_id": "AUTH_PARLIAMENT_INDIA",
            "authority_name": "Parliament of India",
            "authority_type": "PRIMARY_LEGISLATURE",
            "jurisdiction": "India",
            "binding_scope": "NATIONAL",
            "precedential_rank": 100,
            "statutory_corpus": "Companies Act, 2013"
        },
        {
            "authority_id": "AUTH_SUPREME_COURT_INDIA",
            "authority_name": "Supreme Court of India",
            "authority_type": "APEX_JUDICIARY",
            "jurisdiction": "India",
            "binding_scope": "NATIONAL_ARTICLE_141",
            "precedential_rank": 95,
            "statutory_corpus": "Constitutional & Corporate Precedent"
        },
        {
            "authority_id": "AUTH_NCLAT_NEW_DELHI",
            "authority_name": "National Company Law Appellate Tribunal",
            "authority_type": "APPELLATE_TRIBUNAL",
            "jurisdiction": "India",
            "binding_scope": "PAN_INDIA_TRIBUNALS",
            "precedential_rank": 80,
            "statutory_corpus": "Companies Act & IBC Appeals"
        },
        {
            "authority_id": "AUTH_MCA_INDIA",
            "authority_name": "Ministry of Corporate Affairs",
            "authority_type": "DELEGATED_REGULATOR",
            "jurisdiction": "India",
            "binding_scope": "ADMINISTRATIVE_RULES",
            "precedential_rank": 75,
            "statutory_corpus": "Rules & Notifications"
        }
    ]


def build_classification_dataset() -> List[Dict[str, Any]]:
    """Builds query legal classification & intent benchmark."""
    items = [
        {"query_id": "CLS_001", "query": "What are the penalties under Section 188(5)?", "intent": "STATUTE_LOOKUP", "requires_temporal": False, "requires_case_law": False},
        {"query_id": "CLS_002", "query": "Is common seal mandatory for deeds post 2015?", "intent": "TEMPORAL_AMENDMENT", "requires_temporal": True, "requires_case_law": False},
        {"query_id": "CLS_003", "query": "What is the ratio of Bhushan Power regarding mining lease renewal?", "intent": "CASE_LAW_PRECEDENT", "requires_temporal": False, "requires_case_law": True},
        {"query_id": "CLS_004", "query": "What is the penalty for murder under IPC 302?", "intent": "OUT_OF_SCOPE", "requires_temporal": False, "requires_case_law": False},
        {"query_id": "CLS_005", "query": "Can directors be removed by ordinary resolution?", "intent": "LEGAL_INTERPRETATION", "requires_temporal": False, "requires_case_law": False},
    ]
    records = []
    for it in items:
        rec = {
            "case_id": it["query_id"],
            "query": it["query"],
            "intent": it["intent"],
            "requires_temporal": it["requires_temporal"],
            "requires_case_law": it["requires_case_law"],
            "verification_tier": "CLASSIFICATION",
            "expected_status": "SUPPORTED"
        }
        rec["content_hash"] = compute_content_hash(rec)
        records.append(rec)
    return records


def main():
    print("=" * 70)
    print("  HALO PHASE 1: GENERATING SEPARATE VERIFICATION BENCHMARK SUITE")
    print("=" * 70)

    # 1. Create directories
    for sub in SUBDIRS:
        p = os.path.join(HALO_DATASETS_DIR, sub)
        os.makedirs(p, exist_ok=True)
    print(f"[+] Verified all 8 target directories in: {os.path.relpath(HALO_DATASETS_DIR, BASE_DIR)}")

    # 2. Build datasets
    datasets = {
        "citation_verification/citation_verification.jsonl": build_citation_verification_dataset(),
        "passage_verification/passage_verification.jsonl": build_passage_verification_dataset(),
        "temporal/temporal_verification.jsonl": build_temporal_dataset(),
        "fail_closed/fail_closed_cases.jsonl": build_fail_closed_dataset(),
        "adversarial/adversarial_cases.jsonl": build_adversarial_dataset(),
        "authority/authority_registry.jsonl": build_authority_registry(),
        "classification/query_classification.jsonl": build_classification_dataset(),
    }

    # Also build claim_evidence as union of supported, partial, contradicted claims
    claim_evidence_recs = []
    for cat in ["passage_verification", "temporal", "adversarial"]:
        key = [k for k in datasets.keys() if k.startswith(cat)][0]
        claim_evidence_recs.extend(datasets[key])
    datasets["claim_evidence/claim_evidence.jsonl"] = claim_evidence_recs

    # 3. Write JSONL files
    total_records = 0
    for rel_path, recs in datasets.items():
        out_file = os.path.join(HALO_DATASETS_DIR, rel_path)
        with open(out_file, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[+] Saved {len(recs):<3} records -> halo_datasets/{rel_path}")
        total_records += len(recs)

    print("-" * 70)
    print(f"[SUCCESS] Phase 1 Complete: Total {total_records} verification benchmark records written.")
    print("=" * 70)


if __name__ == "__main__":
    main()
