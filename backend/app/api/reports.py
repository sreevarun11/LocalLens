import os
import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Any

from backend.app.config import settings
from backend.app.db.repository import Repository
from backend.app.auth.dependencies import get_current_user, get_current_verified_user
from backend.app.reports.pdf_generator import generate_report_pdf
from backend.app.providers.places import OverpassPlacesProvider
from backend.app.providers.environment import OpenMeteoAirQualityProvider
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.evidence.personalization import PersonalizationEngine

router = APIRouter(prefix="/api/reports", tags=["Decision Reports"])

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

class PropertyContextInput(BaseModel):
    property_address: str | None = None
    floor_level: str | None = None
    unit_facing: str | None = None
    water_source_declared: str | None = None
    power_backup_declared: str | None = None
    rent_or_price: str | None = None
    user_notes: str | None = None

class GenerateReportRequest(BaseModel):
    locality_name: str
    lat: float
    lng: float
    comparison_locality_name: str | None = None
    comparison_lat: float | None = None
    comparison_lng: float | None = None
    user_profile: str = "family"
    user_priorities: list[str] = Field(default_factory=lambda: ["education", "healthcare", "transport", "daily_life"])
    sections_included: list[str] = Field(default_factory=lambda: ["summary", "amenities", "environment", "checklist", "sources"])
    property_context: PropertyContextInput | None = None

@router.post("/generate")
async def generate_report(req: GenerateReportRequest, user: dict = Depends(get_current_verified_user)):
    """
    Server-side storable report generation.
    Enforces email verification, credit deduction, and non-proprietary data storage.
    """
    user_id = user["id"]
    
    # 1. Credit Check
    credits_data = Repository.get_credits(user_id)
    if credits_data["credits_remaining"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have used all available report credits. Please purchase additional credits."
        )

    # 2. Server-side fetch of strictly storable data (OSM Overpass + Open-Meteo)
    overpass_provider = OverpassPlacesProvider()
    env_provider = OpenMeteoAirQualityProvider()

    places_result = await overpass_provider.get_nearby_places(req.lat, req.lng, radius_m=1500)
    env_result = await env_provider.get_air_quality(req.lat, req.lng)

    # 3. Derive Evidence & Personalization
    locality_key = "report_target"
    evidence_items, gaps = EvidenceBuilder.build_evidence(
        locality_key=locality_key,
        places_res=places_result,
        env_res=env_result
    )

    findings_list, gap_callouts, verify_on_site = PersonalizationEngine.evaluate(
        evidence_items=evidence_items,
        gaps=gaps,
        profile=req.user_profile,  # type: ignore
        selected_priorities=req.user_priorities,  # type: ignore
        distance_preferences=[]
    )

    findings = [f.model_dump() for f in findings_list]
    checklist = [q.question for q in verify_on_site]

    # Amenity breakdown rows for PDF
    categories = ["healthcare", "education", "safety_infrastructure", "daily_life", "transport", "lifestyle"]
    counts = places_result.data.counts_by_category if places_result.data else {}
    amenity_rows = []
    for cat in categories:
        cat_places = [p for p in (places_result.data.places if places_result.data else []) if p.category == cat]
        nearest_m = cat_places[0].distance_m if cat_places else None
        amenity_rows.append({
            "category": cat,
            "count": counts.get(cat, len(cat_places)),
            "nearest_m": nearest_m
        })

    env_data = env_result.data.model_dump() if env_result.data else None

    # 4. Compute unique hash & metadata
    report_id = str(uuid.uuid4())
    now_str = datetime.utcnow().isoformat()
    verification_hash = hashlib.sha256(f"{report_id}:{req.locality_name}:{user_id}:{now_str}".encode()).hexdigest()
    
    app_base_url = settings.APP_BASE_URL.rstrip('/')
    verification_url = f"{app_base_url}/verify/{report_id}"
    pdf_filename = f"report_{report_id}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

    # 5. Generate PDF
    prop_dict = req.property_context.model_dump() if req.property_context else {}
    generate_report_pdf(
        output_path=pdf_path,
        report_id=report_id,
        locality_name=req.locality_name,
        verification_hash=verification_hash,
        verification_url=verification_url,
        findings=findings,
        amenity_rows=amenity_rows,
        env_data=env_data,
        property_context=prop_dict,
        checklist_questions=checklist,
        comparison_name=req.comparison_locality_name,
        user_profile=req.user_profile,
        user_priorities=req.user_priorities
    )

    # 6. Deduct credit atomically
    deducted = Repository.deduct_credit(user_id)
    if not deducted:
        raise HTTPException(status_code=402, detail="Failed to deduct credit. Insufficient balance.")

    # 7. Persist storable snapshot
    raw_evidence = [it.model_dump(mode="json") for it in evidence_items]
    aggregated_metrics = {
        "findings_count": len(findings),
        "amenity_counts": counts,
        "env_aqi": env_data.get("aqi") if env_data else None
    }
    providers_used = [
        {"name": "OpenStreetMap", "license": "ODbL 1.0", "storage": "storable"},
        {"name": "Open-Meteo Air Quality", "license": "Free/Attribution", "storage": "storable"}
    ]

    title = f"Decision Report: {req.locality_name}"
    Repository.create_report(
        user_id=user_id,
        title=title,
        locality_name=req.locality_name,
        lat=req.lat,
        lng=req.lng,
        comparison_locality_name=req.comparison_locality_name,
        comparison_lat=req.comparison_lat,
        comparison_lng=req.comparison_lng,
        user_profile=req.user_profile,
        user_priorities=req.user_priorities,
        sections_included=req.sections_included,
        verification_hash=verification_hash,
        pdf_storage_path=pdf_path,
        qr_code_url=verification_url,
        raw_evidence=raw_evidence,
        aggregated_metrics=aggregated_metrics,
        providers_used=providers_used,
        property_context=prop_dict,
        report_id=report_id
    )

    new_credits = Repository.get_credits(user_id)

    return {
        "id": report_id,
        "title": title,
        "locality_name": req.locality_name,
        "created_at": now_str,
        "verification_hash": verification_hash,
        "verification_url": verification_url,
        "pdf_url": f"/api/reports/{report_id}/pdf",
        "credits_remaining": new_credits["credits_remaining"]
    }

