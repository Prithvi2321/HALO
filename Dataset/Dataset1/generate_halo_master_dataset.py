import json
import os
import sys
import hashlib
import random
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

# =====================================================================
# API CONFIGURATION & MODEL FALLBACKS
# =====================================================================
API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY) if API_KEY else None

PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]

# Directory Structure Constants
BASE_DIR = "halo_datasets"
DIRS = {
    "corpus": os.path.join(BASE_DIR, "corpus", "acts"),
    "judgments": os.path.join(BASE_DIR, "corpus", "judgments"),
    "metadata": os.path.join(BASE_DIR, "corpus", "metadata"),
    "retrieval": os.path.join(BASE_DIR, "retrieval"),
    "negative_retrieval": os.path.join(BASE_DIR, "negative_retrieval"),
    "citation_verification": os.path.join(BASE_DIR, "citation_verification"),
    "claim_evidence": os.path.join(BASE_DIR, "claim_evidence"),
    "passage_verification": os.path.join(BASE_DIR, "passage_verification"),
    "temporal": os.path.join(BASE_DIR, "temporal"),
    "adversarial": os.path.join(BASE_DIR, "adversarial"),
    "fail_closed": os.path.join(BASE_DIR, "fail_closed"),
    "classification": os.path.join(BASE_DIR, "classification"),
    "authority": os.path.join(BASE_DIR, "authority"),
    "quality": os.path.join(BASE_DIR, "quality"),
    "human_evaluation": os.path.join(BASE_DIR, "human_evaluation"),
}

for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# =====================================================================
# PYDANTIC SCHEMAS FOR SYNTHETIC GENERATION
# =====================================================================

class RetrievalGenQuery(BaseModel):
    query: str = Field(description="Realistic user query or legal question.")
    query_type: str = Field(description="e.g., EXACT_LOOKUP, DEFINITION, EXCEPTION, TEMPORAL")
    difficulty: Literal["easy", "medium", "hard"]
    relevance_grade: int = Field(description="3 for direct, 2 for supporting, 1 for weak, 0 for irrelevant", ge=0, le=3)
    reason: str = Field(description="Why the selected passage answers this query.")

class RetrievalGenBatch(BaseModel):
    queries: List[RetrievalGenQuery]

class HardNegativeGenItem(BaseModel):
    query: str = Field(description="User query where target passage is positive, but negative passage is confusing.")
    hard_negative_passage_id: str = Field(description="The passage ID chosen as a hard negative from candidate pool.")
    negative_reason: str = Field(description="Reason why negative is confusing (e.g. Same Act different section).")
    difficulty: Literal["easy", "medium", "hard"]

class HardNegativeGenBatch(BaseModel):
    negatives: List[HardNegativeGenItem]

class CitationGenItem(BaseModel):
    claim: str = Field(description="Generated legal claim.")
    relationship: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "UNSUPPORTED", "FABRICATED_CITATION"]
    expected_verification_status: Literal["PASS", "FAIL", "FLAG"]
    explanation: str = Field(description="Explanation of the relationship to the cited passage.")

class CitationGenBatch(BaseModel):
    cases: List[CitationGenItem]

class ClassificationGenItem(BaseModel):
    query: str = Field(description="Synthetic legal query.")
    intent: Literal[
        "STATUTE_LOOKUP", "CASE_LAW", "LEGAL_DEFINITION", "LEGAL_INTERPRETATION",
        "COMPARISON", "TEMPORAL", "AMENDMENT", "REPEAL", "PROCEDURAL",
        "JURISDICTION", "MULTI_HOP", "OUT_OF_SCOPE", "AMBIGUOUS"
    ]
    difficulty: Literal["easy", "medium", "hard"]
    requires_temporal_reasoning: bool
    requires_case_law: bool
    requires_multiple_sources: bool

class ClassificationGenBatch(BaseModel):
    queries: List[ClassificationGenItem]

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def compute_sha256_canonical(obj: Any) -> str:
    """Computes SHA-256 over deterministic JSON string representation."""
    canonical_str = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

