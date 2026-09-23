# Section 3: Legal Corpus Construction & Multi-Pillar Benchmark Design

This document provides the complete, mathematically formal specification of the corpora and benchmark suite engineered for the **HALO (High-Fidelity Autonomous Legal Optimization)** research paper.

---

## 1. Dual-Corpus Retrieval Space Construction

Unlike standard open-domain RAG benchmarks that crawl unverified web pages, the HALO retrieval corpus comprises two canonical, authoritative, and mutually reconciled primary legal sources governing Indian Corporate Law:

```text
+-----------------------------------------------------------------------------------------+
|                               HALO UNIFIED RETRIEVAL CORPUS                             |
|                                    (Total: 2,773 Passages)                              |
+----------------------------------------------------+------------------------------------+
|               DATASET 1: STATUTORY CORPUS          |     DATASET 2: JUDICIAL CORPUS     |
|              (Companies Act, 2013 + Amendments)    |        (Landmark Precedents)       |
+----------------------------------------------------+------------------------------------+
| • 504 Sections across Chapters I–XXIX              | • 57 Landmark Judgments            |
| • Schedules I–VII                                  | • Supreme Court (38 judgments)     |
| • 1,640 Atomic Sub-Section Passages                | • NCLAT / High Courts (19 judgments|
| • Amendment Integration (2015, 2017, 2019, 2020)   | • 1,256 Parsed Legal Paragraphs    |
| • SHA-256: 37c5ced49fc3925342a...                  | • 1,133 Contextual Passages        |
|                                                    | • 552 Verified Legal Citations     |
|                                                    | • 666 Resolved Statutory X-Refs    |
|                                                    | • SHA-256: 43af9b6ed2df7be54...    |
+----------------------------------------------------+------------------------------------+
```

### 1.1 Dataset 1: Statutory Corpus (Companies Act, 2013)
* **Scope**: The entire codified statute of the Indian Companies Act, 2013 (Act No. 18 of 2013), as amended by:
  1. Companies (Amendment) Act, 2015 (Act No. 21 of 2015)
  2. Companies (Amendment) Act, 2017 (Act No. 1 of 2018)
  3. Companies (Amendment) Act, 2019 (Act No. 22 of 2019)
  4. Companies (Amendment) Act, 2020 (Act No. 29 of 2020)
* **Atomic Passage Segmentation**:
  Statutory sections were not naively chunked by token windows (which destroys legal sub-clause dependencies). Instead, sections were segmented into atomic legal units using syntactic statutory parsing:
  $$\mathcal{P}_{\text{stat}} = \{ p_{s, sub} \mid s \in \text{Sections}, sub \in \text{Subsections/Provisos/Explanations} \}$$
  Total statutory passages: $|\mathcal{P}_{\text{stat}}| = 1,640$.
* **Metadata Schema**: Each passage record contains:
  * `passage_id`: e.g. `PAS_ACT_COMPANIES_2013_SEC_135_SUB_1`
  * `document_id`: `ACT_COMPANIES_2013`
  * `section_id`: e.g. `ACT_COMPANIES_2013_SEC_135`
  * `heading`: Statutory section title (e.g. *"Corporate Social Responsibility"*)
  * `text`: Verbatim sub-section text with amendment notes preserved.

### 1.2 Dataset 2: Judicial Precedent Corpus (Case Law)
* **Scope**: 57 landmark decisions rendered by the Supreme Court of India, the National Company Law Appellate Tribunal (NCLAT), and High Courts interpreting core provisions of corporate jurisprudence (oppression & mismanagement, mergers, CSR, director liabilities, insolvency interface).
* **Structural Parsing & Normalization**:
  * Native PDF extraction with font-weight header detection and footnote separation.
  * Extracted 1,256 numbered legal paragraphs.
  * Formed 1,133 atomic passages respecting ratio decidendi boundaries.
  * Resolved 666 statutory cross-references linking directly to Dataset 1 section IDs.
  * Verified 552 canonical legal citations (AIR, SCC, Comp Cas, SCR).
* **Metadata Schema**:
  * `passage_id`: e.g. `PAS_JUDG_SC_2019_001_P12`
  * `document_id`: Case canonical identifier (e.g. `CAND-SC-2019-2019_10_133_142`)
  * `court`: Court identifier (e.g. `Supreme Court of India`)
  * `citation`: Standard Indian case citation
  * `statutory_cross_references`: Array of linked Dataset 1 sections.

---

## 2. Dataset 3: The Multi-Pillar Benchmark Suite

