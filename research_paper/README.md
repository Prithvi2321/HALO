# HALO Research Paper Dossier: High-Fidelity Autonomous Legal Optimization
## Academic Paper Blueprint & Experimental Documentation

This directory (`/research_paper`) contains the complete, publication-grade scientific documentation, mathematical formulations, experimental results, and LaTeX tables for the research paper on the **HALO (High-Fidelity Autonomous Legal Optimization)** framework for Indian Corporate Law.

---

## Paper Outline & Dossier Mapping

```text
===================================================================================================
RESEARCH PAPER STRUCTURE                   ASSOCIATED DOSSIER FILE
===================================================================================================
Title, Abstract & Introduction             -> research_paper/README.md
Section 3: Corpus & Benchmark Design       -> research_paper/01_corpus_and_benchmark.md
Section 4: Baseline Methodologies          -> research_paper/02_baseline_methodologies.md
Section 5: Empirical Results & Ablation    -> research_paper/03_experimental_results_and_ablation.md
Appendix / LaTeX Tables & Figures          -> research_paper/04_latex_tables.tex
===================================================================================================
```

---

## Suggested Paper Working Titles
1. **HALO: High-Fidelity Autonomous Legal Optimization for Statutory and Judicial Retrieval-Augmented Generation**
2. **Beyond Hallucination: A Dual-Layer Audited RAG Architecture for Indian Corporate Law**
3. **Lexical Precision vs. Semantic Drift: An Empirical Benchmark of Dense, Sparse, and Hybrid Retrieval in Statutory Law**

---

## Target Venues
* **Top AI/NLP Conferences**: ACL, EMNLP, NAACL, COLING, AAAI, IJCAI.
* **Specialized Legal AI & Information Retrieval Venues**:
  * **ICAIL** (International Conference on Artificial Intelligence and Law)
  * **SIGIR** (Special Interest Group on Information Retrieval)
  * **JURIX** (International Conference on Legal Knowledge and Information Systems)
  * **Artificial Intelligence and Law (Springer Journal)**

---

## Core Research Questions (RQs)
* **RQ1 (Dense vs. Sparse Tradeoff)**: Does dense semantic retrieval (bi-encoder) outperform sparse lexical retrieval (BM25) when answering statutory questions, or does dense vector compression cause semantic drift on exact section numbers and numeric thresholds?
* **RQ2 (The Vocabulary Mismatch Problem)**: How significantly does vocabulary mismatch degrade sparse lexical retrieval when queries use non-statutory conceptual lay terms?
* **RQ3 (Susceptibility to Adversarial Distractors)**: How vulnerable are standalone retrievers to hard-negative statutory distractors sharing identical legal terminology (*Tribunal*, *Special Resolution*), and does retrieval augmentation increase hallucination rates when distractors are retrieved?
* **RQ4 (Hybrid Fusion & Verification)**: Can reciprocal rank fusion combined with cross-encoder reranking and dual-layer verification eliminate statutory hallucination while maintaining high factual completeness?

---

## Project Execution Status Matrix

| System / Baseline | Status | Key Characteristics | Evaluated Split | Primary Metric |
| :--- | :---: | :--- | :---: | :--- |
| **Dataset 1 (Statute)** | **FROZEN** | 1,640 passages (Companies Act, 2013) | N/A | SHA-256 Verified |
| **Dataset 2 (Judicial)** | **FROZEN** | 1,133 passages (57 Landmark Judgments) | N/A | SHA-256 Verified |
| **Dataset 3 (Benchmark)**| **FROZEN** | 1,032 queries across 10 families | 64 DEV / 168 TEST | 10 QA Gates Passed |
| **Baseline 1 (LLM-Only)**| **FROZEN** | Zero retrieval, purely parametric | DEV (64) + TEST (168) | AFPR: 57.67% |
| **Baseline 2 (Dense RAG)**| **FROZEN** | `BGE-Large`, 1024-dim, Top-5, Cosine | DEV (64) + TEST (168) | Recall@5: 41.18% (D3-B) |
| **Baseline 3 (BM25 RAG)** | **FROZEN** | `BM25Okapi`, Legal Tokenizer, Top-5 | DEV (64) + TEST (168) | AFPR: 60.17% (D3-D) |
| **Baseline 4 (Hybrid RAG)**| **FROZEN** | Dense + BM25 via RRF ($k=60$), Top-5 | DEV (64) + TEST (168) | AFPR: 60.42% (D3-D) / Recall@5: 41.18% (D3-B) |
| **Baseline 5 (Reranker)**  | **FROZEN** | Hybrid + Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) | DEV (64) + TEST (168) | AFPR: 63.00%, Recall@5: 62.82%, HNFAR: 8.33% |
| **HALO Full Architecture** | **PENDING**| Dual-Layer Verification + Fail-Closed | Planned | Zero-Hallucination |

---

*This directory is updated systematically after every experimental baseline to maintain publishable, LaTeX-ready materials. Baseline 5 Cryptographic Freeze Receipt: `experiments/runs/b5_reranker/freeze_receipt.json` (Digest: `d49f57d538ce0f37881bd550c686acce1dba5058dc2d5693e4df75a6a6142ab8`).*
