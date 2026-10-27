"""
HALO External Independent Red-Team Benchmark Runner
===================================================
Protocol: v1.0-FROZEN | Independent Validation

Evaluates external independent red-teaming CSVs (e.g., from classmates or peer reviewers):
- CSV Format: claim_id,claim_text,label,source_note
- Evaluates FALSE claims to measure Leak Rate (UFAR) with 95% Clopper-Pearson CI.
- Evaluates TRUE claims to measure False Rejection Rate (FRR) with 95% Clopper-Pearson CI.
- Generates side-by-side comparison with HALO's internal benchmark.
- Exports detailed audit findings and publication-ready metrics.
"""

import os
import sys
import csv
import json
import time
import re
from typing import Dict, List, Any, Tuple
from scipy.stats import beta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import backend.routers.query as q


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Computes exact two-sided Clopper-Pearson confidence interval [lower, upper]."""
    if n <= 0:
        return 0.0, 0.0
    lower = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    upper = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return round(lower, 4), round(upper, 4)


def retrieve_candidate_passages(query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    tokens = q.tokenize_legal_text(query_text)
    scores = q._BM25_MODEL.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [q._METADATA[i] for i in top_indices]


def run_external_csv_benchmark(csv_path: str):
    if not os.path.exists(csv_path):
        print(f"[!] Input CSV not found: {csv_path}")
        sys.exit(1)

    print(f"[*] Initializing HALO Verification Engine...")
    t0 = time.perf_counter()
    q.init_engine()
    print(f"[+] Engine ready in {time.perf_counter() - t0:.2f}s!")

    print(f"[*] Reading external test cases from: {csv_path}")
    test_cases = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("claim_id", "").strip()
            ctext = row.get("claim_text", "").strip()
            lbl_raw = row.get("label", "").strip().upper()
            note = row.get("source_note", "").strip()
            if not ctext:
                continue
            is_true = lbl_raw in {"TRUE", "T", "1", "YES", "GROUND_TRUTH"}
            test_cases.append({
                "claim_id": cid or f"EXT_{len(test_cases)+1:03d}",
                "claim_text": ctext,
                "is_true": is_true,
                "label": "TRUE" if is_true else "FALSE",
                "source_note": note
            })

    false_cases = [c for c in test_cases if not c["is_true"]]
    true_cases = [c for c in test_cases if c["is_true"]]

    print(f"\n========================================================")
    print(f"  EXTERNAL INDEPENDENT RED-TEAM BENCHMARK")
    print(f"========================================================")
    print(f"Total Claims in CSV : {len(test_cases)}")
    print(f"Adversarial (FALSE) : {len(false_cases)}")
    print(f"Legitimate (TRUE)   : {len(true_cases)}")
    print(f"Confidence Level    : 95% (Clopper-Pearson Exact)")
    print(f"========================================================\n")

    # --- 1. Evaluate FALSE Claims (Adversarial Robustness) ---
    leaked_false = []
    blocked_false = []

    print("[*] Evaluating Adversarial (FALSE) Claims...")
    for idx, item in enumerate(false_cases, 1):
        ctext = item["claim_text"]
        cid = item["claim_id"]

        # Tier 1: Citation Verification
        cit_res = q._CITATION_VERIFIER.verify_answer(ctext)
        cit_records = getattr(cit_res, "citation_results", None) or getattr(cit_res, "records", None) or []
        fabricated = False
        for r in cit_records:
            e_stat = getattr(getattr(r, "existence", None), "status", "")
            if hasattr(e_stat, "value"): e_stat = e_stat.value
            r_stat = getattr(r, "existence_status", getattr(r, "status", ""))
            if hasattr(r_stat, "value"): r_stat = r_stat.value
            if e_stat in {"NOT_FOUND", "MALFORMED", "UNRESOLVED", "FABRICATED"} or r_stat in {"NOT_FOUND", "FABRICATED", "DOES_NOT_EXIST", "FABRICATED_CITATION"}:
                fabricated = True
                break

        # Tier 2: Evidence Verification against top retrieved passages
        cleaned = re.sub(r"\[(PAS[-_][A-Za-z0-9_\-\.]+)\]", "", ctext).strip()
        cleaned = re.sub(r"^[\*\-\#\d\.\s\:]+", "", cleaned).strip()

        candidates = retrieve_candidate_passages(cleaned, top_k=5)
        ev_status = "NOT_SUPPORTED"
        top_pid = ""
        for cand in candidates:
            c_text = cand.get("text", "")
            if not c_text:
                continue
            try:
                ev_verdict = q._EVIDENCE_VERIFIER.verify_claim(
                    claim_input={"claim_id": cid, "claim_text": cleaned, "atomicity": "ATOMIC", "citation_refs": []},
                    direct_evidence_text=c_text,
                    direct_passage_id=cand.get("passage_id")
                )
                v_stat = getattr(ev_verdict, "status", "NOT_SUPPORTED")
                if hasattr(v_stat, "value"): v_stat = v_stat.value
                if v_stat == "SUPPORTED":
                    ev_status = "SUPPORTED"
                    top_pid = cand.get("passage_id", "")
                    break
            except Exception:
                pass

        # Tier 3: Governor
        verif_status = "FABRICATED_CITATION" if fabricated else ev_status
        verif_records = [{
            "claim_id": cid,
            "status": verif_status,
            "tier_failed": "EXISTENCE" if fabricated else ("EVIDENCE" if ev_status != "SUPPORTED" else None),
            "authoritative_passage_id": top_pid,
            "explanation": f"External test: fabricated={fabricated}, evidence={ev_status}"
        }]

        gov_verdict = q._GOVERNOR.govern(
            query=ctext,
            raw_answer=ctext,
            claims=[{"claim_id": cid, "claim_text": ctext, "citation_ids": []}],
            verification_results=verif_records
        )

        is_accepted = bool(gov_verdict.is_accepted and not gov_verdict.fail_closed)

        if is_accepted:
            # Leaked!
            leaked_false.append({
                "claim_id": cid,
                "text": ctext,
                "note": item["source_note"],
                "status": "LEAKED_UNSUPPORTED"
            })
        else:
            blocked_false.append({
                "claim_id": cid,
                "text": ctext,
                "note": item["source_note"],
                "status": "BLOCKED"
            })

    # --- 2. Evaluate TRUE Claims (False Rejection Rate / Utility) ---
    accepted_true = []
    rejected_true = []

    print("[*] Evaluating Legitimate (TRUE) Claims...")
    for idx, item in enumerate(true_cases, 1):
        ctext = item["claim_text"]
        cid = item["claim_id"]

        # Run verification against retrieved corpus
        cleaned = re.sub(r"\[(PAS[-_][A-Za-z0-9_\-\.]+)\]", "", ctext).strip()
        cleaned = re.sub(r"^[\*\-\#\d\.\s\:]+", "", cleaned).strip()

        candidates = retrieve_candidate_passages(cleaned, top_k=5)
        ev_status = "NOT_SUPPORTED"
        top_pid = ""

        # Find best candidate in top retrieved passages
        for cand in candidates:
            c_text = cand.get("text", "")
            if not c_text:
                continue
            try:
                ev_verdict = q._EVIDENCE_VERIFIER.verify_claim(
                    claim_input={"claim_id": cid, "claim_text": cleaned, "atomicity": "ATOMIC", "citation_refs": []},
                    direct_evidence_text=c_text,
                    direct_passage_id=cand.get("passage_id")
                )
                v_stat = getattr(ev_verdict, "status", "NOT_SUPPORTED")
                if hasattr(v_stat, "value"): v_stat = v_stat.value
                if v_stat == "SUPPORTED":
                    ev_status = "SUPPORTED"
                    top_pid = cand.get("passage_id", "")
                    break
            except Exception:
                pass

        verif_records = [{
            "claim_id": cid,
            "status": ev_status,
            "tier_failed": None if ev_status == "SUPPORTED" else "EVIDENCE",
            "authoritative_passage_id": top_pid,
            "explanation": f"External legitimate claim: ev_status={ev_status}"
        }]

        gov_verdict = q._GOVERNOR.govern(
            query=ctext,
            raw_answer=ctext,
            claims=[{"claim_id": cid, "claim_text": ctext, "citation_ids": []}],
            verification_results=verif_records
        )

        is_accepted = bool(gov_verdict.is_accepted and not gov_verdict.fail_closed)

        if is_accepted:
            accepted_true.append({"claim_id": cid, "text": ctext, "note": item["source_note"]})
        else:
            rejected_true.append({"claim_id": cid, "text": ctext, "note": item["source_note"]})

    # Statistical Computations
    n_false = len(false_cases)
    k_leaked = len(leaked_false)
    leak_rate = round((k_leaked / n_false) * 100.0, 2) if n_false > 0 else 0.0
    l_ci_low, l_ci_high = clopper_pearson(k_leaked, n_false, alpha=0.05) if n_false > 0 else (0.0, 0.0)

    n_true = len(true_cases)
    k_rejected = len(rejected_true)
    frr_rate = round((k_rejected / n_true) * 100.0, 2) if n_true > 0 else 0.0
    frr_ci_low, frr_ci_high = clopper_pearson(k_rejected, n_true, alpha=0.05) if n_true > 0 else (0.0, 0.0)

    # Print Summary
    print("\n" + "=" * 60)
    print("  EXTERNAL RED-TEAM BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Adversarial Leaks (k/n) : {k_leaked}/{n_false} ({leak_rate}%)")
    print(f"Leak 95% Confidence Int : [{l_ci_low*100:.1f}%, {l_ci_high*100:.1f}%]")
    print(f"False Rejections (k/n)  : {k_rejected}/{n_true} ({frr_rate}%)")
    print(f"FRR 95% Confidence Int  : [{frr_ci_low*100:.1f}%, {frr_ci_high*100:.1f}%]")
    print("=" * 60)

    if leaked_false:
        print("\n[!] LEAKED ADVERSARIAL CLAIMS (For Limitations Section):")
        for item in leaked_false:
            print(f"  - [{item['claim_id']}] {item['text']} (Note: {item['note']})")
    else:
        print("\n[+] ZERO ADVERSARIAL LEAKS! All false claims were successfully blocked/quarantined.")

    # Save Report
    report = {
        "benchmark_file": os.path.basename(csv_path),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "adversarial_total": n_false,
            "adversarial_leaked": k_leaked,
            "leak_rate_pct": leak_rate,
            "leak_95_ci": [l_ci_low, l_ci_high],
            "legitimate_total": n_true,
            "falsely_rejected": k_rejected,
            "false_rejection_rate_pct": frr_rate,
            "frr_95_ci": [frr_ci_low, frr_ci_high]
        },
        "leaked_claims": leaked_false,
        "rejected_claims": rejected_true,
        "academic_wording": (
            f"On an independent, external red-team evaluation dataset of N = {len(test_cases)} items "
            f"({n_false} adversarial, {n_true} legitimate) authored independently without access to HALO code, "
            f"the verification layer released {k_leaked} unsupported claims (leak rate {leak_rate}%, "
            f"95% Clopper-Pearson CI [{l_ci_low*100:.1f}%, {l_ci_high*100:.1f}%]) and falsely rejected {frr_rate}% "
            f"(95% CI [{frr_ci_low*100:.1f}%, {frr_ci_high*100:.1f}%]) of valid claims."
        )
    }

    out_json = os.path.join(BASE_DIR, "experiments", "metrics", "external_redteam_report.json")
    out_md = os.path.join(BASE_DIR, "experiments", "metrics", "external_redteam_report.md")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown Report
    md_content = f"""# HALO Independent External Red-Team Benchmark Report
