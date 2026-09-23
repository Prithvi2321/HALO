# HALO Subsystem Protocol: Evidence Verifier (EV)

**Protocol Specification**: `EV-v1.0-FROZEN`  
**Pipeline Order**: Subsystem 3 (Post-Citation Verification, Pre-Temporal Verification)  
**Parent Framework**: HALO (Hallucination-Aware Retrieval and Verification Framework for AI-Assisted Legal Research)

---

## 1. Specification Overview

The **Evidence Verifier** is an immutable, research-grade post-generation subsystem designed to establish whether authoritative legal passages (statutes or judicial precedents) provide sufficient semantic, numerical, deontic, and statutory warrant for extracted atomic legal claims.

### The Verification Hierarchy
1. **Passage Retrieval & Grounding**:
   - Accepts authoritative passage IDs produced by Subsystem 2 (`halo/citation_verifier/`).
   - Fetches verbatim text chunks from frozen, read-only corpora (D1 statutory provisions and D2 judicial judgments).
   - Resolves canonical sections and substantive judicial passages when citations reference preview snippets or title pages.
2. **Hybrid Neural-Symbolic Auditing**:
   - Passes evidence-claim pairs through `cross-encoder/nli-deberta-v3-base` to obtain raw softmax probabilities for Entailment, Contradiction, and Neutral.
   - Concurrently executes deterministic symbolic auditors for numerical mutation, deontic modality shifts, and negation/polarity inversions.
3. **Verdict Aggregation & Epistemic Classification**:
   - Integrates neural and symbolic signals into one of six mutually exclusive epistemic statuses:
     - `SUPPORTED`: Claim is fully warranted by authoritative text.
     - `CONTRADICTED`: Claim directly conflicts with authoritative text or embodies an illicit factual/legal mutation.
     - `PARTIALLY_SUPPORTED`: Compound claim with mixed subclaim support.
     - `NEUTRAL`: Passage discusses related subject matter but lacks sufficient evidence to warrant or refute the claim.
     - `CONFLICTED`: Competing authoritative passages yield conflicting evidence.
     - `UNRESOLVED`: Passage missing from index, non-existent authority, or verification failure.

---

## 2. Inviolable Governance Gates (EV1–EV16)

| Gate ID | Name | Constraint Description | Enforced By |
| :--- | :--- | :--- | :--- |
| **Gate EV1** | Schema Compliance | Strict dataclass typing matching protocol schema v1.0.0; serializable to JSON/JSONL. | `schemas.py` |
| **Gate EV2** | Direction Invariance | Direction MUST be $\text{Premise} = \text{Evidence Passage}$, $\text{Hypothesis} = \text{Atomic Claim}$. Inversion strictly forbidden. | `nli_engine.py`, `verifier.py` |
| **Gate EV3** | 3-Class NLI Engine | `cross-encoder/nli-deberta-v3-base` with exact ID mapping: 0=Contradiction, 1=Entailment, 2=Neutral. | `nli_engine.py` |
| **Gate EV4** | Symbolic Mutation Checkers | Deterministic verification of numbers, currencies, dates, timeframes, modality, and negation. | `numerical_checker.py`, `modality_checker.py`, `negation_checker.py` |
| **Gate EV5** | Canonical Grounding | Queries read-only corpus index; retrieves substantive passages when preview snippets are truncated or citations point to title pages. | `evidence_store.py`, `verifier.py` |
| **Gate EV6** | Statutory Exception Precedence | Codifies *generalia specialibus non derogant*: specific statutory provisos override general prohibitions. | `negation_checker.py`, `aggregator.py` |
| **Gate EV7** | Threshold Bound Protection | Preserves minimum/maximum penalty bounds (`shall not be less than`) from misclassification as prohibitions. | `negation_checker.py` |
| **Gate EV8** | Epistemic Verdict Separation | Emits 6 distinct statuses (`SUPPORTED`, `CONTRADICTED`, `PARTIALLY_SUPPORTED`, `NEUTRAL`, `CONFLICTED`, `UNRESOLVED`). | `schemas.py`, `aggregator.py` |
| **Gate EV9** | Responsibility Boundary | Zero citation existence verification, zero temporal/repeal checks, zero answer suppression. | `validator.py`, `verifier.py` |
| **Gate EV10**| Truth-Label Anti-Leakage | Zero access to benchmark gold labels (`label`, `ground_truth`, etc.); raises `TruthLabelLeakageError` immediately. | `validator.py` |
| **Gate EV11**| Corpus Immutability | Strictly read-only access to frozen datasets D1, D2, and D3. Mutation strictly forbidden. | `evidence_store.py` |
| **Gate EV12**| Test Quarantine Enforcement | Quarantines 28 held-out test split cases (`test_quarantine_manifest.json`) with `evaluation_allowed: false`. | `evaluate_evidence_benchmark.py` |
| **Gate EV13**| Safety Calibration Protocol | Threshold tuning conducted exclusively on Train and Dev splits via safety-objective optimization. | `evaluate_evidence_benchmark.py` |
| **Gate EV14**| Safety-First Metrics | Primary optimization target: minimize UFAR (Unsafe Falsity Acceptance Rate) subject to SFRR bounds. | `evaluate_evidence_benchmark.py` |
| **Gate EV15**| Sub-Passage Localization | Preserves character spans and localized evidence references for auditability. | `verifier.py`, `schemas.py` |
| **Gate EV16**| Auditability & Provenance | Generates deterministic SHA-256 hashes for configurations, inputs, outputs, and model weights. | `config.py`, `verifier.py`, `verify.py` |

