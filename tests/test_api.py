"""
Unit Tests for Phase 11: HALO REST API
======================================
Protocol: v1.0-FROZEN
Tests FastAPI endpoints: health, research, and audit inspection.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from halo.api.app import app


class TestHaloAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Verifies GET /api/v1/health returns HEALTHY status."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["protocol"], "v1.0-FROZEN")

    def test_research_endpoint_supported(self):
        """Verifies POST /api/v1/research executes verification and returns audited response."""
        payload = {
            "query": "What is the net profit threshold for CSR under Section 135(1)?",
            "candidate_answer": "Section 135(1) mandates a CSR Committee for companies having a net profit of rupees five crore or more.",
            "citations": [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "135", "subsection": "1"}],
        }
        resp = self.client.post("/api/v1/research", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_authoritative"])
        self.assertFalse(data["fail_closed"])
        self.assertTrue(data["audit_id"].startswith("AUD-"))
        self.assertIn("Verified Legal Findings", data["final_answer"])

        # Test audit retrieval endpoint
        aid = data["audit_id"]
        audit_resp = self.client.get(f"/api/v1/audit/{aid}")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.json()
        self.assertEqual(audit_data["audit_id"], aid)
        self.assertEqual(audit_data["query"], payload["query"])

    def test_research_endpoint_fail_closed(self):
        """Verifies POST /api/v1/research triggers fail closed on fabricated section."""
        payload = {
            "query": "What are the rules under Section 999?",
            "candidate_answer": "Section 999 mandates penalties for quantum computing.",
            "citations": [{"type": "STATUTORY", "act": "Companies Act, 2013", "section": "999"}],
        }
        resp = self.client.post("/api/v1/research", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_authoritative"])
        self.assertTrue(data["fail_closed"])
        self.assertIn("FAIL-CLOSED ADVISORY", data["final_answer"])


if __name__ == "__main__":
    unittest.main()
