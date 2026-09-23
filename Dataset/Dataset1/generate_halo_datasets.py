import json
import os
import random
import time
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

# =====================================================================
# API CONFIGURATION
# Paste your Gemini API Key directly inside quotes below:
# =====================================================================
API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY) if API_KEY else None

# Primary model and fallback list for high-demand periods
PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]


# --- PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT ---

class RetrievalQuery(BaseModel):
    query: str = Field(description="Synthetic natural language query or legal question based strictly on the text.")
    query_type: str = Field(description="e.g., Exact section lookup, Statutory interpretation, Definition, Exception/proviso")
    difficulty: Literal["easy", "medium", "hard"]
    relevance_grade: Literal["EXACT_MATCH", "PARTIAL_MATCH", "HIGHLY_RELEVANT"]
    reason: str = Field(description="Explanation why this passage satisfies the query.")


class RetrievalDatasetBatch(BaseModel):
    queries: List[RetrievalQuery]


class HardNegativePair(BaseModel):
    query: str = Field(description="Query derived from positive section.")
    hard_negative_passage_id: str = Field(description="The passage ID chosen as a hard negative from candidate pool.")
    negative_reason: str = Field(
        description="Reason for hard negative (e.g., 'Same Act but different section', 'Similar legal terminology', 'Proviso confusion')"
    )
    difficulty: Literal["easy", "medium", "hard"]


class NegativeDatasetBatch(BaseModel):
    hard_negatives: List[HardNegativePair]


# --- HELPER FUNCTIONS ---

