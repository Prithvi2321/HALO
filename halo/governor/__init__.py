"""
HALO Fail-Closed Governor Subsystem
===================================
Protocol: v1.0-FROZEN
Deterministic fail-closed policy enforcement:
- Strict rejection and purging of CONTRADICTED and FABRICATED propositions
- Transparent qualification of FLAGGED and PARTIAL propositions
- Zero-evidence fail-closed refusal
- Authoritative answer reconstruction with cryptographic audit references
"""

from .governor import FailClosedGovernor, GovernorVerdict

__all__ = ["FailClosedGovernor", "GovernorVerdict"]
