import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = 86400    # 1 day (in seconds)
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days (in seconds)

    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "SWF_ACC"
    JWT_REFRESH_COOKIE_NAME = "SWF_REF"
    JWT_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"  # True for prod (HTTPS), False for dev
    JWT_COOKIE_SAMESITE = "Lax"      # Or "Strict"
    JWT_COOKIE_CSRF_PROTECT = False  # Set True if you want CSRF protection

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    #Google
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/images")
