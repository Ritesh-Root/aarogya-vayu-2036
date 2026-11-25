"""Shared fixtures."""
import pytest

import app.main as main_module
from app import sandbox


@pytest.fixture
def sandboxed(monkeypatch):
    """Run against an in-memory per-visitor sandbox so the bundled data/ files are never written."""
    monkeypatch.setattr(main_module.storage, "sandbox", True)
    monkeypatch.setattr(main_module.audit_ledger, "sandbox", True)
    store = sandbox.SessionStore(max_sessions=500, ttl_s=86400)
    monkeypatch.setattr(sandbox, "SESSIONS", store)
    return store


