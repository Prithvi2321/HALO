# HALO Evidence Verifier Subsystem

**Protocol Version**: `v1.0-FROZEN`  
**Subsystem**: Third post-generation verification component of the **HALO** (Hallucination-Aware Retrieval and Verification Framework for AI-Assisted Legal Research) pipeline.

---

## 1. Subsystem Mission & Scientific Boundary

The **Evidence Verifier** operates downstream of the **Citation Verifier** and upstream of the **Temporal Verifier** and **Fail-Closed Governor**. Its singular scientific objective is to determine whether authoritative legal passages provide sufficient semantic and normative evidence to warrant generated atomic claims.

### Epistemic Boundary Architecture (Gate EV9)
```
[Claim Extractor] 
      │ (atomic claims + raw citation refs)
      ▼
[Citation Verifier] ── answers: "Does this citation identify a real authority, and is its metadata accurate?"
      │              ── outputs: verified canonical authorities + matched passage IDs
      ▼
[Evidence Verifier] ── answers: "Does that authoritative passage actually support this claim?"
      │              ── outputs: SUPPORTED / CONTRADICTED / PARTIALLY_SUPPORTED / NEUTRAL / CONFLICTED / UNRESOLVED
      ▼
[Temporal Verifier] ── answers: "Is this verified authority currently valid or repealed/amended?"
      ▼
[Fail-Closed Governor] ── answers: "Should this answer be suppressed or emitted?"
```

* **Citation existence != citation support**: Verifying that Section 188(1) or [2017] 10 S.C.R. 1006 exists does *not* imply that the generated legal claim is legally supported by that text.
* **Separation of Concerns (Gate EV9)**:
  - **No Citation Existence Verification**: Handled exclusively by `halo/citation_verifier/`.
  - **No Temporal / Repeal Verification**: Handled exclusively by `halo/temporal_verifier/`.
  - **No Answer Suppression / Abstention**: Handled exclusively by `halo/fail_closed_governor/`.
* **Gate EV10 Truth-Label Anti-Leakage**: Any presence of benchmark ground truth labels (`label`, `ground_truth`, `gold_label`, `verdict_status`) in inference inputs raises a fatal `TruthLabelLeakageError`.

---

## 2. Core Methodological Principles & Innovations

### 1. Inviolable Direction Invariance (Gate EV2)
Natural language inference is strongly asymmetric. In legal hallucination verification:
$$\text{Premise} = \text{Authoritative Evidence Passage}, \quad \text{Hypothesis} = \text{Generated Atomic Claim}$$
Inverting this direction ($\text{Hypothesis} \to \text{Premise}$) asks whether the claim entails the statute, which is legally unsound and strictly forbidden.

### 2. Research-Grade 3-Class NLI Foundation (Gate EV3)
Backed by `cross-encoder/nli-deberta-v3-base` with exact label mapping:
- Class `0`: **CONTRADICTION**
- Class `1`: **ENTAILMENT**
- Class `2`: **NEUTRAL**

Probabilities are computed via softmax over raw logits:
$$P(\text{class}) = \frac{\exp(z_{\text{class}})}{\sum_c \exp(z_c)}$$

### 3. Hybrid Symbolic-Neural Mutation Auditing (Gate EV4)
Pre-trained transformers frequently fail on fine-grained legal mutations. The subsystem combines DeBERTa-v3 with three deterministic symbolic checkers:
- **Numerical & Temporal Mutation (`numerical_checker.py`)**: Audits monetary penalties, percentage thresholds, statutory time limits (days, months, years), and section cross-references.
- **Modality & Deontic Mutation (`modality_checker.py`)**: Detects illicit shifts between mandatory obligations (`shall`, `must`), discretionary permissions (`may`), and prohibitions (`shall not`).
- **Negation & Statutory Inversion (`negation_checker.py`)**: Catches polarity flips, contradictory legal antonym pairs (`prohibited` vs `permitted`), and false affirmative claims against statutory exemptions.

### 4. Canonical Grounding & Authoritative Multi-Passage Resolution (Gate EV5)
When claim snippets are truncated or when citations point to title/caption pages (e.g. `-P001`), the engine automatically queries the authoritative corpus (`d1_sections` and `d2_judgments`). For judicial precedents, substantive ruling passages are scanned to identify the core ratio decidendi (e.g. *Mobilox Innovations* mini-trial doctrine in `P059`).

