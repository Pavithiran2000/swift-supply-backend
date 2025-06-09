import os
import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app import Config
from app.models import (
    Product, SellerProfile, User, UserRole, Category, ProductType, Brand,
    Tag, ProductImage, Order, Inquiry, SalesData, ProductView, SupplierReview,
    OrderStatus, InquiryStatus, ActivityType, InventoryLog, BusinessType
)
from app.extensions import db
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc, and_
from flask_jwt_extended import jwt_required, get_jwt_identity

supplier_bp = Blueprint('supplier', __name__, url_prefix='/suppliers')


@supplier_bp.route("/", methods=["GET"])
def get_all_suppliers():
    # Get pagination params (default: page=1, limit=10)
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(request.args.get("per_page", 12))
    except (TypeError, ValueError):
        limit = 12

    # Just get all sellers for now, paginated
    pagination = SellerProfile.query.paginate(page=page, per_page=limit, error_out=False)

    result = []
    for s in pagination.items:
        contact_email = s.user.email if s.user and s.user.email else None
        contact_phone = s.user.contact if s.user and s.user.contact else None

        result.append({
            # "id": f"SUP-{s.id:03d}",
            "id": f"{s.id}",
            "name": s.store_name or "",
            "description": s.description or "",
            "logo": s.logo_url or "",
            "coverImage": s.cover_image_url or "",
            "location": s.store_address or "",
            "contact": {
                "email": contact_email,
                "phone": contact_phone
            },
            "rating": round(s.rating or 0, 2),
            "totalReviews": s.total_reviews or 0,
            "verified": s.is_verified,
            "productTypes": [pt.name for pt in s.product_types],
            "categories": list(set([pt.category.name for pt in s.product_types if pt.category])),
            "businessType": s.business_type.value if s.business_type else "Supplier",
            "certifications": s.certifications if s.certifications else [],
            "isGoldSupplier": s.is_gold_supplier,
            "isPremium": s.is_premium,
            "totalProducts": s.total_products or 0,
            "totalOrders": s.total_orders or 0,
            "successRate": round(s.success_rate or 0.0, 2),
            "createdAt": s.created_at.strftime("%Y-%m-%d") if s.created_at else None,
            "lastActive": s.last_active.strftime("%Y-%m-%d") if s.last_active else None
        })

    total = pagination.total
    total_pages = (total + limit - 1) // limit

    return jsonify({
        "suppliers": result,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages
        }
    })


# Get a specific supplier by ID with complete profile
@supplier_bp.route("/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    # Get recent reviews
    recent_reviews = db.session.query(SupplierReview).filter_by(seller_id=supplier_id).order_by(
        desc(SupplierReview.created_at)
    ).limit(10).all()

    reviews_data = []
    for review in recent_reviews:
        reviews_data.append({
            'id': str(review.id),
            'buyerName': review.buyer_name,
            'buyerCountry': review.buyer_country,
            'rating': review.rating,
            'comment': review.comment,
            'orderValue': review.order_value,
            'productCategory': review.product_category,
            'date': review.created_at.isoformat() if review.created_at else "",
            'verified': review.is_verified
        })

    # Get supplier data
    supplier_data = seller.to_dict()
    supplier_data['reviews'] = reviews_data

    return jsonify(supplier_data)


@supplier_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_supplier_inventory():
    """Get supplier's inventory with optional filters and pagination"""
    supplier_id = get_jwt_identity()
    print(f"Supplier ID from JWT: {supplier_id}")
    seller = SellerProfile.query.filter_by(user_id=supplier_id, is_verified=True).first()
    print(f"Seller found: {seller}")
    if not seller:
        return jsonify({"error": "Unauthorized access"}), 403

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    query = Product.query.filter_by(seller_id=seller.id)

    total = query.count()
    print(f"Total products for supplier {supplier_id}: {total}")
    products = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for product in products:
        stock_level = product.stock or 0
        if stock_level > 1000:
            stock_status = "in-stock"
        elif stock_level > 0:
            stock_status = "low-stock"
        else:
            stock_status = "out-of-stock"

        result.append({
            **product.to_dict(),
            "stock": stock_level,
            "minStock": 1000,
            "status": stock_status,
            "lastUpdated": product.updated_at.isoformat() if product.updated_at else None,
            "views": product.view_count or 0,
            "inquiries": product.inquiry_count or 0,
            "orders": product.order_count or 0,
            "revenue": round((product.order_count or 0) * product.price, 2)
        })

    return jsonify({
        "products": result,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit
        }
    })


