"""
Definitions Catalog Parser for Section 2 and Section 378A.
Complies with Section 19 & 50 of prompt.md.
"""

import os
import sys
import json
import re
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.models import DefinedTerm


def parse_definitions(config_path: str = "config.yaml") -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    struct_path = os.path.join(config["output"]["structured_dir"], "structured_act.json")
    final_dir = config["output"]["final_dir"]
    os.makedirs(final_dir, exist_ok=True)

    with open(struct_path, "r", encoding="utf-8") as f:
        act_data = json.load(f)

    print("[*] Extracting statutory definitions from Section 2 & 378A...")

    definitions = []

    # Find Section 2
    sec_2 = None
    for s in act_data["sections"]:
        if s["section_number"] == "2":
            sec_2 = s
            break

    if sec_2:
        sec_text = sec_2["text"]
        # Match clauses: (1) "abridged prospectus" means...
        # or (20) "company" means...
        # Support Unicode quotes: “, ”, ", '
        def_pat = re.compile(
            r"(?:^|\n)\((\d+)\)\s+[\"“\']([^\"”\']+)[\"”\']\s+(means|includes|shall have the meaning)[\s\S]*?(?=(?:(?:\n)\(\d+\)\s+[\"“\'])|$)",
            re.MULTILINE
        )

        matches = list(def_pat.finditer(sec_text))
        for m in matches:
            cl_num = m.group(1)
            term = m.group(2).strip()
            def_text = m.group(0).strip()
            passage_id = f"PAS_ACT_COMPANIES_2013_SEC_2_CLAUSE_{cl_num}"

            definitions.append(DefinedTerm(
                term=term,
                source_section=f"2({cl_num})",
                clause_number=cl_num,
                definition=def_text,
                definition_passage_id=passage_id,
                valid_from="2013-08-29",
                valid_to=None
            ).model_dump())

    # Find Section 378A (Producer Company definitions)
    sec_378a = None
    for s in act_data["sections"]:
        if s["section_number"] == "378A":
            sec_378a = s
            break

    if sec_378a:
        # Match clauses like (a) "active Member" means...
        def_pat_378 = re.compile(
            r"(?:^|\n)\(([a-z])\)\s+[\"“\']([^\"”\']+)[\"”\']\s+(means|includes)[\s\S]*?(?=(?:(?:\n)\([a-z]\)\s+[\"“\'])|$)",
            re.MULTILINE
        )
        for m in def_pat_378.finditer(sec_378a["text"]):
            cl_let = m.group(1)
            term = m.group(2).strip()
            def_text = m.group(0).strip()
            passage_id = f"PAS_ACT_COMPANIES_2013_SEC_378A_CLAUSE_{cl_let.upper()}"

            definitions.append(DefinedTerm(
                term=term,
                source_section=f"378A({cl_let})",
                clause_number=cl_let,
                definition=def_text,
                definition_passage_id=passage_id,
                valid_from="2020-09-28",
                valid_to=None
            ).model_dump())

    out_file = os.path.join(final_dir, "companies_act_2013_definitions.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2, ensure_ascii=False)

    print(f"    [+] Extracted {len(definitions)} legal definitions.")
    print(f"    [+] Saved to: {out_file}")

    return definitions


if __name__ == "__main__":
    parse_definitions()
