"""Transaction listing and budget tracking."""


def _seed_instance(make_workspace, seed_categories, seed_transactions):
    iid = make_workspace("Spend")
    cats = seed_categories(iid, ["Food", "Transport"])
    seed_transactions(
        iid,
        [
            {"date": "2024-02-01", "text": "Milk", "amount": 3.5,
             "category_id": cats["Food"], "receipt_id": "r1"},
            {"date": "2024-02-02", "text": "Bus", "amount": 2.0,
             "category_id": cats["Transport"], "receipt_id": "r2"},
            {"date": "2024-02-03", "text": "Bread", "amount": 1.5,
             "category_id": cats["Food"], "receipt_id": "r3"},
        ],
    )
    return iid, cats


def test_list_transactions(client, make_workspace, seed_categories, seed_transactions):
    iid, _ = _seed_instance(make_workspace, seed_categories, seed_transactions)
    resp = client.get(f"/v1/instances/{iid}/transactions")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total_rows"] == 3
    # category_id is mapped to a human-readable name.
    categories = {row["category"] for row in body["rows"]}
    assert categories == {"Food", "Transport"}


def test_create_budget(client, make_workspace, seed_categories, seed_transactions):
    iid, cats = _seed_instance(make_workspace, seed_categories, seed_transactions)
    resp = client.post(
        f"/v1/instances/{iid}/budgets",
        json={"category_id": cats["Food"], "limit": 100},
    )
    assert resp.status_code == 200


def test_create_budget_missing_fields(client, make_workspace):
    iid = make_workspace("B")
    resp = client.post(f"/v1/instances/{iid}/budgets", json={"limit": 100})
    assert resp.status_code == 400


def test_budget_utilisation(client, make_workspace, seed_categories, seed_transactions):
    iid, cats = _seed_instance(make_workspace, seed_categories, seed_transactions)
    client.post(
        f"/v1/instances/{iid}/budgets",
        json={"category_id": cats["Food"], "limit": 10},
    )

    resp = client.get(f"/v1/instances/{iid}/budgets")
    assert resp.status_code == 200
    details = resp.get_json()["Details"]
    food = next(d for d in details if d["category"] == "Food")
    # Food spend = 3.5 + 1.5 = 5.0, limit 10 -> remaining 5.0
    assert food["spent"] == 5.0
    assert food["limit"] == 10.0
    assert food["remaining"] == 5.0


def test_budget_update_overwrites(client, make_workspace, seed_categories, seed_transactions):
    iid, cats = _seed_instance(make_workspace, seed_categories, seed_transactions)
    client.post(f"/v1/instances/{iid}/budgets", json={"category_id": cats["Food"], "limit": 10})
    client.post(f"/v1/instances/{iid}/budgets", json={"category_id": cats["Food"], "limit": 50})

    details = client.get(f"/v1/instances/{iid}/budgets").get_json()["Details"]
    food = next(d for d in details if d["category"] == "Food")
    assert food["limit"] == 50.0
