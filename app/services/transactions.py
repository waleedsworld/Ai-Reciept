import pandas as pd
import csv
import os
from collections import defaultdict
from app.utils.query_transactions import query_transactions, get_category_map


def list_transactions(instance_id):
    transactions = query_transactions(instance_id)
    return transactions


def create_or_update_budget(instance_id, category_id, limit):
    file_path = "storage/budgets.csv"

    # If file doesn't exist, create it
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=["instance_id", "category_id", "limit"])
    else:
        df = pd.read_csv(file_path)

    # Check if the category already exists for this instance
    match = (df["instance_id"] == instance_id) & (df["category_id"] == category_id)

    if match.any():
        df.loc[match, "limit"] = limit
    else:
        df = pd.concat([
            df,
            pd.DataFrame([{
                "instance_id": instance_id,
                "category_id": category_id,
                "limit": limit
            }])
        ], ignore_index=True)

    df.to_csv(file_path, index=False)


def get_budget_utilisation(instance_id, budgets_csv_path="storage/budgets.csv"):
    # Step 1: Load budgets and filter for this instance
    budgets = []
    with open(budgets_csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if str(row["instance_id"]) == str(instance_id):
                budgets.append({
                    "category_id": int(row["category_id"]),
                    "limit": float(row["limit"])
                })

    # Step 2: Get category names for this instance
    category_map = get_category_map(instance_id)

    # Step 3: Get all transactions for this instance
    tx_response = query_transactions(instance_id, limit=1000000)  # get all
    transactions = tx_response["rows"]

    # Step 4: Calculate total spent per category name
    spent_by_category = defaultdict(float)
    for tx in transactions:
        category = tx["category"]
        spent_by_category[category] += float(tx["amount"])

    # Step 5: Combine budgets + spend
    result = []
    for entry in budgets:
        cat_id = entry["category_id"]
        cat_name = category_map.get(cat_id, "Unknown")
        limit = entry["limit"]
        spent = spent_by_category.get(cat_name, 0.0)
        remaining = limit - spent

        result.append({
            "category": cat_name,
            "limit": limit,
            "spent": round(spent, 2),
            "remaining": round(remaining, 2)
        })

    return result
