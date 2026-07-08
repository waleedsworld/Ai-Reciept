"""End-to-end user journey through the public API.

Mirrors the real workflow: create a workspace, seed categories, upload &
parse a receipt (parser mocked — no OpenAI), then read the data back through
transactions and reports.  The receipt image save + CSV persistence are all
real.
"""

import io

import app.services.reciepts as reciepts_mod


def test_full_journey(client, auth, seed_categories, monkeypatch):
    # 1. Create a workspace.
    iid = client.post("/v1/instances", json={"name": "Trip"}, headers=auth).get_json()[
        "instance_id"
    ]

    # 2. Give it categories via the API.
    cats = client.post(
        f"/v1/instances/{iid}/initialize",
        json={"categories": "Food, Transport"},
        headers=auth,
    ).get_json()["categories"]
    food_id = next(c["id"] for c in cats if c["name"] == "Food")

    # 3. Mock the LLM receipt parser with a deterministic parse.
    def fake_parser(img_url, instance_id):
        return {
            "date": "2024-02-10",
            "total": 8.0,
            "items": [
                {"text": "Apples", "price": 5.0, "category_id": food_id},
                {"text": "Bananas", "price": 3.0, "category_id": food_id},
            ],
        }

    monkeypatch.setattr(reciepts_mod, "reciept_parser", fake_parser)

    upload = client.post(
        "/v1/reciepts",
        data={
            "reciept": (io.BytesIO(b"fake-image-bytes"), "receipt.jpg"),
            "instance_id": iid,
        },
        content_type="multipart/form-data",
        headers=auth,
    )
    assert upload.status_code == 200
    receipt_id = upload.get_json()["receipt_id"]
    assert len(upload.get_json()["items"]) == 2

    # 4. The parsed receipt is retrievable.
    got = client.get(f"/v1/reciepts/{receipt_id}")
    assert got.status_code == 200
    assert got.get_json()["JSON"]["receipt_id"] == receipt_id

    # 5. Transactions now reflect the uploaded line items.
    tx = client.get(f"/v1/instances/{iid}/transactions").get_json()
    assert tx["total_rows"] == 2
    texts = {row["text"] for row in tx["rows"]}
    assert texts == {"Apples", "Bananas"}

    # 6. The report totals it all up.
    report = client.get(f"/v1/instances/{iid}/reports?period=all").get_json()
    assert report["total_spent"] == 8.0


def test_upload_requires_auth(client):
    resp = client.post(
        "/v1/reciepts",
        data={"reciept": (io.BytesIO(b"x"), "r.jpg"), "instance_id": "abc"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_upload_requires_file(client, auth):
    resp = client.post(
        "/v1/reciepts",
        data={"instance_id": "abc"},
        content_type="multipart/form-data",
        headers=auth,
    )
    assert resp.status_code == 400
