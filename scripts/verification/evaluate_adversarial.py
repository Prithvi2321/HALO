"""
Adversarial Evaluation Runner
=============================
Protocol: v1.0-FROZEN
Evaluates HALO Verification System across adversarial attack vectors:
- Case-Holding Fabrication (Real case, fake holding)
- Statutory Section Displacement (Real topic, wrong section)
- Statutory Negation / Inversion Attack
- Judicial Ratio Inversion
Computes Adversarial False Acceptance Rate (AFAR). Target: 0.00%.
"""

import json
import os
import sys
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from halo.pipeline import HaloPipeline


def run_adversarial_evaluation() -> Dict[str, Any]:
    dataset_path = os.path.join(BASE_DIR, "halo_datasets", "adversarial", "adversarial_cases.jsonl")
    out_dir = os.path.join(BASE_DIR, "experiments", "runs", "halo")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "adversarial_evaluation_report.json")

    pipeline = HaloPipeline(log_path=os.path.join(out_dir, "adversarial_audit_store.jsonl"))

    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    total = len(records)
    false_acceptances = 0
    quarantined_count = 0
    refused_count = 0
    case_results = []

    print(f"Executing Adversarial Evaluation on {total} canonical attack cases...")
    print("=" * 70)

    for rec in records:
        cid = rec["case_id"]
        query = rec["query"]
        claim = rec["generated_claim"]
        cit = rec["citation"]
        evidence = rec.get("evidence_passage", "")
        pid = rec.get("authoritative_passage_id")

        candidate_passages = [{"passage_id": pid, "text": evidence}] if evidence else []

        # Process through full HALO pipeline
        res = pipeline.process(
            query=query,
            raw_answer=claim,
            candidate_passages=candidate_passages,
            explicit_citations=[cit],
        )

        is_auth = res["is_authoritative"]
        fail_closed = res["fail_closed"]
        rejected = res["quarantine_report"]["rejected_count"]
        verified = res["quarantine_report"]["verified_count"]

        # If any adversarial claim is marked as authoritative verified finding, it's a false acceptance!
        if is_auth and verified > 0:
            false_acceptances += 1
            attack_outcome = "FALSE_ACCEPTANCE (LEAKED)"
        else:
            if fail_closed:
                refused_count += 1
                attack_outcome = "REFUSED (FAIL-CLOSED)"
            else:
                quarantined_count += 1
                attack_outcome = "QUARANTINED & PURGED"

        case_results.append({
            "case_id": cid,
            "query": query,
            "adversarial_claim": claim,
            "attack_outcome": attack_outcome,
            "audit_id": res["audit_id"],
            "rejected_count": rejected,
            "overall_confidence": res["overall_confidence"],
            "quarantine_report": res["quarantine_report"],
        })

        print(f"[{cid}] Outcome: {attack_outcome} | Rejections: {rejected} | Conf: {res['overall_confidence']:.2f}")

    afar = (false_acceptances / total) * 100.0
    print("=" * 70)
    print(f"Total Adversarial Cases Tested: {total}")
    print(f"Attacks Neutralized (Quarantined/Refused): {quarantined_count + refused_count} / {total}")
    print(f"False Acceptances: {false_acceptances}")
    print(f"Adversarial False Acceptance Rate (AFAR): {afar:.2f}%")

    report = {
        "protocol": "v1.0-FROZEN",
        "benchmark": "halo_datasets/adversarial/adversarial_cases.jsonl",
        "total_cases": total,
        "false_acceptances": false_acceptances,
        "quarantined_count": quarantined_count,
        "refused_count": refused_count,
        "adversarial_false_acceptance_rate_pct": afar,
        "passed": afar == 0.0,
        "case_details": case_results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Adversarial Evaluation Report written to: {report_path}")
    return report


if __name__ == "__main__":
    run_adversarial_evaluation()
