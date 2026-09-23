# HALO Experiment Protocol v1.0
## Official Evaluation Specification for HALO and Comparative Baselines

**Document Version**: `v1.0`  
**Status**: `OFFICIAL & FROZEN`  
**Corpus Dependencies**: 
- Dataset 1 (`v1.0.0-FROZEN`, 504 sections, 1,640 passages, SHA-256 verified)
- Dataset 2 (`v1.0.0-FROZEN`, 57 judgments, 1,133 passages, 552 citations, SHA-256 verified)
- Dataset 3 (`v1.0.0-FROZEN`, 1,032 test records across 13 sub-families, SHA-256 verified)

**Primary Evaluated Systems**:
1. **Baseline 1**: LLM-only (No Retrieval)
2. **Baseline 2**: Dense Vector RAG
3. **Baseline 3**: BM25 + Dense Hybrid RAG
4. **Baseline 4**: Hybrid RAG + Cross-Encoder Reranking
5. **HALO**: Hybrid RAG + Reranking + Three-Tier Verification + Fail-Closed Governor

---

## 1. Exact Role of Dataset 3 in Evaluation

Dataset 3 ($N = 1,032$) serves as the **immutable evaluation and adversarial benchmark suite**. Its role is strictly defined by the following invariant boundaries:

1. **Pure Benchmark Isolation**:
   - Dataset 3 is **never indexed** in the retrieval knowledge base.
   - The retrieval corpus consists solely of the 2,773 frozen passages from Dataset 1 (1,640 statutory passages) and Dataset 2 (1,133 judicial passages).
   - Under no circumstances may Dataset 3 queries, gold answers, or synthetic perturbations be added to the vector store, BM25 inverted index, or training corpus.

2. **Pillar-Specific Evaluation Roles**:
   - **Retrieval Pillar (D3-A, D3-B, D3-C: 427 records)**: Evaluates candidate retrieval engines (Baselines 2, 3, 4, and HALO). System outputs ranked lists of passage IDs evaluated against `positive_evidence_ids` and `relevant_passage_ids`.
   - **Grounding Pillar (D3-D: 100 records)**: Evaluates end-to-end response generation across all five systems against atomic `acceptable_answer_points` and penalizing `unacceptable_claims`.
   - **Citation Verification Pillar (D3-E, D3-F, D3-G: 300 records)**: Evaluates citation integrity and hallucination detection. Systems are tested on whether they accept authentic records, flag metadata anomalies, and reject fabricated cases or unsupported propositions.
   - **Systemic Robustness Pillar (D3-H through D3-M: 205 records)**: Evaluates boundary resilience, fail-closed enforcement on non-existent provisions, clarification elicitation on ambiguous queries, temporal disambiguation, conflict detection, out-of-scope rejection, and resistance to prompt injections.

3. **Zero Pre-Generated Answers**:
   - Dataset 3 contains ground-truth legal facts and adversarial perturbations, but **zero model-generated responses**.
   - Model generations are produced dynamically during experiment execution under the frozen protocol settings.

---

## 2. Train / Dev / Test Usage

