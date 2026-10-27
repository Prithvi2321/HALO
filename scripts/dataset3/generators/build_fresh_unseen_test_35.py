"""
HALO Fresh Untouched Test Benchmark Generator (N=35)
=====================================================
Protocol: UNTOUCHED-TEST-v1.0
Author: Independent Legal AI Evaluation Auditor
Scope: Unexamined Sections of Companies Act 2013 & IBC:
  - Section 62 (Further issue of capital)
  - Section 68 (Buyback of securities)
  - Section 71 (Debentures & DRR)
  - Section 73 (Prohibition of public deposits)
  - Section 115 (Resolutions requiring special notice)
  - Section 118 (Minutes of proceedings)
  - Section 123 (Declaration of dividend)
  - Section 124 (Unpaid dividend account & IEPF)
  - Section 134 (Board report disclosures)
  - Section 139 (Appointment and rotation of statutory auditors)
  - Section 164 (Disqualifications of directors)
  - Section 177 (Audit committee & vigil mechanism)
  - Section 185 (Loans to directors)
  - Section 186 (Loan and investment by company)
  - Section 203 (Key managerial personnel)
  - Section 248 (Strike off by Registrar)
  - Section 454 (Adjudication of penalties)

Seals with cryptographic SHA-256 hash receipt before any evaluation.
"""

import os
import sys
import json
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "halo_datasets" / "fresh_unseen_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "fresh_unseen_test_35.jsonl"
RECEIPT_FILE = OUT_DIR / "fresh_unseen_test_freeze_receipt.json"

