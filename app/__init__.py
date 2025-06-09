from flask import Flask, send_from_directory
from app.config import Config
from .extensions import db, migrate, jwt, cors, mail
from .routes.category import category_bp
from .routes.product import product_type_bp, product_bp
from .routes.supplier import supplier_bp
from .routes.brand import brand_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # app.config['SQLALCHEMY_DATABASE_URI']= Config.SQLALCHEMY_DATABASE_URI
    db.init_app(app)

    migrate.init_app(app, db)

    # with app.app_context():
    #     from app import models
    from app import models

    jwt.init_app(app)
    cors.init_app(app, origins=[
        # "http://localhost:3000",    # React frontend
        # "http://localhost:3001",    # Admin frontend
        "https://swift-supply.xyz", # Production React frontend
        "https://www.swift-supply.xyz", # Production React frontend (www subdomain)
        "https://admin.swift-supply.xyz", # Admin panel subdomain
    ])    
    mail.init_app(app)

    @app.route('/images/<filename>', methods=['GET'])
    def uploaded_file(filename):
        return send_from_directory('images', filename, as_attachment=False)



    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(category_bp)  # /categories/
    app.register_blueprint(product_type_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(brand_bp)

    # db.create_all()

    return app
