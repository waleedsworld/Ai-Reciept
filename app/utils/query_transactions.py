import pandas as pd
import os
import csv


def get_category_map(instance_id, csv_path="storage/categories.csv"):
    category_map = {}

    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['instance_id'] == instance_id:
                category_id = int(row['id'])
                category_name = row['name']
                category_map[category_id] = category_name

    return category_map


def query_transactions(instance_id, date=None, category_id=None, offset=0, limit=50):
    csv_path = f"storage/instances/{instance_id}.csv"

    if not os.path.exists(csv_path):
        return {"error": f"CSV not found for instance_id: {instance_id}"}, 404

    # Get category_id -> name mapping
    categories = get_category_map(instance_id)

    # Load the CSV into a DataFrame
    df = pd.read_csv(csv_path)

    # Apply filters
    if date:
        df = df[df['date'] == date]

    if category_id is not None:
        df = df[df['category_id'] == category_id]

    total_rows = len(df)

    # Apply pagination
    paginated_df = df.iloc[offset:offset + limit]

    # Format response and map category_id to category name
    rows = []
    for _, row in paginated_df.iterrows():
        category_name = categories.get(row['category_id'], "Unknown")
        rows.append({
            "date": row["date"],
            "text": row["text"],
            "amount": row["amount"],
            "category": category_name
        })

    return {
        "rows": rows,
        "total_rows": total_rows
    }
