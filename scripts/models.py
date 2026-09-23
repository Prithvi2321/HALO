"""
HALO Dataset 1 - Data Models and Schemas
Authoritative, immutable, provenance-preserving statutory entities.
Upgraded with full Temporal Lifecycle, Editorial Markers, and 4-tier Cryptographic Lineage.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VersionType(str, Enum):
    ORIGINAL = "original"
    AMENDMENT = "amendment"
    CONSOLIDATED = "consolidated"
    CONSOLIDATED_CURRENT = "consolidated_current"


class AmendmentOp(str, Enum):
    INSERT = "INSERT"
    DELETE = "DELETE"
    SUBSTITUTE = "SUBSTITUTE"
    RENUMBER = "RENUMBER"
    OMIT = "OMIT"
    ADD = "ADD"
    REPEAL = "REPEAL"
    REPEAL_AND_REPLACE = "REPEAL_AND_REPLACE"
    MODIFY = "MODIFY"


class EnforcementStatus(str, Enum):
    ENACTED = "ENACTED"
    PUBLISHED = "PUBLISHED"
    AMENDED = "AMENDED"
    COMMENCED = "COMMENCED"
    IN_FORCE = "IN_FORCE"
    PENDING_COMMENCEMENT = "PENDING_COMMENCEMENT"
    OMITTED = "OMITTED"
    REPEALED = "REPEALED"


class EditorialMarker(BaseModel):
    marker: str
    location: str = "section_text"
    target: str = ""
    target_footnote_id: str = ""
    raw_snippet: Optional[str] = None


class Footnote(BaseModel):
    footnote_id: str
    marker: str
    text: str
    source_page: int
    amending_act: Optional[str] = None
    amending_section: Optional[str] = None
    commencement_date: Optional[str] = None


class SourceDocumentManifest(BaseModel):
    source_document_id: str
    document_type: str
    title: str
    act_title: str
    act_number: Optional[str] = None
    publication_date: Optional[str] = None
    enactment_date: Optional[str] = None
    effective_date: Optional[str] = None
    version_type: VersionType
    as_of_date: Optional[str] = None
    source_name: str
    source_url: Optional[str] = None
    downloaded_at: str
    file_name: str
    file_size_bytes: int
    sha256: str  # source_pdf_sha256
    page_count: int
    mime_type: str = "application/pdf"


class ExtractedPage(BaseModel):
    source_document_id: str
    page_number: int
    char_count: int
    raw_text: str
    raw_text_sha256: str
    extraction_method: str  # native_pdf | ocr
    ocr_confidence: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)


class NormalizedPage(BaseModel):
    source_document_id: str
    page_number: int
    clean_text: str
    body_text: str
    footnotes: List[Footnote] = Field(default_factory=list)
    headers_removed: List[str] = Field(default_factory=list)
    footers_removed: List[str] = Field(default_factory=list)
    canonical_text_sha256: str


class ClauseNode(BaseModel):
    clause_id: str
    clause_identifier: str  # e.g. "(a)", "(i)"
    text: str
    canonical_text: str
    editorial_markers: List[EditorialMarker] = Field(default_factory=list)
    sub_clauses: List["ClauseNode"] = Field(default_factory=list)
    source_page_start: int
    source_page_end: int
    content_hash: str


class ProvisoNode(BaseModel):
    proviso_id: str
    proviso_type: str  # proviso | further_proviso | also_proviso
    text: str
    canonical_text: str
    source_page_start: int
    source_page_end: int


class ExplanationNode(BaseModel):
    explanation_id: str
    explanation_number: Optional[str] = None
    text: str
    canonical_text: str
    source_page_start: int
    source_page_end: int


class SubsectionNode(BaseModel):
    subsection_id: str
    subsection_number: str
    text: str
    canonical_text: str
    editorial_markers: List[EditorialMarker] = Field(default_factory=list)
    clauses: List[ClauseNode] = Field(default_factory=list)
    provisos: List[ProvisoNode] = Field(default_factory=list)
    explanations: List[ExplanationNode] = Field(default_factory=list)
    source_page_start: int
    source_page_end: int
    content_hash: str


class SectionNode(BaseModel):
    section_id: str
    section_number: str
    heading: str
    text: str  # raw text with editorial markers preserved
    canonical_text: str  # clean statutory text for retrieval
    chapter_id: str
    editorial_markers: List[EditorialMarker] = Field(default_factory=list)
    footnotes: List[Footnote] = Field(default_factory=list)
    subsections: List[SubsectionNode] = Field(default_factory=list)
    clauses: List[ClauseNode] = Field(default_factory=list)
    provisos: List[ProvisoNode] = Field(default_factory=list)
    explanations: List[ExplanationNode] = Field(default_factory=list)
    source_document_id: str
    source_page_start: int
    source_page_end: int
    # Explicit Temporal Lifecycle
    enactment_date: str = "2013-08-29"
    publication_date: str = "2013-08-30"
    amendment_date: Optional[str] = None
    commencement_date: Optional[str] = None
    enforcement_status: EnforcementStatus = EnforcementStatus.IN_FORCE
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "active"  # active | omitted | substituted | repealed
    version_id: str
    amendment_history: List[str] = Field(default_factory=list)
    # 4-tier cryptographic lineage
    source_pdf_sha256: str = ""
    raw_extracted_text_sha256: str = ""
    canonical_text_sha256: str = ""
    content_hash: str = ""
    review_required: bool = False


class ChapterNode(BaseModel):
    chapter_id: str
    chapter_number: str
    title: str
    part: Optional[str] = None
    sections: List[SectionNode] = Field(default_factory=list)


class ScheduleNode(BaseModel):
    schedule_id: str
    schedule_number: str
    title: str
    text: str
    canonical_text: str
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    source_page_start: int
    source_page_end: int
    content_hash: str


class CanonicalAct(BaseModel):
    document_id: str
    source: str
    act_title: str
    act_number: str
    enactment_date: Optional[str] = None
    publication_date: Optional[str] = None
    jurisdiction: str = "India"
    document_type: str = "Central Act"
    source_url: Optional[str] = None
    retrieved_at: str
    content_hash: str
    version_id: str
    version_type: VersionType
    as_of_date: Optional[str] = None
    chapters: List[ChapterNode] = Field(default_factory=list)
    schedules: List[ScheduleNode] = Field(default_factory=list)


class Passage(BaseModel):
    passage_id: str
    document_id: str
    version_id: str
    section_id: str
    subsection_id: Optional[str] = None
    clause_id: Optional[str] = None
    schedule_id: Optional[str] = None
    passage_type: str  # section | subsection | clause | proviso | explanation | schedule
    heading: str
    text: str  # raw text
    canonical_text: str  # clean text for BM25 / dense embedding
    editorial_markers: List[EditorialMarker] = Field(default_factory=list)
    source_document_id: str
    source_page_start: int
    source_page_end: int
    source_url: Optional[str] = None
    # 4-tier Lineage
    source_pdf_sha256: str
    raw_extracted_text_sha256: str = ""
    canonical_text_sha256: str = ""
    enactment_date: Optional[str] = None
    publication_date: Optional[str] = None
    amendment_date: Optional[str] = None
    commencement_date: Optional[str] = None
    enforcement_status: EnforcementStatus = EnforcementStatus.IN_FORCE
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "active"
    amendment_history: List[str] = Field(default_factory=list)
    footnotes: List[Footnote] = Field(default_factory=list)
    content_hash: str
    review_required: bool = False


class AmendmentAction(BaseModel):
    amendment_id: str
    amending_act_id: str
    amending_act_number: str
    enactment_date: Optional[str] = None
    publication_date: Optional[str] = None
    commencement_date: Optional[str] = None
    effective_date: Optional[str] = None
    enforcement_status: EnforcementStatus = EnforcementStatus.IN_FORCE
    target_act: str = "The Companies Act, 2013"
    target_section: str
    target_subsection: Optional[str] = None
    target_clause: Optional[str] = None
    target_subclause: Optional[str] = None
    operation: AmendmentOp
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    source_document_id: str
    source_page: int
    notes: Optional[str] = None
    status: str = "EXTRACTED"


class DefinedTerm(BaseModel):
    term: str
    source_section: str
    clause_number: str
    definition: str
    definition_passage_id: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class CrossReference(BaseModel):
    source_passage_id: str
    source_section_id: str
    target_reference: str
    target_section_id: Optional[str] = None
    reference_type: str  # internal_section | internal_schedule | external_act
    raw_mention: str


class FreezeManifest(BaseModel):
    dataset_name: str = "HALO_DATASET_1_COMPANIES_ACT_2013"
    version: str = "v1.0.0-candidate-frozen"
    status: str = "CANDIDATE-FROZEN / PENDING FINAL QA"
    frozen_at: str
    source_pdf_hashes: Dict[str, str]
    raw_pages_sha256: str
    normalized_pages_sha256: str
    canonical_act_sha256: str
    passages_jsonl_sha256: str
    provenance_sha256: str
    amendments_sha256: str
    versions_sha256: str
    definitions_sha256: str
    cross_references_sha256: str
    validation_report_sha256: str
    total_sections: int
    total_passages: int
    total_amendments: int


class HumanReviewItem(BaseModel):
    item_id: str
    section_id: str
    section_number: str
    priority: str = "LOW"  # HIGH | MEDIUM | LOW
    reason: str
    source_document_id: str
    source_page: int
    diff_text: Optional[str] = None
    resolved: bool = False
