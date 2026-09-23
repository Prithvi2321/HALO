"""
Production REST API for HALO Verification System
================================================
Protocol: v1.0-FROZEN
Endpoints:
- POST /api/v1/research: Executes research verification, fail-closed governance, and answer reconstruction
- GET /api/v1/audit/{audit_id}: Retrieves immutable cryptographic audit trail
- GET /api/v1/health: System liveness and version status
"""

import os
import sys
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Ensure root HALO package is discoverable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from halo.pipeline import HaloPipeline

app = FastAPI(
    title="HALO Legal Verification System API",
    version="1.0-FROZEN",
    description="Authoritative legal intelligence, multi-tier verification, and fail-closed governance for Indian Corporate Law.",
)

# Initialize pipeline singleton
pipeline = HaloPipeline()


class ResearchRequest(BaseModel):
    query: str = Field(..., description="User legal query")
    candidate_answer: Optional[str] = Field(None, description="Pre-generated candidate legal answer to verify")
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Explicit statutory/judicial citations")
    candidate_passages: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Retrieved candidate legal passages")


class ResearchResponse(BaseModel):
    audit_id: str
    query: str
    is_authoritative: bool
    fail_closed: bool
    final_answer: str
    overall_confidence: float
    quarantine_report: Dict[str, Any]
    conflict_detection: Dict[str, Any]
    content_hash: str
    timestamp: str


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "HALO Legal Verification System",
        "protocol": "v1.0-FROZEN",
        "version": "1.0.0",
    }


@app.post("/api/v1/research", response_model=ResearchResponse)
def research_query(req: ResearchRequest):
    raw_answer = req.candidate_answer or req.query
    try:
        result = pipeline.process(
            query=req.query,
            raw_answer=raw_answer,
            candidate_passages=req.candidate_passages,
            explicit_citations=req.citations,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification pipeline failed: {str(e)}",
        )


@app.get("/api/v1/audit/{audit_id}")
def get_audit(audit_id: str):
    record = pipeline.audit_logger.get_audit_record(audit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit record with ID '{audit_id}' was not found.",
        )
    return record.to_dict()
