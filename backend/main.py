"""
HALO Chatbot Backend Server (Nyaya Sahayak)
===========================================
Production FastAPI server orchestrating the HALO retrieval, generation,
and fail-closed legal verification architecture.
"""

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.routers.query import router as query_router

app = FastAPI(
    title="HALO Legal Research Intelligence (Nyaya Sahayak)",
    version="1.0.0",
    description="Hallucination-Aware Legal Output REST API for Indian Corporate Law and Supreme Court Precedents."
)

# Enable CORS for React frontend on port 3000 / localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)


@app.get("/")
def root():
    return {
        "status": "ONLINE",
        "app": "HALO — Nyaya Sahayak",
        "description": "Hallucination-Aware Legal Output Intelligence System",
        "version": "1.0.0",
        "active_corpus_passages": 12223,
        "endpoints": ["/api/query", "/api/history", "/api/stats", "/docs"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