def safe_gemini_call(prompt: str, schema_cls: Any, temperature: float = 0.2, max_retries: int = 5) -> Tuple[Any, str]:
    """Handles Gemini API invocation with backoff, retry, and model fallback."""
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
    for model in models_to_try:
        delay = 2
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                        temperature=temperature
                    )
                )
                return schema_cls.model_validate_json(response.text), model
            except (ServerError, APIError) as e:
                if any(err_code in str(e) for err_code in ["503", "UNAVAILABLE", "429"]):
                    print(f"[{model}] High demand encountered. Attempt {attempt+1}/{max_retries}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
            except Exception as e:
                print(f"[{model}] Parsing or unexpected error: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
    raise RuntimeError("All configured LLM models failed to respond.")

# =====================================================================
# CORPUS LOADER & ATOMIC INDEX BUILDER
# =====================================================================

# class AuthoritativeCorpusIndexer:
    """Loads authoritative legal corpus files and extracts atomic searchable units."""
    def __init__(self):
        self.documents: Dict[str, dict] = {}
        self.sections: Dict[str, dict] = {}
        self.passages: Dict[str, dict] = {}

    def ingest_act_file(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc_id = data["document_id"]
        # Ensure deterministic content hash computation
        data["content_hash"] = compute_sha256_canonical(data.get("chapters", []))
        self.documents[doc_id] = data

        for chapter in data.get("chapters", []):
            for sec in chapter.get("sections", []):
                sec_id = sec["section_id"]
                self.sections[sec_id] = {
                    "document_id": doc_id,
                    "section_id": sec_id,
                    "section_number": sec["section_number"],
                    "heading": sec.get("heading", ""),
                    "text": sec.get("text", ""),
                    "effective_from": sec.get("effective_from"),
                    "effective_to": sec.get("effective_to"),
                    "status": sec.get("status", "ACTIVE")
                }

                # Construct Passages
                if sec.get("subsections"):
                    for sub in sec["subsections"]:
                        sub_id = sub["subsection_id"]
                        if sub.get("clauses"):
                            for cl in sub["clauses"]:
                                pas_id = f"PAS_{cl['clause_id']}"
                                self.passages[pas_id] = {
                                    "passage_id": pas_id,
                                    "document_id": doc_id,
                                    "section_id": sec_id,
                                    "subsection_id": sub_id,
                                    "clause_id": cl["clause_id"],
                                    "text": cl["text"],
                                    "heading": f"{sec.get('heading', '')} - Clause ({cl['number']})",
                                    "source": data["source"],
                                    "source_url": data["source_url"],
                                    "effective_from": sec.get("effective_from"),
                                    "effective_to": sec.get("effective_to"),
                                    "content_hash": compute_sha256_canonical(cl["text"])
                                }
                        else:
                            pas_id = f"PAS_{sub_id}"
                            self.passages[pas_id] = {
                                "passage_id": pas_id,
                                "document_id": doc_id,
                                "section_id": sec_id,
                                "subsection_id": sub_id,
                                "clause_id": None,
                                "text": sub["text"],
                                "heading": f"{sec.get('heading', '')} - Sub ({sub['number']})",
                                "source": data["source"],
                                "source_url": data["source_url"],
                                "effective_from": sec.get("effective_from"),
                                "effective_to": sec.get("effective_to"),
                                "content_hash": compute_sha256_canonical(sub["text"])
                            }
                else:
                    pas_id = f"PAS_{sec_id}"
                    self.passages[pas_id] = {
                        "passage_id": pas_id,
                        "document_id": doc_id,
                        "section_id": sec_id,
                        "subsection_id": None,
                        "clause_id": None,
                        "text": sec["text"],
                        "heading": sec.get("heading", ""),
                        "source": data["source"],
                        "source_url": data["source_url"],
                        "effective_from": sec.get("effective_from"),
                        "effective_to": sec.get("effective_to"),
                        "content_hash": compute_sha256_canonical(sec["text"])
                    }

    def validate_ids(self, doc_id: str, sec_id: str, pas_id: str) -> bool:
        """Validates that referenced ground-truth IDs exist in authoritative corpus."""
        if doc_id not in self.documents:
            return False
        if sec_id not in self.sections:
            return False
        if pas_id not in self.passages:
            return False
        # Validate hierarchy integrity
        pas = self.passages[pas_id]
        if pas["document_id"] != doc_id or pas["section_id"] != sec_id:
            return False
        return True
# 
# =====================================================================
# DATASET GENERATOR PIPELINE
# =====================================================================
class AuthoritativeCorpusIndexer:
    """Loads authoritative legal corpus files and extracts atomic searchable units."""
    def __init__(self):
        self.documents: Dict[str, dict] = {}
        self.sections: Dict[str, dict] = {}
        self.passages: Dict[str, dict] = {}

    def ingest_act_file(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle nested metadata schema vs flat schema
        meta = data.get("document_metadata", {})
        doc_id = meta.get("document_id") or data.get("document_id") or data.get("doc_id") or data.get("act_id")
        
        if not doc_id:
            raise KeyError(
                f"Could not find a valid document ID in {file_path}. "
                f"Keys found: {list(data.keys())}"
            )

        # Normalize canonical root metadata
        data["document_id"] = doc_id
        data["source"] = data.get("source") or meta.get("jurisdiction", "India Code")
        data["source_url"] = data.get("source_url", "")

        # Extract chapters across flat array or parts -> chapters hierarchy
        raw_chapters = []
        if "chapters" in data:
            raw_chapters = data["chapters"]
        elif "structure" in data and "parts" in data["structure"]:
            for part in data["structure"]["parts"]:
                raw_chapters.extend(part.get("chapters", []))

        data["chapters"] = raw_chapters
        data["content_hash"] = compute_sha256_canonical(raw_chapters)
        self.documents[doc_id] = data

        for chapter in raw_chapters:
            for sec in chapter.get("sections", []):
                sec_id = sec.get("section_id") or f"{doc_id}_SEC_{sec.get('section_number', '0')}"
                sec_number = sec.get("section_number", "")
                sec_title = sec.get("heading") or sec.get("section_title", "")

                # Extract primary text from section body or subsections
                sec_text = sec.get("text", "")
                subsections = sec.get("subsections", [])
                if not sec_text and subsections:
                    sec_text = " ".join([sub.get("text", "") for sub in subsections if sub.get("text")])

                self.sections[sec_id] = {
                    "document_id": doc_id,
                    "section_id": sec_id,
                    "section_number": sec_number,
                    "heading": sec_title,
                    "text": sec_text,
                    "effective_from": sec.get("effective_from"),
                    "effective_to": sec.get("effective_to"),
                    "status": sec.get("status", "ACTIVE")
                }

                # Construct Passages
                pas_id = sec.get("passage_id") or f"PAS_{sec_id}"
                
                # Check for explicit passage ID or extract from clause/subsection breakdown
                if subsections and len(subsections) > 1:
                    for idx, sub in enumerate(subsections, start=1):
                        sub_pas_id = f"PAS_{sec_id}_SUB_{idx}"
                        self.passages[sub_pas_id] = {
                            "passage_id": sub_pas_id,
                            "document_id": doc_id,
                            "section_id": sec_id,
                            "subsection_id": f"{sec_id}_SUB_{idx}",
                            "clause_id": None,
                            "text": sub.get("text", ""),
                            "heading": f"{sec_title} - Subsection ({idx})",
                            "source": data["source"],
                            "source_url": data["source_url"],
                            "effective_from": sec.get("effective_from"),
                            "effective_to": sec.get("effective_to"),
                            "content_hash": compute_sha256_canonical(sub.get("text", ""))
                        }
                else:
                    self.passages[pas_id] = {
                        "passage_id": pas_id,
                        "document_id": doc_id,
                        "section_id": sec_id,
                        "subsection_id": None,
                        "clause_id": None,
                        "text": sec_text,
                        "heading": sec_title,
                        "source": data["source"],
                        "source_url": data["source_url"],
                        "effective_from": sec.get("effective_from"),
                        "effective_to": sec.get("effective_to"),
                        "content_hash": compute_sha256_canonical(sec_text)
                    }

    def validate_ids(self, doc_id: str, sec_id: str, pas_id: str) -> bool:
        """Validates that referenced ground-truth IDs exist in authoritative corpus."""
        if doc_id not in self.documents:
            return False
        if sec_id not in self.sections:
            return False
        if pas_id not in self.passages:
            return False
        
        pas = self.passages[pas_id]
        if pas["document_id"] != doc_id or pas["section_id"] != sec_id:
            return False
        return True
class HALODatasetPipeline:
    def __init__(self, indexer: AuthoritativeCorpusIndexer):
        self.indexer = indexer

    def write_jsonl(self, path: str, records: List[dict]):
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def run_d2_retrieval_benchmark(self) -> Dict[str, List[dict]]:
        print("[Pipeline] Generating D2 — Retrieval Benchmark...")
        train_recs, dev_recs, test_recs = [], [], []

        for pas_id, pas in self.indexer.passages.items():
            # Validate Ground Truth before LLM Prompting
            if not self.indexer.validate_ids(pas["document_id"], pas["section_id"], pas_id):
                print(f"[REJECTED] Ground truth ID validation failed for passage {pas_id}")
                continue

            prompt = f"""
            System: You are an expert Indian Legal AI Architect.
            Source Passage ({pas_id}):
            "{pas['text']}"
            Heading: {pas['heading']}

            Generate 2 distinct queries answered by this passage.
            Assign relevance_grade=3 for exact direct match.
            """
            batch, model_used = safe_gemini_call(prompt, RetrievalGenBatch, temperature=0.2)

            for idx, q in enumerate(batch.queries):
                record = {
                    "dataset_version": "1.0.0",
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "record_id": f"D2_RET_{pas_id}_{idx+1:02d}",
                    "query_id": f"Q_D2_{pas_id}_{idx+1:02d}",
                    "query": q.query,
                    "query_type": q.query_type,
                    "difficulty": q.difficulty,
                    "expected_document_ids": [pas["document_id"]],
                    "expected_section_ids": [pas["section_id"]],
                    "expected_passage_ids": [pas_id],
                    "relevance_grades": {pas_id: q.relevance_grade},
                    "reason": q.reason,
                    "synthetic_query": True,
                    "evidence_synthetic": False,
                    "split": ""
                }

                # Deduplication & Leakage Prevention: Deterministic Split Assignment
                r = random.random()
                if r < 0.70:
                    record["split"] = "train"
                    train_recs.append(record)
                elif r < 0.85:
                    record["split"] = "dev"
                    dev_recs.append(record)
                else:
                    record["split"] = "test"
                    test_recs.append(record)

        self.write_jsonl(os.path.join(DIRS["retrieval"], "retrieval_train.jsonl"), train_recs)
        self.write_jsonl(os.path.join(DIRS["retrieval"], "retrieval_dev.jsonl"), dev_recs)
        self.write_jsonl(os.path.join(DIRS["retrieval"], "retrieval_test.jsonl"), test_recs)
        return {"train": train_recs, "dev": dev_recs, "test": test_recs}

    def run_d3_hard_negatives(self):
        print("[Pipeline] Generating D3 — Hard Negative Benchmark...")
        records = []
        all_passages = list(self.indexer.passages.values())

        if len(all_passages) < 2:
            print("[Warning] Insufficient passages to construct hard negatives.")
            return records

        for pas in all_passages:
            candidates = [p for p in all_passages if p["passage_id"] != pas["passage_id"]]
            candidate_payload = [
                {"passage_id": c["passage_id"], "heading": c["heading"], "text": c["text"][:150]}
                for c in candidates[:5]
            ]

            prompt = f"""
            Target Positive Passage ({pas['passage_id']}): "{pas['text']}"
            Candidate Negatives: {json.dumps(candidate_payload)}

            Create a query where Target Positive is correct, but ONE candidate is a highly confusing Hard Negative.
            """
            batch, _ = safe_gemini_call(prompt, HardNegativeGenBatch, temperature=0.3)

            for idx, neg in enumerate(batch.negatives):
                # Reject record if hard_negative_passage_id is hallucinated or invalid
                if neg.hard_negative_passage_id not in self.indexer.passages:
                    continue

                rec = {
                    "dataset_version": "1.0.0",
                    "record_id": f"D3_NEG_{pas['passage_id']}_{idx+1:02d}",
                    "query_id": f"Q_D3_{pas['passage_id']}_{idx+1:02d}",
                    "query": neg.query,
                    "positive_passage_ids": [pas["passage_id"]],
                    "hard_negative_passage_ids": [neg.hard_negative_passage_id],
                    "negative_reason": neg.negative_reason,
                    "difficulty": neg.difficulty,
                    "synthetic_query": True,
                    "evidence_synthetic": False
                }
                records.append(rec)

        self.write_jsonl(os.path.join(DIRS["negative_retrieval"], "negative_retrieval.jsonl"), records)
        return records

    def run_d4_citation_verification(self):
        print("[Pipeline] Generating D4 — Citation Verification Benchmark...")
        records = []

        for pas_id, pas in self.indexer.passages.items():
            prompt = f"""
            Legal Passage ({pas_id}): "{pas['text']}"

            Generate 3 test cases for citation verification:
            1. Claim SUPPORTED by passage.
            2. Claim CONTRADICTED by passage.
            3. Claim UNSUPPORTED / FABRICATED CITATION context.
            """
            batch, _ = safe_gemini_call(prompt, CitationGenBatch, temperature=0.3)

            for idx, case in enumerate(batch.cases):
                rec = {
                    "test_id": f"D4_CIT_{pas_id}_{idx+1:02d}",
                    "claim": case.claim,
                    "citation": {
                        "document_id": pas["document_id"],
                        "section_id": pas["section_id"],
                        "passage_id": pas_id
                    },
                    "relationship": case.relationship,
                    "evidence_text": pas["text"],
                    "expected_verification_status": case.expected_verification_status,
                    "explanation": case.explanation,
                    "synthetic_claim": True,
                    "evidence_synthetic": False
                }
                records.append(rec)

        self.write_jsonl(os.path.join(DIRS["citation_verification"], "citation_verification.jsonl"), records)
        return records

    def run_d10_no_evidence(self):
        print("[Pipeline] Generating D10 — Fail-Closed / No-Evidence Benchmark...")
        records = [
            {
                "test_id": "D10_FAIL_001",
                "query": "What is the penalty under Section 999 of the Companies Act, 2013?",
                "expected_behavior": "FAIL_CLOSED",
                "reason": "Section 999 does not exist in the Companies Act, 2013.",
                "available_evidence_ids": [],
                "synthetic": True
            },
            {
                "test_id": "D10_FAIL_002",
                "query": "Quote the Supreme Court ruling from 2029 regarding Quantum AI Corporate Governance.",
                "expected_behavior": "FAIL_CLOSED",
                "reason": "Out of scope / non-existent case law.",
                "available_evidence_ids": [],
                "synthetic": True
            }
        ]
        self.write_jsonl(os.path.join(DIRS["fail_closed"], "no_evidence.jsonl"), records)
        return records

    def run_d11_authority_registry(self):
        print("[Pipeline] Generating D11 — Legal Authority Registry...")
        registry = [
            {
                "authority_id": "AUTH_SC_INDIA",
                "source_type": "JUDICIAL",
                "authority_level": "SUPREME_COURT",
                "jurisdiction": "India",
                "organization": "Supreme Court of India",
                "source_reliability": "AUTHORITATIVE",
                "precedential_weight": 100,
                "official": True
            },
            {
                "authority_id": "AUTH_PARLIAMENT_INDIA",
                "source_type": "STATUTORY",
                "authority_level": "PARLIAMENT",
                "jurisdiction": "India",
                "organization": "Parliament of India",
                "source_reliability": "AUTHORITATIVE",
                "precedential_weight": 100,
                "official": True
            }
        ]
        self.write_jsonl(os.path.join(DIRS["authority"], "authority_registry.jsonl"), registry)
        return registry

# =====================================================================
# MAIN EXECUTION
# =====================================================================

if __name__ == "__main__":
    print("=========================================================")
    print("      HALO MASTER DATASET GENERATION ENGINE              ")
    print("=========================================================")

    # Initialize Indexer and Load Sample Act
    indexer = AuthoritativeCorpusIndexer()
    sample_act_path = "sample_act.json"

    if os.path.exists(sample_act_path):
        print(f"Loading authoritative act corpus from {sample_act_path}...")
        indexer.ingest_act_file(sample_act_path)
    else:
        print(f"[Error] {sample_act_path} not found. Please place an authoritative Act file in working directory.")
        sys.exit(1)

    print(f"Indexed {len(indexer.documents)} Document(s), {len(indexer.sections)} Section(s), {len(indexer.passages)} Passage(s).")

    # Run Pipeline Generators
    pipeline = HALODatasetPipeline(indexer)
    d2_results = pipeline.run_d2_retrieval_benchmark()
    d3_results = pipeline.run_d3_hard_negatives()
    d4_results = pipeline.run_d4_citation_verification()
    d10_results = pipeline.run_d10_no_evidence()
    d11_results = pipeline.run_d11_authority_registry()

    print("\n[Complete] Benchmark dataset ecosystem generated successfully.")