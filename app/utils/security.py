from werkzeug.security import generate_password_hash, check_password_hash
import random, string

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash, password):
    return check_password_hash(hash, password)

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))
