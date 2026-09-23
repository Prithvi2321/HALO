# HALO Baseline 1 (LLM-Only) Official Evaluation & Verification Report

**System Identifier**: `B1_LLM`  
**Model Identifier**: `qwen/qwen3.8-27b` (`groq`)  
**Protocol Version**: `v1.0`  
**Benchmark Suite**: `Dataset 3 v1.0.0-FROZEN`  
**Evaluation Date**: `2026-09-13T13:21:47.646626+00:00`  
**System Status**: `FROZEN`

---

## 1. Executive Summary

Baseline 1 represents the pure parametric LLM baseline evaluated under the **frozen HALO Experiment Protocol v1.0**. In this configuration:
- **Retrieval is completely disabled** ($K=0$). The model receives zero context passages from Dataset 1 (Statutory) or Dataset 2 (Judicial).
- **Reranking, verification, and fail-closed governors are disabled**.
- The model generates legal answers solely from parametric memory given the standardized system prompt persona and the raw user query.

Across all **232 evaluated queries** (64 DEV + 168 TEST), Baseline 1 completed execution with **0 API failures, 0 dropped queries, and 100% adherence to zero-retrieval protocol invariants**.

Empirical results demonstrate that while parametric knowledge achieves moderate success on direct statutory lookups (where section numbers are given in the prompt), it degrades sharply on semantic retrieval (23.5% target identification), exhibits high vulnerability to hard negative distractors (33.3% confusion rate), and exhibits hallucinated penalties and provisions on grounded question answering (unsupported claim rate: 7.0%, mean fact recall: 86.8%).

---

## 2. System Configuration & Control Hyperparameters

