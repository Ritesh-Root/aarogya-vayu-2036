"""Per-visitor demo sandbox: each browser gets its own stock, approvals and audit chain."""
import uuid

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app import sandbox
from app.storage import StorageError

FAC = "PHC-LKO-01"


@pytest.fixture
def sandboxed(monkeypatch):
    monkeypatch.setattr(main_module.storage, "sandbox", True)
    monkeypatch.setattr(main_module.audit_ledger, "sandbox", True)
    store = sandbox.SessionStore(max_sessions=500, ttl_s=86400)
    monkeypatch.setattr(sandbox, "SESSIONS", store)
    return store


def _client():
    return TestClient(main_module.app)


def _first_item(client):
    desk = client.get(f"/api/clinic/{FAC}/desk").json()
    return desk["inventory"][0]


def _count(client, item, qty):
    return client.post(f"/api/clinic/{FAC}/stock-action", json={
        "facility_id": FAC, "medicine_id": item["medicine_id"], "batch_number": item["batch_number"],
        "action_type": "PHYSICAL_COUNT", "quantity": qty, "reason": "sandbox test",
    })


def test_cookie_is_set(sandboxed):
    res = _client().get("/api/regions")
    assert sandbox.SESSION_COOKIE in res.cookies


def test_two_visitors_isolated(sandboxed):
    a, b = _client(), _client()
    seed = _first_item(b)
    recs = a.get("/api/recommendations?region=lucknow&scenario=smog").json()
    assert recs
    assert a.post("/api/approve-transfer?scenario=smog", json={"recommendation_id": recs[0]["id"]}).status_code == 200
    assert _count(a, _first_item(a), seed["on_hand"] + 7).status_code == 200

    assert _first_item(b)["on_hand"] == seed["on_hand"]
    b_log = b.get("/api/audit-log?region=lucknow&limit=100").json()
    assert [e["event_type"] for e in b_log] == ["GENESIS"]
    b_recs = b.get("/api/recommendations?region=lucknow&scenario=smog").json()
    assert all(r["status"] != "APPROVED" for r in b_recs)


def test_reset_only_mine(sandboxed):
    a, b = _client(), _client()
    seed = _first_item(a)
    _count(a, _first_item(a), seed["on_hand"] + 3)
    _count(b, _first_item(b), seed["on_hand"] + 5)
    assert a.post("/api/demo/reset").status_code == 200
    assert _first_item(a)["on_hand"] == seed["on_hand"]
    assert _first_item(b)["on_hand"] == seed["on_hand"] + 5


def test_session_cap(sandboxed, monkeypatch):
    small = sandbox.SessionStore(max_sessions=50, ttl_s=86400)
    monkeypatch.setattr(sandbox, "SESSIONS", small)
    for _ in range(200):
        _client().get(f"/api/clinic/{FAC}/desk")
    assert len(small) <= 50


def test_session_ttl_expires(sandboxed):
    store = sandbox.SessionStore(max_sessions=10, ttl_s=0)
    store.get("s1", "lucknow", lambda: {"x": 1})
    store.get("s2", "lucknow", lambda: {"x": 1})
    assert len(store) == 1  # s1 expired when s2 arrived


def test_unknown_session_reseeds(sandboxed):
    c = _client()
    c.cookies.set(sandbox.SESSION_COOKIE, uuid.uuid4().hex)
    res = c.get(f"/api/clinic/{FAC}/desk")
    assert res.status_code == 200 and res.json()["inventory"]


def test_invalid_cookie_replaced(sandboxed):
    c = _client()
    c.cookies.set(sandbox.SESSION_COOKIE, "../../etc/passwd")
    res = c.get("/api/regions")
    assert sandbox.SESSION_COOKIE in res.cookies and res.cookies[sandbox.SESSION_COOKIE] != "../../etc/passwd"


def test_rollback_on_commit_failure(sandboxed, monkeypatch):
    c = _client()
    item = _first_item(c)
    before = len(c.get("/api/audit-log?region=lucknow&limit=100").json())

    def boom(*a, **k):
        raise StorageError("disk on fire")

    monkeypatch.setattr(main_module.storage, "_sandbox_commit", boom)
    res = _count(c, item, item["on_hand"] + 1)
    assert res.status_code >= 500
    monkeypatch.undo()
    monkeypatch.setattr(main_module.storage, "sandbox", True)
    monkeypatch.setattr(main_module.audit_ledger, "sandbox", True)
    after = len(c.get("/api/audit-log?region=lucknow&limit=100").json())
    assert after == before


def test_region_switch_has_no_side_effects(sandboxed):
    a, b = _client(), _client()
    a.post("/api/region/switch", json={"region": "bhubaneswar"})
    a.post("/api/region/switch", json={"region": "lucknow"})
    assert [e["event_type"] for e in a.get("/api/audit-log?region=lucknow&limit=100").json()] == ["GENESIS"]
    assert main_module.active_region_id == "lucknow"


def test_ledger_per_region_verifies(sandboxed):
    c = _client()
    _count(c, _first_item(c), _first_item(c)["on_hand"] + 2)
    bbs = c.get("/api/clinic/PHC-BBS-01/desk").json()["inventory"][0]
    c.post("/api/clinic/PHC-BBS-01/stock-action", json={
        "facility_id": "PHC-BBS-01", "medicine_id": bbs["medicine_id"], "batch_number": bbs["batch_number"],
        "action_type": "PHYSICAL_COUNT", "quantity": bbs["on_hand"] + 2, "reason": "t"})
    for reg in ("lucknow", "bhubaneswar"):
        v = c.get(f"/api/audit-log/verify?region={reg}").json()
        assert v["valid"] is True and v["total_blocks"] >= 2


def test_audit_log_first_then_desk(sandboxed):
    c = _client()
    assert c.get("/api/audit-log?region=lucknow").status_code == 200
    res = c.get(f"/api/clinic/{FAC}/desk")
    assert res.status_code == 200 and res.json()["inventory"]
