"""
Cross-Reference Detection Engine.
Complies with Sections 22 & 23 of prompt.md.
"""

import os
import sys
import json
import re
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import CrossReference


def extract_cross_references(config_path: str = "config.yaml") -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    struct_path = os.path.join(config["output"]["structured_dir"], "structured_act.json")
    final_dir = config["output"]["final_dir"]
    os.makedirs(final_dir, exist_ok=True)

    with open(struct_path, "r", encoding="utf-8") as f:
        act_data = json.load(f)

    print("[*] Detecting statutory cross-references...")

    # Regex patterns
    sec_ref_pat = re.compile(r"\b(?:section|sections)\s+(\d+[A-Z]?(?:\s*(?:and|,)\s*\d+[A-Z]?)*)", re.IGNORECASE)
    sch_ref_pat = re.compile(r"\b(?:Schedule)\s+([IVXLCDM]+)", re.IGNORECASE)
    ext_act_pat = re.compile(r"\b([A-Z][a-zA-Z\s]+(?:Act|Code),\s*\d{4})\b")

    valid_sec_ids = {s["section_id"] for s in act_data["sections"]}
    all_refs = []

    for sec in act_data["sections"]:
        s_id = sec["section_id"]
        text = sec["text"]

        # Section references
        for m in sec_ref_pat.finditer(text):
            raw_match = m.group(0)
            target_str = m.group(1)
            start_pos = m.start()
            end_pos = m.end()
            surrounding_context = text[max(0, start_pos - 40):min(len(text), end_pos + 40)].lower()

            # Handle multiple sections like '4 and 5'
            targets = re.findall(r"\d+[A-Z]?", target_str)
            for t in targets:
                candidate_id = f"ACT_COMPANIES_2013_SEC_{t}"
                if candidate_id in valid_sec_ids and "1956" not in surrounding_context:
                    ref_type = "internal_section"
                    target_id = candidate_id
                elif "1956" in surrounding_context or "sebi" in surrounding_context or "board" in surrounding_context:
                    ref_type = "external_act"
                    target_id = None
                else:
                    ref_type = "unresolved_reference"
                    target_id = None

                all_refs.append(CrossReference(
                    source_passage_id=f"PAS_{s_id}",
                    source_section_id=s_id,
                    target_reference=f"Section {t}",
                    target_section_id=target_id,
                    reference_type=ref_type,
                    raw_mention=raw_match
                ).model_dump())

        # Schedule references
        for m in sch_ref_pat.finditer(text):
            sch_num = m.group(1)
            all_refs.append(CrossReference(
                source_passage_id=f"PAS_{s_id}",
                source_section_id=s_id,
                target_reference=f"Schedule {sch_num}",
                target_section_id=f"ACT_COMPANIES_2013_SCH_{sch_num}",
                reference_type="internal_schedule",
                raw_mention=m.group(0)
            ).model_dump())

        # External Act references
        for m in ext_act_pat.finditer(text):
            act_name = m.group(1).strip()
            all_refs.append(CrossReference(
                source_passage_id=f"PAS_{s_id}",
                source_section_id=s_id,
                target_reference=act_name,
                target_section_id=None,
                reference_type="external_act",
                raw_mention=m.group(0)
            ).model_dump())

    out_file = os.path.join(final_dir, "companies_act_2013_cross_references.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_refs, f, indent=2, ensure_ascii=False)

    print(f"    [+] Discovered {len(all_refs)} explicit cross-references across sections.")
    print(f"    [+] Saved to: {out_file}")
    return all_refs


if __name__ == "__main__":
    extract_cross_references()
