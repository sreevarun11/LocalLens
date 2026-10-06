from typing import Literal, Any
from pydantic import BaseModel, Field
from backend.app.schemas.base import EvidenceItem, EvidenceGap

ProfileKey = Literal[
    "family",
    "commuter",
    "student",
    "elderly",
    "first_time_renter",
    "home_buyer",
    "relocation"
]

PriorityKey = Literal[
    "education",
    "healthcare",
    "transport",
    "daily_life",
    "parks",
    "lifestyle",
    "environment",
    "safety_infrastructure",
    "commute"
]

PROFILE_DEFAULTS: dict[ProfileKey, list[PriorityKey]] = {
    "family": ["education", "healthcare", "transport", "daily_life", "parks"],
    "commuter": ["transport", "commute", "daily_life"],
    "student": ["education", "transport", "daily_life", "lifestyle"],
    "elderly": ["healthcare", "daily_life", "parks", "safety_infrastructure"],
    "first_time_renter": ["transport", "daily_life", "lifestyle", "commute"],
    "home_buyer": ["education", "healthcare", "transport", "environment", "safety_infrastructure"],
    "relocation": ["healthcare", "education", "transport", "daily_life", "environment"]
}

class DistancePreference(BaseModel):
    priority: PriorityKey
    preferred_distance_m: int

class Finding(BaseModel):
    id: str
    priority: PriorityKey
    status: Literal["available", "limited", "unavailable", "error"]
    headline: str
    detail: str
    metric_name: str
    metric_value: str | int | float | None = None
    within_preference: Literal["yes", "no", "unknown"] | None = None
    preference_note: str | None = None
    evidence_ids: list[str]
    entities: list[dict[str, Any]] = Field(default_factory=list)

class PriorityGapCallout(BaseModel):
    priority: PriorityKey
    gap_description: str
    available_facts: str
    missing_data: str

class VerifyOnSiteQuestion(BaseModel):
    id: str
    priority_or_gap: str
    question: str
    context: str

# Developer-authored static bank of suggested questions (Section 8.1)
VERIFY_ON_SITE_BANK: list[VerifyOnSiteQuestion] = [
    VerifyOnSiteQuestion(
        id="vos_water_supply",
        priority_or_gap="water",
        question="What is the building's primary water source (municipal pipe, private borewell, or tanker), and how many hours daily is water supplied?",
        context="Locality-level water quality datasets are unavailable from integrated public sources."
    ),
    VerifyOnSiteQuestion(
        id="vos_school_admissions",
        priority_or_gap="education",
        question="Which school boards (CBSE, ICSE, State, IB) are represented, and are admissions currently open for your desired grades?",
        context="Map databases record school locations, not seat availability, fee structures, or curricula."
    ),
    VerifyOnSiteQuestion(
        id="vos_healthcare_emergency",
        priority_or_gap="healthcare",
        question="Does the nearest medical center maintain a 24/7 casualty/emergency unit, or does it operate daytime clinics only?",
        context="Hospital listings confirm physical presence, not emergency hours or specialty staffing."
    ),
    VerifyOnSiteQuestion(
        id="vos_peak_traffic",
        priority_or_gap="commute",
        question="What is the actual commute time during morning peak hours (8:30–10:00 AM) and evening return (6:00–8:00 PM)?",
        context="Routing models estimate typical travel times; real bottlenecks vary significantly day to day."
    ),
    VerifyOnSiteQuestion(
        id="vos_night_transit",
        priority_or_gap="transport",
        question="Are auto-rickshaws, feeder buses, or app cabs reliably accessible after 9:00 PM near the property?",
        context="Transit stops record static infrastructure, not night-time frequency or ride-hailing response."
    ),
    VerifyOnSiteQuestion(
        id="vos_security_society",
        priority_or_gap="safety_infrastructure",
        question="What security protocols are active at the property (manned security, gated access, CCTV coverage)?",
        context="Crime incident statistics are compiled at district level and cannot be attributed to individual streets."
    ),
    VerifyOnSiteQuestion(
        id="vos_local_noise_air",
        priority_or_gap="environment",
        question="Is there persistent construction, diesel generator exhaust, or highway noise during early morning or late night hours?",
        context="Environmental models estimate broad regional grids (~11 km) and do not capture micro-level neighborhood noise."
    )
]

