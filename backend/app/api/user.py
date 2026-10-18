from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any
from backend.app.db.repository import Repository
from backend.app.auth.dependencies import get_current_user, get_optional_user, get_current_admin_user

router = APIRouter(prefix="/api", tags=["User Data & Preferences"])

class UpdatePreferencesRequest(BaseModel):
    default_profile: str
    default_priorities: list[str]
    distance_preferences: list[dict[str, Any]] = Field(default_factory=list)

class AddSearchHistoryRequest(BaseModel):
    locality_name: str
    lat: float
    lng: float
    provider: str = "Google Places"

class AddSavedLocationRequest(BaseModel):
    locality_name: str
    lat: float
    lng: float
    label: str | None = None
    notes: str | None = None

class UpdateSavedLocationRequest(BaseModel):
    label: str | None = None
    notes: str | None = None

class FeedbackRequest(BaseModel):
    report_id: str | None = None
    locality_name: str | None = None
    feedback_type: str = "general" # 'incorrect_data' | 'missing_place' | 'general'
    description: str

class AddCreditsRequest(BaseModel):
    amount: int = 1
    payment_method: str = "simulation"

@router.get("/credits")
def get_user_credits(user: dict = Depends(get_current_user)):
    return Repository.get_credits(user["id"])

@router.post("/credits/add")
def add_user_credits(req: AddCreditsRequest, admin_user: dict = Depends(get_current_admin_user)):
    if req.amount <= 0 or req.amount > 50:
        raise HTTPException(status_code=400, detail="Credit quantity must be between 1 and 50")
    success = Repository.add_credits(admin_user["id"], req.amount)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add credits")
    credits = Repository.get_credits(admin_user["id"])
    return {"message": f"Successfully added {req.amount} credit(s)", "credits": credits}

@router.get("/preferences")
def get_user_preferences(user: dict = Depends(get_current_user)):
    return Repository.get_preferences(user["id"])

@router.put("/preferences")
def update_user_preferences(req: UpdatePreferencesRequest, user: dict = Depends(get_current_user)):
    success = Repository.update_preferences(
        user["id"],
        req.default_profile,
        req.default_priorities,
        req.distance_preferences
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update preferences")
    return {"message": "Preferences updated successfully"}

@router.get("/search-history")
def get_search_history(user: dict = Depends(get_current_user)):
    return Repository.get_search_history(user["id"])

@router.post("/search-history")
def record_search_history(req: AddSearchHistoryRequest, user: dict = Depends(get_current_user)):
    success = Repository.add_search_history(
        user["id"], req.locality_name, req.lat, req.lng, req.provider
    )
    return {"recorded": success}

@router.delete("/search-history")
def clear_search_history(user: dict = Depends(get_current_user)):
    success = Repository.clear_search_history(user["id"])
    return {"cleared": success}

@router.get("/saved-locations")
def get_saved_locations(user: dict = Depends(get_current_user)):
    return Repository.get_saved_locations(user["id"])

@router.post("/saved-locations")
def add_saved_location(req: AddSavedLocationRequest, user: dict = Depends(get_current_user)):
    item = Repository.add_saved_location(
        user["id"], req.locality_name, req.lat, req.lng, req.label, req.notes
    )
    if not item:
        raise HTTPException(status_code=500, detail="Failed to save location")
    return item

@router.put("/saved-locations/{location_id}")
def update_saved_location(location_id: str, req: UpdateSavedLocationRequest, user: dict = Depends(get_current_user)):
    success = Repository.update_saved_location(user["id"], location_id, req.label, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Saved location not found or update failed")
    return {"message": "Saved location updated"}

@router.delete("/saved-locations/{location_id}")
def delete_saved_location(location_id: str, user: dict = Depends(get_current_user)):
    success = Repository.delete_saved_location(user["id"], location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Saved location not found")
    return {"message": "Saved location deleted"}

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else None
    success = Repository.submit_feedback(
        user_id=user_id,
        report_id=req.report_id,
        locality_name=req.locality_name,
        feedback_type=req.feedback_type,
        description=req.description
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    return {"message": "Thank you for your feedback!"}
