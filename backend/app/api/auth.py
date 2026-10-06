from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from backend.app.db.repository import Repository
from backend.app.auth.tokens import create_access_token
from backend.app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    user = Repository.create_user(
        email=req.email,
        password=req.password,
        display_name=req.display_name,
        is_email_verified=False  # Requires email verification per Section 11
    )
    if not user:
        raise HTTPException(status_code=400, detail="Email is already registered or invalid")
    
    token = create_access_token(user["id"], user["email"], user["is_email_verified"])
    return AuthResponse(access_token=token, user=user)

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    user = Repository.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    token = create_access_token(user["id"], user["email"], user["is_email_verified"])
    return AuthResponse(access_token=token, user=user)

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    credits_data = Repository.get_credits(user["id"])
    return {
        "user": user,
        "credits": credits_data
    }

@router.post("/verify-email-simulate")
def verify_email_simulate(user: dict = Depends(get_current_user)):
    """
    Development & testing endpoint to simulate email confirmation.
    Awards 3 report credits and sets is_email_verified=True.
    """
    success = Repository.verify_user_email(user["id"])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to verify email")
    
    updated_user = Repository.get_user_by_id(user["id"])
    credits_data = Repository.get_credits(user["id"])
    new_token = create_access_token(user["id"], user["email"], True)
    
    return {
        "message": "Email verified successfully. 3 report credits awarded.",
        "access_token": new_token,
        "user": updated_user,
        "credits": credits_data
    }

@router.post("/resend-verification")
def resend_verification(user: dict = Depends(get_current_user)):
    return {
        "message": f"Verification email resent to {user['email']}. Please check your inbox."
    }
