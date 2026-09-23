"""
HALO Confidence Engine Subsystem
================================
Protocol: v1.0-FROZEN
Computes deterministic, evidence-grounded mathematical confidence scores:
- Zero LLM self-confidence or self-reflection
- Multiplicative weakest-link integration across Citation, Evidence, and Temporal scores
- Strict bounds: 0.0 <= Confidence <= 1.0
"""

from .engine import ConfidenceEngine, ClaimConfidenceScore, AnswerConfidenceScore

__all__ = ["ConfidenceEngine", "ClaimConfidenceScore", "AnswerConfidenceScore"]
