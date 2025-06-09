from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import Config

GOOGLE_CLIENT_ID = Config.GOOGLE_CLIENT_ID


# def verify_google_token(token):
# try:
#     idinfo = id_token.verify_oauth2_token(token, requests.Request(), Config.GOOGLE_CLIENT_ID)
#     return idinfo
# except Exception:
#     return None

def verify_google_token(token):
    try:
        print(token)
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=300)
        print("id info", idinfo)
        # idinfo contains keys like 'sub', 'email', 'name', 'picture', 'email_verified'
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            raise ValueError("Could not verify audience.")
        if not idinfo.get('email_verified', False):
            raise ValueError("Email not verified by Google.")
        return idinfo
    except ValueError as e:
        raise ValueError(f"Invalid token: {e}")