class PersonalizationEngine:
    @staticmethod
    def evaluate(
        evidence_items: list[EvidenceItem],
        gaps: list[EvidenceGap],
        profile: ProfileKey,
        selected_priorities: list[PriorityKey],
        distance_preferences: list[DistancePreference] | None = None
    ) -> tuple[list[Finding], list[PriorityGapCallout], list[VerifyOnSiteQuestion]]:
        findings: list[Finding] = []
        callouts: list[PriorityGapCallout] = []
        checklist: list[VerifyOnSiteQuestion] = []

        pref_map = {p.priority: p.preferred_distance_m for p in (distance_preferences or [])}
        item_map = {item.id: item for item in evidence_items}

        # Process each selected priority in priority order
        for prio in selected_priorities:
            pref_dist = pref_map.get(prio)

            if prio in ["education", "healthcare", "safety_infrastructure", "daily_life", "transport", "lifestyle", "parks"]:
                # Look for nearest distance evidence item
                dist_key_suffix = "parks" if prio == "parks" else prio
                matching_items = [it for it in evidence_items if it.module in [prio, "lifestyle"] and it.metric == "nearest_distance_m"]
                count_items = [it for it in evidence_items if it.module in [prio, "lifestyle"] and it.metric == "count_within_radius"]

                dist_item = matching_items[0] if matching_items else None
                count_item = count_items[0] if count_items else None

                entities_summary = [
                    {"name": e.name, "distance_m": e.distance_m} for e in (dist_item.entities if dist_item else [])
                ]

                if dist_item and dist_item.value is not None:
                    nearest_m = int(dist_item.value)
                    within_pref = None
                    pref_note = None

                    if pref_dist is not None:
                        if dist_item.result_cap_reached:
                            within_pref = "unknown"
                            pref_note = f"Provider result cap reached; nearest listed facility is {nearest_m}m."
                        elif nearest_m <= pref_dist:
                            within_pref = "yes"
                            pref_note = f"Nearest facility is {nearest_m}m away (comfortably within your {pref_dist}m preference)."
                        else:
                            within_pref = "no"
                            pref_note = f"Nearest listed is {nearest_m}m away (exceeds your {pref_dist}m preference). No listing found within your preferred distance in this map database."

                    count_val = count_item.value if count_item else "multiple"
                    findings.append(Finding(
                        id=f"finding:{prio}",
                        priority=prio,
                        status="available",
                        headline=f"{prio.replace('_', ' ').title()}: Nearest facility identified at {nearest_m}m",
                        detail=f"Found {count_val} listings within search radius. Nearest listed is {nearest_m}m straight-line distance.",
                        metric_name="nearest_distance_m",
                        metric_value=nearest_m,
                        within_preference=within_pref,
                        preference_note=pref_note,
                        evidence_ids=[dist_item.id] + ([count_item.id] if count_item else []),
                        entities=entities_summary
                    ))
                else:
                    findings.append(Finding(
                        id=f"finding:{prio}:unavailable",
                        priority=prio,
                        status="unavailable",
                        headline=f"{prio.replace('_', ' ').title()}: No listings found in map database within search radius",
                        detail="No matching facility was recorded in the integrated map database within 1.5 km. Absence does not prove an amenity does not exist. Verify on site.",
                        metric_name="nearest_distance_m",
                        metric_value=None,
                        within_preference="no" if pref_dist else None,
                        preference_note="No listing found within your preferred distance in this map database." if pref_dist else None,
                        evidence_ids=[]
                    ))

            elif prio == "environment":
                aqi_item = next((it for it in evidence_items if it.module == "environment" and it.metric == "aqi"), None)
                pm25_item = next((it for it in evidence_items if it.module == "environment" and it.metric == "pm25"), None)
                if aqi_item:
                    findings.append(Finding(
                        id="finding:environment",
                        priority="environment",
                        status="limited",
                        headline=f"Environment: Modeled US AQI {aqi_item.value}",
                        detail=f"Regional atmospheric reanalysis model indicates ambient US AQI of {aqi_item.value} (PM2.5: {pm25_item.value if pm25_item else '—'} µg/m³). Note: Modeled estimate, not an exact site sensor.",
                        metric_name="aqi",
                        metric_value=aqi_item.value,
                        evidence_ids=[aqi_item.id] + ([pm25_item.id] if pm25_item else [])
                    ))
                else:
                    findings.append(Finding(
                        id="finding:environment:unavailable",
                        priority="environment",
                        status="unavailable",
                        headline="Environment: Station and modeled metrics unavailable",
                        detail="No environmental data could be resolved for these coordinates.",
                        metric_name="aqi",
                        evidence_ids=[]
                    ))

            elif prio == "commute":
                drive_item = next((it for it in evidence_items if it.module == "commute" and it.metric == "driving_duration_min"), None)
                transit_item = next((it for it in evidence_items if it.module == "commute" and it.metric == "transit_duration_min"), None)
                if drive_item:
                    findings.append(Finding(
                        id="finding:commute",
                        priority="commute",
                        status="available",
                        headline=f"Commute: ~{drive_item.value} mins driving time estimated",
                        detail=f"Estimated driving time: {drive_item.value} mins. Transit route: {transit_item.value if transit_item else '—'} mins. Travel times vary by road congestion.",
                        metric_name="driving_duration_min",
                        metric_value=drive_item.value,
                        evidence_ids=[drive_item.id] + ([transit_item.id] if transit_item else [])
                    ))

        # Build Priority-Gap Callouts
        for prio in selected_priorities:
            if prio == "safety_infrastructure":
                callouts.append(PriorityGapCallout(
                    priority="safety_infrastructure",
                    gap_description="Physical emergency listings vs crime incident statistics.",
                    available_facts="Physical police and fire stations mapped from external listings.",
                    missing_data="Locality-level crime statistics are unavailable from official sources."
                ))

        # Check for water gap
        callouts.append(PriorityGapCallout(
            priority="healthcare",
            gap_description="Locality water supply and quality data.",
            available_facts="Commercial hospitals and pharmacies identified in map listings.",
            missing_data="Building-level drinking water quality and supply schedules are unavailable from public databases."
        ))

        # Select relevant Verify-On-Site questions
        for q in VERIFY_ON_SITE_BANK:
            if q.priority_or_gap in selected_priorities or q.priority_or_gap in ["water", "safety_infrastructure"]:
                checklist.append(q)

        return findings, callouts, checklist