### 5. Statutory Exception Precedence (*Generalia Specialibus Non Derogant*) (Gate EV6)
Codifies statutory interpretation principles where explicit provisos (e.g. Section 188(1) 3rd proviso for arm's length transactions) take precedence over general statutory prohibitions.

### 6. Threshold Bound Protection (Gate EV7)
Statutory lower and upper bounds (`shall not be less than`, `shall not exceed`) are protected from being misclassified as deontic prohibitions, preventing false polarity flips on minimum penalty provisions.

---

## 3. Subsystem Layout

```
halo/evidence_verifier/
├── __init__.py                  # Public API exports (EvidenceVerifier, verify_evidence, etc.)
├── config.py                    # Configuration, paths, threshold defaults, SHA-256 hash
├── schemas.py                   # Pydantic & dataclass schemas (Tiers 1-3, Verdict, Inputs)
├── exceptions.py                # Exception hierarchy (TruthLabelLeakageError, etc.)
├── evidence_store.py            # Read-only corpus index over frozen D1 (Statutes) and D2 (Judgments)
├── validator.py                 # Input validation and Gate EV10 anti-leakage audit
├── nli_engine.py                # DeBERTa-v3 cross-encoder inference engine with provenance
├── numerical_checker.py         # Deterministic numerical, currency, time, ratio auditor
├── modality_checker.py          # Deterministic deontic modality auditor (shall / may / must)
├── negation_checker.py          # Deterministic legal negation & antonym polarity auditor
├── aggregator.py                # Hybrid verdict aggregator (Neural + Symbolic fusion)
├── verifier.py                  # Master EvidenceVerifier pipeline coordinator
├── verify.py                    # CLI batch execution runner with SHA-256 run manifest
├── test_quarantine_manifest.json# Test split quarantine manifest (evaluation_allowed: false)
└── tests/                       # 18 test modules covering Gates EV1–EV16 (51/51 tests passing)
```

---

## 4. Empirical Evaluation & Benchmarks

### 1. Test Split Quarantine (EV12)
The 28 held-out test cases in `halo_datasets/splits/test.jsonl` (hash: `1bdcea5524d17d94a1ee271ac5545e9bb50c0d4cd93d27e6dfba4d238d6b3ac0`) are strictly quarantined under `test_quarantine_manifest.json` (`evaluation_allowed: false`) to preserve benchmark integrity.

### 2. Comprehensive Test Suite Results
- **Unit Test Suite (`halo/evidence_verifier/tests/`)**: **51 / 51 passed (100%)** in 1.48s.
- **Citation Verifier Regression Suite (`halo/citation_verifier/tests/`)**: **31 / 31 passed (100%)** in 0.27s (zero regressions).
- **Passage Verification Suite (`tests/test_passage_verification.py`)**: **24 / 24 benchmark cases passed (100%)**.

### 3. Calibrated Safety-First Thresholds
Calibrated exclusively on the Dev split to minimize Unsafe Falsity Acceptance Rate (UFAR) subject to Safe Falsity Rejection Rate (SFRR $\le 0.15$):
- `entailment_min`: **0.70**
- `contradiction_min`: **0.65**
- `contradiction_max_for_entailment`: **0.10**
- `entailment_max_for_contradiction`: **0.10**

### 4. Category-Specific Benchmark Accuracy
- **Pure Passage Support**: **100.0%** (Dev: 6/6), **93.75%** (Train: 15/16)
- **Conflict Detection**: **100.0%** (Dev: 2/2, Train: 5/5)
- **Modality Mutation**: **100.0%** (Dev: 1/1, Train: 10/13 = 76.9%)
- **Numerical Mutation**: **82.35%** (Train: 14/17)
- **Fail-Closed Cases**: **100.0%** (Train: 8/8)

---

## 5. Usage: Python API & Batch CLI

### Python API
```python
from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.schemas import ClaimVerificationInput, CitationReferenceInput

verifier = EvidenceVerifier()

# 1. Direct claim verification against citation passage IDs
claim_input = ClaimVerificationInput(
    answer_id="ANS_001",
    claim_id="ANS_001_C01",
    claim_text="Under Section 135(1) of the Companies Act, 2013, CSR committee is mandatory for companies meeting financial thresholds.",
    citation_refs=[
        CitationReferenceInput(
            citation_id="CIT_001",
            passage_id="PAS_ACT_COMPANIES_2013_SEC_135_SUB_1",
            verification_status="EXISTS"
        )
    ]
)

verdict = verifier.verify_claim(claim_input)
print(verdict.status)            # "SUPPORTED"
print(verdict.confidence_score)  # 0.941
print(verdict.entailment_prob)   # 0.941
print(verdict.explanation)       # "Supported by authoritative passage."

# 2. Arbitrary text pair verification
text_verdict = verifier.verify_claim_against_passage(
    claim_text="Every company shall have at least one woman director.",
    passage_text="Section 149(1): Provided that such class or classes of companies as may be prescribed shall have at least one woman director."
)
print(text_verdict.status)       # "SUPPORTED"
```

### Batch Pipeline CLI
```bash
# Execute end-to-end batch verification across verified citations:
python -m halo.evidence_verifier.verify \
  --input experiments/runs/citation_verifier/dev_verified_citations.jsonl \
  --output experiments/runs/evidence_verifier/dev_verified_evidence.jsonl
```
Produces `dev_verified_evidence.jsonl` along with a cryptographic `run_manifest.json` containing run metadata, model provenance, verdict breakdown, and SHA-256 output hashes.