To prevent data contamination and overfitting, dataset splits must be consumed strictly as follows:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DATASET 3 PARTITIONING                          │
├────────────────────────────┬─────────────────────────────┬─────────────┤
│      TRAIN SPLIT (70%)     │       DEV SPLIT (15%)       │ TEST (15%)  │
│  - Statutory: 352 Sections │  - Statutory: 78 Sections   │ - 74 Secs   │
│  - Judicial:  41 Judgments │  - Judicial:  7 Judgments   │ - 9 Juds    │
│  - Passages: 1,939 (70.0%) │  - Passages: 425 (15.3%)    │ - 409 (14.7)│
├────────────────────────────┼─────────────────────────────┼─────────────┤
│          USAGE:            │           USAGE:            │   USAGE:    │
│  • Dense/BM25 tuning       │  • Verification threshold   │ • SINGLE-   │
│  • Fusion parameter search │    calibration (tau)        │   PASS      │
│  • Reranker fine-tuning    │  • Prompt validation        │   FINAL     │
│  • Few-shot demos          │  • Model checkpoint pick    │   EVAL      │
└────────────────────────────┴─────────────────────────────┴─────────────┘
```

1. **Train Split**:
   - Permitted for: Tuning BM25 parameters ($k_1, b$), calibrating dense-sparse fusion weights ($\alpha$), training/fine-tuning dense encoders or cross-encoders, and selecting few-shot exemplar demonstrations.
2. **Dev Split**:
   - Permitted for: Model checkpoint selection, tuning verification decision thresholds ($\tau_{\text{entailment}}$, $\tau_{\text{evidence}}$), and prompt format validation.
3. **Test Split**:
   - Permitted for: **Final, unadjusted evaluation only**.
   - **Strict prohibition**: No parameter adjustments, prompt modifications, threshold alterations, or error-analysis-driven tuning on the Test split.
4. **Adversarial Benchmark Suites (D3-E through D3-M)**:
   - Treated as held-out zero-shot diagnostic suites. Evaluated without task-specific supervised fine-tuning to measure authentic generalization.

---

## 3. Control Variables (Identical Across All Five Systems)

To isolate architectural contributions, the following parameters are held constant across all five systems:

1. **Target Evaluation Queries**: The identical prompt query string, input ordering, and test instance metadata.
2. **Foundational Generative Model (LLM)**: Identical model identifier, weights, API provider, and quantization.
3. **Sampling Hyperparameters**:
   - `temperature = 0.0` (greedy decoding for deterministic reproducibility)
   - `top_p = 1.0`
   - `top_k = 1`
   - `max_tokens = 1024`
   - `presence_penalty = 0.0`
   - `frequency_penalty = 0.0`
4. **Base System Prompt Persona**:
   ```text
   You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory and judicial citations. If the provided context is insufficient or the proposition is unsupported, state so explicitly.
   ```
5. **Hardware & Execution Environment**:
   - Operating System: Windows 11 / Linux (POSIX equivalent)
   - Python Version: 3.11+
   - PyTorch Seed: `42`
   - Global Seed: `PYTHONHASHSEED=42`

---

## 4. Independent Variables (System-by-System Architectural Changes)

| System Name | Retrieval Mechanism | Reranking Stage | Verification Pipeline | Fail-Closed Governor | Context Given to LLM |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 1** (LLM-only) | None ($K=0$) | None | None | None | None (Parametric memory only) |
| **Baseline 2** (Dense RAG) | Dense Bi-Encoder ($K=5$) | None | None | None | Top 5 dense passages |
| **Baseline 3** (Hybrid RAG) | Dense ($K=50$) + BM25 ($K=50$) $\rightarrow$ RRF ($K=5$) | None | None | None | Top 5 RRF passages |
| **Baseline 4** (Rerank RAG) | Dense + BM25 $\rightarrow$ RRF ($K=50$) | Cross-Encoder Reranker $\rightarrow$ Top 5 | None | None | Top 5 reranked passages |
| **HALO** (Proposed) | Dense + BM25 $\rightarrow$ RRF ($K=50$) | Cross-Encoder Reranker $\rightarrow$ Top 10 | Three-Tier Verification Engine | Fail-Closed Policy ($\tau_{\text{evidence}}$) | Verified Top 5 passages + Tier status |

---

## 5. LLM Specification

- **Primary Generative Model**: `google/gemini-1.5-pro` (or open-source local equivalent: `meta-llama/Meta-Llama-3.1-70B-Instruct`).
- **Target Context Window**: 128,000 tokens supported; input prompt capped at 8,192 tokens.
- **Inference Runtime**: Official Google GenAI SDK (`google-genai` / `google-generativeai`) or vLLM server (`vllm serve --model meta-llama/Meta-Llama-3.1-70B-Instruct --gpu-memory-utilization 0.95`).
- **Precision**: 16-bit floating point (bfloat16) or API standard.

---

## 6. Embedding Model Specification

- **Dense Encoder**: `BAAI/bge-large-en-v1.5`
  - Output Embedding Dimension: $1,024$
  - Max Sequence Length: $512$ tokens
  - Normalization: L2 normalized vectors (enabling inner product = cosine similarity)
  - Query Instruction: `"Represent this sentence for searching relevant passages: "`
  - Passage Instruction: `""` (no prefix for corpus passages)
- **Alternative for Ablation (Legal Domain)**: `nlpaueb/legal-bert-base-uncased` ($768$ dimensions).

---

## 7. BM25 Configuration

- **Inverted Index Implementation**: `rank_bm25.BM25Okapi`
- **Parameters**:
  - $k_1 = 1.5$ (term frequency saturation)
  - $b = 0.75$ (document length normalization)
  - $\epsilon = 0.25$
- **Tokenizer**: Legal-aware regular expression tokenizer:
  `\b[A-Za-z]+(?:'[A-Za-z]+)?\b|\b\d+(?:[\(\)\.\-/\w]+)?\b`
  Preserves expressions like `Section 135(1)`, `DIR-12`, `(2019) 1 SCC 100`, and `₹5,00,000`.
- **Stopwords**: Standard English stopword list with legal-operator protection. The following terms are **never** dropped:
  `["shall", "must", "may", "not", "no", "without", "proviso", "omitted", "substituted"]`.

---

## 8. Hybrid Retrieval & Score Fusion

- **Fusion Algorithm**: Reciprocal Rank Fusion (RRF)
  $$RRF(d) = \sum_{m \in \{Dense, BM25\}} \frac{1}{k + rank_m(d)}$$
  where rank constant $k = 60$.
- **Candidate Pool Size**:
  - Top $K_{BM25} = 50$ retrieved documents.
  - Top $K_{Dense} = 50$ retrieved documents.
  - Union pool: $K_{Fusion} = 50$ unique candidates scored by RRF.

---

## 9. Cross-Encoder Reranker Specification

- **Model**: `BAAI/bge-reranker-large`
- **Input Format**: Single sequence pair: `[CLS] Query [SEP] Passage Text [SEP]`
- **Max Input Length**: $512$ tokens (passages exceeding 512 tokens truncated from the end).
- **Scoring Function**: Raw output logit mapped via sigmoid $\sigma(z) \in [0, 1]$.
- **Target Output**: Top $K_{\text{rerank}} = 10$ highest-scoring passages passed to the verification engine.

---

## 10. Top-K Retrieval Settings Matrix

| Parameter Stage | Baseline 1 | Baseline 2 | Baseline 3 | Baseline 4 | HALO |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dense Candidate Pool ($K_{\text{dense}}$) | 0 | 5 | 50 | 50 | 50 |
| BM25 Candidate Pool ($K_{\text{bm25}}$) | 0 | 0 | 50 | 50 | 50 |
| RRF Fusion Pool ($K_{\text{rrf}}$) | 0 | 0 | 50 | 50 | 50 |
| Cross-Encoder Evaluated ($K_{\text{ce\_in}}$) | 0 | 0 | 0 | 50 | 50 |
| Cross-Encoder Selected ($K_{\text{ce\_out}}$) | 0 | 0 | 0 | 5 | 10 |
| Passages Passed to Verifier ($K_{\text{verif}}$) | 0 | 0 | 0 | 0 | 10 |
| Final Passages Injected into LLM Context ($K_{\text{llm}}$)| **0** | **5** | **5** | **5** | **Verified Top 5** |

---

## 11. Generation Settings & Prompt Structure

For retrieval-augmented systems (Baselines 2, 3, 4, and HALO), context is injected using the following standardized schema:

```text
[SYSTEM]
You are an authoritative Indian Legal Research Assistant specializing in the Companies Act, 2013 and Indian corporate jurisprudence. Answer the inquiry factually, accurately, and with precise statutory and judicial citations.

CRITICAL GROUNDING RULES:
1. Rely strictly on the provided Context Passages below.
2. Do NOT extrapolate or assume statutory provisions not present in the context.
3. If the context does not contain sufficient legal evidence to establish the answer, state clearly: "INSUFFICIENT_EVIDENCE: The provided corpus does not contain statutory or judicial evidence to substantiate this inquiry."
4. Every legal assertion must cite its supporting passage ID (e.g. [PAS_ACT_COMPANIES_2013_SEC_135_001]).

[CONTEXT PASSAGES]
<passage id="PAS_ID_1">
[Passage Text 1]
</passage>
<passage id="PAS_ID_2">
[Passage Text 2]
</passage>
...

[QUESTION]
{query_text}

[ANSWER FORMAT]
Provide a structured legal response followed by a formal list of cited provisions.
```

---

## 12. Reproducibility & Determinism Configuration

All experiments must log and adhere to the following reproducibility manifest:

```python
REPRODUCIBILITY_CONFIG = {
    "random_seed": 42,
    "numpy_seed": 42,
    "torch_seed": 42,
    "cuda_deterministic": True,
    "temperature": 0.0,
    "top_p": 1.0,
    "top_k": 1,
    "max_tokens": 1024,
    "corpus_manifest_sha256": "df75c2b2567139a368797dd00375bf4b69b6d4cd9263e87bfa4c9715a0d9ce4f"
}
```

---

## 13. Standardized Output Format

Every system run must emit individual execution records in JSON Lines format adhering to the following schema:

```json
{
  "experiment_id": "EXP_HALO_TEST_20260912_v1.0",
  "system_id": "HALO",
  "query_id": "D3_RET_000001",
  "benchmark_family": "D3-A",
  "split": "test",
  "query": "What does Section 1 of the Companies Act, 2013 prescribe regarding short title, extent, commencement and application?",
  "retrieval": {
    "retrieved_passage_ids": [
      "PAS_ACT_COMPANIES_2013_SEC_1_001",
      "PAS_ACT_COMPANIES_2013_SEC_1_002"
    ],
    "retrieval_scores": [0.9421, 0.8812],
    "retrieval_latency_ms": 38.4
  },
  "generation": {
    "predicted_answer": "Section 1 provides that the Act extends to the whole of India...",
    "cited_statutory_sections": ["ACT_COMPANIES_2013_SEC_1"],
    "cited_case_citations": [],
    "generation_latency_ms": 310.2
  },
  "verification": {
    "verification_status": "SUPPORTED",
    "tier1_existence": "PASS",
    "tier2_metadata": "PASS",
    "tier3_entailment": "PASS",
    "fail_closed_triggered": false
  },
  "total_latency_ms": 348.6,
  "timestamp_utc": "2026-09-12T23:45:00Z"
}
```

---

## 14. Formal Evaluation Metrics

### A. Retrieval Metrics (D3-A, D3-B, D3-C)
- **Recall@K** ($K \in \{1, 5, 10\}$):
  $$\text{Recall@K} = \frac{|\text{Retrieved@K} \cap \text{Relevant}|}{|\text{Relevant}|}$$
- **Mean Reciprocal Rank (MRR)**:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
- **NDCG@K** ($K \in \{5, 10\}$): Normalized Discounted Cumulative Gain.
- **Hard Negative False Acceptance Rate (HNFAR)** (on D3-C):
  $$\text{HNFAR} = \frac{\text{Count}(\text{Hard Negative in Top } 5)}{|Q_{\text{hard}}|}$$

### B. Grounding & Generation Metrics (D3-D)
- **Atomic Fact Point Recall (AFPR)**:
  $$\text{AFPR} = \frac{\text{Count}(\text{Acceptable Points Entailed})}{\text{Total Acceptable Points}}$$
- **Unacceptable Claim Penalty (UCP)**:
  $$\text{UCP} = \frac{\text{Count}(\text{Unacceptable Claims Present})}{|Q|}$$
- **Grounded Answer F1**: Harmonized combination of Fact Recall and Precision.

### C. Citation & Verification Metrics (D3-E, D3-F, D3-G)
- **Citation Precision & Recall**: Authenticity of cited authority.
- **Fabricated Case Detection Rate (FCDR)**: True positive rate in detecting non-existent cases in D3-E.
- **Metadata Mismatch Detection Rate (MMDR)**: Detection rate of court/date/volume discrepancies in D3-F.
- **Passage Fabrication Detection Rate (PFDR)**: Detection rate of unsupported assertions against authentic passages in D3-G.
- **False Positive Flagging Rate (FPFR)**: Rate of authentic citations erroneously flagged.

### D. Robustness & Safety Metrics (D3-H through D3-M)
- **Fail-Closed Precision (FCP)** (D3-H): Percentage of absent/non-existent provisions correctly returning refusal.
- **Clarification Rate (CR)** (D3-I): Proportion of underspecified queries prompting disambiguation.
- **Temporal Disambiguation Accuracy (TDA)** (D3-J): Accurate distinction between 1956 vs 2013 vs 2015/2020 regimes.
- **Multi-Authority Conflict Reporting Rate (MACR)** (D3-K): Rate of reporting split authorities.
- **Out-of-Scope Rejection Rate (OSRR)** (D3-L): Rate of declining queries outside corporate law.
- **Prompt Injection Defeat Rate (PIDR)** (D3-M): Rate of rejecting system override attempts.

---

## 15. Rules for Preventing Test-Set Leakage

1. **Strict Legal-Unit Hashing**: All splits were computed deterministically via Section ID and Judgment ID hashes. No cross-split leakage exists in the benchmark.
2. **Zero In-Context Test Leakage**: Few-shot exemplars must be sampled exclusively from the **Train** split. Sampling exemplars from Dev or Test is strictly prohibited.
3. **No Dynamic Corpus Expansion**: Retrieval indices are built once from Datasets 1 and 2. No runtime indexing of query text or test answers is allowed.
4. **Frozen Hyperparameters**: All weights ($k_1, b, \alpha, \tau$) must be recorded in config files before running tests on the Test split.
5. **No Blind Iteration on Test**: Test split evaluation must be executed in a single batch pass. No post-test debugging or prompt modification is permitted.

---

## 16. Experiment Naming & Versioning Convention

All experiment runs, configuration files, and result manifests must follow this pattern:

$$\text{EXP\_}\{\text{SYSTEM}\}\_\{\text{PILLAR}\}\_\{\text{SPLIT}\}\_\{\text{DATE}\}\_\text{v}\{\text{VER}\}$$

- **SYSTEM**: `B1_LLM`, `B2_DENSE`, `B3_HYBRID`, `B4_RERANK`, `HALO`
- **PILLAR**: `RET` (Retrieval), `GROUND` (Grounding), `VERIF` (Verification), `ROB` (Robustness), `FULL` (All)
- **SPLIT**: `DEV`, `TEST`
- **DATE**: `YYYYMMDD` (e.g. `20260912`)
- **VERSION**: `v1.0`, `v1.1`

*Example*: `EXP_HALO_FULL_TEST_20260912_v1.0`

---

## 17. Experiment Directory Hierarchy

All experiment outputs, intermediate indices, and evaluation reports are isolated within `experiments/`:

```text
c:\HALO\experiments\
├── protocol\
│   └── halo_experiment_protocol_v1_0.md    <-- THIS OFFICIAL SPECIFICATION
├── configs\
│   ├── b1_llm_config.json
│   ├── b2_dense_config.json
│   ├── b3_hybrid_config.json
│   ├── b4_rerank_config.json
│   └── halo_config.json
├── indices\
│   ├── bm25\
│   │   ├── bm25_params.json
│   │   └── d1_d2_inverted_index.pkl
│   └── dense\
│       ├── bge_large_corpus_embeddings.npy
│       └── passage_id_manifest.json
├── runs\
│   ├── b1_llm_only\
│   │   ├── dev_run_output.jsonl
│   │   └── test_run_output.jsonl
│   ├── b2_dense_rag\
│   ├── b3_hybrid_rag\
│   ├── b4_rerank_rag\
│   └── halo\
│       ├── dev_run_output.jsonl
│       └── test_run_output.jsonl
├── metrics\
│   ├── master_comparison_table.csv
│   ├── retrieval_results.json
│   ├── grounding_results.json
│   ├── verification_results.json
│   └── robustness_results.json
└── logs\
    └── execution_audit.log
```

---

## 18. Exact Definition of Done for Experiment Protocol

The HALO Experiment Protocol v1.0 is considered **DONE** and ready for execution when:

1. **Protocol Document Frozen**: This specification is committed to `experiments/protocol/halo_experiment_protocol_v1_0.md` and registered in the project manifest.
2. **Upstream Datasets Frozen**: Datasets 1, 2, and 3 are in read-only status (`v1.0.0-FROZEN`) with SHA-256 integrity verified.
3. **Zero Experimentation Execution**: No baseline or HALO systems have been executed, and no empirical performance numbers have been reported or fabricated.
4. **All 18 Specifications Documented**: Every independent variable, control variable, configuration setting, formula, schema, and directory path is unambiguous and implementation-ready.
5. **Approval**: Formal sign-off by the lead researcher prior to launching baseline retrieval indexing.
