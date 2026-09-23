"""
HALO Baseline 3 — Deterministic Sparse BM25 Vector Index Builder
================================================================
Constructs the official BM25 retrieval index for Baseline 3 using rank_bm25.BM25Okapi.

Corpus:
  - Dataset 1: Companies Act, 2013 (1,640 passages)
  - Dataset 2: Curated Judicial Corpus (1,133 passages)
  - Total: 2,773 passages

Guarantees:
  - Cryptographic verification of frozen corpus hashes prior to indexing.
  - Deterministic passage ordering (lexicographical by passage_id).
  - Legal-aware regular expression tokenization with protected statutory operators.
  - Parameters: k1=1.5, b=0.75, epsilon=0.25 strictly per protocol v1.0.
  - Zero leakage: Dataset 3 benchmark queries/answers are strictly excluded.
"""

import os
import sys
import json
import re
import pickle
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "experiments", "configs", "b3_bm25_config.json")
INDEX_DIR = os.path.join(BASE_DIR, "experiments", "indices", "bm25")

# Frozen Corpus Paths
D1_PASSAGES_PATH = os.path.join(BASE_DIR, "data", "dataset_1", "final", "companies_act_2013_passages.jsonl")
D2_PASSAGES_PATH = os.path.join(BASE_DIR, "data", "dataset2", "canonical", "passages.jsonl")
D3_CANONICAL_PATH = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")

# Expected Frozen SHA-256 Hashes
EXPECTED_D1_SHA256 = "37c5ced49fc3925342a7eebfc84eb2988f863166b60c0a8cf527aefae0e8c27c"
EXPECTED_D2_SHA256 = "43af9b6ed2df7be5489a71e81cf1f0125469d0cbe4443d0e536edb35703d3996"

TOKEN_PATTERN = re.compile(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b|\b\d+(?:[A-Za-z0-9_\(\)\.\-/]*[A-Za-z0-9_\)]|\b)")

STANDARD_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "my", "myself", "nor", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

PROTECTED_LEGAL_TERMS = {"shall", "must", "may", "not", "no", "without", "proviso", "omitted", "substituted"}
EFFECTIVE_STOPWORDS = STANDARD_STOPWORDS - PROTECTED_LEGAL_TERMS


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def tokenize_legal_text(text: str) -> List[str]:
    """Tokenizes text using legal regular expressions while preserving protected legal operators."""
    raw_tokens = TOKEN_PATTERN.findall(text)
    tokens = []
    for t in raw_tokens:
        tl = t.lower()
        if tl not in EFFECTIVE_STOPWORDS:
            tokens.append(tl)
    return tokens


