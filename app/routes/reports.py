from flask import Blueprint, request,jsonify,send_file,abort
import os
from app.services.graphs import get_bar_chart_data ,get_line_chart_data,get_pie_chart_data
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server environments
import matplotlib.pyplot as plt
from app.services.reports import instance_report


report_bp = Blueprint('report_bp',__name__)

@report_bp.route("/v1/instances/<id>/reports", methods=["GET"])
def get_instance_reports(id):
    period = request.args.get("period", "monthly")
    start = request.args.get("start")
    end = request.args.get("end")

    report_data = instance_report(id, period, start, end)
    return jsonify(report_data),200
   


CHARTS_PATH = "storage/charts"

def save_chart(fig, filename):
    os.makedirs(CHARTS_PATH, exist_ok=True)
    full_path = os.path.join(CHARTS_PATH, filename)
    fig.savefig(full_path, bbox_inches='tight')
    plt.close(fig)
    return f"/{CHARTS_PATH}/{filename}"  # relative URL


@report_bp.route('/v1/instances/<instance_id>/graphs',methods=['GET'])
def get_graph_data(instance_id):
    chart_type = 'pie'
    if chart_type == "pie":
        return get_pie_chart_data(instance_id)
    elif chart_type == "bar":
        return get_bar_chart_data(instance_id)
    elif chart_type == "line":
        return get_line_chart_data(instance_id)
    else:
        return {"error": "Invalid chart type"}, 400
    

@report_bp.route('/v1/instances/<instance_id>/export', methods=['GET'])
def export_csv(instance_id):
    """
    Streams a raw CSV file for the given instance ID.
    Expects the CSV to be located at 'storage/instances/{instance_id}.csv'.
    """

    csv_path = f'storage/instances/{instance_id}.csv'

    # Check if file exists
    if not os.path.isfile(csv_path):
        abort(404, description="CSV file not found.")

    try:
        return send_file(
            csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{instance_id}.csv'
        )
    except Exception as e:
        abort(500, description=f"An error occurred while streaming the file: {str(e)}")
