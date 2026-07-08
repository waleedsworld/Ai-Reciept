"""Reports, chart-data endpoints and CSV export."""

import os
import uuid

from run import app as flask_app


def _seed(make_workspace, seed_categories, seed_transactions, seed_budget):
    iid = make_workspace("Report")
    cats = seed_categories(iid, ["Food", "Transport"])
    seed_transactions(
        iid,
        [
            {"date": "2024-02-01", "text": "Milk", "amount": 3.5,
             "category_id": cats["Food"], "receipt_id": "r1"},
            {"date": "2024-02-01", "text": "Bus", "amount": 2.0,
             "category_id": cats["Transport"], "receipt_id": "r1"},
            {"date": "2024-03-15", "text": "Bread", "amount": 4.5,
             "category_id": cats["Food"], "receipt_id": "r2"},
        ],
    )
    seed_budget([{"instance_id": iid, "category_id": cats["Food"], "limit": 5}])
    return iid, cats


def test_instance_report_all_periods(client, make_workspace, seed_categories, seed_transactions, seed_budget):
    iid, _ = _seed(make_workspace, seed_categories, seed_transactions, seed_budget)
    resp = client.get(f"/v1/instances/{iid}/reports?period=all")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total_spent"] == 10.0
    assert isinstance(body["top_items"], list)
    assert isinstance(body["top_categories"], list)
    assert isinstance(body["daily_spend"], list)
    assert isinstance(body["monthly_spend"], list)
    # Two distinct months of activity.
    assert len(body["monthly_spend"]) == 2


def test_instance_report_custom_range(client, make_workspace, seed_categories, seed_transactions, seed_budget):
    iid, _ = _seed(make_workspace, seed_categories, seed_transactions, seed_budget)
    resp = client.get(
        f"/v1/instances/{iid}/reports?period=custom&start=2024-02-01&end=2024-02-28"
    )
    assert resp.status_code == 200
    # Only February rows (3.5 + 2.0) fall in the window.
    assert resp.get_json()["total_spent"] == 5.5


def test_pie_chart_data(client, make_workspace, seed_categories, seed_transactions, seed_budget):
    iid, _ = _seed(make_workspace, seed_categories, seed_transactions, seed_budget)
    resp = client.get(f"/v1/instances/{iid}/graphs")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["type"] == "pie"
    labels = {d["label"] for d in body["data"]}
    assert "Category Food" in labels


def test_export_csv(client):
    # Flask's send_file resolves relative paths against the app root, and the
    # route's existence check is cwd-relative — in real deployments cwd IS the
    # app root, so exercise it that way with a uniquely-named throwaway file.
    root = flask_app.root_path
    inst_dir = os.path.join(root, "storage", "instances")
    os.makedirs(inst_dir, exist_ok=True)
    iid = f"pytest-export-{uuid.uuid4()}"
    csv_path = os.path.join(inst_dir, f"{iid}.csv")
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("date,text,amount,category_id,receipt_id\n")
        fh.write("2024-02-01,Milk,3.5,1,r1\n")
        fh.write("2024-03-15,Bread,4.5,1,r2\n")

    old_cwd = os.getcwd()
    os.chdir(root)
    try:
        resp = client.get(f"/v1/instances/{iid}/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        text = resp.get_data(as_text=True)
        assert "Milk" in text and "Bread" in text
    finally:
        os.chdir(old_cwd)
        os.remove(csv_path)


def test_export_missing_instance_404(client, make_workspace):
    make_workspace("X")
    resp = client.get("/v1/instances/nonexistent/export")
    assert resp.status_code == 404
