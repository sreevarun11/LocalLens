import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token
from backend.app.auth.dependencies import get_current_user, security
from backend.app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory sliding-window rate limiter for failed login attempts
_failed_login_attempts: dict[str, list[float]] = defaultdict(list)
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60

def _check_login_rate_limit(key: str):
    now = time.time()
    _failed_login_attempts[key] = [
        t for t in _failed_login_attempts[key]
        if now - t < LOGIN_RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(_failed_login_attempts[key]) >= MAX_FAILED_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before trying again."
        )

def _record_failed_login(key: str):
    _failed_login_attempts[key].append(time.time())

def _reset_login_attempts(key: str):
    _failed_login_attempts.pop(key, None)

class RegisterRequest(BaseModel):
    username: str | None = None
    password: str = Field(..., min_length=10, description="Account password (minimum 10 characters)")
    display_name: str | None = None
    email: str | None = None

class LoginRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str

class RecoverPasswordRequest(BaseModel):
    username: str
    recovery_code: str
    new_password: str = Field(..., min_length=10, description="New password (minimum 10 characters)")

class RegenerateRecoveryCodesRequest(BaseModel):
    current_password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    recovery_codes: list[str] | None = None

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    if len(req.password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 10 characters long"
        )
    
    if not req.username and not req.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required to register."
        )

    # If username provided, user is verified (no email OTP required); if legacy email-only, require verification
    is_verified = True if req.username else False
    raw_username = req.username or (req.email.split("@")[0] if req.email else "user")
    clean_username = raw_username.strip()
    if len(clean_username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters long"
        )

    # Prevent registration of reserved administrator usernames
    admin_uname = getattr(settings, "ADMIN_USERNAME", "sreevarun").lower().strip()
    reserved_usernames = {admin_uname, "sreevarun", "admin", "administrator", "root"}
    if clean_username.lower() in reserved_usernames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is reserved and cannot be registered publicly."
        )

    user = Repository.create_user(
        username=clean_username,
        password=req.password,
        display_name=req.display_name,
        email=req.email,
        is_admin=False,
        is_email_verified=is_verified
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered"
        )
    
    recovery_codes = user.get("recovery_codes", [])

    token = create_access_token(
        user_id=user["id"],
        username_or_email=user["username"],
        is_email_verified=is_verified,
        is_admin=user.get("is_admin", False)
    )
    Repository.create_session(user["id"], token)

    return AuthResponse(access_token=token, user=user, recovery_codes=recovery_codes)

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, request: Request):
    identifier = (req.username or req.email or "").strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required to log in"
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{identifier.lower()}"
    _check_login_rate_limit(rate_limit_key)

    user = Repository.authenticate_user(identifier, req.password)
    if not user:
        _record_failed_login(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    _reset_login_attempts(rate_limit_key)

    token = create_access_token(
        user_id=user["id"],
        username_or_email=user.get("username") or user.get("email") or "user",
        is_email_verified=True,
        is_admin=user.get("is_admin", False)
    )
    Repository.create_session(user["id"], token)

    return AuthResponse(access_token=token, user=user)

@router.post("/logout")
def logout(creds: HTTPAuthorizationCredentials | None = Depends(security)):
    """
    Terminates the current user session on the server.
    Revokes the token in the database so it cannot be used again.
    """
    if creds and creds.credentials:
        Repository.revoke_session(creds.credentials)
    return {"success": True, "message": "Session logged out successfully"}

@router.post("/recover-password")
def recover_password(req: RecoverPasswordRequest):
    if len(req.new_password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 10 characters long"
        )

    success, message = Repository.recover_password(
        username=req.username,
        recovery_code=req.recovery_code,
        new_password=req.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return {"message": message}

@router.post("/regenerate-recovery-codes")
def regenerate_recovery_codes(
    req: RegenerateRecoveryCodesRequest,
    current_user: dict = Depends(get_current_user)
):
    codes, message = Repository.regenerate_recovery_codes(
        user_id=current_user["id"],
        current_password=req.current_password
    )
    if not codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return {"message": message, "recovery_codes": codes}

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    credits_data = Repository.get_credits(current_user["id"])
    return {
        "user": current_user,
        "credits": credits_data
    }

@router.post("/verify-email-simulate")
def verify_email_simulate(current_user: dict = Depends(get_current_user)):
    """Backward compatibility endpoint."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulated email verification is disabled in production."
        )
    Repository.verify_user_email(current_user["id"])
    updated_user = Repository.get_user_by_id(current_user["id"])
    credits_data = Repository.get_credits(current_user["id"])
    new_token = create_access_token(
        user_id=current_user["id"],
        username_or_email=current_user.get("username") or current_user.get("email") or "user",
        is_email_verified=True,
        is_admin=current_user.get("is_admin", False)
    )
    return {
        "message": "Email verified successfully. 3 report credits awarded.",
        "access_token": new_token,
        "user": updated_user,
        "credits": credits_data
    }

@router.post("/resend-verification")
def resend_verification(current_user: dict = Depends(get_current_user)):
    """Backward compatibility endpoint."""
    return {"message": "Verification acknowledged."}
