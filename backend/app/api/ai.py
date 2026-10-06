import hashlib
import json
import logging
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.app.schemas.base import ModuleResult, EvidenceItem, EvidenceGap
from backend.app.schemas.location import PlacesData
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, CommuteData
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.evidence.personalization import (
    PersonalizationEngine,
    ProfileKey,
    PriorityKey,
    DistancePreference,
    Finding,
    PriorityGapCallout,
    VerifyOnSiteQuestion
)
from backend.app.ai.input_sanitizer import sanitize_evidence_for_llm
from backend.app.ai.claim_validator import ClaimValidator
from backend.app.ai.deterministic_fallback import generate_deterministic_synthesis
from backend.app.ai.llm_provider import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Evidence Synthesis"])

llm_service = LLMService()

# In-memory synthesis cache by evidence hash
SYNTHESIS_CACHE: dict[str, dict[str, Any]] = {}

class AISummarizeRequest(BaseModel):
    locality_name: str
    locality_key: str = "loc1"
    profile: ProfileKey = "family"
    priorities: list[PriorityKey] | None = None
    distance_preferences: list[DistancePreference] | None = None
    places: ModuleResult[PlacesData] | None = None
    environment: ModuleResult[AirQualityData] | None = None
    water: ModuleResult[WaterQualityData] | None = None
    crime: ModuleResult[CrimeData] | None = None
    commute: ModuleResult[CommuteData] | None = None

class AIStatement(BaseModel):
    text: str
    kind: str  # "observation", "interpretation", "gap"
    evidence_ids: list[str]

class AISection(BaseModel):
    priority: str
    statements: list[AIStatement]

class AISummaryResponse(BaseModel):
    headline: str
    sections: list[AISection]
    verify_on_site: list[dict[str, Any]]
    mode: str  # "ai_grounded" | "deterministic_fallback"
    evidence_items: list[EvidenceItem]
    gaps: list[EvidenceGap]

@router.post("/summarize", response_model=AISummaryResponse)
async def summarize_evidence(req: AISummarizeRequest):
    # 1. Deterministic Evidence Extraction
    evidence_items, gaps = EvidenceBuilder.build_evidence(
        locality_key=req.locality_key,
        places_res=req.places,
        env_res=req.environment,
        water_res=req.water,
        crime_res=req.crime,
        commute_res=req.commute
    )

    priorities = req.priorities or ["education", "healthcare", "transport"]

    # Deterministic findings
    findings, callouts, verify_questions = PersonalizationEngine.evaluate(
        evidence_items=evidence_items,
        gaps=gaps,
        profile=req.profile,
        selected_priorities=priorities,
        distance_preferences=req.distance_preferences
    )

    # 2. Input Hygiene: Strip places names, photos, reviews, user text
    sanitized_input = sanitize_evidence_for_llm(evidence_items, gaps)
    prompt_payload = json.dumps({
        "locality": req.locality_name,
        "profile": req.profile,
        "priorities": priorities,
        "sanitized_facts": sanitized_input
    }, sort_keys=True)

    cache_key = hashlib.sha256(prompt_payload.encode()).hexdigest()
    if cache_key in SYNTHESIS_CACHE:
        cached = SYNTHESIS_CACHE[cache_key]
        return AISummaryResponse(
            headline=cached["headline"],
            sections=cached["sections"],
            verify_on_site=cached["verify_on_site"],
            mode=cached["mode"],
            evidence_items=evidence_items,
            gaps=gaps
        )

    # 3. Call LLM Service
    raw_llm_json = await llm_service.generate_summary(prompt_payload)

    if raw_llm_json:
        # 4. Run ClaimValidator
        validated_json, is_valid = ClaimValidator.validate_response(
            response_json=raw_llm_json,
            evidence_items=evidence_items,
            gaps=gaps,
            locality_names=[req.locality_name]
        )
        if is_valid:
            validated_json["mode"] = "ai_grounded"
            SYNTHESIS_CACHE[cache_key] = validated_json
            return AISummaryResponse(
                headline=validated_json["headline"],
                sections=validated_json["sections"],
                verify_on_site=validated_json["verify_on_site"],
                mode="ai_grounded",
                evidence_items=evidence_items,
                gaps=gaps
            )
        else:
            logger.warning("LLM response failed ClaimValidator (>30% errors). Triggering deterministic fallback.")

    # 5. Deterministic Fallback if LLM unconfigured, timed out, or failed validation
    fallback_json = generate_deterministic_synthesis(
        locality_name=req.locality_name,
        findings=findings,
        gaps=gaps,
        verify_questions=verify_questions
    )
    SYNTHESIS_CACHE[cache_key] = fallback_json

    return AISummaryResponse(
        headline=fallback_json["headline"],
        sections=fallback_json["sections"],
        verify_on_site=fallback_json["verify_on_site"],
        mode="deterministic_fallback",
        evidence_items=evidence_items,
        gaps=gaps
    )
