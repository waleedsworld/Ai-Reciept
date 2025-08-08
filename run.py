from flask import Flask, request,jsonify,render_template
from app.routes.workspace import workspace_bp
from app.routes.categories import categories_dp
from app.routes.reciepts import reciepts_bp
from app.routes.transactions import transaction_bp
from app.routes.reports import report_bp
from app.routes.insights import insights_bp
from app.utils.save_reciept_image import save_receipt_image
from app.utils.reciept_parser import reciept_parser
from datetime import datetime,timezone

app = Flask(__name__)

app.register_blueprint(workspace_bp)
app.register_blueprint(categories_dp)
app.register_blueprint(reciepts_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(report_bp)
app.register_blueprint(insights_bp)

@app.route("/")
def runApp():
    return "APP running Successfully"

@app.route('/v1/health',methods=['GET'])
def check_health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat()
    }



# testing image upload
@app.route("/upload", methods=["GET", "POST"])
def upload_receipt():
    if request.method == "POST":
        file = request.files.get("reciept")
        if not file:
            return "No file uploaded", 400
        receipt_id, path = save_receipt_image(file)
        img_url = path.split('\\')[1]
        extracted =reciept_parser(img_url)
        return jsonify({"receipt_id": receipt_id, "path": path,"json":extracted})
    
    return render_template("upload.html")


app.run(debug=True)
