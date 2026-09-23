# HALO Baseline 5 Evaluation Report: Hybrid RAG + Cross-Encoder Reranking
## 5-Way Controlled Comparative Ablation Across Baselines 1, 2, 3, 4, and 5

**System ID**: `B5_HYBRID_CROSS_ENCODER`  
**Protocol Version**: `v1.0-FROZEN`  
**Evaluated Split**: TEST Split ($N = 168$ queries) + DEV Split ($N = 64$ queries) = 232 Queries  
**Reranker Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`  
**Evaluation Timestamp**: 2026-09-16T16:43:55.372352+00:00  

---

### Master 5-Way Comparative Ablation Table

| Benchmark Pillar / Metric | Baseline 1 (LLM-Only) | Baseline 2 (Dense RAG) | Baseline 3 (Sparse BM25) | Baseline 4 (Hybrid RRF) | Baseline 5 (CE Rerank) | Delta (B5 vs B4) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **D3-A Recall@5** | N/A | 61.54% | 48.72% | 58.97% | **62.82%** | +3.85% |
| **D3-A HitRate@5** | 64.10% | 79.49% | 61.54% | 76.92% | **79.49%** | +2.57% |
| **D3-B Recall@5 (Concepts)** | N/A | 41.18% | 29.41% | 41.18% | **41.18%** | +0.00% |
| **D3-C Positive Hit@5** | 41.67% | 75.00% | 0.00% | 75.00% | **75.00%** | +0.00% |
| **D3-C HNFAR (Distractor Trap)** | N/A | 8.33% | 41.67% | 50.00% | **8.33%** | -41.67% |
| **D3-D AFPR (Fact Recall)** | 57.67% | 56.17% | 60.17% | 60.42% | **63.00%** | +2.58% |
| **D3-D Complete Answer Rate** | 20.00% | 23.00% | 22.00% | 22.00% | **26.00%** | +4.00% |
| **D3-D Hallucination Rate** | 7.00% | 12.00% | 16.00% | 15.00% | **17.00%** | +2.00% |

---

### Latency Profiles Breakdown (Baseline 5)

| Component | Mean Latency (ms) | Median (ms) | P95 (ms) | P99 (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **Dense Retrieval (BGE-Large)** | 346.19 | 236.44 | 838.84 | 931.21 |
| **Sparse Retrieval (BM25Okapi)** | 13.95 | 10.1 | 28.29 | 32.62 |
| **RRF Fusion ($k=60$)** | 0.04 | 0.03 | 0.06 | 0.07 |
| **Cross-Encoder Reranking** | 693.67 | 408.9 | 1637.51 | 1774.65 |
| **Total Retrieval Pipeline** | 1053.85 | 641.49 | 2418.18 | 2661.75 |
| **LLM Generation (Qwen-27B)** | 5221.06 | 3466.96 | 10257.64 | 40568.42 |
| **End-to-End System** | 6274.91 | 4533.82 | 11570.9 | 41117.92 |

---
