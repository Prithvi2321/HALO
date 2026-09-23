"""
HALO Claim Extractor: CLI Tool
==============================
Protocol: v1.0-FROZEN
Usage:
  python -m halo.claim_extractor.extract --input answer.json --output claims.json
  python -m halo.claim_extractor.extract --input answers.jsonl --output claims.jsonl
"""

import argparse
import json
import os
import sys
from typing import Dict, Any

from halo.claim_extractor.extractor import ClaimExtractor
from halo.claim_extractor.config import ClaimExtractorConfig


def process_single(extractor: ClaimExtractor, data: Dict[str, Any], answer_key: str) -> Dict[str, Any]:
    text = data.get(answer_key)
    if text is None:
        # Fallback to common answer keys in B5 and benchmark
        if "generation" in data and isinstance(data["generation"], dict):
            text = data["generation"].get("predicted_answer")
        elif "predicted_answer" in data:
            text = data["predicted_answer"]
        elif "generated_claim" in data:
            text = data["generated_claim"]
        elif "text" in data:
            text = data["text"]
        elif "answer" in data:
            text = data["answer"]

    if text is None:
        text = str(data)

    ans_id = data.get("query_id") or data.get("id") or data.get("answer_id")
    result = extractor.extract(text, answer_id=ans_id)
    return result.to_dict()


def main():
    parser = argparse.ArgumentParser(description="HALO Legal Claim Extractor CLI")
    parser.add_argument("--input", "-i", required=True, help="Path to input JSON or JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSON or JSONL file")
    parser.add_argument("--answer-key", default="predicted_answer", help="Key name containing answer text")
    parser.add_argument("--proximity-strategy", default="same_sentence_then_adjacent", help="Citation proximity strategy")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[!] Error: Input file not found: {args.input}")
        sys.exit(1)

    config = ClaimExtractorConfig(citation_proximity_strategy=args.proximity_strategy)
    extractor = ClaimExtractor(config=config)

    # Detect JSON vs JSONL
    is_jsonl = args.input.endswith(".jsonl")

    if is_jsonl:
        records_processed = 0
        with open(args.input, "r", encoding="utf-8") as in_f, open(args.output, "w", encoding="utf-8") as out_f:
            for line in in_f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    out_rec = process_single(extractor, rec, args.answer_key)
                    out_f.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                    records_processed += 1
                except Exception as e:
                    print(f"[!] Warning: Error processing line: {e}")
        print(f"[+] Successfully extracted claims from {records_processed} records -> {args.output}")
    else:
        with open(args.input, "r", encoding="utf-8") as in_f:
            data = json.load(in_f)

        if isinstance(data, list):
            results = [process_single(extractor, item, args.answer_key) for item in data]
        else:
            results = process_single(extractor, data, args.answer_key)

        with open(args.output, "w", encoding="utf-8") as out_f:
            json.dump(results, out_f, indent=2, ensure_ascii=False)

        print(f"[+] Successfully extracted claims -> {args.output}")


if __name__ == "__main__":
    main()
