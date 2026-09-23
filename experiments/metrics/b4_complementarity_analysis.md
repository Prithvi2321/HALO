# HALO Baseline 4 — Dense vs. BM25 Complementarity Analysis

**Protocol Version**: `v1.0-FROZEN`  
**Generated UTC**: `2026-09-15 20:39:16 UTC`  
**Total Retrieval Queries Analyzed**: `68` (D3-A, D3-B, D3-C)  

---

## 1. Candidate Overlap & Diversity

- **Average Top-5 Jaccard Similarity**: `0.1682`
- **Average Shared Passages in Top-5**: `1.32` out of 5

| Shared Passages in Top-5 | Query Count | Percentage |
| :---: | :---: | :---: |
| 0 passages | 12 | 17.6% |
| 1 passages | 33 | 48.5% |
| 2 passages | 13 | 19.1% |
| 3 passages | 9 | 13.2% |
| 4 passages | 1 | 1.5% |
| 5 passages | 0 | 0.0% |

---

## 2. 4-Quadrant Evidence Complementarity Matrix

| Category | Condition | Query Count | Rate | Scientific Meaning |
| :--- | :--- | :---: | :---: | :--- |
| **Quadrant 1 (Dense Only)** | Dense ✅ / BM25 ❌ | **15** | **22.06%** | Dense captures semantic paraphrasing where lexical tokens fail. |
| **Quadrant 2 (BM25 Only)** | BM25 ✅ / Dense ❌ | **2** | **2.94%** | BM25 captures precise statutory section numbers and legal terms. |
| **Quadrant 3 (Both Agree)** | Dense ✅ / BM25 ✅ | **32** | **47.06%** | High-confidence matches receiving maximal RRF score ($2/61$). |
| **Quadrant 4 (Both Miss)** | Dense ❌ / BM25 ❌ | **19** | **27.94%** | Hard cases requiring multi-hop indexing or legal reasoning. |
| **Theoretical Union** | Either ✅ | **49** | **72.06%** | Maximum ceiling achievable by combining both retrievers. |

---

## 3. Representative Qualitative Case Studies

### Quadrant 1: Dense Retrieval Succeeds, BM25 Misses (Semantic Recovery)

**Case 1 — Query ID**: `D3_RET_000012` (D3-A)  
**Query**: *"What does Section 105 of the Companies Act, 2013 prescribe regarding proxies?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_105_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_105_SUB_5', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_366_SUB_2', 'PAS-JUD-NCLAT-2019-007-P001']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_133', 'PAS-JUD-NCLAT-2017-005-P001', 'PAS_ACT_COMPANIES_2013_SEC_139_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_366_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_4']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_366_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_5', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS-JUD-NCLAT-2017-005-P001', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_1']` (Hit: True)

**Case 2 — Query ID**: `D3_RET_000042` (D3-A)  
**Query**: *"What does Section 122 of the Companies Act, 2013 prescribe regarding applicability of this chapter to one person company?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_122_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_3_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_2_SUB_62', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_446B']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_446B', 'PAS_ACT_COMPANIES_2013_SEC_139_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_127']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_446B', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_3_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_2_SUB_62', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_4']` (Hit: False)

**Case 3 — Query ID**: `D3_RET_000084` (D3-A)  
**Query**: *"What does Section 149 of the Companies Act, 2013 prescribe regarding company to have board of directors?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_149_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_134_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_179_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_150_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_173_SUB_1']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_150_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_134_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_135_SUB_1']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_134_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_150_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_179_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_4']` (Hit: False)

### Quadrant 2: BM25 Succeeds, Dense Retrieval Misses (Exact Lexical Precision)

**Case 1 — Query ID**: `D3_RET_000202` (D3-A)  
**Query**: *"What was held by the Supreme Court Of India in S.E.B.I. v. ALLIANCE FINSTOCK LTD. & ORS. ETC. ETC. regarding general statutory interpretation?"*  
**Gold Target Passages**: `['PAS-JUD-SC-2015-2015_10_145_162-P001', 'PAS-JUD-SC-2015-2015_10_145_162-P002']`  
**Dense Top-5**: `['PAS-JUD-SC-2015-2015_10_145_162-P015', 'PAS-JUD-SC-2015-2015_10_145_162-P005', 'PAS-JUD-SC-2015-2015_10_145_162-P011', 'PAS-JUD-SC-2015-2015_10_145_162-P013', 'PAS-JUD-SC-2015-2015_10_145_162-P003']` (Hit: False)  
**BM25 Top-5**: `['PAS-JUD-SC-2015-2015_10_145_162-P001', 'PAS-JUD-SC-2016-2016_11_419_475-P006', 'PAS-JUD-SC-2015-2015_10_145_162-P015', 'PAS-JUD-SC-2015-2015_10_145_162-P009', 'PAS-JUD-SC-2020-2020_10_1132_1150-P014']` (Hit: True)  
**Fused Top-5 (RRF)**: `['PAS-JUD-SC-2015-2015_10_145_162-P015', 'PAS-JUD-SC-2015-2015_10_145_162-P001', 'PAS-JUD-SC-2015-2015_10_145_162-P005', 'PAS-JUD-SC-2016-2016_11_419_475-P006', 'PAS-JUD-SC-2015-2015_10_145_162-P011']` (Hit: True)

**Case 2 — Query ID**: `D3_RET_000327` (D3-B)  
**Query**: *"Under Indian company law jurisprudence, what are the overarching statutory mandates and compliance mechanisms regarding declaration of dividend?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_123_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_24_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_127', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_6', 'PAS-JUD-SC-2022-2022_10_102_126-P016', 'PAS-JUD-SC-2022-2022_10_102_126-P019']` (Hit: False)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_127', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_1', 'PAS-JUD-NCLAT-2019-011-P001']` (Hit: True)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_127', 'PAS_ACT_COMPANIES_2013_SEC_24_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_6']` (Hit: False)

