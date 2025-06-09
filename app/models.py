from datetime import datetime
from sqlalchemy import Enum as PgEnum, JSON, func
from enum import Enum
from typing import List, Dict, Optional, Any
from sqlalchemy.types import TypeDecorator

from app.extensions import db


class JSONList(TypeDecorator):
    """Represents a list stored as a JSON string"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if value is None:
            return []
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return value


class JSONDict(TypeDecorator):
    """Represents a dictionary stored as a JSON string"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if value is None:
            return {}
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        return value


class UserRole(Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"


class UserType(Enum):
    RETAILER = "RETAILER"
    WHOLESALE = "WHOLESALE"


class BusinessType(Enum):
    MANUFACTURER = "MANUFACTURER"
    TRADING_COMPANY = "TRADING COMPANY"
    SUPPLIER = "SUPPLIER"
    DISTRIBUTOR = "DISTRIBUTOR"


class OrderStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InquiryStatus(Enum):
    PENDING = "PENDING"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"


class ActivityType(Enum):
    INQUIRY = "INQUIRY"
    ORDER = "ORDER"
    VIEW = "VIEW"
    MESSAGE = "MESSAGE"


# Association tables
buyer_category = db.Table(
    'buyer_category',
    db.Column('buyer_profile_id', db.Integer, db.ForeignKey('buyer_profile.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

seller_product_type = db.Table(
    'seller_product_type',
    db.Column('seller_profile_id', db.Integer, db.ForeignKey('seller_profile.id')),
    db.Column('product_type_id', db.Integer, db.ForeignKey('product_type.id'))
)

product_discount = db.Table(
    'product_discount',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
    db.Column('discount_id', db.Integer, db.ForeignKey('discount.id'))
)

product_tag = db.Table(
    'product_tag',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

brand_product_type = db.Table(
    'brand_product_type',
    db.Model.metadata,
    db.Column('brand_id', db.Integer, db.ForeignKey('brand.id'), primary_key=True),
    db.Column('product_type_id', db.Integer, db.ForeignKey('product_type.id'), primary_key=True),
)

# User model
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact = db.Column(db.String(20))
    role = db.Column(PgEnum(UserRole), nullable=False)
    password_hash = db.Column(db.String(512))
    # profile_url = db.Column(db.String(255))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(256), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    # Relationships
    buyer_profile = db.relationship("BuyerProfile", uselist=False, back_populates="user")
    seller_profile = db.relationship("SellerProfile", uselist=False, back_populates="user")

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    product_types = db.relationship('ProductType', backref='category', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class ProductType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    products = db.relationship('Product', backref='product_type', lazy=True)
    brands = db.relationship(
        'Brand',
        secondary=brand_product_type,
        back_populates='product_types',
        lazy='dynamic'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    products = db.relationship('Product', backref='brand', lazy=True)

    # Many-to-many with ProductType
    product_types = db.relationship(
        'ProductType',
        secondary=brand_product_type,
        back_populates='brands',
        lazy='dynamic'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BuyerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_type = db.Column(PgEnum(UserType), nullable=False)
    company_name = db.Column(db.String(120))
    company_reg = db.Column(db.String(120))
    company_address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', back_populates='buyer_profile')
    preferred_categories = db.relationship('Category', secondary=buyer_category, backref='buyers')


class SellerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_name = db.Column(db.String(120))
    store_reg = db.Column(db.String(120), unique=True)
    store_address = db.Column(db.String(255))
    description = db.Column(db.Text)
    business_type = db.Column(PgEnum(BusinessType), default=BusinessType.SUPPLIER)
    logo_url = db.Column(db.String(255))
    cover_image_url = db.Column(db.String(255))

    # Verification and ratings
    is_verified = db.Column(db.Boolean, default=False)
    is_gold_supplier = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)

    # Statistics
    total_products = db.Column(db.Integer, default=0)
    total_orders = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)

    # Dashboard stats
    total_inquiries = db.Column(db.Integer, default=0)
    unread_messages = db.Column(db.Integer, default=0)
    pending_orders = db.Column(db.Integer, default=0)
    product_views = db.Column(db.Integer, default=0)
    low_stock_alerts = db.Column(db.Integer, default=0)

    # Certifications stored as JSON array
    certifications = db.Column(JSONList, default=list)

    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='seller_profile')
    product_types = db.relationship('ProductType', secondary=seller_product_type, backref='sellers')
    products = db.relationship('Product', backref='seller', lazy=True)
    orders = db.relationship('Order', backref='seller', lazy=True)
    inquiries = db.relationship('Inquiry', backref='seller', lazy=True)
    reviews = db.relationship('SupplierReview', backref='seller', lazy=True)

    # Validation
    @staticmethod
    def validate_rating(rating: float) -> float:
        """Validate rating is between 0 and 5"""
        if rating is None:
            return 0.0
        return max(0.0, min(5.0, float(rating)))

    @property
    def location(self) -> str:
        """Get formatted location"""
        return self.store_address or ''

    # Improve JSON field typing
    certifications = db.Column(JSONList, default=list)

    # Add typed dictionary output
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics for supplier"""
        from datetime import date, timedelta

        # Calculate today's revenue
        today = date.today()
        today_revenue = db.session.query(db.func.sum(SalesData.revenue)).filter(
            SalesData.seller_id == self.id,
            SalesData.date == today
        ).scalar() or 0

        # Get 30-day product analytics
        thirty_days_ago = today - timedelta(days=30)
        views_last_30d = db.session.query(ProductView).join(Product).filter(
            Product.seller_id == self.id,
            ProductView.viewed_at >= thirty_days_ago
        ).count()

        # Calculate percentage changes
        prev_thirty_days_views = db.session.query(ProductView).join(Product).filter(
            Product.seller_id == self.id,
            ProductView.viewed_at >= thirty_days_ago - timedelta(days=30),
            ProductView.viewed_at < thirty_days_ago
        ).count()

        view_change = ((views_last_30d - prev_thirty_days_views) / max(1, prev_thirty_days_views)) * 100

        return {
            'totalInquiries': self.total_inquiries,
            'unreadMessages': self.unread_messages,
            'pendingOrders': self.pending_orders,
            'productViews': self.product_views,
            'lowStockAlerts': self.get_low_stock_count(),
            'todayOrderValue': today_revenue,
            'percentageChanges': {
                'views': round(view_change, 1),
                'inquiries': self.get_inquiry_change(), 'messages': self.get_message_change(),
                'orders': self.get_order_change(),
                'stock': self.get_stock_change(),
                'revenue': self.get_revenue_change()
            }
        }

    def get_low_stock_count(self) -> int:
        """Get count of products with low stock"""
        return db.session.query(Product).filter(
            Product.seller_id == self.id,
            Product.stock < 10,
            Product.is_active == True
        ).count()

    def get_inquiry_change(self) -> float:
        """Calculate 30-day inquiry change percentage"""
        from datetime import date, timedelta
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        current = db.session.query(Inquiry).filter(
            Inquiry.seller_id == self.id,
            Inquiry.created_at >= thirty_days_ago
        ).count()

        previous = db.session.query(Inquiry).filter(
            Inquiry.seller_id == self.id,
            Inquiry.created_at >= thirty_days_ago - timedelta(days=30),
            Inquiry.created_at < thirty_days_ago
        ).count()

        return round(((current - previous) / max(1, previous)) * 100, 1)

    def get_message_change(self) -> float:
        """Calculate 30-day message change percentage"""
        # For now, return 0 as we don't have a message tracking system yet
        # This can be implemented when we add a messaging system
        return 0.0

    def get_order_change(self) -> float:
        """Calculate 30-day order change percentage"""
        from datetime import date, timedelta
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        current = db.session.query(Order).filter(
            Order.seller_id == self.id,
            Order.created_at >= thirty_days_ago
        ).count()

        previous = db.session.query(Order).filter(
            Order.seller_id == self.id,
            Order.created_at >= thirty_days_ago - timedelta(days=30),
            Order.created_at < thirty_days_ago
        ).count()

        return round(((current - previous) / max(1, previous)) * 100, 1)

    def get_stock_change(self) -> float:
        """Calculate stock level change percentage"""
        # Calculate average stock level change
        # For now, return a placeholder value
        return 0.0

    def get_revenue_change(self) -> float:
        """Calculate 30-day revenue change percentage"""
        from datetime import date, timedelta
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        current_revenue = db.session.query(func.sum(SalesData.revenue)).filter(
            SalesData.seller_id == self.id,
            SalesData.date >= thirty_days_ago
        ).scalar() or 0

        previous_revenue = db.session.query(func.sum(SalesData.revenue)).filter(
            SalesData.seller_id == self.id,
            SalesData.date >= thirty_days_ago - timedelta(days=30),
            SalesData.date < thirty_days_ago
        ).scalar() or 0

        return round(((current_revenue - previous_revenue) / max(1, previous_revenue)) * 100, 1)

    def to_dict(self):
        """Convert seller profile to dictionary matching frontend interface"""
        return {
            'id': str(self.id),
            'name': self.store_name,
            'description': self.description,
            'logo': self.logo_url,
            'coverImage': self.cover_image_url,
            'location': self.store_address,
            'contact': {
                'email': self.user.email,
                'phone': self.user.contact
            },
            'rating': self.rating,
            'totalReviews': self.total_reviews,
            'verified': self.is_verified,
            'productTypes': [pt.name for pt in self.product_types],
            'categories': list(set([pt.category.name for pt in self.product_types if pt.category])),
            'businessType': self.business_type.value if self.business_type else 'Supplier',
            'certifications': self.certifications or [],
            'isGoldSupplier': self.is_gold_supplier,
            'isPremium': self.is_premium,
            'totalProducts': self.total_products,
            'totalOrders': self.total_orders,
            'successRate': self.success_rate,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastActive': self.last_active.isoformat() if self.last_active else None
        }


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float)  # For showing discounts

    # Foreign keys
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'))
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'))

    # Stock and ordering
    stock = db.Column(db.Integer, nullable=False, default=0)
    min_order_qty = db.Column(db.Integer, default=1)

    # Product identifiers
    sku = db.Column(db.String(120), unique=True)

    # Product flags
    in_stock = db.Column(db.Boolean, default=True)
    is_new = db.Column(db.Boolean, default=True)
    is_trending = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # Statistics
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    inquiry_count = db.Column(db.Integer, default=0)
    order_count = db.Column(db.Integer, default=0)

    # Specifications stored as JSON
    specifications = db.Column(JSONDict, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
    attributes = db.relationship('ProductAttribute', backref='product', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('ProductReview', backref='product', lazy=True, cascade="all, delete-orphan")
    discounts = db.relationship('Discount', secondary=product_discount, backref='products')
    tags = db.relationship('Tag', secondary=product_tag, backref='products')
    inventory_logs = db.relationship('InventoryLog', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    favorites = db.relationship('Favorite', backref='product', lazy=True)

    @staticmethod
    def validate_rating(rating: float) -> float:
        """Validate rating is between 0 and 5"""
        if rating is None:
            return 0.0
        return max(0.0, min(5.0, float(rating)))

    def update_rating(self, new_rating: float):
        """Update product rating when a new review is added"""
        validated_rating = self.validate_rating(new_rating)
        if self.review_count == 0:
            self.rating = validated_rating
        else:
            self.rating = ((self.rating * self.review_count) + validated_rating) / (self.review_count + 1)
        self.review_count += 1

    def to_dict(self):
        """Convert product to dictionary matching frontend interface"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'originalPrice': self.original_price,
            'images': [img.url for img in self.images],
            'category': self.product_type.category.name if self.product_type and self.product_type.category else '',
            'productType': self.product_type.name if self.product_type else '',
            'brand': self.brand.name if self.brand else '',
            'supplier': {
                'id': str(self.seller.id),
                'name': self.seller.store_name,
                'rating': self.seller.rating,
                'location': self.seller.store_address,
                'verified': self.seller.is_verified
            } if self.seller else None,
            'specifications': self.specifications or {},
            'rating': self.rating,
            'reviews': self.review_count,
            'minOrderQty': self.min_order_qty,
            'inStock': self.in_stock,
            'isNew': self.is_new,
            'isTrending': self.is_trending,
            'tags': [tag.name for tag in self.tags],
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductAttribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Discount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    discount_percent = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# class ShippingOption(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     estimated_days = db.Column(db.Integer, nullable=False)
#     price = db.Column(db.Float, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Advanced Models ---

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)

    status = db.Column(PgEnum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)

    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='orders')
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Convert order to dictionary matching frontend interface"""
        return {
            'id': str(self.id),
            'orderNumber': self.order_number,
            'buyerName': f"{self.buyer.first_name} {self.buyer.last_name}",
            'items': [item.to_dict() for item in self.order_items],
            'totalAmount': self.total_amount,
            'status': self.status.value,
            'orderDate': self.order_date.isoformat() if self.order_date else None,
            'notes': self.notes
        }


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert order item to dictionary matching frontend interface"""
        return {
            'productId': str(self.product_id),
            'productName': self.product.name if self.product else '',
            'quantity': self.quantity,
            'unitPrice': self.unit_price,
            'totalPrice': self.total_price
        }


class ChatRoom(db.Model):
    """Chat room between buyer and seller, optionally tagged with a product"""
    __tablename__ = "chat_room"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)  # Optional product context

    # Chat metadata
    is_active = db.Column(db.Boolean, default=True)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='buyer_chats')
    seller = db.relationship('SellerProfile', foreign_keys=[seller_id], backref='seller_chats')
    product = db.relationship('Product', backref='chat_rooms')
    messages = db.relationship('ChatMessage', backref='chat_room', lazy=True, cascade="all, delete-orphan",
                               order_by="ChatMessage.created_at")

    # Unique constraint to prevent duplicate chat rooms
    __table_args__ = (db.UniqueConstraint('buyer_id', 'seller_id', 'product_id', name='unique_chat_room'),)

    def to_dict(self):
        """Convert chat room to dictionary matching frontend interface"""
        last_message = self.messages[-1] if self.messages else None

        return {
            'id': str(self.id),
            'buyerId': str(self.buyer_id),
            'sellerId': str(self.seller_id),
            'productId': str(self.product_id) if self.product_id else None,
            'productInfo': {
                'id': str(self.product.id),
                'name': self.product.name,
                'price': self.product.price,
                'image': self.product.images[0].url if self.product and self.product.images else None
            } if self.product else None,
            'sellerInfo': {
                'id': str(self.seller.id),
                'name': self.seller.store_name,
                'avatar': self.seller.logo_url
            },
            'buyerInfo': {
                'id': str(self.buyer.id),
                'name': f"{self.buyer.first_name} {self.buyer.last_name}",
                'avatar': None  # Add avatar field to User model if needed
            },
            'lastMessage': last_message.to_dict() if last_message else None,
            'lastMessageAt': self.last_message_at.isoformat() if self.last_message_at else None,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class ChatMessage(db.Model):
    """Individual messages within a chat room"""
    __tablename__ = "chat_message"

    id = db.Column(db.Integer, primary_key=True)
    chat_room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')  # 'text', 'image', 'file', 'system'

    # Message status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)

    # File attachment (if any)
    attachment_url = db.Column(db.String(255), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    attachment_type = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')

    def to_dict(self):
        """Convert message to dictionary matching frontend interface"""
        return {
            'id': str(self.id),
            'chatRoomId': str(self.chat_room_id),
            'senderId': str(self.sender_id),
            'content': self.content,
            'messageType': self.message_type,
            'isRead': self.is_read,
            'readAt': self.read_at.isoformat() if self.read_at else None,
            'attachment': {
                'url': self.attachment_url,
                'name': self.attachment_name,
                'type': self.attachment_type
            } if self.attachment_url else None,
            'senderInfo': {
                'id': str(self.sender.id),
                'name': f"{self.sender.first_name} {self.sender.last_name}",
                'role': self.sender.role.value
            },
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


# For backward compatibility, keep Chat as an alias
Chat = ChatRoom


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class InventoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    change = db.Column(db.Integer, nullable=False)  # +stock or -stock
    reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Additional models for supplier dashboard and features

class Inquiry(db.Model):
    """Buyer inquiries to suppliers"""
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    subject = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(PgEnum(InquiryStatus), default=InquiryStatus.PENDING)

    is_read = db.Column(db.Boolean, default=False)
    response = db.Column(db.Text)
    responded_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='sent_inquiries')
    product = db.relationship('Product', backref='inquiries')


class SupplierReview(db.Model):
    """Reviews for suppliers"""
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))

    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)

    # Review details from frontend interface
    buyer_name = db.Column(db.String(120))
    buyer_country = db.Column(db.String(100))
    order_value = db.Column(db.Float)
    product_category = db.Column(db.String(120))

    is_verified = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='supplier_reviews')
    order = db.relationship('Order', backref='review')


