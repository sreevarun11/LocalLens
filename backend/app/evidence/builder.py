from datetime import datetime
from typing import Any
from backend.app.schemas.base import (
    ModuleResult,
    EvidenceItem,
    EvidenceEntity,
    EvidenceGap,
    DataSourceInfo
)
from backend.app.schemas.location import PlacesData
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, SafetyAndCrimeData, CommuteData

class EvidenceBuilder:
    """
    Pure, deterministic builder converting raw ModuleResults into structured EvidenceItems and Gaps.
    Strictly forbids data fabrication.
    """

    @staticmethod
    def build_evidence(
        locality_key: str,
        places_res: ModuleResult[PlacesData] | None = None,
        env_res: ModuleResult[AirQualityData] | None = None,
        water_res: ModuleResult[WaterQualityData] | None = None,
        crime_res: ModuleResult[SafetyAndCrimeData] | ModuleResult[CrimeData] | None = None,
        commute_res: ModuleResult[CommuteData] | None = None
    ) -> tuple[list[EvidenceItem], list[EvidenceGap]]:
        items: list[EvidenceItem] = []
        gaps: list[EvidenceGap] = []

        now = datetime.utcnow()

        # 1. Process Places Evidence
        if places_res and places_res.data and places_res.status in ["available", "limited"]:
            places = places_res.data.places
            source = places_res.sources[0] if places_res.sources else DataSourceInfo(name="Places Provider")

            # Group places by category
            categories = ["healthcare", "education", "safety_infrastructure", "daily_life", "transport", "lifestyle"]
            for cat in categories:
                cat_title = cat.replace('_', ' ').title()
                cat_places = [p for p in places if p.category == cat]
                # Nearest distance item
                nearest_dist = cat_places[0].distance_m if cat_places else None
                nearest_entities = [
                    EvidenceEntity(
                        name=p.name,
                        place_id=p.id,
                        lat=p.lat,
                        lng=p.lng,
                        distance_m=p.distance_m,
                        category=p.category
                    ) for p in cat_places[:5]
                ]

                nearest_finding = (
                    f"Nearest {cat_title.lower()} is located {nearest_dist}m straight-line distance."
                    if nearest_dist is not None
                    else f"No {cat_title.lower()} recorded within {places_res.coverage.radius_m}m survey radius."
                )

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:nearest_distance_m",
                    locality_key=locality_key,
                    module=cat,
                    metric="nearest_distance_m",
                    title=f"Nearest {cat_title}",
                    finding=nearest_finding,
                    value=nearest_dist,
                    unit="meters",
                    status="available" if nearest_dist is not None else "limited",
                    radius_m=places_res.coverage.radius_m,
                    result_cap_reached=places_res.coverage.result_cap_reached,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="exact_place" if nearest_dist is not None else "nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    reporting_period="Live OpenStreetMap snapshot",
                    geographic_resolution="exact_place" if nearest_dist is not None else "nearby_place",
                    data_kind="map_listing",
                    limitations=places_res.limitations or ["Straight-line distance; actual street walking/driving paths may differ.", "OpenStreetMap community mapping completeness."]
                ))

                # Ring counts (500m, 1000m, 1500m)
                count_500 = len([p for p in cat_places if p.distance_m <= 500])
                count_1000 = len([p for p in cat_places if p.distance_m <= 1000])
                # Full total count from counts_by_category if available, otherwise len(cat_places)
                if places_res.data.counts_by_category and cat in places_res.data.counts_by_category:
                    count_total = places_res.data.counts_by_category[cat]
                else:
                    count_total = len(cat_places)

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:count_within_radius",
                    locality_key=locality_key,
                    module=cat,
                    metric="count_within_radius",
                    title=f"{cat_title} Count (≤{places_res.coverage.radius_m}m)",
                    finding=f"Identified {count_total} {cat_title.lower()} within {places_res.coverage.radius_m}m survey radius.",
                    value=count_total,
                    unit="listings",
                    status="available" if count_total > 0 else "limited",
                    radius_m=places_res.coverage.radius_m,
                    result_cap_reached=places_res.coverage.result_cap_reached,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    reporting_period="Live OpenStreetMap snapshot",
                    geographic_resolution="nearby_place",
                    data_kind="map_listing",
                    limitations=places_res.limitations or ["Straight-line radius survey; subject to open contributor mapping density."]
                ))

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:ring_500m_count",
                    locality_key=locality_key,
                    module=cat,
                    metric="ring_500m_count",
                    title=f"{cat_title} (≤500m Ring)",
                    finding=f"{count_500} {cat_title.lower()} within 500m pedestrian radius.",
                    value=count_500,
                    unit="listings",
                    status="available",
                    radius_m=500,
                    result_cap_reached=False,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    reporting_period="Live OpenStreetMap snapshot",
                    geographic_resolution="nearby_place",
                    data_kind="map_listing",
                    limitations=places_res.limitations
                ))

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:ring_1000m_count",
                    locality_key=locality_key,
                    module=cat,
                    metric="ring_1000m_count",
                    title=f"{cat_title} (≤1000m Ring)",
                    finding=f"{count_1000} {cat_title.lower()} within 1000m radius.",
                    value=count_1000,
                    unit="listings",
                    status="available",
                    radius_m=1000,
                    result_cap_reached=False,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    reporting_period="Live OpenStreetMap snapshot",
                    geographic_resolution="nearby_place",
                    data_kind="map_listing",
                    limitations=places_res.limitations
                ))

                # Transparent mapping gap if no records were found in this category
                if count_total == 0:
                    gaps.append(EvidenceGap(
                        module=cat,
                        status="limited",
                        available_facts=f"Survey completed within {places_res.coverage.radius_m}m radius.",
                        missing_data=f"No matching {cat.replace('_', ' ')} records found in OpenStreetMap data within {places_res.coverage.radius_m}m survey radius.",
                        reason=f"No matching records found in OpenStreetMap data within {places_res.coverage.radius_m}m survey radius; this indicates a mapping data gap, not physical absence.",
                        granularity_needed="exact_place"
                    ))
        else:
            status_desc = places_res.status if places_res else "unavailable"
            err_msg = places_res.message if places_res and places_res.message else "Nearby places data unavailable"
            gaps.append(EvidenceGap(
                module="places",
                status=status_desc if status_desc in ["limited", "error"] else "unavailable",
                available_facts="None",
                missing_data="Nearby places dataset unavailable",
                reason=f"Nearby places dataset/provider unavailable ({status_desc}): {err_msg}",
                granularity_needed="exact_place"
            ))

        # 2. Process Environment Evidence
        if env_res and env_res.data and env_res.status in ["available", "limited"]:
            env_data = env_res.data
            source = env_res.sources[0] if env_res.sources else DataSourceInfo(name="Open-Meteo Air Quality")
            rep_period = env_res.measured_at.strftime("%Y-%m-%d %H:%M UTC") if env_res.measured_at else "Current model forecast"
            geo_res = f"{env_data.model_grid_resolution_km or 11} km atmospheric grid" if env_res.provenance_kind == "modeled_estimate" else "monitoring_station"

            if env_data.aqi is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:aqi",
                    locality_key=locality_key,
                    module="environment",
                    metric="aqi",
                    title="Air Quality Index (AQI)",
                    finding=f"Ambient US AQI: {env_data.aqi} ({env_data.aqi_scale})",
                    value=env_data.aqi,
                    unit=env_data.aqi_scale,
                    status="available" if env_res.provenance_kind == "station_measurement" else "limited",
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    reporting_period=rep_period,
                    geographic_resolution=geo_res,
                    data_kind=env_res.provenance_kind,
                    limitations=env_res.limitations or ["European CAMS atmospheric model grid estimate (~11 km resolution), not an on-site property sensor."]
                ))
            if env_data.pm25 is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:pm25",
                    locality_key=locality_key,
                    module="environment",
                    metric="pm25",
                    title="Particulate Matter PM2.5",
                    finding=f"Ambient PM2.5 concentration: {env_data.pm25} µg/m³",
                    value=env_data.pm25,
                    unit="µg/m³",
                    status="available" if env_res.provenance_kind == "station_measurement" else "limited",
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    reporting_period=rep_period,
                    geographic_resolution=geo_res,
                    data_kind=env_res.provenance_kind,
                    limitations=env_res.limitations
                ))
            if env_data.pm10 is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:pm10",
                    locality_key=locality_key,
                    module="environment",
                    metric="pm10",
                    title="Particulate Matter PM10",
                    finding=f"Ambient PM10 concentration: {env_data.pm10} µg/m³",
                    value=env_data.pm10,
                    unit="µg/m³",
                    status="available" if env_res.provenance_kind == "station_measurement" else "limited",
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    reporting_period=rep_period,
                    geographic_resolution=geo_res,
                    data_kind=env_res.provenance_kind,
                    limitations=env_res.limitations
                ))
            if env_data.temperature_c is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:temperature_c",
                    locality_key=locality_key,
                    module="environment",
                    metric="temperature_c",
                    title="Ambient Temperature",
                    finding=f"Temperature: {env_data.temperature_c}°C ({env_data.weather_desc or 'Current'})",
                    value=env_data.temperature_c,
                    unit="°C",
                    status="available",
                    entities=[],
                    provenance_kind="modeled_estimate",
                    granularity="grid_forecast",
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    reporting_period=rep_period,
                    geographic_resolution="grid_forecast",
                    data_kind="weather_forecast",
                    limitations=["Numerical weather model forecast"]
                ))
        else:
            status_desc = env_res.status if env_res else "unavailable"
            gaps.append(EvidenceGap(
                module="environment",
                status=status_desc if status_desc in ["limited", "error"] else "unavailable",
                available_facts="None",
                missing_data="Atmospheric and air quality measurements",
                reason=env_res.message if env_res else "Environmental metrics unavailable",
                granularity_needed="monitoring_station"
            ))

        # 3. Process Water Quality
        if water_res and water_res.data and water_res.status in ["available", "limited"]:
            w_data = water_res.data
            source = water_res.sources[0] if water_res.sources else DataSourceInfo(name="Central Ground Water Board (CGWB) & Ground Water Department, Govt. of Telangana")
            rep_year = w_data.reporting_year or "Assessment Year 2022"
            geo_res = w_data.geographic_resolution or (f"Mandal ({w_data.mandal_name})" if w_data.data_level == "mandal" else f"District ({w_data.district_name})")

            if w_data.assessment_category is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:water:assessment_category",
                    locality_key=locality_key,
                    module="water",
                    metric="assessment_category",
                    title="Groundwater Assessment Category",
                    finding=f"Aquifer extraction status: {w_data.assessment_category} ({w_data.data_level.title() if w_data.data_level else 'Regional'})",
                    value=w_data.assessment_category,
                    unit="category",
                    status="available",
                    entities=[],
                    provenance_kind=water_res.provenance_kind,
                    granularity=water_res.coverage.granularity,
                    source=source,
                    fetched_at=water_res.fetched_at,
                    measured_at=water_res.measured_at,
                    reporting_period=rep_year,
                    geographic_resolution=geo_res,
                    data_kind="historical_assessment",
                    limitations=water_res.limitations or ["Groundwater assessment categories evaluate regional aquifer recharge vs extraction balances and do NOT certify drinking-water potability.", "Ambient chemistry baseline reflects deep monitoring wells, not municipal tap water."]
                ))

            if w_data.stage_of_extraction_pct is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:water:stage_of_extraction_pct",
                    locality_key=locality_key,
                    module="water",
                    metric="stage_of_extraction_pct",
                    title="Stage of Groundwater Extraction",
                    finding=f"Groundwater extraction stage: {w_data.stage_of_extraction_pct}% ({w_data.data_level.title() if w_data.data_level else 'Regional'})",
                    value=w_data.stage_of_extraction_pct,
                    unit="%",
                    status="available",
                    entities=[],
                    provenance_kind=water_res.provenance_kind,
                    granularity=water_res.coverage.granularity,
                    source=source,
                    fetched_at=water_res.fetched_at,
                    measured_at=water_res.measured_at,
                    reporting_period=rep_year,
                    geographic_resolution=w_data.data_level or "district",
                    data_kind="historical_assessment",
                    limitations=water_res.limitations
                ))

            if w_data.district_stage_of_extraction_pct is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:water:district_stage_of_extraction_pct",
                    locality_key=locality_key,
                    module="water",
                    metric="district_stage_of_extraction_pct",
                    title=f"{w_data.district_name or 'District'} Stage of Groundwater Extraction",
                    finding=f"District aggregate groundwater extraction stage: {w_data.district_stage_of_extraction_pct}%",
                    value=w_data.district_stage_of_extraction_pct,
                    unit="%",
                    status="available",
                    entities=[],
                    provenance_kind=water_res.provenance_kind,
                    granularity="district",
                    source=source,
                    fetched_at=water_res.fetched_at,
                    measured_at=water_res.measured_at,
                    reporting_period=rep_year,
                    geographic_resolution="district",
                    data_kind="historical_assessment",
                    limitations=water_res.limitations
                ))

            if w_data.mandal_stage_of_extraction_pct is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:water:mandal_stage_of_extraction_pct",
                    locality_key=locality_key,
                    module="water",
                    metric="mandal_stage_of_extraction_pct",
                    title=f"{w_data.mandal_name or 'Mandal'} Stage of Groundwater Extraction",
                    finding=f"Mandal groundwater extraction stage: {w_data.mandal_stage_of_extraction_pct}%",
                    value=w_data.mandal_stage_of_extraction_pct,
                    unit="%",
                    status="available",
                    entities=[],
                    provenance_kind=water_res.provenance_kind,
                    granularity="mandal",
                    source=source,
                    fetched_at=water_res.fetched_at,
                    measured_at=water_res.measured_at,
                    reporting_period=rep_year,
                    geographic_resolution="mandal",
                    data_kind="historical_assessment",
                    limitations=water_res.limitations
                ))

            # Building-level tap-water quality gap callout is STILL registered per requirement 5
            gaps.append(EvidenceGap(
                module="water",
                status="unavailable",
                available_facts=f"CGWB regional aquifer extraction assessment ({w_data.assessment_category or 'assessed'}).",
                missing_data="Continuous building-level municipal tap water quality (TDS/pH/chlorine) and daily supply schedules.",
                reason="Official groundwater resource assessments evaluate regional aquifer extraction and do not certify building-level tap drinking water quality.",
                granularity_needed="property"
            ))
        else:
            status_desc = water_res.status if water_res else "unavailable"
            gaps.append(EvidenceGap(
                module="water",
                status=status_desc if status_desc in ["limited", "error"] else "unavailable",
                available_facts="State-level coverage in Telangana dataset.",
                missing_data="Official groundwater assessment for coordinates outside Telangana.",
                reason=water_res.message if water_res and water_res.message else "Official water resource metrics unavailable for this location.",
                granularity_needed="property"
            ))

        # 4. Process Safety Infrastructure & Crime Data (Known Gap for micro crime rates)
        if crime_res and crime_res.data and crime_res.status in ["available", "limited"]:
            c_data = crime_res.data
            if hasattr(c_data, "nearby_facilities") and c_data.nearby_facilities:
                police_facs = [f for f in c_data.nearby_facilities if f.facility_type == "police"]
                fire_facs = [f for f in c_data.nearby_facilities if f.facility_type == "fire_station"]
                source_fac = crime_res.sources[0] if crime_res.sources else DataSourceInfo(name="OpenStreetMap")

                if police_facs:
                    np = police_facs[0]
                    items.append(EvidenceItem(
                        id=f"{locality_key}:safety:nearest_police_m",
                        locality_key=locality_key,
                        module="safety_infrastructure",
                        metric="nearest_police_distance_m",
                        title="Nearest Police Station",
                        finding=f"Nearest police station is {np.name} ({np.distance_m}m / {np.distance_km} km)",
                        value=np.distance_m,
                        unit="meters",
                        status="available",
                        entities=[
                            EvidenceEntity(
                                name=np.name,
                                place_id=np.id,
                                lat=np.lat,
                                lng=np.lng,
                                distance_m=np.distance_m,
                                category="safety_infrastructure"
                            )
                        ],
                        provenance_kind=crime_res.provenance_kind,
                        granularity="exact_place",
                        source=source_fac,
                        fetched_at=crime_res.fetched_at,
                        reporting_period="Live OpenStreetMap snapshot",
                        geographic_resolution="exact_place",
                        data_kind="map_listing",
                        limitations=crime_res.limitations
                    ))

                if fire_facs:
                    nf = fire_facs[0]
                    items.append(EvidenceItem(
                        id=f"{locality_key}:safety:nearest_fire_station_m",
                        locality_key=locality_key,
                        module="safety_infrastructure",
                        metric="nearest_fire_distance_m",
                        title="Nearest Fire Station",
                        finding=f"Nearest fire station is {nf.name} ({nf.distance_m}m / {nf.distance_km} km)",
                        value=nf.distance_m,
                        unit="meters",
                        status="available",
                        entities=[
                            EvidenceEntity(
                                name=nf.name,
                                place_id=nf.id,
                                lat=nf.lat,
                                lng=nf.lng,
                                distance_m=nf.distance_m,
                                category="safety_infrastructure"
                            )
                        ],
                        provenance_kind=crime_res.provenance_kind,
                        granularity="exact_place",
                        source=source_fac,
                        fetched_at=crime_res.fetched_at,
                        reporting_period="Live OpenStreetMap snapshot",
                        geographic_resolution="exact_place",
                        data_kind="map_listing",
                        limitations=crime_res.limitations
                    ))

            if hasattr(c_data, "emergency_contacts") and c_data.emergency_contacts:
                items.append(EvidenceItem(
                    id=f"{locality_key}:safety:emergency_contacts_count",
                    locality_key=locality_key,
                    module="safety_infrastructure",
                    metric="emergency_contacts_count",
                    title="Verified Emergency Helplines",
                    finding=f"{len(c_data.emergency_contacts)} verified emergency services active statewide (112, 100, 101, 108, 1090, 1930)",
                    value=len(c_data.emergency_contacts),
                    unit="services",
                    status="available",
                    entities=[],
                    provenance_kind=crime_res.provenance_kind,
                    granularity="state",
                    source=DataSourceInfo(
                        name="Telangana State Police & Emergency Services",
                        url="https://tspolice.gov.in"
                    ),
                    fetched_at=crime_res.fetched_at,
                    reporting_period="Telangana Police Official Emergency Directory",
                    geographic_resolution="state",
                    data_kind="emergency_directory",
                    limitations=crime_res.limitations
                ))

            if hasattr(c_data, "jurisdiction") and c_data.jurisdiction and c_data.jurisdiction.jurisdiction_name:
                items.append(EvidenceItem(
                    id=f"{locality_key}:safety:police_jurisdiction",
                    locality_key=locality_key,
                    module="safety_infrastructure",
                    metric="police_jurisdiction",
                    title="Police Jurisdiction",
                    finding=f"Covered by {c_data.jurisdiction.jurisdiction_name} ({c_data.jurisdiction.jurisdiction_type.replace('_', ' ').title()})",
                    value=c_data.jurisdiction.jurisdiction_name,
                    unit="administrative_unit",
                    status="available" if c_data.jurisdiction.jurisdiction_type != "unavailable" else "limited",
                    entities=[],
                    provenance_kind=crime_res.provenance_kind,
                    granularity="commissionerate" if c_data.jurisdiction.jurisdiction_type == "commissionerate" else "district",
                    source=DataSourceInfo(
                        name="Telangana State Police",
                        url=c_data.jurisdiction.source_url or "https://tspolice.gov.in"
                    ),
                    fetched_at=crime_res.fetched_at,
                    reporting_period="Telangana Police Administrative Framework",
                    geographic_resolution=c_data.jurisdiction.jurisdiction_type,
                    data_kind="administrative_jurisdiction",
                    limitations=c_data.jurisdiction.limitations
                ))

        gaps.append(EvidenceGap(
            module="crime",
            status="unavailable",
            available_facts="Mapped emergency infrastructure, verified emergency directory, and police jurisdiction.",
            missing_data="Micro-neighborhood crime incidence rates and street-level crime records.",
            reason="Locality-level crime incident statistics are unavailable from official sources (NCRB only compiles district/commissionerate aggregates).",
            granularity_needed="locality"
        ))

        # 5. Process Commute Evidence
        if commute_res and commute_res.data and commute_res.status in ["available", "limited"]:
            c_data = commute_res.data
            source = commute_res.sources[0] if commute_res.sources else DataSourceInfo(name="OSRM Road-Network Engine")
            for mode_key, mode_val in c_data.modes.items():
                if mode_val.status == "available" and mode_val.duration_min is not None:
                    items.append(EvidenceItem(
                        id=f"{locality_key}:commute:{mode_key}_duration_min",
                        locality_key=locality_key,
                        module="commute",
                        metric=f"{mode_key}_duration_min",
                        title=f"{mode_key.title()} Commute Duration",
                        finding=f"Estimated {mode_key} duration: {mode_val.duration_min} mins via road network",
                        value=mode_val.duration_min,
                        unit="minutes",
                        status="available",
                        entities=[],
                        provenance_kind=commute_res.provenance_kind,
                        granularity="exact_place",
                        source=source,
                        fetched_at=commute_res.fetched_at,
                        reporting_period="Real-time OSRM network calculation",
                        geographic_resolution="exact_place",
                        data_kind="road_network_estimate",
                        limitations=mode_val.limitations or commute_res.limitations or ["OSRM road-network routing estimate without live traffic congestion or traffic signal delays"]
                    ))
                if mode_val.status == "available" and mode_val.distance_km is not None:
                    items.append(EvidenceItem(
                        id=f"{locality_key}:commute:{mode_key}_distance_km",
                        locality_key=locality_key,
                        module="commute",
                        metric=f"{mode_key}_distance_km",
                        title=f"{mode_key.title()} Commute Distance",
                        finding=f"Road-network route distance: {mode_val.distance_km} km",
                        value=mode_val.distance_km,
                        unit="km",
                        status="available",
                        entities=[],
                        provenance_kind=commute_res.provenance_kind,
                        granularity="exact_place",
                        source=source,
                        fetched_at=commute_res.fetched_at,
                        reporting_period="Real-time OSRM network calculation",
                        geographic_resolution="exact_place",
                        data_kind="road_network_estimate",
                        limitations=mode_val.limitations or commute_res.limitations or ["OSRM road-network routing estimate"]
                    ))

            # Transparently record transit schedule gap if transit timetables are unavailable
            transit_mode = c_data.modes.get("transit")
            if not transit_mode or transit_mode.status != "available":
                gaps.append(EvidenceGap(
                    module="commute",
                    status="unavailable",
                    available_facts="Mapped road-network route distance and driving estimates.",
                    missing_data="Live transit timetables, bus/metro schedules, and real-time congestion delays.",
                    reason="Public transit timetables and journey schedules are unavailable without a verified agency GTFS feed; transit times are not invented or synthesized from car speeds.",
                    granularity_needed="exact_place"
                ))
        elif commute_res and commute_res.status in ["unavailable", "error"]:
            status_desc = commute_res.status
            gaps.append(EvidenceGap(
                module="commute",
                status=status_desc,
                available_facts="None",
                missing_data="Road-network routing estimate",
                reason=commute_res.message or "Road-network routing unavailable between the specified coordinates.",
                granularity_needed="exact_place"
            ))

        return items, gaps
