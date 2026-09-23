# HALO Subsystem Protocol: Citation Verifier (CV)

**Protocol Specification**: `CV-v1.0-FROZEN`  
**Pipeline Order**: Subsystem 2 (Post-Claim Extraction, Pre-Evidence Verification)  
**Parent Framework**: HALO (Hallucination-Aware Retrieval and Verification Framework for AI-Assisted Legal Research)

---

## 1. Specification Overview

The Citation Verifier is an immutable, deterministic subsystem tasked with resolving legal authorities cited in natural language legal answers and verifying their metadata against canonical statutory and judicial corpora (D1 and D2).

### Three Verification Tiers
1. **Tier 1: Existence Verification**:
   - Classifies authority existence into:
     - `EXISTS`: Authority or section unambiguously located in canonical legal corpus.
     - `NOT_FOUND`: Searched authoritative corpus and affirmatively established absence.
     - `AMBIGUOUS`: Multiple competing candidates; cannot deterministically resolve to a single authority.
     - `MALFORMED`: Syntactically defective citation string.
     - `UNRESOLVED`: System lookup incomplete or failure to query corpus.
2. **Tier 2: Metadata Verification**:
   - Field-by-field verification of cited attributes against canonical records:
     - `MATCH`: All cited fields (Act title, court, volume year, paragraph bounds) align with canonical record.
     - `PARTIAL_MATCH`: Primary authority exists, but minor field (e.g. subsection nuance) differs.
     - `MISMATCH`: Explicit conflict detected (e.g. Court cited as NCLAT when decided by Supreme Court; paragraph out of bounds; Act enactment year mutated).
     - `UNRESOLVED`: Cannot verify metadata due to non-existent authority.
3. **Tier 3: Claim Association**:
   - Binds verified citations to atomic claims extracted in Subsystem 1 (`halo/claim_extractor/`).
   - Propagates `matched_passage_ids` downstream to Subsystem 3 (`halo/evidence_verifier/`).

---

## 2. Inviolable Governance Gates (CV1–CV14)

| Gate ID | Name | Constraint Description | Enforced By |
| :--- | :--- | :--- | :--- |
| **Gate CV1** | Schema Compliance | Strict dataclass typing matching protocol schema v1.0.0. | `schemas.py` |
| **Gate CV2** | Existence Verification | Resolves existing statutory sections and judgments to `EXISTS`. | `statutory_matcher.py`, `judicial_matcher.py` |
| **Gate CV3** | Adversarial Citation Rejection | Flags fabricated statutes, non-existent sections, and fictitious cases as `NOT_FOUND`. | `corpus_index.py`, `statutory_matcher.py` |
| **Gate CV4** | Metadata Conflict Detection | Audits court, year, and paragraph boundaries. | `metadata_matcher.py` |
| **Gate CV5** | Fuzzy Match Prohibition | `FUZZY_CANDIDATE` matches **NEVER** emit `EXISTS` (must evaluate to `AMBIGUOUS` or `UNRESOLVED`). | `judicial_matcher.py` |
| **Gate CV6** | Claim Association | Multi-claim citations capture all referencing `claim_id`s; matched passages preserved. | `association.py` |
| **Gate CV7** | Span & Text Integrity | Exact character offsets and raw verbatim citation text preserved. | `parser.py`, `verifier.py` |
| **Gate CV8** | Determinism & Auditability | 100% deterministic execution; SHA-256 provenance hashes generated for every record and output payload. | `verifier.py` |
| **Gate CV9** | No Evidence Support Leakage | Strictly prohibits truth/support verdicts (`SUPPORTED`, `CONTRADICTED`, `HALLUCINATED`, `CORRECT`, `INCORRECT`). | `validator.py` |
| **Gate CV10**| Corpus Isolation | Zero mutation of frozen D1, D2, D3, B1-B5, or benchmark files. | `corpus_index.py` |
| **Gate CV11**| Test Split Quarantine | 28 held-out test split cases strictly quarantined from training or tuning. | `tests/test_isolation.py` |
| **Gate CV12**| End-to-End Pipeline | Seamless integration consuming `halo/claim_extractor/` outputs. | `verifier.py`, `verify.py` |
| **Gate CV13**| False Existence Rate (FER) | Zero tolerance ($FER = 0.0\%$) for falsely accepting fabricated citations. | `verify.py`, `tests/test_fabricated.py` |
| **Gate CV14**| High-Throughput Latency | Sub-millisecond mean execution per citation ($< 10$ ms requirement; actual $0.21$ ms). | `verifier.py` |

---

## 3. The 5 Scientific & Engineering Principles

### Principle 1: Direct Canonical Querying (No Arbitrary Numeric Limits)
Earlier designs proposed checking whether a section number exceeded 470 as a heuristic for non-existence. This was rejected because statutory frameworks contain omitted sections, lettered sections (e.g. Section 3A), and schedules. The Citation Verifier queries the canonical index directly (`section_number in d1_sections`), ensuring statutory realism.

### Principle 2: Separation of Authority Existence from Passage Resolution
Authority existence is not synonymous with passage chunk availability. The verifier enforces a four-stage hierarchy:
1. Does the Act / Case exist? (`authority_exists`)
2. Does the Section / Precedent exist? (`section_exists`)
3. Does the Subsection / Coram exist? (`subsection_exists`)
4. Are passage chunks available for retrieval? (`matched_passage_ids`)

### Principle 3: Strict Bar on Near-Match Acceptance
Near-matches on case titles (e.g. token overlap $30\% \le cov < 70\%$) are classified as `FUZZY_CANDIDATE`. A fuzzy candidate is NEVER upgraded to `EXISTS`, preventing synthetic hallucinations from masquerading as authentic precedents.

### Principle 4: Semiotic Separation of UNRESOLVED and NOT_FOUND
`NOT_FOUND` represents positive epistemic knowledge that an authoritative corpus was consulted and the cited authority does not exist. `UNRESOLVED` represents epistemic limitation (e.g. unparseable syntax or ambiguous references).

### Principle 5: False Existence Rate (FER)
A citation verifier that achieves 99% recall but accepts fabricated citations is dangerous for high-stakes legal research. FER is defined as:
$$FER = \frac{FP}{FP + TN}$$
In all evaluations against synthetic adversarial statutes and cases, HALO achieves $FER = 0.0\%$.
