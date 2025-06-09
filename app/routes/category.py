from flask import Blueprint, jsonify
from app.models import Category
from app.extensions import db

category_bp = Blueprint("category", __name__, url_prefix="/api/categories")

@category_bp.route("/", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([
        {"id": c.id, "name": c.name}
        for c in categories
    ])


@category_bp.route("/list", methods=["GET"])
def get_categories_list():
    categories = Category.query.all()
    # Use list comprehension to serialize
    return jsonify([category.to_dict() for category in categories])
