from app.services.graphs import get_bar_chart_data ,get_line_chart_data,get_pie_chart_data
from app.utils.query_transactions import get_category_map
from app.utils.llm_advice import llm_advice
from app.services.reports import instance_report

print(llm_advice('bb007a2b-a94e-4e74-bf1a-0e807fb92f72'))
