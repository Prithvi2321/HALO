"""
Pydantic Models for HALO Dataset 3 Benchmark Suite
==================================================
Covers all 13 benchmark sub-families:
  D3-A: Retrieval Benchmark
  D3-B: Paraphrased / Semantic Retrieval
  D3-C: Hard Negative Retrieval
  D3-D: Grounded Answer Benchmark
  D3-E: Citation Existence Benchmark
  D3-F: Citation Metadata Mismatch
  D3-G: Passage-Level Fabrication
  D3-H: Fail-Closed / No-Evidence Benchmark
  D3-I: Ambiguous Query Benchmark
  D3-J: Temporal / Historical Law Benchmark
  D3-K: Conflict / Multi-Authority Benchmark
  D3-L: Out-of-Domain Benchmark
  D3-M: Adversarial Prompt Benchmark
"""

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# D3-A, D3-B, D3-C: Retrieval Records
# -----------------------------------------------------------------------------
class RetrievalRecord(BaseModel):
    query_id: str = Field(description="Unique identifier, e.g. D3_RET_000001")
    benchmark_family: Literal["D3-A", "D3-B", "D3-C"] = Field(description="Benchmark sub-family")
    query: str = Field(description="Natural language query or legal inquiry")
    query_type: str = Field(description="STATUTORY_LOOKUP, STATUTORY_INTERPRETATION, CASE_HOLDING, PARAPHRASED_SEMANTIC, HARD_NEGATIVE")
    difficulty: Literal["easy", "medium", "hard", "adversarial"]
    source_scope: List[str] = Field(description="List of source datasets, e.g. ['dataset1'], ['dataset2'], or ['dataset1', 'dataset2']")
    positive_evidence_ids: List[str] = Field(description="Section IDs or Judgment IDs forming primary positive evidence")
    relevant_document_ids: List[str] = Field(default_factory=list, description="Associated document IDs")
    relevant_passage_ids: List[str] = Field(description="Passage IDs in Dataset 1 or Dataset 2 that satisfy the query")
    hard_negative_passage_ids: List[str] = Field(default_factory=list, description="Authentic confounding negative passage IDs")
    negative_reason: Optional[str] = Field(default=None, description="Explanation why hard negatives are deceptive yet non-relevant")
    dataset_source: Literal["dataset1", "dataset2", "hybrid"]
    evidence_text: str = Field(description="Verbatim text of the primary supporting evidence passage")
    evidence_type: Literal["statute", "judgment", "hybrid"]
    annotation_status: Literal["VALIDATED", "HUMAN_REVIEWED", "REJECTED"] = "VALIDATED"
    split: Literal["train", "dev", "test"]


# -----------------------------------------------------------------------------
# D3-D: Grounded Answer Record
# -----------------------------------------------------------------------------
class GroundingRecord(BaseModel):
    query_id: str = Field(description="Unique identifier, e.g. D3_GROUND_000001")
    benchmark_family: Literal["D3-D"] = "D3-D"
    query: str = Field(description="Grounded inquiry requiring synthesized legal response")
    gold_answer: str = Field(description="Authoritative, legally sound answer synthesized strictly from evidence")
    acceptable_answer_points: List[str] = Field(description="Atomic factual points required for full score")
    unacceptable_claims: List[str] = Field(default_factory=list, description="Known hallucinated or inverted claims that penalize score")
    required_evidence_ids: List[str] = Field(description="Passage IDs strictly required to establish factual sufficiency")
    source_dataset: Literal["dataset1", "dataset2", "hybrid"]
    difficulty: Literal["easy", "medium", "hard", "adversarial"]
    split: Literal["train", "dev", "test"] = "test"


