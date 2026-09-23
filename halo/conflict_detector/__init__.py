"""
HALO Conflict Detector Subsystem
================================
Protocol: v1.0-FROZEN
Detects statutory divergence, judicial split, and authority hierarchy conflicts:
- Statutory vs Judicial divergence
- Bench size hierarchy (Constitution Bench > Division Bench)
- Forum hierarchy (Supreme Court of India > NCLAT > NCLT)
- Legislative amendment overriding prior judicial ruling
"""

from .detector import ConflictDetector, ConflictDetectionResult

__all__ = ["ConflictDetector", "ConflictDetectionResult"]
