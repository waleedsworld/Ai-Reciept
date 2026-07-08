"""Category management: initialize / add / rename / delete."""


def test_initialize_categories(client, auth, make_workspace):
    iid = make_workspace("Cat")
    resp = client.post(
        f"/v1/instances/{iid}/initialize",
        json={"categories": "Food, Transport, Fun"},
        headers=auth,
    )
    assert resp.status_code == 200
    names = [c["name"] for c in resp.get_json()["categories"]]
    assert names == ["Food", "Transport", "Fun"]


def test_initialize_dedupes(client, auth, make_workspace):
    iid = make_workspace("Cat")
    client.post(
        f"/v1/instances/{iid}/initialize",
        json={"categories": "Food, Transport"},
        headers=auth,
    )
    # Re-seeding the same names adds nothing new.
    resp = client.post(
        f"/v1/instances/{iid}/initialize",
        json={"categories": "Food, Transport"},
        headers=auth,
    )
    assert resp.status_code == 200
    assert "No new categories" in resp.get_json()["message"]


def test_initialize_empty_rejected(client, auth, make_workspace):
    iid = make_workspace("Cat")
    resp = client.post(
        f"/v1/instances/{iid}/initialize", json={"categories": "  , ,"}, headers=auth
    )
    assert resp.status_code == 400


def test_initialize_requires_auth(client, make_workspace):
    iid = make_workspace("Cat")
    resp = client.post(f"/v1/instances/{iid}/initialize", json={"categories": "Food"})
    assert resp.status_code == 403


def test_add_category(client, auth, make_workspace):
    iid = make_workspace("Cat")
    resp = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "Books"}, headers=auth
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Books"
    assert isinstance(body["id"], int)


def test_add_duplicate_category_rejected(client, auth, make_workspace):
    iid = make_workspace("Cat")
    client.post(f"/v1/instances/{iid}/categories", json={"name": "Books"}, headers=auth)
    resp = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "books"}, headers=auth
    )
    assert resp.status_code == 400


def test_add_category_missing_name(client, auth, make_workspace):
    iid = make_workspace("Cat")
    resp = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "   "}, headers=auth
    )
    assert resp.status_code == 400


def test_rename_category(client, auth, make_workspace):
    iid = make_workspace("Cat")
    add = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "Grocery"}, headers=auth
    ).get_json()
    cat_id = add["id"]

    resp = client.put(f"/v1/categories/{cat_id}", json={"name": "Groceries"}, headers=auth)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Groceries"


def test_rename_missing_category(client, auth, make_workspace):
    iid = make_workspace("Cat")
    client.post(f"/v1/instances/{iid}/categories", json={"name": "One"}, headers=auth)
    resp = client.put("/v1/categories/9999", json={"name": "Nope"}, headers=auth)
    assert resp.status_code == 404


def test_delete_category(client, auth, make_workspace):
    iid = make_workspace("Cat")
    # Need at least two categories — one must always remain.
    client.post(f"/v1/instances/{iid}/categories", json={"name": "Keep"}, headers=auth)
    drop = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "Drop"}, headers=auth
    ).get_json()

    resp = client.delete(f"/v1/categories/{drop['id']}", headers=auth)
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] is True


def test_cannot_delete_last_category(client, auth, make_workspace):
    iid = make_workspace("Cat")
    only = client.post(
        f"/v1/instances/{iid}/categories", json={"name": "Solo"}, headers=auth
    ).get_json()
    resp = client.delete(f"/v1/categories/{only['id']}", headers=auth)
    assert resp.status_code == 400


def test_category_routes_require_auth(client):
    assert client.put("/v1/categories/1", json={"name": "X"}).status_code == 403
    assert client.delete("/v1/categories/1").status_code == 403
