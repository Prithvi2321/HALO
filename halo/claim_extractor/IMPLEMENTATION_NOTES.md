# HALO Claim Extractor — Implementation Notes

**Subsystem**: `halo/claim_extractor/`  
**Protocol Version**: `v1.0-FROZEN`  
**Role**: Senior ML Engineer + NLP Research Engineer + Backend Architect  
**Status**: Implementation Phase  

---

## 1. Discovered Formats & Repository Context

### A. Baseline 5 (B5) Output Format
Inspected from [`experiments/runs/b5_reranker/dev_run_output.jsonl`](file:///c:/HALO/experiments/runs/b5_reranker/dev_run_output.jsonl):
* **Record Structure**:
  ```json
  {
    "experiment_id": "EXP_B5_HYBRID_CE_DEV_20260916_140901_v1.0",
    "system_id": "B5_HYBRID_CROSS_ENCODER",
    "query_id": "D3_RET_000007",
    "benchmark_family": "D3-A",
    "split": "dev",
    "query": "What does Section 102 of the Companies Act, 2013 prescribe...",
    "retrieval": { ... },
    "generation": {
      "model": "qwen/qwen3.8-27b",
      "provider": "groq",
      "predicted_answer": "Based on the authoritative legal evidence provided, Section 102(1)...",
      "generation_latency_ms": 1100.0
    },
    "verification": { ... }
  }
  ```
* **Extraction Target**: The primary input to the Claim Extractor is `generation.predicted_answer` (or any raw legal text string). The `query_id` is mapped to `answer_id`.

### B. Frozen Verification Benchmark Format
Inspected from [`halo_datasets/claim_evidence/claim_evidence.jsonl`](file:///c:/HALO/halo_datasets/claim_evidence/claim_evidence.jsonl):
* **Record Structure**:
  ```json
  {
    "id": "CIT_EXIST_001",
    "query": "What are the CSR committee constitution thresholds?",
    "generated_claim": "Section 135(1) mandates a CSR Committee for companies meeting net worth of ₹500 crore.",
    "citation": {"act": "Companies Act, 2013", "section": "135", "subsection": "1"},
    "expected_status": "SUPPORTED",
    "authoritative_passage_id": "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
    "evidence_passage": "(1) Every company having net worth of rupees five hundred crore...",
    "verification_tier": "EXISTENCE",
    "difficulty": "easy",
    "source": "Companies Act, 2013",
    "source_dataset": "D1",
    "case_type": "citation_existence",
    "mutation_type": null,
    "mutation_details": null,
    "expected_behavior": "ACCEPT",
    "explanation": "Section 135 exists in authoritative statutory corpus.",
    "content_hash": "b2f67..."
  }
  ```
* **Integration Alignment**: Benchmark claims (such as in `compound_claims.jsonl`, `numerical_mutations.jsonl`, `modality_mutations.jsonl`) represent canonical atomic or compound claims that the Claim Extractor will segment, classify, and span-align.

---

## 2. Integration Assumptions & Architecture Boundaries

1. **Retriever Independence**:
   - The Claim Extractor has **zero direct coupling to the B5 retriever**.
   - Input: A text answer string (and optional metadata like `answer_id`).
   - Output: An immutable, structured collection of `ExtractedClaim` objects with exact character spans, citation associations, and controlled claim types.
2. **Strict Separation of Extraction vs Verification**:
   - The Claim Extractor **NEVER assigns legal truth values** (`SUPPORTED`, `CONTRADICTED`, `HALLUCINATED`, `TRUE`, `FALSE`).
   - Downstream verification engines (`citation_verifier`, `evidence_verifier`, `temporal_verifier`) consume the extracted atomic claims.
3. **Deterministic Span Integrity**:
   - Character spans (`start_char`, `end_char`) are calculated on the raw, un-normalized input text.
   - For every extracted claim: `input_text[start_char:end_char] == source_text` must strictly hold (100% span integrity).
4. **Controlled Controlled Claim Types**:
   - Claims must be classified into the 15-member enum:
     `STATUTORY_PROVISION`, `LEGAL_OBLIGATION`, `LEGAL_PROHIBITION`, `LEGAL_PERMISSION`, `LEGAL_REQUIREMENT`, `PROCEDURAL_REQUIREMENT`, `NUMERICAL_REQUIREMENT`, `TEMPORAL_CLAIM`, `AUTHORITY_CLAIM`, `CASE_HOLDING`, `DEFINITION`, `EXCEPTION`, `SCOPE_CLAIM`, `FACTUAL_CLAIM`, `OTHER`.
5. **No Modification of Frozen Assets**:
   - Datasets D1, D2, D3, Baselines B1–B5, and `halo_datasets/` (all 19 assets) remain read-only and cryptographically untouched.

---

## 3. Dependencies & Conventions

* **Standard Library Priority**: `re`, `json`, `hashlib`, `datetime`, `uuid`, `dataclasses`, `typing`, `enum`, `os`, `sys`, `argparse`.
* **Zero External Network Dependencies**: The core deterministic pipeline does not require live API calls, ensuring offline determinism and reproducible latency.
* **Hash Computation**: SHA-256 for `input_hash` (over raw text) and `output_hash` (over canonical JSON dump of claims).
