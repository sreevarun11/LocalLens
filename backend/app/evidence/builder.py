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
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, CommuteData

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
        crime_res: ModuleResult[CrimeData] | None = None,
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

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:nearest_distance_m",
                    locality_key=locality_key,
                    module=cat,
                    metric="nearest_distance_m",
                    value=nearest_dist,
                    unit="meters",
                    radius_m=places_res.coverage.radius_m,
                    result_cap_reached=places_res.coverage.result_cap_reached,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="exact_place" if nearest_dist is not None else "nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    limitations=places_res.limitations
                ))

                # Ring counts (500m, 1000m, 1500m)
                count_500 = len([p for p in cat_places if p.distance_m <= 500])
                count_1000 = len([p for p in cat_places if p.distance_m <= 1000])
                count_total = len(cat_places)

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:count_within_radius",
                    locality_key=locality_key,
                    module=cat,
                    metric="count_within_radius",
                    value=count_total,
                    unit="listings",
                    radius_m=places_res.coverage.radius_m,
                    result_cap_reached=places_res.coverage.result_cap_reached,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    limitations=places_res.limitations
                ))

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:ring_500m_count",
                    locality_key=locality_key,
                    module=cat,
                    metric="ring_500m_count",
                    value=count_500,
                    unit="listings",
                    radius_m=500,
                    result_cap_reached=False,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    limitations=places_res.limitations
                ))

                items.append(EvidenceItem(
                    id=f"{locality_key}:{cat}:ring_1000m_count",
                    locality_key=locality_key,
                    module=cat,
                    metric="ring_1000m_count",
                    value=count_1000,
                    unit="listings",
                    radius_m=1000,
                    result_cap_reached=False,
                    entities=nearest_entities,
                    provenance_kind=places_res.provenance_kind,
                    granularity="nearby_place",
                    source=source,
                    fetched_at=places_res.fetched_at,
                    limitations=places_res.limitations
                ))
        else:
            gaps.append(EvidenceGap(
                module="places",
                reason=places_res.message if places_res else "Nearby places not retrieved",
                granularity_needed="exact_place"
            ))

        # 2. Process Environment Evidence
        if env_res and env_res.data and env_res.status in ["available", "limited"]:
            env_data = env_res.data
            source = env_res.sources[0] if env_res.sources else DataSourceInfo(name="Open-Meteo Air Quality")

            if env_data.aqi is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:aqi",
                    locality_key=locality_key,
                    module="environment",
                    metric="aqi",
                    value=env_data.aqi,
                    unit=env_data.aqi_scale,
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    limitations=env_res.limitations
                ))
            if env_data.pm25 is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:pm25",
                    locality_key=locality_key,
                    module="environment",
                    metric="pm25",
                    value=env_data.pm25,
                    unit="µg/m³",
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    limitations=env_res.limitations
                ))
            if env_data.pm10 is not None:
                items.append(EvidenceItem(
                    id=f"{locality_key}:environment:pm10",
                    locality_key=locality_key,
                    module="environment",
                    metric="pm10",
                    value=env_data.pm10,
                    unit="µg/m³",
                    entities=[],
                    provenance_kind=env_res.provenance_kind,
                    granularity=env_res.coverage.granularity,
                    source=source,
                    fetched_at=env_res.fetched_at,
                    measured_at=env_res.measured_at,
                    limitations=env_res.limitations
                ))
        else:
            gaps.append(EvidenceGap(
                module="environment",
                reason=env_res.message if env_res else "Environmental metrics unavailable",
                granularity_needed="monitoring_station"
            ))

        # 3. Process Water Quality (Known Gap)
        gaps.append(EvidenceGap(
            module="water",
            reason="No integrated machine-readable water quality dataset exists for this locality.",
            granularity_needed="property"
        ))

        # 4. Process Crime Data (Known Gap)
        gaps.append(EvidenceGap(
            module="crime",
            reason="Locality-level crime incident statistics are unavailable from official sources (NCRB only compiles district/commissionerate aggregates).",
            granularity_needed="locality"
        ))

        # 5. Process Commute Evidence
        if commute_res and commute_res.data and commute_res.status in ["available", "limited"]:
            c_data = commute_res.data
            source = commute_res.sources[0] if commute_res.sources else DataSourceInfo(name="Routes Provider")
            for mode_key, mode_val in c_data.modes.items():
                if mode_val.duration_min is not None:
                    items.append(EvidenceItem(
                        id=f"{locality_key}:commute:{mode_key}_duration_min",
                        locality_key=locality_key,
                        module="commute",
                        metric=f"{mode_key}_duration_min",
                        value=mode_val.duration_min,
                        unit="minutes",
                        entities=[],
                        provenance_kind=commute_res.provenance_kind,
                        granularity="exact_place",
                        source=source,
                        fetched_at=commute_res.fetched_at,
                        limitations=commute_res.limitations
                    ))
                if mode_val.distance_km is not None:
                    items.append(EvidenceItem(
                        id=f"{locality_key}:commute:{mode_key}_distance_km",
                        locality_key=locality_key,
                        module="commute",
                        metric=f"{mode_key}_distance_km",
                        value=mode_val.distance_km,
                        unit="km",
                        entities=[],
                        provenance_kind=commute_res.provenance_kind,
                        granularity="exact_place",
                        source=source,
                        fetched_at=commute_res.fetched_at,
                        limitations=commute_res.limitations
                    ))

        return items, gaps