class ProductView(db.Model):
    """Track product views for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Can be null for anonymous views
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)

    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', backref='product_views')
    user = db.relationship('User', backref='product_views')


class Activity(db.Model):
    """Activity feed for supplier dashboard"""
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)

    activity_type = db.Column(PgEnum(ActivityType), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Related entity information
    related_entity_id = db.Column(db.Integer)
    related_entity_name = db.Column(db.String(255))
    related_entity_type = db.Column(db.String(50))  # 'product', 'buyer', 'order'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    seller = db.relationship('SellerProfile', backref='activities')


class SalesData(db.Model):
    """Daily sales data for charts"""
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    revenue = db.Column(db.Float, default=0.0)
    order_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    seller = db.relationship('SellerProfile', backref='sales_data')

    # Unique constraint to prevent duplicate entries for same seller-date
    __table_args__ = (db.UniqueConstraint('seller_id', 'date', name='unique_seller_date'),)


class BuyerEngagement(db.Model):
    """Track buyer engagement funnel"""
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('seller_profile.id'), nullable=False)
    stage = db.Column(db.String(50), nullable=False)  # 'views', 'inquiries', 'quotes', 'orders'
    count = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, default=datetime.utcnow().date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    seller = db.relationship('SellerProfile', backref='engagement_data')
