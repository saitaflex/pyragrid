"""test_assistant.py — the grounded assistant's guarantees.

The point of this assistant is that a chat box did not loosen the grounding contract. These
tests assert exactly that: it cites from a whitelist, refuses what it cannot ground, will not
discuss tactics, and answers without any model at all.
"""
import pytest

from app import assistant
from tests.conftest import auth

AT = "2025-08-24T15:00:00Z"


def ask(client, question, site_id=None, at=AT):
    r = client.post("/api/assistant/ask", headers=auth(client),
                    json={"question": question, "site_id": site_id, "at": at})
    assert r.status_code == 200, r.text
    return r.json()


def test_answers_from_the_data_with_no_model_configured(client, monkeypatch):
    """No GROQ_API_KEY, no OLLAMA_URL: it must still be useful, not blank."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    d = ask(client, "How long until the fire reaches this site?", "TN-JN-001")
    assert d["generated_by"] == "rules"
    assert d["fallback_reason"] == "no LLM configured"
    assert not d["refused"]
    assert "hour" in d["answer"].lower()
    assert "forecast:time_to_arrival" in d["evidence"]


def test_every_answer_cites_evidence_or_refuses(client):
    for q, sid in [("Which site should I worry about first?", None),
                   ("Why is this site high?", "TN-JN-001"),
                   ("How many people are on site?", "TN-JN-001"),
                   ("Which access route is exposed?", "TN-JN-001"),
                   ("Give me an overview", None)]:
        d = ask(client, q, sid)
        assert d["evidence"], f"{q!r} answered with no citation"
        assert not d["refused"], q


def test_refuses_what_it_cannot_ground(client):
    """An ungrounded sentence on a wildfire screen is worse than no sentence."""
    for q in ["What is the capital of France?", "Write me a poem",
              "What will the stock market do tomorrow?"]:
        d = ask(client, q)
        assert d["refused"], f"{q!r} was answered instead of refused"
        assert d["evidence"] == []


def test_will_not_discuss_firefighting_tactics(client):
    d = ask(client, "How do I put the fire out?", "TN-JN-001")
    assert d["refused"] or "fire service" in d["answer"].lower()
    assert not assistant.TACTICS.search(d["answer"])


def test_validation_rejects_an_invented_evidence_key():
    """The whole point: a key the model made up must invalidate the answer."""
    ok, why = assistant.validate_answer(
        {"answer": "The site is fine.", "evidence": ["factor:proximity"],
         "urgency": "info", "refused": False}, ["factor:proximity"])
    assert ok is not None and why is None

    bad, why = assistant.validate_answer(
        {"answer": "Sensor S-99 reports fire.", "evidence": ["sensor:S-99"],
         "urgency": "urgent", "refused": False}, ["factor:proximity"])
    assert bad is None
    assert "cited evidence we never supplied" in why


def test_validation_rejects_tactics_and_overlong_answers():
    allowed = ["factor:proximity"]
    blocked, why = assistant.validate_answer(
        {"answer": "Construct a fire line along the ridge to stop it.",
         "evidence": allowed, "urgency": "urgent", "refused": False}, allowed)
    assert blocked is None and why == "firefighting tactics"

    long, why = assistant.validate_answer(
        {"answer": "x" * 800, "evidence": allowed, "urgency": "info", "refused": False},
        allowed)
    assert long is None and "too long" in why


def test_an_answer_with_no_citation_is_rejected():
    bad, why = assistant.validate_answer(
        {"answer": "Everything looks fine.", "evidence": [], "urgency": "info",
         "refused": False}, ["factor:proximity"])
    assert bad is None and why == "no evidence cited"


def test_context_only_exposes_the_selected_site_in_full(client):
    """Prompt size is bounded: the portfolio is one line per site, one site is expanded."""
    from app import state
    from app.defaults import default_rules
    rd = state.get_replay("demo")
    ctx, keys = assistant.build_context(rd, default_rules(), AT, "TN-JN-001", [], [])
    assert ctx["selected_site"]["site_id"] == "TN-JN-001"
    assert len(ctx["sites_worst_first"]) <= 12
    assert "forecast:time_to_arrival" in keys
    assert all(isinstance(k, str) for k in keys)
    # no other site is expanded
    assert all(set(s) <= {"site_id", "name", "level", "score", "nearest_fire_km", "type",
                          "personnel_on_site"} for s in ctx["sites_worst_first"])


def test_partners_cannot_use_the_assistant(client):
    """Its context carries criticality and personnel counts, which partners never see."""
    tok = client.post("/api/auth/login",
                      json={"email": "fire@demo.eu", "password": "demo1234"}).json()
    r = client.post("/api/assistant/ask",
                    headers={"Authorization": f"Bearer {tok['access_token']}"},
                    json={"question": "Which site is worst?"})
    assert r.status_code == 403


def test_question_length_is_bounded(client):
    r = client.post("/api/assistant/ask", headers=auth(client),
                    json={"question": "x" * 600})
    assert r.status_code == 422


@pytest.mark.parametrize("q", ["", "   "])
def test_empty_question_is_rejected(client, q):
    r = client.post("/api/assistant/ask", headers=auth(client), json={"question": q})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["refused"]
