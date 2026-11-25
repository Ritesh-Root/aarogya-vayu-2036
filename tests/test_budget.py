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
