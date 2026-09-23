# HALO DATASET 1: STATUTORY CORPUS FINAL QA & FREEZE REPORT

**Corpus**: The Companies Act, 2013 (with Amending Acts of 2015 and 2020)  
**Corpus Release Status**: `CANDIDATE-FROZEN / PENDING FINAL QA`  
**Evaluation Date**: 2026-09-05 15:30:24 UTC  
**Role**: Senior Legal Data Engineer + Senior Software Engineer + Data Quality Architect  

---

## 1. Executive Summary

This report documents the exhaustive, source-to-JSON ground truth audit and freeze protocol for **HALO Dataset 1: The Companies Act, 2013**. 

Dataset 1 is the authoritative statutory corpus serving as the ground truth foundation for the entire HALO evaluation ecosystem. In strict adherence to Cardinal Rules 1–5:
- The official source PDFs in `data/dataset_1/source/companies_act/` are the supreme authority.
- No legal text or dates have been synthesized or imputed from LLM knowledge.
- Dataset 1 remains completely isolated from downstream benchmark datasets (Datasets 3–8).
- Raw text and canonical text are maintained independently.

---

## 2. Source Document Integrity

Every source PDF was verified for byte-level integrity, immutability, and declared SHA-256 matching:

| Source Document ID | Official File | Pages | Size (Bytes) | SHA-256 Checksum | Integrity Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ACT_COMPANIES_2013` | `TCA1.pdf` | 370 | 5,070,430 | `0b915c8ea8927674b988584a9c8572fcaa526ad6d89a02b4234797087946b4d6` | **VERIFIED (IMMUTABLE)** |
| `ACT_COMPANIES_AMEND_2015` | `TCA2015.pdf` | 5 | 112,762 | `f0f1ff814a6f4fff582e3e542f3de46f0d25a06de39e5cd11aee187fd32e6f24` | **VERIFIED (IMMUTABLE)** |
| `ACT_COMPANIES_AMEND_2020` | `TCA2020.pdf` | 35 | 417,037 | `3ed9c6c3d312350d164fc257c040e46b148a8133b1fa54f7f666826a3bc410bb` | **VERIFIED (IMMUTABLE)** |

---

## 3. PDF Extraction Quality

- **Total Pages Processed**: 410 / 410 (100% sequential alignment, 0 missing pages).
- **Empty Pages**: 0.
- **Corrupted / Illegible Pages**: 0.
- **OCR Fallback Pages**: 0 (all 410 pages have native digital typography >= 50 characters).
- **Boilerplate Stripping**: 411 running headers and 175 running footers cleanly isolated into `boilerplate_audit.json`.

---

## 4. Structural Validation

- **Total Detected Sections**: 504 / 504 (including special provisions: `3A`, `76A`, `378A` through `378Z-O`, `470`).
- **Unique Section Numbers**: 504 (0 duplicate sections, 0 missing sections).
- **Hierarchy Preservation**:
  - **Subsections**: 1,496 numbered provisions `(1)`, `(2)`, `(3)`.
  - **Clauses**: 1,500 lettered clauses `(a)`, `(b)`, `(c)`.
  - **Provisos**: 814 provisos (`Provided that`, `Provided further that`, `Provided also that`).
  - **Explanations**: 130 explanations (`Explanation.—`).
- **Legal Definitions**: 84 terms cataloged from Section 2 & Section 378A.
- **Schedules**: Schedules I through VII extracted with full table and part structures.

---

## 5. Dual-Text Architecture & Footnote Handling

To satisfy the twin requirements of high-precision legal retrieval and publication fidelity:
1. **Raw Text (`raw_text`)**: Preserves the exact publication state with editorial markers (e.g., `3[within thirty days of its incorporation]`).
2. **Canonical Text (`canonical_text`)**: Strips bracketed marker wrappers and omission asterisks (`within thirty days of its incorporation`) to ensure BM25 and dense retrieval search pure statutory wording.
3. **Editorial Marker Catalog**: 443 markers across sections cataloged with specific targets.
4. **Statutory Footnote Index**: **555 official footnotes** cataloged from India Code publication, containing 466 explicit gazetted `w.e.f.` dates and amending Act citations.

---

## 6. Amendment Validation

- **Amending Acts Ingested**:
  - Act 21 of 2015: 22 amending sections.
  - Act 29 of 2020: 65 amending sections.
- **Total Operations**: 87 operations.
- **Operations Breakdown**:
  - `SUBSTITUTE`: 59
  - `INSERT`: 15
  - `OMIT`: 13
- **Unresolvable Targets**: 0 (100% of target sections exist in the principal Act).

---

## 7. Temporal Lifecycle & Version Model

The temporal model enforces the explicit lifecycle:
$$\text{Enacted} \longrightarrow \text{Published} \longrightarrow \text{Amended} \longrightarrow \text{Commenced} \longrightarrow \text{In Force} \longrightarrow \text{Repealed / Omitted}$$

- **Enforcement Status Distribution**:
  - `IN_FORCE`: 452 sections
  - `AMENDED`: 9 sections (pending Gazette commencement confirmation)
  - `OMITTED`: 43 sections (including Section 267)
- **Invalid Date Sequences**: 0.
- **Multi-Version Historical Store**: `v2013_original`, `v2015_amended`, and `v2020_amended` preserved in `companies_act_2013_versions.json`.

---

## 8. Golden Section Comparative Audit (10 Sections)

Deep source-to-JSON audits on 10 representative sections:

| Section | Heading | Source Pages | Status | Footnotes | Passages | Audit Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Section 12** | Registered office of company | p.33-p.34 | `IN_FORCE` | 4 footnotes | 8 passages | **PASS** |
| **Section 22** | Execution of bills of exchange | p.41 | `IN_FORCE` | 1 footnote | 4 passages | **PASS** |
| **Section 48** | Variation of shareholders' rights | p.53 | `IN_FORCE` | 0 footnotes | 2 passages | **PASS** |
| **Section 54** | Issue of sweat equity shares | p.56-p.57 | `IN_FORCE` | 1 footnote | 2 passages | **PASS** |
| **Section 76A** | Punishment for contravention of s. 73/76 | p.71 | `IN_FORCE` | 2 footnotes | 1 passage | **PASS** |
| **Section 117** | Resolutions and agreements to be filed | p.85-p.86 | `IN_FORCE` | 3 footnotes | 3 passages | **PASS** |
| **Section 135** | Corporate Social Responsibility | p.93-p.94 | `IN_FORCE` | 6 footnotes | 7 passages | **PASS** |
| **Section 188** | Related party transactions | p.128-p.130 | `IN_FORCE` | 3 footnotes | 5 passages | **PASS** |
| **Section 267** | [Omitted.] | p.169 | `OMITTED` | 1 footnote | 1 passage | **PASS** |
| **Section 470** | Power to remove difficulties | p.252 | `IN_FORCE` | 0 footnotes | 3 passages | **PASS** |

---

## 9. Edge-Case Audit (A through X)

All 24 edge-case categories from Section 29 verified:
- **A. Lettered Section Numbers**: `3A`, `76A`, `378A`–`378Z-O` verified.
- **B. Omitted Sections**: Section 267 verified as `OMITTED` with historical text preserved.
- **C. Multi-page Sections**: Section 2 (15 pages), Section 135 (2 pages) verified.
- **D. Amendments in Existing Text**: Section 12 subsection (1) verified.
- **E. Phrase Replacement**: Section 188 ordinary resolution substitution verified.
- **F. Multiple Amendments to Same Section**: Section 135 verified.
- **G. Consecutive Amendments**: Section 12 verified.
- **H. Delayed Commencement**: Footnotes with explicit `w.e.f.` dates verified.
- **I. Provisos**: 814 provisos parsed without regex lookahead cutoffs.
- **J. Explanations**: 130 statutory explanations parsed.
- **K. Illustrations**: Preserved in statutory body.
- **L. Footnotes**: 555 footnotes cataloged.
- **M. Tables**: Schedule I Tables A–J verified.
- **N. Schedules**: Schedules I–VII complete.
- **O. Financial Formulas**: Schedule II & III accounting principles intact.
- **P. Cross References**: 668 statutory references cataloged.
- **Q-S. Conditionality Punctuation**: `Provided that` (321), `Notwithstanding` (100), `Subject to` (170), `Unless` (125) verified.
- **T. Multiple Alternatives**: `or` / `and` syntactic branches verified.
- **U. Monetary Thresholds**: Rupee crore/lakh values 100% verified against corruption.
- **V-X. Dates & Superscripts**: All verified.

---

## 10. Deterministic Rebuild Verification

- **Build 1 vs Build 2 Comparison**: 10 out of 10 final artifacts compared byte-for-byte and AST-for-AST.
- **Result**: **100% BIT-FOR-BIT IDENTICAL**.
  - `companies_act_2013.json`: `bbbc8b28e1e9c518...` (MATCH)
  - `companies_act_2013_passages.jsonl`: `3642bf8c19d890c6...` (MATCH)
  - `companies_act_2013_versions.json`: `46c12dca0069b608...` (MATCH)
  - `companies_act_2013_amendments.json`: `e9157ef759ca327c...` (MATCH)
  - `companies_act_2013_provenance.json`: `cf27e26b29923714...` (MATCH)
  - `companies_act_2013_cross_references.json`: `d3534ce796056f40...` (MATCH)
  - `companies_act_2013_definitions.json`: `61c367132a83a095...` (MATCH)
  - `companies_act_2013_validation_report.json`: `1a687e517629cd59...` (MATCH)
  - `freeze_manifest.json`: `813eccc901f5fa0d...` (MATCH)
  - `dataset_1_manifest.json`: `0419b47b9a009506...` (MATCH)

---

## 11. Human Review Queue Summary

- **Total Review Items**: 5 items logged in `data/dataset_1/qa/human_review_queue.jsonl`.
- **Critical Severity**: 0
- **High Severity**: 0
- **Medium Severity**: 0
- **Low Severity**: 5 (Administrative items: amended provisions where gazetted notification commencement date is not stated inline in India Code footnotes, correctly left with `commencement_date: null` rather than guessed).

---

## 12. Senior Engineer Freeze Decision

**Decision**: `CANDIDATE-FROZEN / PENDING FINAL QA`

**Justification**:
1. Zero critical or high-severity discrepancies.
2. 100% deterministic rebuild across all 10 release artifacts.
3. Complete 4-tier cryptographic lineage chain established.
4. All 10 golden section deep audits passed.
5. In accordance with Section 32 of the specification, the corpus is appropriately designated as **Candidate-Frozen / Pending Final QA** until the 5 low-severity administrative Gazette commencement confirmations are formally signed off by human legal review.

---

**Master Dataset SHA-256**: `813eccc901f5fa0d5b0dd9517f13ab9d327859a4b155fadf4b31e47f100d46aa`
