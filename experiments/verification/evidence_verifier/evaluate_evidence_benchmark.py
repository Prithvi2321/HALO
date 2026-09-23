"""
HALO Evidence Verifier: Benchmark Evaluation & Threshold Calibration Harness
============================================================================
Protocol: v1.0-FROZEN
Evaluates semantic evidence verification across Train and Dev benchmark splits.
Strictly quarantines the 28 Test cases (EV14).
Implements:
1. Safety-objective based threshold calibration on Dev split only (User Correction #9 & #10)
2. Per-category metric breakdown (User Correction #17)
3. Complete 6x6 confusion matrix (User Correction #18)
4. Safety metrics: UFAR, SFRR, UR, Contradiction Recall
5. Latency profiling (mean, P50, P95, P99) and throughput
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import hashlib
import json
import os
import sys
import time

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from halo.evidence_verifier.verifier import EvidenceVerifier
from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.schemas import (
    EvidenceVerdictStatus,
    ClaimAtomicity,
)
from halo.evidence_verifier.exceptions import TruthLabelLeakageError


ALL_STATUSES = [
    EvidenceVerdictStatus.SUPPORTED.value,
    EvidenceVerdictStatus.CONTRADICTED.value,
    EvidenceVerdictStatus.PARTIALLY_SUPPORTED.value,
    EvidenceVerdictStatus.NEUTRAL.value,
    EvidenceVerdictStatus.CONFLICTED.value,
    EvidenceVerdictStatus.UNRESOLVED.value,
]


def compute_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_split(split_path: Path, split_name: str, allow_quarantined_test: bool = False) -> List[Dict[str, Any]]:
    """Loads benchmark split records, enforcing test split quarantine."""
    if "test" in split_name.lower() and not allow_quarantined_test:
        raise PermissionError(
            "GATE EV14 VIOLATION: Test split is strictly quarantined! "
            "Cannot access test.jsonl during development or threshold calibration."
        )
    records = []
    with open(split_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def evaluate_split(
    verifier: EvidenceVerifier,
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Runs evidence verifier on benchmark split records and computes comprehensive metrics."""
    latencies: List[float] = []
    predictions: List[str] = []
    ground_truths: List[str] = []
    categories: List[str] = []

    # 6x6 Confusion Matrix initialization
    matrix = {true_s: {pred_s: 0 for pred_s in ALL_STATUSES} for true_s in ALL_STATUSES}

    for rec in records:
        cid = rec.get("id") or rec.get("case_id")
        claim = rec.get("generated_claim") or rec.get("claim_text") or ""
        evidence = rec.get("evidence_passage") or ""
        pid = rec.get("authoritative_passage_id")
        gold_status = rec.get("expected_status", "UNRESOLVED")
        case_type = rec.get("case_type", "unknown")

        # Map non-evidence tiers to closest expected semantic verdict
        # e.g., FABRICATED_CITATION without evidence is UNRESOLVED
        if gold_status in ("FABRICATED_CITATION", "UNSUPPORTED"):
            mapped_gold = EvidenceVerdictStatus.UNRESOLVED.value if not evidence.strip() else EvidenceVerdictStatus.NEUTRAL.value
        elif gold_status in ALL_STATUSES:
            mapped_gold = gold_status
        else:
            mapped_gold = EvidenceVerdictStatus.UNRESOLVED.value

        t0 = time.perf_counter()
        # Verify using isolated inputs (no ground truth passed to verifier)
        res = verifier.verify(
            claim=claim,
            evidence_passage=evidence if evidence.strip() else None,
            case_id=cid,
            authoritative_passage_id=pid if pid != "NONE" else None,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

        pred_status = res.status
        predictions.append(pred_status)
        ground_truths.append(mapped_gold)
        categories.append(case_type)

        if mapped_gold in matrix and pred_status in matrix[mapped_gold]:
            matrix[mapped_gold][pred_status] += 1

    # Compute classification metrics
    total = len(records)
    correct = sum(1 for p, g in zip(predictions, ground_truths) if p == g)
    accuracy = round(correct / max(total, 1), 4)

    # Per-class precision, recall, F1
    per_class = {}
    macro_p_sum, macro_r_sum, macro_f1_sum = 0.0, 0.0, 0.0
    active_classes = 0

    for s in ALL_STATUSES:
        tp = matrix[s][s]
        fp = sum(matrix[other][s] for other in ALL_STATUSES if other != s)
        fn = sum(matrix[s][other] for other in ALL_STATUSES if other != s)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        support_count = tp + fn
        per_class[s] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support_count,
        }

        if support_count > 0:
            macro_p_sum += prec
            macro_r_sum += rec
            macro_f1_sum += f1
            active_classes += 1

    macro_p = round(macro_p_sum / max(active_classes, 1), 4)
    macro_r = round(macro_r_sum / max(active_classes, 1), 4)
    macro_f1 = round(macro_f1_sum / max(active_classes, 1), 4)

    # Safety Metrics
    # 1. UFAR: Unsupported False Acceptance Rate
    unsupported_indices = [i for i, g in enumerate(ground_truths) if g != EvidenceVerdictStatus.SUPPORTED.value]
    unsupported_total = len(unsupported_indices)
    unsupported_accepted = sum(1 for i in unsupported_indices if predictions[i] == EvidenceVerdictStatus.SUPPORTED.value)
    ufar = round(unsupported_accepted / max(unsupported_total, 1), 4)

    # 2. SFRR: Supported False Rejection Rate
    supported_indices = [i for i, g in enumerate(ground_truths) if g == EvidenceVerdictStatus.SUPPORTED.value]
    supported_total = len(supported_indices)
    supported_rejected = sum(1 for i in supported_indices if predictions[i] != EvidenceVerdictStatus.SUPPORTED.value)
    sfrr = round(supported_rejected / max(supported_total, 1), 4)

    # 3. UR: Unresolved Rate
    unresolved_count = sum(1 for p in predictions if p == EvidenceVerdictStatus.UNRESOLVED.value)
    ur = round(unresolved_count / max(total, 1), 4)

    # 4. Contradiction False Negative Rate
    contra_indices = [i for i, g in enumerate(ground_truths) if g == EvidenceVerdictStatus.CONTRADICTED.value]
    contra_total = len(contra_indices)
    contra_missed = sum(1 for i in contra_indices if predictions[i] != EvidenceVerdictStatus.CONTRADICTED.value)
    cfnr = round(contra_missed / max(contra_total, 1), 4)

    # User Correction #17: Per-category performance breakdown
    cat_metrics = {}
    unique_cats = sorted(list(set(categories)))
    for cat in unique_cats:
        cat_indices = [i for i, c in enumerate(categories) if c == cat]
        cat_total = len(cat_indices)
        cat_correct = sum(1 for i in cat_indices if predictions[i] == ground_truths[i])
        cat_acc = round(cat_correct / max(cat_total, 1), 4)

        # Mutation detection rate if mutation category
        detection_rate = cat_acc
        cat_metrics[cat] = {
            "total": cat_total,
            "correct": cat_correct,
            "accuracy": cat_acc,
            "detection_rate": detection_rate,
        }

    # Latency percentiles
    sorted_lat = sorted(latencies)
    p50 = round(sorted_lat[int(len(sorted_lat) * 0.50)], 2) if sorted_lat else 0.0
    p95 = round(sorted_lat[int(len(sorted_lat) * 0.95)], 2) if sorted_lat else 0.0
    p99 = round(sorted_lat[int(len(sorted_lat) * 0.99)], 2) if sorted_lat else 0.0
    mean_lat = round(sum(latencies) / max(len(latencies), 1), 2)
    total_time_sec = sum(latencies) / 1000.0
    throughput = round(total / max(total_time_sec, 0.001), 2)

    return {
        "total_cases": total,
        "accuracy": accuracy,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "safety_metrics": {
            "UFAR": ufar,
            "SFRR": sfrr,
            "UR": ur,
            "CFNR": cfnr,
        },
        "per_class": per_class,
        "per_category": cat_metrics,
        "confusion_matrix_6x6": matrix,
        "latency_ms": {
            "mean": mean_lat,
            "p50": p50,
            "p95": p95,
            "p99": p99,
        },
        "throughput_cases_per_sec": throughput,
    }


