# HALO Expanded Verification Benchmark Suite

**Protocol Version**: `v1.0-FROZEN`  
**Status**: `OFFICIALLY_AUDITED_AND_CRYPTOGRAPHICALLY_FROZEN`  
**Master Root SHA-256**: `a14fafdde0b753f675f79d29deb5133dae65acad5ec424f1ff75502bf180fb97`  
**Receipt Signature**: `a32b6f51af4945c76df7f5649a785bb7c690ac80a01d745dee2d996ed6ee03a4`  
**Total Canonical Cases**: 180  

---

## 1. Overview & Purpose

The **HALO Expanded Verification Benchmark Suite** is the authoritative, multi-tier legal fact-checking and post-generation hallucination benchmark for the HALO project. It is purpose-built to evaluate post-retrieval verification components—including atomic claim extraction, multi-tier citation verification, natural language inference (NLI) evidence verification, chronological amendment validation, doctrinal conflict detection, and fail-closed refusal governance.

All grounded claims in this benchmark are derived strictly and deterministically from:
- **Dataset 1 (Statutory Corpus)**: *Companies Act, 2013* (1,640 passages | `37c5ced49fc3925342a7eebfc84eb2988f863166b60c0a8cf527aefae0e8c27c`)
- **Dataset 2 (Judicial Corpus)**: Supreme Court, NCLAT, and High Court commercial judgments (**1,133 passages** across 57 source judgments | `43af9b6ed2df7be5489a71e81cf1f0125469d0cbe4443d0e536edb35703d3996`)

The benchmark has been audited against all 18 Acceptance Gates (G1–G18) with a 100% pass rate and zero contamination against held-out Dataset 3 or Baseline 1–5 evaluation query logs.

---

## 2. Directory Architecture & 19 Registered Assets

