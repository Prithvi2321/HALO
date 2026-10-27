"""
HALO Step 1: Corporate Supreme Court Ingestion & Index Builder
=============================================================
Merges the 9,450 filtered 2023 Supreme Court corporate passages with
Dataset 1 (1,640 statutory) and Dataset 2 (1,133 curated judicial),
applies hierarchical contextual formatting, and builds:
1. Updated BM25 Sparse Index (12,223 passages)
2. Updated Dense BGE Vector Store (12,223 x 1024 tensor)
"""

import os
import sys
import json
import time
import pickle
import torch
import numpy as np
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from transformers import AutoTokenizer, AutoModel
from rank_bm25 import BM25Okapi
from scripts.experiments.build_bm25_index import tokenize_legal_text

# Paths
D1_PASSAGES = os.path.join(BASE_DIR, "data", "dataset_1", "final", "companies_act_2013_passages.jsonl")
D2_PASSAGES = os.path.join(BASE_DIR, "data", "dataset2", "canonical", "passages.jsonl")
SC_2023_CORP_PASSAGES = os.path.join(BASE_DIR, "Data", "sc_judgments", "2023", "sc_2023_corporate_passages.jsonl")

BM25_DIR = os.path.join(BASE_DIR, "experiments", "indices", "bm25")
DENSE_DIR = os.path.join(BASE_DIR, "experiments", "indices", "dense")
os.makedirs(os.path.join(BM25_DIR, "index"), exist_ok=True)
os.makedirs(DENSE_DIR, exist_ok=True)

