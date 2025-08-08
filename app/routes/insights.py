from flask import request, jsonify, Blueprint
from app.utils.llm_advice import llm_advice
from app.services.insights import handle_chat

insights_bp = Blueprint('insights_bp',__name__)


@insights_bp.route('/v1/instances/<id>/advice',methods=['POST'])
def get_advice(id):
    body = request.get_json()
    suggestion = llm_advice(id,body['focus'])
    return jsonify(suggestion),200


@insights_bp.route('/v1/instances/<id>/chat',methods=['POST'])
def chat_with_bot(id):

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400

    message = data["message"]
    resp = handle_chat(id,message)

    return jsonify(resp),200
