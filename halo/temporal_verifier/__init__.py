"""
HALO Temporal Verifier Subsystem
================================
Protocol: v1.0-FROZEN
Tracks statutory enforceability, amendments, repeals, and temporal validity:
- CURRENT: Provision is active and in force in present consolidated law
- AMENDED: Provision has been modified by Parliamentary amending enactment
- REPEALED: Enactment or section repealed (e.g. Companies Act, 1956 repealed by Sec 465)
- HISTORICAL: Asserting repealed/omitted law as current law is detected as CONTRADICTED
"""

from .verifier import TemporalVerifier, TemporalVerificationResult

__all__ = ["TemporalVerifier", "TemporalVerificationResult"]
