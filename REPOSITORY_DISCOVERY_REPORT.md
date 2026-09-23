# HALO Verification Benchmark: Repository Discovery Report

**Protocol**: `v1.0-FROZEN`  
**Role**: Senior Data Engineer + Legal NLP Evaluation Architect  
**Date**: 2026-09-17  
**Status**: Pre-Generation Audit Complete

---

## 1. Primary Corpus Locations & Freeze Integrity

| Corpus / Asset | Filesystem Location | Passage Count / Records | Authoritative Freeze Hash (SHA-256) | Role in Milestone |
| :--- | :--- | :---: | :--- | :---: |
| **Dataset 1 (Statutory Corpus)** | `data/dataset_1/final/` | 1,640 codified passages (Companies Act, 2013) | `37c5ced49fc3925342a7eebfc84eb2988f863166b60c0a8cf527aefae0e8c27c` | **PRIMARY SOURCE (IMMUTABLE)** |
| **Dataset 1 Versions** | `data/dataset_1/final/companies_act_2013_versions.json` | 3 point-in-time statutory versions (2013, 2015, 2020) | `46c12dca0069b608ba9774ea2a8daef82d5289d8bfe40f0c4b3df8816cefccff` | **TEMPORAL PROVENANCE (IMMUTABLE)** |
| **Dataset 1 Amendments** | `data/dataset_1/final/companies_act_2013_amendments.json` | 1,916 amendment operations | `9ce152c92e3c0c000e4277bc1b6a7a503a44ad545e8e89547d2524d7778b40ec` | **AMENDMENT PROVENANCE (IMMUTABLE)** |
| **Dataset 2 (Judicial Corpus)** | `data/dataset2/canonical/passages.jsonl` | 1,133 judicial passages (57 Supreme Court/NCLAT judgments) | `43af9b6ed2df7be5489a71e81cf1f0125469d0cbe4443d0e536edb35703d3996` | **PRIMARY SOURCE (IMMUTABLE)** |
| **Dataset 2 Judgments** | `data/dataset2/canonical/judgments.jsonl` | 57 judgments & neutral citations | `fe75dee7ee7a5c115f41dd7d3a9f8ca44edb068cefb9a9a69c299a22d77d9935` | **METADATA PROVENANCE (IMMUTABLE)** |
| **Dataset 2 Citations** | `data/dataset2/canonical/citations.jsonl` | 552 resolved case citations | `846c4bfdcee12cc7bf26d0ee59da4d471a50544e192d59a1c273045e840afc0b` | **CITATION PROVENANCE (IMMUTABLE)** |
| **Dataset 3 (Benchmark Suite)** | `data/dataset3/canonical/dataset3_all.jsonl` | 1,032 canonical benchmark items | `431a27d8fbc569255ae53fe209b869c6ae0b0bc8090b750500be0176ea54afc4` | **FROZEN EVAL BENCHMARK (ISOLATED - ZERO TOUCH)** |

> **Critical Contamination Barrier**: Dataset 3 (`data/dataset3/canonical/dataset3_all.jsonl`) is strictly quarantined and must NEVER be used for generation, calibration, label synthesis, or benchmark construction.

---

## 2. Frozen Baseline Receipts & Audit State

All baseline experiment runs are verified and immutable:
* **Baseline 1 (LLM-Only)**: `experiments/runs/b1_llm_only/freeze_receipt.json` (`a2cd8c15...`)
* **Baseline 2 (Dense RAG)**: `experiments/runs/b2_dense_rag/freeze_receipt.json` (`bc666c8e...`)
* **Baseline 3 (Sparse BM25)**: `experiments/runs/b3_bm25/freeze_receipt.json` (`dfe92e62...`)
* **Baseline 4 (Hybrid RAG)**: `experiments/runs/b4_hybrid/freeze_receipt.json` (`d8ec36f8...`)
* **Baseline 5 (Hybrid + Cross-Encoder Reranker)**: `experiments/runs/b5_reranker/freeze_receipt.json` (`d49f57d5...`)

---

## 3. Legacy Prototype Data vs. New Benchmark Root

* **Legacy Prototype Location**: `Dataset/Dataset1/halo_datasets/`
  * Contains early prototype test fragments (e.g. 6 prototype citation entries, 2 prototype authority entries, 2 fail-closed entries).
  * Status: **LEGACY / READ-ONLY**. Must NOT be overwritten, modified, or merged into the new benchmark.
* **New Authoritative Benchmark Root**: `halo_datasets/`
  * Fully independent directory structure at repository root with 12 subdirectories:
    `citation_verification/`, `passage_verification/`, `claim_evidence/`, `temporal/`, `adversarial/`, `fail_closed/`, `authority/`, `conflict/`, `splits/`, `manifests/`, `qa/`, `generators/`.

---

## 4. Authoritative Passage IDs and Metadata Specifications

### 4.1 Dataset 1 (Statutory Corpus)
* **ID Format**: `PAS_ACT_COMPANIES_2013_SEC_<N>_SUB_<M>` or `PAS_ACT_COMPANIES_2013_SEC_<N>`
* **Key Fields**:
  - `passage_id`: Unique identifier (e.g. `PAS_ACT_COMPANIES_2013_SEC_135_SUB_1`)
  - `section_id`: E.g. `ACT_COMPANIES_2013_SEC_135`
  - `heading`: Section title (e.g. `Corporate Social Responsibility`)
  - `text`: Primary statutory text
  - `canonical_text`: Standardized text
  - `enforcement_status`: `IN_FORCE` | `NOT_IN_FORCE`
  - `effective_from`: ISO date (e.g. `2014-04-01`)
  - `content_hash`: SHA-256 of canonical text

### 4.2 Dataset 2 (Judicial Corpus)
* **ID Format**: `PAS-JUD-SC-<year>-<case_id>-P<para_num>`
* **Key Fields**:
  - `passage_id`: Unique identifier (e.g. `PAS-JUD-SC-2016-2016_11_149_171-P001`)
  - `document_id`: Judgment ID (e.g. `JUD-SC-2016-2016_11_149_171`)
  - `court`: E.g. `SUPREME_COURT_OF_INDIA`
  - `citation`: Reporter citation (e.g. `[2016] 11 S.C.R. 149`)
  - `case_title`: Standardized case caption
  - `text`: Judicial text snippet
  - `provenance_id`: Paragraph tracking identifier

---

## 5. Hashing & Freeze Utilities Identified

* **Hashing Algorithm**: SHA-256 canonical hashing of normalized JSON keys (`json.dumps(obj, sort_keys=True, ensure_ascii=False)`).
* **Freeze Framework**: Structured JSON manifest accompanied by `SHA256SUMS.txt` and cryptographic `VERIFICATION_DATASET_FREEZE_RECEIPT.json`.
* **Immutability Enforcement**: Scripts located in `halo_datasets/generators/` and QA checks in `halo_datasets/qa/`.
