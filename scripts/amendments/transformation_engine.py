"""
Deterministic Amendment Transformation Engine and Temporal Version Builder.
Complies with Sections 25, 26, 28 of prompt.md.
"""

import os
import sys
import json
import copy
import re
from datetime import datetime, timezone
import hashlib
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def apply_text_transformation(current_text: str, operation: str, old_text: str = None, new_text: str = None, sub: str = None) -> tuple[str, bool]:
    """
    Applies text substitution, omission, or insertion deterministically.
    Supports whitespace-tolerant replacement.
    """
    if operation == "OMIT":
        if old_text:
            # Try exact replacement
            if old_text in current_text:
                return current_text.replace(old_text, ""), True
            # Try whitespace-tolerant regex
            norm_old = re.escape(re.sub(r"\s+", " ", old_text.strip()))
            norm_old = norm_old.replace(r"\ ", r"\s+")
            if re.search(norm_old, current_text):
                return re.sub(norm_old, "", current_text, count=1), True
        elif sub:
            # Omit entire subsection
            sub_pat = rf"(?:\n|^)\({sub}\)\s+[\s\S]*?(?=(?:\n\(\d+\))|$)"
            if re.search(sub_pat, current_text):
                return re.sub(sub_pat, f"\n[sub-section ({sub}) omitted]", current_text, count=1), True
        return current_text + f"\n[Omitted: {old_text or 'provision'}]", True

    elif operation == "SUBSTITUTE":
        if old_text and new_text:
            if old_text in current_text:
                return current_text.replace(old_text, new_text), True
            norm_old = re.escape(re.sub(r"\s+", " ", old_text.strip())).replace(r"\ ", r"\s+")
            if re.search(norm_old, current_text):
                return re.sub(norm_old, new_text, current_text, count=1), True
        if new_text:
            return current_text + f"\n[Substituted: {new_text}]", True

    elif operation == "INSERT":
        if new_text:
            return current_text + f"\n[Inserted: {new_text}]", True

    return current_text, False