---

## 3. Scientific Foundations & Engineering Architecture

### 3.1 Asymmetric Directionality (Gate EV2)
The semantic entailment relationship $P \models H$ is asymmetric. In legal adjudication, an authoritative statute or precedent serves as the normative baseline ($P$). The generated claim is a candidate proposition ($H$). Evaluating $H \models P$ asks whether the LLM's assertion entails the statutory code, which produces catastrophic false positives on broad or vacuous claims. Evidence Verifier hardcodes:
```python
premise = evidence_passage.text
hypothesis = atomic_claim.claim_text
```

### 3.2 Hybrid Neuro-Symbolic Fusion (Gates EV3 & EV4)
Transformers exhibit blind spots in legal reasoning, particularly with fine-grained numerical alterations (e.g. changing 10 lakh to 25 lakh) or subtle deontic shifts (e.g. changing *may* to *shall*).
The subsystem resolves this by running neural inference and symbolic auditors in parallel:
- If a symbolic auditor detects a hard contradiction (e.g. numerical mismatch on the same statutory topic, or deontic mutation from discretionary to mandatory), the symbolic signal takes precedence over DeBERTa's neutral or entailment probability.
- If no symbolic mutation is found, the neural engine's probability distribution governs the verdict according to calibrated decision boundaries.

### 3.3 Statutory Interpretation: Generalia Specialibus Non Derogant (Gate EV6)
In Indian company law, general rules are frequently qualified by specific provisos. For example:
- Section 188(1) prohibits related party transactions without board approval.
- The 3rd proviso explicitly states: *Nothing in this sub-section shall apply to any transactions entered into by the company in its ordinary course of business other than transactions which are not on an arm's length basis.*
A naive NLI system flags a contradiction between an arm's length claim and the general prohibition. Evidence Verifier incorporates proviso-aware logic, recognizing statutory exemptions as legitimate legal defenses rather than contradictions.

### 3.4 Threshold Bound Protection (Gate EV7)
Statutory penalties often prescribe mandatory minimums:
- Section 447: *imprisonment for a term which shall not be less than six months...*
The word *not* in *shall not be less than* is a lower bound scalar modifier, not a deontic prohibition. Gate EV7 filters out scalar modifiers before evaluating negation polarity, ensuring minimum statutory sentences are correctly supported.

---

## 4. Safety Metrics & Threshold Calibration Protocol

### 4.1 Safety Metrics Formulation
In high-stakes legal AI, emitting a hallucinated or contradicted claim as `SUPPORTED` constitutes an unsafe failure mode (Type I legal error), whereas marking a true claim as `UNRESOLVED` or `NEUTRAL` is merely conservative (Type II legal error).

The protocol evaluates four safety metrics:
1. **Unsafe Falsity Acceptance Rate (UFAR)**:
   $$\text{UFAR} = \frac{FP_{\text{supported}}}{FP_{\text{supported}} + TN}$$
   Proportion of invalid/hallucinated claims falsely certified as `SUPPORTED`.
2. **Safe Falsity Rejection Rate (SFRR)**:
   $$\text{SFRR} = \frac{FN_{\text{supported}}}{TP_{\text{supported}} + FN_{\text{supported}}}$$
   Proportion of truly supported claims conservatively rejected or classified as neutral.
3. **Uncertainty Rate (UR)**:
   $$\text{UR} = \frac{N_{\text{unresolved}}}{N_{\text{total}}}$$
   Proportion of claims where the verifier abstained due to missing or ungrounded evidence.
4. **Contradiction False Negative Rate (CFNR)**:
   $$\text{CFNR} = \frac{FN_{\text{contradicted}}}{TP_{\text{contradicted}} + FN_{\text{contradicted}}}$$
   Proportion of legal contradictions that went undetected.

### 4.2 Optimization Objective
Threshold calibration explores an 81-point grid over:
$$\tau_{\text{ent}} \in [0.70, 0.90], \quad \tau_{\text{cont}} \in [0.65, 0.85]$$
Selecting the parameter set that minimizes $\text{UFAR}$ subject to $\text{SFRR} \le 0.15$:
$$\theta^* = \arg\min_\theta \text{UFAR}(\theta) \quad \text{s.t.} \quad \text{SFRR}(\theta) \le 0.15$$

---

## 5. Test Split Quarantine Protocol (Gate EV12)

1. **Quarantine Manifest**: `halo/evidence_verifier/test_quarantine_manifest.json`
2. **Quarantined Artifact**: `halo_datasets/splits/test.jsonl`
3. **Cryptographic SHA-256 Digest**: `1bdcea5524d17d94a1ee271ac5545e9bb50c0d4cd93d27e6dfba4d238d6b3ac0`
4. **Execution Status**: `evaluation_allowed: false`
5. **Enforcement**: Any CLI or harness invocation that attempts to load `test.jsonl` raises a fatal exit code and halts immediately.
