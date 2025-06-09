from flask_mail import Message
from app.extensions import mail
from flask import current_app

def send_otp_email(recipient, otp):
    msg = Message("SwiftSupply OTP Verification", recipients=[recipient])
    msg.body = f"Your OTP code is: {otp}"
    mail.send(msg)

def send_password_reset(recipient, reset_link):
    msg = Message("SwiftSupply Password Reset", recipients=[recipient])
    msg.body = f"Click to reset your password: {reset_link}"
    mail.send(msg)
