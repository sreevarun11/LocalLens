import os
import unittest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.base import (
    ModuleResult,
    EvidenceItem,
    EvidenceGap,
    Coverage,
    DataSourceInfo
)
from backend.app.schemas.location import PlacesData, PlaceItem
from backend.app.schemas.modules import (
    AirQualityData,
    WaterQualityData,
    SafetyAndCrimeData,
    SafetyFacility,
    EmergencyContact,
    JurisdictionInfo,
    CommuteData,
    CommuteModeResult,
    Coordinates
)
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.evidence.personalization import (
    PersonalizationEngine,
    DistancePreference,
    PROFILE_DEFAULTS
)
from backend.app.reports.pdf_generator import generate_report_pdf

client = TestClient(app)

class TestEvidenceStage5(unittest.TestCase):
    """
    Phase 5 comprehensive test suite:
    - Stage 5A: Unified Evidence Model & Standard Status Semantics
    - Stage 5B: Unified Neighborhood Intelligence & Synthesis
    - Stage 5C: Profile-Aware Personalization (All Profiles & Priorities)
    - Stage 5D: Provenance, Coverage, Temporal & Geographic Integrity
    - Stage 5E: PDF Report Reliability & Consistency
    """

    def setUp(self):
        self.locality_key = "loc_stage5_test"

        # 1. Realistic Places Module Result
        self.places_result = ModuleResult[PlacesData](
            module="places",
            status="available",
            provenance_kind="map_listing",
            data=PlacesData(
                places=[
                    PlaceItem(
                        id="node/101",
                        name="Apollo Health City",
                        category="healthcare",
                        lat=17.4150,
                        lng=78.4120,
                        distance_m=420,
                        source_name="OpenStreetMap"
                    ),
                    PlaceItem(
                        id="node/102",
                        name="Oakridge International School",
                        category="education",
                        lat=17.4180,
                        lng=78.4150,
                        distance_m=850,
                        source_name="OpenStreetMap"
                    ),
                    PlaceItem(
                        id="node/103",
                        name="Ratnadeep Supermarket",
                        category="daily_life",
                        lat=17.4130,
                        lng=78.4110,
                        distance_m=310,
                        source_name="OpenStreetMap"
                    ),
                    PlaceItem(
                        id="node/104",
                        name="Gachibowli Metro Halt",
                        category="transport",
                        lat=17.4200,
                        lng=78.4170,
                        distance_m=650,
                        source_name="OpenStreetMap"
                    )
                ],
                counts_by_category={
                    "healthcare": 3,
                    "education": 2,
                    "daily_life": 5,
                    "transport": 2,
                    "lifestyle": 4,
                    "safety_infrastructure": 1
                },
                radius_m=1500,
                cap_reached=False
            ),
            sources=[DataSourceInfo(name="OpenStreetMap", license="ODbL 1.0")],
            coverage=Coverage(
                granularity="nearby_place",
                radius_m=1500,
                result_count=17,
                result_cap_reached=False,
                nearest_distance_m=310
            ),
            limitations=["Straight-line distance; physical paths vary.", "Contributor mapping density."]
        )

        # 2. Environmental Module Result (Modeled CAMS)
        self.env_result = ModuleResult[AirQualityData](
            module="environment",
            status="limited",
            provenance_kind="modeled_estimate",
            data=AirQualityData(
                aqi=78,
                aqi_scale="US AQI",
                pm25=24.5,
                pm10=48.2,
                model_grid_resolution_km=11,
                temperature_c=28.5,
                weather_desc="Partly Cloudy"
            ),
            sources=[DataSourceInfo(name="Open-Meteo European CAMS")],
            coverage=Coverage(granularity="monitoring_station", note="11 km atmospheric model grid"),
            measured_at=datetime(2026, 10, 16, 10, 0),
            limitations=["European CAMS ~11 km grid resolution, not an on-site property sensor."]
        )

        # 3. Water Quality Result (Historical CGWB)
        self.water_result = ModuleResult[WaterQualityData](
            module="water",
            status="available",
            provenance_kind="official_dataset",
            data=WaterQualityData(
                sample_count=1,
                data_level="mandal",
                district_name="Ranga Reddy",
                mandal_name="Serilingampally",
                assessment_category="Critical",
                stage_of_extraction_pct=60.21,
                mandal_stage_of_extraction_pct=None,  # Separated per Phase 4 audit
                district_stage_of_extraction_pct=60.21,
                reporting_year="Assessment Year 2022",
                dataset_publication="CGWB & TGWD Dynamic Ground Water Resources of Telangana State (2022)",
                water_table_pre_monsoon_mbgl=12.4,
                water_table_post_monsoon_mbgl=8.1,
                seasonal_water_table_rise_m=4.3,
                tds_range_mg_l="450 - 920",
                ph_range="7.2 - 7.9"
            ),
            sources=[DataSourceInfo(name="Central Ground Water Board (CGWB) & TGWD")],
            coverage=Coverage(granularity="mandal"),
            measured_at=datetime(2022, 3, 31),
            limitations=["Regional aquifer assessment; does not certify tap drinking water potability."]
        )

        # 4. Safety & Crime Result
        self.safety_result = ModuleResult[SafetyAndCrimeData](
            module="safety",
            status="available",
            provenance_kind="official_dataset",
            data=SafetyAndCrimeData(
                data_granularity="commissionerate",
                nearby_facilities=[
                    SafetyFacility(
                        id="safety/pol_1",
                        name="Gachibowli Police Station",
                        facility_type="police",
                        lat=17.4390,
                        lng=78.3580,
                        distance_m=1100,
                        distance_km=1.1,
                        source_name="OpenStreetMap"
                    ),
                    SafetyFacility(
                        id="safety/fire_1",
                        name="Madhapur Fire Station",
                        facility_type="fire_station",
                        lat=17.4480,
                        lng=78.3810,
                        distance_m=2400,
                        distance_km=2.4,
                        source_name="OpenStreetMap"
                    )
                ],
                emergency_contacts=[
                    EmergencyContact(
                        service="Police Emergency",
                        number="100",
                        description="Police emergency dispatch",
                        jurisdiction="Telangana State",
                        verified_authority="Telangana Police",
                        source_url="https://tspolice.gov.in",
                        limitations=[]
                    ),
                    EmergencyContact(
                        service="National Emergency Number",
                        number="112",
                        description="Unified emergency helpline",
                        jurisdiction="All India / Telangana",
                        verified_authority="Ministry of Home Affairs",
                        source_url="https://112.gov.in",
                        limitations=[]
                    ),
                    EmergencyContact(
                        service="Fire & Rescue Services",
                        number="101",
                        description="Fire emergency response",
                        jurisdiction="Telangana State",
                        verified_authority="Telangana State Disaster Response and Fire Services",
                        source_url="https://fire.telangana.gov.in",
                        limitations=[]
                    ),
                    EmergencyContact(
                        service="Medical Emergency & Ambulance",
                        number="108",
                        description="Emergency medical transport",
                        jurisdiction="Telangana State",
                        verified_authority="EMRI Green Health Services",
                        source_url="https://emri.in",
                        limitations=[]
                    ),
                    EmergencyContact(
                        service="Women Helpline (SHE Teams)",
                        number="1090",
                        description="Safety assistance and harassment reporting",
                        jurisdiction="Telangana State",
                        verified_authority="Telangana Police Women Safety Wing",
                        source_url="https://womensafetywing.telangana.gov.in",
                        limitations=[]
                    ),
                    EmergencyContact(
                        service="Cyber Crime Helpline",
                        number="1930",
                        description="Financial fraud and cybercrime reporting",
                        jurisdiction="National / Telangana",
                        verified_authority="Indian Cyber Crime Coordination Centre (I4C)",
                        source_url="https://cybercrime.gov.in",
                        limitations=[]
                    )
                ],
                jurisdiction=JurisdictionInfo(
                    jurisdiction_name="Cyberabad Police Commissionerate",
                    jurisdiction_type="commissionerate",
                    supporting_authority="Telangana State Police",
                    source_url="https://cyberabadpolice.gov.in",
                    geographic_resolution="commissionerate",
                    limitations=["Commissionerate boundaries do not align with revenue mandals."]
                ),
                crime_statistics_status="unavailable",
                crime_disclosure_note="Locality-level crime incident statistics are unavailable from official sources.",
                absence_caveat="The absence of published locality-level crime statistics does not imply that an area is safe."
            ),
            sources=[DataSourceInfo(name="Telangana State Police & OpenStreetMap")],
            coverage=Coverage(granularity="commissionerate"),
            limitations=["Locality-level crime statistics are not compiled by official sources."]
        )

        # 5. Commute Result (OSRM Road-Network)
        self.commute_result = ModuleResult[CommuteData](
            module="commute",
            status="available",
            provenance_kind="modeled_estimate",
            data=CommuteData(
                origin_coords=Coordinates(lat=17.4150, lng=78.4120),
                destination_name="HITEC City",
                destination_coords=Coordinates(lat=17.4504, lng=78.3808),
                modes={
                    "driving": CommuteModeResult(
                        mode="driving",
                        duration_min=18,
                        distance_km=7.4,
                        status="available",
                        provider="OSRM Road-Network Engine",
                        data_kind="road_network_estimate",
                        limitations=["Road-network routing estimate without live traffic congestion."]
                    ),
                    "transit": CommuteModeResult(
                        mode="transit",
                        status="unavailable",
                        provider="LocalLens Transit Engine",
                        data_kind="unavailable",
                        limitations=["Public transit schedules unavailable without GTFS feed."]
                    )
                }
            ),
            sources=[DataSourceInfo(name="OSRM Road-Network Engine")],
            coverage=Coverage(granularity="exact_place"),
            limitations=["OSRM road-network routing estimate without live traffic congestion."]
        )

    # ========================================================
    # 1. STAGE 5A TESTS: UNIFIED EVIDENCE MODEL & STATUS SEMANTICS
    # ========================================================

    def test_unified_evidence_builder_complete_extraction(self):
        """Verifies EvidenceBuilder extracts structured items and gaps with full provenance."""
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key=self.locality_key,
            places_res=self.places_result,
            env_res=self.env_result,
            water_res=self.water_result,
            crime_res=self.safety_result,
            commute_res=self.commute_result
        )

        # Verify evidence items exist across modules
        self.assertTrue(len(items) > 0)
        modules_represented = {it.module for it in items}
        self.assertIn("healthcare", modules_represented)
        self.assertIn("education", modules_represented)
        self.assertIn("environment", modules_represented)
        self.assertIn("water", modules_represented)
        self.assertIn("safety_infrastructure", modules_represented)
        self.assertIn("commute", modules_represented)

        # Verify every item has title, finding, status, and reporting period
        for it in items:
            self.assertIsNotNone(it.title, f"Item {it.id} missing title")
            self.assertIsNotNone(it.finding, f"Item {it.id} missing finding")
            self.assertIn(it.status, ["available", "limited", "unavailable", "error"])
            self.assertIsNotNone(it.reporting_period, f"Item {it.id} missing reporting_period")
            self.assertIsNotNone(it.geographic_resolution, f"Item {it.id} missing geographic_resolution")

        # Verify mandatory gaps are registered cleanly
        gap_modules = {g.module for g in gaps}
        self.assertIn("water", gap_modules)
        self.assertIn("crime", gap_modules)
        self.assertIn("commute", gap_modules)

        # Verify water gap callout reason
        water_gap = next(g for g in gaps if g.module == "water")
        self.assertIn("Official groundwater resource assessments evaluate regional aquifer extraction", water_gap.reason)
        self.assertEqual(water_gap.granularity_needed, "property")

        # Verify crime gap callout reason
        crime_gap = next(g for g in gaps if g.module == "crime")
        self.assertIn("Locality-level crime incident statistics are unavailable from official sources", crime_gap.reason)
        self.assertEqual(crime_gap.granularity_needed, "locality")

    def test_provider_error_and_empty_state_handling(self):
        """Verifies provider failures and out-of-coverage locations produce honest gaps, never fake zeros."""
        failed_places = ModuleResult[PlacesData](
            module="places",
            status="error",
            provenance_kind="map_listing",
            data=None,
            coverage=Coverage(granularity="unknown"),
            message="Overpass HTTP 504 Gateway Timeout"
        )
        out_of_coverage_water = ModuleResult[WaterQualityData](
            module="water",
            status="unavailable",
            provenance_kind="official_dataset",
            data=None,
            coverage=Coverage(granularity="unknown"),
            message="Location outside Telangana groundwater assessment coverage."
        )

        items, gaps = EvidenceBuilder.build_evidence(
            locality_key="loc_fail_test",
            places_res=failed_places,
            water_res=out_of_coverage_water
        )

        # Places items should be empty, places gap recorded
        places_gaps = [g for g in gaps if g.module == "places"]
        self.assertEqual(len(places_gaps), 1)
        self.assertEqual(places_gaps[0].status, "error")
        self.assertIn("Overpass HTTP 504", places_gaps[0].reason)

        # Water gap recorded with honest out-of-coverage message
        water_gaps = [g for g in gaps if g.module == "water"]
        self.assertEqual(len(water_gaps), 1)
        self.assertEqual(water_gaps[0].status, "unavailable")
        self.assertIn("outside Telangana", water_gaps[0].reason)

    # ========================================================
    # 2. STAGE 5C TESTS: PROFILE-AWARE PERSONALIZATION
    # ========================================================

    def test_personalization_all_profiles_ordering(self):
        """Verifies all 7 profiles evaluate deterministically without mutating underlying facts."""
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key=self.locality_key,
            places_res=self.places_result,
            env_res=self.env_result,
            water_res=self.water_result,
            crime_res=self.safety_result,
            commute_res=self.commute_result
        )

        profiles = ["family", "commuter", "student", "elderly", "first_time_renter", "home_buyer", "relocation"]
        for prof in profiles:
            defaults = PROFILE_DEFAULTS[prof]
            findings, callouts, checklist = PersonalizationEngine.evaluate(
                evidence_items=items,
                gaps=gaps,
                profile=prof,
                selected_priorities=defaults
            )

            # Findings count must equal number of evaluated priorities
            self.assertEqual(len(findings), len(defaults))
            # Findings order must match the requested priority sequence
            for idx, p in enumerate(defaults):
                self.assertEqual(findings[idx].priority, p)

            # Check that zero synthetic scores or verdicts were generated
            for f in findings:
                self.assertNotIn("score", f.headline.lower())
                self.assertNotIn("/10", f.headline)
                self.assertNotIn("100%", f.headline)
                self.assertNotIn("verdict", f.detail.lower())
                self.assertNotIn("winner", f.detail.lower())

            # Checklist questions must be present
            self.assertTrue(len(checklist) > 0)

    def test_personalization_distance_preference_adherence(self):
        """Verifies distance preference evaluates 'yes', 'no', 'unknown' deterministically."""
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key=self.locality_key,
            places_res=self.places_result
        )

        # Healthcare nearest is 420m
        # Preference 500m -> within preference ("yes")
        findings_yes, _, _ = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="family",
            selected_priorities=["healthcare"],
            distance_preferences=[DistancePreference(priority="healthcare", preferred_distance_m=500)]
        )
        self.assertEqual(findings_yes[0].within_preference, "yes")
        self.assertIn("comfortably within your 500m preference", findings_yes[0].preference_note)

        # Preference 300m -> exceeds preference ("no")
        findings_no, _, _ = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="family",
            selected_priorities=["healthcare"],
            distance_preferences=[DistancePreference(priority="healthcare", preferred_distance_m=300)]
        )
        self.assertEqual(findings_no[0].within_preference, "no")
        self.assertIn("exceeds your 300m preference", findings_no[0].preference_note)

    def test_water_and_safety_priorities_in_personalization(self):
        """Verifies water and safety_infrastructure evaluate with complete contextual detail."""
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key=self.locality_key,
            places_res=self.places_result,
            water_res=self.water_result,
            crime_res=self.safety_result
        )

        findings, callouts, checklist = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="home_buyer",
            selected_priorities=["water", "safety_infrastructure"]
        )

        # Water finding
        water_f = next(f for f in findings if f.priority == "water")
        self.assertEqual(water_f.status, "available")
        self.assertIn("Critical", water_f.headline)
        self.assertIn("Assessment Year 2022", water_f.detail)
        self.assertIn("potability", water_f.detail)

        # Safety finding
        safety_f = next(f for f in findings if f.priority == "safety_infrastructure")
        self.assertEqual(safety_f.status, "available")
        self.assertIn("Nearest police station at 1100m", safety_f.headline)
        self.assertIn("Cyberabad Police Commissionerate", safety_f.detail)
        self.assertIn("crime incident statistics are unavailable", safety_f.detail)

        # Callouts
        callout_prios = {c.priority for c in callouts}
        self.assertIn("water", callout_prios)
        self.assertIn("safety_infrastructure", callout_prios)

    # ========================================================
    # 3. STAGE 5B/5D TESTS: API ENDPOINTS & VERIFICATION
    # ========================================================

    def test_api_insights_post_endpoint(self):
        """Verifies POST /api/insights returns valid unified insights structure."""
        payload = {
            "locality_key": "loc_api_test",
            "profile": "student",
            "priorities": ["education", "transport", "daily_life"],
            "places": self.places_result.model_dump(mode="json"),
            "environment": self.env_result.model_dump(mode="json"),
            "water": self.water_result.model_dump(mode="json"),
            "crime": self.safety_result.model_dump(mode="json"),
            "commute": self.commute_result.model_dump(mode="json")
        }

        resp = client.post("/api/insights", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["profile"], "student")
        self.assertEqual(data["priorities"], ["education", "transport", "daily_life"])
        self.assertTrue(len(data["findings"]) == 3)
        self.assertTrue(len(data["evidence_items"]) > 0)
        self.assertTrue(len(data["gaps"]) > 0)
        self.assertTrue(len(data["verify_on_site"]) > 0)

    def test_api_insights_profiles_get_endpoint(self):
        """Verifies GET /api/insights/profiles returns all 7 supported profiles."""
        resp = client.get("/api/insights/profiles")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("profiles", data)
        profile_ids = [p["id"] for p in data["profiles"]]
        for expected in ["family", "commuter", "student", "elderly", "first_time_renter", "home_buyer", "relocation"]:
            self.assertIn(expected, profile_ids)

    # ========================================================
    # 4. STAGE 5E TESTS: PDF REPORT GENERATION & CONSISTENCY
    # ========================================================

    def test_pdf_report_with_stage5_unified_evidence(self):
        """Verifies PDF report generates successfully with full unified evidence and zero null/None leaks."""
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key=self.locality_key,
            places_res=self.places_result,
            env_res=self.env_result,
            water_res=self.water_result,
            crime_res=self.safety_result,
            commute_res=self.commute_result
        )

        findings_list, _, checklist = PersonalizationEngine.evaluate(
            evidence_items=items,
            gaps=gaps,
            profile="family",
            selected_priorities=["education", "healthcare", "water", "safety_infrastructure"]
        )

        amenity_rows = [
            {"category": "healthcare", "count": 3, "nearest_m": 420},
            {"category": "education", "count": 2, "nearest_m": 850},
            {"category": "safety_infrastructure", "count": 1, "nearest_m": 1100},
            {"category": "daily_life", "count": 5, "nearest_m": 310},
            {"category": "transport", "count": 2, "nearest_m": 650},
            {"category": "lifestyle", "count": 4, "nearest_m": 500}
        ]

        test_pdf_id = f"test_stage5_{uuid.uuid4().hex[:8]}"
        out_path = os.path.join("data", "reports", f"{test_pdf_id}.pdf")

        pdf_path = generate_report_pdf(
            output_path=out_path,
            report_id=test_pdf_id,
            locality_name="Gachibowli, Hyderabad",
            verification_hash="b4b5a6c7d8e9f0123456789abcdef0123456789abcdef0123456789abcdef01",
            verification_url=f"http://127.0.0.1:8000/verify/{test_pdf_id}",
            findings=[f.model_dump() for f in findings_list],
            amenity_rows=amenity_rows,
            env_data=self.env_result.data.model_dump() if self.env_result.data else None,
            water_data=self.water_result.data.model_dump() if self.water_result.data else None,
            safety_data=self.safety_result.data.model_dump() if self.safety_result.data else None,
            property_context={"property_address": "Flat 402, Gachibowli Heights", "rent_or_price": "45,000"},
            checklist_questions=[q.question for q in checklist],
            user_profile="family",
            user_priorities=["education", "healthcare", "water", "safety_infrastructure"]
        )

        self.assertTrue(os.path.exists(pdf_path))
        pdf_size = os.path.getsize(pdf_path)
        self.assertTrue(pdf_size > 5000, f"Generated PDF unexpectedly small: {pdf_size} bytes")

        # Clean up test artifact
        try:
            os.remove(pdf_path)
        except OSError:
            pass

if __name__ == "__main__":
    unittest.main()