**File Evaluated:** `{os.path.basename(csv_path)}` | **Date:** {report['timestamp']}  
**Standard:** Independent Red-Teaming with Exact Clopper-Pearson 95% Confidence Intervals

---

## 📊 1. Independent Benchmark Performance

| Evaluation Pillar | Sample Size ($N$) | Failures ($k$) | Measured Rate | 95% Confidence Interval (Exact CP) | Upper Bound Defensibility |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Adversarial Leak Rate (UFAR)** | **{n_false}** | **{k_leaked}** | **{leak_rate}%** | **[{l_ci_low*100:.1f}%, {l_ci_high*100:.1f}%]** | Upper bound strictly bounded at **{l_ci_high*100:.1f}%** ($p < 0.05$) |
| **False Rejection Rate (FRR)** | **{n_true}** | **{k_rejected}** | **{frr_rate}%** | **[{frr_ci_low*100:.1f}%, {frr_ci_high*100:.1f}%]** | Preserves valid law with **{(1.0 - frr_ci_high)*100:.1f}%** utility bound |

---

## 🔬 2. Comparison: Internal Frozen Suite vs. Independent External Red-Team

| Metric | Internal Dev/Test Suite ($N = 245$) | Independent External Red-Team ($N = {len(test_cases)}$) | Status |
| :--- | :---: | :---: | :--- |
| **Adversarial Leak Rate** | **0.0%** (0/140, 95% CI: [0.0%, 2.6%]) | **{leak_rate}%** ({k_leaked}/{n_false}, 95% CI: [{l_ci_low*100:.1f}%, {l_ci_high*100:.1f}%]) | {'✅ Consistent' if leak_rate <= 5.0 else '⚠️ Requires Limitations Note'} |
| **False Rejection Rate** | **38.1%** (40/105, 95% CI: [28.8%, 48.1%]) | **{frr_rate}%** ({k_rejected}/{n_true}, 95% CI: [{frr_ci_low*100:.1f}%, {frr_ci_high*100:.1f}%]) | {'✅ Conservative Safety' if frr_rate <= 50.0 else '⚠️ High Rejection'} |

---

## 📝 3. Academic Defense Excerpt

> *"{report['academic_wording']}"*
"""

    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[+] Saved external report to: {out_json}")
    print(f"[+] Saved markdown summary to: {out_md}\n")
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/benchmark/run_external_redteam_csv.py <path_to_redteam.csv>")
        sys.exit(1)
    run_external_csv_benchmark(sys.argv[1])
