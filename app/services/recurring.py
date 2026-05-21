"""Recurring-charge (subscription) detection.

Turns a flat list of receipt line items into a short list of *recurring*
charges — "you've paid Netflix three months running" — without any LLM.

The idea: a subscription looks like the same thing bought over and over at a
steady cadence. So we group transactions by their (normalised) item text, look
at the gaps between purchases, and keep the ones whose gaps are regular enough
to look like a real repeating charge. For each we estimate the cadence
(weekly / monthly / …), the monthly and annual burden, when the next charge is
due, and whether the price has crept up over time.

Everything here is pure pandas/statistics — no network, no API key — so it
works on the offline CSV store just like the rest of the report math.
"""

from __future__ import annotations

import os
import re
from statistics import mean, pstdev

import pandas as pd

from app.utils.query_transactions import get_category_map

# Average days per period. Used both to name a cadence and to normalise a
# per-charge amount into a comparable "per month" figure.
CADENCES = {
    "daily": 1.0,
    "weekly": 7.0,
    "biweekly": 14.0,
    "monthly": 30.44,
    "quarterly": 91.31,
    "yearly": 365.25,
}

DAYS_PER_MONTH = 30.44
DAYS_PER_YEAR = 365.25
CURRENCY = "PKR"  # matches the rest of the app's reports


def _normalise(text: str) -> str:
    """Collapse a raw item label into a stable grouping key.

    "Netflix  Premium", "netflix premium" and "NETFLIX PREMIUM!" should all land
    in the same bucket, so we lowercase, strip punctuation and squeeze runs of
    whitespace.
    """
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _classify_cadence(median_gap: float):
    """Map a typical gap (in days) to the closest named cadence.

    Returns (name, closeness) where closeness is 1.0 for a perfect match and
    falls off as the gap drifts from any known period. Uses a ratio in log space
    so "off by 2 days on a weekly" is penalised more than on a monthly.
    """
    best_name, best_closeness = "irregular", 0.0
    for name, period in CADENCES.items():
        # Ratio distance, symmetric around 1.0 whether gap is longer or shorter.
        ratio = median_gap / period
        distance = abs(ratio - 1.0)
        closeness = max(0.0, 1.0 - distance)
        if closeness > best_closeness:
            best_name, best_closeness = name, closeness
    return best_name, best_closeness


def _price_trend(first_amount: float, last_amount: float):
    """Describe how the charge has moved from its first to its most recent hit."""
    if first_amount <= 0:
        return "stable", 0.0
    pct = (last_amount - first_amount) / first_amount * 100.0
    if pct >= 5.0:
        trend = "increasing"
    elif pct <= -5.0:
        trend = "decreasing"
    else:
        trend = "stable"
    return trend, round(pct, 2)


