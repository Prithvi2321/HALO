"""
D3-B Failure Audit (Run on the DEV split only, never test).
==========================================================
For each D3-B query it reports:
  - whether the gold passage exists in the index
  - whether it was in the top-5
  - the gold passage's source type (act / landmark judgment / SC 2023)
  - what the top-5 actually were (to spot crowding by 2023 passages)
"""
import os
import json
import sys
import collections

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATASET3 = os.path.join(BASE_DIR, "Data", "dataset3", "canonical", "dataset3_all.jsonl")
if not os.path.exists(DATASET3):
    DATASET3 = os.path.join(BASE_DIR, "data", "dataset3", "canonical", "dataset3_all.jsonl")

INDEX_META = os.path.join(BASE_DIR, "experiments", "indices", "bm25", "metadata.jsonl")

if len(sys.argv) > 1:
    RUN_FILE = sys.argv[1]
else:
    # Default to B5 dev run
    RUN_FILE = os.path.join(BASE_DIR, "experiments", "runs", "b5_reranker", "dev_run_output.jsonl")
    if not os.path.exists(RUN_FILE):
        RUN_FILE = os.path.join(BASE_DIR, "experiments", "runs", "upgraded_dev", "dev_run_output.jsonl")

def read_jsonl(path):
    if not os.path.exists(path):
        print(f"[!] Path not found: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

print(f"[*] Reading Index Metadata: {INDEX_META}")
meta = {m["passage_id"]: m for m in read_jsonl(INDEX_META)}
print(f"[+] Loaded {len(meta)} index passages.")

print(f"[*] Reading Dataset 3: {DATASET3}")
gold = {}
for r in read_jsonl(DATASET3):
    if r.get("benchmark_family") == "D3-B":
        raw = r.get("raw_record", {})
        ids = raw.get("relevant_passage_ids") or raw.get("positive_evidence_ids") or []
        qid = r.get("record_id") or raw.get("query_id")
        gold[qid] = {
            "query": r.get("query_or_claim") or raw.get("query", ""),
            "gold": ids,
            "split": r.get("split") or raw.get("split", "dev")
        }
print(f"[+] Loaded {len(gold)} D3-B gold queries.")

def source_of(pid):
    if not pid:
        return "none"
    m = meta.get(pid, {})
    if "PAS_ACT" in pid or m.get("dataset") == "dataset1":
        return "ACT_2013"
    elif "PAS-JUD-SC-2023" in pid or "2023_" in pid:
        return "SC_2023"
    elif "PAS-JUD" in pid:
        return "LANDMARK_JUDICIAL"
    return m.get("dataset") or "unknown"

print(f"[*] Analyzing Run Output: {RUN_FILE}")
rows, causes = [], collections.Counter()
run_records = read_jsonl(RUN_FILE)

for rec in run_records:
    if rec.get("benchmark_family") != "D3-B":
        continue
    qid = rec.get("query_id") or rec.get("record_id")
    g = gold.get(qid)
    if not g:
        continue
    
    ret_obj = rec.get("retrieval", {})
    top5 = ret_obj.get("retrieved_passage_ids") or ret_obj.get("top5_passage_ids") or []
    if not top5 and "top5_passages" in ret_obj:
        top5 = [p.get("passage_id") for p in ret_obj["top5_passages"]]

    in_index = [p in meta for p in g["gold"]]
    hit = any(p in top5 for p in g["gold"])

    if hit:
        cause = "HIT"
    elif not all(in_index):
        cause = "GOLD_NOT_IN_INDEX"  # data mapping problem
    elif top5 and g["gold"] and collections.Counter(source_of(p) for p in top5).most_common(1)[0][0] != source_of(g["gold"][0]):
        cause = "WRONG_SOURCE_TYPE_DOMINATES"  # crowding by other corpus source
    else:
        cause = "RANKED_BELOW_5_OR_SEMANTIC_MISS"

    causes[cause] += 1
    rows.append({
        "query_id": qid,
        "query": g["query"],
        "cause": cause,
        "gold": g["gold"],
        "gold_source": [source_of(p) for p in g["gold"]],
        "top5": top5,
        "top5_sources": [source_of(p) for p in top5]
    })

print("\n" + "=" * 60)
print("  D3-B DEV AUDIT FAILURE BREAKDOWN")
print("=" * 60)
for r in rows:
    if r["cause"] != "HIT":
        print(f"\n[{r['cause']}] {r['query_id']}")
        print(f"  Q: {r['query']}")
        print(f"  Gold: {r['gold']} ({r['gold_source']})")
        print(f"  Top-5: {r['top5']}")
        print(f"  Top-5 Sources: {r['top5_sources']}")

print("\n" + "=" * 60)
print("AUDIT SUMMARY:", dict(causes), "of", len(rows), "queries")
print("=" * 60)

out_file = os.path.join(BASE_DIR, "experiments", "metrics", "d3b_dev_audit.json")
os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)
print(f"[+] Saved audit breakdown to: {out_file}\n")
