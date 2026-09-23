"""
Unit Tests for Gate EV2: Canonical Evidence Resolution & Read-Only Store
========================================================================
Protocol: v1.0-FROZEN
Verifies canonical resolution of D1 statutory and D2 judicial passage IDs,
SHA-256 passage text hashing, and read-only non-mutability.
"""

import pytest
from halo.evidence_verifier.evidence_store import EvidenceStore
from halo.evidence_verifier.config import EvidenceVerifierConfig


@pytest.fixture(scope="module")
def store():
    return EvidenceStore.get_instance()


def test_d1_statutory_passage_resolution(store):
    """Gate EV2: Authoritative D1 passage ID resolution."""
    pid = "PAS_ACT_COMPANIES_2013_SEC_135_SUB_1"
    rec = store.get_passage(pid)
    assert rec is not None
    assert rec.passage_id == pid
    assert rec.dataset == "D1"
    assert rec.source == "Companies Act, 2013"
    assert "Corporate Social Responsibility" in rec.text or "net worth" in rec.text
    assert len(rec.text_hash) == 64


def test_d2_judicial_passage_resolution(store):
    """Gate EV2: Authoritative D2 passage ID resolution."""
    # Find any judicial passage in D2
    sample_pid = None
    for pid, rec in store._passages.items():
        if rec.dataset == "D2":
            sample_pid = pid
            break

    assert sample_pid is not None
    rec = store.get_passage(sample_pid)
    assert rec is not None
    assert rec.dataset == "D2"
    assert len(rec.text) > 0
    assert len(rec.text_hash) == 64


def test_nonexistent_passage_returns_none(store):
    """Gate EV6: Nonexistent passage ID must safely return None without throwing."""
    assert store.get_passage("PAS_NONEXISTENT_999999") is None
    assert store.get_passage("") is None
    assert store.get_passage(None) is None


def test_evidence_store_is_read_only(store):
    """Gate EV2: Evidence store must not expose mutation methods."""
    assert not hasattr(store, "write_passage")
    assert not hasattr(store, "update_passage")
    assert not hasattr(store, "delete_passage")