@router.get("")
def list_reports(user: dict = Depends(get_current_user)):
    reports = Repository.get_user_reports(user["id"])
    for r in reports:
        r["pdf_url"] = f"/api/reports/{r['id']}/pdf"
        r["verification_url"] = f"/verify/{r['id']}"
    return reports

@router.get("/{report_id}")
def get_report(report_id: str, user: dict = Depends(get_current_user)):
    report = Repository.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You do not have permission to view this report")
    report["pdf_url"] = f"/api/reports/{report_id}/pdf"
    report["verification_url"] = f"/verify/{report_id}"
    return report

@router.get("/{report_id}/pdf")
def download_pdf(report_id: str, inline: bool = False):
    pdf_path = os.path.join(REPORTS_DIR, f"report_{report_id}.pdf")
    if not os.path.exists(pdf_path):
        report = Repository.get_report_by_id(report_id)
        if report and report.get("pdf_storage_path") and os.path.exists(report["pdf_storage_path"]):
            pdf_path = report["pdf_storage_path"]
        else:
            raise HTTPException(status_code=404, detail="Report PDF file not found")
    
    headers = {
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "public, max-age=3600"
    }
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"LocalLens_Report_{report_id[:8]}.pdf",
        content_disposition_type="inline" if inline else "attachment",
        headers=headers
    )

@router.get("/verify/{report_id}")
def verify_report(report_id: str):
    data = Repository.get_public_verification(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="No verified report found matching this identifier")
    return {
        "status": "valid",
        "report_id": data["id"],
        "title": data["title"],
        "locality_name": data["locality_name"],
        "comparison_locality_name": data.get("comparison_locality_name"),
        "created_at": data["created_at"],
        "verification_hash": data["verification_hash"],
        "certified_by": "LocalLens Independent Register",
        "integrity_status": "AUTHENTIC_UNMODIFIED"
    }
