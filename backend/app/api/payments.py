import hmac
import hashlib
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.auth.dependencies import get_current_user
from backend.app.db.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])

class CreateOrderRequest(BaseModel):
    idempotency_key: str | None = None

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    amount_paise: int = 2900
    amount_inr: float = 29.0
    currency: str = "INR"
    key_id: str
    is_free_allowance: bool = False
    credits_remaining: int = 0

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.get("/config")
def get_payment_config(current_user: dict = Depends(get_current_user)):
    """Returns payment gateway client configuration without secrets."""
    credits = Repository.get_credits(current_user["id"])
    key_id = settings.RAZORPAY_KEY_ID or ("rzp_test_LocalLensDevKey" if settings.ENVIRONMENT != "production" else "")
    return {
        "key_id": key_id,
        "amount_paise": settings.REPORT_PRICE_PAISE,
        "amount_inr": round(settings.REPORT_PRICE_PAISE / 100, 2),
        "currency": "INR",
        "feature_payments": settings.FEATURE_PAYMENTS,
        "credits_remaining": credits.get("credits_remaining", 0)
    }

@router.post("/create-order", response_model=CreateOrderResponse)
def create_payment_order(
    req: CreateOrderRequest | None = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a Razorpay payment order for ₹29 (2900 paise) if user has 0 report credits remaining.
    If the user has free allowance credits remaining, informs client to consume free allowance directly.
    """
    req = req or CreateOrderRequest()
    user_id = current_user["id"]
    credits = Repository.get_credits(user_id)
    rem_credits = credits.get("credits_remaining", 0)

    key_id = settings.RAZORPAY_KEY_ID or ("rzp_test_LocalLensDevKey" if settings.ENVIRONMENT != "production" else "")

    if rem_credits > 0:
        return CreateOrderResponse(
            order_id="free_allowance",
            amount=0,
            amount_paise=0,
            amount_inr=0.0,
            currency="INR",
            key_id=key_id,
            is_free_allowance=True,
            credits_remaining=rem_credits
        )

    # Check idempotency key before creating a new order
    cleaned_idempotency_key = req.idempotency_key.strip() if req.idempotency_key else None
    if cleaned_idempotency_key:
        existing = Repository.get_payment_by_idempotency_key(user_id, cleaned_idempotency_key)
        if existing:
            return CreateOrderResponse(
                order_id=existing["razorpay_order_id"],
                amount=existing["amount_paise"],
                amount_paise=existing["amount_paise"],
                amount_inr=float(existing["amount_inr"]),
                currency="INR",
                key_id=key_id,
                is_free_allowance=False,
                credits_remaining=rem_credits
            )

    amount_paise = settings.REPORT_PRICE_PAISE
    amount_inr = round(amount_paise / 100, 2)
    order_id = None

    # Real Razorpay client integration if API keys are configured
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"rcpt_{uuid.uuid4().hex[:12]}",
                "notes": {
                    "user_id": user_id,
                    "username": current_user.get("username", "user"),
                    "purpose": "LocalLens Decision Report Purchase"
                }
            }
            rzp_order = client.order.create(data=order_data)
            order_id = rzp_order.get("id")
        except Exception as e:
            logger.warning(f"Razorpay live client failed: {e}")
            if settings.ENVIRONMENT == "production":
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Payment gateway communication error. Please try again later."
                )

    if not order_id:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment gateway is unconfigured or unavailable in production."
            )
        # Fallback test mode order in non-production
        order_id = f"order_{uuid.uuid4().hex[:16]}"

    # Persist created order in payments table
    recorded = Repository.record_payment_order(
        user_id=user_id,
        razorpay_order_id=order_id,
        amount_paise=amount_paise,
        amount_inr=amount_inr,
        idempotency_key=cleaned_idempotency_key or str(uuid.uuid4())
    )
    if not recorded:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record payment order."
        )

    return CreateOrderResponse(
        order_id=recorded["razorpay_order_id"],
        amount=recorded["amount_paise"],
        amount_paise=recorded["amount_paise"],
        amount_inr=float(recorded["amount_inr"]),
        currency="INR",
        key_id=key_id,
        is_free_allowance=False,
        credits_remaining=rem_credits
    )

@router.post("/verify-payment")
def verify_payment(
    req: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verifies payment signature using HMAC-SHA256 and idempotently awards 1 report credit.
    """
    order_id = req.razorpay_order_id.strip() if req.razorpay_order_id else ""
    payment_id = req.razorpay_payment_id.strip() if req.razorpay_payment_id else ""
    signature = req.razorpay_signature.strip() if req.razorpay_signature else ""

    if not order_id or not payment_id or not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found or payment could not be processed: order ID, payment ID, and signature are required."
        )

    # Verify HMAC-SHA256 signature when secret is configured
    if settings.RAZORPAY_KEY_SECRET:
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cryptographic payment signature verification failed."
            )
    else:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment gateway secret is not configured in production."
            )
        # In test mode without secret key, reject empty signature
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment signature."
            )

    success, message = Repository.verify_and_complete_payment(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
        expected_user_id=current_user["id"],
        expected_amount_paise=settings.REPORT_PRICE_PAISE
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order not found or payment could not be processed: {message}"
        )

    updated_credits = Repository.get_credits(current_user["id"])
    return {
        "status": "success",
        "success": True,
        "message": "Payment verified successfully. 1 report credit has been added to your balance.",
        "credits": updated_credits,
        "credits_remaining": updated_credits.get("credits_remaining", 0)
    }
