# HALO Baseline 5: Cross-Encoder Reranker Diagnostics Report
## Scientific Analysis of Rank Shifts, Distractor Discrimination & 4-Way Query Transitions

**System**: `B5_HYBRID_CROSS_ENCODER`  
**Protocol**: `v1.0-FROZEN`  
**Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2`  
**Evaluation Partition**: Test Retrieval Partition ($N = 68$ queries: D3-A, D3-B, D3-C)  

---

### 1. Executive Diagnostic Summary

| Metric Dimension | Value | Jurisprudential & Information Retrieval Meaning |
| :--- | :---: | :--- |
| **Total Pairs Scored** | 590 | Total candidate passage pairs evaluated across retrieval partition |
| **Mean Absolute Rank Shift** | 2.071 positions | Average displacement in rank between RRF fusion and Cross-Encoder |
| **Promoted Candidates** | 225 (38.1%) | Candidates whose position improved under Cross-Encoder |
| **Demoted Candidates** | 232 (39.3%) | Candidates pushed down by Cross-Encoder cross-attention |
| **Unchanged Positions** | 133 (22.5%) | Perfect agreement between RRF rank and Cross-Encoder score |

---

### 2. 4-Way Query Transition Classification (B4 vs. B5)

```text
  Total Retrieval Queries: 68
  ├── FIXES (B4 Missed -> B5 Succeeded)        :  2 (2.9%)
  ├── BREAKS (B4 Succeeded -> B5 Missed)       :  1 (1.5%)
  ├── DUAL AGREEMENT (Both Succeeded in Top-5) : 45 (66.2%)
  └── DUAL MISS (Both Failed to Retrieve Top-5): 20 (29.4%)
```

---

### 3. Family D3-C Hard-Negative Distractor Discrimination

* **Total D3-C Queries**: 12
* **Hard Negatives Demoted out of Top-5 (Success)**: 0
* **Hard Negatives Promoted into Top-5 (Adversarial Trap)**: 2
* **Hard Negatives Remaining in Top-5**: 6
* **Hard Negatives Remaining outside Top-5**: 4

---
