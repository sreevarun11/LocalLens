from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.app.schemas.base import ModuleResult, EvidenceItem, EvidenceGap
from backend.app.schemas.location import PlacesData
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, SafetyAndCrimeData, CommuteData
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.evidence.personalization import (
    PersonalizationEngine,
    ProfileKey,
    PriorityKey,
    DistancePreference,
    Finding,
    PriorityGapCallout,
    VerifyOnSiteQuestion,
    PROFILE_DEFAULTS
)

router = APIRouter(prefix="/insights", tags=["Insights & Personalization"])

class InsightsRequest(BaseModel):
    locality_key: str = "loc1"
    profile: ProfileKey = "family"
    priorities: list[PriorityKey] | None = None
    distance_preferences: list[DistancePreference] | None = None
    places: ModuleResult[PlacesData] | None = None
    environment: ModuleResult[AirQualityData] | None = None
    water: ModuleResult[WaterQualityData] | None = None
    crime: ModuleResult[SafetyAndCrimeData] | ModuleResult[CrimeData] | None = None
    commute: ModuleResult[CommuteData] | None = None

class InsightsResponse(BaseModel):
    profile: ProfileKey
    priorities: list[PriorityKey]
    findings: list[Finding]
    gap_callouts: list[PriorityGapCallout]
    verify_on_site: list[VerifyOnSiteQuestion]
    evidence_items: list[EvidenceItem]
    gaps: list[EvidenceGap]

@router.post("", response_model=InsightsResponse)
async def generate_insights(req: InsightsRequest):
    # If priorities not explicitly provided, use profile defaults
    priorities = req.priorities or PROFILE_DEFAULTS.get(req.profile, ["healthcare", "education", "transport"])

    # 1. Deterministic Evidence Extraction
    evidence_items, gaps = EvidenceBuilder.build_evidence(
        locality_key=req.locality_key,
        places_res=req.places,
        env_res=req.environment,
        water_res=req.water,
        crime_res=req.crime,
        commute_res=req.commute
    )

    # 2. Deterministic Personalization Evaluation
    findings, gap_callouts, verify_on_site = PersonalizationEngine.evaluate(
        evidence_items=evidence_items,
        gaps=gaps,
        profile=req.profile,
        selected_priorities=priorities,
        distance_preferences=req.distance_preferences
    )

    return InsightsResponse(
        profile=req.profile,
        priorities=priorities,
        findings=findings,
        gap_callouts=gap_callouts,
        verify_on_site=verify_on_site,
        evidence_items=evidence_items,
        gaps=gaps
    )

@router.get("/profiles")
async def get_profiles():
    return {
        "profiles": [
            {"id": "family", "name": "Family with Children", "defaults": PROFILE_DEFAULTS["family"]},
            {"id": "commuter", "name": "Daily Commuter", "defaults": PROFILE_DEFAULTS["commuter"]},
            {"id": "student", "name": "Student", "defaults": PROFILE_DEFAULTS["student"]},
            {"id": "elderly", "name": "Elderly Household", "defaults": PROFILE_DEFAULTS["elderly"]},
            {"id": "first_time_renter", "name": "First-Time Renter", "defaults": PROFILE_DEFAULTS["first_time_renter"]},
            {"id": "home_buyer", "name": "Home Buyer", "defaults": PROFILE_DEFAULTS["home_buyer"]},
            {"id": "relocation", "name": "Relocating Professional", "defaults": PROFILE_DEFAULTS["relocation"]}
        ]
    }
