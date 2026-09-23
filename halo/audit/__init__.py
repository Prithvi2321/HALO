"""
HALO Audit Subsystem
====================
Protocol: v1.0-FROZEN
Cryptographic audit logging and traceability for verified legal intelligence:
- UUID-based query audit IDs
- Immutable JSONL audit storage
- Cryptographic SHA-256 verification seals
- Instant audit inspection by audit_id
"""

from .logger import AuditLogger, AuditRecord

__all__ = ["AuditLogger", "AuditRecord"]
