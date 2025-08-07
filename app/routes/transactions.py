from flask import request, jsonify,Blueprint
from app.services.transactions import list_transactions,create_or_update_budget,get_budget_utilisation

transaction_bp = Blueprint('transaction_bp',__name__)

@transaction_bp.route('/v1/instances/<id>/transactions',methods=['GET'])
def list_transactions_route(id):
    transaction = list_transactions(id)
    return jsonify(transaction),200


@transaction_bp.route('/v1/instances/<instance_id>/budgets', methods=['POST'])
def create_or_update_budget_route(instance_id):
    data = request.get_json()
    category_id = data.get("category_id")
    limit = data.get("limit")

    if category_id is None or limit is None:
        return {"error": "Missing 'category_id' or 'limit'"}, 400

    create_or_update_budget(instance_id, category_id, limit)

    return {"message": "Budget upserted successfully"}, 200


@transaction_bp.route('/v1/instances/<instance_id>/budgets', methods=['GET'])
def get_utilised_budget_route(instance_id):
    resp = get_budget_utilisation(instance_id)
    return jsonify({'Details':resp}),200