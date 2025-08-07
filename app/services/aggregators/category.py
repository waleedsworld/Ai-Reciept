import pandas as pd
from app.utils.query_transactions import get_category_map


def category_totals(df: pd.DataFrame, instance_id: str) -> list[dict]:
    category_map = get_category_map(instance_id)

    df = df.dropna(subset=["category_id", "amount"])
    df["category_id"] = df["category_id"].astype(int)

    grouped = (
        df.groupby("category_id")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    grouped["category_name"] = grouped["category_id"].map(category_map)
    grouped = grouped.drop(columns=["category_id"])
    grouped["total"] = grouped["total"].round(2)

    return grouped[["category_name", "total"]].to_dict(orient="records")


def category_monthly(df: pd.DataFrame, instance_id: str) -> list[dict]:
    category_map = get_category_map(instance_id)

    df = df.dropna(subset=["date", "amount", "category_id"])
    df["date"] = pd.to_datetime(df["date"])
    df["category_id"] = df["category_id"].astype(int)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    grouped = (
        df.groupby(["category_id", "month"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    grouped["category_name"] = grouped["category_id"].map(category_map)
    grouped["total"] = grouped["total"].round(2)
    grouped = grouped.drop(columns=["category_id"])

    return grouped[["category_name", "month", "total"]].to_dict(orient="records")


def category_weekly(df: pd.DataFrame, instance_id: str) -> list[dict]:
    category_map = get_category_map(instance_id)

    df = df.dropna(subset=["date", "amount", "category_id"])
    df["date"] = pd.to_datetime(df["date"])
    df["category_id"] = df["category_id"].astype(int)
    df["year_week"] = df["date"].dt.strftime("%G-W%V")

    grouped = (
        df.groupby(["category_id", "year_week"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    grouped["category_name"] = grouped["category_id"].map(category_map)
    grouped["total"] = grouped["total"].round(2)
    grouped = grouped.drop(columns=["category_id"])

    return grouped[["category_name", "year_week", "total"]].to_dict(orient="records")


def category_overages(data_df: pd.DataFrame, budgets_df: pd.DataFrame, instance_id: str) -> dict:
    category_map = get_category_map(instance_id)

    data_df = data_df.dropna(subset=["date", "amount", "category_id"])
    data_df["date"] = pd.to_datetime(data_df["date"]).dt.date
    data_df["category_id"] = data_df["category_id"].astype(int)

    budgets_df["category_id"] = budgets_df["category_id"].astype(int)

    merged = data_df.merge(budgets_df, how="left", on="category_id")

    grouped = merged.groupby(["date", "category_id"]).agg({
        "amount": "sum",
        "limit": "first"
    }).reset_index()

    def check_exceeded(row):
        if pd.isna(row["limit"]):
            return None
        return row["amount"] > row["limit"]

    grouped["exceeded"] = grouped.apply(check_exceeded, axis=1)

    result = {}
    for _, row in grouped.iterrows():
        day_str = str(row["date"])
        category_name = category_map.get(row["category_id"], "Uncategorized")

        if day_str not in result:
            result[day_str] = {}

        result[day_str][category_name] = {
            "spent": float(row["amount"]),
            "limit": None if pd.isna(row["limit"]) else float(row["limit"]),
            "exceeded": row["exceeded"]
        }

    return result
