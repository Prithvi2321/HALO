# HALO Dataset 3: Benchmark Charter & Evaluation Policy

**Version**: 1.0.0  
**Status**: DRAFT (Pending Freeze)  
**Corpus Scope**: Grounded in HALO Dataset 1 (`v1.0.0-FROZEN`) and HALO Dataset 2 (`v1.0.0-FROZEN`).

---

## 1. Executive Purpose

HALO Dataset 3 is the frozen, multi-family evaluation benchmark for the **HALO Indian Legal Research System**. It is designed to evaluate five distinct architectural paradigms without bias, query leakage, or speculative scoring:

1. **Baseline 1 (LLM-Only)**: Zero-retrieval direct generation to measure baseline parametric legal knowledge and intrinsic hallucination rates.
2. **Baseline 2 (Vector RAG)**: Standard dense bi-encoder retrieval + generative reader.
3. **Baseline 3 (BM25 + Semantic Hybrid RAG)**: Lexical + dense fusion retrieval.
4. **Baseline 4 (Hybrid RAG + Cross-Encoder Reranking)**: Fusion retrieval with neural reranking prior to context assembly.
5. **System 5 (HALO)**: Hybrid Retrieval + Neural Reranking + Generative Reader + Three-Tier Deterministic Verification (Citation Existence, Metadata Matching, and Passage-Level Claim Entailment with Fail-Closed Guardrails).

---

## 2. Core Architectural Principles

### 2.1 Separation of Evidence and Evaluation
- **Dataset 1** (Authoritative Statutory Corpus: The Companies Act, 2013) and **Dataset 2** (Curated Judicial Corpus: 57 judgments across Supreme Court, NCLAT, High Courts) are the single sources of legal truth.
- **Dataset 3 is NOT a legal corpus**. It is a benchmark contract containing queries, ground-truth evidence identifiers, acceptable answer atomic propositions, and adversarial stress tests.
- Dataset 3 **NEVER** mutates or updates Dataset 1 or Dataset 2.

### 2.2 The Two Worlds Evaluation Paradigm
To evaluate both retrieval effectiveness and verification robustness, Dataset 3 establishes two distinct operational regimes:
- **World A (Real Ground Truth)**: Real queries paired with authentic supporting evidence from Dataset 1 and/or Dataset 2. Measures Recall@K, Precision@K, NDCG@K, MRR, and Answer Groundedness.
- **World B (Adversarial Verification)**: Grounded in authentic case law and statutes, but systematically perturbs citations, courts, dates, paragraph references, and legal propositions to measure whether the verification layer detects fabricated or unsupported claims (`SUPPORTED`, `FLAGGED`, `REJECTED`, `PASSAGE_UNSUPPORTED`).

### 2.3 Strict Pre-Tuning Freeze
- Dataset 3 is frozen prior to system threshold calibration, prompt engineering, or reranker fine-tuning.
- The **Test split** is held out exclusively for final model reporting and research publication.

---

## 3. Sub-Benchmark Taxonomy

Dataset 3 comprises 13 distinct benchmark families grouped into four core pillars:

| Pillar | Sub-Benchmark | Code | Evaluation Focus |
| :--- | :--- | :--- | :--- |
| **Retrieval** | Direct Statutory & Case Retrieval | `D3-A` | Dense, sparse, and hybrid retrieval over sections and judicial passages |
| | Paraphrased & Semantic Retrieval | `D3-B` | Semantic invariance under natural language reformulation and vocabulary variation |
| | Hard Negative Retrieval | `D3-C` | Discrimination between positive passages and confounding adjacent/topic-similar negatives |
| **Grounding** | Grounded Answer Generation | `D3-D` | Factual support, atomic point coverage, and absence of unacceptable claims |
| **Verification** | Citation Existence Verification | `D3-E` | Detection of completely fabricated case names or non-existent citations |
| | Citation Metadata Mismatch | `D3-F` | Detection of swapped citations, altered courts, shifted judgment dates, or case numbers |
| | Passage-Level Fabrication | `D3-G` | Detection of valid citations paired with fabricated/unsupported legal propositions |
| **Robustness** | Fail-Closed / No-Evidence | `D3-H` | Verification that the system abstains on non-existent provisions (e.g. §999) or unrepresented cases |
| | Ambiguous Queries | `D3-I` | Proper handling of underspecified legal inquiries via clarification or confidence downgrading |
| | Temporal & Historical Transition | `D3-J` | Disambiguation of 1956 vs 2013 provisions and historical vs amended penalty terms |
| | Judicial Conflicts | `D3-K` | Surfacing divergent interpretations across High Courts/Tribunals rather than arbitrary selection |
| | Out-of-Domain Queries | `D3-L` | Rejection of non-corporate legal topics (sports, weather, programming) without legal hallucination |
| | Adversarial Prompt Injections | `D3-M` | Resistance to user prompts attempting to bypass the three-tier verification firewall |

---

## 4. Benchmark Execution Protocol

- No benchmark result, accuracy metric, Recall@K, or hallucination detection rate may be claimed until formal execution of evaluation scripts against the frozen Dataset 3 test set.
- All evaluation outputs must preserve complete provenance back to Dataset 3 record IDs.
