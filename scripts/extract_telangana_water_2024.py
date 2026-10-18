#!/usr/bin/env python3
"""
extract_telangana_water_2024.py

Extracts and validates official Telangana groundwater resources data from the
CGWB report:
"Dynamic Ground Water Resources of Telangana State, 2024"
Published by Central Ground Water Board (CGWB) & Ground Water Department, Govt of Telangana.
Official Publication: https://cgwb.gov.in/cgwbpnm/public/publication-detail/1541
Download URL: https://cgwb.gov.in/cgwbpnm/public/download/1541

Outputs:
backend/data/telangana_water_resources_2024.json
"""

import argparse
import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extract_water_2024")

# Canonical 33 districts of Telangana
CANONICAL_DISTRICTS: List[str] = [
    "Adilabad", "Bhadradri Kothagudem", "Hanumakonda", "Hyderabad", "Jagtial",
    "Jangaon", "Jayashankar Bhupalpally", "Jogulamba Gadwal", "Kamareddy",
    "Karimnagar", "Khammam", "Kumuram Bheem Asifabad", "Mahabubabad",
    "Mahabubnagar", "Mancherial", "Medak", "Medchal Malkajgiri", "Mulugu",
    "Nagarkurnool", "Nalgonda", "Narayanpet", "Nirmal", "Nizamabad",
    "Peddapalli", "Rajanna Sircilla", "Ranga Reddy", "Sangareddy", "Siddipet",
    "Suryapet", "Vikarabad", "Wanaparthy", "Warangal", "Yadadri Bhuvanagiri"
]

# District spelling variations found in CGWB 2024 tables mapped to canonical names
DISTRICT_SYNONYMS: Dict[str, str] = {
    "komarambhee m asifabad": "Kumuram Bheem Asifabad",
    "komaram bheem asifabad": "Kumuram Bheem Asifabad",
    "komarambheem asifabad": "Kumuram Bheem Asifabad",
    "kumuram bheem asifabad": "Kumuram Bheem Asifabad",
    "kumuram bheem": "Kumuram Bheem Asifabad",
    "komaram bheem": "Kumuram Bheem Asifabad",
    "jayashankar bhupalapally": "Jayashankar Bhupalpally",
    "jayashankar bhupalpally": "Jayashankar Bhupalpally",
    "peddapalle": "Peddapalli",
    "peddapalli": "Peddapalli",
    "rajanna siricilla": "Rajanna Sircilla",
    "rajanna sircilla": "Rajanna Sircilla",
    "mulug": "Mulugu",
    "mulugu": "Mulugu",
    "rangareddy": "Ranga Reddy",
    "ranga reddy": "Ranga Reddy",
    "medchal malkajgiri": "Medchal Malkajgiri",
    "medchal-malkajgiri": "Medchal Malkajgiri",
    "bhadradri kothagudem": "Bhadradri Kothagudem",
    "jogulamba gadwal": "Jogulamba Gadwal",
    "yadadri bhuvanagiri": "Yadadri Bhuvanagiri",
    "hanumakonda": "Hanumakonda",
    "warangal urban": "Hanumakonda",
    "warangal rural": "Warangal",
    "warangal": "Warangal"
}
for d in CANONICAL_DISTRICTS:
    DISTRICT_SYNONYMS[d.lower()] = d


