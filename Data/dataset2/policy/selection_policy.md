# HALO Dataset 2: Selection & Coverage Policy

**Objective**: Ensure the curated judicial corpus achieves optimal legal reasoning diversity, statutory coverage of the Companies Act, 2013, and balanced representation across judicial tiers.

---

## 1. Target Corpus Distribution
The selection process optimizes for quality and coverage rather than rigid numerical quotas:

| Judicial Forum | Target Range | Focus / Jurisdiction |
| :--- | :---: | :--- |
| **Supreme Court of India** | **25 – 35** | Apex constitutional and appellate interpretation of company law doctrines |
| **NCLAT (Appellate Tribunal)** | **8 – 15** | Specialized statutory appellate decisions on corporate insolvency, oppression, and mergers |
| **High Courts (Commercial Benches)** | **8 – 15** | Primary company jurisdiction (e.g. Bombay, Delhi, Madras, Gujarat High Courts) |
| **Total Target** | **40 – 60** | Comprehensive, audited corpus |

---

## 2. Eleven Core Corporate Law Topics & Coverage Targets

To prevent topic clustering, candidate selection enforces minimum coverage targets across 11 substantive corporate law domains:

| Topic Area | Target Count | Key Companies Act (2013) Provisions | Predecessor (1956) Provisions |
| :--- | :---: | :--- | :--- |
| **1. Oppression & Mismanagement** | ~6 | §§ 241, 242, 243, 244, 245 | §§ 397, 398, 399 |
| **2. Related-Party Transactions (RPT)** | ~4 | § 188, § 184, § 189 | § 297, § 299 |
| **3. Director Liability & Disqualification** | ~5 | §§ 164, 166, 167, 149 | §§ 274, 283 |
| **4. Corporate Governance & Board Powers** | ~4 | §§ 173, 177, 178, 179 | §§ 285, 291, 292 |
| **5. Corporate Social Responsibility (CSR)** | ~2 | § 135, Schedule VII | *(New in 2013)* |
| **6. Shareholder Rights & Class Actions** | ~5 | §§ 47, 100, 108, 245 | §§ 87, 169 |
| **7. Incorporation & Corporate Veil** | ~3 | §§ 3, 7, 8, 34, 35 | §§ 12, 33, 34 |
| **8. Mergers, Amalgamations & Arrangements** | ~4 | §§ 230, 231, 232 | §§ 391, 392, 394 |
| **9. Corporate Fraud & Severe Penalties** | ~4 | §§ 447, 448, 212 (SFIO) | §§ 235, 628 |
| **10. Tribunal & Appellate Jurisdiction** | ~5 | §§ 408, 410, 420, 421, 430 | §§ 10E, 10F |
| **11. General Statutory Interpretation** | ~8 | General company law interpretation & statutory continuity | General |

---

## 3. Multi-Factor Scoring Formula

Each candidate judgment receives a composite score $S \in [0.0, 1.0]$:

$$S = \sum (w_i \times s_i) - P_{\text{duplicate}} - P_{\text{risk}}$$

Where the weighted components are:

1. **Companies Act Statutory Relevance ($w = 0.25$)**: Density and centrality of statutory citations and analysis of the Companies Act.
2. **Legal Reasoning Depth ($w = 0.20$)**: Length and substantive structure of judicial ratio (substance vs procedural orders).
3. **Precedential Significance ($w = 0.15$)**: Bench size (Constitution/Division Bench), neutral citations (INSC), and official reporting (SCR, Comp Cas).
4. **Citation Network Value ($w = 0.10$)**: Inter-case precedent citations and statutory cross-references.
5. **Factual & Topic Diversity ($w = 0.10$)**: Bonus awarded for underrepresented topics from the 11-topic rubric.
6. **Statutory Section Coverage ($w = 0.10$)**: Bonus for direct linkage to core Dataset 1 provisions (§135, §188, §241, §242, §447).
7. **Source Authority & Cleanliness ($w = 0.10$)**: Verified official court source (`OFFICIAL` tier) with clean typography.
8. **Penalties**:
   - Near-duplicate or overlapping party penalty ($P_{\text{duplicate}}$).
   - Poor scan / high OCR error risk penalty ($P_{\text{risk}}$).

---

## 4. Human / Policy Selection Gate
Before any PDF is downloaded:
1. All candidates in `candidate_judgments.jsonl` are deduplicated and scored in `selection_scores.jsonl`.
2. Candidates are ranked within their court tier and topic category.
3. Top ~40–60 candidates meeting minimum threshold ($S \ge 0.65$) and satisfying the 11-topic coverage criteria are written to `shortlisted_candidates.jsonl`.
4. Only cases marked `status: "SELECTED"` in the shortlist are approved for physical acquisition.
