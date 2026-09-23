"""
Schedules Parser for Schedules I through VII of the Companies Act, 2013.
Complies with Section 20 & 21 of prompt.md.
"""

import os
import sys
import json
import re
import hashlib
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import ScheduleNode


SCHEDULE_METADATA = [
    {"num": "I", "title": "MEMORANDUM AND ARTICLES OF ASSOCIATION", "start_page": 253},
    {"num": "II", "title": "USEFUL LIVES TO COMPUTE DEPRECIATION", "start_page": 276},
    {"num": "III", "title": "GENERAL INSTRUCTIONS FOR PREPARATION OF BALANCE SHEET AND STATEMENT OF PROFIT AND LOSS", "start_page": 283},
    {"num": "IV", "title": "CODE FOR INDEPENDENT DIRECTORS", "start_page": 358},
    {"num": "V", "title": "CONDITIONS FOR APPOINTMENT OF MANAGING OR WHOLE-TIME DIRECTOR OR MANAGER", "start_page": 361},
    {"num": "VI", "title": "INFRASTRUCTURAL PROJECTS AND LOANS", "start_page": 367},
    {"num": "VII", "title": "ACTIVITIES RELATING TO CORPORATE SOCIAL RESPONSIBILITY", "start_page": 369},
]


def parse_schedules(config_path: str = "config.yaml") -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    norm_path = os.path.join(config["output"]["normalized_dir"], "pages_normalized.json")
    struct_dir = config["output"]["structured_dir"]

    with open(norm_path, "r", encoding="utf-8") as f:
        all_norm_pages = json.load(f)

    act_pages = all_norm_pages["ACT_COMPANIES_2013"]

    print("[*] Parsing Schedules I through VII...")

    schedules = []

    for idx, sch_meta in enumerate(SCHEDULE_METADATA):
        start_p = sch_meta["start_page"]
        end_p = SCHEDULE_METADATA[idx + 1]["start_page"] - 1 if idx + 1 < len(SCHEDULE_METADATA) else 370

        sch_text_parts = []
        for p in act_pages:
            if start_p <= p["page_number"] <= end_p:
                sch_text_parts.append(p["clean_text"])

        full_sch_text = "\n".join(sch_text_parts).strip()
        sch_hash = hashlib.sha256(full_sch_text.encode("utf-8")).hexdigest()
        sch_id = f"ACT_COMPANIES_2013_SCH_{sch_meta['num']}"

        # Detect Tables (e.g. TABLE A, TABLE B)
        table_matches = list(re.finditer(r"(TABLE\s+[A-Z\-\s]+)", full_sch_text))
        tables = []
        for tm in table_matches:
            tables.append({"table_name": tm.group(1).strip()})

        # Detect Parts (e.g. PART I, PART II)
        part_matches = list(re.finditer(r"(PART\s+[IVXLCDM]+)", full_sch_text))
        parts = []
        for pm in part_matches:
            parts.append({"part_name": pm.group(1).strip()})

        node = ScheduleNode(
            schedule_id=sch_id,
            schedule_number=sch_meta["num"],
            title=sch_meta["title"],
            text=full_sch_text,
            canonical_text=full_sch_text,
            parts=parts,
            tables=tables,
            source_page_start=start_p,
            source_page_end=end_p,
            content_hash=sch_hash
        )
        schedules.append(node.model_dump())
        print(f"    [+] Schedule {sch_meta['num']}: Pages {start_p}-{end_p}, {len(tables)} tables, {len(parts)} parts.")

    # Save to structured dir
    out_file = os.path.join(struct_dir, "schedules.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2, ensure_ascii=False)

    print(f"[*] Saved {len(schedules)} schedules to {out_file}")
    return schedules


if __name__ == "__main__":
    parse_schedules()