def normalize_name(name: str) -> str:
    """Normalize names for collision-free alphanumeric comparison."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_district_and_mandal(text_part: str) -> Tuple[Optional[str], Optional[str]]:
    """Split leading district and trailing mandal name from text."""
    clean_text = " ".join(text_part.split())
    for syn_key in sorted(DISTRICT_SYNONYMS.keys(), key=len, reverse=True):
        if clean_text.lower().startswith(syn_key):
            matched_district = DISTRICT_SYNONYMS[syn_key]
            mandal_name = clean_text[len(syn_key):].strip(" -_")
            return matched_district, mandal_name
    return None, None


def extract_annexure_2(reader: pypdf.PdfReader) -> Dict[str, Dict[str, Any]]:
    """
    Extract Annexure-II (District-wise summary) from page 91.
    Returns dict keyed by canonical district name.
    """
    logger.info("Extracting Annexure-II (District summary) from page 91...")
    page_text = reader.pages[91].extract_text() or ""
    districts_data: Dict[str, Dict[str, Any]] = {}

    for line in page_text.splitlines():
        line = line.strip()
        m = re.match(r"^(\d+)\s+([A-Za-z\s]+?)\s+([\d\.\s]+)$", line)
        if not m:
            continue
        sno = int(m.group(1))
        dname_raw = m.group(2).strip()
        num_str = m.group(3).strip()
        nums = [float(x) for x in num_str.split()]

        if len(nums) != 14:
            raise ValueError(f"Annexure-II row {sno} '{dname_raw}' has {len(nums)} values, expected 14")

        matched_d = None
        for syn_key in sorted(DISTRICT_SYNONYMS.keys(), key=len, reverse=True):
            if dname_raw.lower() == syn_key or dname_raw.lower().startswith(syn_key):
                matched_d = DISTRICT_SYNONYMS[syn_key]
                break

        if not matched_d:
            raise ValueError(f"Unmatched district name in Annexure-II: '{dname_raw}'")

        districts_data[matched_d] = {
            "s_no": sno,
            "district": matched_d,
            "district_raw_name": dname_raw,
            "recharge_monsoon_rainfall_ham": nums[0],
            "recharge_monsoon_other_ham": nums[1],
            "recharge_non_monsoon_rainfall_ham": nums[2],
            "recharge_non_monsoon_other_ham": nums[3],
            "total_annual_recharge_ham": nums[4],
            "total_natural_discharges_ham": nums[5],
            "annual_extractable_resources_ham": nums[6],
            "extraction_irrigation_ham": nums[7],
            "extraction_industrial_ham": nums[8],
            "extraction_domestic_ham": nums[9],
            "total_annual_extraction_ham": nums[10],
            "annual_domestic_allocation_2025_ham": nums[11],
            "net_availability_future_use_ham": nums[12],
            "stage_of_extraction_pct": nums[13],
            "units": "ham (hectare-metres)"
        }

    if len(districts_data) != 33:
        raise ValueError(f"Annexure-II extracted {len(districts_data)} districts, expected 33")

    logger.info("Successfully extracted Annexure-II for all 33 districts.")
    return districts_data


def extract_annexure_3b(reader: pypdf.PdfReader) -> Dict[str, Dict[str, Any]]:
    """
    Extract Annexure-III(B) (District categorizations) from page 112.
    Returns dict keyed by canonical district name.
    """
    logger.info("Extracting Annexure-III(B) (District categorizations) from page 112...")
    page_text = reader.pages[112].extract_text() or ""
    cat_b_data: Dict[str, Dict[str, Any]] = {}

    for line in page_text.splitlines():
        line = line.strip()
        m = re.match(r"^(\d+)\s+([A-Za-z\s]+?)\s+(\d+)\s+(.*)$", line)
        if not m:
            continue
        sno = int(m.group(1))
        dname_raw = m.group(2).strip()
        total_units = int(m.group(3))
        tokens = m.group(4).strip().split()

        vals = [0.0 if t == "-" else float(t) for t in tokens]
        if len(vals) != 10:
            raise ValueError(f"Annexure-III(B) row {sno} '{dname_raw}' tokens len {len(vals)}, expected 10")

        safe_cnt, safe_pct, semi_cnt, semi_pct, crit_cnt, crit_pct, oe_cnt, oe_pct, sal_cnt, sal_pct = vals

        matched_d = None
        for syn_key in sorted(DISTRICT_SYNONYMS.keys(), key=len, reverse=True):
            if dname_raw.lower() == syn_key or dname_raw.lower().startswith(syn_key):
                matched_d = DISTRICT_SYNONYMS[syn_key]
                break

        if not matched_d:
            raise ValueError(f"Unmatched district in Annexure-III(B): '{dname_raw}'")

        cat_b_data[matched_d] = {
            "total_units": total_units,
            "safe_count": int(safe_cnt),
            "safe_pct": safe_pct,
            "semi_critical_count": int(semi_cnt),
            "semi_critical_pct": semi_pct,
            "critical_count": int(crit_cnt),
            "critical_pct": crit_pct,
            "over_exploited_count": int(oe_cnt),
            "over_exploited_pct": oe_pct,
            "saline_count": int(sal_cnt),
            "saline_pct": sal_pct
        }

    if len(cat_b_data) != 33:
        raise ValueError(f"Annexure-III(B) extracted {len(cat_b_data)} districts, expected 33")

    logger.info("Successfully extracted Annexure-III(B) for all 33 districts.")
    return cat_b_data


def extract_annexure_3a(reader: pypdf.PdfReader) -> Dict[Tuple[str, str], str]:
    """
    Extract Annexure-III(A) (Assessment unit categorization) from pages 92 to 111.
    Returns dict mapping (canonical_district, normalized_mandal) -> standardized category.
    """
    logger.info("Extracting Annexure-III(A) (Unit categorizations) from pages 92-111...")
    full_text = ""
    for p in range(92, 112):
        full_text += "\n" + (reader.pages[p].extract_text() or "")

    cat_map: Dict[Tuple[str, str], str] = {}
    row_count = 0

    for line in full_text.splitlines():
        line = line.strip()
        m = re.match(r"^(\d+)\s+Telangana\s+(.*)$", line)
        if not m:
            continue
        row_count += 1
        sno = int(m.group(1))
        rest = m.group(2).strip()

        matched_cat = None
        unit_part = None
        for c in ["Over Exploited", "Over-Exploited", "Semi Critical", "Semi-Critical", "Critical", "Safe", "Saline"]:
            if rest.lower().endswith(c.lower()):
                matched_cat = c
                unit_part = rest[:-len(c)].strip()
                break

        if not matched_cat or not unit_part:
            raise ValueError(f"Failed to parse category from Annexure-III(A) row {sno}: '{rest}'")

        if "over" in matched_cat.lower():
            std_cat = "Over-Exploited"
        elif "semi" in matched_cat.lower():
            std_cat = "Semi-Critical"
        elif "critical" in matched_cat.lower():
            std_cat = "Critical"
        elif "safe" in matched_cat.lower():
            std_cat = "Safe"
        elif "saline" in matched_cat.lower():
            std_cat = "Saline"
        else:
            std_cat = matched_cat

        matched_d, mandal_name = match_district_and_mandal(unit_part)
        if not matched_d or not mandal_name:
            raise ValueError(f"Could not parse district/mandal from Annexure-III(A) unit '{unit_part}' (row {sno})")

        key = (matched_d, normalize_name(mandal_name))
        cat_map[key] = std_cat

    if row_count != 620:
        raise ValueError(f"Annexure-III(A) row count is {row_count}, expected 620")
    if len(cat_map) != 620:
        raise ValueError(f"Annexure-III(A) unique unit key count is {len(cat_map)}, expected 620")

    logger.info("Successfully extracted Annexure-III(A) for all 620 assessment units.")
    return cat_map


def extract_annexure_6(reader: pypdf.PdfReader) -> List[Dict[str, Any]]:
    """
    Extract Annexure-VI (Attribute Table) from pages 130 to 149.
    Returns list of 620 parsed dictionaries.
    """
    logger.info("Extracting Annexure-VI (Attribute Table) from pages 130-149...")
    full_text = ""
    for page_idx in range(130, 150):
        full_text += "\n" + (reader.pages[page_idx].extract_text() or "")

    fixed_text = re.sub(r"(\d+)\.\s*\n\s*(\d+)", r"\1.\2", full_text)
    lines = []
    for line in fixed_text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if any(h in line_clean for h in ["Annexure VI", "Assessment Unit Wise", "Ground Water Recharge", "Monsoon Season", "Non Monsoon", "Current Annual"]):
            continue
        if any(h in line_clean for h in ["Discharges", "Extractable", "Allocation", "Future Use", "Stage of", "Extraction"]):
            continue
        if line_clean.isdigit() and int(line_clean) < 160:  # Page numbers
            continue
        lines.append(line_clean)

    joined_content = "\n".join(lines)
    row_starts = list(re.finditer(r"(?:^|\n)(\d+)\s+Telangana\s+", joined_content))

    if len(row_starts) != 620:
        raise ValueError(f"Annexure-VI found {len(row_starts)} row starts, expected 620")

    parsed_units: List[Dict[str, Any]] = []

    for i in range(len(row_starts)):
        start_pos = row_starts[i].start()
        end_pos = row_starts[i + 1].start() if i + 1 < len(row_starts) else len(joined_content)
        r_text = joined_content[start_pos:end_pos].strip()
        s_no = int(row_starts[i].group(1))

        if s_no != i + 1:
            raise ValueError(f"Annexure-VI sequence mismatch at index {i}: row S.No is {s_no}")

        cleaned = re.sub(r"^\d+\s+Telangana\s+", "", r_text, flags=re.IGNORECASE)
        tokens = " ".join(cleaned.split()).split()

        num_tokens: List[float] = []
        idx = len(tokens) - 1
        while idx >= 0:
            try:
                val = float(tokens[idx])
                num_tokens.insert(0, val)
                idx -= 1
            except ValueError:
                break

        text_part = " ".join(tokens[: idx + 1])

        if len(num_tokens) != 14:
            raise ValueError(f"Annexure-VI S.No {s_no} has {len(num_tokens)} numbers (expected 14): {r_text}")

        matched_d, mandal_name = match_district_and_mandal(text_part)
        if not matched_d:
            raise ValueError(f"Annexure-VI S.No {s_no}: Failed to match district in '{text_part}'")
        if not mandal_name:
            raise ValueError(f"Annexure-VI S.No {s_no}: Empty mandal name in '{text_part}'")

        parsed_units.append({
            "s_no": s_no,
            "district": matched_d,
            "mandal": mandal_name,
            "recharge_monsoon_rainfall_ham": num_tokens[0],
            "recharge_monsoon_other_ham": num_tokens[1],
            "recharge_non_monsoon_rainfall_ham": num_tokens[2],
            "recharge_non_monsoon_other_ham": num_tokens[3],
            "total_annual_recharge_ham": num_tokens[4],
            "total_natural_discharges_ham": num_tokens[5],
            "annual_extractable_resources_ham": num_tokens[6],
            "extraction_irrigation_ham": num_tokens[7],
            "extraction_industrial_ham": num_tokens[8],
            "extraction_domestic_ham": num_tokens[9],
            "total_extraction_ham": num_tokens[10],
            "annual_domestic_allocation_2025_ham": num_tokens[11],
            "net_availability_future_use_ham": num_tokens[12],
            "stage_of_extraction_pct": num_tokens[13]
        })

    logger.info("Successfully extracted Annexure-VI for all 620 assessment units.")
    return parsed_units


def validate_and_merge_data(
    districts_data: Dict[str, Dict[str, Any]],
    cat_b_data: Dict[str, Dict[str, Any]],
    cat_a_map: Dict[Tuple[str, str], str],
    annexure_6_units: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Perform rigorous mathematical, referential, and category validation across all tables.
    Never silently repairs ambiguous data.
    """
    logger.info("Starting strict cross-table validation...")

    # 1. Check unit count and district coverage
    if len(annexure_6_units) != 620:
        raise AssertionError(f"Expected exactly 620 assessment units, got {len(annexure_6_units)}")

    districts_found = set(u["district"] for u in annexure_6_units)
    if districts_found != set(CANONICAL_DISTRICTS):
        missing_d = set(CANONICAL_DISTRICTS) - districts_found
        extra_d = districts_found - set(CANONICAL_DISTRICTS)
        raise AssertionError(f"District coverage mismatch: missing={missing_d}, extra={extra_d}")

    # 2. Match each Annexure VI unit with Annexure III(A) category
    merged_units = []
    category_counts = {"Safe": 0, "Semi-Critical": 0, "Critical": 0, "Over-Exploited": 0, "Saline": 0}
    district_cat_counts: Dict[str, Dict[str, int]] = {
        d: {"Safe": 0, "Semi-Critical": 0, "Critical": 0, "Over-Exploited": 0, "Saline": 0, "total": 0}
        for d in CANONICAL_DISTRICTS
    }

    for u in annexure_6_units:
        d = u["district"]
        norm_m = normalize_name(u["mandal"])
        key = (d, norm_m)

        if key not in cat_a_map:
            raise AssertionError(f"Unit in Annexure-VI not found in Annexure-III(A): S.No {u['s_no']}, '{d}' - '{u['mandal']}'")

        category = cat_a_map[key]
        category_counts[category] += 1
        district_cat_counts[d][category] += 1
        district_cat_counts[d]["total"] += 1

        # Mathematical internal checks on volumetric numbers
        recharge_calc = (
            u["recharge_monsoon_rainfall_ham"]
            + u["recharge_monsoon_other_ham"]
            + u["recharge_non_monsoon_rainfall_ham"]
            + u["recharge_non_monsoon_other_ham"]
        )
        if abs(recharge_calc - u["total_annual_recharge_ham"]) > 0.5:
            raise AssertionError(
                f"Recharge sum mismatch at S.No {u['s_no']} ({d} - {u['mandal']}): calc={recharge_calc}, reported={u['total_annual_recharge_ham']}"
            )

        extractable_calc = u["total_annual_recharge_ham"] - u["total_natural_discharges_ham"]
        if abs(extractable_calc - u["annual_extractable_resources_ham"]) > 0.5:
            raise AssertionError(
                f"Extractable resource mismatch at S.No {u['s_no']} ({d} - {u['mandal']}): calc={extractable_calc}, reported={u['annual_extractable_resources_ham']}"
            )

        extraction_calc = (
            u["extraction_irrigation_ham"]
            + u["extraction_industrial_ham"]
            + u["extraction_domestic_ham"]
        )
        if abs(extraction_calc - u["total_extraction_ham"]) > 0.5:
            raise AssertionError(
                f"Extraction sum mismatch at S.No {u['s_no']} ({d} - {u['mandal']}): calc={extraction_calc}, reported={u['total_extraction_ham']}"
            )

        merged_rec = dict(u)
        merged_rec["category"] = category
        merged_units.append(merged_rec)

    # 3. Verify category counts against Annexure III(B) totals
    expected_totals = {"Safe": 490, "Semi-Critical": 85, "Critical": 13, "Over-Exploited": 32, "Saline": 0}
    if category_counts != expected_totals:
        raise AssertionError(f"Category counts mismatch! Extracted={category_counts}, Expected={expected_totals}")

    # 4. Verify each district's mandal breakdown matches Annexure III(B)
    for d, counts in district_cat_counts.items():
        expected_b = cat_b_data[d]
        if counts["total"] != expected_b["total_units"]:
            raise AssertionError(f"District {d} mandal total mismatch: {counts['total']} != {expected_b['total_units']}")
        if counts["Safe"] != expected_b["safe_count"]:
            raise AssertionError(f"District {d} safe count mismatch: {counts['Safe']} != {expected_b['safe_count']}")
        if counts["Semi-Critical"] != expected_b["semi_critical_count"]:
            raise AssertionError(f"District {d} semi-crit mismatch: {counts['Semi-Critical']} != {expected_b['semi_critical_count']}")
        if counts["Critical"] != expected_b["critical_count"]:
            raise AssertionError(f"District {d} crit mismatch: {counts['Critical']} != {expected_b['critical_count']}")
        if counts["Over-Exploited"] != expected_b["over_exploited_count"]:
            raise AssertionError(f"District {d} OE mismatch: {counts['Over-Exploited']} != {expected_b['over_exploited_count']}")

    logger.info("Category and district unit breakdown verified 100% against Annexure III(B).")

    # 5. Build rich district records combining Annexure II and III(B)
    combined_districts: Dict[str, Dict[str, Any]] = {}
    for d in CANONICAL_DISTRICTS:
        d_summary = dict(districts_data[d])
        d_cats = cat_b_data[d]
        # Assign district category based on overall SOE% and GEC-2015
        soe = d_summary["stage_of_extraction_pct"]
        if soe > 100.0:
            d_category = "Over-Exploited"
        elif soe > 90.0:
            d_category = "Critical"
        elif soe > 70.0:
            d_category = "Semi-Critical"
        else:
            d_category = "Safe"

        combined_districts[d] = {
            "s_no": d_summary["s_no"],
            "district": d,
            "soe_pct": d_summary["stage_of_extraction_pct"],
            "extractable_ham": d_summary["annual_extractable_resources_ham"],
            "annual_extraction_ham": d_summary["total_annual_extraction_ham"],
            "total_recharge_ham": d_summary["total_annual_recharge_ham"],
            "natural_discharges_ham": d_summary["total_natural_discharges_ham"],
            "irrigation_extraction_ham": d_summary["extraction_irrigation_ham"],
            "industrial_extraction_ham": d_summary["extraction_industrial_ham"],
            "domestic_extraction_ham": d_summary["extraction_domestic_ham"],
            "domestic_allocation_2025_ham": d_summary["annual_domestic_allocation_2025_ham"],
            "net_future_availability_ham": d_summary["net_availability_future_use_ham"],
            "category": d_category,
            "mandals": {
                "total": d_cats["total_units"],
                "safe": d_cats["safe_count"],
                "safe_pct": d_cats["safe_pct"],
                "semi_critical": d_cats["semi_critical_count"],
                "semi_critical_pct": d_cats["semi_critical_pct"],
                "critical": d_cats["critical_count"],
                "critical_pct": d_cats["critical_pct"],
                "over_exploited": d_cats["over_exploited_count"],
                "over_exploited_pct": d_cats["over_exploited_pct"],
                "saline": d_cats["saline_count"]
            }
        }

    # 6. Build fast lookup index by "district:mandal"
    mandals_by_key: Dict[str, Dict[str, Any]] = {}
    for u in merged_units:
        lookup_key = f"{u['district'].lower()}:{u['mandal'].lower()}"
        norm_key = f"{normalize_name(u['district'])}:{normalize_name(u['mandal'])}"
        mandals_by_key[lookup_key] = u
        if norm_key != lookup_key:
            mandals_by_key[norm_key] = u

    # 7. Assemble final dataset with comprehensive metadata
    final_dataset = {
        "metadata": {
            "title": "Dynamic Ground Water Resources of Telangana State, 2024",
            "publisher": "Central Ground Water Board (CGWB), Ministry of Jal Shakti, Department of Water Resources, RD & GR, Government of India & Ground Water Department, Government of Telangana",
            "reporting_period": "Assessment Year 2024 (As on March/May 2024 / Water Year 2023-24)",
            "national_compilation_reference": "National Compilation on Dynamic Ground Water Resources of India, 2024",
            "official_url": "https://cgwb.gov.in/cgwbpnm/public/publication-detail/1541",
            "download_url": "https://cgwb.gov.in/cgwbpnm/public/download/1541",
            "methodology": "Ground Water Resource Estimation Committee (GEC-2015) Norms via IN-GRES",
            "dataset_type": "historical_assessment",
            "epoch": "2024",
            "license": "Government Open Data License - India (GODL) / NDSAP",
            "ingestion_date": "2026-10-16",
            "units": {
                "recharge_and_extraction": "hectare-metres (ham) [1 ham = 10,000 m³ = 0.01 mcm = 0.00001 bcm]",
                "stage_of_extraction": "percentage (%)"
            },
            "assessment_category_definitions": {
                "Safe": "Stage of Ground Water Extraction <= 70% with no significant long-term water-level decline.",
                "Semi-Critical": "Stage of Ground Water Extraction between 70% and 90%.",
                "Critical": "Stage of Ground Water Extraction between 90% and 100%.",
                "Over-Exploited": "Stage of Ground Water Extraction > 100% (annual extraction exceeds annual extractable replenishment).",
                "Saline": "Ground water assessment units with poor chemical quality / high salinity."
            },
            "mandatory_limitation": "Groundwater-resource assessments evaluate macro aquifer replenishment vs extraction and DO NOT certify drinking-water potability. Never claim groundwater is safe to drink solely because an assessment category is Safe. Building-level tap-water quality, Krishna/Godavari municipal piped supply, TDS, hardness, pH, and private borewell depth require on-site testing and local records."
        },
        "state_summary": {
            "total_annual_recharge_bcm": 20.4,
            "total_annual_recharge_ham": 2040000.0,
            "annual_extractable_resources_bcm": 18.44,
            "annual_extractable_resources_ham": 1844000.0,
            "total_annual_extraction_bcm": 8.47,
            "total_annual_extraction_ham": 847000.0,
            "overall_stage_of_extraction_pct": 45.91,
            "total_assessment_mandals": 620,
            "safe_mandals": 490,
            "safe_mandals_pct": 79.03,
            "semi_critical_mandals": 85,
            "semi_critical_mandals_pct": 13.71,
            "critical_mandals": 13,
            "critical_mandals_pct": 2.1,
            "over_exploited_mandals": 32,
            "over_exploited_mandals_pct": 5.16,
            "saline_mandals": 0
        },
        "districts": combined_districts,
        "assessment_units": merged_units,
        "mandals_by_key": mandals_by_key
    }

    logger.info("Validation complete: 620 units, 33 districts, 0 missing records.")
    return final_dataset


