"""Global daily AI budget (one always-on instance), and the health route."""
import pytest
from fastapi.testclient import TestClient

import app.llm as llm
import app.main as main_module

client = TestClient(main_module.app)


@pytest.fixture
def spent(monkeypatch):
    monkeypatch.setattr(llm, "AI_DAILY_CALL_BUDGET", 3)
    monkeypatch.setattr(main_module, "_llm_hits", {})
    llm.reset_ai_budget()
    for _ in range(3):
        assert llm.consume_ai_budget() is True
    yield
    llm.reset_ai_budget()


def test_budget_counts_down(monkeypatch):
    monkeypatch.setattr(llm, "AI_DAILY_CALL_BUDGET", 2)
    llm.reset_ai_budget()
    assert [llm.consume_ai_budget() for _ in range(3)] == [True, True, False]
    llm.reset_ai_budget()


def test_budget_resets_next_day(monkeypatch):
    monkeypatch.setattr(llm, "AI_DAILY_CALL_BUDGET", 1)
    llm.reset_ai_budget()
    assert llm.consume_ai_budget() is True and llm.consume_ai_budget() is False
    monkeypatch.setattr(llm, "_today", lambda: "2099-01-01")
    assert llm.consume_ai_budget() is True
    llm.reset_ai_budget()


def test_provider_not_called_when_spent(spent, monkeypatch):
    called = []
    monkeypatch.setattr(llm, "_gemini", lambda: called.append(1))
    monkeypatch.setattr(llm, "_claude", lambda: called.append(1))
    import asyncio
    from pydantic import BaseModel

    class S(BaseModel):
        x: int

    assert asyncio.run(llm.generate_json("s", "u", S)) is None
    assert called == []


def test_budget_exhausted_chat_falls_back(spent):
    res = client.post("/api/cmo/chat?scenario=smog", json={"question": "Which clinics run out first?", "region": "lucknow"})
    assert res.status_code == 200
    assert "no LLM" in res.json()["answered_by"]


def test_tts_429_when_spent(spent):
    res = client.post("/api/cmo/speak", json={"text": "Namaste"})
    assert res.status_code == 429
    assert "budget" in res.json()["detail"].lower()


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200 and res.json()["status"] == "ok"


def test_gemini_uses_vertex_on_cloud_run(monkeypatch):
    """On Cloud Run Gemini goes through Vertex AI with the service account: no API key is copied anywhere."""
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    made = {}

    class FakeClient:
        def __init__(self, **kwargs):
            made.update(kwargs)

    import google.genai as genai
    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(llm, "_gemini_client", None)
    assert llm.provider_status()["gemini"] is True
    assert llm._gemini() is not None
    assert made == {"vertexai": True, "project": "demo-project", "location": "global"}
    monkeypatch.setattr(llm, "_gemini_client", None)


def test_client_ip_on_cloud_run_ignores_spoofed_headers(monkeypatch):
    """Google's front end appends the real client IP as the last X-Forwarded-For entry; x-real-ip is client-set there."""
    from starlette.requests import Request
    monkeypatch.setenv("K_SERVICE", "aarogya-vayu-2036")
    scope = {"type": "http", "headers": [(b"x-real-ip", b"1.1.1.1"), (b"x-forwarded-for", b"9.9.9.9, 203.0.113.7")],
             "client": ("169.254.1.1", 1234)}
    assert main_module.client_ip(Request(scope)) == "203.0.113.7"
