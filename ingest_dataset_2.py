"""
HALO Dataset 2: Production-Grade Ingestion & Curation Pipeline
=============================================================
Orchestrates Phase A (Metadata Discovery, Deduplication & Selection Gate)
and Phase B (Selective Acquisition, Deterministic Extraction, Paragraph
Segmentation, Citation Extraction, Dataset 1 Cross-Referencing & Export).
Sets state to READY_TO_FREEZE for final independent audit and freeze operation.
"""

import os
import sys
import logging
from datetime import datetime

from scripts.dataset_2.models import JudgmentMetadata
from scripts.dataset_2.discovery import run_discovery
from scripts.dataset_2.ranker import CandidateRanker
from scripts.dataset_2.selection_gate import SelectionGate
from scripts.dataset_2.acquirer import DocumentAcquirer
from scripts.dataset_2.extractor import JudgmentExtractor
from scripts.dataset_2.parser import JudicialParser
from scripts.dataset_2.passage_generator import PassageGenerator
from scripts.dataset_2.provenance import ProvenanceGenerator
from scripts.dataset_2.exporter import CanonicalExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("halo.dataset_2.pipeline")


def run_pipeline():
    logger.info("=" * 72)
    logger.info("   HALO DATASET 2: CURATED JUDICIAL CORPUS INGESTION PIPELINE   ")
    logger.info("=" * 72)

    # -------------------------------------------------------------
    # PHASE A: Metadata Discovery, Deduplication & Selection Gate
    # -------------------------------------------------------------
    logger.info("\n>>> STARTING PHASE A: METADATA DISCOVERY & CURATION GATE <<<")
    candidates = run_discovery(target_count=60)

    ranker = CandidateRanker()
    scored = ranker.rank_candidates(candidates)

    gate = SelectionGate(min_score=0.50)
    selected_cohort = gate.select_cohort(scored)

    if not selected_cohort:
        logger.error("No candidates approved by selection gate! Pipeline aborted.")
        sys.exit(1)

    # -------------------------------------------------------------
    # PHASE B: Selective Acquisition, Extraction, Parsing & Export
    # -------------------------------------------------------------
    logger.info("\n>>> STARTING PHASE B: SELECTIVE ACQUISITION & PROCESSING <<<")
    acquirer = DocumentAcquirer()
    acquired_records = acquirer.acquire_selected()

    if not acquired_records:
        logger.error("No documents acquired! Pipeline aborted.")
        sys.exit(1)

    extractor = JudgmentExtractor()
    parser = JudicialParser()
    passage_gen = PassageGenerator()
    prov_gen = ProvenanceGenerator()

    all_judgments = []
    all_paragraphs = []
    all_passages = []
    all_citations = []
    all_cross_references = []
    all_provenance = []

    for idx, rec in enumerate(acquired_records, 1):
        cand = rec["candidate"]
        snapshot = rec["snapshot"]
        pdf_path = rec["pdf_path"]

        j_id = cand.candidate_id.replace("CAND-", "JUD-")
        logger.info(f"\n[{idx}/{len(acquired_records)}] Processing: {j_id} ({cand.case_title[:45]})")

        ext_data = extractor.extract_document(pdf_path, j_id)
        total_pages = ext_data["quality_report"]["total_pages"]
        total_chars = ext_data["quality_report"]["total_characters"]

        j_meta = JudgmentMetadata(
            judgment_id=j_id,
            document_type="JUDGMENT",
            court=cand.court,
            bench=cand.bench,
            coram=cand.coram,
            case_number=cand.case_number or "Unspecified",
            case_title=cand.case_title,
            date_of_judgment=cand.decision_date or "2020-01-01",
            citations=cand.citations,
            neutral_citation=cand.citations[0] if cand.citations else None,
            jurisdiction="India",
            source_snapshot=snapshot,
            topic_classification=cand.topic_tags,
            statutory_provisions_cited=[]
        )

        paragraphs = parser.segment_paragraphs(ext_data, j_id, snapshot.sha256)
        citations = parser.extract_citations(paragraphs, j_id)
        xrefs = parser.extract_statutory_cross_references(paragraphs, j_id)

        cited_secs = list(set(x.source_section for x in xrefs))
        j_meta.statutory_provisions_cited = cited_secs

        passages = passage_gen.generate_passages(j_meta, paragraphs)
        p_provs = prov_gen.generate_paragraph_provenance(paragraphs, snapshot)
        d_prov = prov_gen.generate_document_provenance(j_meta, snapshot, total_pages, total_chars)

        all_judgments.append(j_meta)
        all_paragraphs.extend(paragraphs)
        all_passages.extend(passages)
        all_citations.extend(citations)
        all_cross_references.extend(xrefs)
        all_provenance.extend([d_prov] + p_provs)

    # Export canonical files in READY_TO_FREEZE status
    exporter = CanonicalExporter()
    manifest = exporter.export_corpus(
        judgments=all_judgments,
        paragraphs=all_paragraphs,
        passages=all_passages,
        citations=all_citations,
        cross_references=all_cross_references,
        provenance_records=all_provenance,
        source_records=acquired_records,
        freeze_status="READY_TO_FREEZE"
    )

    logger.info("\n" + "=" * 72)
    logger.info("   DATASET 2 INGESTION COMPLETE: STATUS IS READY_TO_FREEZE      ")
    logger.info("=" * 72)
    return manifest


if __name__ == "__main__":
    run_pipeline()
