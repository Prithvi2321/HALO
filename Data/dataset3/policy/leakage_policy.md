# HALO Dataset 3: Data Leakage Prevention Policy & Split Strategy

**Document ID**: `HALO-D3-LEAKAGE-POLICY-v1`  
**Applicability**: Train / Dev / Test Partitions across Dataset 3

---

## 1. Cardinal Rule: Legal-Unit Partitioning

In standard machine learning, datasets are frequently split by randomly allocating individual queries (e.g. 70% Train, 15% Dev, 15% Test via `random.random()`). 

**In legal retrieval and statutory evaluation, random query splitting causes catastrophic data leakage.**
If four queries are derived from Section 135 (Corporate Social Responsibility) and three are assigned to the Training set while one is assigned to the Test set, the evaluation measures mere memorization of the statutory provision rather than genuine generalization.

### The Invariant:
> **All queries and evidence originating from the same atomic legal unit must reside exclusively within the same partition.**

```text
                      LEGAL UNIT (SECTION / JUDGMENT)
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
         All Questions Generated           All Questions Generated
           from Section 135                   from Tata v. Vishal
                    │                                 │
                    ▼                                 ▼
             ASSIGN TO DEV                     ASSIGN TO TEST
           (Never Split Across)               (Never Split Across)
```

---

## 2. Partitioning Units

1. **Statutory Evidence (Dataset 1)**:
   - The atomic legal unit is the **Section** (e.g. `ACT_COMPANIES_2013_SEC_135`).
   - All subsections, clauses, provisos, explanations, and corresponding retrieval passages derived from Section $X$ are bound to Section $X$.
   - Any query whose primary positive evidence is Section $X$ is assigned to the partition containing Section $X$.

2. **Judicial Evidence (Dataset 2)**:
   - The atomic legal unit is the **Judgment** (e.g. `JUD-SC-2021-2021_10_1080_1103`).
   - All paragraphs, passages, and holdings derived from Judgment $J$ are bound to Judgment $J$.
   - Any query whose primary positive evidence is Judgment $J$ is assigned to the partition containing Judgment $J$.

3. **Multi-Hop / Hybrid Evidence (Dataset 1 + Dataset 2)**:
   - Queries combining both a statutory section and a judicial interpretation are assigned based on the primary governing judgment, while ensuring no component section has conflicting positive labels in the test set.

---

## 3. Stratification & Allocation Targets

Partitions are determined using deterministic cryptographic hashing (SHA-256 of `unit_id + seed`) stratified across:
- **Statutory Stratification**: Balanced across all 29 Chapters of the Companies Act, 2013.
- **Judicial Stratification**: Balanced across the 3 court forums (Supreme Court, NCLAT, High Courts).

Target Distribution:
- **TRAIN**: ~70% of legal units
- **DEV**: ~15% of legal units
- **TEST**: ~15% of legal units

---

## 4. Mathematical Leakage Invariants & Automated Auditing

Before Dataset 3 can be approved or frozen, the automated QA suite must prove:

$$\text{Sections}(\text{Train}) \cap \text{Sections}(\text{Dev}) = \emptyset$$
$$\text{Sections}(\text{Train}) \cap \text{Sections}(\text{Test}) = \emptyset$$
$$\text{Sections}(\text{Dev}) \cap \text{Sections}(\text{Test}) = \emptyset$$

$$\text{Judgments}(\text{Train}) \cap \text{Judgments}(\text{Dev}) = \emptyset$$
$$\text{Judgments}(\text{Train}) \cap \text{Judgments}(\text{Test}) = \emptyset$$
$$\text{Judgments}(\text{Dev}) \cap \text{Judgments}(\text{Test}) = \emptyset$$

$$\text{Passages}(\text{Train}) \cap \text{Passages}(\text{Dev}) = \emptyset$$
$$\text{Passages}(\text{Train}) \cap \text{Passages}(\text{Test}) = \emptyset$$
$$\text{Passages}(\text{Dev}) \cap \text{Passages}(\text{Test}) = \emptyset$$

### Near-Duplicate Text Leakage Detection:
All query texts are compared pairwise across splits using normalized token Jaccard similarity and character-level edit distance. Any pair across splits exceeding:
- Normalized Token Jaccard $\ge 0.75$
- Normalized Levenshtein Similarity $\ge 0.85$
is flagged and rejected by QA Gate 6.
