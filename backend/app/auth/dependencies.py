from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.auth.tokens import decode_access_token
from backend.app.db.repository import Repository

security = HTTPBearer(auto_error=False)

def get_optional_user(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    if not creds or not creds.credentials:
        return None
    
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        return None
    
    user = Repository.get_user_by_id(payload["sub"])
    return user

def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = Repository.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

def get_current_verified_user(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required before accessing this feature. Please verify your email."
        )
    return user