def calibrate_on_dev(dev_records: List[Dict[str, Any]], dev_path: Path) -> Dict[str, Any]:
    """
    User Correction #9 & #10:
    Safety-objective threshold calibration strictly on Dev split.
    Objective: Minimize UFAR (unsupported false acceptance) subject to SFRR <= 0.15,
               tie-breaking on Macro-F1.
    """
    print("[*] Running Dev-only threshold calibration grid search...")
    base_verifier = EvidenceVerifier()

    # 1. Precompute NLI scores and flags on Dev records (1 pass over Dev)
    print(f"[*] Precomputing inference over {len(dev_records)} Dev records...")
    cached_dev = []
    for rec in dev_records:
        cid = rec.get("id") or rec.get("case_id")
        claim = rec.get("generated_claim") or rec.get("claim_text") or ""
        evidence = rec.get("evidence_passage") or ""
        pid = rec.get("authoritative_passage_id")
        gold_status = rec.get("expected_status", "UNRESOLVED")
        case_type = rec.get("case_type", "unknown")

        if gold_status in ("FABRICATED_CITATION", "UNSUPPORTED"):
            mapped_gold = EvidenceVerdictStatus.UNRESOLVED.value if not evidence.strip() else EvidenceVerdictStatus.NEUTRAL.value
        elif gold_status in ALL_STATUSES:
            mapped_gold = gold_status
        else:
            mapped_gold = EvidenceVerdictStatus.UNRESOLVED.value

        t0 = time.perf_counter()
        res = base_verifier.verify(
            claim=claim,
            evidence_passage=evidence if evidence.strip() else None,
            case_id=cid,
            authoritative_passage_id=pid if pid != "NONE" else None,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        cached_dev.append({
            "cid": cid,
            "claim": claim,
            "evidence": evidence,
            "pid": pid,
            "gold_status": mapped_gold,
            "case_type": case_type,
            "elapsed_ms": elapsed_ms,
            "base_status": res.status,
            "entailment_score": res.entailment_score,
            "contradiction_score": res.contradiction_score,
            "neutral_score": res.neutral_score,
            "flags": getattr(res, "flags", []),
        })

    grid_entailment = [0.70, 0.75, 0.80]
    grid_contradiction = [0.65, 0.70, 0.75]
    grid_contra_max_for_ent = [0.10, 0.15, 0.20]
    grid_ent_max_for_contra = [0.10, 0.15, 0.20]

    best_config_params = None
    best_objective_val = float("inf")
    best_f1 = -1.0
    candidate_results = []

    for ent_min in grid_entailment:
        for contra_min in grid_contradiction:
            for c_max_e in grid_contra_max_for_ent:
                for e_max_c in grid_ent_max_for_contra:
                    preds = []
                    golds = []
                    matrix = {true_s: {pred_s: 0 for pred_s in ALL_STATUSES} for true_s in ALL_STATUSES}
                    for item in cached_dev:
                        g = item["gold_status"]
                        e_s = item["entailment_score"]
                        c_s = item["contradiction_score"]
                        flags = item["flags"]

                        if any("CONTRADICTION" in fl for fl in flags):
                            p_stat = EvidenceVerdictStatus.CONTRADICTED.value
                        elif e_s >= ent_min and c_s <= c_max_e:
                            p_stat = EvidenceVerdictStatus.SUPPORTED.value
                        elif c_s >= contra_min and e_s <= e_max_c:
                            p_stat = EvidenceVerdictStatus.CONTRADICTED.value
                        else:
                            p_stat = item["base_status"]

                        preds.append(p_stat)
                        golds.append(g)
                        if g in matrix and p_stat in matrix[g]:
                            matrix[g][p_stat] += 1

                    total = len(preds)
                    correct = sum(1 for p, g in zip(preds, golds) if p == g)
                    acc = round(correct / max(total, 1), 4)

                    unsupported_indices = [i for i, g in enumerate(golds) if g != EvidenceVerdictStatus.SUPPORTED.value]
                    unsupp_acc = sum(1 for i in unsupported_indices if preds[i] == EvidenceVerdictStatus.SUPPORTED.value)
                    ufar = round(unsupp_acc / max(len(unsupported_indices), 1), 4)

                    supp_indices = [i for i, g in enumerate(golds) if g == EvidenceVerdictStatus.SUPPORTED.value]
                    supp_rej = sum(1 for i in supp_indices if preds[i] != EvidenceVerdictStatus.SUPPORTED.value)
                    sfrr = round(supp_rej / max(len(supp_indices), 1), 4)

                    macro_f1_sum = 0.0
                    active = 0
                    for s in ALL_STATUSES:
                        tp = matrix[s][s]
                        fp = sum(matrix[other][s] for other in ALL_STATUSES if other != s)
                        fn = sum(matrix[s][other] for other in ALL_STATUSES if other != s)
                        p_c = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                        r_c = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                        f_c = (2 * p_c * r_c) / (p_c + r_c) if (p_c + r_c) > 0 else 0.0
                        if tp + fn > 0:
                            macro_f1_sum += f_c
                            active += 1
                    macro_f1 = round(macro_f1_sum / max(active, 1), 4)

                    sfrr_penalty = max(0.0, sfrr - 0.15) * 10.0
                    objective_score = ufar + sfrr_penalty

                    candidate_results.append({
                        "params": {
                            "entailment_min": ent_min,
                            "contradiction_min": contra_min,
                            "contradiction_max_for_entailment": c_max_e,
                            "entailment_max_for_contradiction": e_max_c,
                        },
                        "objective_score": round(objective_score, 4),
                        "UFAR": ufar,
                        "SFRR": sfrr,
                        "macro_f1": macro_f1,
                        "accuracy": acc,
                    })

                    if objective_score < best_objective_val or (abs(objective_score - best_objective_val) < 1e-4 and macro_f1 > best_f1):
                        best_objective_val = objective_score
                        best_f1 = macro_f1
                        best_config_params = {
                            "entailment_min": ent_min,
                            "contradiction_min": contra_min,
                            "contradiction_max_for_entailment": c_max_e,
                            "entailment_max_for_contradiction": e_max_c,
                        }

    # Verify best config on Dev with full evaluate_split
    final_cfg = EvidenceVerifierConfig(**best_config_params)
    final_v = EvidenceVerifier(config=final_cfg)
    best_dev_metrics = evaluate_split(final_v, dev_records)

    dev_hash = compute_file_hash(dev_path)
    calibrated_cfg = EvidenceVerifierConfig(**best_config_params)

    calibration_artifact = {
        "calibration_split": "dev",
        "dev_case_count": len(dev_records),
        "dev_dataset_hash": dev_hash,
        "calibration_objective": "minimize UFAR subject to SFRR <= 0.15, tie-breaker: macro_f1",
        "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_thresholds": best_config_params,
        "config_hash": calibrated_cfg.compute_config_hash(),
        "dev_metrics": best_dev_metrics,
        "candidate_grid_size": len(candidate_results),
    }

    return calibration_artifact


def main():
    parser = argparse.ArgumentParser(description="HALO Evidence Verifier Benchmark Harness")
    parser.add_argument("--calibrate", action="store_true", help="Run Dev-only threshold calibration")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate Train and Dev splits")
    parser.add_argument("--test", action="store_true", help="Run frozen held-out Test split evaluation (one-shot, held-out evaluation)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    train_path = repo_root / "halo_datasets" / "splits" / "train.jsonl"
    dev_path = repo_root / "halo_datasets" / "splits" / "dev.jsonl"
    output_dir = repo_root / "experiments" / "verification" / "evidence_verifier"
    output_dir.mkdir(parents=True, exist_ok=True)

    dev_records = load_split(dev_path, "dev")

    if args.calibrate or (not args.evaluate and not args.calibrate and not args.test):
        calibration_result = calibrate_on_dev(dev_records, dev_path)
        cal_path = output_dir / "threshold_calibration.json"
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(calibration_result, f, indent=2, ensure_ascii=False)
        print(f"[+] Calibration complete! Selected thresholds: {calibration_result['selected_thresholds']}")
        print(f"[+] Dev accuracy: {calibration_result['dev_metrics']['accuracy']}, Macro-F1: {calibration_result['dev_metrics']['macro_f1']}")
        print(f"[+] Saved -> {cal_path}")

    if args.evaluate or (not args.evaluate and not args.calibrate and not args.test):
        print("\n[*] Evaluating frozen Train and Dev benchmark splits...")
        # Load calibrated config if available
        cal_path = output_dir / "threshold_calibration.json"
        if cal_path.exists():
            with open(cal_path, "r", encoding="utf-8") as f:
                cal_data = json.load(f)
                best_params = cal_data.get("selected_thresholds", {})
                config = EvidenceVerifierConfig(**best_params)
        else:
            config = EvidenceVerifierConfig()

        verifier = EvidenceVerifier(config=config)

        # 1. Evaluate Train split (125 cases)
        train_records = load_split(train_path, "train")
        train_metrics = evaluate_split(verifier, train_records)
        print(f"[+] Train (125 cases) - Accuracy: {train_metrics['accuracy']}, Macro-F1: {train_metrics['macro_f1']}, UFAR: {train_metrics['safety_metrics']['UFAR']}, SFRR: {train_metrics['safety_metrics']['SFRR']}")

        # 2. Evaluate Dev split (27 cases)
        dev_metrics = evaluate_split(verifier, dev_records)
        print(f"[+] Dev (27 cases) - Accuracy: {dev_metrics['accuracy']}, Macro-F1: {dev_metrics['macro_f1']}, UFAR: {dev_metrics['safety_metrics']['UFAR']}, SFRR: {dev_metrics['safety_metrics']['SFRR']}")

        # Save evaluation report
        eval_report = {
            "subsystem": "evidence_verifier",
            "benchmark_version": "1.0.0",
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "config_hash": config.compute_config_hash(),
            "thresholds": {
                "entailment_min": config.entailment_min,
                "contradiction_min": config.contradiction_min,
                "contradiction_max_for_entailment": config.contradiction_max_for_entailment,
                "entailment_max_for_contradiction": config.entailment_max_for_contradiction,
            },
            "train_metrics": train_metrics,
            "dev_metrics": dev_metrics,
            "test_split_status": "QUARANTINED (evaluation_allowed: false)",
        }

        report_path = output_dir / "development_metrics.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(eval_report, f, indent=2, ensure_ascii=False)
        print(f"[+] Full evaluation report saved -> {report_path}")

    if args.test:
        print("\n[*] Evaluating frozen held-out Test split (EV14 Single-Shot Evaluation)...")
        test_path = repo_root / "halo_datasets" / "splits" / "test.jsonl"
        manifest_path = output_dir / "test_quarantine_manifest.json"

        if not test_path.exists():
            raise FileNotFoundError(f"Test split not found at {test_path}")
        if not manifest_path.exists():
            raise FileNotFoundError(f"Test quarantine manifest not found at {manifest_path}")

        # Verify integrity of test set hash
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        test_hash = compute_file_hash(test_path)
        if test_hash.lower() != manifest_data["benchmark_hash"].lower():
            raise ValueError(f"Test split hash mismatch! Expected {manifest_data['benchmark_hash']}, got {test_hash}")

        # Load frozen calibrated configuration
        cal_path = output_dir / "threshold_calibration.json"
        if not cal_path.exists():
            raise FileNotFoundError("threshold_calibration.json not found! Cannot evaluate test without frozen calibration.")
        with open(cal_path, "r", encoding="utf-8") as f:
            cal_data = json.load(f)
            best_params = cal_data.get("selected_thresholds", {})
            config = EvidenceVerifierConfig(**best_params)

        verifier = EvidenceVerifier(config=config)
        test_records = load_split(test_path, "test", allow_quarantined_test=True)
        test_metrics = evaluate_split(verifier, test_records)

        print(f"[+] Test (28 cases) - Accuracy: {test_metrics['accuracy']}, Macro-F1: {test_metrics['macro_f1']}, UFAR: {test_metrics['safety_metrics']['UFAR']}, SFRR: {test_metrics['safety_metrics']['SFRR']}")

        test_report = {
            "subsystem": "evidence_verifier",
            "benchmark_version": "1.0.0",
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "config_hash": config.compute_config_hash(),
            "thresholds": best_params,
            "test_metrics": test_metrics,
            "quarantine_verified": True,
            "test_case_count": len(test_records),
            "test_dataset_hash": test_hash,
        }

        test_report_path = output_dir / "test_metrics.json"
        with open(test_report_path, "w", encoding="utf-8") as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        print(f"[+] Test evaluation report saved -> {test_report_path}")


if __name__ == "__main__":
    main()
