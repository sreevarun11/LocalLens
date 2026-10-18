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
    "commute",
    "water"
]

PROFILE_DEFAULTS: dict[ProfileKey, list[PriorityKey]] = {
    "family": ["education", "healthcare", "transport", "daily_life", "parks"],
    "commuter": ["transport", "commute", "daily_life", "safety_infrastructure"],
    "student": ["education", "transport", "daily_life", "lifestyle"],
    "elderly": ["healthcare", "daily_life", "parks", "safety_infrastructure"],
    "first_time_renter": ["transport", "daily_life", "lifestyle", "commute"],
    "home_buyer": ["education", "healthcare", "transport", "environment", "water", "safety_infrastructure"],
    "relocation": ["healthcare", "education", "transport", "daily_life", "environment", "safety_infrastructure"]
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
    ),
    VerifyOnSiteQuestion(
        id="vos_daily_essentials",
        priority_or_gap="daily_life",
        question="Are fresh grocery markets, pharmacies, and daily household repair services accessible on foot without crossing major highways?",
        context="Listing databases track commercial POIs, not operational stock, opening hours, or pedestrian safety."
    ),
    VerifyOnSiteQuestion(
        id="vos_parks_open_space",
        priority_or_gap="parks",
        question="Is the nearest public park or walking track well-maintained, lighted after sunset, and freely accessible to residents?",
        context="Geospatial boundaries record land use, not maintenance quality or gate hours."
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

        # Process each selected priority in deterministic priority order
        for prio in selected_priorities:
            pref_dist = pref_map.get(prio)

            if prio in ["education", "healthcare", "daily_life", "transport", "lifestyle", "parks"]:
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
                        detail="No matching facility was recorded in the integrated map database within search radius. Absence does not prove an amenity does not exist. Verify on site.",
                        metric_name="nearest_distance_m",
                        metric_value=None,
                        within_preference="no" if pref_dist else None,
                        preference_note="No listing found within your preferred distance in this map database." if pref_dist else None,
                        evidence_ids=[]
                    ))

            elif prio == "safety_infrastructure":
                police_item = next((it for it in evidence_items if it.module == "safety_infrastructure" and it.metric == "nearest_police_distance_m"), None)
                fire_item = next((it for it in evidence_items if it.module == "safety_infrastructure" and it.metric == "nearest_fire_distance_m"), None)
                contacts_item = next((it for it in evidence_items if it.module == "safety_infrastructure" and it.metric == "emergency_contacts_count"), None)
                jur_item = next((it for it in evidence_items if it.module == "safety_infrastructure" and it.metric == "police_jurisdiction"), None)

                # Fallback to places module safety_infrastructure if safety provider items not present
                places_safety = next((it for it in evidence_items if it.module == "safety_infrastructure" and it.metric == "nearest_distance_m"), None)

                nearest_m = None
                if police_item and police_item.value is not None:
                    nearest_m = int(police_item.value)
                elif places_safety and places_safety.value is not None:
                    nearest_m = int(places_safety.value)

                evidence_ids = []
                if police_item: evidence_ids.append(police_item.id)
                if fire_item: evidence_ids.append(fire_item.id)
                if contacts_item: evidence_ids.append(contacts_item.id)
                if jur_item: evidence_ids.append(jur_item.id)
                if places_safety and not evidence_ids: evidence_ids.append(places_safety.id)

                entities_summary = []
                if police_item and police_item.entities:
                    entities_summary.extend([{"name": e.name, "distance_m": e.distance_m} for e in police_item.entities])
                if fire_item and fire_item.entities:
                    entities_summary.extend([{"name": e.name, "distance_m": e.distance_m} for e in fire_item.entities])

                if nearest_m is not None:
                    within_pref = None
                    pref_note = None
                    if pref_dist is not None:
                        if nearest_m <= pref_dist:
                            within_pref = "yes"
                            pref_note = f"Nearest emergency facility is {nearest_m}m away (within your {pref_dist}m preference)."
                        else:
                            within_pref = "no"
                            pref_note = f"Nearest listed emergency station is {nearest_m}m away (exceeds your {pref_dist}m preference)."

                    jur_text = f" Jurisdiction: {jur_item.value}." if jur_item else ""
                    contacts_text = f" Statewide emergency helpline 112 active ({contacts_item.value} services verified)." if contacts_item else ""
                    findings.append(Finding(
                        id="finding:safety_infrastructure",
                        priority="safety_infrastructure",
                        status="available",
                        headline=f"Safety Infrastructure: Nearest police station at {nearest_m}m",
                        detail=f"Nearest police station is {nearest_m}m away.{jur_text}{contacts_text} Note: Locality crime incident statistics are unavailable from official sources.",
                        metric_name="nearest_police_distance_m",
                        metric_value=nearest_m,
                        within_preference=within_pref,
                        preference_note=pref_note,
                        evidence_ids=evidence_ids,
                        entities=entities_summary
                    ))
                else:
                    findings.append(Finding(
                        id="finding:safety_infrastructure:limited",
                        priority="safety_infrastructure",
                        status="limited",
                        headline="Safety Infrastructure: No police station recorded within search radius",
                        detail="No police or fire station was recorded within the survey radius in OpenStreetMap. Statewide emergency helpline 112 is active. Locality crime statistics are unavailable.",
                        metric_name="nearest_police_distance_m",
                        metric_value=None,
                        within_preference="no" if pref_dist else None,
                        preference_note="No emergency station found within your preferred distance in map database." if pref_dist else None,
                        evidence_ids=evidence_ids
                    ))

            elif prio == "environment":
                aqi_item = next((it for it in evidence_items if it.module == "environment" and it.metric == "aqi"), None)
                pm25_item = next((it for it in evidence_items if it.module == "environment" and it.metric == "pm25"), None)
                if aqi_item:
                    findings.append(Finding(
                        id="finding:environment",
                        priority="environment",
                        status="limited" if aqi_item.provenance_kind == "modeled_estimate" else "available",
                        headline=f"Environment: Modeled US AQI {aqi_item.value}",
                        detail=f"Regional atmospheric reanalysis model indicates ambient US AQI of {aqi_item.value} (PM2.5: {pm25_item.value if pm25_item else '—'} µg/m³). Note: European CAMS ~11 km grid estimate, not an on-site property sensor.",
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
                dist_item = next((it for it in evidence_items if it.module == "commute" and it.metric == "driving_distance_km"), None)
                if drive_item:
                    findings.append(Finding(
                        id="finding:commute",
                        priority="commute",
                        status="available",
                        headline=f"Commute: ~{drive_item.value} mins driving time estimated",
                        detail=f"Estimated driving time: {drive_item.value} mins ({dist_item.value if dist_item else '—'} km). Transit route: {transit_item.value if transit_item else 'Unavailable without GTFS feed'} mins. Travel times vary by road congestion.",
                        metric_name="driving_duration_min",
                        metric_value=drive_item.value,
                        evidence_ids=[drive_item.id] + ([transit_item.id] if transit_item else []) + ([dist_item.id] if dist_item else [])
                    ))
                else:
                    findings.append(Finding(
                        id="finding:commute:unavailable",
                        priority="commute",
                        status="unavailable",
                        headline="Commute: Road-network routing unavailable",
                        detail="No road route could be computed between the specified coordinates.",
                        metric_name="driving_duration_min",
                        evidence_ids=[]
                    ))

            elif prio == "water":
                cat_item = next((it for it in evidence_items if it.module == "water" and it.metric == "assessment_category"), None)
                dist_soe = next((it for it in evidence_items if it.module == "water" and it.metric == "district_stage_of_extraction_pct"), None)
                mandal_soe = next((it for it in evidence_items if it.module == "water" and it.metric == "mandal_stage_of_extraction_pct"), None)
                if cat_item:
                    m_text = f"Mandal extraction: {mandal_soe.value}%" if mandal_soe and mandal_soe.value is not None else "Mandal extraction percentage unavailable in published state summary tables"
                    d_text = f"District aggregate extraction: {dist_soe.value}%" if dist_soe and dist_soe.value is not None else ""
                    findings.append(Finding(
                        id="finding:water",
                        priority="water",
                        status="available",
                        headline=f"Water Resources: Aquifer Categorized as {cat_item.value}",
                        detail=f"Official CGWB baseline assessment ({cat_item.reporting_period or '2022'}). {d_text}. {m_text}. Note: Regional aquifer sustainability does not certify tap drinking-water potability.",
                        metric_name="assessment_category",
                        metric_value=cat_item.value,
                        evidence_ids=[cat_item.id] + ([dist_soe.id] if dist_soe else []) + ([mandal_soe.id] if mandal_soe else [])
                    ))
                else:
                    findings.append(Finding(
                        id="finding:water:unavailable",
                        priority="water",
                        status="unavailable",
                        headline="Water Resources: Official Assessment Unavailable",
                        detail="No official CGWB groundwater assessment found for this location (outside Telangana coverage). Tap water quality must be tested on site.",
                        metric_name="assessment_category",
                        evidence_ids=[]
                    ))

        # Build Priority-Gap Callouts for active priorities
        for prio in selected_priorities:
            if prio == "safety_infrastructure":
                callouts.append(PriorityGapCallout(
                    priority="safety_infrastructure",
                    gap_description="Physical emergency listings vs crime incident statistics.",
                    available_facts="Physical police and fire stations mapped from open geospatial listings.",
                    missing_data="Locality-level crime statistics are unavailable from official sources."
                ))
            elif prio == "water":
                callouts.append(PriorityGapCallout(
                    priority="water",
                    gap_description="Aquifer extraction assessment vs building tap water potability.",
                    available_facts="Regional CGWB groundwater resource assessment and aquifer categorization.",
                    missing_data="Building-level drinking water quality and supply schedules are unavailable from public databases."
                ))
            elif prio == "commute":
                callouts.append(PriorityGapCallout(
                    priority="commute",
                    gap_description="Road-network routing estimate vs real-time traffic and transit.",
                    available_facts="OSRM road-network distance and nominal driving duration.",
                    missing_data="Live transit timetable schedules and traffic delay feeds."
                ))
            elif prio == "environment":
                callouts.append(PriorityGapCallout(
                    priority="environment",
                    gap_description="Regional atmospheric grid model vs street-level air quality.",
                    available_facts="European CAMS ~11 km regional atmospheric model estimates.",
                    missing_data="Hyperlocal, property-level air and noise pollution sensors."
                ))

        # Check for water gap callout under healthcare if water wasn't explicitly selected (preserves section 8 requirement)
        if "water" not in selected_priorities and "healthcare" in selected_priorities:
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