def main():
    parser = argparse.ArgumentParser(description="Extract 2024 CGWB Telangana Groundwater Resources")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("backend/data/tmp/gwra_telangana_2024.pdf"),
        help="Path to downloaded CGWB 2024 report PDF"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/data/telangana_water_resources_2024.json"),
        help="Path to write validated JSON output"
    )
    args = parser.parse_args()

    if not args.pdf.exists():
        logger.error(f"Source PDF not found at {args.pdf}. Download from https://cgwb.gov.in/cgwbpnm/public/download/1541")
        sys.exit(1)

    logger.info(f"Reading source PDF: {args.pdf} ({args.pdf.stat().st_size:,} bytes)")
    reader = pypdf.PdfReader(str(args.pdf))
    logger.info(f"Loaded PDF with {len(reader.pages)} pages.")

    districts_data = extract_annexure_2(reader)
    cat_b_data = extract_annexure_3b(reader)
    cat_a_map = extract_annexure_3a(reader)
    annexure_6_units = extract_annexure_6(reader)

    dataset = validate_and_merge_data(districts_data, cat_b_data, cat_a_map, annexure_6_units)

    # Ensure output parent directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully generated validated dataset at {args.output} ({args.output.stat().st_size:,} bytes)")

    # Print Serilingampally verification comparison
    seri_rec = dataset["mandals_by_key"].get("ranga reddy:serilingampally")
    if seri_rec:
        print("\n=== Verified Serilingampally (2024 Record) ===")
        print(f"District: {seri_rec['district']}")
        print(f"Mandal: {seri_rec['mandal']}")
        print(f"S.No in Annexure-VI: {seri_rec['s_no']}")
        print(f"Category: {seri_rec['category']}")
        print(f"Stage of Ground Water Extraction: {seri_rec['stage_of_extraction_pct']}%")
        print(f"Annual Extractable Resource: {seri_rec['annual_extractable_resources_ham']} HAM")
        print(f"Total Current Annual Extraction: {seri_rec['total_extraction_ham']} HAM")
        print(f"  - Domestic Extraction: {seri_rec['extraction_domestic_ham']} HAM")
        print(f"  - Industrial Extraction: {seri_rec['extraction_industrial_ham']} HAM")
        print(f"  - Irrigation Extraction: {seri_rec['extraction_irrigation_ham']} HAM")
        print(f"2025 Domestic Allocation: {seri_rec['annual_domestic_allocation_2025_ham']} HAM")
        print("==============================================\n")


if __name__ == "__main__":
    main()
