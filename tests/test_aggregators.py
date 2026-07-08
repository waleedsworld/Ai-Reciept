"""Unit tests for the pure DataFrame aggregation helpers."""

import csv
import os

import pandas as pd

from app.services.aggregators.items import top_items
from app.services.aggregators.summary import (
    total_spend,
    daily_spend,
    weekly_spend,
    monthly_spend,
)
from app.services.aggregators.category import category_totals


def _frame():
    return pd.DataFrame(
        [
            {"date": "2024-02-01", "text": "Milk", "amount": 3.0, "category_id": 1, "receipt_id": "r1"},
            {"date": "2024-02-01", "text": "Milk", "amount": 3.0, "category_id": 1, "receipt_id": "r2"},
            {"date": "2024-02-02", "text": "Bus", "amount": 2.0, "category_id": 2, "receipt_id": "r3"},
            {"date": "2024-03-05", "text": "Bread", "amount": 4.0, "category_id": 1, "receipt_id": "r4"},
        ]
    )


def _write_categories(instance_id, mapping):
    path = os.path.join("storage", "categories.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance_id", "id", "name"])
        w.writeheader()
        for cid, name in mapping.items():
            w.writerow({"instance_id": instance_id, "id": cid, "name": name})


def test_total_spend():
    assert total_spend(_frame()) == {"total_spent": 12.0, "currency": "PKR"}


def test_total_spend_missing_column_raises():
    import pytest

    with pytest.raises(ValueError):
        total_spend(pd.DataFrame({"foo": [1]}))


def test_top_items_ranks_by_count():
    items = top_items(_frame())
    assert items[0]["item"] == "Milk"
    assert items[0]["count"] == 2
    assert items[0]["total_spent"] == 6.0


def test_top_items_empty():
    assert top_items(pd.DataFrame()) == []


def test_daily_spend():
    result = daily_spend(_frame())
    by_date = {r["date"]: r["total_spent"] for r in result}
    assert by_date["2024-02-01"] == 6.0
    assert by_date["2024-02-02"] == 2.0


def test_daily_spend_empty():
    assert daily_spend(pd.DataFrame()) == []


def test_monthly_spend():
    result = monthly_spend(_frame())
    by_month = {r["month"]: r["total"] for r in result}
    assert by_month["2024-02"] == 8.0
    assert by_month["2024-03"] == 4.0


def test_weekly_spend_shape():
    result = weekly_spend(_frame())
    assert all("week" in r and "total" in r for r in result)
    assert sum(r["total"] for r in result) == 12.0


def test_category_totals_maps_names():
    _write_categories("inst-1", {1: "Food", 2: "Transport"})
    result = category_totals(_frame(), "inst-1")
    by_name = {r["category_name"]: r["total"] for r in result}
    assert by_name["Food"] == 10.0
    assert by_name["Transport"] == 2.0
