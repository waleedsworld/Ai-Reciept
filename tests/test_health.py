"""Health endpoint and landing pages."""

from datetime import datetime


def test_health_ok(client):
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    # "time" is a valid ISO-8601 timestamp.
    datetime.fromisoformat(body["time"])


def test_landing_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"


def test_upload_page_renders(client):
    resp = client.get("/upload")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
