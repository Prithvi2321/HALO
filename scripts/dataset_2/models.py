"""
HALO Dataset 2: Core Data Models & Schemas
==========================================
Pydantic v2 schemas enforcing strict validation, source snapshots,
citation verification states, and bidirectional linkage to Dataset 1.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SourceAuthority(str, Enum):
    OFFICIAL = "OFFICIAL"          # Official court repository / SCR Gazette
    SECONDARY = "SECONDARY"        # Verified open legal data repository
    TERTIARY = "TERTIARY"          # Mirror or metadata-only aggregator


class CourtType(str, Enum):
    SUPREME_COURT_OF_INDIA = "SUPREME_COURT_OF_INDIA"
    NCLAT = "NCLAT"
    HIGH_COURT = "HIGH_COURT"


class LifecycleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    METADATA_VALIDATED = "METADATA_VALIDATED"
    DOCUMENT_ACQUIRED = "DOCUMENT_ACQUIRED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    QUALITY_CHECKED = "QUALITY_CHECKED"
    LEGAL_RELEVANCE_REVIEWED = "LEGAL_RELEVANCE_REVIEWED"
    SELECTED = "SELECTED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    READY_TO_FREEZE = "READY_TO_FREEZE"
    FROZEN = "FROZEN"
    # Terminal rejection states
    REJECTED_METADATA = "REJECTED_METADATA"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
    REJECTED_LOW_QUALITY = "REJECTED_LOW_QUALITY"
    REJECTED_OUT_OF_DOMAIN = "REJECTED_OUT_OF_DOMAIN"
    REJECTED_UNVERIFIED_SOURCE = "REJECTED_UNVERIFIED_SOURCE"


class CitationState(str, Enum):
    DETECTED = "DETECTED"
    NORMALIZED = "NORMALIZED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class SourceSnapshot(BaseModel):
    source_id: str = Field(..., description="Unique source identifier from source_registry.json")
    source_authority: SourceAuthority = Field(..., description="Authority tier (OFFICIAL, SECONDARY, TERTIARY)")
    source_url: str = Field(..., description="Exact HTTP or S3 URL from which document was fetched")
    retrieval_timestamp: str = Field(..., description="ISO-8601 UTC timestamp of retrieval")
    http_metadata: Dict[str, Any] = Field(default_factory=dict, description="ETag, Content-Length, Content-Type")
    file_size: int = Field(..., description="File size in bytes on disk")
    sha256: str = Field(..., description="Cryptographic SHA-256 digest of original document")
    license: str = Field(..., description="License terms applicable to source document")


class CandidateJudgment(BaseModel):
    candidate_id: str = Field(..., description="Unique identifier for candidate e.g. CAND-SC-2020-001")
    source_id: str = Field(..., description="Source registry reference")
    court: CourtType = Field(..., description="Judicial forum")
    bench: Optional[str] = Field(None, description="Bench description e.g. 2 Judges, Constitution Bench")
    case_title: str = Field(..., description="Official case title e.g. Party A v. Party B")
    case_number: Optional[str] = Field(None, description="Official appeal or petition number")
    decision_date: Optional[str] = Field(None, description="ISO-8601 date YYYY-MM-DD")
    citations: List[str] = Field(default_factory=list, description="Extracted citations e.g. 2020 INSC 525")
    coram: List[str] = Field(default_factory=list, description="Presiding judges")
    discovery_terms: List[str] = Field(default_factory=list, description="Terms that matched during discovery")
    topic_tags: List[str] = Field(default_factory=list, description="Corporate law topics identified")
    source_url: str = Field(..., description="Source locator")
    source_authority: SourceAuthority = Field(SourceAuthority.OFFICIAL)
    lifecycle_state: LifecycleState = Field(LifecycleState.DISCOVERED)
    relevance_score: Optional[float] = Field(None, description="Multi-factor score from 0.0 to 1.0")
    selection_status: str = Field("PENDING", description="PENDING, SHORTLISTED, SELECTED, or REJECTED")


class JudgmentMetadata(BaseModel):
    judgment_id: str = Field(..., description="Canonical ID e.g. JUD-SC-2020-1043")
    document_type: str = Field("JUDGMENT", description="Always JUDGMENT or ORDER")
    court: CourtType = Field(..., description="Judicial forum")
    bench: Optional[str] = Field(None, description="Bench size e.g. 2 Judges")
    coram: List[str] = Field(default_factory=list, description="List of judge names")
    case_number: str = Field(..., description="Civil Appeal No., etc.")
    case_title: str = Field(..., description="Parties title")
    date_of_judgment: str = Field(..., description="ISO-8601 date YYYY-MM-DD")
    citations: List[str] = Field(default_factory=list, description="Official law report citations")
    neutral_citation: Optional[str] = Field(None, description="Official neutral citation e.g. 2020 INSC 525")
    jurisdiction: str = Field("India", description="Always India")
    source_snapshot: SourceSnapshot = Field(..., description="Complete source snapshot")
    topic_classification: List[str] = Field(default_factory=list, description="Assigned topics from 11-topic rubric")
    statutory_provisions_cited: List[str] = Field(default_factory=list, description="Sections referenced")


class JudgmentParagraph(BaseModel):
    paragraph_id: str = Field(..., description="Unique paragraph identifier e.g. JUD-SC-2020-1043-P42")
    judgment_id: str = Field(..., description="Parent judgment ID")
    paragraph_number: int = Field(..., description="Sequential or printed paragraph number")
    page_start: int = Field(..., description="Source page number where paragraph starts")
    page_end: int = Field(..., description="Source page number where paragraph ends")
    char_start: int = Field(..., description="Character offset in extracted text")
    char_end: int = Field(..., description="Character offset in extracted text")
    text: str = Field(..., description="Clean canonical text of paragraph")
    source_sha256: str = Field(..., description="SHA-256 of source document")
    extraction_method: str = Field("native_pdf", description="'native_pdf' or 'ocr'")
    ocr_engine: Optional[str] = Field(None, description="OCR engine name if applicable")
    ocr_confidence: Optional[float] = Field(None, description="Confidence score if OCR used")


class CitationRecord(BaseModel):
    citation_id: str = Field(..., description="Unique citation record ID")
    judgment_id: str = Field(..., description="Parent judgment ID")
    source_paragraph_id: str = Field(..., description="Paragraph containing citation")
    raw_text: str = Field(..., description="Raw text snippet of citation")
    normalized_citation: str = Field(..., description="Normalized legal citation")
    citation_type: str = Field(..., description="e.g. INSC, SCR, SCC, AIR, COMP_CAS")
    verification_state: CitationState = Field(CitationState.DETECTED)
    resolved_case_title: Optional[str] = Field(None, description="Title of cited case if resolved")


class StatutoryCrossReference(BaseModel):
    cross_reference_id: str = Field(..., description="Unique reference ID e.g. XREF-000183")
    judgment_id: str = Field(..., description="Parent judgment ID")
    paragraph_id: str = Field(..., description="Source paragraph ID")
    detected_text: str = Field(..., description="Raw statutory reference snippet")
    source_statute: str = Field(..., description="Statute name e.g. Companies Act, 2013 or Companies Act, 1956")
    source_section: str = Field(..., description="Section string e.g. 241, 529A")
    mapping_type: str = Field("DIRECT_2013", description="DIRECT_2013, PREDECESSOR_1956, or COGNATE_CORPORATE_STATUTE")
    target_dataset: Optional[str] = Field(None, description="Target dataset e.g. HALO_DATASET_1")
    dataset_1_id: Optional[str] = Field(None, description="Corresponding Dataset 1 ID e.g. ACT_COMPANIES_2013_SEC_241")
    resolution_status: str = Field(..., description="RESOLVED or UNRESOLVED")
    resolution_method: str = Field(..., description="exact_section_match, predecessor_continuity, or cognate_statute_match")


class JudicialPassage(BaseModel):
    passage_id: str = Field(..., description="Passage ID e.g. PAS-JUD-SC-2020-1043-P42")
    document_id: str = Field(..., description="Parent judgment ID")
    paragraph_ids: List[str] = Field(..., description="List of paragraph IDs in passage")
    text: str = Field(..., description="Canonical retrievable passage text")
    court: CourtType = Field(..., description="Judicial forum")
    citation: Optional[str] = Field(None, description="Primary citation")
    topics: List[str] = Field(default_factory=list, description="Topic classifications")
    provenance_id: str = Field(..., description="Provenance record pointer")


class JudgmentProvenance(BaseModel):
    provenance_id: str = Field(..., description="Unique provenance record ID")
    judgment_id: str = Field(..., description="Parent judgment ID")
    paragraph_id: Optional[str] = Field(None, description="Specific paragraph if paragraph-level")
    source_snapshot: SourceSnapshot = Field(..., description="Source snapshot record")
    page_start: int = Field(..., description="Start page")
    page_end: int = Field(..., description="End page")
    char_start: int = Field(..., description="Start character offset")
    char_end: int = Field(..., description="End character offset")
