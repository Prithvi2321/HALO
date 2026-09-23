# HALO — Claim Extractor Subsystem (`halo/claim_extractor/`)

**Subsystem**: Stage 1 of the HALO Verification Framework  
**Protocol Version**: `v1.0-FROZEN`  
**Downstream Consumer**: Citation Verifier, Evidence Verifier, Temporal Verifier, Fail-Closed Governor  
**Input Source**: Baseline 5 Grounded Generations (`predicted_answer`)  

---

## 1. Overview & Architectural Role

The **Claim Extractor** decomposes generated legal answers into discrete, atomic, and independently verifiable legal propositions without determining their truth, falsity, or verification status.

```text
[B5 Generated Legal Answer]
          │
          ▼
1. Legal Sentence Segmentation (Abbreviation Protection: Sec., w.e.f., Ltd., v., S.C.R.)
          │
          ▼
2. Citation Detection & Span Offsets (Statutory: Sec. 135(1); Judicial: [2018] 1 SCC 353)
          │
          ▼
3. Refusal & Boilerplate Filter ("I do not have sufficient legal evidence...")
          │
          ▼
4. Propositional Atomicity Decomposition (Coordinate clauses, semicolons, provisos)
          │
          ▼
5. Controlled Claim Classification (15-member ClaimType Enum)
          │
          ▼
6. Citation Proximity Association (Same sentence -> Adjacent sentence fallback)
          │
          ▼
7. Byte-Level Span Integrity Audit (Guarantees text[start:end] == source_text)
          │
          ▼
8. Gate C9 Audit: Zero Truth Leakage (Ensures epistemic neutrality)
          │
          ▼
[Audited Atomic Claims Collection + Canonical SHA-256 Digest]
```

---

## 2. Inviolable Design Constraints

1. **Gate C9 — Epistemic Neutrality (No Truth Leakage)**:
   The Claim Extractor **NEVER** assigns verification verdicts (`SUPPORTED`, `CONTRADICTED`, `HALLUCINATED`, `CORRECT`, `INCORRECT`). Truth evaluation is strictly the domain of downstream verifiers.
2. **Gate C7 — Byte-for-Byte Span Integrity**:
   For 100% of extracted claims: `answer_text[claim.source_span.start_char:claim.source_span.end_char] == claim.source_span.source_text`.
3. **Controlled Claim Classification**:
   Every claim is classified into the controlled 15-member `ClaimType` enum.
4. **Zero Mutation of Frozen Assets (Gate C10)**:
   Datasets D1, D2, D3, baselines B1–B5, and `halo_datasets/` remain read-only.
5. **Test Split Quarantine (Gate C11)**:
   The 28 test benchmark cases in `halo_datasets/splits/test.jsonl` remain isolated.

---

## 3. Controlled `ClaimType` Enum

| Claim Type | Legal Meaning | Example Pattern |
| :--- | :--- | :--- |
| `STATUTORY_PROVISION` | Direct statutory citation or statement of section | *"Section 135 of the Companies Act, 2013..."* |
| `LEGAL_OBLIGATION` | Mandatory duty imposed by law | *"The Board shall constitute a CSR committee..."* |
| `LEGAL_PROHIBITION` | Absolute negative legal bar | *"No company shall contribute to any political party..."* |
| `LEGAL_PERMISSION` | Discretionary option granted to entity | *"A company may contribute to bona fide funds..."* |
| `LEGAL_REQUIREMENT` | General governing legal condition | *"The resolution requires approval of directors..."* |
| `PROCEDURAL_REQUIREMENT` | Meeting, voting, or notice formality | *"Notice of at least 21 clear days is required..."* |
| `NUMERICAL_REQUIREMENT` | Quantitative threshold or monetary amount | *"Net worth of ₹500 crore or turnover of ₹1,000 crore"* |
| `TEMPORAL_CLAIM` | Temporal validity, amendment, or effective date | *"Came into force w.e.f. 01.04.2014..."* |
| `AUTHORITY_CLAIM` | Jurisdiction of regulatory or judicial forum | *"NCLT possesses exclusive jurisdiction under IBC..."* |
| `CASE_HOLDING` | Judicial precedent or court ratio decidendi | *"The Supreme Court held in Mobilox Innovations..."* |
| `DEFINITION` | Statutory term definition or deeming clause | *"Small company is defined under Section 2(85)..."* |
| `EXCEPTION` | Statutory proviso or saving carveout | *"Provided that private companies are exempt..."* |
| `SCOPE_CLAIM` | Applicability or exemption boundary | *"Applies to every listed public company..."* |
| `FACTUAL_CLAIM` | Empirical or factual assertion | *"The transaction was executed on 12th August..."* |
| `OTHER` | Controlled fallback | Any remaining non-categorized claim |

---

## 4. Empirical Validation: B5 Dev Answers

Validated against 64 generated legal answers from Baseline 5 (`experiments/runs/b5_reranker/dev_run_output.jsonl`):

| Metric | Empirical Value | Status |
| :--- | :--- | :--- |
| **Total Records Processed** | 64 | Complete |
| **Total Claims Extracted** | 664 | Validated |
| **Average Claims per Answer** | 10.38 | Nominal |
| **Total Citations Detected** | 556 | Validated |
| **Span Integrity Match Rate** | **100.0% (664 / 664)** | **Zero Span Drift** |
| **Mean Extraction Latency** | **2.15 ms** / answer | Highly performant |
| **Output Digest** | `2c0621da98d67cf9ccf84eeec3ed734b128d9c5879cccce5bc92fdc6f9432ede` | Frozen |

---

## 5. Usage

### Python API
```python
from halo.claim_extractor import extract_claims, ClaimExtractor

# Convenience function
result = extract_claims(
    "Section 135(1) mandates a CSR Committee for companies meeting net worth of ₹500 crore.",
    answer_id="Q_001"
)

for claim in result.claims:
    print(f"[{claim.claim_type}] {claim.claim_text}")
    print(f"Span: {claim.source_span.start_char}-{claim.source_span.end_char}")
```

### CLI Batch Extraction
```bash
python -m halo.claim_extractor.extract \
  --input experiments/runs/b5_reranker/dev_run_output.jsonl \
  --output experiments/runs/claim_extractor/dev_extracted_claims.jsonl
```

### Running Test Suite
```bash
python -m pytest halo/claim_extractor/tests -v
```
All **37 test cases** pass cleanly with 100% compliance across all 12 Acceptance Gates (C1–C12).