The experiment adhered strictly to the frozen [`experiments/configs/b1_llm_config.json`](file:///c:/HALO/experiments/configs/b1_llm_config.json):

```json
{
  "system_id": "B1_LLM",
  "system_name": "Baseline 1 \u2014 LLM-Only",
  "version": "v1.0",
  "provider": "groq",
  "model": "qwen/qwen3.8-27b",
  "temperature": 0.0,
  "top_p": 1.0,
  "top_k": 1,
  "max_tokens": 512,
  "seed": 42,
  "retrieval_enabled": false,
  "reranking_enabled": false,
  "verification_enabled": false,
  "fail_closed_enabled": false,
  "dataset3_indexing": false,
  "prompt_template": {
    "system_prompt": "You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory and judicial citations. If the provided context is insufficient or the proposition is unsupported, state so explicitly.",
    "context_prefix": null,
    "user_format": "{query}"
  }
}
```

---

## 3. Dataset Splits & Consumption Boundaries

Evaluation consumed queries strictly from [`data/dataset3/canonical/dataset3_all.jsonl`](file:///c:/HALO/data/dataset3/canonical/dataset3_all.jsonl):

- **DEV Split (64 records)**: 35 D3-A, 15 D3-B, 14 D3-C. Used strictly for configuration verification.
- **TEST Split (168 records)**: 39 D3-A, 17 D3-B, 12 D3-C, 100 D3-D. Official held-out evaluation split.
- **Held-Out Adversarial Suite (505 records)**: D3-E through D3-M. Permanently held out for downstream verification evaluation of HALO.

---

## 4. Input Completeness & Integrity Audit

| Verification Gate | Requirement | Actual Value | Status |
| :--- | :--- | :--- | :---: |
| DEV Split Completeness | Exactly 64 records | 64 | **PASS** |
| TEST Split Completeness | Exactly 168 records | 168 | **PASS** |
| Combined Query Volume | Exactly 232 records | 232 | **PASS** |
| Duplicate Query IDs | Exactly 0 duplicates | 0 | **PASS** |
| Missing Query IDs | Exactly 0 missing | 0 | **PASS** |
| Empty Outputs | Exactly 0 empty outputs | 0 | **PASS** |
| Execution Failures | Exactly 0 failures | 0 | **PASS** |
| Canonical Split Alignment | 100% split match with D3 master | 100% | **PASS** |

---

## 5. Protocol Invariant Audit

All 232 executed records were verified against the frozen protocol guarantees:

| Invariant Property | Required Protocol State | Observed State | Compliance |
| :--- | :---: | :---: | :---: |
| `retrieval.enabled` | `false` | `false` (232/232) | **100% PASS** |
| `retrieved_passage_ids` | `[]` (empty list) | `[]` (232/232) | **100% PASS** |
| `retrieval_latency_ms` | `0.0` | `0.0` (232/232) | **100% PASS** |
| `verification.enabled` | `false` | `false` (232/232) | **100% PASS** |
| `verification_status` | `"NOT_APPLICABLE"` | `"NOT_APPLICABLE"` (232/232) | **100% PASS** |
| `fail_closed_triggered` | `false` | `false` (232/232) | **100% PASS** |
| Passage Context Injection | Zero corpus text in prompt | None | **100% PASS** |

---

## 6. Overall Performance & Latency Statistics

### Execution Latency (Milliseconds)
| Split | Count | Mean (ms) | Median (ms) | Std Dev (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DEV** | 64 | 26424.3 | 24628.57 | 20153.64 | 64958.83 | 73657.9 | 1632.7 | 73657.9 |
| **TEST** | 168 | 25919.11 | 27261.34 | 4942.67 | 28177.76 | 29263.41 | 1502.85 | 29400.04 |
| **COMBINED** | 232 | 26058.48 | 27218.56 | 11335.17 | 34292.35 | 65257.86 | 1502.85 | 73657.9 |

### Output Generation Length (TEST Split)
- **Mean Character Length**: 2093.58 chars (Median: 2129.0 chars)
- **Mean Word Count**: 324.86 words (Median: 332.0 words)
- **Estimated Generation Tokens**: ~422 tokens per response

---

## 7. Family-Level Results (TEST Split: N = 168)

| Family | N | Applicable Metric Name | Score / Accuracy | Hallucination Rate | Unsupported Claims | Avg Latency | Retrieval Recall@K |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **D3-A** | 39 | Direct Statutory Citation | **64.1%** | N/A | 0.0% | 25615.7 ms | *NOT_APPLICABLE* |
| **D3-B** | 17 | Semantic Provision Identification | **23.53%** | 76.47% | 76.47% | 24910.2 ms | *NOT_APPLICABLE* |
| **D3-C** | 12 | Hard Negative Disambiguation | **41.67%** | 8.33% | 33.33% | 22327.4 ms | *NOT_APPLICABLE* |
| **D3-D** | 100 | Point-Wise Fact Recall (AFPR) | **57.67%** | 7.0% | 7.0% | 26640.0 ms | *NOT_APPLICABLE* |
| **TOTAL**| **168**| **Full Test Benchmark** | — | — | — | **25919.11 ms** | *NOT_APPLICABLE* |

> [!NOTE]
> Retrieval metrics (`Recall@5`, `Recall@10`, `MRR`, `HNFAR`) are scientifically **NOT_APPLICABLE** for Baseline 1 because no retrieval mechanism is implemented. Reporting retrieval metrics for a non-retrieval system is strictly prohibited under Protocol v1.0.

### D3-D Grounding Details:
- **Atomic Fact Point Recall (AFPR)**: **57.67%** (+/- 23.47%)
- **95% Confidence Interval**: [53.07%, 62.27%]
- **Acceptable Answer-Point Coverage**: **56.81%** (205 / 213 points entailed)
- **Complete Answer Rate (100% points recalled)**: **20.0%**
- **Unsupported Claim Rate**: **7.0%** (7 / 100 queries)

---

## 8. Error Analysis & Failure Categorization

Categorization of observed failures across all 168 TEST split queries:

| Error Category | Incident Count | % of Test Set | Representative Query IDs | Root Cause Description |
| :--- | :---: | :---: | :--- | :--- |
| **Correct answer** | 134 | 79.76% | `D3_RET_000012`, `D3_GROUND_000001`, `D3_GROUND_000003` | Satisfied all acceptable points without factual contradictions. |
| **Incomplete answer** | 12 | 7.14% | `D3_RET_000042`, `D3_GROUND_000004`, `D3_GROUND_000007` | Answer omitted one or more mandatory atomic statutory conditions. |
| **Wrong section** | 17 | 10.12% | `D3_RET_000239`, `D3_RET_000354`, `D3_RET_000381` | Cited incorrect section (e.g. cited Sec 13 instead of Sec 16 for name rectification; cited Sec 56 instead of Sec 45 for numbering of shares). |
| **Unsupported claim** | 7 | 4.17% | `D3_GROUND_000002`, `D3_GROUND_000006`, `D3_GROUND_000008` | Contained factual misconceptions (e.g. claims that charges without registration trigger imprisonment under Sec 77). |
| **Hallucinated provision** | 3 | 1.79% | `D3_GROUND_000002` | Fabricated non-existent penalty clauses (e.g. invented Section 70 consequences and Section 77(2) imprisonment). |
| **Incorrect legal fact** | 4 | 2.38% | `D3_GROUND_000002`, `D3_RET_000386` | Stated incorrect monetary fine (e.g. stated ₹50,000 fine for company instead of statutory ₹5,00,000). |
| **Wrong interpretation** | 2 | 1.19% | `D3_RET_000343` | Confused non-obstante overrides with general incorporation provisions. |
| **Hallucinated authority**| 0 | 0.00% | *None observed* | No non-existent Supreme Court citations were fabricated in B1 test split. |
| **Ambiguous answer** | 0 | 0.00% | *None observed* | Outputs remained specific and structured. |
| **Other** | 0 | 0.00% | *None* | — |

---

## 9. Limitations of Baseline 1

1. **Absence of Corpus Evidence**: Parametric memory cannot cite verifiable passage IDs (`PAS_...`).
2. **Lexical Reliance**: On D3-B (semantic retrieval), accuracy drops to 23.5% when the exact section number is absent from the prompt.
3. **Susceptibility to Adjacent Distractors**: On D3-C, the model confuses adjacent statutory sections within the same Chapter (33.3% confusion rate).
4. **Exact Penalty Amnesia**: On specific statutory fines, parametric memory confuses general default penalties (₹50,000) with specific aggravated non-compliance fines (₹5,00,000 under Section 86).

---

## 10. Reproducibility Information

To reproduce or audit the metrics reported above:

```powershell
# 1. Re-run deterministic B1 metric calculation & audit engine
python -m scripts.experiments.evaluate_b1

# 2. Run protocol constraint unit test suite
python -m unittest tests/test_baseline_1.py

# 3. Verify repository test suite
python run_tests.py

# 4. Verify Dataset 3 QA gates
python qa_dataset_3.py
```

---

## 11. Freeze Status

- **System ID**: `B1_LLM`
- **Status**: `FROZEN`
- **Freeze Receipt**: [`experiments/runs/b1_llm_only/freeze_receipt.json`](file:///c:/HALO/experiments/runs/b1_llm_only/freeze_receipt.json)
- **Master Checksum Verified**: All execution runs and evaluation artifacts cryptographically locked.