# -----------------------------------------------------------------------------
# D3-E, D3-F: Citation Verification Record
# -----------------------------------------------------------------------------
class CitationVerificationRecord(BaseModel):
    test_id: str = Field(description="Unique identifier, e.g. D3_CIT_000001")
    benchmark_family: Literal["D3-E", "D3-F"] = Field(description="D3-E (Existence) or D3-F (Metadata Mismatch)")
    claim: str = Field(description="Legal proposition or sentence containing the legal citation")
    cited_case_name: str = Field(description="Case title as claimed")
    cited_citation: str = Field(description="Reporter citation as claimed")
    cited_court: str = Field(description="Court or tribunal as claimed")
    cited_date: str = Field(description="Judgment date as claimed")
    cited_paragraph: Optional[str] = Field(default=None, description="Paragraph index as claimed")
    expected_verification_status: Literal["SUPPORTED", "FLAGGED", "REJECTED"]
    failure_type: Literal[
        "AUTHENTIC_RECORD",
        "FABRICATED_CASE",
        "FABRICATED_CITATION",
        "CITATION_SWAP",
        "WRONG_COURT",
        "WRONG_DATE",
        "NON_EXISTENT_PARAGRAPH"
    ]
    real_source_ids: List[str] = Field(default_factory=list, description="Real judgment or passage IDs if grounded, else empty")
    metadata_discrepancy_details: Optional[str] = Field(default=None, description="Detailed explanation of the discrepancy")
    difficulty: Literal["easy", "medium", "hard", "adversarial"]


# -----------------------------------------------------------------------------
# D3-G: Passage-Level Fabrication Record
# -----------------------------------------------------------------------------
class PassageVerificationRecord(BaseModel):
    test_id: str = Field(description="Unique identifier, e.g. D3_PAS_000001")
    benchmark_family: Literal["D3-G"] = "D3-G"
    claim: str = Field(description="Plausible-sounding claim with real case metadata")
    cited_case_name: str = Field(description="Valid real case title from Dataset 2")
    cited_citation: str = Field(description="Valid real citation from Dataset 2")
    cited_court: str = Field(description="Valid real court from Dataset 2")
    cited_date: str = Field(description="Valid real date from Dataset 2")
    cited_passage_id: str = Field(description="Authentic passage ID in Dataset 2")
    cited_passage_text: str = Field(description="Verbatim passage text demonstrating the absence/contradiction of the claim")
    fabricated_proposition: str = Field(description="The specific proposition asserted in the claim but absent from the text")
    expected_verification_status: Literal["PASSAGE_UNSUPPORTED", "REJECTED"] = "PASSAGE_UNSUPPORTED"
    failure_type: Literal["UNSUPPORTED_PROPOSITION", "LEGAL_INVERSION"] = "UNSUPPORTED_PROPOSITION"
    real_source_ids: List[str] = Field(description="The authentic judgment and passage IDs")
    difficulty: Literal["easy", "medium", "hard", "adversarial"] = "adversarial"


# -----------------------------------------------------------------------------
# D3-H through D3-M: Robustness & Adversarial Record
# -----------------------------------------------------------------------------
class RobustnessRecord(BaseModel):
    test_id: str = Field(description="Unique identifier, e.g. D3_ROB_000001")
    benchmark_family: Literal["D3-H", "D3-I", "D3-J", "D3-K", "D3-L", "D3-M"]
    query: str = Field(description="Input query, ambiguous prompt, or adversarial injection")
    expected_behavior: Literal[
        "FAIL_CLOSED",
        "CLARIFICATION_REQUIRED",
        "TEMPORAL_DISAMBIGUATION",
        "CONFLICT_DETECTED",
        "OUT_OF_SCOPE",
        "BYPASS_REJECTED"
    ]
    available_evidence_ids: List[str] = Field(default_factory=list, description="Supporting passage IDs if available, else empty")
    reason: str = Field(description="Ground-truth justification for expected system behavior")
    temporal_metadata: Optional[Dict[str, Any]] = Field(default=None, description="For D3-J: 1956 vs 2013 or amendment history details")
    conflicting_authorities: Optional[List[Dict[str, Any]]] = Field(default=None, description="For D3-K: Details of divergent rulings")
    difficulty: Literal["easy", "medium", "hard", "adversarial"]


# -----------------------------------------------------------------------------
# Unified Canonical Record
# -----------------------------------------------------------------------------
class Dataset3UnifiedRecord(BaseModel):
    record_id: str
    benchmark_family: str
    pillar: Literal["retrieval", "grounding", "citation_verification", "robustness"]
    query_or_claim: str
    expected_output_or_status: str
    difficulty: Literal["easy", "medium", "hard", "adversarial"]
    split: Literal["train", "dev", "test", "held_out"]
    primary_source_ids: List[str] = Field(default_factory=list)
    raw_record: Dict[str, Any]
