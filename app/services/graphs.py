from app.services.aggregators.category import category_totals
import pandas as pd

def get_pie_chart_data(instance_id):
    """
    Pie chart data showing total spend per category.
    """
    df = pd.read_csv(f"storage/instances/{instance_id}.csv")

    data = category_totals(df,instance_id)  # [{'category_id': 4, 'total': 1246.0}, ...]
    return {
        "type": "pie",
        "data": [
            {
                "label": f"Category {entry['category_name']}",
                "value": entry["total"]
            }
            for entry in data
        ]
    }


from app.services.aggregators.summary import monthly_spend

def get_bar_chart_data(instance_id):
    """
    Bar chart data showing total spend per month.
    """
    df = pd.read_csv(f"storage/instances/{instance_id}.csv")
    data = monthly_spend(df)  # [{'month': '2024-02', 'total': 1246.0}, ...]
    return {
        "type": "bar",
        "data": [
            {
                "label": entry["month"],
                "value": entry["total"]
            }
            for entry in data
        ]
    }


from app.services.aggregators.summary import daily_spend

def get_line_chart_data(instance_id):
    """
    Line chart data showing total spent per day.
    """
    df = pd.read_csv(f"storage/instances/{instance_id}.csv")
    data = daily_spend(df)  # [{'date': '2024-02-25', 'total_spent': 317.0}, ...]
    return {
        "type": "line",
        "data": [
            {
                "label": entry["date"],
                "value": entry["total_spent"]
            }
            for entry in data
        ]
    }
