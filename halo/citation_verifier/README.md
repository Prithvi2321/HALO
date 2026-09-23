# HALO Citation Verifier Subsystem

**Protocol Version**: `v1.0-FROZEN`  
**Subsystem**: Second post-generation verification component of the **HALO** (Hallucination-Aware Retrieval and Verification Framework for AI-Assisted Legal Research) pipeline.

---

## 1. Subsystem Mission & Scientific Boundary

The Citation Verifier operates downstream of the **Claim Extractor** and upstream of the **Evidence Verifier**.

### Epistemic Boundary (Gate CV9)
```
[Claim Extractor] 
      │
      ▼ (atomic claims + citation refs)
[Citation Verifier] ── answers: "Does this citation identify a real authority, and is its metadata accurate?"
      │              ── CANNOT emit: SUPPORTED / CONTRADICTED / HALLUCINATED / CORRECT / INCORRECT
      ▼ (verified authorities + matched passage IDs)
[Evidence Verifier] ── answers: "Does that authoritative passage actually support this claim?"
```
* **Citation existence != citation support**. Verifying that Section 135(1) or [2016] 11 S.C.R. 149 exists does *not* imply that the generated legal claim is factually true or legally supported.
* **Gate CV9 Violation Enforcement**: Any attempt by the Citation Verifier to emit truth/support verdicts raises an immediate fatal `EvidenceLeakageViolationError`.

---

## 2. Architecture & The 5 Core Principles

1. **Canonical Corpus Querying (No Hard-Coded Numeric Bounds)**:
   - Evaluates whether an enactment or section exists by querying the authoritative in-memory index (`d1_sections`), never assuming statutory section bounds (e.g. avoiding brittle assumptions like `section > 470 = NOT_FOUND`).
2. **Separation of Authority Existence from Passage Existence**:
   - Explicit 4-tier hierarchy:
     $$\text{Authority Existence} \longrightarrow \text{Section Existence} \longrightarrow \text{Subsection Existence} \longrightarrow \text{Passage Resolution}$$
   - A statutory provision or judicial precedent can validly exist even if the current segmentation index does not provide granular sub-clause passages.
3. **Strict Bar on FUZZY_CANDIDATE for Existence Decisions (Gate CV5)**:
   - `EXACT_MATCH` $\to$ `EXISTS`
   - `NORMALIZED_MATCH` $\to$ `EXISTS`
   - `FUZZY_CANDIDATE` $\to$ `AMBIGUOUS` or `UNRESOLVED` (NEVER `EXISTS`). Sub-threshold near-matches cannot convert fabricated or ambiguous citations into valid authorities.
4. **Strict Distinction Between UNRESOLVED and NOT_FOUND**:
   - `NOT_FOUND`: Canonical authoritative corpus searched and affirmative absence established (e.g. non-existent Section 480 or fabricated Act).
   - `UNRESOLVED`: System could not establish existence due to unresolvable ambiguity, missing index context, or external lookup error.
   - `MALFORMED`: Unparseable or syntactic invalidity.
   - `AMBIGUOUS`: Multiple competing authority candidates.
5. **False Existence Rate (FER) as a First-Class Safety Metric**:
   - $$FER = \frac{FP}{FP + TN}$$
   - Measures the proportion of non-authoritative or fabricated citations falsely classified as `EXISTS`. In safety-critical legal AI, $FER = 0.0\%$ is non-negotiable.

---

## 3. Subsystem Layout

```
halo/citation_verifier/
├── __init__.py               # Public API exports
├── config.py                 # Paths to frozen corpora (D1 & D2) and thresholds
├── schemas.py                # Pydantic/dataclass schemas for Tiers 1-3
├── exceptions.py             # Error hierarchy (EvidenceLeakageViolationError, etc.)
├── normalizer.py             # Text standardization & canonical key generators
├── parser.py                 # Structured citation extraction (Statute, Case, Reporter)
├── corpus_index.py           # In-memory read-only index over frozen D1 & D2
├── metadata_matcher.py       # Tier 2 court, year, section, para bound auditing
├── statutory_matcher.py      # D1 Companies Act hierarchical resolution
├── judicial_matcher.py       # D2 Supreme Court judgment resolution
├── association.py            # Tier 3 Citation-to-Claim association
├── validator.py              # Input validation and Gate CV9 truth-leakage audit
├── verifier.py               # Master CitationVerifier pipeline engine
├── verify.py                 # CLI batch verification runner
└── tests/                    # 11 unit test modules covering Gates CV1–CV14
```

---

## 4. Empirical Evaluation on Frozen Benchmark

Evaluated on Train and Dev splits (41 benchmark cases) with the held-out Test split (28 cases) strictly quarantined:

| Metric | Target | Benchmark Result | Status |
| :--- | :--- | :--- | :--- |
| **Tier 1 Existence Accuracy** | $\ge 95.0\%$ | **100.0%** | Passed |
| **False Existence Rate (FER)** | **0.0%** | **0.0%** (0/9 fabricated accepted) | Passed |
| **Fabricated Citation Recall** | $100.0\%$ | **100.0%** (9/9 fabricated caught) | Passed |
| **Existence Precision / Recall / F1** | $\ge 95.0\%$ | **100.0% / 100.0% / 100.0%** | Passed |
| **Mean Verification Latency** | $< 10.0$ ms | **0.212 ms** ($>4,500$ cit/s) | Passed |
| **Gate CV9 Truth Leakage Audit** | **0 leaks** | **0 leaks detected** | Passed |
| **Unit Test Suite (CV1–CV14)** | $100\%$ | **31 / 31 passed (0.27s)** | Passed |

---

## 5. Usage CLI & Python API

### Python API
```python
from halo.citation_verifier.verifier import verify_citations

# 1. Direct text verification
result = verify_citations("Under Section 135(1) of the Companies Act, 2013, CSR is mandatory.")
record = result.citation_results[0]
print(record.existence.status)  # "EXISTS"
print(record.canonical_authority_id)  # "ACT_COMPANIES_2013_SEC_135"

# 2. End-to-end payload from Claim Extractor
claim_payload = {
    "answer_id": "ANS_001",
    "claims": [
        {
            "claim_id": "ANS_001_C01",
            "claim_text": "Section 188(1) regulates related party transactions.",
            "citation_refs": [{"citation_text": "Section 188(1)"}]
        }
    ]
}
res = verify_citations(claim_payload)
print(res.citation_results[0].claim_ids)  # ["ANS_001_C01"]
print(res.citation_results[0].existence.matched_passage_ids)  # Preserved for Evidence Verifier
```

### Batch CLI
```bash
python -m halo.citation_verifier.verify \
  --input experiments/runs/claim_extractor/dev_extracted_claims.jsonl \
  --output experiments/runs/citation_verifier/dev_verified_citations.jsonl
```
