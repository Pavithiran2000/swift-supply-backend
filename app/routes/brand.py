from flask import Blueprint, jsonify
from app.models import Brand, ProductType
from app.extensions import db

brand_bp = Blueprint("brand", __name__, url_prefix="/api/brands")


@brand_bp.route("/list/<string:product_type_name>", methods=["GET"])
def get_brand_list(product_type_name):
    # Find the product type by name
    product_type = ProductType.query.filter_by(name=product_type_name).first()
    if not product_type:
        return jsonify({"error": "Product type not found"}), 404

    # Get brands linked to this product type
    brands = product_type.brands.all()  # Because lazy='dynamic'

    # Serialize and return
    return jsonify([brand.to_dict() for brand in brands])

