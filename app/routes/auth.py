from flask import Blueprint, request, jsonify, url_for, current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, User, UserRole, UserType, BuyerProfile, SellerProfile
from app.utils.security import hash_password, verify_password, generate_otp
from app.services.email_service import send_otp_email, send_password_reset
from app.services.google_auth import verify_google_token
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, set_refresh_cookies, set_access_cookies, unset_jwt_cookies
)
from datetime import datetime, timedelta
import uuid

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def test():
    print("test")
    return {"test": "pass"}



# # 1. SIGNUP
# @auth_bp.route('/signup', methods=['POST'])
# def signup():
#     data = request.json
#     # --- Validate and map fields ---
#     # role is buyer/seller, user_type is retailers/wholesales (for buyer)
#     role = data.get("role")
#     if role not in ["buyer", "seller"]:
#         return jsonify({"msg": "Invalid user role"}), 400
#     if User.query.filter_by(email=data['email'], is_vertifed=True).first():
#         return jsonify({"msg": "Email already registered"}), 400
#
#     otp = generate_otp()
#     otp_expiry = datetime.utcnow() + timedelta(minutes=10)
#     user = User(
#         first_name=data.get('firstName'),
#         last_name=data.get('lastName'),
#         email=data['email'],
#         contact=data.get('contact'),
#         role=UserRole(role),
#         is_verified=False,
#         otp_code=otp,
#         otp_expiry=otp_expiry,
#     )
#     user.set_password(data['password'])
#
#     db.session.add(user)
#     db.session.flush()  # get user.id before creating profile
#
#     if role == "buyer":
#         buyer_profile = BuyerProfile(
#             user_id=user.id,
#             buyer_type=UserType(data['userType']),
#             company_name=data.get('companyName', ''),  # optional, can adjust
#             company_reg=data.get('companyReg', ''),
#             company_address=data.get('companyAddress', '')
#         )
#         db.session.add(buyer_profile)
#     elif role == "seller":
#         seller_profile = SellerProfile(
#             user_id=user.id,
#             store_name=data.get('storeName', ''),
#             store_reg=data.get('storeReg', ''),
#             store_address=data.get('storeAddress', ''),
#         )
#         db.session.add(seller_profile)
#
#     db.session.commit()
#     send_otp_email(user.email, otp)
#     return jsonify({"msg": "User created. OTP sent to email."}), 201
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"msg": "Email is required"}), 400

    # 1. Check for existing user by email
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if existing_user.is_verified:
            return jsonify({"msg": "Email already registered and verified."}), 400
        # Overwrite not-verified user details
        user = existing_user
        user.first_name = data.get('firstName')
        user.last_name = data.get('lastName')
        user.contact = data.get('contact')
        user.role = UserRole(data.get('role'))
        user.otp_code = generate_otp()
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        user.set_password(data.get('password'))
        # Delete existing profile if present
        if user.role == UserRole.BUYER and user.buyer_profile:
            db.session.delete(user.buyer_profile)
        if user.role == UserRole.SELLER and user.seller_profile:
            db.session.delete(user.seller_profile)
    else:
        # New user object
        user = User(
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            email=email,
            contact=data.get('contact'),
            role=UserRole(data.get('role')),
            is_verified=False,
            otp_code=generate_otp(),
            otp_expiry=datetime.utcnow() + timedelta(minutes=10)
        )
        user.set_password(data.get('password'))
        db.session.add(user)
        db.session.flush()  # so user.id is available

    # 2. Validate role and reg fields
    role = data.get("role")
    if role not in ["buyer", "seller"]:
        return jsonify({"msg": "Invalid user role"}), 400

    # 3. Unique check for companyReg or storeReg
    try:
        if role == "buyer":
            company_reg = data.get('companyReg', '').strip()
            if not company_reg:
                return jsonify({"msg": "companyReg is required for buyers"}), 400
            if BuyerProfile.query.filter_by(company_reg=company_reg).first():
                return jsonify({"msg": "Company registration already exists"}), 400
            buyer_profile = BuyerProfile(
                user_id=user.id,
                buyer_type=UserType(data['userType']),
                company_name=data.get('companyName', ''),
                company_reg=company_reg,
                company_address=data.get('companyAddress', '')
            )
            db.session.add(buyer_profile)
        elif role == "seller":
            store_reg = data.get('storeReg', '').strip()
            if not store_reg:
                return jsonify({"msg": "storeReg is required for sellers"}), 400
            if SellerProfile.query.filter_by(store_reg=store_reg).first():
                return jsonify({"msg": "Store registration already exists"}), 400
            seller_profile = SellerProfile(
                user_id=user.id,
                store_name=data.get('storeName', ''),
                store_reg=store_reg,
                store_address=data.get('storeAddress', '')
            )
            db.session.add(seller_profile)

        db.session.commit()
        send_otp_email(user.email, user.otp_code)
        return jsonify({"msg": "User created/updated. OTP sent to email."}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"msg": "Database error occurred.", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error.", "details": str(e)}), 500



# # Check if email/contact exists (for use in Step 1)
# @auth_bp.route('/check-unique', methods=['POST'])
# def check_unique():
#     data = request.json
#     resp = {}
#     email = data.get('email')
#     contact = data.get('contact')
#     company_reg = data.get('companyReg')
#     store_reg = data.get('storeReg')
#
#     # Check email
#     if email:
#         exists = User.query.filter_by(email=email.strip().lower(), is_verified=True).first()
#         resp['emailExists'] = bool(exists)
#
#     # Check contact
#     if contact:
#         exists = User.query.filter_by(contact=contact.strip(), is_verified=True).first()
#         resp['contactExists'] = bool(exists)
#
#     # Check company reg (buyer)
#     if company_reg:
#         exists = BuyerProfile.query.filter_by(company_reg=company_reg.strip()).first()
#         resp['companyRegExists'] = bool(exists)
#
#     # Check store reg (seller)
#     if store_reg:
#         exists = SellerProfile.query.filter_by(store_reg=store_reg.strip()).first()
#         resp['storeRegExists'] = bool(exists)
#
#     return jsonify(resp)


@auth_bp.route('/check-unique', methods=['POST'])
def check_unique():
    """
    Checks if the provided email, contact, companyReg, or storeReg exists in the database
    and is associated with a verified user/profile.
    """
    data = request.json
    resp = {}

    email = data.get('email', '').strip().lower()
    contact = data.get('contact', '').strip()
    company_reg = data.get('companyReg', '').strip()
    store_reg = data.get('storeReg', '').strip()

    # Check email (only verified)
    if email:
        exists = User.query.filter_by(email=email, is_verified=True).first()
        resp['emailExists'] = bool(exists)

    # Check contact (only verified)
    if contact:
        exists = User.query.filter_by(contact=contact, is_verified=True).first()
        resp['contactExists'] = bool(exists)

    # Check companyReg (buyer) - Only if user's account is verified
    if company_reg:
        profile = BuyerProfile.query.filter_by(company_reg=company_reg).first()
        resp['companyRegExists'] = bool(profile and profile.user and profile.user.is_verified)

    # Check storeReg (seller) - Only if user's account is verified
    if store_reg:
        profile = SellerProfile.query.filter_by(store_reg=store_reg).first()
        resp['storeRegExists'] = bool(profile and profile.user and profile.user.is_verified)

    return jsonify(resp)




# 2. OTP verification
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email, otp = data['email'], data['otp_code']
    user = User.query.filter_by(email=email).first()
    if not user or not user.otp_code or user.otp_code != otp or user.otp_expiry < datetime.utcnow():
        return jsonify({"msg": "Invalid or expired OTP"}), 400
    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()
    return jsonify({"msg": "User verified success"}), 201


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.json
    email = data.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
    if user.is_verified:
        return jsonify({"msg": "Account already verified"}), 400

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    send_otp_email(user.email, otp)
    return jsonify({"msg": "OTP resent to your email"}), 200

# 3. LOGIN
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email, password = data['email'], data['password']
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid credentials"}), 401
    if not user.is_verified:
        return jsonify({"msg": "Account not verified. Please verify via OTP."}), 401
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    resp = jsonify(access_token=access_token, refresh_token=refresh_token)
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp

@auth_bp.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(resp)
    return resp

# 4. FORGOT PASSWORD
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()
    reset_link = f"{request.host_url.rstrip('/')}/reset-password?token={reset_token}"
    send_password_reset(email, reset_link)
    return jsonify({"msg": "Reset link sent"})

# 5. RESET PASSWORD
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token, new_password = data.get('token'), data.get('new_password')
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        return jsonify({"msg": "Invalid or expired token"}), 400
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    return jsonify({"msg": "Password reset successful"})

# 6. GOOGLE SSO
@auth_bp.route('/google-signin', methods=['POST'])
def google_signin():
    token = request.json.get('token')
    idinfo = verify_google_token(token)
    if not idinfo:
        return jsonify({"msg": "Google sign-in failed"}), 400
    email = idinfo['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "No SwiftSupply account found for this Google email. Please register first."}), 403
    if not user.is_verified:
        return jsonify({"msg": "Account not verified. Please complete email verification."}), 403
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    resp = jsonify(access_token=access_token, refresh_token=refresh_token)
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


# 7. GET CURRENT USER (for UI header etc)
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Unauthorized user"}), 401
    profile = None
    print("user role:", user.role)
    if user.role == UserRole.BUYER and user.buyer_profile:
        profile = {
            "buyer_type": user.buyer_profile.buyer_type.value,
            "company_name": user.buyer_profile.company_name,
            "company_reg": user.buyer_profile.company_reg,
            "company_address": user.buyer_profile.company_address,
        }
    elif user.role == UserRole.SELLER and user.seller_profile:
        profile = {
            "store_name": user.seller_profile.store_name,
            "store_reg": user.seller_profile.store_reg,
            "store_address": user.seller_profile.store_address,
        }
    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role.value,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "contact": user.contact,
        "profile": profile,
    })
