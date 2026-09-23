"""
HALO Dataset 2: Deterministic Retrieval Passage Generator
=========================================================
Groups paragraphs into discrete, retrievable legal passages with full metadata.
Passage generation is strictly deterministic (no embeddings generated here).
"""

from typing import List, Dict, Any
from .models import JudgmentParagraph, JudicialPassage, JudgmentMetadata


class PassageGenerator:
    """Generates retrievable passage units from paragraphs."""

    def __init__(self, target_chars_per_passage: int = 1500):
        self.target_chars = target_chars_per_passage

    def generate_passages(
        self,
        metadata: JudgmentMetadata,
        paragraphs: List[JudgmentParagraph]
    ) -> List[JudicialPassage]:
        """
        Groups sequential paragraphs into coherent retrievable passages.
        Single substantive paragraphs (>600 chars) form independent passages.
        Smaller adjacent paragraphs are grouped together up to target_chars.
        """
        passages: List[JudicialPassage] = []
        current_paras: List[JudgmentParagraph] = []
        current_len = 0
        passage_num = 1

        primary_cit = metadata.neutral_citation or (metadata.citations[0] if metadata.citations else None)

        for p in paragraphs:
            p_len = len(p.text)
            # If paragraph is long on its own, flush current and emit standalone
            if p_len >= 600:
                if current_paras:
                    # Flush accumulated
                    pas_id = f"PAS-{metadata.judgment_id}-P{passage_num:03d}"
                    combined_text = "\n\n".join(cp.text for cp in current_paras)
                    passages.append(JudicialPassage(
                        passage_id=pas_id,
                        document_id=metadata.judgment_id,
                        paragraph_ids=[cp.paragraph_id for cp in current_paras],
                        text=combined_text,
                        court=metadata.court,
                        citation=primary_cit,
                        topics=metadata.topic_classification,
                        provenance_id=f"PROV-{pas_id}"
                    ))
                    passage_num += 1
                    current_paras = []
                    current_len = 0

                # Emit standalone
                pas_id = f"PAS-{metadata.judgment_id}-P{passage_num:03d}"
                passages.append(JudicialPassage(
                    passage_id=pas_id,
                    document_id=metadata.judgment_id,
                    paragraph_ids=[p.paragraph_id],
                    text=p.text,
                    court=metadata.court,
                    citation=primary_cit,
                    topics=metadata.topic_classification,
                    provenance_id=f"PROV-{pas_id}"
                ))
                passage_num += 1
                continue

            # Accumulate smaller paragraphs
            if current_len + p_len > self.target_chars and current_paras:
                pas_id = f"PAS-{metadata.judgment_id}-P{passage_num:03d}"
                combined_text = "\n\n".join(cp.text for cp in current_paras)
                passages.append(JudicialPassage(
                    passage_id=pas_id,
                    document_id=metadata.judgment_id,
                    paragraph_ids=[cp.paragraph_id for cp in current_paras],
                    text=combined_text,
                    court=metadata.court,
                    citation=primary_cit,
                    topics=metadata.topic_classification,
                    provenance_id=f"PROV-{pas_id}"
                ))
                passage_num += 1
                current_paras = [p]
                current_len = p_len
            else:
                current_paras.append(p)
                current_len += p_len

        # Flush final remaining
        if current_paras:
            pas_id = f"PAS-{metadata.judgment_id}-P{passage_num:03d}"
            combined_text = "\n\n".join(cp.text for cp in current_paras)
            passages.append(JudicialPassage(
                passage_id=pas_id,
                document_id=metadata.judgment_id,
                paragraph_ids=[cp.paragraph_id for cp in current_paras],
                text=combined_text,
                court=metadata.court,
                citation=primary_cit,
                topics=metadata.topic_classification,
                provenance_id=f"PROV-{pas_id}"
            ))

        return passages
