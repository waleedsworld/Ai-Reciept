"""AI insight endpoints (advice + chat) with the OpenAI client mocked out.

These exercise the full request path — routing, instance_report context
assembly, response shaping — without ever calling the network.
"""

import types

import pytest

import app.utils.llm_advice as llm_advice_mod
import app.services.insights as insights_mod


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def _fake_openai(content):
    """Build a stand-in exposing chat.completions.create -> canned content."""
    fake = types.SimpleNamespace()
    fake.chat = types.SimpleNamespace()
    fake.chat.completions = types.SimpleNamespace(
        create=lambda *a, **k: _FakeResponse(content)
    )
    return fake


@pytest.fixture
def seeded_instance(make_workspace, seed_categories, seed_transactions, seed_budget):
    iid = make_workspace("Insights")
    cats = seed_categories(iid, ["Food"])
    seed_transactions(
        iid,
        [
            {"date": "2024-02-01", "text": "Milk", "amount": 3.5,
             "category_id": cats["Food"], "receipt_id": "r1"},
        ],
    )
    seed_budget([{"instance_id": iid, "category_id": cats["Food"], "limit": 5}])
    return iid


def test_advice_returns_suggestions(client, seeded_instance, monkeypatch):
    monkeypatch.setattr(
        llm_advice_mod, "openai", _fake_openai('{"suggestions": "Cut back on snacks."}')
    )
    resp = client.post(
        f"/v1/instances/{seeded_instance}/advice", json={"focus": "groceries"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["suggestions"] == "Cut back on snacks."


def test_chat_returns_reply(client, seeded_instance, monkeypatch):
    monkeypatch.setattr(
        insights_mod, "openai", _fake_openai("You spent 3.5 on Food.")
    )
    resp = client.post(
        f"/v1/instances/{seeded_instance}/chat", json={"message": "How much on food?"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["response"] == "You spent 3.5 on Food."


def test_chat_missing_message(client, seeded_instance):
    resp = client.post(f"/v1/instances/{seeded_instance}/chat", json={})
    assert resp.status_code == 400