The benchmark registers **19 distinct assets** (16 JSONL dataset files + 3 specification/manifest JSON files) in [`manifests/SHA256SUMS.txt`](file:///c:/HALO/halo_datasets/manifests/SHA256SUMS.txt):

```text
halo_datasets/
├── benchmark_plan.json                  # [1/19] Formal benchmark specification & target distributions
├── manifests/
│   ├── hash_specification.json          # [2/19] 16-field deterministic SHA-256 canonical hashing rules
│   ├── SHA256SUMS.txt                   # Checksums of all 19 registered benchmark assets
│   ├── dataset_manifest.json            # Master dataset manifest with counts, distributions, and digests
│   └── VERIFICATION_DATASET_FREEZE_RECEIPT.json # Official freeze receipt (sealed)
├── claim_evidence/
│   ├── claim_evidence.jsonl             # [3/19] Consolidated 180-record benchmark suite
│   └── compound_claims.jsonl            # [4/19] Multi-clause compound propositions (16 cases)
├── citation_verification/
│   ├── citation_existence.jsonl         # [5/19] Act/section/case existence checks (24 cases)
│   ├── citation_metadata.jsonl          # [6/19] Court/year/section/para metadata mismatch (22 cases)
│   └── citation_verification.jsonl      # [7/19] Unified citation verification dataset (46 cases)
├── passage_verification/
│   ├── passage_verification.jsonl       # [8/19] Core textual support & contradiction (24 cases)
│   ├── numerical_mutations.jsonl        # [9/19] Systematic quantitative threshold mutations (24 cases)
│   └── modality_mutations.jsonl         # [10/19] Modal shift mutations (shall vs may) (16 cases)
├── temporal/
│   └── temporal_verification.jsonl      # [11/19] 2015/2020 amendment awareness & repeal checks (18 cases)
├── authority/
│   └── authority_verification.jsonl     # [12/19] Administrative & judicial forum authority (10 cases)
├── conflict/
│   └── conflict_cases.jsonl             # [13/19] Statutory vs judicial tensions & hierarchies (8 cases)
├── adversarial/
│   └── adversarial_cases.jsonl          # [14/19] 10 adversarial attacks (displacement, inversion, fabrication)
├── fail_closed/
│   └── fail_closed_cases.jsonl          # [15/19] Out-of-domain & zero-evidence refusal triggers (8 cases)
├── splits/
│   ├── train.jsonl                      # [16/19] Train split (125 cases, 69.44%)
│   ├── dev.jsonl                        # [17/19] Validation split (27 cases, 15.00%)
│   ├── test.jsonl                       # [18/19] Held-out Test split (28 cases, 15.56%)
│   └── split_manifest.json              # [19/19] Passage-family disjoint split manifest
├── generators/
│   ├── build_verification_benchmark.py  # Master benchmark generator
│   ├── build_manifest.py                # Manifest & checksum builder
│   └── freeze_benchmark.py              # Gate auditor & cryptographic freeze engine
└── qa/
    ├── run_all_qa.py                    # Master test harness evaluating Gates G1-G18
    ├── qa_schema.py                     # G1/G2: 16-field schema & enum validator
    ├── qa_provenance.py                 # G6: Passage ID grounding verifier
    ├── qa_source_integrity.py           # G5: Dataset 1 & Dataset 2 SHA-256 verifier
    ├── qa_duplicates.py                 # G7/G8: ID and claim deduplication audit
    ├── qa_splits.py                     # G9: Passage-family disjointness auditor
    ├── qa_balance.py                    # G10-G12: Class coverage, category, and difficulty balance
    ├── qa_hashes.py                     # G15: Byte-for-byte SHA-256 hash determinism
    ├── qa_temporal.py                   # G14: Amendment operation validator
    ├── qa_adversarial.py                # G13: Adversarial attack metadata auditor
    ├── qa_contamination.py              # G16/G17: Zero-leakage audit against D3 & Baselines
    ├── qa_master_report.json            # Machine-readable output of all 18 gates
    ├── dedup_report.json                # Deduplication audit report
    ├── source_coverage.json             # Source passage coverage report
    └── contamination_report.json        # Contamination audit report
```

---

## 3. Schema & Canonical Content Hashing

Every record in the benchmark strictly contains exactly 16 deterministic fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique case identifier (e.g., `CIT_EXIST_001`, `NUM_MUT_014`) |
| `query` | `str` | Legal prompt or query |
| `generated_claim` | `str` | The asserted legal proposition to be verified |
| `citation` | `dict` | Structured statutory or judicial citation metadata |
| `expected_status` | `str` | Target status: `SUPPORTED`, `CONTRADICTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `FABRICATED_CITATION`, `FLAGGED` |
| `authoritative_passage_id` | `str` | Grounding passage ID from D1/D2 or `"NONE"` for ungrounded/out-of-domain |
| `evidence_passage` | `str` | Canonical excerpt from authoritative corpus |
| `verification_tier` | `str` | Tier: `EXISTENCE`, `METADATA`, `PASSAGE_SUPPORT`, `TEMPORAL`, `CONFLICT`, `FAIL_CLOSED` |
| `difficulty` | `str` | Stratification: `easy`, `medium`, `hard` |
| `source` | `str` | Canonical source description |
| `source_dataset` | `str` | `"D1"` (Statutory) or `"D2"` (Judicial) |
| `case_type` | `str` | Primary category identifier (1 of 11 mutually exclusive categories) |
| `mutation_type` | `str` | Mutation operation applied or `None` for authentic claims |
| `mutation_details` | `dict` | Structured parameterization of the mutation |
| `expected_behavior` | `str` | Governor policy action: `ACCEPT`, `REJECT`, `QUALIFY` |
| `explanation` | `str` | Detailed analytical reasoning for the ground-truth label |
| `content_hash` | `str` | Deterministic SHA-256 computed over the 16 fields sorted alphabetically |

---

## 4. Benchmark Composition & Distributions

### A. The 11 Mutually Exclusive Primary Categories (180 Total Records)
Every case belongs to exactly one primary category. The counts sum exactly to 180:

$$\sum_{i=1}^{11} C_i = 24 + 22 + 24 + 24 + 16 + 16 + 18 + 10 + 8 + 10 + 8 = 180$$

| # | Primary Category | Cases | Share | Core Evaluative Objective |
| :-: | :--- | :---: | :---: | :--- |
| **1** | `citation_existence` | 24 | 13.33% | Verifies existence of Act, Section, Case name, and Reporter citation against authentic corpus vs phantom citations |
| **2** | `citation_metadata` | 22 | 12.22% | Catches court discrepancies, year mismatches, section heading errors, and non-existent paragraph numbers |
| **3** | `passage_support` | 24 | 13.33% | Tests standard textual entailment vs substantive legal contradiction against authentic statutory/judicial text |
| **4** | `numerical_mutation` | 24 | 13.33% | Tests quantitative precision across codified thresholds (₹50cr vs ₹500cr, 21 vs 14 days, 2% vs 5%) |
| **5** | `modality_mutation` | 16 | 8.89% | Tests modal shift detection ("shall" mandatory vs "may" discretionary) |
| **6** | `compound_claim` | 16 | 8.89% | Tests atomic claim decomposition of conjoined propositions with mixed truth values (`PARTIALLY_SUPPORTED`) |
| **7** | `temporal_verification` | 18 | 10.00% | Evaluates chronological awareness of 2015/2020 parliamentary amendments, omitted capital, and 1956 repeal |
| **8** | `authority_verification` | 10 | 5.56% | Evaluates forum legitimacy (NCLT, NCLAT, Special Courts vs fabricated regulatory bodies) |
| **9** | `conflict_detection` | 8 | 4.44% | Identifies statutory vs judicial tensions and Article 141 forum hierarchy (SC > NCLAT/HC) |
| **10** | `adversarial_cases` | 10 | 5.56% | 10 stress tests against ratio inversion, section displacement, and negation attacks |
| **11** | `fail_closed_cases` | 8 | 4.44% | Triggers governor fail-closed quarantine on ungrounded/out-of-domain queries |
| — | **Total Canonical Benchmark** | **180** | **100.00%** | Comprehensive post-retrieval verification benchmark |

### B. Classification of the 20 Negative Control Cases
The 20 negative control and refusal cases (`authoritative_passage_id = "NONE"`) are explicitly typed into three distinct failure modes:
1. **Synthetic Adversarial Attacks (10 cases)**: Real citations paired with inverted ratios, displaced sections, or negation attacks.
2. **Out-of-Domain Traps (3 cases)**: Queries outside Indian corporate/commercial law (e.g. IPC Section 302 murder, Patents Act Section 53 term, Air Pollution Act Section 37).
3. **Zero-Evidence / Non-Existent Provisions (7 cases)**: Assertions regarding fabricated sections (e.g. Section 999, Section 888, Section 490, Section 500), non-existent statutes (Metaverse Act, AI Commercial Code), or prohibited bearer shares.

### C. Class Distribution Audit (Intentional Skew Acknowledged)
The benchmark intentionally skews toward negative/mutated classes because its core research objective is **hallucination detection and false-acceptance suppression**:

| Ground-Truth Status | Count | Percentage | Research Function |
| :--- | :---: | :---: | :--- |
| `CONTRADICTED` | 88 | 48.89% | Primary test for substantive, numerical, modal, and conflict contradictions |
| `SUPPORTED` | 41 | 22.78% | Positive control ensuring accurate claims are preserved without false refusal |
| `PARTIALLY_SUPPORTED` | 21 | 11.67% | Evaluates propositional decomposition (accept valid clause, isolate invalid) |
| `FLAGGED` | 15 | 8.33% | Tests advisory quarantine for metadata errors and temporal ambiguity |
| `FABRICATED_CITATION` | 14 | 7.78% | Tests Tier 1 citation existence filtering |
| `UNSUPPORTED` | 1 | 0.56% | Negative probe for assertions completely absent from evidence passage |

> [!NOTE]
> **Imbalance Note**: This distribution is intentionally not uniform. In legal verification benchmarks, contradictory and fabricated assertions are over-sampled to robustly evaluate safety mechanisms and measure Unsupported-Claim False Acceptance Rate (UFAR).

### D. Difficulty Stratification
- **Easy**: 46 cases (25.56%)
- **Medium**: 52 cases (28.89%)
- **Hard**: 82 cases (45.56%)

---

## 5. Split Architecture & Test Set Hygiene

| Split | Cases | Share | Unique Passage Families | Cross-Split Leakage | Methodological Purpose |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Train** | 125 | 69.44% | 25 | **Zero (0)** | Development, prompt iteration, and pipeline debugging |
| **Dev** | 27 | 15.00% | 9 | **Zero (0)** | Hyperparameter selection and threshold tuning (confidence weights, NLI cutoffs, temporal boundaries) |
| **Test** | 28 | 15.56% | 12 | **Zero (0)** | **Strictly held-out for ONE single, final evaluation run; zero threshold fitting** |

> [!IMPORTANT]
> **Strict Test-Set Protocol**: In accordance with legal NLP evaluation standards, the **Test set (28 cases) must remain strictly held-out and untouched** during component development and threshold tuning. All threshold calibration (confidence weights, entailment cutoffs, governor trigger thresholds) must be performed exclusively on the Dev set.

---

## 6. Acceptance Gates & Verification Audit (G1–G18)

Audited by [`halo_datasets/qa/run_all_qa.py`](file:///c:/HALO/halo_datasets/qa/run_all_qa.py):

| Gate | Status | Gate Name | Verification Finding |
| :---: | :---: | :--- | :--- |
| **G1** | `[PASS]` | Total Record Count | **180 records** verified (Target: 180, Min: 100) |
| **G2** | `[PASS]` | Schema Conformance | **180/180 records** contain all 16 canonical fields |
| **G3** | `[PASS]` | Expected Status Enum | **6 valid classes** verified |
| **G4** | `[PASS]` | Verification Tier Enum | **All 6 tiers** verified |
| **G5** | `[PASS]` | Source Corpora Integrity | Dataset 1 (1,640 passages) & Dataset 2 (**1,133 passages**) digests verified byte-for-byte |
| **G6** | `[PASS]` | Passage Provenance Tracing | **160 grounded passages** verified against D1/D2; 20 ungrounded cases properly flagged |
| **G7** | `[PASS]` | Record ID Uniqueness | **180 unique IDs**, 0 duplicates |
| **G8** | `[PASS]` | Claim Text Deduplication | **180 unique claims**, 0 duplicates |
| **G9** | `[PASS]` | Split Disjointness & Zero Leakage | Train: 125, Dev: 27, Test: 28 (**Zero passage overlap**) |
| **G10** | `[PASS]` | Class Distribution Coverage | All 6 classes represented; distribution documented and imbalance acknowledged |
| **G11** | `[PASS]` | Category Distribution Coverage | **All 11 mutually exclusive categories** active (including `compound_claim`) |
| **G12** | `[PASS]` | Difficulty Distribution Balance | Easy: 46, Medium: 52, Hard: 82 |
| **G13** | `[PASS]` | Adversarial Suite Alignment | 10/10 adversarial attacks specify attack metadata and `REJECT` expectation |
| **G14** | `[PASS]` | Temporal Amendment Provenance | 18/18 temporal cases verified against 2015/2020 amendments and 1956 repeal |
| **G15** | `[PASS]` | Content Hash Determinism | 180/180 SHA-256 `content_hash` match canonical recomputation |
| **G16** | `[PASS]` | Dataset 3 Contamination Audit | Audited against **1,032 canonical D3 queries**: **0 overlaps (0.00%)** |
| **G17** | `[PASS]` | Baseline 1–5 Contamination Audit | Audited against **232 baseline queries**: **0 overlaps (0.00%)** |
| **G18** | `[PASS]` | Fail-Closed Expected-Behavior Integrity | 8 fail-closed benchmark cases have explicitly defined expected refusal behaviors (`authoritative_passage_id = 'NONE'`, expected `REJECT`/`QUALIFY`). Actual runtime governor recall to be evaluated in downstream phase. |

---

## 7. Cryptographic Freeze Seal

According to [`manifests/VERIFICATION_DATASET_FREEZE_RECEIPT.json`](file:///c:/HALO/halo_datasets/manifests/VERIFICATION_DATASET_FREEZE_RECEIPT.json), the benchmark was cryptographically sealed by executing [`generators/freeze_benchmark.py`](file:///c:/HALO/halo_datasets/generators/freeze_benchmark.py):

* **Benchmark ID**: `HALO_EXPANDED_VERIFICATION_BENCHMARK_SUITE`
* **Protocol Version**: `v1.0-FROZEN`
* **Status**: `OFFICIALLY_AUDITED_AND_CRYPTOGRAPHICALLY_FROZEN`
* **Master Root SHA-256 Digest**: `a14fafdde0b753f675f79d29deb5133dae65acad5ec424f1ff75502bf180fb97`
* **Receipt Signature**: `a32b6f51af4945c76df7f5649a785bb7c690ac80a01d745dee2d996ed6ee03a4`
* **Read-Only Enforced**: `true`