FRESH_CASES = [
    # --- POSITIVE CONTROLS (N=10) ---
    {
        "id": "UNTOUCHED_POS_001",
        "case_type": "passage_support",
        "generated_claim": "A company may purchase its own shares if the buyback is authorized by its articles and a special resolution is passed in general meeting under Section 68.",
        "authoritative_passage_id": "D1_SEC_68",
        "evidence_passage": "(1) Notwithstanding anything contained in this Act, but subject to the provisions of sub-section (2), a company may purchase its own shares or other specified securities... (2) No company shall purchase its own shares or other specified securities under sub-section (1), unless— (a) the buy-back is authorised by its articles; (b) a special resolution has been passed at a general meeting of the company authorising the buy-back:",
        "citation": "Section 68(1)-(2), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Verbatim authorized buyback conditions under Section 68(1)-(2)."
    },
    {
        "id": "UNTOUCHED_POS_002",
        "case_type": "passage_support",
        "generated_claim": "The buy-back of shares in any financial year shall not exceed twenty-five per cent of the total paid-up capital and free reserves of the company.",
        "authoritative_passage_id": "D1_SEC_68",
        "evidence_passage": "Provided that the buy-back of equity shares in any financial year shall not exceed twenty-five per cent. of its total paid-up equity capital in that financial year:",
        "citation": "Section 68(2)(c) proviso, Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "25% statutory cap on equity buyback under Section 68(2)(c)."
    },
    {
        "id": "UNTOUCHED_POS_003",
        "case_type": "passage_support",
        "generated_claim": "No company shall accept or renew deposits from the public under Section 73 except in the manner provided under Chapter V.",
        "authoritative_passage_id": "D1_SEC_73",
        "evidence_passage": "(1) On and after the commencement of this Act, no company shall invite, accept or renew deposits under this Act from the public except in a manner provided under this Chapter:",
        "citation": "Section 73(1), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Statutory prohibition on public deposits under Section 73(1)."
    },
    {
        "id": "UNTOUCHED_POS_004",
        "case_type": "passage_support",
        "generated_claim": "Any dividend remaining unpaid or unclaimed for thirty days from declaration must be transferred within seven days to the Unpaid Dividend Account.",
        "authoritative_passage_id": "D1_SEC_124",
        "evidence_passage": "(1) Where a dividend has been declared by a company but has not been paid or claimed within thirty days from the date of the declaration to any shareholder entitled to the payment thereof, the company shall, within seven days from the date of expiry of the said period of thirty days, transfer the total amount of dividend which remains unpaid or unclaimed to a special account to be opened by the company in that behalf in any scheduled bank to be called the Unpaid Dividend Account.",
        "citation": "Section 124(1), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 124(1) Unpaid Dividend Account transfer rule."
    },
    {
        "id": "UNTOUCHED_POS_005",
        "case_type": "passage_support",
        "generated_claim": "Any money transferred to the Unpaid Dividend Account remaining unclaimed for seven years must be transferred to the Investor Education and Protection Fund.",
        "authoritative_passage_id": "D1_SEC_124",
        "evidence_passage": "(5) Any money transferred to the Unpaid Dividend Account of a company which remains unpaid or unclaimed for a period of seven years from the date of such transfer shall be transferred by the company along with interest accrued, if any, thereon to the Fund established under sub-section (1) of section 125:",
        "citation": "Section 124(5), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 124(5) 7-year transfer to IEPF."
    },
    {
        "id": "UNTOUCHED_POS_006",
        "case_type": "passage_support",
        "generated_claim": "Every listed company and prescribed public company must constitute an Audit Committee consisting of a minimum of three directors with independent directors forming a majority.",
        "authoritative_passage_id": "D1_SEC_177",
        "evidence_passage": "(1) The Board of Directors of every listed public company and such other class or classes of companies, as may be prescribed, shall constitute an Audit Committee. (2) The Audit Committee shall consist of a minimum of three directors with independent directors forming a majority:",
        "citation": "Section 177(1)-(2), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 177(1)-(2) Audit Committee composition."
    },
    {
        "id": "UNTOUCHED_POS_007",
        "case_type": "passage_support",
        "generated_claim": "A company cannot directly or indirectly advance any loan to its directors or to any person in whom the director is interested except as permitted under Section 185.",
        "authoritative_passage_id": "D1_SEC_185",
        "evidence_passage": "(1) No company shall, directly or indirectly, advance any loan, including any loan represented by a book debt to, or give any guarantee or provide any security in connection with any loan taken by,— (a) any director of company, or of a company which is its holding company or any partner or relative of any such director; or (b) any firm in which any such director or relative is a partner.",
        "citation": "Section 185(1), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 185(1) prohibition on loans to directors."
    },
    {
        "id": "UNTOUCHED_POS_008",
        "case_type": "passage_support",
        "generated_claim": "No company shall give any loan or guarantee exceeding sixty per cent of its paid-up share capital, free reserves and securities premium account or one hundred per cent of its free reserves and securities premium account, whichever is more, without prior approval by special resolution.",
        "authoritative_passage_id": "D1_SEC_186",
        "evidence_passage": "(2) No company shall directly or indirectly — (a) give any loan to any person or other body corporate; (b) give any guarantee or provide security... exceeding sixty per cent. of its paid-up share capital, free reserves and securities premium account or one hundred per cent. of its free reserves and securities premium account, whichever is more. (3) Where the aggregate... exceed the limits specified under sub-section (2), no loan or guarantee shall be given... unless previously authorised by a special resolution passed in a general meeting:",
        "citation": "Section 186(2)-(3), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 186(2)-(3) 60% / 100% threshold on inter-corporate loans."
    },
    {
        "id": "UNTOUCHED_POS_009",
        "case_type": "passage_support",
        "generated_claim": "Every company must cause minutes of all proceedings of general meetings and Board meetings to be entered in books kept for that purpose within thirty days of the meeting.",
        "authoritative_passage_id": "D1_SEC_118",
        "evidence_passage": "(1) Every company shall cause minutes of the proceedings of every general meeting of any class of shareholders or creditors, and every resolution passed by postal ballot and of every meeting of its Board of Directors or of every committee of the Board, to be prepared and signed in such manner as may be prescribed and kept within thirty days of the conclusion of every such meeting concerned,",
        "citation": "Section 118(1), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 118(1) minutes entered within 30 days."
    },
    {
        "id": "UNTOUCHED_POS_010",
        "case_type": "passage_support",
        "generated_claim": "No individual shall be appointed as an auditor of a listed company for more than one term of five consecutive years under Section 139.",
        "authoritative_passage_id": "D1_SEC_139",
        "evidence_passage": "(2) No listed company or a company belonging to such class or classes of companies as may be prescribed, shall appoint or re-appoint— (a) an individual as auditor for more than one term of five consecutive years; and (b) an audit firm as auditor for more than two terms of five consecutive years:",
        "citation": "Section 139(2), Companies Act, 2013",
        "expected_status": "SUPPORTED",
        "expected_behavior": "ACCEPT",
        "explanation": "Section 139(2) auditor term limit: individual max 1 term of 5 consecutive years."
    },

    # --- NUMERICAL THRESHOLD MUTATIONS (N=6) ---
    {
        "id": "UNTOUCHED_NUM_001",
        "case_type": "numerical_mutation",
        "generated_claim": "The buy-back of equity shares in any financial year may extend up to fifty per cent of total paid-up equity capital.",
        "authoritative_passage_id": "D1_SEC_68",
        "evidence_passage": "Provided that the buy-back of equity shares in any financial year shall not exceed twenty-five per cent. of its total paid-up equity capital in that financial year:",
        "citation": "Section 68(2)(c) proviso, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated 25% cap to 50%."
    },
    {
        "id": "UNTOUCHED_NUM_002",
        "case_type": "numerical_mutation",
        "generated_claim": "Unclaimed dividend in the Unpaid Dividend Account is transferred to the IEPF after twelve years.",
        "authoritative_passage_id": "D1_SEC_124",
        "evidence_passage": "(5) Any money transferred to the Unpaid Dividend Account of a company which remains unpaid or unclaimed for a period of seven years from the date of such transfer shall be transferred by the company along with interest accrued, if any, thereon to the Fund established under sub-section (1) of section 125:",
        "citation": "Section 124(5), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated 7 years to 12 years."
    },
    {
        "id": "UNTOUCHED_NUM_003",
        "case_type": "numerical_mutation",
        "generated_claim": "An individual auditor may be appointed for more than three terms of five consecutive years in a listed company.",
        "authoritative_passage_id": "D1_SEC_139",
        "evidence_passage": "(2) No listed company or a company belonging to such class or classes of companies as may be prescribed, shall appoint or re-appoint— (a) an individual as auditor for more than one term of five consecutive years;",
        "citation": "Section 139(2)(a), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated one term of 5 years to three terms."
    },
    {
        "id": "UNTOUCHED_NUM_004",
        "case_type": "numerical_mutation",
        "generated_claim": "Under Section 186, a company may lend up to eighty per cent of its paid-up capital without any special resolution.",
        "authoritative_passage_id": "D1_SEC_186",
        "evidence_passage": "(2) No company shall directly or indirectly — (a) give any loan to any person or other body corporate; (b) give any guarantee or provide security... exceeding sixty per cent. of its paid-up share capital, free reserves and securities premium account or one hundred per cent. of its free reserves and securities premium account, whichever is more.",
        "citation": "Section 186(2), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated 60% statutory threshold to 80%."
    },
    {
        "id": "UNTOUCHED_NUM_005",
        "case_type": "numerical_mutation",
        "generated_claim": "Minutes of general meetings must be entered into books within 90 days of the meeting.",
        "authoritative_passage_id": "D1_SEC_118",
        "evidence_passage": "(1) Every company shall cause minutes of the proceedings of every general meeting... to be prepared and signed in such manner as may be prescribed and kept within thirty days of the conclusion of every such meeting concerned,",
        "citation": "Section 118(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated 30 days to 90 days."
    },
    {
        "id": "UNTOUCHED_NUM_006",
        "case_type": "numerical_mutation",
        "generated_claim": "An Audit Committee must consist of a minimum of five directors under Section 177.",
        "authoritative_passage_id": "D1_SEC_177",
        "evidence_passage": "(2) The Audit Committee shall consist of a minimum of three directors with independent directors forming a majority:",
        "citation": "Section 177(2), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Mutated minimum 3 directors to 5 directors."
    },

    # --- MODALITY MUTATIONS (N=5) ---
    {
        "id": "UNTOUCHED_MOD_001",
        "case_type": "modality_mutation",
        "generated_claim": "Prescribed public companies may optionally choose to constitute an Audit Committee if convenient.",
        "authoritative_passage_id": "D1_SEC_177",
        "evidence_passage": "(1) The Board of Directors of every listed public company and such other class or classes of companies, as may be prescribed, shall constitute an Audit Committee.",
        "citation": "Section 177(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Statute mandates 'shall constitute'; claim shifts to optional choice."
    },
    {
        "id": "UNTOUCHED_MOD_002",
        "case_type": "modality_mutation",
        "generated_claim": "A company may freely accept deposits from the public without following Chapter V rules.",
        "authoritative_passage_id": "D1_SEC_73",
        "evidence_passage": "(1) On and after the commencement of this Act, no company shall invite, accept or renew deposits under this Act from the public except in a manner provided under this Chapter:",
        "citation": "Section 73(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Statute explicitly prohibits ('no company shall accept'); claim asserts free permission."
    },
    {
        "id": "UNTOUCHED_MOD_003",
        "case_type": "modality_mutation",
        "generated_claim": "Every company may optionally maintain minutes of its general meetings at its discretion.",
        "authoritative_passage_id": "D1_SEC_118",
        "evidence_passage": "(1) Every company shall cause minutes of the proceedings of every general meeting... to be prepared and signed in such manner as may be prescribed and kept within thirty days of the conclusion of every such meeting concerned,",
        "citation": "Section 118(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Statute mandates 'shall cause minutes'; claim asserts optional discretion."
    },
    {
        "id": "UNTOUCHED_MOD_004",
        "case_type": "modality_mutation",
        "generated_claim": "A company may advance personal loans to its managing director without board approval.",
        "authoritative_passage_id": "D1_SEC_185",
        "evidence_passage": "(1) No company shall, directly or indirectly, advance any loan, including any loan represented by a book debt to, or give any guarantee or provide any security in connection with any loan taken by,— (a) any director of company,",
        "citation": "Section 185(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Statute prohibits ('no company shall advance any loan to director'); claim asserts permission."
    },
    {
        "id": "UNTOUCHED_MOD_005",
        "case_type": "modality_mutation",
        "generated_claim": "Listed companies may voluntarily rotate their statutory auditors only if shareholders request it.",
        "authoritative_passage_id": "D1_SEC_139",
        "evidence_passage": "(2) No listed company or a company belonging to such class or classes of companies as may be prescribed, shall appoint or re-appoint— (a) an individual as auditor for more than one term of five consecutive years; and (b) an audit firm as auditor for more than two terms of five consecutive years:",
        "citation": "Section 139(2), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Rotation is mandatory by statutory negative covenant ('shall not appoint'); claim shifts to voluntary."
    },

    # --- CITATION EXISTENCE & METADATA PROBES (N=4) ---
    {
        "id": "UNTOUCHED_CIT_001",
        "case_type": "citation_existence",
        "generated_claim": "Section 921 of the Companies Act, 2013 governs buyback of securities.",
        "authoritative_passage_id": "D1_SEC_921",
        "evidence_passage": "",
        "citation": "Section 921, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Phantom Section 921 does not exist in Companies Act (max section is 470)."
    },
    {
        "id": "UNTOUCHED_CIT_002",
        "case_type": "citation_metadata",
        "generated_claim": "Section 177 of the Companies Act, 2013 is titled 'Power of Registrar to Strike Off Defunct Companies'.",
        "authoritative_passage_id": "D1_SEC_177",
        "evidence_passage": "177. Audit Committee.—(1) The Board of Directors of every listed public company and such other class or classes of companies, as may be prescribed, shall constitute an Audit Committee.",
        "citation": "Section 177, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Section 177 is titled 'Audit Committee', not strike off (strike off is Section 248)."
    },
    {
        "id": "UNTOUCHED_CIT_003",
        "case_type": "citation_metadata",
        "generated_claim": "Section 124 of the Companies Act, 2013 is titled 'Punishment for Insider Trading'.",
        "authoritative_passage_id": "D1_SEC_124",
        "evidence_passage": "124. Unpaid Dividend Account.—(1) Where a dividend has been declared by a company but has not been paid or claimed within thirty days...",
        "citation": "Section 124, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Section 124 is titled 'Unpaid Dividend Account'."
    },
    {
        "id": "UNTOUCHED_CIT_004",
        "case_type": "citation_existence",
        "generated_claim": "Under Section 843 of the Companies Act, 2013, an audit committee must have ten members.",
        "authoritative_passage_id": "D1_SEC_843",
        "evidence_passage": "",
        "citation": "Section 843, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Phantom Section 843."
    },

    # --- TEMPORAL & AMENDMENT PROBES (N=4) ---
    {
        "id": "UNTOUCHED_TMP_001",
        "case_type": "temporal_verification",
        "generated_claim": "Private companies in 2026 are completely barred from giving loans to any director under Section 185 without MCA Central Government approval.",
        "authoritative_passage_id": "D1_SEC_185",
        "evidence_passage": "Provided that nothing contained in this sub-section shall apply to a private company— (a) in whose share capital no other body corporate has invested any money; (b) if the borrowings of such a company from banks or financial institutions... is less than twice of its paid-up share capital or fifty crore rupees, whichever is lower;",
        "citation": "Section 185 exemption notification, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "MCA Notification GSR 464(E) and 2017 Amendment Act exempted qualified private companies."
    },
    {
        "id": "UNTOUCHED_TMP_002",
        "case_type": "temporal_verification",
        "generated_claim": "Under Section 454, all corporate filing defaults must be prosecuted exclusively before a criminal magistrate.",
        "authoritative_passage_id": "D1_SEC_454",
        "evidence_passage": "(1) The Central Government may, by an order published in the Official Gazette, appoint as many officers of the Central Government, not below the rank of Registrar, as adjudicating officers for adjudging penalty under the provisions of this Act in the manner as may be prescribed.",
        "citation": "Section 454(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Companies (Amendment) Act 2019/2020 decriminalized filing defaults to in-house adjudication mechanism."
    },
    {
        "id": "UNTOUCHED_TMP_003",
        "case_type": "temporal_verification",
        "generated_claim": "A company must obtain Central Government approval for any debenture issue under Section 71.",
        "authoritative_passage_id": "D1_SEC_71",
        "evidence_passage": "(1) A company may issue debentures with an option to convert such debentures into shares, either wholly or partly at the time of redemption: Provided that the issue of debentures with an option to convert such debentures into shares, wholly or partly, shall be approved by a special resolution passed at a general meeting.",
        "citation": "Section 71(1), Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "No Central Government approval required; only special resolution."
    },
    {
        "id": "UNTOUCHED_TMP_004",
        "case_type": "temporal_verification",
        "generated_claim": "Every company must obtain a certificate of commencement of business from the Controller of Capital Issues.",
        "authoritative_passage_id": "D1_SEC_10A",
        "evidence_passage": "(1) A company incorporated after the commencement of the Companies (Amendment) Act, 2019 and having a share capital shall not commence any business or exercise any borrowing powers unless— (a) a declaration is filed by a director within a period of one hundred and eighty days of the date of incorporation of the company with the Registrar...",
        "citation": "Section 10A, Companies Act, 2013",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Controller of Capital Issues repealed in 1992; Section 10A requires director declaration to Registrar."
    },

    # --- COMPOUND CLAIMS (N=3) ---
    {
        "id": "UNTOUCHED_CMP_001",
        "case_type": "compound_claim",
        "generated_claim": "An Audit Committee must have a minimum of three directors, and all directors must be executive directors.",
        "authoritative_passage_id": "D1_SEC_177",
        "evidence_passage": "(2) The Audit Committee shall consist of a minimum of three directors with independent directors forming a majority:",
        "citation": "Section 177(2), Companies Act, 2013",
        "expected_status": "PARTIALLY_SUPPORTED",
        "expected_behavior": "QUALIFY",
        "explanation": "Clause 1 (min 3 directors) is supported; Clause 2 (all executive) is contradicted (independent majority required)."
    },
    {
        "id": "UNTOUCHED_CMP_002",
        "case_type": "compound_claim",
        "generated_claim": "A company may purchase its own shares under Section 68, and buyback can exceed fifty per cent of paid-up capital without any special resolution.",
        "authoritative_passage_id": "D1_SEC_68",
        "evidence_passage": "(1) ...a company may purchase its own shares or other specified securities... Provided that the buy-back of equity shares in any financial year shall not exceed twenty-five per cent. of its total paid-up equity capital...",
        "citation": "Section 68(1)-(2), Companies Act, 2013",
        "expected_status": "PARTIALLY_SUPPORTED",
        "expected_behavior": "QUALIFY",
        "explanation": "Clause 1 is supported; Clause 2 is contradicted (capped at 25% and requires special resolution)."
    },
    {
        "id": "UNTOUCHED_CMP_003",
        "case_type": "compound_claim",
        "generated_claim": "Unpaid dividend must be transferred to the Unpaid Dividend Account within seven days, and all unpaid funds become company profits after 30 days.",
        "authoritative_passage_id": "D1_SEC_124",
        "evidence_passage": "(1) Where a dividend has been declared... the company shall, within seven days from the date of expiry of the said period of thirty days, transfer the total amount of dividend which remains unpaid or unclaimed to a special account... called the Unpaid Dividend Account.",
        "citation": "Section 124(1), Companies Act, 2013",
        "expected_status": "PARTIALLY_SUPPORTED",
        "expected_behavior": "QUALIFY",
        "explanation": "Clause 1 is supported; Clause 2 is contradicted (never becomes company profit; transfers to IEPF)."
    },

    # --- FAIL-CLOSED / OUT OF DOMAIN (N=3) ---
    {
        "id": "UNTOUCHED_FCL_001",
        "case_type": "fail_closed_cases",
        "generated_claim": "Section 138 of the Negotiable Instruments Act imposes two years imprisonment for cheque bounce against individual drawer accounts.",
        "authoritative_passage_id": "NI_ACT_138",
        "evidence_passage": "",
        "citation": "Section 138, Negotiable Instruments Act, 1881",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Out of domain statutory probe outside core corporate repository."
    },
    {
        "id": "UNTOUCHED_FCL_002",
        "case_type": "fail_closed_cases",
        "generated_claim": "Section 25 of the Water (Prevention and Control of Pollution) Act mandates State Pollution Board consent prior to industrial discharge.",
        "authoritative_passage_id": "WATER_ACT_25",
        "evidence_passage": "",
        "citation": "Section 25, Water Act, 1974",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Out of domain environmental statute."
    },
    {
        "id": "UNTOUCHED_FCL_003",
        "case_type": "fail_closed_cases",
        "generated_claim": "Section 35 of the Consumer Protection Act, 2019 permits filing product liability complaints before the District Consumer Commission.",
        "authoritative_passage_id": "CPA_35",
        "evidence_passage": "",
        "citation": "Section 35, Consumer Protection Act, 2019",
        "expected_status": "CONTRADICTED",
        "expected_behavior": "REJECT",
        "explanation": "Out of domain consumer dispute legislation."
    }
]

