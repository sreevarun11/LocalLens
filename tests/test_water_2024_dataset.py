import json
import math
import os
import unittest
from pathlib import Path

import pypdf

from scripts.extract_telangana_water_2024 import (
    CANONICAL_DISTRICTS,
    extract_annexure_2,
    extract_annexure_3a,
    extract_annexure_3b,
    extract_annexure_6,
    normalize_name,
    validate_and_merge_data,
)


class TestWater2024Dataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = Path(__file__).resolve().parent.parent
        cls.data_2024_path = cls.base_dir / "backend" / "data" / "telangana_water_resources_2024.json"
        cls.data_2022_path = cls.base_dir / "backend" / "data" / "telangana_water_resources.json"
        cls.pdf_path = cls.base_dir / "backend" / "data" / "tmp" / "gwra_telangana_2024.pdf"

        with open(cls.data_2024_path, "r", encoding="utf-8") as f:
            cls.data_2024 = json.load(f)

        with open(cls.data_2022_path, "r", encoding="utf-8") as f:
            cls.data_2022 = json.load(f)

    def test_dataset_file_and_metadata(self):
        """Verify the 2024 dataset file exists and has rigorous metadata."""
        self.assertTrue(self.data_2024_path.exists())
        meta = self.data_2024.get("metadata", {})

        self.assertEqual(meta.get("title"), "Dynamic Ground Water Resources of Telangana State, 2024")
        self.assertIn("CGWB", meta.get("publisher", ""))
        self.assertIn("Ground Water Department, Government of Telangana", meta.get("publisher", ""))
        self.assertEqual(meta.get("epoch"), "2024")
        self.assertIn("Assessment Year 2024", meta.get("reporting_period", ""))
        self.assertIn("GEC-2015", meta.get("methodology", ""))
        self.assertIn("https://cgwb.gov.in", meta.get("official_url", ""))
        self.assertIn("mandatory_limitation", meta)
        self.assertIn("do not certify drinking-water potability", meta["mandatory_limitation"].lower())

    def test_state_summary_integrity(self):
        """Verify official state-level groundwater totals from 2024 report."""
        summary = self.data_2024.get("state_summary", {})

        self.assertEqual(summary.get("total_annual_recharge_bcm"), 20.4)
        self.assertEqual(summary.get("annual_extractable_resources_bcm"), 18.44)
        self.assertEqual(summary.get("total_annual_extraction_bcm"), 8.47)
        self.assertEqual(summary.get("overall_stage_of_extraction_pct"), 45.91)
        self.assertEqual(summary.get("total_assessment_mandals"), 620)
        self.assertEqual(summary.get("safe_mandals"), 490)
        self.assertEqual(summary.get("semi_critical_mandals"), 85)
        self.assertEqual(summary.get("critical_mandals"), 13)
        self.assertEqual(summary.get("over_exploited_mandals"), 32)
        self.assertEqual(summary.get("saline_mandals"), 0)

        # Check total sums match
        cat_sum = (
            summary["safe_mandals"]
            + summary["semi_critical_mandals"]
            + summary["critical_mandals"]
            + summary["over_exploited_mandals"]
            + summary["saline_mandals"]
        )
        self.assertEqual(cat_sum, 620)

    def test_assessment_units_completeness_and_uniqueness(self):
        """Verify exactly 620 unique assessment units covering all 33 districts."""
        units = self.data_2024.get("assessment_units", [])
        self.assertEqual(len(units), 620, "Must have exactly 620 assessment units")

        s_nos = [u["s_no"] for u in units]
        self.assertEqual(s_nos, list(range(1, 621)), "S.No must be consecutive from 1 to 620")

        # Verify district coverage
        districts_covered = set(u["district"] for u in units)
        self.assertEqual(len(districts_covered), 33)
        self.assertEqual(districts_covered, set(CANONICAL_DISTRICTS))

        # Check for null, NaN, or negative values where disallowed
        for u in units:
            self.assertIsNotNone(u["district"])
            self.assertIsNotNone(u["mandal"])
            self.assertIn(u["category"], ["Safe", "Semi-Critical", "Critical", "Over-Exploited", "Saline"])
            self.assertGreaterEqual(u["total_annual_recharge_ham"], 0)
            self.assertGreaterEqual(u["annual_extractable_resources_ham"], 0)
            self.assertGreaterEqual(u["total_extraction_ham"], 0)
            self.assertGreaterEqual(u["stage_of_extraction_pct"], 0)

            # Ensure no NaN
            for col in [
                "recharge_monsoon_rainfall_ham",
                "recharge_monsoon_other_ham",
                "recharge_non_monsoon_rainfall_ham",
                "recharge_non_monsoon_other_ham",
                "total_annual_recharge_ham",
                "total_natural_discharges_ham",
                "annual_extractable_resources_ham",
                "extraction_irrigation_ham",
                "extraction_industrial_ham",
                "extraction_domestic_ham",
                "total_extraction_ham",
                "annual_domestic_allocation_2025_ham",
                "net_availability_future_use_ham",
                "stage_of_extraction_pct"
            ]:
                val = u[col]
                self.assertFalse(math.isnan(val), f"NaN found in {u['district']} - {u['mandal']} for {col}")

    def test_volumetric_mathematical_consistency(self):
        """Verify internal arithmetic consistency of volumetric figures for all 620 units."""
        units = self.data_2024.get("assessment_units", [])
        for u in units:
            # 1. Recharge components sum to total recharge
            recharge_calc = (
                u["recharge_monsoon_rainfall_ham"]
                + u["recharge_monsoon_other_ham"]
                + u["recharge_non_monsoon_rainfall_ham"]
                + u["recharge_non_monsoon_other_ham"]
            )
            self.assertAlmostEqual(
                recharge_calc,
                u["total_annual_recharge_ham"],
                delta=0.5,
                msg=f"Recharge component sum mismatch in S.No {u['s_no']} {u['district']} - {u['mandal']}"
            )

            # 2. Extractable resources = total recharge - natural discharges
            extractable_calc = u["total_annual_recharge_ham"] - u["total_natural_discharges_ham"]
            self.assertAlmostEqual(
                extractable_calc,
                u["annual_extractable_resources_ham"],
                delta=0.5,
                msg=f"Extractable resource calculation mismatch in S.No {u['s_no']} {u['district']} - {u['mandal']}"
            )

            # 3. Extraction components sum to total extraction
            extraction_calc = (
                u["extraction_irrigation_ham"]
                + u["extraction_industrial_ham"]
                + u["extraction_domestic_ham"]
            )
            self.assertAlmostEqual(
                extraction_calc,
                u["total_extraction_ham"],
                delta=0.5,
                msg=f"Extraction component sum mismatch in S.No {u['s_no']} {u['district']} - {u['mandal']}"
            )

    def test_category_consistency_and_breakdown(self):
        """Verify overall category breakdown matches official Annexure III(B) counts."""
        units = self.data_2024.get("assessment_units", [])
        cat_counts = {"Safe": 0, "Semi-Critical": 0, "Critical": 0, "Over-Exploited": 0, "Saline": 0}
        for u in units:
            cat_counts[u["category"]] += 1

        self.assertEqual(cat_counts["Safe"], 490)
        self.assertEqual(cat_counts["Semi-Critical"], 85)
        self.assertEqual(cat_counts["Critical"], 13)
        self.assertEqual(cat_counts["Over-Exploited"], 32)
        self.assertEqual(cat_counts["Saline"], 0)

    def test_districts_object_structure(self):
        """Verify the 33-district object contains both volumetric and category breakdowns."""
        districts = self.data_2024.get("districts", {})
        self.assertEqual(len(districts), 33)

        for dname in CANONICAL_DISTRICTS:
            self.assertIn(dname, districts)
            dinfo = districts[dname]
            self.assertIn("soe_pct", dinfo)
            self.assertIn("extractable_ham", dinfo)
            self.assertIn("annual_extraction_ham", dinfo)
            self.assertIn("mandals", dinfo)

            m_info = dinfo["mandals"]
            self.assertGreater(m_info["total"], 0)
            sum_m = m_info["safe"] + m_info["semi_critical"] + m_info["critical"] + m_info["over_exploited"] + m_info["saline"]
            self.assertEqual(sum_m, m_info["total"], f"District {dname} mandal counts do not add up")

    def test_serilingampally_verified_record(self):
        """Verify Serilingampally in 2024 dataset matches Annexure VI and Annexure III(A)."""
        by_key = self.data_2024.get("mandals_by_key", {})
        seri = by_key.get("ranga reddy:serilingampally")

        self.assertIsNotNone(seri, "Serilingampally record must exist in mandals_by_key")
        self.assertEqual(seri["district"], "Ranga Reddy")
        self.assertEqual(seri["mandal"], "Serilingampally")
        self.assertEqual(seri["s_no"], 209)
        self.assertEqual(seri["category"], "Over-Exploited")
        self.assertEqual(seri["stage_of_extraction_pct"], 129.7)
        self.assertEqual(seri["annual_extractable_resources_ham"], 984.1)
        self.assertEqual(seri["total_extraction_ham"], 1276.4)
        self.assertEqual(seri["extraction_domestic_ham"], 1212.1)
        self.assertEqual(seri["extraction_industrial_ham"], 56.2)
        self.assertEqual(seri["extraction_irrigation_ham"], 8.1)
        self.assertEqual(seri["annual_domestic_allocation_2025_ham"], 785.0)

    def test_epoch_separation_and_immutability(self):
        """Ensure 2022 baseline is preserved unchanged while 2024 is distinctly separate."""
        # 1. 2022 dataset checks
        meta_2022 = self.data_2022.get("metadata", {})
        self.assertIn("Assessment Year 2022", meta_2022.get("reporting_period", ""))
        self.assertEqual(self.data_2022["state_summary"]["total_assessment_mandals"], 594)
        self.assertIn("serilingampally", self.data_2022["ocs_mandals"])
        self.assertEqual(self.data_2022["ocs_mandals"]["serilingampally"]["category"], "Critical")
        # Ensure 2022 does not fabricate mandal extraction %
        self.assertNotIn("stage_of_extraction_pct", self.data_2022["ocs_mandals"]["serilingampally"])

        # 2. 2024 dataset checks
        meta_2024 = self.data_2024.get("metadata", {})
        self.assertIn("Assessment Year 2024", meta_2024.get("reporting_period", ""))
        self.assertEqual(self.data_2024["state_summary"]["total_assessment_mandals"], 620)
        seri_2024 = self.data_2024["mandals_by_key"]["ranga reddy:serilingampally"]
        self.assertEqual(seri_2024["category"], "Over-Exploited")
        self.assertEqual(seri_2024["stage_of_extraction_pct"], 129.7)

    def test_parser_reproducibility(self):
        """Verify the parser runs without error on the source PDF and produces consistent records."""
        if not self.pdf_path.exists():
            self.skipTest(f"PDF not found at {self.pdf_path}")

        reader = pypdf.PdfReader(str(self.pdf_path))
        d_data = extract_annexure_2(reader)
        b_data = extract_annexure_3b(reader)
        a_map = extract_annexure_3a(reader)
        units_6 = extract_annexure_6(reader)

        result = validate_and_merge_data(d_data, b_data, a_map, units_6)
        self.assertEqual(len(result["assessment_units"]), 620)
        self.assertEqual(len(result["districts"]), 33)


if __name__ == "__main__":
    unittest.main()