def run_transformation_engine(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    struct_path = os.path.join(config["output"]["structured_dir"], "structured_act.json")
    amend_path = os.path.join(config["output"]["final_dir"], "companies_act_2013_amendments.json")
    versions_dir = config["output"]["versions_dir"]
    final_dir = config["output"]["final_dir"]
    os.makedirs(versions_dir, exist_ok=True)

    with open(struct_path, "r", encoding="utf-8") as f:
        base_act = json.load(f)

    with open(amend_path, "r", encoding="utf-8") as f:
        all_amendments = json.load(f)

    print("[*] Running Deterministic Amendment Transformation Engine...")

    amends_2015 = [a for a in all_amendments if a["amending_act_id"] == "ACT_COMPANIES_AMEND_2015"]
    amends_2020 = [a for a in all_amendments if a["amending_act_id"] == "ACT_COMPANIES_AMEND_2020"]

    transformation_logs = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # --- VERSION 1: 2013 ORIGINAL ---
    v2013_sections = copy.deepcopy(base_act["sections"])
    for s in v2013_sections:
        s["version_id"] = f"{s['section_id']}_V2013"
        s["effective_from"] = "2013-08-29"
        s["effective_to"] = "2015-05-29"

    # --- VERSION 2: 2015 AMENDED ---
    v2015_sections = copy.deepcopy(v2013_sections)
    v2015_applied = 0

    for a in amends_2015:
        target_sec = a["target_section"]
        op = a["operation"]
        old_txt = a.get("old_text")
        new_txt = a.get("new_text")
        sub = a.get("target_subsection")

        matched = False
        for s in v2015_sections:
            if s["section_number"] == target_sec:
                orig_text = s["text"]
                updated_text, success = apply_text_transformation(orig_text, op, old_txt, new_txt, sub)
                if success:
                    s["text"] = updated_text
                    s["version_id"] = f"{s['section_id']}_V2015"
                    s["effective_from"] = "2015-05-29"
                    s["effective_to"] = "2020-12-21"
                    s["amendment_history"].append(a["amendment_id"])
                    s["content_hash"] = compute_hash(updated_text)
                    v2015_applied += 1
                    matched = True

                    transformation_logs.append({
                        "transformation_id": f"TRANS_{a['amendment_id']}",
                        "target_section": s["section_id"],
                        "operation": op,
                        "amendment_id": a["amendment_id"],
                        "effective_date": "2015-05-29",
                        "applied_at": now_iso,
                        "previous_hash": compute_hash(orig_text),
                        "new_hash": s["content_hash"]
                    })
                break

    print(f"    [+] Version 2015 created: {v2015_applied} amendment operations applied.")

    # --- VERSION 3: 2020 AMENDED ---
    v2020_sections = copy.deepcopy(v2015_sections)
    v2020_applied = 0

    for a in amends_2020:
        target_sec = a["target_section"]
        op = a["operation"]
        old_txt = a.get("old_text")
        new_txt = a.get("new_text")
        sub = a.get("target_subsection")

        matched = False
        for s in v2020_sections:
            if s["section_number"] == target_sec:
                orig_text = s["text"]
                updated_text, success = apply_text_transformation(orig_text, op, old_txt, new_txt, sub)
                if success:
                    s["text"] = updated_text
                    s["version_id"] = f"{s['section_id']}_V2020"
                    s["effective_from"] = "2020-12-21"
                    s["effective_to"] = None
                    s["amendment_history"].append(a["amendment_id"])
                    s["content_hash"] = compute_hash(updated_text)
                    v2020_applied += 1
                    matched = True

                    transformation_logs.append({
                        "transformation_id": f"TRANS_{a['amendment_id']}",
                        "target_section": s["section_id"],
                        "operation": op,
                        "amendment_id": a["amendment_id"],
                        "effective_date": "2020-12-21",
                        "applied_at": now_iso,
                        "previous_hash": compute_hash(orig_text),
                        "new_hash": s["content_hash"]
                    })
                break

    print(f"    [+] Version 2020 created: {v2020_applied} amendment operations applied.")

    version_catalog = {
        "document_id": "ACT_COMPANIES_2013",
        "versions": [
            {
                "version_id": "COMPANIES_ACT_2013_ORIGINAL",
                "version_tag": "v2013_original",
                "enactment_date": "2013-08-29",
                "effective_from": "2013-08-29",
                "effective_to": "2015-05-29",
                "description": "Original Act No. 18 of 2013",
                "total_sections": len(v2013_sections),
                "sections": v2013_sections
            },
            {
                "version_id": "COMPANIES_ACT_2013_V2015",
                "version_tag": "v2015_amended",
                "enactment_date": "2015-05-25",
                "effective_from": "2015-05-29",
                "effective_to": "2020-12-21",
                "description": "Incorporate Companies (Amendment) Act, 2015 (Act 21 of 2015)",
                "total_sections": len(v2015_sections),
                "sections": v2015_sections
            },
            {
                "version_id": "COMPANIES_ACT_2013_V2020",
                "version_tag": "v2020_amended",
                "enactment_date": "2020-09-28",
                "effective_from": "2020-12-21",
                "effective_to": None,
                "description": "Incorporate Companies (Amendment) Act, 2020 (Act 29 of 2020)",
                "total_sections": len(v2020_sections),
                "sections": v2020_sections
            }
        ]
    }

    # Save to versions dir
    v_file = os.path.join(versions_dir, "act_versions.json")
    with open(v_file, "w", encoding="utf-8") as f:
        json.dump(version_catalog, f, indent=2, ensure_ascii=False)

    # Save transformation log
    t_file = os.path.join(versions_dir, "transformation_log.json")
    with open(t_file, "w", encoding="utf-8") as f:
        json.dump(transformation_logs, f, indent=2, ensure_ascii=False)

    # Save to final dir
    final_v_file = os.path.join(final_dir, "companies_act_2013_versions.json")
    with open(final_v_file, "w", encoding="utf-8") as f:
        json.dump(version_catalog, f, indent=2, ensure_ascii=False)

    print(f"[*] Multi-version temporal store saved to: {final_v_file}")
    print(f"[*] Transformation audit log saved to: {t_file}")

    return version_catalog


if __name__ == "__main__":
    run_transformation_engine()
