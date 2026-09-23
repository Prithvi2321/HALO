"""
Conflict Detector Subsystem
===========================
Protocol: v1.0-FROZEN
Detects statutory and judicial conflicts, divergences, and hierarchy overrides.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


@dataclass
class ConflictDetectionResult:
    has_conflict: bool = False
    conflict_type: Optional[str] = None  # STATUTORY_JUDICIAL | PRECEDENT_SPLIT | AMENDMENT_OVERRIDE | FORUM_HIERARCHY
    diverging_sources: List[Dict[str, Any]] = field(default_factory=list)
    controlling_authority: Optional[str] = None
    explanation: str = ""
    resolution_advisory: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConflictDetector:
    """Detects normative divergence between statutes, judgments, and legal interpretations."""

    COURT_HIERARCHY_WEIGHTS = {
        "SUPREME_COURT_OF_INDIA": 100,
        "HIGH_COURT": 75,
        "NCLAT": 60,
        "NCLT": 40,
        "UNKNOWN": 10,
    }

    def __init__(self):
        # Known doctrinal tensions / conflicts
        self.known_conflicts = [
            {
                "topic": "moratorium_personal_guarantor",
                "keywords": ["moratorium", "guarantor", "personal guarantor"],
                "statutory_source": "Section 14, Insolvency and Bankruptcy Code, 2016",
                "divergence_nature": "High Court / NCLAT split vs Supreme Court authoritative ruling",
                "controlling_case": "Lalit Kumar Jain v. Union of India (2021)",
                "ruling": "Moratorium under Section 14 does not shield personal guarantors of corporate debtors.",
            },
            {
                "topic": "mining_lease_retrospective_amendment",
                "keywords": ["mining lease", "section 10a", "bhushan power", "letter of intent"],
                "statutory_source": "Section 10A, MMDR Act (amended 2015)",
                "divergence_nature": "Legitimate expectation doctrine vs statutory invalidation of pending applications",
                "controlling_case": "Bhushan Power & Steel Ltd. v. Mr. S.L. Seal, [2016] 11 S.C.R. 149",
                "ruling": "Pending applications without prior Central Government approval lapse under the 2015 amendment.",
            },
            {
                "topic": "operational_debt_dispute",
                "keywords": ["pre-existing dispute", "operational creditor", "section 9", "mobilox"],
                "statutory_source": "Section 8 & 9, Insolvency and Bankruptcy Code, 2016",
                "divergence_nature": "Plausible contention standard vs indisputable debt",
                "controlling_case": "Mobilox Innovations Pvt. Ltd. v. Kirusa Software Pvt. Ltd., [2017] 10 S.C.R. 1006",
                "ruling": "Notice of dispute need only present a plausible, non-spurious dispute, not prove it conclusively at Section 9 stage.",
            }
        ]

    def detect_conflicts(
        self,
        query: str,
        claims: List[str],
        evidences: List[Dict[str, Any]],
    ) -> ConflictDetectionResult:
        """Analyzes query, claims, and retrieved sources for doctrinal or hierarchy conflicts."""
        q_lower = query.lower()
        full_text = q_lower + " " + " ".join(c.lower() for c in claims)

        for conf in self.known_conflicts:
            matched_kw = sum(1 for kw in conf["keywords"] if kw in full_text)
            if matched_kw >= 2:
                return ConflictDetectionResult(
                    has_conflict=True,
                    conflict_type="STATUTORY_JUDICIAL",
                    diverging_sources=[
                        {"source": conf["statutory_source"], "role": "Statutory provision"},
                        {"source": conf["controlling_case"], "role": "Supreme Court authoritative precedent"},
                    ],
                    controlling_authority=conf["controlling_case"],
                    explanation=f"Doctrinal tension identified: {conf['divergence_nature']}.",
                    resolution_advisory=f"Binding Precedent (Article 141): {conf['ruling']} Controls.",
                )

        # Forum hierarchy evaluation if multiple judicial sources exist
        courts = [e.get("court") for e in evidences if e.get("court")]
        if len(set(courts)) > 1:
            highest_court = max(courts, key=lambda c: self.COURT_HIERARCHY_WEIGHTS.get(c, 0))
            return ConflictDetectionResult(
                has_conflict=True,
                conflict_type="FORUM_HIERARCHY",
                diverging_sources=[{"court": c} for c in set(courts)],
                controlling_authority=highest_court,
                explanation=f"Multiple adjudicatory fora cited ({', '.join(set(courts))}).",
                resolution_advisory=f"Under judicial hierarchy, decisions of {highest_court} prevail over subordinate tribunals.",
            )

        return ConflictDetectionResult(has_conflict=False)