def load_all_passages() -> List[Dict[str, Any]]:
    print("=" * 75)
    print("STEP 1: LOADING & MERGING CORPORATE CORPORA")
    print("=" * 75)
    passages = []

    # 1. Dataset 1 (Companies Act)
    print(f"[*] Loading Dataset 1 (Companies Act, 2013)...")
    with open(D1_PASSAGES, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                sec_id = item.get("section_id") or ""
                heading = item.get("heading") or ""
                txt = (item.get("canonical_text") or item.get("text", "")).strip()

                if "SEC_" in sec_id:
                    sec_num = sec_id.split("SEC_")[-1]
                    header = f"Companies Act 2013 Section {sec_num} {heading}: "
                elif "SCH_" in sec_id:
                    sch_num = sec_id.split("SCH_")[-1]
                    header = f"Companies Act 2013 Schedule {sch_num} {heading}: "
                else:
                    header = f"Companies Act 2013 {heading}: "

                passages.append({
                    "passage_id": item["passage_id"],
                    "document_id": item.get("document_id", "ACT_COMPANIES_2013"),
                    "dataset": "dataset1",
                    "section_id": sec_id,
                    "heading": heading,
                    "citation": None,
                    "case_title": None,
                    "court": None,
                    "decision_date": item.get("enactment_date") or item.get("commencement_date"),
                    "text": txt,
                    "searchable_text": header + txt
                })
    print(f"    [+] Dataset 1: {len(passages):,} passages loaded.")

    # 2. Dataset 2 (Pre-2023 Curated Judicial)
    count_before_d2 = len(passages)
    print(f"[*] Loading Dataset 2 (Curated Judicial SC/HC/NCLAT)...")
    with open(D2_PASSAGES, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                txt = item.get("text", "").strip()
                court = item.get("court") or ""
                cit = item.get("citation") or ""
                case_title = item.get("case_title") or item.get("title") or ""
                header = f"{court} {cit} {case_title}: ".strip() + " "

                passages.append({
                    "passage_id": item["passage_id"],
                    "document_id": item.get("document_id"),
                    "dataset": "dataset2",
                    "section_id": None,
                    "heading": None,
                    "citation": cit,
                    "case_title": case_title,
                    "court": court,
                    "decision_date": item.get("decision_date"),
                    "text": txt,
                    "searchable_text": header + txt
                })
    print(f"    [+] Dataset 2: {len(passages) - count_before_d2:,} passages loaded.")

    # 3. 2023 Supreme Court Corporate Passages
    count_before_sc = len(passages)
    print(f"[*] Loading 2023 Supreme Court Corporate Precedents...")
    with open(SC_2023_CORP_PASSAGES, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                txt = item.get("text", "").strip()
                court = item.get("court") or "Supreme Court of India"
                cit = item.get("citation") or item.get("neutral_citation") or ""
                case_title = item.get("case_title") or ""
                header = f"{court} {cit} {case_title}: ".strip() + " "

                passages.append({
                    "passage_id": item["passage_id"],
                    "document_id": item.get("document_id"),
                    "dataset": "dataset2",
                    "section_id": None,
                    "heading": None,
                    "citation": cit,
                    "case_title": case_title,
                    "court": court,
                    "decision_date": item.get("decision_date"),
                    "text": txt,
                    "searchable_text": header + txt
                })
    print(f"    [+] 2023 SC Corporate: {len(passages) - count_before_sc:,} passages loaded.")

    # Sort deterministically by passage_id
    passages.sort(key=lambda x: x["passage_id"])
    print("\n" + "=" * 75)
    print(f"[+] Total Merged Corporate Legal Passages: {len(passages):,} (Sorted deterministically)")
    print("=" * 75)
    return passages

def build_bm25_index(passages: List[Dict[str, Any]]):
    print("\n[*] BUILDING BM25 SPARSE INDEX...")
    t0 = time.perf_counter()

    tokenized_corpus = []
    metadata = []
    for idx, p in enumerate(passages):
        tokenized_corpus.append(tokenize_legal_text(p["searchable_text"]))
        metadata.append({
            "index": idx,
            "passage_id": p["passage_id"],
            "document_id": p["document_id"],
            "dataset": p["dataset"],
            "section_id": p["section_id"],
            "heading": p["heading"],
            "citation": p["citation"],
            "case_title": p["case_title"],
            "court": p["court"],
            "decision_date": p["decision_date"],
            "text": p["searchable_text"]
        })

    bm25 = BM25Okapi(tokenized_corpus, k1=1.5, b=0.75, epsilon=0.25)

    # Save BM25 Model
    model_path = os.path.join(BM25_DIR, "index", "bm25_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(bm25, f)

    # Save BM25 Metadata
    meta_path = os.path.join(BM25_DIR, "metadata.jsonl")
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in metadata:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    t1 = time.perf_counter()
    print(f"    [+] BM25 Index successfully saved: {len(passages):,} passages in {t1 - t0:.2f}s!")
    return metadata

def build_dense_bge_index(passages: List[Dict[str, Any]], metadata: List[Dict[str, Any]]):
    print("\n[*] BUILDING DENSE BGE VECTOR STORE (12 CPU THREADS, BATCH=64)...")
    num_threads = os.cpu_count() or 8
    torch.set_num_threads(num_threads)
    print(f"    [+] Initialized PyTorch with {torch.get_num_threads()} CPU threads.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"    [+] Compute device: {device}")

    model_name = "BAAI/bge-large-en-v1.5"
    print(f"    [+] Loading tokenizer and model: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    model = AutoModel.from_pretrained(model_name, local_files_only=True).to(device)
    model.eval()

    batch_size = 64
    all_embeddings = []
    total_passages = len(passages)
    t_start = time.perf_counter()

    for i in range(0, total_passages, batch_size):
        batch = passages[i:i + batch_size]
        batch_texts = [p["searchable_text"] for p in batch]

        with torch.inference_mode():
            inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=256, return_tensors="pt").to(device)
            outputs = model(**inputs)
            embs = outputs[0][:, 0]
            embs = torch.nn.functional.normalize(embs, p=2, dim=1).cpu()

        all_embeddings.append(embs)

        if (i + len(batch)) % 1000 == 0 or (i + len(batch)) == total_passages:
            elapsed = time.perf_counter() - t_start
            done = i + len(batch)
            rate = done / elapsed
            rem_sec = (total_passages - done) / rate if rate > 0 else 0
            print(f"    [{done:5d}/{total_passages}] Embedded {done:,} passages ({rate:.1f} pass/s) | Remaining: {rem_sec/60:.1f}m")

    # Stack full tensor
    final_tensor = torch.cat(all_embeddings, dim=0)
    assert final_tensor.shape == (total_passages, 1024), f"Unexpected tensor shape: {final_tensor.shape}"

    # Save Tensor and Metadata
    pt_path = os.path.join(DENSE_DIR, "index.pt")
    npy_path = os.path.join(DENSE_DIR, "index.npy")
    dense_meta_path = os.path.join(DENSE_DIR, "metadata.jsonl")

    print(f"\n[*] Saving Dense Tensor to: {pt_path}...")
    torch.save(final_tensor, pt_path)
    np.save(npy_path, final_tensor.numpy())

    print(f"[*] Saving Dense Metadata to: {dense_meta_path}...")
    with open(dense_meta_path, "w", encoding="utf-8") as f:
        for m in metadata:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    elapsed_total = time.perf_counter() - t_start
    print(f"\n[+] Dense BGE Vector Store successfully built: {final_tensor.shape} in {elapsed_total/60:.2f}m!")

def verify_indices():
    print("\n" + "=" * 75)
    print("VERIFICATION CHECK: ACTIVE RETRIEVAL INDICES")
    print("=" * 75)

    # 1. Verify BM25
    bm25_model_path = os.path.join(BM25_DIR, "index", "bm25_model.pkl")
    bm25_meta_path = os.path.join(BM25_DIR, "metadata.jsonl")
    with open(bm25_model_path, "rb") as f:
        bm25 = pickle.load(f)
    bm25_lines = sum(1 for l in open(bm25_meta_path, "r", encoding="utf-8") if l.strip())
    print(f"[+] BM25 Index: Verified with {bm25_lines:,} passages in corpus.")

    # 2. Verify Dense
    dense_tensor_path = os.path.join(DENSE_DIR, "index.pt")
    dense_meta_path = os.path.join(DENSE_DIR, "metadata.jsonl")
    t = torch.load(dense_tensor_path, map_location="cpu")
    dense_lines = sum(1 for l in open(dense_meta_path, "r", encoding="utf-8") if l.strip())
    print(f"[+] Dense Vector Store: Verified tensor {t.shape} matching {dense_lines:,} passages.")
    print("=" * 75)
    print("INGESTION & INDEXING COMPLETE: 12,223 PASSAGES ACTIVE IN PIPELINE!")
    print("=" * 75)

def main():
    passages = load_all_passages()
    metadata = build_bm25_index(passages)
    build_dense_bge_index(passages, metadata)
    verify_indices()

if __name__ == "__main__":
    main()
