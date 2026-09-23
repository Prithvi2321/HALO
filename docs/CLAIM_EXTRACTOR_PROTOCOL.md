# HALO Protocol Document: Claim Extractor Specification
**Document ID**: `HALO-PROTO-VERIF-01`  
**Protocol Version**: `v1.0-FROZEN`  
**Classification**: Post-Retrieval Verification Engine Protocol  
**Subsystem**: `halo.claim_extractor`  

---

## 1. Specification Scope & Architectural Placement

The Claim Extractor is the primary ingress point of the post-retrieval verification pipeline in HALO. It accepts generated natural-language legal answers produced by Baseline 5 (or any generation stage) and produces an ordered, immutable sequence of atomic propositions.

### Boundaries
* **Upstream**: Retrieval Baselines (B1–B5). The Claim Extractor operates strictly on the generated answer text and does not modify or rerun retrieval.
* **Downstream**: 
  1. Citation Verifier (`halo.citation_verifier`)
  2. Evidence Verifier (`halo.evidence_verifier`)
  3. Temporal Verifier (`halo.temporal_verifier`)
  4. Fail-Closed Governor (`halo.governor`)

---

## 2. Inviolable Verification Rules & Acceptance Gates

| Gate ID | Gate Name | Verification Criteria | Status |
| :--- | :--- | :--- | :--- |
| **C1** | **Schema Compliance** | Adheres to `ExtractedClaim`, `SourceSpan`, `CitationRef`, and 15-member `ClaimType` enum. | Passed (Unit Tests) |
| **C2** | **Atomicity Enforcement** | Compound sentences, semicolons, and provisos decomposed into standalone atomic claims. | Passed (Unit Tests) |
| **C3** | **Modality Preservation** | Deontic modals (`shall`, `must`, `may`, `cannot`) preserved verbatim in source text and metadata. | Passed (Unit Tests) |
| **C4** | **Numerical Integrity** | Exact monetary figures (₹), percentages, day counts, and thresholds preserved without rounding. | Passed (Unit Tests) |
| **C5** | **Temporal Preservation** | Statutory effective dates (`w.e.f.`), repeal markers, and amendment phrases preserved. | Passed (Unit Tests) |
| **C6** | **Citation Association** | Citations linked to claims via proximity rule (same sentence $\to$ adjacent sentence $\to$ None). | Passed (Unit Tests) |
| **C7** | **Span Integrity** | 100% byte-for-byte exact match: `answer[start:end] == source_text` across all claims. | Passed (Empirical Audit) |
| **C8** | **Determinism** | Identical inputs produce bit-for-bit identical outputs and identical SHA-256 output hashes. | Passed (Unit Tests) |
| **C9** | **No Truth Leakage** | Subsystem MUST NOT assign verification verdicts (`SUPPORTED`, `CONTRADICTED`, etc.). | Passed (Unit Tests) |
| **C10**| **Frozen Protection** | Datasets D1, D2, D3, B1–B5, and `halo_datasets/` remain read-only and cryptographically verified. | Passed (Receipt Audit) |
| **C11**| **Test Split Isolation** | Test benchmark cases (`halo_datasets/splits/test.jsonl`) remain strictly quarantined. | Passed (Receipt Audit) |
| **C12**| **Auditability** | SHA-256 digests computed over input text and canonical serialized claim output. | Passed (Empirical Audit) |

---

## 3. Algorithmic Pipeline Specifications

### 3.1 Legal Sentence Segmentation
* **Abbreviation Protection**: Sentence splitting must not break on legal citation shorthand, case abbreviations, or statutory prefixes (`Sec.`, `Secs.`, `w.e.f.`, `Ltd.`, `Pvt. Ltd.`, `v.`, `vs.`, `S.C.R.`, `SCC`, `Hon'ble`, `para.`, `cl.`, `r/w`, `No.`, `Co.`, `Govt.`).
* **Offset Invariance**: Character offsets `[start_char, end_char]` must reference the raw input answer string directly.

### 3.2 Citation Detection & Span Offsets
* **Statutory Citations**: Matches Act names, section numbers, subsections, and clauses (e.g., `Section 135(1)(a) of the Companies Act, 2013`).
* **Judicial Citations**: Matches reporter citations (`[2018] 1 SCC 353`, `AIR 2020 SC 123`, `INSC`), as well as party names in adversary format (`Mobilox Innovations v. Kirusa Software`).

### 3.3 Refusal & Disclaimer Filtering
Sentences matching non-committal disclaimer templates or explicit refusals are excluded from claim extraction:
* *"I do not have sufficient legal evidence..."*
* *"The provided context does not contain..."*
* Pure structural section headers (*"Analysis:"*, *"Conclusion:"*).

### 3.4 Propositional Atomicity Decomposition
A complex legal sentence is split into distinct claims if it contains:
1. **Semicolons**: Independent coordinate clauses separated by `;`.
2. **Statutory Provisos**: Clauses introduced by `Provided that` or `Provided further that`.
3. **Coordinate Conjunctions**: Independent clauses linked by `, and` followed by a modal operator or distinct legal subject.

### 3.5 Controlled Claim Classification
Claims are deterministically classified into the 15-member `ClaimType` enum via regex feature matching:
`STATUTORY_PROVISION`, `LEGAL_OBLIGATION`, `LEGAL_PROHIBITION`, `LEGAL_PERMISSION`, `LEGAL_REQUIREMENT`, `PROCEDURAL_REQUIREMENT`, `NUMERICAL_REQUIREMENT`, `TEMPORAL_CLAIM`, `AUTHORITY_CLAIM`, `CASE_HOLDING`, `DEFINITION`, `EXCEPTION`, `SCOPE_CLAIM`, `FACTUAL_CLAIM`, `OTHER`.

---

## 4. Verification Milestone Sign-Off

* **Unit Test Suite**: 37 test cases across 10 modules in `halo/claim_extractor/tests/` $\to$ **100% Passed**.
* **Empirical Validation**: 64 B5 Dev answers $\to$ 664 atomic claims extracted, 0 errors, 100.0% byte-for-byte span match, mean latency 2.15 ms/answer.
* **Master Extraction Digest**: `2c0621da98d67cf9ccf84eeec3ed734b128d9c5879cccce5bc92fdc6f9432ede`.
