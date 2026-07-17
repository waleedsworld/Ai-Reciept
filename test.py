"""Tiny offline smoke test — exercises the app without hitting OpenAI.

Run it with the server stopped:  python test.py
It spins up the Flask test client, creates a workspace, seeds categories and
reads them back, so you can confirm the CSV/JSON storage layer works end to end.
"""

from run import app


def main():
    client = app.test_client()
    headers = {"Authorization": "Bearer demo-user"}

    # Health
    assert client.get("/v1/health").get_json()["status"] == "ok"

    # Create a workspace
    r = client.post("/v1/instances", json={"name": "Groceries"}, headers=headers)
    assert r.status_code == 201, r.get_data(as_text=True)
    instance_id = r.get_json()["instance_id"]
    print("Created workspace:", instance_id)

    # Seed some categories
    r = client.post(
        f"/v1/instances/{instance_id}/initialize",
        json={"categories": "Food, Transport, Fun"},
        headers=headers,
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    print("Seeded categories:", [c["name"] for c in r.get_json()["categories"]])

    # List workspaces back
    r = client.get("/v1/instances", headers=headers)
    ids = [w["id"] for w in r.get_json()["instances"]]
    assert instance_id in ids
    print("Smoke test passed ✅")


if __name__ == "__main__":
    main()
