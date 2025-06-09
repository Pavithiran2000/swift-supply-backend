from flask import Blueprint, jsonify, request
from app.models import Product, ProductType, Category

product_bp = Blueprint("products", __name__, url_prefix="/products")
product_type_bp = Blueprint("product_type", __name__, url_prefix="/api/product-types")

@product_type_bp.route("/", methods=["GET"])
def get_product_types():
    product_types = ProductType.query.all()
    return jsonify([
        {"id": pt.id, "name": pt.name}
        for pt in product_types
    ])


@product_type_bp.route("/list/<string:category_name>", methods=["GET"])
def get_productType_list(category_name):
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        return jsonify({"error": "Category not found"}), 404

    product_types = ProductType.query.filter_by(category_id=category.id).all()
    return jsonify([pt.to_dict() for pt in product_types])


@product_bp.route("/", methods=["GET"])
def get_products():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 12))
    except (TypeError, ValueError):
        page, limit = 1, 12

    pagination = Product.query.paginate(page=page, per_page=limit, error_out=False)
    products = [p.to_dict() for p in pagination.items]

    return jsonify({
        "products": products,
        "total": pagination.total,
        "totalPages": pagination.pages,
        "page": page,
        "limit": limit
    })

@product_bp.route("/<string:product_id>", methods=["GET"])
def get_product_by_id(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

@product_bp.route("/<string:product_id>/related", methods=["GET"])
def get_related_products(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product_id
    ).limit(3).all()
    return jsonify([p.to_dict() for p in related])
