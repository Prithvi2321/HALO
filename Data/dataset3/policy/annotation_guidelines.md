# HALO Dataset 3: Annotation Guidelines & Labeling Standards

**Document ID**: `HALO-D3-GUIDELINES-v1`  
**Applicability**: All Dataset 3 Benchmark Families (`D3-A` through `D3-M`)

---

## 1. Difficulty Level Taxonomy

Every benchmark record in Dataset 3 must be assigned one of four standardized difficulty tiers based on structural and reasoning complexity:

| Tier | Definition | Examples |
| :--- | :--- | :--- |
| **`easy`** | Direct, verbatim, or near-verbatim statutory inquiry or single-case lookup with unmistakable lexical anchors. Single-passage resolution. | "What is the penalty for contravention under Section 86 of the Companies Act, 2013?"<br>"Which court decided Mobilox Innovations Private Limited v. Kirusa Software?" |
| **`medium`** | Paraphrased natural language question, semantic reformulation, or single-hop interpretation requiring lexical-to-conceptual translation without exact keywords. | "Under what conditions is a corporation exempted from forming a committee for corporate philanthropy?" (Maps to Section 135(1) Proviso). |
| **`hard`** | Complex multi-provision synthesis, cross-subsection exceptions, multi-hop statute-plus-judgment reasoning, or resolution among confounding near-synonyms. | "How does the Supreme Court in Tata Consultancy Services reconcile Section 14 moratorium powers under IBC with arbitration clauses under the Companies Act?" |
| **`adversarial`** | Systematically manipulated claim or prompt specifically engineered to test edge-failure modes: plausible hallucinated citations, swapped metadata, unsupported paragraphs, or bypass instructions. | "In Bhushan Power & Steel, the Supreme Court held at para 22 that State MoUs supersede Section 10A of the amended MMDR Act." (Fabricated legal proposition paired with real case metadata). |

---

## 2. Ground-Truth Relevance Grading for Retrieval

For families `D3-A`, `D3-B`, and `D3-C`, relevance is cataloged with graded values compatible with standard TREC / BEIR evaluation:

- **Grade 2 (`PRIMARY_POSITIVE`)**: The exact subsection, clause, or judgment passage that directly and authoritatively resolves the query.
- **Grade 1 (`CONTEXTUAL_POSITIVE`)**: The parent section or adjacent contextual provision necessary to understand definitions, procedural prerequisites, or provisos.
- **Grade 0 (`NEGATIVE`)**: Unrelated passages.
- **Grade -1 (`HARD_NEGATIVE`)**: Confounding passages (adjacent sections, same terminology in different chapters, irrelevant paragraphs in the same judgment) used specifically in `D3-C`.

---

## 3. Grounded Answer Criteria (`D3-D`)

For Grounded Answer evaluation, records require atomic point decomposition:
1. **`gold_answer`**: Comprehensive, legally accurate synthesis derived strictly from the cited passages.
2. **`acceptable_answer_points`**: A list of independent, atomic legal propositions that must be present in a candidate answer for full credit.
3. **`unacceptable_claims`**: Specific, known potential hallucinations or legal inversions that trigger an immediate penalty if generated.
4. **`required_evidence_ids`**: The minimal set of passage IDs required to establish factual sufficiency.

---

## 4. Adversarial Verification Failure Types (`D3-E`, `D3-F`, `D3-G`)

Adversarial records test the three tiers of verification in HALO:

| Verification Tier | Failure Code | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| **Tier 1: Existence** | `AUTHENTIC_RECORD` | Unmodified real case, real citation, real court, real date. | `SUPPORTED` |
| | `FABRICATED_CASE` | Entirely fictitious case name and party names. | `REJECTED` |
| | `FABRICATED_CITATION` | Real case name paired with an invented reporter volume/page number. | `FLAGGED` / `REJECTED` |
| **Tier 2: Metadata** | `CITATION_SWAP` | Real case paired with a valid citation belonging to a different real case in Dataset 2. | `FLAGGED` |
| | `WRONG_COURT` | Real judgment attributed to the incorrect court or forum (e.g. SC attributed to NCLAT). | `FLAGGED` |
| | `WRONG_DATE` | Real judgment with altered date of decision (>6 months shift). | `FLAGGED` |
| | `NON_EXISTENT_PARA` | Valid case and citation, but cited paragraph index does not exist in the source document. | `FLAGGED` / `REJECTED` |
| **Tier 3: Entailment** | `PASSAGE_UNSUPPORTED` | Valid case, court, citation, and existing paragraph, but the claimed proposition is contradictorily or completely unsupported by the passage text. | `PASSAGE_UNSUPPORTED` / `REJECTED` |

---

## 5. Robustness & Fail-Closed Behavior (`D3-H` through `D3-M`)

- **`D3-H` (Fail-Closed)**: Queries referencing non-existent provisions (e.g., Section 999) or non-existent cases must trigger `expected_behavior = "FAIL_CLOSED"` with empty evidence. Generating an invented answer is scored as a critical failure.
- **`D3-I` (Ambiguity)**: Underspecified inquiries must yield `expected_behavior = "CLARIFICATION_REQUIRED"` or explicit confidence degradation.
- **`D3-J` (Temporal)**: Inquiries spanning repealed 1956 provisions vs 2013 provisions must explicitly surface the applicable temporal period.
- **`D3-K` (Conflict)**: Queries touching divergent rulings between High Courts must return `expected_behavior = "CONFLICT_DETECTED"`.
- **`D3-L` (Out-of-Domain)**: Queries outside Indian corporate law must return `expected_behavior = "OUT_OF_SCOPE"`.
- **`D3-M` (Adversarial Prompts)**: Injections demanding bypass of verification must return `expected_behavior = "BYPASS_REJECTED"`.