def detect_recurring(
    instance_id: str,
    min_occurrences: int = 3,
    max_variability: float = 0.4,
):
    """Find recurring charges for one workspace.

    Parameters
    ----------
    instance_id : str
        Workspace whose transaction CSV we inspect.
    min_occurrences : int
        How many separate purchase days an item needs before it can count as a
        subscription. Three is the sweet spot — two points is just a line.
    max_variability : float
        Cap on the coefficient of variation (stdev / mean) of the gaps between
        purchases. Lower = stricter about how metronome-like a charge must be.

    Returns
    -------
    (payload, status_code)
    """
    csv_path = f"storage/instances/{instance_id}.csv"
    if not os.path.exists(csv_path):
        return {"error": f"No data found for instance_id: {instance_id}"}, 404

    df = pd.read_csv(csv_path)
    if df.empty:
        return _empty_payload(min_occurrences, max_variability), 200

    # Coerce and drop rows we can't reason about.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "amount", "text"])
    if df.empty:
        return _empty_payload(min_occurrences, max_variability), 200

    category_map = get_category_map(instance_id)
    df["key"] = df["text"].apply(_normalise)

    recurring = []
    for key, group in df.groupby("key"):
        if not key:
            continue

        # Collapse multiple same-day buys of the same item into one charge/day,
        # so a double-scan doesn't masquerade as a tiny cadence.
        daily = (
            group.groupby(group["date"].dt.normalize())["amount"]
            .sum()
            .sort_index()
        )
        if len(daily) < min_occurrences:
            continue

        dates = list(daily.index)
        amounts = [float(a) for a in daily.values]

        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        gaps = [g for g in gaps if g > 0]
        if len(gaps) < min_occurrences - 1:
            continue

        avg_gap = mean(gaps)
        median_gap = float(pd.Series(gaps).median())
        gap_sd = pstdev(gaps) if len(gaps) > 1 else 0.0
        variability = gap_sd / avg_gap if avg_gap else 1.0

        # Too erratic to call a subscription.
        if variability > max_variability:
            continue

        cadence, cadence_closeness = _classify_cadence(median_gap)
        if cadence == "irregular":
            continue

        # Confidence blends "how metronome-like" with "how close to a real
        # cadence", nudged up by having more data points to lean on.
        regularity = max(0.0, 1.0 - variability)
        evidence = min(1.0, len(dates) / (min_occurrences + 2))
        confidence = round(
            (0.5 * regularity + 0.3 * cadence_closeness + 0.2 * evidence), 3
        )

        avg_amount = round(mean(amounts), 2)
        last_amount = round(amounts[-1], 2)
        first_amount = round(amounts[0], 2)
        trend, trend_pct = _price_trend(first_amount, last_amount)

        # Normalise this charge to a per-month / per-year figure using its own
        # typical gap, so a weekly coffee and a yearly domain are comparable.
        monthly = round(avg_amount * (DAYS_PER_MONTH / median_gap), 2)
        annual = round(avg_amount * (DAYS_PER_YEAR / median_gap), 2)

        last_date = dates[-1]
        next_expected = (last_date + pd.Timedelta(days=median_gap)).date().isoformat()

        # Most common category for this item (items usually sit in one).
        cat_ids = group["category_id"].dropna()
        category = "Uncategorized"
        if not cat_ids.empty:
            try:
                category = category_map.get(int(cat_ids.mode().iloc[0]), "Uncategorized")
            except (ValueError, TypeError):
                category = "Uncategorized"

        # A human-friendly label: the most frequent original spelling.
        display = group["text"].mode()
        label = str(display.iloc[0]) if not display.empty else key

        recurring.append({
            "item": label,
            "category": category,
            "cadence": cadence,
            "occurrences": len(dates),
            "avg_amount": avg_amount,
            "last_amount": last_amount,
            "avg_interval_days": round(avg_gap, 1),
            "estimated_monthly": monthly,
            "estimated_annual": annual,
            "first_seen": dates[0].date().isoformat(),
            "last_seen": last_date.date().isoformat(),
            "next_expected": next_expected,
            "price_trend": trend,
            "price_change_pct": trend_pct,
            "confidence": confidence,
        })

    # Biggest ongoing money sinks first.
    recurring.sort(key=lambda r: r["estimated_monthly"], reverse=True)

    total_monthly = round(sum(r["estimated_monthly"] for r in recurring), 2)
    total_annual = round(sum(r["estimated_annual"] for r in recurring), 2)

    return {
        "instance_id": instance_id,
        "currency": CURRENCY,
        "recurring_count": len(recurring),
        "total_estimated_monthly": total_monthly,
        "total_estimated_annual": total_annual,
        "params": {
            "min_occurrences": min_occurrences,
            "max_variability": max_variability,
        },
        "recurring": recurring,
    }, 200


def _empty_payload(min_occurrences: int, max_variability: float) -> dict:
    return {
        "currency": CURRENCY,
        "recurring_count": 0,
        "total_estimated_monthly": 0.0,
        "total_estimated_annual": 0.0,
        "params": {
            "min_occurrences": min_occurrences,
            "max_variability": max_variability,
        },
        "recurring": [],
    }
