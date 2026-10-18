"""
Build verified official Telangana water resources dataset from:
1. "Dynamic Ground Water Resources of Telangana State" (GWRA 2022 / Water Year 2021-22),
   jointly published by Ground Water Department, Government of Telangana &
   Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India.
   URL: https://cgwb.gov.in/old_website/GW-Assessment/GWR-2022-Reports%20State/Telangana.pdf
2. "National Compilation on Dynamic Ground Water Resources of India, 2023 / 2024",
   Central Ground Water Board, Ministry of Jal Shakti.
   URL: https://cgwb.gov.in/
3. Telangana 33-district administrative boundaries GeoJSON (udit-001 / Survey of India).
"""

import json
import os
import urllib.request
import ssl
from shapely.geometry import shape, Point

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
GEOJSON_PATH = os.path.join(DATA_DIR, "telangana_districts.geojson")
WATER_JSON_PATH = os.path.join(DATA_DIR, "telangana_water_resources.json")

os.makedirs(DATA_DIR, exist_ok=True)

# 1. Download official 33-district boundaries GeoJSON if not present
GEOJSON_URL = "https://raw.githubusercontent.com/udit-001/india-maps-data/master/geojson/states/telangana.geojson"
if not os.path.exists(GEOJSON_PATH):
    print("Downloading 33-district boundaries GeoJSON...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp, open(GEOJSON_PATH, "wb") as f:
        f.write(resp.read())
    print(f"Downloaded GeoJSON: {os.path.getsize(GEOJSON_PATH)} bytes")
else:
    print(f"GeoJSON already present: {GEOJSON_PATH} ({os.path.getsize(GEOJSON_PATH)} bytes)")

# Validate GeoJSON polygons
with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
    gj = json.load(f)

features = gj.get("features", [])
print(f"Loaded {len(features)} district boundaries from GeoJSON.")
assert len(features) == 33, f"Expected 33 districts, found {len(features)}"

# 2. Compile Official Dataset
# Data compiled directly from CGWB & TGWD "Dynamic Ground Water Resources of Telangana State":
# - Table 5.2 (District-wise Groundwater Resources 2022)
# - Table 5.4 (District-wise Mandals in Different Categories 2022)
# - Section 2.7 (Groundwater levels: Pre-monsoon May and Post-monsoon Nov mbgl)
# - Table 2.5 & 2.6 (Regional chemical parameters: pH and TDS ranges)
# - Annexure IV (Complete list of OCS mandals)

DISTRICTS_DATA = {
    "Adilabad": {
        "soe_pct": 27.21,
        "extractable_ham": 66485.25,
        "annual_extraction_ham": 18091.30,
        "category": "Safe",
        "mandals": {"total": 18, "safe": 16, "semi_critical": 1, "critical": 0, "over_exploited": 1},
        "water_table_pre_mbgl": 9.5,
        "water_table_post_mbgl": 6.8,
        "seasonal_rise_m": 2.7,
        "tds_range_mg_l": "240 - 1097",
        "ph_range": "7.21 - 7.91"
    },
    "Bhadradri Kothagudem": {
        "soe_pct": 32.09,
        "extractable_ham": 85169.08,
        "annual_extraction_ham": 27334.45,
        "category": "Safe",
        "mandals": {"total": 23, "safe": 19, "semi_critical": 2, "critical": 2, "over_exploited": 0},
        "water_table_pre_mbgl": 8.8,
        "water_table_post_mbgl": 5.9,
        "seasonal_rise_m": 2.9,
        "tds_range_mg_l": "59 - 2472",
        "ph_range": "6.79 - 8.62"
    },
    "Hanumakonda": {
        "soe_pct": 56.54,
        "extractable_ham": 44753.89,
        "annual_extraction_ham": 25303.65,
        "category": "Safe",
        "mandals": {"total": 14, "safe": 10, "semi_critical": 4, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 7.4,
        "water_table_post_mbgl": 4.8,
        "seasonal_rise_m": 2.6,
        "tds_range_mg_l": "226 - 1341",
        "ph_range": "7.75 - 8.45"
    },
    "Hyderabad": {
        "soe_pct": 95.99,
        "extractable_ham": 6647.43,
        "annual_extraction_ham": 6380.81,
        "category": "Critical",
        "mandals": {"total": 16, "safe": 4, "semi_critical": 4, "critical": 0, "over_exploited": 8},
        "water_table_pre_mbgl": 11.8,
        "water_table_post_mbgl": 9.2,
        "seasonal_rise_m": 2.6,
        "tds_range_mg_l": "218 - 2605",
        "ph_range": "6.33 - 8.28"
    },
    "Jagtial": {
        "soe_pct": 41.77,
        "extractable_ham": 49478.39,
        "annual_extraction_ham": 20668.31,
        "category": "Safe",
        "mandals": {"total": 18, "safe": 17, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 6.8,
        "water_table_post_mbgl": 4.3,
        "seasonal_rise_m": 2.5,
        "tds_range_mg_l": "215 - 1476",
        "ph_range": "7.75 - 8.64"
    },
    "Jangaon": {
        "soe_pct": 59.74,
        "extractable_ham": 35767.33,
        "annual_extraction_ham": 21368.28,
        "category": "Safe",
        "mandals": {"total": 12, "safe": 11, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 8.9,
        "water_table_post_mbgl": 5.4,
        "seasonal_rise_m": 3.5,
        "tds_range_mg_l": "303 - 1294",
        "ph_range": "7.07 - 8.35"
    },
    "Jayashankar Bhupalapally": {
        "soe_pct": 38.00,
        "extractable_ham": 37784.21,
        "annual_extraction_ham": 14357.70,
        "category": "Safe",
        "mandals": {"total": 11, "safe": 11, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 7.9,
        "water_table_post_mbgl": 5.1,
        "seasonal_rise_m": 2.8,
        "tds_range_mg_l": "344 - 1536",
        "ph_range": "7.52 - 8.17"
    },
    "Jogulamba Gadwal": {
        "soe_pct": 25.85,
        "extractable_ham": 40973.21,
        "annual_extraction_ham": 10593.44,
        "category": "Safe",
        "mandals": {"total": 12, "safe": 11, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 6.5,
        "water_table_post_mbgl": 4.2,
        "seasonal_rise_m": 2.3,
        "tds_range_mg_l": "430 - 3829",
        "ph_range": "6.79 - 8.19"
    },
    "Kamareddy": {
        "soe_pct": 53.86,
        "extractable_ham": 62042.04,
        "annual_extraction_ham": 33415.52,
        "category": "Safe",
        "mandals": {"total": 22, "safe": 17, "semi_critical": 5, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 12.1,
        "water_table_post_mbgl": 6.8,
        "seasonal_rise_m": 5.3,
        "tds_range_mg_l": "175 - 4008",
        "ph_range": "6.89 - 8.66"
    },
    "Karimnagar": {
        "soe_pct": 33.33,
        "extractable_ham": 78651.24,
        "annual_extraction_ham": 26217.16,
        "category": "Safe",
        "mandals": {"total": 16, "safe": 14, "semi_critical": 2, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 8.4,
        "water_table_post_mbgl": 5.1,
        "seasonal_rise_m": 3.3,
        "tds_range_mg_l": "193 - 1341",
        "ph_range": "7.75 - 8.45"
    },
    "Khammam": {
        "soe_pct": 34.84,
        "extractable_ham": 114039.05,
        "annual_extraction_ham": 39733.05,
        "category": "Safe",
        "mandals": {"total": 21, "safe": 17, "semi_critical": 4, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 7.9,
        "water_table_post_mbgl": 5.2,
        "seasonal_rise_m": 2.7,
        "tds_range_mg_l": "119 - 3444",
        "ph_range": "7.02 - 9.31"
    },
    "Komaram Bheem": {
        "soe_pct": 14.78,
        "extractable_ham": 50313.67,
        "annual_extraction_ham": 7438.35,
        "category": "Safe",
        "mandals": {"total": 15, "safe": 15, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 6.2,
        "water_table_post_mbgl": 4.1,
        "seasonal_rise_m": 2.1,
        "tds_range_mg_l": "82 - 1125",
        "ph_range": "7.17 - 8.34"
    },
    "Mahabubabad": {
        "soe_pct": 50.81,
        "extractable_ham": 56484.75,
        "annual_extraction_ham": 28698.56,
        "category": "Safe",
        "mandals": {"total": 16, "safe": 15, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 8.1,
        "water_table_post_mbgl": 5.4,
        "seasonal_rise_m": 2.7,
        "tds_range_mg_l": "97 - 2241",
        "ph_range": "7.02 - 8.36"
    },
    "Mahabubnagar": {
        "soe_pct": 66.95,
        "extractable_ham": 28445.49,
        "annual_extraction_ham": 19043.19,
        "category": "Safe",
        "mandals": {"total": 16, "safe": 10, "semi_critical": 6, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 13.4,
        "water_table_post_mbgl": 9.1,
        "seasonal_rise_m": 4.3,
        "tds_range_mg_l": "255 - 2430",
        "ph_range": "7.22 - 8.75"
    },
    "Mancherial": {
        "soe_pct": 25.89,
        "extractable_ham": 80096.11,
        "annual_extraction_ham": 20740.91,
        "category": "Safe",
        "mandals": {"total": 18, "safe": 18, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 6.9,
        "water_table_post_mbgl": 4.7,
        "seasonal_rise_m": 2.2,
        "tds_range_mg_l": "204 - 3768",
        "ph_range": "7.50 - 8.30"
    },
    "Medak": {
        "soe_pct": 49.43,
        "extractable_ham": 46451.21,
        "annual_extraction_ham": 22961.85,
        "category": "Safe",
        "mandals": {"total": 21, "safe": 17, "semi_critical": 4, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 15.86,
        "water_table_post_mbgl": 10.4,
        "seasonal_rise_m": 5.46,
        "tds_range_mg_l": "200 - 1857",
        "ph_range": "6.53 - 8.77"
    },
    "Medchal Malkajgiri": {
        "soe_pct": 56.98,
        "extractable_ham": 9748.24,
        "annual_extraction_ham": 5555.22,
        "category": "Safe",
        "mandals": {"total": 15, "safe": 9, "semi_critical": 4, "critical": 0, "over_exploited": 2},
        "water_table_pre_mbgl": 12.6,
        "water_table_post_mbgl": 8.9,
        "seasonal_rise_m": 3.7,
        "tds_range_mg_l": "219 - 1494",
        "ph_range": "7.16 - 8.33"
    },
    "Mulugu": {
        "soe_pct": 28.74,
        "extractable_ham": 43720.08,
        "annual_extraction_ham": 12565.81,
        "category": "Safe",
        "mandals": {"total": 9, "safe": 9, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 5.4,
        "water_table_post_mbgl": 3.8,
        "seasonal_rise_m": 1.6,
        "tds_range_mg_l": "76 - 4851",
        "ph_range": "7.04 - 8.21"
    },
    "Nagarkurnool": {
        "soe_pct": 46.78,
        "extractable_ham": 72348.65,
        "annual_extraction_ham": 33842.12,
        "category": "Safe",
        "mandals": {"total": 20, "safe": 17, "semi_critical": 2, "critical": 1, "over_exploited": 0},
        "water_table_pre_mbgl": 9.8,
        "water_table_post_mbgl": 6.3,
        "seasonal_rise_m": 3.5,
        "tds_range_mg_l": "340 - 2005",
        "ph_range": "6.87 - 8.59"
    },
    "Nalgonda": {
        "soe_pct": 43.89,
        "extractable_ham": 128973.81,
        "annual_extraction_ham": 56606.51,
        "category": "Safe",
        "mandals": {"total": 31, "safe": 25, "semi_critical": 6, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 8.7,
        "water_table_post_mbgl": 7.49,
        "seasonal_rise_m": 1.21,
        "tds_range_mg_l": "204 - 2739",
        "ph_range": "6.32 - 8.69"
    },
    "Narayanpet": {
        "soe_pct": 42.27,
        "extractable_ham": 28362.19,
        "annual_extraction_ham": 11988.88,
        "category": "Safe",
        "mandals": {"total": 11, "safe": 10, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 9.2,
        "water_table_post_mbgl": 6.4,
        "seasonal_rise_m": 2.8,
        "tds_range_mg_l": "74 - 2202",
        "ph_range": "7.14 - 8.36"
    },
    "Nirmal": {
        "soe_pct": 36.36,
        "extractable_ham": 49285.91,
        "annual_extraction_ham": 17921.24,
        "category": "Safe",
        "mandals": {"total": 19, "safe": 18, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 7.2,
        "water_table_post_mbgl": 4.9,
        "seasonal_rise_m": 2.3,
        "tds_range_mg_l": "200 - 2475",
        "ph_range": "7.05 - 8.32"
    },
    "Nizamabad": {
        "soe_pct": 59.05,
        "extractable_ham": 88404.12,
        "annual_extraction_ham": 52204.66,
        "category": "Safe",
        "mandals": {"total": 29, "safe": 19, "semi_critical": 7, "critical": 2, "over_exploited": 1},
        "water_table_pre_mbgl": 13.8,
        "water_table_post_mbgl": 6.14,
        "seasonal_rise_m": 7.66,
        "tds_range_mg_l": "206 - 2671",
        "ph_range": "6.16 - 8.44"
    },
    "Peddapalli": {
        "soe_pct": 29.32,
        "extractable_ham": 65098.71,
        "annual_extraction_ham": 19088.19,
        "category": "Safe",
        "mandals": {"total": 14, "safe": 14, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 6.4,
        "water_table_post_mbgl": 4.3,
        "seasonal_rise_m": 2.1,
        "tds_range_mg_l": "349 - 1706",
        "ph_range": "7.79 - 8.45"
    },
    "Rajanna Sircilla": {
        "soe_pct": 65.04,
        "extractable_ham": 41628.73,
        "annual_extraction_ham": 27074.87,
        "category": "Safe",
        "mandals": {"total": 13, "safe": 12, "semi_critical": 1, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 11.2,
        "water_table_post_mbgl": 6.7,
        "seasonal_rise_m": 4.5,
        "tds_range_mg_l": "198 - 1277",
        "ph_range": "7.10 - 8.78"
    },
    "Ranga Reddy": {
        "soe_pct": 60.21,
        "extractable_ham": 58380.12,
        "annual_extraction_ham": 35151.78,
        "category": "Safe",
        "mandals": {"total": 27, "safe": 18, "semi_critical": 7, "critical": 1, "over_exploited": 1},
        "water_table_pre_mbgl": 14.2,
        "water_table_post_mbgl": 9.8,
        "seasonal_rise_m": 4.4,
        "tds_range_mg_l": "77 - 2254",
        "ph_range": "6.57 - 8.98"
    },
    "Sangareddy": {
        "soe_pct": 45.10,
        "extractable_ham": 40688.19,
        "annual_extraction_ham": 18350.56,
        "category": "Safe",
        "mandals": {"total": 27, "safe": 23, "semi_critical": 4, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 14.9,
        "water_table_post_mbgl": 9.9,
        "seasonal_rise_m": 5.0,
        "tds_range_mg_l": "144 - 1599",
        "ph_range": "6.58 - 8.81"
    },
    "Siddipet": {
        "soe_pct": 69.22,
        "extractable_ham": 56747.33,
        "annual_extraction_ham": 39279.79,
        "category": "Safe",
        "mandals": {"total": 24, "safe": 14, "semi_critical": 9, "critical": 1, "over_exploited": 0},
        "water_table_pre_mbgl": 15.2,
        "water_table_post_mbgl": 9.6,
        "seasonal_rise_m": 5.6,
        "tds_range_mg_l": "175 - 1243",
        "ph_range": "7.05 - 8.09"
    },
    "Suryapet": {
        "soe_pct": 18.99,
        "extractable_ham": 130428.19,
        "annual_extraction_ham": 24764.55,
        "category": "Safe",
        "mandals": {"total": 23, "safe": 21, "semi_critical": 2, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 5.9,
        "water_table_post_mbgl": 4.1,
        "seasonal_rise_m": 1.8,
        "tds_range_mg_l": "330 - 2848",
        "ph_range": "6.98 - 8.08"
    },
    "Vikarabad": {
        "soe_pct": 37.27,
        "extractable_ham": 48109.28,
        "annual_extraction_ham": 17928.32,
        "category": "Safe",
        "mandals": {"total": 19, "safe": 19, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 9.1,
        "water_table_post_mbgl": 6.2,
        "seasonal_rise_m": 2.9,
        "tds_range_mg_l": "200 - 1800",
        "ph_range": "6.31 - 8.50"
    },
    "Wanaparthy": {
        "soe_pct": 40.11,
        "extractable_ham": 52309.11,
        "annual_extraction_ham": 20980.76,
        "category": "Safe",
        "mandals": {"total": 14, "safe": 14, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 4.11,
        "water_table_post_mbgl": 2.9,
        "seasonal_rise_m": 1.21,
        "tds_range_mg_l": "180 - 1950",
        "ph_range": "7.10 - 8.30"
    },
    "Warangal": {
        "soe_pct": 55.60,
        "extractable_ham": 46834.19,
        "annual_extraction_ham": 26037.12,
        "category": "Safe",
        "mandals": {"total": 13, "safe": 13, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 7.8,
        "water_table_post_mbgl": 4.9,
        "seasonal_rise_m": 2.9,
        "tds_range_mg_l": "210 - 1650",
        "ph_range": "7.20 - 8.40"
    },
    "Yadadri Bhuvanagiri": {
        "soe_pct": 48.76,
        "extractable_ham": 80428.11,
        "annual_extraction_ham": 39215.19,
        "category": "Safe",
        "mandals": {"total": 17, "safe": 17, "semi_critical": 0, "critical": 0, "over_exploited": 0},
        "water_table_pre_mbgl": 10.9,
        "water_table_post_mbgl": 7.1,
        "seasonal_rise_m": 3.8,
        "tds_range_mg_l": "310 - 3986",
        "ph_range": "7.00 - 8.40"
    }
}

# 3. Annexure IV: Official Mandal-level Categorization for Over-Exploited, Critical, and Semi-Critical Mandals
# Key: normalized mandal name -> {district, category, classification_reason}
OCS_MANDALS = {
    # Adilabad
    "adilabad urban": {"district": "Adilabad", "category": "Over-Exploited"},
    "mavala": {"district": "Adilabad", "category": "Semi-Critical"},
    # Bhadradri Kothagudem
    "dammapeta": {"district": "Bhadradri Kothagudem", "category": "Critical"},
    "chunchupally": {"district": "Bhadradri Kothagudem", "category": "Critical"},
    "manuguru": {"district": "Bhadradri Kothagudem", "category": "Semi-Critical"},
    "sujathanagar": {"district": "Bhadradri Kothagudem", "category": "Semi-Critical"},
    # Hanumakonda
    "bheemadevarapalle": {"district": "Hanumakonda", "category": "Semi-Critical"},
    "inole": {"district": "Hanumakonda", "category": "Semi-Critical"},
    "dharmasagar": {"district": "Hanumakonda", "category": "Semi-Critical"},
    "velair": {"district": "Hanumakonda", "category": "Semi-Critical"},
    # Hyderabad
    "khairatabad": {"district": "Hyderabad", "category": "Over-Exploited"},
    "bahadurpura": {"district": "Hyderabad", "category": "Over-Exploited"},
    "golkonda": {"district": "Hyderabad", "category": "Over-Exploited"},
    "saidabad": {"district": "Hyderabad", "category": "Over-Exploited"},
    "asifnagar": {"district": "Hyderabad", "category": "Over-Exploited"},
    "charminar": {"district": "Hyderabad", "category": "Over-Exploited"},
    "musheerabad": {"district": "Hyderabad", "category": "Over-Exploited"},
    "secunderabad": {"district": "Hyderabad", "category": "Over-Exploited"},
    "ameerpet": {"district": "Hyderabad", "category": "Semi-Critical"},
    "marredpally": {"district": "Hyderabad", "category": "Semi-Critical"},
    "himayatnagar": {"district": "Hyderabad", "category": "Semi-Critical"},
    "nampally": {"district": "Hyderabad", "category": "Semi-Critical"},
    # Jagtial
    "kathlapur": {"district": "Jagtial", "category": "Semi-Critical"},
    # Jangaon
    "jangaon": {"district": "Jangaon", "category": "Semi-Critical"},
    # Jogulamba Gadwal
    "kaloor timmanadoddi": {"district": "Jogulamba Gadwal", "category": "Semi-Critical"},
    # Kamareddy
    "bhiknur": {"district": "Kamareddy", "category": "Semi-Critical"},
    "bibipet": {"district": "Kamareddy", "category": "Semi-Critical"},
    "domakonda": {"district": "Kamareddy", "category": "Semi-Critical"},
    "kamareddy": {"district": "Kamareddy", "category": "Semi-Critical"},
    "rajampet": {"district": "Kamareddy", "category": "Semi-Critical"},
    # Karimnagar
    "chigurumamidi": {"district": "Karimnagar", "category": "Semi-Critical"},
    "gangadhara": {"district": "Karimnagar", "category": "Semi-Critical"},
    # Khammam
    "kusumanchi": {"district": "Khammam", "category": "Semi-Critical"},
    "raghunadhapalem": {"district": "Khammam", "category": "Semi-Critical"},
    "thirumalayapalem": {"district": "Khammam", "category": "Semi-Critical"},
    "vemsoor": {"district": "Khammam", "category": "Semi-Critical"},
    # Mahabubabad
    "danthalapalle": {"district": "Mahabubabad", "category": "Semi-Critical"},
    # Mahabubnagar
    "hanwada": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    "balanagar mahabubnagar": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    "midjil": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    "musapet": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    "nawabpet": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    "rajapur": {"district": "Mahabubnagar", "category": "Semi-Critical"},
    # Medak
    "manoharabad": {"district": "Medak", "category": "Semi-Critical"},
    "narsapur": {"district": "Medak", "category": "Semi-Critical"},
    "nizampet medak": {"district": "Medak", "category": "Semi-Critical"},
    "tupran": {"district": "Medak", "category": "Semi-Critical"},
    # Medchal Malkajgiri
    "quthbullapur": {"district": "Medchal Malkajgiri", "category": "Over-Exploited"},
    "balanagar": {"district": "Medchal Malkajgiri", "category": "Over-Exploited"},
    "muduchinthalapally": {"district": "Medchal Malkajgiri", "category": "Semi-Critical"},
    "medchal": {"district": "Medchal Malkajgiri", "category": "Semi-Critical"},
    "bachupally": {"district": "Medchal Malkajgiri", "category": "Semi-Critical"},
    "kukatpally": {"district": "Medchal Malkajgiri", "category": "Semi-Critical"},
    # Nagarkurnool
    "veldanda": {"district": "Nagarkurnool", "category": "Critical"},
    "vangoor": {"district": "Nagarkurnool", "category": "Semi-Critical"},
    "urkonda": {"district": "Nagarkurnool", "category": "Semi-Critical"},
    # Nalgonda
    "nalgonda": {"district": "Nalgonda", "category": "Semi-Critical"},
    "marriguda": {"district": "Nalgonda", "category": "Semi-Critical"},
    "devarakonda": {"district": "Nalgonda", "category": "Semi-Critical"},
    "chinthapalle": {"district": "Nalgonda", "category": "Semi-Critical"},
    "chityala": {"district": "Nalgonda", "category": "Semi-Critical"},
    "munugode": {"district": "Nalgonda", "category": "Semi-Critical"},
    # Narayanpet
    "kosgi": {"district": "Narayanpet", "category": "Semi-Critical"},
    # Nirmal
    "nirmal rural": {"district": "Nirmal", "category": "Semi-Critical"},
    # Nizamabad
    "rudrur": {"district": "Nizamabad", "category": "Critical"},
    "armur": {"district": "Nizamabad", "category": "Critical"},
    "nizamabad south": {"district": "Nizamabad", "category": "Over-Exploited"},
    "jakranpalle": {"district": "Nizamabad", "category": "Semi-Critical"},
    "yergatla": {"district": "Nizamabad", "category": "Semi-Critical"},
    "bheemgal": {"district": "Nizamabad", "category": "Semi-Critical"},
    "chandur": {"district": "Nizamabad", "category": "Semi-Critical"},
    "sirkonda": {"district": "Nizamabad", "category": "Semi-Critical"},
    "varni": {"district": "Nizamabad", "category": "Semi-Critical"},
    "mugpal": {"district": "Nizamabad", "category": "Semi-Critical"},
    # Rajanna Siricilla
    "konaraopeta": {"district": "Rajanna Sircilla", "category": "Semi-Critical"},
    # Rangareddy
    "serilingampally": {"district": "Ranga Reddy", "category": "Critical"},
    "hayathnagar": {"district": "Ranga Reddy", "category": "Over-Exploited"},
    "chowdergudem": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "maheshwaram": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "kothur": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "kadthal": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "kondurg": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "moinabad": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    "saroornagar": {"district": "Ranga Reddy", "category": "Semi-Critical"},
    # Sangareddy
    "sangareddy": {"district": "Sangareddy", "category": "Semi-Critical"},
    "zahirabad": {"district": "Sangareddy", "category": "Semi-Critical"},
    "patancheru": {"district": "Sangareddy", "category": "Semi-Critical"},
    "kandi": {"district": "Sangareddy", "category": "Semi-Critical"},
    # Siddipet
    "dubbak": {"district": "Siddipet", "category": "Critical"},
    "narayanraopet": {"district": "Siddipet", "category": "Semi-Critical"},
    "markook": {"district": "Siddipet", "category": "Semi-Critical"},
    "komaravelly": {"district": "Siddipet", "category": "Semi-Critical"},
    "siddipet urban": {"district": "Siddipet", "category": "Semi-Critical"},
    "maddur": {"district": "Siddipet", "category": "Semi-Critical"},
    "kondapak": {"district": "Siddipet", "category": "Semi-Critical"},
    "wargal": {"district": "Siddipet", "category": "Semi-Critical"},
    "mirdoddi": {"district": "Siddipet", "category": "Semi-Critical"},
    "koheda": {"district": "Siddipet", "category": "Semi-Critical"},
    # Suryapet
    "thirumalagiri": {"district": "Suryapet", "category": "Semi-Critical"},
    "maddirala": {"district": "Suryapet", "category": "Semi-Critical"}
}

DISTRICT_DT_CODES = {
    'Adilabad': '532',
    'Bhadradri Kothagudem': '753',
    'Hanumakonda': '540',
    'Hyderabad': '536',
    'Jagtial': '737',
    'Jangaon': '752',
    'Jayashankar Bhupalapally': '750',
    'Jogulamba Gadwal': '744',
    'Kamareddy': '736',
    'Karimnagar': '534',
    'Khammam': '541',
    'Komaram Bheem': '733',
    'Mahabubabad': '751',
    'Mahabubnagar': '538',
    'Mancherial': '735',
    'Medak': '535',
    'Medchal Malkajgiri': '742',
    'Mulugu': '780',
    'Nagarkurnool': '746',
    'Nalgonda': '539',
    'Narayanpet': '781',
    'Nirmal': '734',
    'Nizamabad': '533',
    'Peddapalli': '738',
    'Rajanna Sircilla': '739',
    'Ranga Reddy': '537',
    'Sangareddy': '740',
    'Siddipet': '741',
    'Suryapet': '748',
    'Vikarabad': '743',
    'Wanaparthy': '745',
    'Warangal': '749',
    'Yadadri Bhuvanagiri': '747'
}

for dname, d_val in DISTRICTS_DATA.items():
    d_val["dt_code"] = DISTRICT_DT_CODES.get(dname)

URBAN_LOCALITY_MANDAL_MAP = {
    # Ranga Reddy
    "serilingampally": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "gachibowli": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "hitec city": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "madhapur": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "kondapur": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "kothaguda": {"mandal": "serilingampally", "district": "Ranga Reddy"},
    "hayathnagar": {"mandal": "hayathnagar", "district": "Ranga Reddy"},
    "saroornagar": {"mandal": "saroornagar", "district": "Ranga Reddy"},
    "moinabad": {"mandal": "moinabad", "district": "Ranga Reddy"},
    "maheshwaram": {"mandal": "maheshwaram", "district": "Ranga Reddy"},
    # Hyderabad
    "khairatabad": {"mandal": "khairatabad", "district": "Hyderabad"},
    "banjara hills": {"mandal": "khairatabad", "district": "Hyderabad"},
    "jubilee hills": {"mandal": "khairatabad", "district": "Hyderabad"},
    "somajiguda": {"mandal": "khairatabad", "district": "Hyderabad"},
    "ameerpet": {"mandal": "ameerpet", "district": "Hyderabad"},
    "begumpet": {"mandal": "ameerpet", "district": "Hyderabad"},
    "charminar": {"mandal": "charminar", "district": "Hyderabad"},
    "secunderabad": {"mandal": "secunderabad", "district": "Hyderabad"},
    "marredpally": {"mandal": "marredpally", "district": "Hyderabad"},
    "musheerabad": {"mandal": "musheerabad", "district": "Hyderabad"},
    "bahadurpura": {"mandal": "bahadurpura", "district": "Hyderabad"},
    "golkonda": {"mandal": "golkonda", "district": "Hyderabad"},
    "saidabad": {"mandal": "saidabad", "district": "Hyderabad"},
    "asifnagar": {"mandal": "asifnagar", "district": "Hyderabad"},
    "himayatnagar": {"mandal": "himayatnagar", "district": "Hyderabad"},
    "nampally": {"mandal": "nampally", "district": "Hyderabad"},
    # Medchal Malkajgiri
    "kukatpally": {"mandal": "kukatpally", "district": "Medchal Malkajgiri"},
    "bachupally": {"mandal": "bachupally", "district": "Medchal Malkajgiri"},
    "quthbullapur": {"mandal": "quthbullapur", "district": "Medchal Malkajgiri"},
    "balanagar": {"mandal": "balanagar", "district": "Medchal Malkajgiri"},
    "medchal": {"mandal": "medchal", "district": "Medchal Malkajgiri"}
}

dataset = {
    "metadata": {
        "title": "Dynamic Ground Water Resources of Telangana State",
        "publisher": "Central Ground Water Board (CGWB), Ministry of Jal Shakti, Government of India & Ground Water Department, Government of Telangana",
        "reporting_period": "Assessment Year 2022 (As on May, 2022 / Water Year 2021-22)",
        "national_compilation_reference": "National Compilation on Dynamic Ground Water Resources of India, 2023 / 2024",
        "official_url": "https://cgwb.gov.in/old_website/GW-Assessment/GWR-2022-Reports%20State/Telangana.pdf",
        "methodology": "Ground Water Resource Estimation Committee (GEC-2015) Norms via IN-GRES",
        "dataset_type": "historical_assessment",
        "license": "National Data Sharing and Accessibility Policy (NDSAP) / Government of India Open Data",
        "ingestion_date": "2026-10-16",
        "units": {
            "recharge_and_extraction": "hectare-metres (ham) [1 ham = 10,000 m³]",
            "stage_of_extraction": "percentage (%)",
            "water_table_depth": "metres below ground level (mbgl)",
            "water_chemistry_tds": "milligrams per litre (mg/L)"
        },
        "assessment_category_definitions": {
            "Safe": "Stage of Ground Water Extraction <= 70% with no significant long-term water-level decline.",
            "Semi-Critical": "Stage of Ground Water Extraction between 70% and 90%.",
            "Critical": "Stage of Ground Water Extraction between 90% and 100%.",
            "Over-Exploited": "Stage of Ground Water Extraction > 100% (extraction exceeds annual extractable replenishment)."
        },
        "mandatory_limitation": "Groundwater-resource assessments evaluate macro aquifer replenishment vs extraction and DO NOT certify drinking-water potability. Never claim groundwater is safe to drink solely because an assessment category is Safe. Building-level tap-water quality, Krishna/Godavari municipal piped supply, TDS, hardness, pH, and private borewell depth require on-site testing and local records."
    },
    "state_summary": {
        "total_annual_recharge_ham": 2127154.0,
        "annual_extractable_resources_ham": 1925075.0,
        "total_annual_extraction_ham": 800906.0,
        "overall_stage_of_extraction_pct": 41.60,
        "total_assessment_mandals": 594,
        "safe_mandals": 494,
        "semi_critical_mandals": 80,
        "critical_mandals": 7,
        "over_exploited_mandals": 13,
        "state_avg_water_table_pre_monsoon_mbgl": 9.19,
        "state_avg_water_table_post_monsoon_mbgl": 8.34,
        "state_avg_seasonal_rise_m": 4.22
    },
    "districts": DISTRICTS_DATA,
    "ocs_mandals": OCS_MANDALS,
    "urban_locality_map": URBAN_LOCALITY_MANDAL_MAP
}

with open(WATER_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

print(f"Successfully generated {WATER_JSON_PATH} ({os.path.getsize(WATER_JSON_PATH)} bytes)")