### Quadrant 3: Both Retrievers Agree (Dual-Channel Consensus)

**Case 1 — Query ID**: `D3_RET_000030` (D3-A)  
**Query**: *"What does Section 116 of the Companies Act, 2013 prescribe regarding resolutions passed at adjourned meeting?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_116']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_175_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_115']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_117_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_118_SUB_8', 'PAS_ACT_COMPANIES_2013_SEC_152_SUB_7']` (Hit: True)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_117_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_4']` (Hit: True)

**Case 2 — Query ID**: `D3_RET_000031` (D3-A)  
**Query**: *"Under the Companies Act, 2013, what are the statutory obligations and legal requirements concerning resolutions passed at adjourned meeting?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_116']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS_ACT_COMPANIES_2013_SEC_117_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_103_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_175_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_122_SUB_3']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS-JUD-NCLAT-2020-012-P001', 'PAS-JUD-NCLAT-2019-011-P001', 'PAS-JUD-NCLAT-2017-005-P001', 'PAS-JUD-NCLAT-2018-006-P001']` (Hit: True)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_116', 'PAS-JUD-NCLAT-2020-012-P001', 'PAS_ACT_COMPANIES_2013_SEC_117_SUB_1', 'PAS-JUD-NCLAT-2019-011-P001', 'PAS_ACT_COMPANIES_2013_SEC_103_SUB_2']` (Hit: True)

**Case 3 — Query ID**: `D3_RET_000043` (D3-A)  
**Query**: *"What does Section 123 of the Companies Act, 2013 prescribe regarding declaration of dividend?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_123_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_123_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_6', 'PAS_ACT_COMPANIES_2013_SEC_24_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_26_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_127']` (Hit: True)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_127', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_126', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_123_SUB_1']` (Hit: True)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_123_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_127', 'PAS_ACT_COMPANIES_2013_SEC_124_SUB_6', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_126']` (Hit: True)

### Quadrant 4: Both Retrievers Miss (Out-of-Vocabulary / Multi-Hop Complexity)

**Case 1 — Query ID**: `D3_RET_000013` (D3-A)  
**Query**: *"What does Section 106 of the Companies Act, 2013 prescribe regarding restriction on voting rights?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_106_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_106_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_105_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_378D', 'PAS_ACT_COMPANIES_2013_SEC_90_SUB_8', 'PAS-JUD-NCLAT-2019-004-P001', 'PAS_ACT_COMPANIES_2013_SEC_47_SUB_2']` (Hit: False)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_108', 'PAS_ACT_COMPANIES_2013_SEC_59_SUB_3', 'PAS_ACT_COMPANIES_2013_SEC_378D', 'PAS_ACT_COMPANIES_2013_SEC_50_SUB_2']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_378D', 'PAS_ACT_COMPANIES_2013_SEC_105_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_133', 'PAS_ACT_COMPANIES_2013_SEC_108', 'PAS_ACT_COMPANIES_2013_SEC_59_SUB_3']` (Hit: False)

**Case 2 — Query ID**: `D3_RET_000068` (D3-A)  
**Query**: *"Under the Companies Act, 2013, what are the statutory obligations and legal requirements concerning removal, resignation of auditor and giving of special notice?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_140_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_140_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_115', 'PAS_ACT_COMPANIES_2013_SEC_248_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_140_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_139_SUB_2']` (Hit: False)  
**BM25 Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_168_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_140_SUB_2', 'PAS-JUD-SC-2016-2016_11_419_475-P005', 'PAS-JUD-SC-2016-2016_11_419_475-P047', 'PAS-JUD-NCLAT-2020-012-P001']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS_ACT_COMPANIES_2013_SEC_140_SUB_2', 'PAS_ACT_COMPANIES_2013_SEC_140_SUB_4', 'PAS_ACT_COMPANIES_2013_SEC_168_SUB_1', 'PAS_ACT_COMPANIES_2013_SEC_115', 'PAS-JUD-SC-2016-2016_11_419_475-P005']` (Hit: False)

**Case 3 — Query ID**: `D3_RET_000085` (D3-A)  
**Query**: *"Under the Companies Act, 2013, what are the statutory obligations and legal requirements concerning company to have board of directors?"*  
**Gold Target Passages**: `['PAS_ACT_COMPANIES_2013_SEC_149_SUB_1']`  
**Dense Top-5**: `['PAS_ACT_COMPANIES_2013_SEC_149_SUB_2', 'PAS-JUD-SC-2022-2022_10_102_126-P024', 'PAS_ACT_COMPANIES_2013_SEC_179_SUB_1', 'PAS-JUD-SC-2022-2022_10_102_126-P003', 'PAS_ACT_COMPANIES_2013_SEC_286']` (Hit: False)  
**BM25 Top-5**: `['PAS-JUD-NCLAT-2020-012-P001', 'PAS-JUD-NCLAT-2019-011-P001', 'PAS-JUD-NCLAT-2017-005-P001', 'PAS-JUD-NCLAT-2018-006-P001', 'PAS-JUD-NCLAT-2019-004-P001']` (Hit: False)  
**Fused Top-5 (RRF)**: `['PAS-JUD-NCLAT-2020-012-P001', 'PAS_ACT_COMPANIES_2013_SEC_149_SUB_2', 'PAS-JUD-NCLAT-2019-011-P001', 'PAS-JUD-SC-2022-2022_10_102_126-P024', 'PAS-JUD-NCLAT-2017-005-P001']` (Hit: False)
