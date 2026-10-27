"""
HALO Supreme Court Corporate & Commercial Jurisprudence Filter
============================================================
Filters extracted 2023 Supreme Court passages for company law, insolvency,
arbitration, securities, and commercial jurisprudence relevant to HALO.
"""

import os
import sys
import json
import re
from collections import defaultdict
from typing import Dict, List, Any, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC_2023_PASSAGES = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_passages.jsonl")
OUTPUT_CORP_PASSAGES = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_passages.jsonl")
OUTPUT_SUMMARY = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_summary.json")

# Definitive Corporate & Commercial Match Patterns
PATTERNS = {
    "companies_act": re.compile(r"\bCompanies\s+Act\b|\bSection\s+\d+\s+of\s+the\s+Companies\s+Act\b", re.IGNORECASE),
    "ibc_insolvency": re.compile(r"\bInsolvency\s+and\s+Bankruptcy\s+Code\b|\bCorporate\s+Debtor\b|\bResolution\s+Plan\b|\bResolution\s+Professional\b|\bCommittee\s+of\s+Creditors\b|\bSection\s+(?:7|9|10|14|31|53)\s+of\s+(?:the\s+)?(?:IBC|Insolvency)\b", re.IGNORECASE),
    "tribunals": re.compile(r"\bNCLT\b|\bNCLAT\b|\bNational\s+Company\s+Law\s+Tribunal\b|\bNational\s+Company\s+Law\s+Appellate\s+Tribunal\b|\bSecurities\s+Appellate\s+Tribunal\b|\bSAT\b", re.IGNORECASE),
    "arbitration": re.compile(r"\bArbitration\s+and\s+Conciliation\s+Act\b|\bSection\s+(?:8|9|11|34|37)\s+of\s+the\s+Arbitration\b|\bArbitral\s+Tribunal\b|\bCommercial\s+Courts\s+Act\b", re.IGNORECASE),
    "sebi_securities": re.compile(r"\bSecurities\s+and\s+Exchange\s+Board\s+of\s+India\b|\bSEBI\b|\bInsider\s+Trading\b|\bSecurities\s+Contracts\s+\(Regulation\)\s+Act\b", re.IGNORECASE),
    "corporate_governance": re.compile(r"\bBoard\s+of\s+Directors\b|\bDisqualification\s+of\s+Directors\b|\bOppression\s+and\s+Mismanagement\b|\bScheme\s+of\s+Arrangement\b|\bAmalgamation\b|\bMerger\b|\bShareholder\s+Agreement\b", re.IGNORECASE),
    "commercial_contracts": re.compile(r"\bBank\s+Guarantee\b|\bLetter\s+of\s+Credit\b|\bSARFAESI\b|\bDebt\s+Recovery\s+Tribunal\b|\bDRT\b", re.IGNORECASE)
}

def filter_corpus():
    print("=" * 75)
    print("FILTERING 2023 SUPREME COURT JUDGMENTS FOR CORPORATE JURISPRUDENCE")
    print("=" * 75)

    if not os.path.exists(SC_2023_PASSAGES):
        print(f"Error: {SC_2023_PASSAGES} not found!")
        return

    # Group passages by document_id
    print("[*] Loading extracted 2023 passages...")
    passages_by_doc = defaultdict(list)
    doc_meta = {}

    with open(SC_2023_PASSAGES, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                doc_id = item["document_id"]
                passages_by_doc[doc_id].append(item)
                if doc_id not in doc_meta:
                    doc_meta[doc_id] = {
                        "case_title": item.get("case_title"),
                        "citation": item.get("citation"),
                        "neutral_citation": item.get("neutral_citation"),
                        "decision_date": item.get("decision_date"),
                        "judge": item.get("judge")
                    }

    total_judgments = len(passages_by_doc)
    total_passages = sum(len(p) for p in passages_by_doc.values())
    print(f"    [+] Loaded {total_passages:,} passages across {total_judgments} judgments.")

    # Match judgments against patterns
    print("[*] Analyzing legal topics across judgments...")
    matched_docs = {}
    category_counts = defaultdict(int)

    for doc_id, p_list in passages_by_doc.items():
        doc_full_text = " ".join(p["text"] for p in p_list)
        matched_categories = set()

        for cat, pattern in PATTERNS.items():
            if pattern.search(doc_full_text):
                matched_categories.add(cat)

        if matched_categories:
            matched_docs[doc_id] = {
                "categories": list(matched_categories),
                "passages": p_list
            }
            for cat in matched_categories:
                category_counts[cat] += 1

    matched_judgments_count = len(matched_docs)
    matched_passages_count = sum(len(d["passages"]) for d in matched_docs.values())

    print("\n" + "=" * 75)
    print("FILTERING BREAKDOWN BY CORPORATE / COMMERCIAL CATEGORY:")
    print("=" * 75)
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  - {cat:<24} : {count:3d} judgments")

    print("\n" + "=" * 75)
    print("SUMMARY RESULTS:")
    print("=" * 75)
    print(f"Total 2023 Judgments Evaluated:       {total_judgments}")
    print(f"Corporate / Commercial Judgments:    {matched_judgments_count} ({matched_judgments_count/total_judgments*100:.1f}%)")
    print(f"Filtered Passages Retained:           {matched_passages_count:,} out of {total_passages:,}")
    print(f"Unrelated Judgments Pruned (Noise):   {total_judgments - matched_judgments_count} (Criminal, Family, Service, Motor Claims)")
    print("=" * 75)

    # Save filtered corporate passages
    print(f"[*] Writing filtered passages to {OUTPUT_CORP_PASSAGES}...")
    with open(OUTPUT_CORP_PASSAGES, "w", encoding="utf-8") as out_f:
        for doc_id, data in matched_docs.items():
            cats = data["categories"]
            for p in data["passages"]:
                p["corporate_topics"] = cats
                out_f.write(json.dumps(p, ensure_ascii=False) + "\n")

    summary_data = {
        "year": "2023",
        "total_judgments_in_year": total_judgments,
        "corporate_judgments_count": matched_judgments_count,
        "corporate_judgments_percentage": round(matched_judgments_count / total_judgments * 100.0, 2),
        "corporate_passages_count": matched_passages_count,
        "category_counts": dict(category_counts),
        "output_file": OUTPUT_CORP_PASSAGES
    }

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as sf:
        json.dump(summary_data, sf, indent=2)

    print("[+] Saved successfully!")

    # Display 5 sample landmark corporate cases identified
    print("\n" + "=" * 75)
    print("SAMPLE LANDMARK 2023 CORPORATE JUDGMENTS IDENTIFIED:")
    print("=" * 75)
    sample_ids = list(matched_docs.keys())[:5]
    for idx, d_id in enumerate(sample_ids, 1):
        m = doc_meta[d_id]
        cats = matched_docs[d_id]["categories"]
        n_paras = len(matched_docs[d_id]["passages"])
        print(f"[{idx}] {m['case_title']}")
        print(f"    Citation: {m['citation']} | Neutral: {m['neutral_citation']} | Date: {m['decision_date']}")
        print(f"    Judge: {m['judge']} | Topics: {', '.join(cats)} | Paras: {n_paras}")
        print()

if __name__ == "__main__":
    filter_corpus()