def main():
    print(f"[*] Generating Fresh Untouched Test Benchmark (N={len(FRESH_CASES)})...")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for c in FRESH_CASES:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with open(OUT_FILE, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    receipt = {
        "benchmark_id": "HALO_FRESH_UNTOUCHED_TEST_35",
        "author": "Independent External Legal Evaluation Auditor",
        "protocol": "UNTOUCHED-TEST-v1.0",
        "case_count": len(FRESH_CASES),
        "status_distribution": {
            "SUPPORTED": sum(1 for c in FRESH_CASES if c["expected_status"] == "SUPPORTED"),
            "CONTRADICTED": sum(1 for c in FRESH_CASES if c["expected_status"] == "CONTRADICTED"),
            "PARTIALLY_SUPPORTED": sum(1 for c in FRESH_CASES if c["expected_status"] == "PARTIALLY_SUPPORTED")
        },
        "master_sha256": sha256,
        "canonical_file_path": str(OUT_FILE),
        "evaluation_rule": "FROZEN AND UNTOUCHED UNTIL FINAL EVALUATION RUN"
    }

    with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)

    print(f"[+] Successfully sealed {len(FRESH_CASES)} cases into: {OUT_FILE}")
    print(f"[+] SHA-256 Digest: {sha256}")
    print(f"[+] Freeze Receipt written to: {RECEIPT_FILE}")

if __name__ == "__main__":
    main()
