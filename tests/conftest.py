"""Shared pytest fixtures for the Receipt Spending Analyzer test-suite.

The application persists everything to relative ``storage/`` paths resolved
against the current working directory.  To keep every test hermetic we chdir
into a fresh ``tmp_path`` (autouse ``isolated_storage`` fixture) and lay down
the folder skeleton the app expects, so tests never touch the developer's real
data and never leak state into one another.
"""

import os
import csv
import json

import pytest

# Import the singleton Flask app once.  The heavy import (pandas, matplotlib)
# happens a single time for the whole session.
from run import app as flask_app


# Column layouts used across the CSV/JSON storage layer.
INSTANCE_COLUMNS = ["date", "text", "amount", "category_id", "receipt_id"]
CATEGORY_COLUMNS = ["instance_id", "id", "name"]
BUDGET_COLUMNS = ["instance_id", "category_id", "limit"]


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Run every test inside its own throwaway storage root."""
    monkeypatch.chdir(tmp_path)
    for sub in ("storage", "storage/instances", "storage/receipts/uploads", "storage/charts"):
        os.makedirs(tmp_path / sub, exist_ok=True)
    # instance_report / budget utilisation read this unconditionally.
    _write_csv(tmp_path / "storage" / "budgets.csv", BUDGET_COLUMNS, [])
    yield tmp_path


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth():
    """Authorization header for the default demo user ('demo-user')."""
    return {"Authorization": "Bearer demo-user"}


# --------------------------------------------------------------------------- #
# Low-level storage helpers (write CSV/JSON straight to disk for seeding).     #
# --------------------------------------------------------------------------- #
def _write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


@pytest.fixture
def make_workspace(client, auth):
    """Create a workspace through the API and return its instance_id."""

    def _make(name="Groceries"):
        resp = client.post("/v1/instances", json={"name": name}, headers=auth)
        assert resp.status_code == 201, resp.get_data(as_text=True)
        return resp.get_json()["instance_id"]

    return _make


@pytest.fixture
def seed_categories():
    """Append category rows to storage/categories.csv for an instance."""

    def _seed(instance_id, names):
        path = os.path.join("storage", "categories.csv")
        existing = []
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as fh:
                existing = list(csv.DictReader(fh))
        start = len(existing) + 1
        rows = existing + [
            {"instance_id": instance_id, "id": start + i, "name": name}
            for i, name in enumerate(names)
        ]
        _write_csv(path, CATEGORY_COLUMNS, rows)
        # Return name -> id map for the freshly-added categories.
        return {name: start + i for i, name in enumerate(names)}

    return _seed


@pytest.fixture
def seed_transactions():
    """Overwrite an instance CSV with the given transaction rows.

    ``rows`` is a list of dicts with keys date/text/amount/category_id/receipt_id.
    """

    def _seed(instance_id, rows):
        path = os.path.join("storage", "instances", f"{instance_id}.csv")
        _write_csv(path, INSTANCE_COLUMNS, rows)

    return _seed


@pytest.fixture
def seed_budget():
    """Write budget rows to storage/budgets.csv."""

    def _seed(rows):
        _write_csv(os.path.join("storage", "budgets.csv"), BUDGET_COLUMNS, rows)

    return _seed
