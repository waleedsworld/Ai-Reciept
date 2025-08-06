from flask import Blueprint, jsonify, request
from app.services.categories import rename_category,delete_category

categories_dp = Blueprint("categories_bp",__name__)


@categories_dp.route("/v1/categories/<id>",methods=['POST'])
def rename_category_route(id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer'):
        return {"error":"Forbidden"},403
    
    token = auth_header.split(' ')[1]
    body = request.get_json()
    
    resp,code = rename_category(token,id,body)
    return jsonify(resp),code


@categories_dp.route("/v1/categories/<id>",methods=['DELETE'])
def delete_category_route(id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer'):
        return {"error":"Forbidden"},403
    
    token = auth_header.split(' ')[1]
    
    resp,code = delete_category(token,id)
    return jsonify(resp),code