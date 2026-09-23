"""
HALO REST API Service
=====================
Protocol: v1.0-FROZEN
Exposes production verification endpoints:
- POST /api/v1/research
- GET /api/v1/audit/{audit_id}
- GET /api/v1/health
"""

from .app import app

__all__ = ["app"]
