import pandas as pd

def top_items(df: pd.DataFrame, top_n: int = 5) -> list[dict]:
    if df.empty or 'text' not in df.columns or 'amount' not in df.columns:
        return []

    item_stats = (
        df.groupby("text")
        .agg(count=("text", "count"), total_spent=("amount", "sum"))
        .sort_values(by="count", ascending=False)
        .head(top_n)
        .reset_index()
    )

    return [
        {"item": row["text"], "count": int(row["count"]), "total_spent": float(row["total_spent"])}
        for _, row in item_stats.iterrows()
    ]
