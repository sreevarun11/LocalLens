from typing import Literal
from pydantic import BaseModel, Field
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.location import PlacesData
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, CommuteData
from backend.app.evidence.personalization import PriorityKey

ComparabilityStatus = Literal["comparable", "partly_comparable", "not_comparable"]

class ComparisonRow(BaseModel):
    category: str
    priority: PriorityKey | str
    metric: str
    label: str
    val_a: str | int | float | None = None
    val_b: str | int | float | None = None
    unit: str | None = None
    comparability: ComparabilityStatus
    comparability_reason: str | None = None
    difference_statement: str | None = None
    source_a: str
    source_b: str
    caveat: str | None = None

class LocalityComparisonSummary(BaseModel):
    locality_a_name: str
    locality_b_name: str
    radius_m: int = 1500
    key_differences: list[str]
    data_gaps: list[str]
    coverage_differences: list[str]
    rows: list[ComparisonRow]

class ComparisonEngine:
    @staticmethod
    def compare_localities(
        loc_a_name: str,
        loc_b_name: str,
        places_a: ModuleResult[PlacesData] | None,
        places_b: ModuleResult[PlacesData] | None,
        env_a: ModuleResult[AirQualityData] | None,
        env_b: ModuleResult[AirQualityData] | None,
        water_a: ModuleResult[WaterQualityData] | None,
        water_b: ModuleResult[WaterQualityData] | None,
        crime_a: ModuleResult[CrimeData] | None,
        crime_b: ModuleResult[CrimeData] | None,
        priorities: list[PriorityKey] | None = None,
        radius_m: int = 1500
    ) -> LocalityComparisonSummary:
        rows: list[ComparisonRow] = []
        key_differences: list[str] = []
        data_gaps: list[str] = []
        coverage_diffs: list[str] = []

        active_priorities = priorities or [
            "education", "healthcare", "transport", "daily_life", "parks", "environment"
        ]

        # 1. Compare Places Categories
        cat_labels = {
            "education": "Schools & Education",
            "healthcare": "Healthcare Facilities",
            "transport": "Public Transit & Stops",
            "daily_life": "Daily Essentials & Groceries",
            "lifestyle": "Cafes & Lifestyle",
            "parks": "Parks & Green Spaces",
            "safety_infrastructure": "Emergency & Safety Infrastructure"
        }

        source_a_name = places_a.sources[0].name if (places_a and places_a.sources) else "Unknown"
        source_b_name = places_b.sources[0].name if (places_b and places_b.sources) else "Unknown"
        same_source = (source_a_name == source_b_name) and (source_a_name != "Unknown")

        # OSM completeness caveat
        is_osm = "OpenStreetMap" in source_a_name or "OpenStreetMap" in source_b_name
        osm_caveat = "Map-data completeness varies by area; a lower count may reflect fewer mapped features." if is_osm else None

        for prio in active_priorities:
            if prio in cat_labels:
                places_list_a = [p for p in (places_a.data.places if (places_a and places_a.data) else []) if p.category == prio or (prio == "parks" and p.subcategory == "park")]
                places_list_b = [p for p in (places_b.data.places if (places_b and places_b.data) else []) if p.category == prio or (prio == "parks" and p.subcategory == "park")]

                nearest_a = places_list_a[0].distance_m if places_list_a else None
                nearest_b = places_list_b[0].distance_m if places_list_b else None
                count_a = len(places_list_a)
                count_b = len(places_list_b)

                cap_a = places_a.coverage.result_cap_reached if places_a else False
                cap_b = places_b.coverage.result_cap_reached if places_b else False

                # Evaluate Comparability
                comp_status: ComparabilityStatus = "comparable"
                comp_reason: str | None = None
                if not same_source:
                    comp_status = "not_comparable"
                    comp_reason = "Different data sources used."
                elif cap_a or cap_b:
                    comp_status = "partly_comparable"
                    comp_reason = "Provider result cap reached on one or both sides; counts represent lower bounds."

                # Nearest Distance Row
                diff_dist = None
                if nearest_a is not None and nearest_b is not None:
                    if abs(nearest_a - nearest_b) >= 200:
                        if nearest_a < nearest_b:
                            diff_dist = f"{loc_a_name} has a facility within {nearest_a}m; {loc_b_name}'s nearest listed is {nearest_b}m."
                        else:
                            diff_dist = f"{loc_b_name} has a facility within {nearest_b}m; {loc_a_name}'s nearest listed is {nearest_a}m."
                        key_differences.append(diff_dist)
                    else:
                        diff_dist = f"Similar proximity: {nearest_a}m in {loc_a_name} vs {nearest_b}m in {loc_b_name}."
                elif nearest_a is not None and nearest_b is None:
                    diff_dist = f"{loc_a_name} has a facility within {nearest_a}m; no listing found in {loc_b_name} within search radius."
                    key_differences.append(diff_dist)
                elif nearest_a is None and nearest_b is not None:
                    diff_dist = f"{loc_b_name} has a facility within {nearest_b}m; no listing found in {loc_a_name} within search radius."
                    key_differences.append(diff_dist)
                else:
                    diff_dist = "No listings found in either locality within search radius."

                rows.append(ComparisonRow(
                    category=prio,
                    priority=prio,
                    metric="nearest_distance_m",
                    label=f"{cat_labels[prio]} (Nearest Distance)",
                    val_a=nearest_a,
                    val_b=nearest_b,
                    unit="meters",
                    comparability=comp_status,
                    comparability_reason=comp_reason,
                    difference_statement=diff_dist,
                    source_a=source_a_name,
                    source_b=source_b_name,
                    caveat=osm_caveat
                ))

                # Count within radius row
                diff_count = None
                val_a_display = f"≥ {count_a}" if cap_a else count_a
                val_b_display = f"≥ {count_b}" if cap_b else count_b

                if cap_a and cap_b:
                    diff_count = "Both localities reached the provider result limit; compare nearest facility distances instead."
                elif cap_a and not cap_b and count_a >= count_b:
                    diff_count = f"{loc_a_name} reached provider limit (≥ {count_a} listings) while {loc_b_name} has {count_b} listings."
                elif cap_b and not cap_a and count_b >= count_a:
                    diff_count = f"{loc_b_name} reached provider limit (≥ {count_b} listings) while {loc_a_name} has {count_a} listings."
                elif count_a != count_b:
                    diff_count = f"{count_a} listings identified in {loc_a_name} vs {count_b} in {loc_b_name}."

                radius_km_str = f"{radius_m / 1000:g} km" if radius_m >= 1000 else f"{radius_m} m"
                rows.append(ComparisonRow(
                    category=prio,
                    priority=prio,
                    metric="count_within_radius",
                    label=f"{cat_labels[prio]} (Count in {radius_km_str})",
                    val_a=val_a_display,
                    val_b=val_b_display,
                    unit="listings",
                    comparability=comp_status,
                    comparability_reason=comp_reason,
                    difference_statement=diff_count,
                    source_a=source_a_name,
                    source_b=source_b_name,
                    caveat=osm_caveat
                ))

        # 2. Compare Environment (Air Quality)
        env_source_a = env_a.sources[0].name if (env_a and env_a.sources) else "Open-Meteo"
        env_source_b = env_b.sources[0].name if (env_b and env_b.sources) else "Open-Meteo"
        aqi_a = env_a.data.aqi if (env_a and env_a.data) else None
        aqi_b = env_b.data.aqi if (env_b and env_b.data) else None

        env_diff = None
        if aqi_a is not None and aqi_b is not None:
            if abs(aqi_a - aqi_b) >= 10:
                env_diff = f"{loc_a_name} ambient US AQI is {aqi_a}; {loc_b_name} is {aqi_b}."
                key_differences.append(env_diff)
            else:
                env_diff = f"Comparable atmospheric AQI ({aqi_a} in {loc_a_name} vs {aqi_b} in {loc_b_name})."

        rows.append(ComparisonRow(
            category="environment",
            priority="environment",
            metric="aqi",
            label="Ambient Air Quality (US AQI)",
            val_a=aqi_a,
            val_b=aqi_b,
            unit="US AQI",
            comparability="comparable" if (aqi_a and aqi_b) else "partly_comparable",
            comparability_reason="Modeled regional reanalysis estimate (ECMWF CAMS ~40 km grid in India), not site-specific sensors." if (aqi_a or aqi_b) else "Environmental data unavailable",
            difference_statement=env_diff,
            source_a=env_source_a,
            source_b=env_source_b,
            caveat="Modeled estimates represent broad regional grids and do not reflect micro-level building conditions."
        ))

        # 3. Data Gaps and Coverage Differences
        data_gaps.append("Locality-level water quality datasets are unavailable from integrated sources for both areas.")
        data_gaps.append("Locality-level crime incident statistics are unavailable from official sources for both areas.")

        cov_a_count = places_a.coverage.result_count if places_a else 0
        cov_b_count = places_b.coverage.result_count if places_b else 0
        coverage_diffs.append(
            f"Mapped amenity density: {cov_a_count} total POIs in {loc_a_name} vs {cov_b_count} in {loc_b_name}."
        )

        return LocalityComparisonSummary(
            locality_a_name=loc_a_name,
            locality_b_name=loc_b_name,
            radius_m=radius_m,
            key_differences=key_differences,
            data_gaps=data_gaps,
            coverage_differences=coverage_diffs,
            rows=rows
        )
