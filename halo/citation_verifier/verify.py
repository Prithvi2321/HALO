"""
HALO Citation Verifier: CLI Tool
================================
Protocol: v1.0-FROZEN
Usage:
  python -m halo.citation_verifier.verify --input extracted_claims.json --output citation_results.json
  python -m halo.citation_verifier.verify --input extracted_claims.jsonl --output citation_results.jsonl
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any

from halo.citation_verifier.verifier import CitationVerifier
from halo.citation_verifier.config import CitationVerifierConfig


def process_record(verifier: CitationVerifier, record: Dict[str, Any]) -> Dict[str, Any]:
    ans_id = record.get("answer_id") or record.get("id") or record.get("query_id")
    result = verifier.verify_answer(record, answer_id=ans_id)
    return result.to_dict()


def main():
    parser = argparse.ArgumentParser(description="HALO Legal Citation Verifier CLI")
    parser.add_argument("--input", "-i", required=True, help="Path to input JSON or JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSON or JSONL file")
    parser.add_argument("--threshold", "-t", type=float, default=0.85, help="Fuzzy match threshold")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[!] Error: Input file not found: {args.input}")
        sys.exit(1)

    config = CitationVerifierConfig(fuzzy_match_threshold=args.threshold)
    verifier = CitationVerifier(config=config)

    is_jsonl = args.input.endswith(".jsonl")
    start_time = time.perf_counter()

    if is_jsonl:
        records_processed = 0
        total_citations = 0
        with open(args.input, "r", encoding="utf-8") as in_f, open(args.output, "w", encoding="utf-8") as out_f:
            for line in in_f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    out_rec = process_record(verifier, rec)
                    out_f.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                    records_processed += 1
                    total_citations += out_rec.get("total_citations", 0)
                except Exception as e:
                    print(f"[!] Warning: Error processing line: {e}")

        elapsed = round(time.perf_counter() - start_time, 2)
        print(f"[+] Successfully verified {total_citations} citations across {records_processed} records -> {args.output} ({elapsed}s)")
    else:
        with open(args.input, "r", encoding="utf-8") as in_f:
            data = json.load(in_f)

        if isinstance(data, list):
            results = [process_record(verifier, item) for item in data]
        else:
            results = process_record(verifier, data)

        with open(args.output, "w", encoding="utf-8") as out_f:
            json.dump(results, out_f, indent=2, ensure_ascii=False)

        elapsed = round(time.perf_counter() - start_time, 2)
        print(f"[+] Successfully verified citations -> {args.output} ({elapsed}s)")


if __name__ == "__main__":
    main()