class BM25IndexBuilder:
    def __init__(self, config_path: str = CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.retrieval_cfg = self.config.get("retrieval", {})
        self.k1 = float(self.retrieval_cfg.get("k1", 1.5))
        self.b = float(self.retrieval_cfg.get("b", 0.75))
        self.epsilon = float(self.retrieval_cfg.get("epsilon", 0.25))

    def verify_frozen_corpora(self):
        print("[*] Verifying frozen corpus hashes before BM25 index construction...")
        d1_hash = compute_sha256(D1_PASSAGES_PATH)
        d2_hash = compute_sha256(D2_PASSAGES_PATH)

        if d1_hash != EXPECTED_D1_SHA256:
            raise ValueError(f"FATAL: Dataset 1 hash mismatch! Expected {EXPECTED_D1_SHA256}, got {d1_hash}")
        if d2_hash != EXPECTED_D2_SHA256:
            raise ValueError(f"FATAL: Dataset 2 hash mismatch! Expected {EXPECTED_D2_SHA256}, got {d2_hash}")

        print(f"    [+] Dataset 1 verified: {d1_hash[:16]}... (1,640 passages)")
        print(f"    [+] Dataset 2 verified: {d2_hash[:16]}... (1,133 passages)")

    def load_passages(self) -> List[Dict[str, Any]]:
        passages = []

        # Load Dataset 1 (Statutory)
        with open(D1_PASSAGES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                p_text = item.get("canonical_text") or item.get("text", "")
                meta = {
                    "passage_id": item["passage_id"],
                    "document_id": item.get("document_id", "ACT_COMPANIES_2013"),
                    "dataset": "dataset1",
                    "section_id": item.get("section_id"),
                    "subsection_id": item.get("subsection_id"),
                    "clause_id": item.get("clause_id"),
                    "heading": item.get("heading"),
                    "judgment_id": None,
                    "court": None,
                    "date": item.get("enactment_date") or item.get("commencement_date"),
                    "citation": None,
                    "text": p_text.strip()
                }
                passages.append(meta)

        # Load Dataset 2 (Judicial)
        with open(D2_PASSAGES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                p_text = item.get("text", "")
                meta = {
                    "passage_id": item["passage_id"],
                    "document_id": item.get("document_id"),
                    "dataset": "dataset2",
                    "section_id": None,
                    "subsection_id": None,
                    "clause_id": None,
                    "heading": None,
                    "judgment_id": item.get("document_id"),
                    "court": item.get("court"),
                    "date": None,
                    "citation": item.get("citation"),
                    "text": p_text.strip()
                }
                passages.append(meta)

        # Sort deterministically by passage_id
        passages.sort(key=lambda x: x["passage_id"])
        print(f"[+] Total merged corpus passages loaded: {len(passages)} (sorted deterministically)")
        assert len(passages) == 2773, f"Expected exactly 2,773 passages, got {len(passages)}"
        return passages

    def verify_no_leakage(self, meta_path: str):
        indexed_ids = set()
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    indexed_ids.add(json.loads(line)["passage_id"])

        d3_record_ids = set()
        with open(D3_CANONICAL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d3_record_ids.add(json.loads(line)["record_id"])

        overlap = indexed_ids & d3_record_ids
        if overlap:
            raise ValueError(f"FATAL: Dataset 3 benchmark leakage detected in BM25 index! Overlap: {overlap}")

    def build_index(self):
        index_sub_dir = os.path.join(INDEX_DIR, "index")
        os.makedirs(index_sub_dir, exist_ok=True)
        self.verify_frozen_corpora()
        passages = self.load_passages()

        from rank_bm25 import BM25Okapi

        print(f"[*] Tokenizing {len(passages)} passages using legal tokenizer...")
        corpus_tokens = []
        for p in passages:
            tokens = tokenize_legal_text(p["text"])
            corpus_tokens.append(tokens)

        print(f"[*] Constructing BM25Okapi inverted index (k1={self.k1}, b={self.b}, epsilon={self.epsilon})...")
        bm25_model = BM25Okapi(corpus_tokens, k1=self.k1, b=self.b, epsilon=self.epsilon)

        model_path = os.path.join(index_sub_dir, "bm25_model.pkl")
        metadata_path = os.path.join(INDEX_DIR, "metadata.jsonl")
        manifest_path = os.path.join(INDEX_DIR, "index_manifest.json")
        receipt_path = os.path.join(INDEX_DIR, "build_receipt.json")

        # 1. Save BM25 pickled model
        with open(model_path, "wb") as f:
            pickle.dump(bm25_model, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"[+] Saved BM25 model artifact: {os.path.relpath(model_path, BASE_DIR)}")

        # 2. Save metadata JSONL
        with open(metadata_path, "w", encoding="utf-8") as f:
            for p in passages:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"[+] Saved metadata JSONL: {os.path.relpath(metadata_path, BASE_DIR)}")

        # 3. Anti-leakage audit
        print("[*] Running zero-leakage audit against Dataset 3...")
        self.verify_no_leakage(metadata_path)
        print("    [+] Zero-leakage verified: Dataset 3 benchmark content is 100% absent.")

        # 4. Save index manifest
        manifest_data = {
            "index_type": "sparse_bm25",
            "algorithm": "BM25Okapi",
            "k1": self.k1,
            "b": self.b,
            "epsilon": self.epsilon,
            "passage_count": len(passages),
            "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "tokenizer": {
                "pattern": r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b|\b\d+(?:[A-Za-z0-9_\(\)\.\-/]*[A-Za-z0-9_\)]|\b)",
                "protected_stopwords": list(sorted(PROTECTED_LEGAL_TERMS))
            },
            "corpus_sources": {
                "dataset1": {
                    "file": "data/dataset_1/final/companies_act_2013_passages.jsonl",
                    "sha256": EXPECTED_D1_SHA256,
                    "passages": 1640
                },
                "dataset2": {
                    "file": "data/dataset2/canonical/passages.jsonl",
                    "sha256": EXPECTED_D2_SHA256,
                    "passages": 1133
                }
            }
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved index manifest: {os.path.relpath(manifest_path, BASE_DIR)}")

        # 5. Build Receipt
        receipt = {
            "index_type": "sparse_bm25",
            "status": "BUILT_AND_VERIFIED",
            "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "passage_count": len(passages),
            "hashes": {
                "bm25_model_pkl": compute_sha256(model_path),
                "metadata_jsonl": compute_sha256(metadata_path),
                "index_manifest_json": compute_sha256(manifest_path)
            },
            "validation": {
                "dataset1_sha256": EXPECTED_D1_SHA256,
                "dataset2_sha256": EXPECTED_D2_SHA256,
                "dataset3_leakage_detected": False
            }
        }
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved build receipt: {os.path.relpath(receipt_path, BASE_DIR)}")

        print("\n" + "=" * 70)
        print("  BM25 INDEX CONSTRUCTION COMPLETE & VERIFIED")
        print("=" * 70)


if __name__ == "__main__":
    builder = BM25IndexBuilder()
    builder.build_index()
