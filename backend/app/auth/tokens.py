import base64
import json
import hmac
import hashlib
import time
from backend.app.config import settings

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(user_id: str, username_or_email: str = "", is_email_verified: bool = True, is_admin: bool = False, expires_in_seconds: int = 86400 * 7) -> str:
    secret_key = settings.get_jwt_secret()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "username": username_or_email,
        "email": username_or_email if "@" in username_or_email else None,
        "is_admin": is_admin,
        "email_verified": is_email_verified,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds
    }
    
    header_b64 = _b64encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64encode(json.dumps(payload).encode('utf-8'))
    
    signature_data = f"{header_b64}.{payload_b64}".encode('utf-8')
    sig = hmac.new(secret_key.encode('utf-8'), signature_data, hashlib.sha256).digest()
    sig_b64 = _b64encode(sig)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> dict | None:
    try:
        secret_key = settings.get_jwt_secret()
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, sig_b64 = parts
        signature_data = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(secret_key.encode('utf-8'), signature_data, hashlib.sha256).digest()
        
        if not hmac.compare_digest(_b64decode(sig_b64), expected_sig):
            return None
        
        payload = json.loads(_b64decode(payload_b64).decode('utf-8'))
        
        if payload.get("exp") and payload["exp"] < int(time.time()):
            return None
            
        return payload
    except Exception:
        return None
