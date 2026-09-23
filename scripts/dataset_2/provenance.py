"""
HALO Dataset 2: Provenance Generation Engine
============================================
Creates granular paragraph-level and document-level cryptographic provenance records.
"""

from typing import List
from .models import JudgmentParagraph, JudgmentProvenance, SourceSnapshot, JudgmentMetadata


class ProvenanceGenerator:
    """Generates immutable provenance records for judicial passages and paragraphs."""

    def generate_paragraph_provenance(
        self,
        paragraphs: List[JudgmentParagraph],
        snapshot: SourceSnapshot
    ) -> List[JudgmentProvenance]:
        records: List[JudgmentProvenance] = []
        for p in paragraphs:
            prov_id = f"PROV-{p.paragraph_id}"
            rec = JudgmentProvenance(
                provenance_id=prov_id,
                judgment_id=p.judgment_id,
                paragraph_id=p.paragraph_id,
                source_snapshot=snapshot,
                page_start=p.page_start,
                page_end=p.page_end,
                char_start=p.char_start,
                char_end=p.char_end
            )
            records.append(rec)
        return records

    def generate_document_provenance(
        self,
        metadata: JudgmentMetadata,
        snapshot: SourceSnapshot,
        total_pages: int,
        total_chars: int
    ) -> JudgmentProvenance:
        return JudgmentProvenance(
            provenance_id=f"PROV-{metadata.judgment_id}",
            judgment_id=metadata.judgment_id,
            paragraph_id=None,
            source_snapshot=snapshot,
            page_start=1,
            page_end=total_pages,
            char_start=0,
            char_end=total_chars
        )
