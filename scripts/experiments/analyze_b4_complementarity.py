"""
HALO Baseline 4 — Complementarity Diagnostic Engine
==================================================
Protocol: v1.0-FROZEN
Phase 5: Dense vs. BM25 Complementarity Analysis

Performs deep scientific inspection into why Hybrid RRF outperforms individual retrievers:
  1. Retrieval Overlap: Jaccard similarity and Top-5 intersection distribution between Dense and BM25.
  2. Evidence Complementarity:
     - Dense-only recovery: Gold passages retrieved in Dense Top-5 but missed by BM25 Top-5.
     - BM25-only recovery: Gold passages retrieved in BM25 Top-5 but missed by Dense Top-5.
     - Dual recovery: Gold passages retrieved in both.
     - Union recovery: Overall reach of hybrid search vs. single retrievers.
  3. 4-Quadrant Representative Case Studies:
     - Quadrant 1: Dense succeeds, BM25 fails.
     - Quadrant 2: BM25 succeeds, Dense fails.
     - Quadrant 3: Both succeed.
     - Quadrant 4: Both fail.
  4. Emits:
     - experiments/metrics/b4_complementarity.json
     - experiments/metrics/b4_complementarity_analysis.md
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_RUN_PATH = os.path.join(BASE_DIR, "experiments", "runs", "b4_hybrid", "test_run_output.jsonl")
D3_CANONICAL_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")
METRICS_DIR = os.path.join(BASE_DIR, "experiments", "metrics")
COMPL_JSON_PATH = os.path.join(METRICS_DIR, "b4_complementarity.json")
COMPL_MD_PATH = os.path.join(METRICS_DIR, "b4_complementarity_analysis.md")


def analyze_complementarity():
    print("[*] Loading ground truth and Baseline 4 TEST run traces...")
    ground_truth = {}
    with open(D3_CANONICAL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                ground_truth[item["record_id"]] = item

    if not os.path.exists(TEST_RUN_PATH):
        raise FileNotFoundError(f"Test run output missing: {TEST_RUN_PATH}")

    test_records = []
    with open(TEST_RUN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_records.append(json.loads(line))

    # We examine retrieval queries (D3-A, D3-B, D3-C) where gold passage IDs are defined
    retrieval_families = ["D3-A", "D3-B", "D3-C"]
    ret_records = [r for r in test_records if r.get("benchmark_family") in retrieval_families]

    jaccards = []
    overlap_counts = []

    dense_only_hits = 0
    bm25_only_hits = 0
    both_hits = 0
    neither_hits = 0
    total_queries_evaluated = 0

    quadrant_cases = {
        "dense_only": [],
        "bm25_only": [],
        "both_succeed": [],
        "both_fail": []
    }

    for r in ret_records:
        qid = r["query_id"]
        gt = ground_truth.get(qid, {})
        raw = gt.get("raw_record", {})
        gold_passages = set(raw.get("relevant_passage_ids") or raw.get("positive_evidence_ids") or [])

        if not gold_passages:
            continue

        total_queries_evaluated += 1

        dense_cands = [c["passage_id"] for c in r["retrieval"].get("dense_candidates", [])][:5]
        bm25_cands = [c["passage_id"] for c in r["retrieval"].get("bm25_candidates", [])][:5]
        fused_top5 = r["retrieval"].get("retrieved_passage_ids", [])[:5]

        s_dense = set(dense_cands)
        s_bm25 = set(bm25_cands)

        inter = s_dense & s_bm25
        union = s_dense | s_bm25
        jaccard = len(inter) / len(union) if union else 0.0
        jaccards.append(jaccard)
        overlap_counts.append(len(inter))

        dense_hit = bool(s_dense & gold_passages)
        bm25_hit = bool(s_bm25 & gold_passages)
        fused_hit = bool(set(fused_top5) & gold_passages)

        case_summary = {
            "query_id": qid,
            "benchmark_family": r["benchmark_family"],
            "query": r["query"],
            "gold_passages": list(gold_passages),
            "dense_top5": dense_cands,
            "bm25_top5": bm25_cands,
            "fused_top5": fused_top5,
            "dense_hit": dense_hit,
            "bm25_hit": bm25_hit,
            "fused_hit": fused_hit
        }

        if dense_hit and not bm25_hit:
            dense_only_hits += 1
            if len(quadrant_cases["dense_only"]) < 3:
                quadrant_cases["dense_only"].append(case_summary)
        elif bm25_hit and not dense_hit:
            bm25_only_hits += 1
            if len(quadrant_cases["bm25_only"]) < 3:
                quadrant_cases["bm25_only"].append(case_summary)
        elif dense_hit and bm25_hit:
            both_hits += 1
            if len(quadrant_cases["both_succeed"]) < 3:
                quadrant_cases["both_succeed"].append(case_summary)
        else:
            neither_hits += 1
            if len(quadrant_cases["both_fail"]) < 3:
                quadrant_cases["both_fail"].append(case_summary)

    avg_jaccard = sum(jaccards) / len(jaccards) if jaccards else 0.0
    avg_overlap = sum(overlap_counts) / len(overlap_counts) if overlap_counts else 0.0

    union_hits = dense_only_hits + bm25_only_hits + both_hits
    union_hit_rate = union_hits / total_queries_evaluated if total_queries_evaluated else 0.0

    compl_data = {
        "analysis_type": "Dense_vs_BM25_Complementarity",
        "total_queries_evaluated": total_queries_evaluated,
        "retrieval_families": retrieval_families,
        "overlap_metrics": {
            "average_jaccard_similarity": round(avg_jaccard, 4),
            "average_candidate_overlap_count_top5": round(avg_overlap, 2),
            "overlap_distribution": {
                f"{k}_passages": overlap_counts.count(k) for k in range(6)
            }
        },
        "complementarity_breakdown": {
            "dense_only_success_count": dense_only_hits,
            "dense_only_success_rate": round(dense_only_hits / total_queries_evaluated, 4),
            "bm25_only_success_count": bm25_only_hits,
            "bm25_only_success_rate": round(bm25_only_hits / total_queries_evaluated, 4),
            "both_success_count": both_hits,
            "both_success_rate": round(both_hits / total_queries_evaluated, 4),
            "neither_success_count": neither_hits,
            "neither_success_rate": round(neither_hits / total_queries_evaluated, 4),
            "theoretical_union_hit_rate": round(union_hit_rate, 4)
        },
        "representative_case_studies": quadrant_cases,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

    os.makedirs(METRICS_DIR, exist_ok=True)
    with open(COMPL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(compl_data, f, indent=2)

    # Generate Markdown Report
    lines = [
        "# HALO Baseline 4 — Dense vs. BM25 Complementarity Analysis",
        "",
        "**Protocol Version**: `v1.0-FROZEN`  ",
        f"**Generated UTC**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
        f"**Total Retrieval Queries Analyzed**: `{total_queries_evaluated}` (D3-A, D3-B, D3-C)  ",
        "",
        "---",
        "",
        "## 1. Candidate Overlap & Diversity",
        "",
        f"- **Average Top-5 Jaccard Similarity**: `{round(avg_jaccard, 4)}`",
        f"- **Average Shared Passages in Top-5**: `{round(avg_overlap, 2)}` out of 5",
        "",
        "| Shared Passages in Top-5 | Query Count | Percentage |",
        "| :---: | :---: | :---: |"
    ]
    for k in range(6):
        cnt = overlap_counts.count(k)
        pct = (cnt / total_queries_evaluated) * 100.0 if total_queries_evaluated else 0.0
        lines.append(f"| {k} passages | {cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 4-Quadrant Evidence Complementarity Matrix",
        "",
        "| Category | Condition | Query Count | Rate | Scientific Meaning |",
        "| :--- | :--- | :---: | :---: | :--- |",
        f"| **Quadrant 1 (Dense Only)** | Dense ✅ / BM25 ❌ | **{dense_only_hits}** | **{round(dense_only_hits/total_queries_evaluated*100, 2)}%** | Dense captures semantic paraphrasing where lexical tokens fail. |",
        f"| **Quadrant 2 (BM25 Only)** | BM25 ✅ / Dense ❌ | **{bm25_only_hits}** | **{round(bm25_only_hits/total_queries_evaluated*100, 2)}%** | BM25 captures precise statutory section numbers and legal terms. |",
        f"| **Quadrant 3 (Both Agree)** | Dense ✅ / BM25 ✅ | **{both_hits}** | **{round(both_hits/total_queries_evaluated*100, 2)}%** | High-confidence matches receiving maximal RRF score ($2/61$). |",
        f"| **Quadrant 4 (Both Miss)** | Dense ❌ / BM25 ❌ | **{neither_hits}** | **{round(neither_hits/total_queries_evaluated*100, 2)}%** | Hard cases requiring multi-hop indexing or legal reasoning. |",
        f"| **Theoretical Union** | Either ✅ | **{union_hits}** | **{round(union_hit_rate*100, 2)}%** | Maximum ceiling achievable by combining both retrievers. |",
        "",
        "---",
        "",
        "## 3. Representative Qualitative Case Studies",
        ""
    ])

    for q_name, title in [
        ("dense_only", "Quadrant 1: Dense Retrieval Succeeds, BM25 Misses (Semantic Recovery)"),
        ("bm25_only", "Quadrant 2: BM25 Succeeds, Dense Retrieval Misses (Exact Lexical Precision)"),
        ("both_succeed", "Quadrant 3: Both Retrievers Agree (Dual-Channel Consensus)"),
        ("both_fail", "Quadrant 4: Both Retrievers Miss (Out-of-Vocabulary / Multi-Hop Complexity)")
    ]:
        lines.append(f"### {title}\n")
        cases = quadrant_cases[q_name]
        if not cases:
            lines.append("*(No cases encountered in this sample)*\n")
        else:
            for idx, c in enumerate(cases, 1):
                lines.append(f"**Case {idx} — Query ID**: `{c['query_id']}` ({c['benchmark_family']})  ")
                lines.append(f"**Query**: *\"{c['query']}\"*  ")
                lines.append(f"**Gold Target Passages**: `{c['gold_passages']}`  ")
                lines.append(f"**Dense Top-5**: `{c['dense_top5']}` (Hit: {c['dense_hit']})  ")
                lines.append(f"**BM25 Top-5**: `{c['bm25_top5']}` (Hit: {c['bm25_hit']})  ")
                lines.append(f"**Fused Top-5 (RRF)**: `{c['fused_top5']}` (Hit: {c['fused_hit']})\n")

    with open(COMPL_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[+] Complementarity analysis complete:")
    print(f"    - JSON: {COMPL_JSON_PATH}")
    print(f"    - Report: {COMPL_MD_PATH}")


if __name__ == "__main__":
    analyze_complementarity()
