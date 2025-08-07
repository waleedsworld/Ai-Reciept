import pandas as pd
from app.utils.query_transactions import get_category_map

def total_spend(df: pd.DataFrame) -> dict:
    """
    Compute the total amount spent in the dataframe.

    Parameters:
        df (pd.DataFrame): Must contain a column 'amount'.

    Returns:
        dict: A dictionary with total amount spent.
    """
    if 'amount' not in df.columns:
        raise ValueError("Missing 'amount' column in dataframe.")
    total = float(df['amount'].fillna(0).sum())  # ✅ Explicitly cast to native float
    return {
        "total_spent": round(total, 2),
        "currency": "PKR"
    }



def daily_spend(df: pd.DataFrame) -> list[dict]:
    """
    Returns daily total spend with date formatted as a string.
    """
    if df.empty:
        return []

    # Ensure 'date' is in datetime format and extract only the date part
    df['date'] = pd.to_datetime(df['date']).dt.date

    # Group by date and sum
    grouped = (
        df.groupby('date')['amount']
        .sum()
        .reset_index()
        .rename(columns={'amount': 'total_spent'})
        .sort_values(by='date')
    )

    # Convert date to ISO string
    grouped['date'] = grouped['date'].apply(lambda x: x.isoformat())

    return grouped.to_dict(orient='records')




def weekly_spend(df: pd.DataFrame) -> list[dict]:
    # Step 1: Ensure date is datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Step 2: Clean amount
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Step 3: Extract ISO week and year
    df["year"] = df["date"].dt.isocalendar().year
    df["week"] = df["date"].dt.isocalendar().week
    df["year_week"] = df["year"].astype(str) + "-W" + df["week"].astype(str).str.zfill(2)

    # Step 4: Group by week and sum
    grouped = df.groupby("year_week", as_index=False)["amount"].sum()

    # Step 5: Format output
    grouped.rename(columns={"amount": "total", "year_week": "week"}, inplace=True)
    return grouped.to_dict(orient="records")


def monthly_spend(df: pd.DataFrame) -> list[dict]:
    # Step 1: Ensure 'date' is datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Step 2: Clean 'amount'
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Step 3: Create 'year_month' column
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    # Step 4: Group by month and sum
    grouped = df.groupby("year_month", as_index=False)["amount"].sum()

    # Step 5: Format output
    grouped.rename(columns={"year_month": "month", "amount": "total"}, inplace=True)
    return grouped.to_dict(orient="records")




import pandas as pd
from app.utils.query_transactions import get_category_map

def receipt_summary(df: pd.DataFrame, id: str) -> list[dict]:
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Get category_id -> category_name mapping
    category_map = get_category_map(id)

    result = []

    for rid, group in df.groupby("receipt_id"):
        receipt = {
            "receipt_id": rid,
            "date": group["date"].min().date().isoformat(),
            "total": float(round(group["amount"].sum(), 2)),
            "items": []
        }

        for _, row in group.iterrows():
            category_id = row.get("category_id", -1)
            category_name = category_map.get(category_id, "Uncategorized")

            receipt["items"].append({
                "name": row.get("text", "Unknown"),
                "category": category_name,
                "amount": round(row["amount"], 2)
            })

        result.append(receipt)

    return result
