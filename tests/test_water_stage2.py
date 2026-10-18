import unittest
import asyncio
import os
import json
from datetime import datetime
from backend.app.providers.environment import TelanganaWaterQualityProvider, DefaultWaterQualityProvider
from backend.app.schemas.modules import WaterQualityData
from backend.app.evidence.builder import EvidenceBuilder
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage


class TestTelanganaWaterQualityStage2(unittest.TestCase):
    def setUp(self):
        self.provider = TelanganaWaterQualityProvider()

    def test_official_dataset_structure_and_completeness(self):
        """Verify the compiled official dataset contains all 33 districts and metadata."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        water_json_path = os.path.join(base_dir, "backend", "data", "telangana_water_resources.json")
        geojson_path = os.path.join(base_dir, "backend", "data", "telangana_districts.geojson")

        self.assertTrue(os.path.exists(water_json_path), "telangana_water_resources.json must exist")
        self.assertTrue(os.path.exists(geojson_path), "telangana_districts.geojson must exist")

        with open(water_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        self.assertEqual(meta.get("title"), "Dynamic Ground Water Resources of Telangana State")
        self.assertIn("CGWB", meta.get("publisher", ""))
        self.assertIn("GEC-2015", meta.get("methodology", ""))
        self.assertIn("cgwb.gov.in", meta.get("official_url", ""))
        self.assertIn("mandatory_limitation", meta)

        districts = data.get("districts", {})
        self.assertEqual(len(districts), 33, "Dataset must cover all 33 districts of Telangana")

        for dname, dinfo in districts.items():
            self.assertIn("soe_pct", dinfo, f"{dname} missing soe_pct")
            self.assertIn("extractable_ham", dinfo, f"{dname} missing extractable_ham")
            self.assertIn("annual_extraction_ham", dinfo, f"{dname} missing annual_extraction_ham")
            self.assertIn("category", dinfo, f"{dname} missing category")
            self.assertIn("water_table_pre_mbgl", dinfo, f"{dname} missing water_table_pre_mbgl")
            self.assertIn("water_table_post_mbgl", dinfo, f"{dname} missing water_table_post_mbgl")
            self.assertIn("seasonal_rise_m", dinfo, f"{dname} missing seasonal_rise_m")
            self.assertIn("mandals", dinfo, f"{dname} missing mandals breakdown")
            self.assertGreater(dinfo["soe_pct"], 0)
            self.assertGreater(dinfo["extractable_ham"], 0)

        # Check OCS mandals registry
        ocs = data.get("ocs_mandals", {})
        self.assertGreaterEqual(len(ocs), 70, "Must contain all OCS mandals from Annexure IV")
        self.assertIn("khairatabad", ocs)
        self.assertEqual(ocs["khairatabad"]["category"], "Over-Exploited")
        self.assertIn("serilingampally", ocs)
        self.assertEqual(ocs["serilingampally"]["category"], "Critical")
        self.assertIn("kukatpally", ocs)
        self.assertEqual(ocs["kukatpally"]["category"], "Semi-Critical")

    def test_district_spatial_lookup_correctness(self):
        """Verify coordinates in major Telangana centers resolve to the exact district."""
        test_points = [
            ("Hyderabad", 17.3616, 78.4747, "Hyderabad"),
            ("Gachibowli", 17.4401, 78.3489, "Ranga Reddy"),
            ("Kukatpally", 17.4933, 78.3995, "Medchal Malkajgiri"),
            ("Warangal Center", 17.9689, 79.5941, "Hanumakonda"),
            ("Karimnagar", 18.4386, 79.1288, "Karimnagar"),
            ("Nizamabad", 18.6725, 78.0941, "Nizamabad"),
            ("Adilabad", 19.6641, 78.5320, "Adilabad"),
            ("Khammam", 17.2473, 80.1514, "Khammam")
        ]

        for name, lat, lng, expected_district in test_points:
            res = asyncio.run(self.provider.get_water_quality(lat, lng))
            self.assertEqual(res.status, "available", f"Failed for {name}")
            self.assertIsNotNone(res.data, f"Data null for {name}")
            self.assertEqual(res.data.district_name, expected_district, f"Expected {expected_district} for {name}")
            self.assertIsNotNone(res.data.stage_of_extraction_pct)
            self.assertIsNotNone(res.data.water_table_pre_monsoon_mbgl)
            self.assertIsNotNone(res.data.water_table_post_monsoon_mbgl)

    def test_mandal_resolution_and_no_false_averaging(self):
        """Verify mandal-level categorizations are reported without guessing or averaging."""
        # 1. When locality identifies an OCS mandal (Serilingampally in Ranga Reddy)
        res_mandal = asyncio.run(self.provider.get_water_quality(17.4401, 78.3489, locality="Serilingampally"))
        self.assertEqual(res_mandal.status, "available")
        self.assertEqual(res_mandal.data.data_level, "mandal")
        self.assertEqual(res_mandal.data.mandal_name, "Serilingampally")
        self.assertEqual(res_mandal.data.assessment_category, "Critical")
        # CRITICAL INTEGRITY CHECK: Mandal-specific % must be None, district % must be 60.21
        self.assertIsNone(res_mandal.data.stage_of_extraction_pct, "Mandal numeric extraction % must not be conflated with district average")
        self.assertEqual(res_mandal.data.district_stage_of_extraction_pct, 60.21)

        # 2. When locality identifies an Over-Exploited mandal (Khairatabad in Hyderabad)
        res_khairatabad = asyncio.run(self.provider.get_water_quality(17.4123, 78.4567, locality="Khairatabad, Hyderabad"))
        self.assertEqual(res_khairatabad.status, "available")
        self.assertEqual(res_khairatabad.data.data_level, "mandal")
        self.assertEqual(res_khairatabad.data.assessment_category, "Over-Exploited")
        self.assertIsNone(res_khairatabad.data.stage_of_extraction_pct)
        self.assertEqual(res_khairatabad.data.district_stage_of_extraction_pct, 95.99)

        # 3. When locality is generic / unknown, reports district level and does NOT infer mandal
        res_generic = asyncio.run(self.provider.get_water_quality(17.4401, 78.3489, locality=None))
        self.assertEqual(res_generic.status, "available")
        self.assertEqual(res_generic.data.data_level, "district")
        self.assertIsNone(res_generic.data.mandal_name)
        self.assertEqual(res_generic.data.district_name, "Ranga Reddy")
        self.assertEqual(res_generic.data.stage_of_extraction_pct, 60.21)
        # District summary contains distribution of mandals
        self.assertIn("District (", res_generic.data.mandals_summary)

    def test_serilingampally_mandal_integrity_audit(self):
        """Stage 2.1 Audit: Verify Serilingampally never reports Ranga Reddy's 60.21% as its own percentage."""
        res = asyncio.run(self.provider.get_water_quality(17.4401, 78.3489, locality="Serilingampally"))
        self.assertEqual(res.status, "available")
        self.assertEqual(res.data.mandal_name, "Serilingampally")
        self.assertEqual(res.data.assessment_category, "Critical")
        self.assertIsNone(res.data.stage_of_extraction_pct, "Serilingampally must NOT present district 60.21% as mandal %")
        self.assertEqual(res.data.district_stage_of_extraction_pct, 60.21, "District aggregate must be explicitly separated")
        self.assertEqual(res.data.district_code, "537")
        self.assertTrue(any("parent Ranga Reddy district aggregate is 60.21%" in lim for lim in res.limitations))

    def test_cross_district_mandal_collision_prevention(self):
        """Stage 2.1 Audit: Verify mandal names from other districts cannot be falsely matched across borders."""
        # Dammapeta is a Critical mandal in Bhadradri Kothagudem.
        # Querying with Hyderabad coordinates (17.3850, 78.4867) must NOT attach Dammapeta to Hyderabad.
        res = asyncio.run(self.provider.get_water_quality(17.3850, 78.4867, locality="Dammapeta"))
        self.assertEqual(res.status, "available")
        self.assertEqual(res.data.district_name, "Hyderabad")
        self.assertEqual(res.data.data_level, "district", "Should fall back to district level on cross-district mismatch")
        self.assertIsNone(res.data.mandal_name)

    def test_historical_baseline_labels_and_metadata(self):
        """Stage 2.1 Audit: Verify dataset is labeled as historical baseline with reporting year and source."""
        res = asyncio.run(self.provider.get_water_quality(17.3850, 78.4867))
        self.assertTrue(res.data.is_historical_baseline)
        self.assertIn("2022", res.data.reporting_year)
        self.assertIn("CGWB & TGWD", res.data.dataset_publication)
        self.assertIsNotNone(res.data.geographic_resolution)
        self.assertEqual(res.data.district_code, "536")

    def test_distinction_sustainability_vs_chemistry_vs_potability(self):
        """Stage 2.1 Audit: Verify 3-part distinction between sustainability, ambient chemistry, and tap potability."""
        res = asyncio.run(self.provider.get_water_quality(17.3850, 78.4867))
        lims_text = " ".join(res.limitations)
        # 1. Sustainability vs potability
        self.assertIn("evaluate regional aquifer recharge vs extraction balances and do NOT certify drinking-water potability", lims_text)
        # 2. Ambient monitoring chemistry vs tap supply
        self.assertIn("Regional groundwater chemistry (TDS and pH) reflects ambient monitoring well baselines from CGWB network, not municipal tap supply", lims_text)
        # 3. Building-level on-site testing requirement
        self.assertIn("Building-level tap-water quality, Krishna/Godavari municipal piped supply schedules, TDS, hardness, pH, and private borewell depth require on-site testing", lims_text)

    def test_outside_telangana_unknown_locations(self):
        """Verify locations outside Telangana return honest unavailable state."""
        out_of_state_points = [
            ("Bengaluru", 12.9716, 77.5946),
            ("Mumbai", 19.0760, 72.8777),
            ("Delhi", 28.6139, 77.2090),
            ("Chennai", 13.0827, 80.2707)
        ]

        for name, lat, lng in out_of_state_points:
            res = asyncio.run(self.provider.get_water_quality(lat, lng))
            self.assertEqual(res.status, "unavailable", f"Should be unavailable for {name}")
            self.assertIsNone(res.data, f"Data should be None for {name}")
            self.assertIn("outside telangana", res.message.lower())
            self.assertTrue(any("outside Telangana" in lim for lim in res.limitations))

    def test_mandatory_limitations_and_disclosures(self):
        """Verify strict adherence to potability caveats and non-endorsement."""
        res = asyncio.run(self.provider.get_water_quality(17.3850, 78.4867))
        self.assertEqual(res.status, "available")

        # Must explicitly warn that Safe category does NOT certify drinking water
        lims = " ".join(res.limitations)
        self.assertIn("do NOT certify drinking", lims)
        self.assertIn("Never claim or assume groundwater is safe to drink", lims)
        self.assertIn("on-site testing", lims)

        # Schema disclaimer field must also carry this disclosure
        self.assertIsNotNone(res.data.disclaimer)
        self.assertIn("DO NOT certify drinking-water potability", res.data.disclaimer)

        # Source attribution
        self.assertEqual(len(res.sources), 1)
        source = res.sources[0]
        self.assertIn("Central Ground Water Board", source.name)
        self.assertIn("Ground Water Department", source.name)
        self.assertIn("cgwb.gov.in", source.url)

    def test_evidence_builder_integration(self):
        """Verify EvidenceBuilder creates items for water resources while keeping the potability gap."""
        res = asyncio.run(self.provider.get_water_quality(17.3850, 78.4867))
        items, gaps = EvidenceBuilder.build_evidence(
            locality_key="test_loc",
            water_res=res
        )

        water_items = [it for it in items if it.module == "water"]
        self.assertGreaterEqual(len(water_items), 2)
        metrics = {it.metric: it.value for it in water_items}
        self.assertIn("district_stage_of_extraction_pct", metrics)
        self.assertIn("assessment_category", metrics)

        # Potability gap must still be registered
        water_gaps = [g for g in gaps if g.module == "water"]
        self.assertEqual(len(water_gaps), 1)
        self.assertIn("do not certify building-level tap drinking water quality", water_gaps[0].reason)

    def test_pdf_report_generation_with_water(self):
        """Stage 2.1 Audit: Verify PDF report generates cleanly with water data."""
        from backend.app.reports.pdf_generator import generate_report_pdf
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            res = asyncio.run(self.provider.get_water_quality(17.4401, 78.3489, locality="Serilingampally"))
            water_dict = res.data.model_dump()

            pdf_out = generate_report_pdf(
                output_path=tmp_path,
                report_id="test-water-pdf-report",
                locality_name="Serilingampally, Hyderabad",
                verification_hash="abc123hash",
                verification_url="http://localhost:8000/verify/test-water-pdf-report",
                findings=[{"headline": "Mandal groundwater stressed", "detail": "Classified as Critical under CGWB"}],
                amenity_rows=[],
                env_data={"aqi": 85, "pm25": 28.5, "pm10": 55.0},
                water_data=water_dict
            )
            self.assertTrue(os.path.exists(pdf_out))
            self.assertGreater(os.path.getsize(pdf_out), 1000)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
