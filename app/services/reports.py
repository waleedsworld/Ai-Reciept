from flask import request,jsonify
import pandas as pd
from app.services.aggregators.items import top_items
from app.services.aggregators.category import category_totals,category_overages
from app.services.aggregators.summary import receipt_summary, daily_spend,weekly_spend,monthly_spend


def instance_report(id, period="monthly", start_str=None, end_str=None):
    import pandas as pd

    # Load CSV data
    df = pd.read_csv(f'storage/instances/{id}.csv')
    bdf = pd.read_csv(f'storage/budgets.csv')

    if df is None or df.empty:
        return {"error": "No data found"}, 404

    df["date"] = pd.to_datetime(df["date"])

    # Filter data by period
    if period == "custom" and start_str and end_str:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        df = df[(df["date"] >= start) & (df["date"] <= end)]
    elif period == "weekly":
        start = df["date"].max() - pd.Timedelta(days=6)
        df = df[df["date"] >= start]
    elif period == "monthly":
        start = df["date"].max() - pd.DateOffset(months=1)
        df = df[df["date"] >= start]
    # else: use all data

    # Generate insights
    return {
        "total_spent": df["amount"].sum(),
        "top_items": top_items(df),
        "top_categories": category_totals(df, id),
        "category_overages": category_overages(df, bdf, id),
        "receipt_summary": receipt_summary(df, id),
        "daily_spend": daily_spend(df),
        "weekly_spend": weekly_spend(df),
        "monthly_spend": monthly_spend(df)
    }
