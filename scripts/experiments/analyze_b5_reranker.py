"""
HALO Baseline 5 — Cross-Encoder Reranker Diagnostics Engine
===========================================================
Protocol: v1.0-FROZEN
Phase 11: Quantitative & Qualitative Analysis of Reranker Dynamics

Analyzes:
  1. Rank shifts between B4 RRF and B5 Cross-Encoder
  2. Candidate promotion / demotion distribution
  3. Family D3-C Hard-Negative suppression efficacy
  4. Relevant (Gold) passage promotion / demotion
  5. 4-Way Query Transition Classification:
     - FIXES: B4 missed, B5 captured
     - BREAKS: B4 captured, B5 missed
     - BOTH_SUCCEED: Both captured
     - BOTH_FAIL: Both missed
  6. Generates b5_reranker_diagnostics.json and b5_reranker_analysis.md
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B4_TEST_RUN = os.path.join(BASE_DIR, "experiments", "runs", "b4_hybrid", "test_run_output.jsonl")
B5_TEST_RUN = os.path.join(BASE_DIR, "experiments", "runs", "b5_reranker", "test_run_output.jsonl")
CANONICAL_D3 = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")

DIAG_JSON_PATH = os.path.join(BASE_DIR, "experiments", "metrics", "b5_reranker_diagnostics.json")
DIAG_REPORT_PATH = os.path.join(BASE_DIR, "experiments", "metrics", "b5_reranker_analysis.md")


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def analyze_reranker():
    print("=" * 70)
    print("  HALO BASELINE 5: CROSS-ENCODER RERANKER DIAGNOSTICS")
    print("=" * 70)

    b4_records = {r["query_id"]: r for r in load_jsonl(B4_TEST_RUN)}
    b5_records = {r["query_id"]: r for r in load_jsonl(B5_TEST_RUN)}

    if not b5_records:
        print("[!] No B5 TEST records found yet.")
        return

    # Load canonical ground truth
    d3_map = {}
    with open(CANONICAL_D3, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                d3_map[item["record_id"]] = item

    total_queries = len(b5_records)
    retrieval_families = ["D3-A", "D3-B", "D3-C"]

    # Metrics accumulators
    rank_shifts: List[int] = []
    promoted_candidates = 0
    demoted_candidates = 0
    unchanged_candidates = 0

    gold_promotions = 0
    gold_demotions = 0
    gold_unchanged = 0

    hn_demoted_out_of_top5 = 0
    hn_promoted_into_top5 = 0
    hn_remained_in_top5 = 0
    hn_remained_out_of_top5 = 0

    fixes: List[Dict[str, Any]] = []
    breaks: List[Dict[str, Any]] = []
    both_succeed: List[Dict[str, Any]] = []
    both_fail: List[Dict[str, Any]] = []

    d3c_case_studies: List[Dict[str, Any]] = []

    for q_id, b5_rec in b5_records.items():
        fam = b5_rec.get("benchmark_family")
        if fam not in retrieval_families:
            continue

        b4_rec = b4_records.get(q_id, {})
        d3_item = d3_map.get(q_id, {})
        raw_gt = d3_item.get("raw_record", {})
        gold_ids = set(raw_gt.get("relevant_passage_ids") or d3_item.get("primary_source_ids", []))
        hn_ids = set(raw_gt.get("hard_negative_passage_ids", []))

        b4_top5 = set(b4_rec.get("retrieval", {}).get("retrieved_passage_ids", []))
        b5_top5 = set(b5_rec.get("retrieval", {}).get("retrieved_passage_ids", []))

        b4_hit = bool(b4_top5.intersection(gold_ids))
        b5_hit = bool(b5_top5.intersection(gold_ids))

        info = {
            "query_id": q_id,
            "family": fam,
            "query": b5_rec["query"],
            "gold_ids": list(gold_ids),
            "b4_top5": list(b4_top5),
            "b5_top5": list(b5_top5)
        }

        if not b4_hit and b5_hit:
            fixes.append(info)
        elif b4_hit and not b5_hit:
            breaks.append(info)
        elif b4_hit and b5_hit:
            both_succeed.append(info)
        else:
            both_fail.append(info)

        # Inspect candidate rank shifts in B5
        ce_cands = b5_rec.get("retrieval", {}).get("cross_encoder_candidates", [])
        for c in ce_cands:
            p_id = c["passage_id"]
            rrf_rank = c.get("original_rrf_rank", 0)
            ce_rank = c.get("cross_encoder_rank", 0)
            shift = rrf_rank - ce_rank  # positive = promoted, negative = demoted
            rank_shifts.append(shift)

            if shift > 0:
                promoted_candidates += 1
            elif shift < 0:
                demoted_candidates += 1
            else:
                unchanged_candidates += 1

            if p_id in gold_ids:
                if shift > 0:
                    gold_promotions += 1
                elif shift < 0:
                    gold_demotions += 1
                else:
                    gold_unchanged += 1

        # D3-C Hard-Negative inspection
        if fam == "D3-C" and hn_ids:
            b4_hn_in_top5 = bool(b4_top5.intersection(hn_ids))
            b5_hn_in_top5 = bool(b5_top5.intersection(hn_ids))

            if b4_hn_in_top5 and not b5_hn_in_top5:
                hn_demoted_out_of_top5 += 1
            elif not b4_hn_in_top5 and b5_hn_in_top5:
                hn_promoted_into_top5 += 1
            elif b4_hn_in_top5 and b5_hn_in_top5:
                hn_remained_in_top5 += 1
            else:
                hn_remained_out_of_top5 += 1

            d3c_case_studies.append({
                "query_id": q_id,
                "query": b5_rec["query"],
                "gold_ids": list(gold_ids),
                "hard_negative_ids": list(hn_ids),
                "b4_top5": list(b4_top5),
                "b5_top5": list(b5_top5),
                "b4_retrieved_hn": b4_hn_in_top5,
                "b5_retrieved_hn": b5_hn_in_top5,
                "b5_candidates": [
                    {
                        "passage_id": c["passage_id"],
                        "original_rrf_rank": c.get("original_rrf_rank"),
                        "cross_encoder_rank": c.get("cross_encoder_rank"),
                        "cross_encoder_score": c.get("cross_encoder_score"),
                        "is_gold": c["passage_id"] in gold_ids,
                        "is_hn": c["passage_id"] in hn_ids
                    }
                    for c in ce_cands
                ]
            })

    total_ret_queries = len(fixes) + len(breaks) + len(both_succeed) + len(both_fail)
    avg_rank_shift = round(sum(abs(s) for s in rank_shifts) / len(rank_shifts), 3) if rank_shifts else 0.0

    diagnostics = {
        "system_id": "B5_HYBRID_CROSS_ENCODER",
        "benchmark_partition": "TEST Split (Retrieval Families: D3-A, D3-B, D3-C)",
        "total_retrieval_queries": total_ret_queries,
        "reranker_rank_shift_metrics": {
            "total_candidate_pairs_scored": len(rank_shifts),
            "mean_absolute_rank_shift": avg_rank_shift,
            "promoted_candidates": promoted_candidates,
            "demoted_candidates": demoted_candidates,
            "unchanged_candidates": unchanged_candidates
        },
        "target_passage_dynamics": {
            "gold_passages_promoted": gold_promotions,
            "gold_passages_demoted": gold_demotions,
            "gold_passages_unchanged": gold_unchanged
        },
        "d3_c_hard_negative_dynamics": {
            "total_d3c_queries": len(d3c_case_studies),
            "hn_demoted_out_of_top5": hn_demoted_out_of_top5,
            "hn_promoted_into_top5": hn_promoted_into_top5,
            "hn_remained_in_top5": hn_remained_in_top5,
            "hn_remained_out_of_top5": hn_remained_out_of_top5
        },
        "query_level_transitions": {
            "fixes_count": len(fixes),
            "breaks_count": len(breaks),
            "both_succeed_count": len(both_succeed),
            "both_fail_count": len(both_fail),
            "fixes_rate": round(len(fixes) / total_ret_queries, 4) if total_ret_queries else 0.0,
            "breaks_rate": round(len(breaks) / total_ret_queries, 4) if total_ret_queries else 0.0,
            "both_succeed_rate": round(len(both_succeed) / total_ret_queries, 4) if total_ret_queries else 0.0,
            "both_fail_rate": round(len(both_fail) / total_ret_queries, 4) if total_ret_queries else 0.0
        },
        "fixes": fixes,
        "breaks": breaks,
        "d3c_case_studies": d3c_case_studies
    }

    os.makedirs(os.path.dirname(DIAG_JSON_PATH), exist_ok=True)
    with open(DIAG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved diagnostics JSON to: {os.path.relpath(DIAG_JSON_PATH, BASE_DIR)}")

    # Generate Markdown report
    md = [
        "# HALO Baseline 5: Cross-Encoder Reranker Diagnostics Report",
        "## Scientific Analysis of Rank Shifts, Distractor Discrimination & 4-Way Query Transitions",
        "",
        f"**System**: `B5_HYBRID_CROSS_ENCODER`  ",
        f"**Protocol**: `v1.0-FROZEN`  ",
        f"**Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2`  ",
        f"**Evaluation Partition**: Test Retrieval Partition ($N = {total_ret_queries}$ queries: D3-A, D3-B, D3-C)  ",
        "",
        "---",
        "",
        "### 1. Executive Diagnostic Summary",
        "",
        "| Metric Dimension | Value | Jurisprudential & Information Retrieval Meaning |",
        "| :--- | :---: | :--- |",
        f"| **Total Pairs Scored** | {len(rank_shifts)} | Total candidate passage pairs evaluated across retrieval partition |",
        f"| **Mean Absolute Rank Shift** | {avg_rank_shift} positions | Average displacement in rank between RRF fusion and Cross-Encoder |",
        f"| **Promoted Candidates** | {promoted_candidates} ({round(promoted_candidates/max(len(rank_shifts),1)*100, 1)}%) | Candidates whose position improved under Cross-Encoder |",
        f"| **Demoted Candidates** | {demoted_candidates} ({round(demoted_candidates/max(len(rank_shifts),1)*100, 1)}%) | Candidates pushed down by Cross-Encoder cross-attention |",
        f"| **Unchanged Positions** | {unchanged_candidates} ({round(unchanged_candidates/max(len(rank_shifts),1)*100, 1)}%) | Perfect agreement between RRF rank and Cross-Encoder score |",
        "",
        "---",
        "",
        "### 2. 4-Way Query Transition Classification (B4 vs. B5)",
        "",
        "```text",
        f"  Total Retrieval Queries: {total_ret_queries}",
        f"  ├── FIXES (B4 Missed -> B5 Succeeded)        : {len(fixes):2d} ({round(len(fixes)/max(total_ret_queries,1)*100, 1)}%)",
        f"  ├── BREAKS (B4 Succeeded -> B5 Missed)       : {len(breaks):2d} ({round(len(breaks)/max(total_ret_queries,1)*100, 1)}%)",
        f"  ├── DUAL AGREEMENT (Both Succeeded in Top-5) : {len(both_succeed):2d} ({round(len(both_succeed)/max(total_ret_queries,1)*100, 1)}%)",
        f"  └── DUAL MISS (Both Failed to Retrieve Top-5): {len(both_fail):2d} ({round(len(both_fail)/max(total_ret_queries,1)*100, 1)}%)",
        "```",
        "",
        "---",
        "",
        "### 3. Family D3-C Hard-Negative Distractor Discrimination",
        "",
        f"* **Total D3-C Queries**: {len(d3c_case_studies)}",
        f"* **Hard Negatives Demoted out of Top-5 (Success)**: {hn_demoted_out_of_top5}",
        f"* **Hard Negatives Promoted into Top-5 (Adversarial Trap)**: {hn_promoted_into_top5}",
        f"* **Hard Negatives Remaining in Top-5**: {hn_remained_in_top5}",
        f"* **Hard Negatives Remaining outside Top-5**: {hn_remained_out_of_top5}",
        "",
        "---",
        ""
    ]

    with open(DIAG_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[+] Saved diagnostics Markdown to: {os.path.relpath(DIAG_REPORT_PATH, BASE_DIR)}")


if __name__ == "__main__":
    analyze_reranker()