## Supplier Products CRUD Routes
# @supplier_bp.route("/<int:supplier_id>/products", methods=["GET"])
# def get_supplier_products(supplier_id):
#     """Get products for a specific supplier"""
#     seller = SellerProfile.query.get(supplier_id)
#     if not seller:
#         return jsonify({"error": "Supplier not found"}), 404
#
#     # Use existing inventory endpoint logic
#     return get_supplier_inventory(supplier_id)


def upload_file(file):
    if not file:
        return None, 'No file part'
    if file.filename == '':
        return None, 'No selected file'

    filename = f"{uuid.uuid4()}.{secure_filename(file.filename).rsplit('.', 1)[-1]}"
    upload_folder = Config.UPLOAD_FOLDER
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    file_path = os.path.join(upload_folder, filename)
    print(f"Saving file to {file_path}")
    file.save(file_path)
    return filename, None


def delete_file(filename):
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    print(f"Deleting file {file_path}")
    if os.path.exists(file_path):
        os.remove(file_path)


@supplier_bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_image():
    supplier_id = get_jwt_identity()
    seller = SellerProfile.query.filter_by(user_id=supplier_id).first()
    if not seller or not seller.is_verified:
        return jsonify({"error": "Unauthorized or unverified"}), 403

    if 'image' not in request.files:
        return jsonify({"error": "No image file part"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Optionally: validate file type and size here

    filename, error = upload_file(file)
    if error:
        return jsonify({"error": error}), 400

    url = f"https://api-swiftsupply/images/{filename}"
    return jsonify({"url": url}), 201


@supplier_bp.route("/product", methods=["POST"])
@jwt_required()
def create_supplier_product():
    supplier_id = get_jwt_identity()
    seller = SellerProfile.query.filter_by(user_id=supplier_id).first()
    if not seller:
        return jsonify({"error": "Unauthorized access"}), 403
    if not seller.is_verified:
        return jsonify({"error": "Please verify your account first."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Product data is required"}), 400

    images = data.get('images', [])
    if len(images) > 5:
        return jsonify({"error": "Maximum 5 images are allowed."}), 400

    required_fields = ['name', 'description', 'price', 'stock']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Field '{field}' is required"}), 400

    category = None
    product_type = None
    if 'category' in data:
        category = Category.query.filter_by(name=data['category']).first()
        if not category:
            return jsonify({"error": "Category not found"}), 404

    if 'productType' in data and category:
        product_type = ProductType.query.filter_by(
            name=data['productType'],
            category_id=category.id
        ).first()
        if not product_type:
            product_type = ProductType(
                name=data['productType'],
                category_id=category.id
            )
            db.session.add(product_type)
            db.session.flush()

    brand = None
    if 'brand' in data:
        brand = Brand.query.filter_by(name=data['brand']).first()
        if not brand:
            brand = Brand(name=data['brand'])
            db.session.add(brand)
            db.session.flush()

    product = Product(
        name=data['name'],
        description=data['description'],
        price=float(data['price']),
        original_price=float(data.get('originalPrice', 0)) if data.get('originalPrice') else None,
        stock=int(data['stock']),
        min_order_qty=int(data.get('minOrderQty', 1)),
        seller_id=seller.id,
        category_id=category.id if category else None,
        product_type_id=product_type.id if product_type else None,
        brand_id=brand.id if brand else None,
        specifications=data.get('specifications', {}),
        is_new=data.get('isNew', True) in ['true', 'True', True],
        is_trending=data.get('isTrending', False) in ['true', 'True', True]
    )

    db.session.add(product)
    db.session.flush()

    for i, url in enumerate(images):
        image = ProductImage(
            product_id=product.id,
            url=url,
            is_primary=(i == 0)
        )
        db.session.add(image)

    if 'tags' in data:
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            product.tags.append(tag)

    seller.total_products = db.session.query(Product).filter_by(seller_id=supplier_id).count() + 1

    db.session.commit()
    result = []

    stock_level = product.stock or 0
    if stock_level > 1000:
        stock_status = "in-stock"
    elif stock_level > 0:
        stock_status = "low-stock"
    else:
        stock_status = "out-of-stock"

    result.append({
        **product.to_dict(),
        "stock": stock_level,
        "minStock": 1000,
        "status": stock_status,
        "lastUpdated": product.updated_at.isoformat() if product.updated_at else None,
        "views": product.view_count or 0,
        "inquiries": product.inquiry_count or 0,
        "orders": product.order_count or 0,
        "revenue": round((product.order_count or 0) * product.price, 2)
    })

    return result, 201

    # return jsonify(product.to_dict()), 201


@supplier_bp.route("/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_supplier_product(product_id):
    supplier_id = get_jwt_identity()
    seller = SellerProfile.query.filter_by(user_id=supplier_id).first()
    if not seller:
        return jsonify({"error": "Unauthorized access"}), 403
    if not seller.is_verified:
        return jsonify({"error": "Please verify your account first."}), 403

    product = Product.query.filter_by(id=product_id, seller_id=seller.id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Product data is required"}), 400

    images = data.get('images', [])
    if len(images) > 5:
        return jsonify({"error": "Maximum 5 images are allowed."}), 400

    print(images)

    # Update product fields
    if 'name' in data:
        product.name = data['name']
    if 'description' in data:
        product.description = data['description']
    if 'price' in data:
        product.price = float(data['price'])
    if 'originalPrice' in data:
        product.original_price = float(data['originalPrice'])
    if 'category' in data:
        category = Category.query.filter_by(name=data['category']).first()
        if not category:
            return jsonify({"error": "Category not found"}), 404
        product.category_id = category.id
    if 'productType' in data:
        product_type = ProductType.query.filter_by(
            name=data['productType'],
            category_id=product.category_id
        ).first()
        if not product_type:
            product_type = ProductType(
                name=data['productType'],
                category_id=product.category_id
            )
            db.session.add(product_type)
            db.session.flush()
        product.product_type_id = product_type.id
    if 'brand' in data:
        brand = Brand.query.filter_by(name=data['brand']).first()
        if not brand:
            brand = Brand(name=data['brand'])
            db.session.add(brand)
            db.session.flush()
        product.brand_id = brand.id
    if 'stock' in data:
        old_stock = product.stock
        product.stock = int(data['stock'])
        product.in_stock = product.stock > 0
        if old_stock != product.stock:
            log = InventoryLog(
                product_id=product.id,
                change=product.stock - old_stock,
                reason='Product update'
            )
            db.session.add(log)
    if 'minOrderQty' in data:
        product.min_order_qty = int(data['minOrderQty'])
    if 'specifications' in data:
        import json
        try:
            specs = data['specifications']
            if isinstance(specs, str):
                specs = json.loads(specs)
            product.specifications = specs
        except Exception:
            product.specifications = {}
    if 'isNew' in data:
        product.is_new = data['isNew'] in ['true', 'True', True]
    if 'isTrending' in data:
        product.is_trending = data['isTrending'] in ['true', 'True', True]

    # Handle images - remove only those not in new list
    old_images = ProductImage.query.filter_by(product_id=product.id).all()
    existing_urls = set(img.url for img in old_images)
    new_urls = set(images)

    # Delete removed images and files
    for img in old_images:
        if img.url not in new_urls:
            filename = img.url.split('/')[-1]
            delete_file(filename)
            db.session.delete(img)

    db.session.flush()

    # Add new images and update is_primary flag for all images (new and existing)
    for i, url in enumerate(images):
        if url not in existing_urls:
            new_img = ProductImage(
                product_id=product.id,
                url=url,
                is_primary=(i == 0)
            )
            db.session.add(new_img)
        else:
            img = next((img for img in old_images if img.url == url), None)
            if img:
                img.is_primary = (i == 0)

    # Update tags
    if 'tags' in data:
        existing_tags = set(tag.name for tag in product.tags)
        new_tags = set(data['tags'])
        # Remove tags not in new_tags
        for tag in product.tags[:]:
            if tag.name not in new_tags:
                product.tags.remove(tag)
        # Add new tags
        for tag_name in new_tags - existing_tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            product.tags.append(tag)

    product.updated_at = datetime.utcnow()
    db.session.commit()
    print(product.to_dict())
    result = []

    stock_level = product.stock or 0
    if stock_level > 1000:
        stock_status = "in-stock"
    elif stock_level > 0:
        stock_status = "low-stock"
    else:
        stock_status = "out-of-stock"

    print("minStock", data["minStock"])

    result.append({
        **product.to_dict(),
        "stock": stock_level,
        "minStock": 1000,
        "status": stock_status,
        "lastUpdated": product.updated_at.isoformat() if product.updated_at else None,
        "views": product.view_count or 0,
        "inquiries": product.inquiry_count or 0,
        "orders": product.order_count or 0,
        "revenue": round((product.order_count or 0) * product.price, 2)
    })

    return result, 201
    # return jsonify(product.to_dict())


@supplier_bp.route("/<int:supplier_id>/products/<int:product_id>", methods=["DELETE"])
def delete_supplier_product(supplier_id, product_id):
    """Delete a product for supplier"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    product = db.session.query(Product).filter_by(
        id=product_id,
        seller_id=supplier_id
    ).first()

    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Soft delete - just mark as inactive
    product.is_active = False
    product.updated_at = datetime.utcnow()

    # Update seller's total products count
    seller.total_products = db.session.query(Product).filter_by(
        seller_id=supplier_id,
        is_active=True
    ).count() - 1

    db.session.commit()

    return jsonify({"message": "Product deleted successfully"})


# Supplier Dashboard Routes
@supplier_bp.route("/<int:supplier_id>/dashboard", methods=["GET"])
def get_supplier_dashboard(supplier_id):
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    return jsonify(seller.get_dashboard_stats())


@supplier_bp.route("/<int:supplier_id>/sales-data", methods=["GET"])
def get_supplier_sales_data(supplier_id):
    # Get last 30 days of sales data
    thirty_days_ago = date.today() - timedelta(days=30)

    sales_data = db.session.query(SalesData).filter(
        SalesData.seller_id == supplier_id,
        SalesData.date >= thirty_days_ago
    ).order_by(SalesData.date).all()

    result = []
    for data in sales_data:
        result.append({
            'date': data.date.isoformat(),
            'revenue': data.revenue or 0,
            'orders': data.order_count or 0
        })

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/product-engagement", methods=["GET"])
def get_product_engagement(supplier_id):
    # Get top 10 products by engagement (views + inquiries + orders)
    products = db.session.query(Product).filter_by(seller_id=supplier_id).order_by(
        desc(Product.view_count + Product.inquiry_count + Product.order_count)
    ).limit(10).all()

    result = []
    for product in products:
        result.append({
            'productName': product.name,
            'views': product.view_count or 0,
            'inquiries': product.inquiry_count or 0,
            'orders': product.order_count or 0
        })

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/recent-orders", methods=["GET"])
def get_recent_orders(supplier_id):
    limit = request.args.get('limit', 10, type=int)

    orders = db.session.query(Order).filter_by(seller_id=supplier_id).order_by(
        desc(Order.created_at)
    ).limit(limit).all()

    result = []
    for order in orders:
        result.append(order.to_dict())

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/inquiries", methods=["GET"])
def get_supplier_inquiries(supplier_id):
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)

    query = db.session.query(Inquiry).filter_by(seller_id=supplier_id)

    if status:
        query = query.filter_by(status=InquiryStatus(status.upper()))

    inquiries = query.order_by(desc(Inquiry.created_at)).limit(limit).all()

    result = []
    for inquiry in inquiries:
        buyer = User.query.get(inquiry.buyer_id)
        product = Product.query.get(inquiry.product_id) if inquiry.product_id else None

        result.append({
            'id': str(inquiry.id),
            'subject': inquiry.subject,
            'message': inquiry.message,
            'status': inquiry.status.value if inquiry.status else 'pending',
            'isRead': inquiry.is_read,
            'response': inquiry.response,
            'buyerName': f"{buyer.first_name} {buyer.last_name}" if buyer else 'Unknown',
            'buyerEmail': buyer.email if buyer else None,
            'productName': product.name if product else None,
            'createdAt': inquiry.created_at.isoformat() if inquiry.created_at else None,
            'respondedAt': inquiry.responded_at.isoformat() if inquiry.responded_at else None
        })

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/low-stock-products", methods=["GET"])
def get_low_stock_products(supplier_id):
    threshold = request.args.get('threshold', 10, type=int)

    products = db.session.query(Product).filter(
        Product.seller_id == supplier_id,
        Product.stock < threshold,
        Product.is_active == True
    ).order_by(Product.stock).all()

    result = []
    for product in products:
        result.append({
            'id': str(product.id),
            'name': product.name,
            'stock': product.stock,
            'minOrderQty': product.min_order_qty,
            'price': product.price,
            'sku': product.sku
        })

    return jsonify(result)


# Contact supplier
@supplier_bp.route("/<int:supplier_id>/contact", methods=["POST"])
def contact_supplier(supplier_id):
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400

    # Create inquiry
    inquiry = Inquiry(
        buyer_id=data.get('buyerId'),  # Should come from auth
        seller_id=supplier_id,
        product_id=data.get('productId'),
        subject=data.get('subject', 'General Inquiry'),
        message=data['message'],
        status=InquiryStatus.PENDING,
        is_read=False
    )

    db.session.add(inquiry)
    db.session.commit()

    return jsonify({"message": "Inquiry sent successfully", "inquiryId": str(inquiry.id)}), 201


# Update supplier profile
@supplier_bp.route("/<int:supplier_id>/profile", methods=["PUT"])
def update_supplier_profile(supplier_id):
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    data = request.get_json()

    # Update fields if provided
    if 'storeName' in data:
        seller.store_name = data['storeName']
    if 'description' in data:
        seller.description = data['description']
    if 'storeAddress' in data:
        seller.store_address = data['storeAddress']
    if 'businessType' in data:
        seller.business_type = data['businessType']
    if 'logoUrl' in data:
        seller.logo_url = data['logoUrl']
    if 'coverImageUrl' in data:
        seller.cover_image_url = data['coverImageUrl']
    if 'certifications' in data:
        seller.certifications = data['certifications']

    seller.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(seller.to_dict())


# # Enhanced product routes with filtering and search
# @product_bp.route("/", methods=["GET"])
# def get_all_products():
#     # Get filter parameters
#     category = request.args.get('category')
#     product_type = request.args.get('productType')
#     price_min = request.args.get('priceMin', type=float)
#     price_max = request.args.get('priceMax', type=float)
#     rating = request.args.get('rating', type=float)
#     in_stock = request.args.get('inStock', type=bool)
#     is_new = request.args.get('isNew', type=bool)
#     is_trending = request.args.get('isTrending', type=bool)
#     supplier_id = request.args.get('supplier', type=int)
#     min_order_qty = request.args.get('minOrderQty', type=int)
#     search = request.args.get('search')

#     # Pagination
#     page = request.args.get('page', 1, type=int)
#     limit = request.args.get('limit', 20, type=int)

#     # Sorting
#     sort_field = request.args.get('sortField', 'created_at')
#     sort_order = request.args.get('sortOrder', 'desc')

#     # Build query with joins
#     query = db.session.query(Product).join(ProductType, Product.product_type_id == ProductType.id, isouter=True).join(
#         Category, Product.category_id == Category.id, isouter=True
#     ).join(Brand, Product.brand_id == Brand.id, isouter=True).filter(Product.is_active == True)

#     # Apply filters
#     if category:
#         query = query.filter(Category.name == category)
#     if product_type:
#         query = query.filter(ProductType.name == product_type)
#     if price_min:
#         query = query.filter(Product.price >= price_min)
#     if price_max:
#         query = query.filter(Product.price <= price_max)
#     if rating:
#         query = query.filter(Product.rating >= rating)
#     if in_stock is not None:
#         query = query.filter(Product.in_stock == in_stock)
#     if is_new is not None:
#         query = query.filter(Product.is_new == is_new)
#     if is_trending is not None:
#         query = query.filter(Product.is_trending == is_trending)
#     if supplier_id:
#         query = query.filter(Product.seller_id == supplier_id)
#     if min_order_qty:
#         query = query.filter(Product.min_order_qty <= min_order_qty)
#     if search:
#         search_term = f"%{search}%"
#         query = query.filter(
#             db.or_(
#                 Product.name.ilike(search_term),
#                 Product.description.ilike(search_term)
#             )
#         )

#     # Apply sorting
#     if sort_field == 'price':
#         order_by = Product.price.desc() if sort_order == 'desc' else Product.price.asc()
#     elif sort_field == 'rating':
#         order_by = Product.rating.desc() if sort_order == 'desc' else Product.rating.asc()
#     elif sort_field == 'reviews':
#         order_by = Product.review_count.desc() if sort_order == 'desc' else Product.review_count.asc()
#     elif sort_field == 'name':
#         order_by = Product.name.desc() if sort_order == 'desc' else Product.name.asc()
#     elif sort_field == 'created_at':
#         order_by = Product.created_at.desc() if sort_order == 'desc' else Product.created_at.asc()
#     else:
#         order_by = Product.created_at.desc()

#     query = query.order_by(order_by)

#     # Pagination
#     total = query.count()
#     products = query.offset((page - 1) * limit).limit(limit).all()

#     result = []
#     for product in products:
#         result.append(product.to_dict())

#     return jsonify({
#         'products': result,
#         'pagination': {
#             'page': page,
#             'limit': limit,
#             'total': total,
#             'totalPages': (total + limit - 1) // limit
#         }
#     })

# # Get a specific product by ID with complete details
# @product_bp.route("/<int:product_id>", methods=["GET"])
# def get_product(product_id):
#     product = Product.query.get(product_id)
#     if not product:
#         return jsonify({"error": "Product not found"}), 404

#     # Track product view
#     view = ProductView(
#         product_id=product_id,
#         ip_address=request.remote_addr,
#         user_agent=request.headers.get('User-Agent'),
#         viewed_at=datetime.utcnow()
#     )
#     db.session.add(view)

#     # Increment view count
#     product.view_count = (product.view_count or 0) + 1
#     db.session.commit()

#     return jsonify(product.to_dict())

# # Search products
# @product_bp.route("/search", methods=["GET"])
# def search_products():
#     query_text = request.args.get('q', '')
#     if not query_text:
#         return jsonify({"error": "Search query is required"}), 400

#     limit = request.args.get('limit', 10, type=int)

#     search_term = f"%{query_text}%"
#     products = db.session.query(Product).filter(
#         db.and_(
#             Product.is_active == True,
#             db.or_(
#                 Product.name.ilike(search_term),
#                 Product.description.ilike(search_term)
#             )
#         )
#     ).limit(limit).all()

#     result = []
#     for product in products:
#         result.append({
#             'id': str(product.id),
#             'name': product.name,
#             'price': product.price,
#             'image': product.images[0].url if product.images else None
#         })

#     return jsonify(result)

# Supplier Inventory Management Routes
# @supplier_bp.route("/<int:supplier_id>/inventory", methods=["GET"])
# def get_supplier_inventory(supplier_id):
#     """Get supplier's inventory with filtering and pagination"""
#     seller = SellerProfile.query.get(supplier_id)
#     if not seller:
#         return jsonify({"error": "Supplier not found"}), 404

#     # Filter parameters
#     category = request.args.get('category')
#     status = request.args.get('status')  # in-stock, low-stock, out-of-stock
#     price_min = request.args.get('priceMin', type=float)
#     price_max = request.args.get('priceMax', type=float)
#     search = request.args.get('search', '')

#     # Pagination
#     page = request.args.get('page', 1, type=int)
#     limit = request.args.get('limit', 20, type=int)

#     # Build query
#     query = db.session.query(Product).filter_by(seller_id=supplier_id)

#     # Apply filters
#     if category:
#         query = query.join(ProductType).join(Category).filter(Category.name == category)

#     if status:
#         if status == 'in-stock':
#             query = query.filter(Product.stock > 10)
#         elif status == 'low-stock':
#             query = query.filter(Product.stock.between(1, 10))
#         elif status == 'out-of-stock':
#             query = query.filter(Product.stock == 0)

#     if price_min:
#         query = query.filter(Product.price >= price_min)
#     if price_max:
#         query = query.filter(Product.price <= price_max)

#     if search:
#         search_term = f"%{search}%"
#         query = query.filter(
#             db.or_(
#                 Product.name.ilike(search_term),
#                 Product.description.ilike(search_term),
#                 Product.sku.ilike(search_term)
#             )
#         )

#     # Pagination
#     total = query.count()
#     products = query.offset((page - 1) * limit).limit(limit).all()

#     result = []
#     for product in products:
#         product_data = product.to_dict()
#         # Add inventory-specific fields
#         if product.stock > 10:
#             status = 'in-stock'
#         elif product.stock > 0:
#             status = 'low-stock'
#         else:
#             status = 'out-of-stock'

#         product_data.update({
#             'stock': product.stock,
#             'minStock': 10,  # Default minimum stock
#             'status': status,
#             'lastUpdated': product.updated_at.isoformat() if product.updated_at else None,
#             'views': product.view_count or 0,
#             'inquiries': product.inquiry_count or 0,
#             'orders': product.order_count or 0,
#             'revenue': (product.order_count or 0) * product.price
#         })
#         result.append(product_data)

#     return jsonify({
#         'products': result,
#         'pagination': {
#             'page': page,
#             'limit': limit,
#             'total': total,
#             'totalPages': (total + limit - 1) // limit
#         }
#     })


@supplier_bp.route("/<int:supplier_id>/inventory/summary", methods=["GET"])
def get_inventory_summary(supplier_id):
    """Get inventory summary statistics"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    # Get inventory statistics
    total_products = db.session.query(Product).filter_by(seller_id=supplier_id).count()
    in_stock = db.session.query(Product).filter(
        Product.seller_id == supplier_id,
        Product.stock > 10
    ).count()
    low_stock = db.session.query(Product).filter(
        Product.seller_id == supplier_id,
        Product.stock.between(1, 10)
    ).count()
    out_of_stock = db.session.query(Product).filter(
        Product.seller_id == supplier_id,
        Product.stock == 0
    ).count()

    # Calculate total inventory value
    total_value = db.session.query(func.sum(Product.price * Product.stock)).filter_by(
        seller_id=supplier_id
    ).scalar() or 0

    return jsonify({
        'totalProducts': total_products,
        'inStock': in_stock,
        'lowStock': low_stock,
        'outOfStock': out_of_stock,
        'totalValue': round(total_value, 2)
    })


@supplier_bp.route("/<int:supplier_id>/inventory/alerts", methods=["GET"])
def get_inventory_alerts(supplier_id):
    """Get low stock alerts"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    threshold = request.args.get('threshold', 10, type=int)

    products = db.session.query(Product).filter(
        Product.seller_id == supplier_id,
        Product.stock <= threshold,
        Product.is_active == True
    ).order_by(Product.stock).all()

    result = []
    for product in products:
        alert_level = 'critical' if product.stock == 0 else 'warning' if product.stock <= 5 else 'low'
        result.append({
            'id': str(product.id),
            'name': product.name,
            'sku': product.sku,
            'stock': product.stock,
            'minStock': threshold,
            'alertLevel': alert_level,
            'lastUpdated': product.updated_at.isoformat() if product.updated_at else None
        })

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/inventory/logs", methods=["GET"])
def get_inventory_logs(supplier_id):
    """Get inventory change history"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    limit = request.args.get('limit', 50, type=int)
    product_id = request.args.get('productId', type=int)

    query = db.session.query(InventoryLog).join(Product).filter(
        Product.seller_id == supplier_id
    )

    if product_id:
        query = query.filter(InventoryLog.product_id == product_id)

    logs = query.order_by(desc(InventoryLog.timestamp)).limit(limit).all()

    result = []
    for log in logs:
        result.append({
            'id': str(log.id),
            'productId': str(log.product_id),
            'productName': log.product.name,
            'change': log.change,
            'reason': log.reason,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        })

    return jsonify(result)


@supplier_bp.route("/<int:supplier_id>/inventory/update-stock", methods=["POST"])
def update_stock(supplier_id):
    """Update product stock levels"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    data = request.get_json()
    if not data or 'updates' not in data:
        return jsonify({"error": "Stock updates data is required"}), 400

    updated_products = []

    for update in data['updates']:
        product_id = update.get('productId')
        new_stock = update.get('stock')
        reason = update.get('reason', 'Manual update')

        if not product_id or new_stock is None:
            continue

        product = db.session.query(Product).filter_by(
            id=product_id,
            seller_id=supplier_id
        ).first()

        if not product:
            continue

        old_stock = product.stock
        stock_change = new_stock - old_stock

        # Update product stock
        product.stock = new_stock
        product.in_stock = new_stock > 0
        product.updated_at = datetime.utcnow()

        # Create inventory log
        log = InventoryLog(
            product_id=product.id,
            change=stock_change,
            reason=reason
        )
        db.session.add(log)

        updated_products.append({
            'id': str(product.id),
            'name': product.name,
            'oldStock': old_stock,
            'newStock': new_stock,
            'change': stock_change
        })

    db.session.commit()

    return jsonify({
        'message': f'Updated stock for {len(updated_products)} products',
        'updatedProducts': updated_products
    })


# Business Profile Routes
@supplier_bp.route("/<int:supplier_id>/business-profile", methods=["GET"])
def get_business_profile(supplier_id):
    """Get supplier's business profile"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    user = User.query.get(seller.user_id)

    profile_data = {
        'id': str(seller.id),
        'businessName': seller.store_name,
        'businessRegistration': seller.store_reg,
        'address': seller.store_address,
        'contactPerson': f"{user.first_name} {user.last_name}" if user else '',
        'email': user.email if user else '',
        'phone': user.contact if user else '',
        'description': seller.description,
        'certifications': seller.certifications or [],
        'isVerified': seller.is_verified,
        'rating': seller.rating,
        'totalReviews': seller.total_reviews,
        'joinedDate': seller.created_at.isoformat() if seller.created_at else None,
        'businessType': seller.business_type.value if seller.business_type else None,
        'logoUrl': seller.logo_url,
        'coverImageUrl': seller.cover_image_url,
        'isGoldSupplier': seller.is_gold_supplier,
        'isPremium': seller.is_premium,
        'productTypes': [pt.name for pt in seller.product_types],
        'categories': list(set([pt.category.name for pt in seller.product_types if pt.category]))
    }

    return jsonify(profile_data)


@supplier_bp.route("/<int:supplier_id>/business-profile", methods=["PUT"])
def update_business_profile(supplier_id):
    """Update supplier's business profile"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Profile data is required"}), 400

    user = User.query.get(seller.user_id)

    # Update user fields
    if user:
        if 'contactPerson' in data:
            names = data['contactPerson'].split(' ', 1)
            user.first_name = names[0]
            user.last_name = names[1] if len(names) > 1 else ''
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.contact = data['phone']

    # Update seller profile fields
    if 'businessName' in data:
        seller.store_name = data['businessName']
    if 'businessRegistration' in data:
        seller.store_reg = data['businessRegistration']
    if 'address' in data:
        seller.store_address = data['address']
    if 'description' in data:
        seller.description = data['description']
    if 'certifications' in data:
        seller.certifications = data['certifications']
    if 'businessType' in data:
        try:
            seller.business_type = BusinessType(data['businessType'])
        except ValueError:
            pass
    if 'logoUrl' in data:
        seller.logo_url = data['logoUrl']
    if 'coverImageUrl' in data:
        seller.cover_image_url = data['coverImageUrl']

    # Update product types and categories
    if 'productTypes' in data:
        seller.product_types.clear()
        for pt_name in data['productTypes']:
            product_type = ProductType.query.filter_by(name=pt_name).first()
            if product_type:
                seller.product_types.append(product_type)

    seller.updated_at = datetime.utcnow()
    db.session.commit()

    return get_business_profile(supplier_id)


@supplier_bp.route("/<int:supplier_id>/verification-status", methods=["GET"])
def get_verification_status(supplier_id):
    """Get supplier's verification status"""
    seller = SellerProfile.query.get(supplier_id)
    if not seller:
        return jsonify({"error": "Supplier not found"}), 404

    return jsonify({
        'supplierId': str(seller.id),
        'isVerified': seller.is_verified,
        'isGoldSupplier': seller.is_gold_supplier,
        'isPremium': seller.is_premium,
        'verificationDate': seller.created_at.isoformat() if seller.is_verified else None,
        'certifications': seller.certifications or [],
        'verificationLevel': 'premium' if seller.is_premium else 'gold' if seller.is_gold_supplier else 'verified' if seller.is_verified else 'basic'
    })
