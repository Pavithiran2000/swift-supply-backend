# insert_seed_data.py
from app import create_app
from app.extensions import db
from app.models import Category, ProductType

app = create_app()

categories = [
    "My Categories",
    "Home Decor",
    "Industrial",
    "Health & Personal Care",
    "Fashion & Beauty",
    "Sports & Entertainment",
    "Tools & Home Improvement",
    "Raw Materials",
    "Maintenance, Repair & Operations",
    "Service",
]

product_types = [
    "Rice & Grains",
    "Tea & Beverages",
    "Spices & Condiments",
    "Apparel & Textiles",
    "Building Materials",
    "Electrical Supplies",
    "Office Supplies",
    "Cleaning Products",
    "Machinery & Equipment",
    "Agricultural Supplies",
]

with app.app_context():
    # Insert categories
    for name in categories:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    # Insert product types
    for name in product_types:
        if not ProductType.query.filter_by(name=name).first():
            db.session.add(ProductType(name=name, category_id=1))  # assign to a default category if required

    db.session.commit()
    print("Seed data inserted successfully!")