def safe_generate_content(contents, schema_cls, temperature=0.2, max_retries=5):
    """
    Executes generate_content with exponential backoff for 503/server errors 
    and handles fallback models if primary model is unavailable.
    """
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS

    for model in models_to_try:
        delay = 2  # initial delay in seconds
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                        temperature=temperature
                    )
                )
                return response, model
            except (ServerError, APIError) as e:
                # Catch 503 or 429 high demand / rate limit errors
                if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                    print(f"[{model}] High demand encountered (Attempt {attempt+1}/{max_retries}). Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise e
        print(f"Model '{model}' remained unavailable after {max_retries} retries. Trying fallback...")

    raise RuntimeError("All configured models are currently experiencing high demand. Please try again later.")


def load_structured_act(file_path: str) -> dict:
    """Load normalized Act JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_sections(act_data: dict) -> List[dict]:
    """Flattens nested Act JSON structure to retrieve individual sections."""
    sections = []
    doc_id = act_data["document_metadata"]["document_id"]
    
    parts = act_data.get("structure", {}).get("parts", [])
    for part in parts:
        for chapter in part.get("chapters", []):
            for section in chapter.get("sections", []):
                full_text_components = []
                for sub in section.get("subsections", []):
                    full_text_components.append(sub.get("text", ""))
                full_text_components.extend(section.get("provisos", []))
                
                sections.append({
                    "document_id": doc_id,
                    "section_id": section["section_id"],
                    "section_number": section["section_number"],
                    "section_title": section["section_title"],
                    "passage_id": section["passage_id"],
                    "text": "\n".join(full_text_components)
                })
    return sections


def assign_split() -> str:
    """Randomly allocates record into isolated 70/15/15 splits."""
    r = random.random()
    if r < 0.70:
        return "train"
    elif r < 0.85:
        return "dev"
    else:
        return "test"


# --- GENERATION PIPELINE ---

def generate_retrieval_dataset_b(section: dict) -> List[dict]:
    """Generates Dataset B (Retrieval Evaluation) records for a section."""
    prompt = f"""
    You are generating a RAG Evaluation Benchmark for Indian Law.
    
    Given this section:
    Section ID: {section['section_id']}
    Title: {section['section_title']}
    Text:
    {section['text']}
    
    Generate 2 realistic user queries that this section directly answers.
    Ensure queries vary in difficulty (easy, medium, hard).
    """
    
    response, used_model = safe_generate_content(
        contents=prompt,
        schema_cls=RetrievalDatasetBatch,
        temperature=0.2
    )
    
    structured_data = RetrievalDatasetBatch.model_validate_json(response.text)
    records = []
    
    for idx, q in enumerate(structured_data.queries):
        split_assignment = assign_split()
        record = {
            "dataset_version": "1.0.0",
            "synthetic": True,
            "created_at": "2026-09-04T20:00:00Z",
            "created_by": used_model,
            "record_id": f"RET_{section['section_id']}_{idx+1:02d}",
            "query_id": f"Q_RET_{section['section_id']}_{idx+1:02d}",
            "query": q.query,
            "query_type": q.query_type,
            "difficulty": q.difficulty,
            "expected_document_ids": [section["document_id"]],
            "expected_section_ids": [section["section_id"]],
            "expected_passage_ids": [section["passage_id"]],
            "relevance_grade": q.relevance_grade,
            "reason": q.reason,
            "split": split_assignment
        }
        records.append(record)
        
    return records


def generate_negative_retrieval_dataset_c(target_section: dict, candidate_sections: List[dict]) -> List[dict]:
    """Generates Dataset C (Negative Retrieval) hard negative records."""
    other_candidates = [
        {"passage_id": c["passage_id"], "title": c["section_title"], "text": c["text"][:200]}
        for c in candidate_sections if c["section_id"] != target_section["section_id"]
    ][:5]
    
    prompt = f"""
    Target Positive Section:
    Passage ID: {target_section['passage_id']}
    Title: {target_section['section_title']}
    Text: {target_section['text']}
    
    Candidate Negative Passages:
    {json.dumps(other_candidates, indent=2)}
    
    Formulate a query where Target Positive Section is the correct answer, 
    but ONE of candidate negative passages would act as a confusing 'Hard Negative' 
    due to overlapping keywords or similar legal concepts.
    """
    
    response, used_model = safe_generate_content(
        contents=prompt,
        schema_cls=NegativeDatasetBatch,
        temperature=0.3
    )
    
    structured_data = NegativeDatasetBatch.model_validate_json(response.text)
    records = []
    
    for idx, neg in enumerate(structured_data.hard_negatives):
        record = {
            "dataset_version": "1.0.0",
            "synthetic": True,
            "created_at": "2026-09-04T20:00:00Z",
            "created_by": used_model,
            "record_id": f"NEG_{target_section['section_id']}_{idx+1:02d}",
            "query_id": f"Q_NEG_{target_section['section_id']}_{idx+1:02d}",
            "query": neg.query,
            "positive_passage_ids": [target_section["passage_id"]],
            "hard_negative_passage_ids": [neg.hard_negative_passage_id],
            "negative_reason": neg.negative_reason,
            "difficulty": neg.difficulty
        }
        records.append(record)
        
    return records


# --- MAIN EXECUTION ---

def run_pipeline(input_act_json: str, output_dir: str = "halo_datasets"):
    """Runs extraction and saves output in standard JSONL format."""
    os.makedirs(f"{output_dir}/retrieval", exist_ok=True)
    os.makedirs(f"{output_dir}/negative_retrieval", exist_ok=True)
    
    print(f"Loading {input_act_json}...")
    act_data = load_structured_act(input_act_json)
    sections = extract_sections(act_data)
    print(f"Extracted {len(sections)} sections from corpus.")
    
    retrieval_records = {"train": [], "dev": [], "test": []}
    negative_records = []
    
    for sec in sections:
        print(f"Processing Section {sec['section_id']}...")
        
        # Dataset B
        ret_records = generate_retrieval_dataset_b(sec)
        for r in ret_records:
            retrieval_records[r["split"]].append(r)
            
        # Dataset C
        if len(sections) > 1:
            neg_records = generate_negative_retrieval_dataset_c(sec, sections)
            negative_records.extend(neg_records)

    # Write Dataset B Files
    for split in ["train", "dev", "test"]:
        out_path = f"{output_dir}/retrieval/retrieval_{split}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in retrieval_records[split]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Saved {len(retrieval_records[split])} records to {out_path}")
        
    # Write Dataset C File
    neg_path = f"{output_dir}/negative_retrieval/negative_retrieval.jsonl"
    with open(neg_path, "w", encoding="utf-8") as f:
        for rec in negative_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Saved {len(negative_records)} records to {neg_path}")


if __name__ == "__main__":
    run_pipeline("sample_act.json")