To rigorously stress-test legal retrieval and answer generation, Dataset 3 defines 1,032 benchmark instances across 10 specialized families, partitioned into 13 files.

### 2.1 The Active 4-Pillar Experimental Benchmark ($N = 232$)
For baseline evaluation under Experiment Protocol v1.0, the benchmark evaluates the 232 instances comprising the DEV ($N=64$) and TEST ($N=168$) splits across 4 core research families:

```text
+------------------------------------------------------------------------------------------+
|                        DATASET 3 EVALUATION PARTITIONS (N = 232)                         |
+-------------------+-----------------+-----------------+----------------------------------+
| BENCHMARK FAMILY  | DEV SPLIT (N=64)|TEST SPLIT(N=168)| RESEARCH EVALUATION OBJECTIVE    |
+-------------------+-----------------+-----------------+----------------------------------+
| Family D3-A       |   11 queries    |   39 queries    | Direct Statutory Retrieval       |
| Family D3-B       |   11 queries    |   17 queries    | Semantic Paraphrase Retrieval    |
| Family D3-C       |    8 queries    |   12 queries    | Hard-Negative Distractors        |
| Family D3-D       |   34 queries    |  100 queries    | Complex Grounded Answer Synthesis|
+-------------------+-----------------+-----------------+----------------------------------+
| TOTAL             |   64 records    |  168 records    | 232 Total Evaluated Queries      |
+-------------------+-----------------+-----------------+----------------------------------+
```

### 2.2 Family Detailed Descriptions & Evaluation Intent

1. **Family D3-A: Direct Statutory Retrieval ($N_{\text{test}} = 39$)**
   * *Description*: Concrete statutory queries explicitly referencing codified provisions, section numbers, or formal statutory names (e.g., *"Under Section 135(5), what is the formula for calculating mandatory annual CSR expenditure?"*).
   * *Metric*: Recall@5, Hit Rate@5, Mean Reciprocal Rank (MRR).
   * *Objective*: Measure inverted-index keyword precision vs. dense vector drift on numeric section tokens.

2. **Family D3-B: Semantic Conceptual Retrieval ($N_{\text{test}} = 17$)**
   * *Description*: Conceptual queries formulated in colloquial or non-verbatim legal language, with zero statutory section citations (e.g., *"Who possesses legal authority to sanction the reduction of share capital for an Indian enterprise?"*).
   * *Metric*: Semantic Recall@5, Semantic Hit Rate@5, MRR.
   * *Objective*: Expose the vocabulary mismatch vulnerability in sparse lexical search and evaluate dense semantic generalization.

3. **Family D3-C: Disambiguation & Hard Negatives ($N_{\text{test}} = 12$)**
   * *Description*: Adversarially curated queries specifically designed to confound retrievers by pairing the gold provision with distractor provisions that share identical legal vocabulary (e.g., distinguishing Section 149(10) re-appointment of independent directors from Section 152(6) retirement of directors by rotation).
   * *Metric*: Positive Hit Rate@5, Hard Negative Retrieval Rate, Hard Negative Fallback Acceptance Rate (HNFAR).
   * *Objective*: Quantify whether retrieval augmentation introduces distractor-induced hallucinations.

4. **Family D3-D: Complex Grounded Legal Answering ($N_{\text{test}} = 100$)**
   * *Description*: Multi-faceted corporate inquiries requiring multi-point factual synthesis, legal qualification extraction, financial threshold reporting, and statutory caveat verification.
   * *Metric*: Atomic Fact Precision/Recall (AFPR), Complete Answer Rate, Hallucination/Unsupported Claim Rate.
   * *Objective*: Measure whether retrieved context actually grounds the LLM or whether the model ignores evidence and hallucinates from parametric memory.

---

## 3. Strict Split Isolation & Data Leakage Prevention

To guarantee zero data leakage into experimental retrievers:
1. **Legal-Unit Disjoint Splitting**: Splits were partitioned by statutory chapter and case topics so that queries in the TEST split do not share exact statutory sections with the DEV split.
2. **Strict Index Exclusion**: All 1,032 queries, gold answers, and test annotations in Dataset 3 are strictly excluded from the retrieval corpus:
   $$\mathcal{C}_{\text{retrieval}} \cap \mathcal{Q}_{\text{D3}} = \emptyset$$
   Verified in automated audit: **0 overlapping records**.
3. **Cryptographic Sealing**: Datasets 1, 2, and 3 are frozen under SHA-256 manifests. Any modification triggers an immediate hash mismatch.
