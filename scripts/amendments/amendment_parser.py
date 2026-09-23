"""
Amendment Document Parser for 2015 and 2020 Amending Acts.
Extracts structured amendment instructions with exact quotes, targets, and operations using offset slicing.
Complies with Section 24, 26, 27 of prompt.md.
"""

import os
import sys
import json
import re
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import AmendmentAction, AmendmentOp


def parse_amendment_sections(doc_id: str, doc_number: str, enactment_date: str, effective_date: str, pages: list[dict], max_sec: int) -> list[dict]:
    full_text = ""
    page_offsets = []
    for p in pages:
        start_char = len(full_text)
        full_text += p["clean_text"] + "\n"
        end_char = len(full_text)
        page_offsets.append((p["page_number"], start_char, end_char))

    def get_page(pos: int) -> int:
        for p_num, s_char, e_char in page_offsets:
            if s_char <= pos <= e_char:
                return p_num
        return pages[-1]["page_number"]

    # 1. Locate start of each amending section (from 2 to max_sec)
    sec_starts = []
    for sec_num in range(2, max_sec + 1):
        pat = re.compile(rf"(?:^|\n){sec_num}\.\s+", re.MULTILINE)
        m = pat.search(full_text)
        if m:
            sec_starts.append((sec_num, m.start()))

    quote_pat = re.compile(r'[\"\u201c\u2018\']([^\u201c\u201d\"\u2018\u2019\']+?)[\"\u201d\u2019\']')

    actions = []

    for idx, (sec_num, start_pos) in enumerate(sec_starts):
        end_pos = sec_starts[idx + 1][1] if idx + 1 < len(sec_starts) else len(full_text)
        raw_sec = full_text[start_pos:end_pos].strip()
        page_num = get_page(start_pos)

        norm_line = re.sub(r"\s+", " ", raw_sec)

        # Target section
        target_sec = "UNKNOWN"
        sec_m = re.search(r"(?:section|sections|Chapter)\s+([0-9A-Z]+)", norm_line[:150], re.IGNORECASE)
        if sec_m:
            target_sec = sec_m.group(1)

        # Target sub-units
        sub_m = re.search(r"sub-section\s*\(([0-9A-Z]+)\)", norm_line, re.IGNORECASE)
        target_sub = sub_m.group(1) if sub_m else None

        clause_m = re.search(r"clause\s*\(([0-9a-z]+)\)", norm_line, re.IGNORECASE)
        target_clause = clause_m.group(1) if clause_m else None

        # Operation detection
        op = AmendmentOp.MODIFY
        lower_line = norm_line.lower()
        if "shall be substituted" in lower_line or "for the words" in lower_line or "for sub-section" in lower_line or "for clause" in lower_line:
            op = AmendmentOp.SUBSTITUTE
        elif "shall be omitted" in lower_line or "is omitted" in lower_line:
            op = AmendmentOp.OMIT
        elif "shall be inserted" in lower_line or "after section" in lower_line or "the following shall be inserted" in lower_line:
            op = AmendmentOp.INSERT
        elif "shall be renumbered" in lower_line:
            op = AmendmentOp.RENUMBER
        elif "shall be added" in lower_line:
            op = AmendmentOp.ADD

        # Quotes extraction
        quotes = [q.strip() for q in quote_pat.findall(raw_sec) if len(q.strip()) > 0 and "EXTRAORDINARY" not in q and "PUBLISHED" not in q]

        old_text = None
        new_text = None

        if op == AmendmentOp.SUBSTITUTE:
            if len(quotes) >= 2:
                old_text = quotes[0]
                new_text = quotes[1]
            elif quotes:
                new_text = quotes[0]
        elif op == AmendmentOp.OMIT:
            if quotes:
                old_text = quotes[0]
        elif op == AmendmentOp.INSERT:
            if quotes:
                new_text = quotes[-1]

        action_id = f"{doc_id}_SEC_{sec_num}"

        actions.append(AmendmentAction(
            amendment_id=action_id,
            amending_act_id=doc_id,
            amending_act_number=doc_number,
            enactment_date=enactment_date,
            effective_date=effective_date,
            target_act="The Companies Act, 2013",
            target_section=target_sec,
            target_subsection=target_sub,
            target_clause=target_clause,
            operation=op,
            old_text=old_text,
            new_text=new_text,
            source_document_id=doc_id,
            source_page=page_num,
            notes=norm_line[:250],
            status="EXTRACTED"
        ).model_dump())

    return actions


def parse_all_amendments(config_path: str = "config.yaml") -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    norm_path = os.path.join(config["output"]["normalized_dir"], "pages_normalized.json")
    final_dir = config["output"]["final_dir"]
    os.makedirs(final_dir, exist_ok=True)

    with open(norm_path, "r", encoding="utf-8") as f:
        all_norm_pages = json.load(f)

    meta_path = os.path.join(config["output"]["staged_dir"], "metadata", "source_manifest.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_map = {m["source_document_id"]: m for m in manifest}

    print("[*] Parsing Amending Acts (2015 and 2020) using offset slicing...")

    all_actions = []

    # 1. 2015 Act (sections 2 to 23)
    act_2015 = manifest_map.get("ACT_COMPANIES_AMEND_2015")
    if act_2015:
        actions_2015 = parse_amendment_sections(
            doc_id=act_2015["source_document_id"],
            doc_number=act_2015["act_number"],
            enactment_date=act_2015["enactment_date"],
            effective_date=act_2015["effective_date"],
            pages=all_norm_pages["ACT_COMPANIES_AMEND_2015"],
            max_sec=23
        )
        print(f"    [+] ACT_COMPANIES_AMEND_2015: Extracted {len(actions_2015)} amending sections.")
        all_actions.extend(actions_2015)

    # 2. 2020 Act (sections 2 to 66)
    act_2020 = manifest_map.get("ACT_COMPANIES_AMEND_2020")
    if act_2020:
        actions_2020 = parse_amendment_sections(
            doc_id=act_2020["source_document_id"],
            doc_number=act_2020["act_number"],
            enactment_date=act_2020["enactment_date"],
            effective_date=act_2020["effective_date"],
            pages=all_norm_pages["ACT_COMPANIES_AMEND_2020"],
            max_sec=66
        )
        print(f"    [+] ACT_COMPANIES_AMEND_2020: Extracted {len(actions_2020)} amending sections.")
        all_actions.extend(actions_2020)

    out_file = os.path.join(final_dir, "companies_act_2013_amendments.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_actions, f, indent=2, ensure_ascii=False)

    print(f"[*] Total amendment operations cataloged: {len(all_actions)}")
    print(f"[*] Saved to: {out_file}")

    return all_actions


if __name__ == "__main__":
    parse_all_amendments()
