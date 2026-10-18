import os
import math
import json
import sqlite3
import logging
from datetime import datetime
from shapely.geometry import shape, Point

from backend.app.config import settings
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.modules import (
    SafetyFacility,
    EmergencyContact,
    JurisdictionInfo,
    SafetyAndCrimeData,
    CrimeData
)
from backend.app.providers.base import CrimeProvider, StoragePolicy
from backend.app.utils.geo import haversine_distance_m

logger = logging.getLogger(__name__)

# Authoritative Emergency Directory verified against official Telangana and Government of India portals
VERIFIED_EMERGENCY_CONTACTS: list[EmergencyContact] = [
    EmergencyContact(
        service="All-India Emergency Response Support System (ERSS)",
        number="112",
        description="Unified national emergency hotline for instant police dispatch, fire response, and medical ambulance coordination.",
        jurisdiction="National / Telangana Statewide",
        verified_authority="Ministry of Home Affairs (MHA) & Telangana State Police",
        source_url="https://112.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Single unified emergency gateway.",
            "Calls are routed to the centralized Emergency Response Centre (ERC) in Hyderabad for immediate field unit dispatch."
        ]
    ),
    EmergencyContact(
        service="Telangana Police Emergency Control Room",
        number="100",
        description="Direct state police emergency response and patrol mobilization helpline.",
        jurisdiction="Telangana Statewide",
        verified_authority="Telangana State Police",
        source_url="https://tspolice.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Integrated with the Telangana Police Integrated Command and Control Centre (ICCC).",
            "Dispatches Dial 100 patrol cars and Blue Colts first responders."
        ]
    ),
    EmergencyContact(
        service="Telangana Disaster Response & Fire Services",
        number="101",
        description="Emergency fire fighting, vehicular rescue, building evacuation, and natural disaster management.",
        jurisdiction="Telangana Statewide",
        verified_authority="Telangana State Disaster Response and Fire Services Department",
        source_url="https://fire.telangana.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Direct hotline for fire outbreak and structural rescue emergencies.",
            "Connects to the nearest departmental fire station control room."
        ]
    ),
    EmergencyContact(
        service="Emergency Health & Medical Ambulance",
        number="108",
        description="24/7 emergency medical transit, paramedic care, and acute trauma transport to designated government/private hospitals.",
        jurisdiction="Telangana Statewide",
        verified_authority="Dept of Health, Medical & Family Welfare, Govt. of Telangana / GVK EMRI",
        source_url="https://health.telangana.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Free state emergency ambulance service operated under public-private partnership.",
            "Vehicle availability subject to geographic fleet positioning and triage urgency."
        ]
    ),
    EmergencyContact(
        service="SHE Teams / Women Safety Helpline",
        number="1090",
        description="Dedicated helpline and specialized patrol units for women distress assistance, harassment prevention, and safety in public spaces.",
        jurisdiction="Telangana Statewide",
        verified_authority="Women Safety Wing, Telangana State Police",
        source_url="https://womensafetywing.telangana.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Operated by specialized plainclothes and uniformed SHE Teams officers.",
            "Also accepts digital reports and WhatsApp distress messages via official departmental portals."
        ]
    ),
    EmergencyContact(
        service="National Cyber Crime Reporting Helpline",
        number="1930",
        description="Immediate emergency reporting of financial fraud, cyber extortion, unauthorized transactions, and online harassment.",
        jurisdiction="National / Telangana Cyber Security Bureau",
        verified_authority="Indian Cyber Crime Coordination Centre (I4C), MHA & Telangana State Police",
        source_url="https://cybercrime.gov.in",
        last_verified_at="2026-10-16",
        limitations=[
            "Financial fraud victims should call immediately within the initial transaction window to enable account freezing.",
            "Formal written report must subsequently be lodged on cybercrime.gov.in."
        ]
    )
]


class TelanganaSafetyProvider(CrimeProvider):
    """
    Dedicated Safety & Crime Intelligence Provider for Telangana State.
    Combines:
    1. Verified nearby police & fire infrastructure from local SQLite spatial dataset (telangana_places.db).
    2. Verified emergency assistance directory with official source citations.
    3. Police commissionerate / district jurisdiction identification where supported by verified boundary evidence.
    4. Truthful, transparent disclosure of unavailable locality-level crime statistics.
    """

    TELANGANA_BBOX = {
        "min_lat": 15.80,
        "max_lat": 19.92,
        "min_lng": 77.24,
        "max_lng": 81.35
    }

    def __init__(self, db_path: str | None = None, geojson_path: str | None = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")

        if db_path:
            self.db_path = db_path
        elif getattr(settings, "TELANGANA_PLACES_DB_PATH", None):
            self.db_path = os.path.abspath(settings.TELANGANA_PLACES_DB_PATH)
        else:
            self.db_path = os.path.join(data_dir, "telangana_places.db")

        self.geojson_path = geojson_path or os.path.join(data_dir, "telangana_districts.geojson")
        self._district_polygons: list[tuple[str, Any]] = []
        self._polygons_loaded: bool = False

    @property
    def name(self) -> str:
        return "Telangana Police & Emergency Infrastructure"

    @property
    def license(self) -> str:
        return "ODbL 1.0 / Open Government Data (OGD) Platform India"

    @property
    def attribution_url(self) -> str:
        return "https://tspolice.gov.in"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 20

    @property
    def capabilities(self) -> list[str]:
        return [
            "nearby_police",
            "nearby_fire",
            "emergency_directory",
            "jurisdiction_resolution",
            "crime_transparency"
        ]

    def is_point_in_telangana(self, lat: float, lng: float) -> bool:
        """Determines if the coordinates fall within the Telangana state geographic envelope."""
        return (
            self.TELANGANA_BBOX["min_lat"] <= lat <= self.TELANGANA_BBOX["max_lat"] and
            self.TELANGANA_BBOX["min_lng"] <= lng <= self.TELANGANA_BBOX["max_lng"]
        )

    def is_database_available(self) -> bool:
        """Checks if the local SQLite spatial database file exists."""
        return os.path.exists(self.db_path)

    def _load_district_polygons(self) -> None:
        if self._polygons_loaded:
            return
        if os.path.exists(self.geojson_path):
            try:
                with open(self.geojson_path, "r", encoding="utf-8") as f:
                    gj = json.load(f)
                for feat in gj.get("features", []):
                    dname = feat.get("properties", {}).get("district")
                    geom = feat.get("geometry")
                    if dname and geom:
                        self._district_polygons.append((dname, shape(geom)))
            except Exception as e:
                logger.error(f"Failed to load telangana_districts.geojson for jurisdiction matching: {e}")
        self._polygons_loaded = True

    def _resolve_district_name(self, lat: float, lng: float) -> str | None:
        self._load_district_polygons()
        pt = Point(lng, lat)
        for dname, poly in self._district_polygons:
            if poly.contains(pt):
                return dname
        for dname, poly in self._district_polygons:
            if poly.buffer(0.02).contains(pt):
                return dname
        return None

    def _resolve_jurisdiction(self, lat: float, lng: float) -> JurisdictionInfo:
        """
        Resolves police commissionerate or district police jurisdiction strictly where
        supported by official administrative boundaries.
        Returns explicit 'unavailable' when digital boundary evidence is unverified or overlapping.
        """
        dname = self._resolve_district_name(lat, lng)
        if not dname:
            return JurisdictionInfo(
                jurisdiction_name=None,
                jurisdiction_type="unavailable",
                supporting_authority=None,
                source_url=None,
                geographic_resolution=None,
                limitations=["Coordinates fall outside verified Telangana administrative boundary polygons."]
            )

        norm_d = dname.lower().replace(" ", "").replace("-", "")

        # 1. Hyderabad City Police Commissionerate (strictly coterminous with Hyderabad revenue district)
        if norm_d == "hyderabad":
            return JurisdictionInfo(
                jurisdiction_name="Hyderabad City Police Commissionerate",
                jurisdiction_type="commissionerate",
                supporting_authority="Telangana State Police",
                source_url="https://hyderabadpolice.gov.in",
                geographic_resolution="commissionerate",
                limitations=["Hyderabad City Police Commissionerate boundary corresponds to the core Hyderabad revenue district boundary."]
            )

        # 2. Capital Region Shared Districts: Ranga Reddy & Medchal-Malkajgiri
        # In these districts, police station beats are partitioned between Cyberabad and Rachakonda Commissionerates.
        # Since digital beat boundary shapefiles are not in public open data, report unavailable per section 2.4.
        if norm_d in ["rangareddy", "medchalmalkajgiri"]:
            return JurisdictionInfo(
                jurisdiction_name=None,
                jurisdiction_type="unavailable",
                supporting_authority="Telangana State Police",
                source_url="https://tspolice.gov.in",
                geographic_resolution="unavailable",
                limitations=[
                    f"Coordinates fall within {dname} district where police station jurisdictions divide between Cyberabad and Rachakonda Commissionerates.",
                    "Official open-data digital boundary shapefiles for individual police station beats are not published in public records; jurisdiction is marked unavailable to avoid misattribution."
                ]
            )

        # 3. Established Standalone Commissionerates in Telangana
        commissionerate_map = {
            "warangal": ("Warangal Police Commissionerate", "https://warangalpolice.telangana.gov.in"),
            "hanumakonda": ("Warangal Police Commissionerate", "https://warangalpolice.telangana.gov.in"),
            "karimnagar": ("Karimnagar Police Commissionerate", "https://karimnagarpolice.telangana.gov.in"),
            "nizamabad": ("Nizamabad Police Commissionerate", "https://nizamabadpolice.telangana.gov.in"),
            "khammam": ("Khammam Police Commissionerate", "https://khammampolice.telangana.gov.in"),
            "siddipet": ("Siddipet Police Commissionerate", "https://siddipetpolice.telangana.gov.in"),
            "peddapalli": ("Ramagundam Police Commissionerate", "https://tspolice.gov.in"),
            "mancherial": ("Ramagundam Police Commissionerate", "https://tspolice.gov.in"),
        }

        if norm_d in commissionerate_map:
            comm_name, comm_url = commissionerate_map[norm_d]
            return JurisdictionInfo(
                jurisdiction_name=comm_name,
                jurisdiction_type="commissionerate",
                supporting_authority="Telangana State Police",
                source_url=comm_url,
                geographic_resolution="commissionerate",
                limitations=[f"{comm_name} exercises police jurisdiction over urban and sub-divisional police station circles in {dname}."]
            )

        # 4. District Police Units (headed by Superintendent of Police - SP)
        return JurisdictionInfo(
            jurisdiction_name=f"{dname} District Police",
            jurisdiction_type="district_police",
            supporting_authority="Telangana State Police",
            source_url="https://tspolice.gov.in",
            geographic_resolution="district_police",
            limitations=[f"Superintendent of Police (SP) {dname} oversees police circles across {dname} revenue district."]
        )

    def _query_nearby_safety_facilities(
        self,
        lat: float,
        lng: float,
        radius_m: int = 3000
    ) -> list[SafetyFacility]:
        """
        Queries local SQLite database with R*Tree spatial indexing for verified police and fire stations.
        Applies strict haversine distance filtering and sort order.
        """
        buffered_radius_m = radius_m + 25
        delta_lat = buffered_radius_m / 111139.0
        cos_lat = math.cos(math.radians(lat))
        delta_lng = buffered_radius_m / (111139.0 * max(cos_lat, 0.01))

        min_lng = lng - delta_lng
        max_lng = lng + delta_lng
        min_lat = lat - delta_lat
        max_lat = lat + delta_lat

        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT p.id, p.name, p.category, p.subcategory, p.lat, p.lng, p.address
            FROM osm_places_rtree r
            JOIN osm_places p ON p.rowid = r.id_int
            WHERE r.max_lng >= ? AND r.min_lng <= ?
              AND r.max_lat >= ? AND r.min_lat <= ?
              AND p.category = 'safety_infrastructure'
        """
        cursor.execute(query, (min_lng, max_lng, min_lat, max_lat))
        rows = cursor.fetchall()
        conn.close()

        facilities: list[SafetyFacility] = []
        for r in rows:
            dist = haversine_distance_m(lat, lng, r["lat"], r["lng"])
            if dist > radius_m:
                continue

            subcat = r["subcategory"]
            if subcat not in ["police", "fire_station"]:
                subcat = "police"

            name = r["name"] or ("Police Station" if subcat == "police" else "Fire Station")

            facilities.append(SafetyFacility(
                id=r["id"],
                name=name,
                facility_type=subcat,
                lat=r["lat"],
                lng=r["lng"],
                distance_m=int(dist),
                distance_km=round(dist / 1000.0, 2),
                address=r["address"],
                source_name="OpenStreetMap (Telangana Statewide Extract)",
                source_attribution="https://www.openstreetmap.org/copyright"
            ))

        facilities.sort(key=lambda f: f.distance_m)
        return facilities[:self.max_results]

    def _get_verified_emergency_contacts(self) -> list[EmergencyContact]:
        """Returns the centralized, verified emergency assistance directory."""
        return list(VERIFIED_EMERGENCY_CONTACTS)

    async def get_safety_and_crime_data(
        self,
        lat: float,
        lng: float,
        radius_m: int = 3000
    ) -> ModuleResult[SafetyAndCrimeData]:
        """
        Main provider method combining:
        - Mapped emergency infrastructure from local spatial dataset
        - Verified emergency assistance directory
        - Police jurisdiction identification
        - Honest unavailable state for micro crime incident statistics
        """
        # Validate coordinates
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return ModuleResult[SafetyAndCrimeData](
                module="crime",
                status="error",
                provenance_kind="official_dataset",
                data=None,
                sources=[self.get_data_source_info()],
                coverage=Coverage(granularity="unknown", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=["Invalid geographic coordinates supplied."],
                message=f"Coordinates ({lat}, {lng}) are out of valid range [-90..90, -180..180]."
            )

        # Enforce geographic coverage boundary: Telangana state only
        if not self.is_point_in_telangana(lat, lng):
            return ModuleResult[SafetyAndCrimeData](
                module="crime",
                status="unavailable",
                provenance_kind="official_dataset",
                data=None,
                sources=[
                    DataSourceInfo(
                        name="National Crime Records Bureau (NCRB)",
                        url="https://ncrb.gov.in",
                        license="Open Government Data (OGD) Platform India",
                        attribution="NCRB Crime in India Publications"
                    )
                ],
                coverage=Coverage(
                    granularity="district",
                    radius_m=radius_m,
                    result_count=0,
                    note="Official crime statistics are aggregated at district or commissionerate levels."
                ),
                fetched_at=datetime.utcnow(),
                limitations=[
                    "Locality-level crime statistics are unavailable from integrated sources.",
                    "The specified coordinates fall outside Telangana state coverage.",
                    "Official NCRB datasets are compiled annually at police commissionerate / district boundaries and cannot be reliably attributed to individual neighborhoods.",
                    "The absence of published locality-level crime statistics does not imply that an area is safe."
                ],
                message="Coordinates are outside Telangana state coverage; locality-level crime statistics are unavailable."
            )

        # Check database availability
        if not self.is_database_available():
            return ModuleResult[SafetyAndCrimeData](
                module="crime",
                status="error",
                provenance_kind="official_dataset",
                data=None,
                sources=[self.get_data_source_info()],
                coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=["Local Telangana spatial database file not found at configured path."],
                message="Local Telangana places database is uninitialized or missing."
            )

        # Query facilities with error handling
        try:
            facilities = self._query_nearby_safety_facilities(lat, lng, radius_m=radius_m)
        except Exception as e:
            logger.error(f"Failed to query safety infrastructure from {self.db_path}: {e}")
            return ModuleResult[SafetyAndCrimeData](
                module="crime",
                status="error",
                provenance_kind="official_dataset",
                data=None,
                sources=[self.get_data_source_info()],
                coverage=Coverage(granularity="nearby_place", radius_m=radius_m, result_count=0),
                fetched_at=datetime.utcnow(),
                limitations=[f"Database query error: {type(e).__name__}"],
                message="Failed to query local safety infrastructure database."
            )

        # Retrieve verified emergency directory and jurisdiction
        emergency_contacts = self._get_verified_emergency_contacts()
        jurisdiction = self._resolve_jurisdiction(lat, lng)

        data = SafetyAndCrimeData(
            nearby_facilities=facilities,
            emergency_contacts=emergency_contacts,
            jurisdiction=jurisdiction,
            crime_statistics_status="unavailable",
            crime_disclosure_note=(
                "Verified locality-level crime statistics are not available in the connected public dataset. "
                "In India, official crime records (NCRB) are compiled at district or commissionerate level and "
                "cannot be reliably attributed to individual neighborhoods."
            ),
            absence_caveat="The absence of published locality-level crime statistics does not imply that an area is safe.",
            incident_count=None,
            rate_per_100k=None,
            data_granularity="district",
            reporting_year=None,
            source_agency=None
        )

        sources = [
            DataSourceInfo(
                name="OpenStreetMap (Telangana Statewide Extract)",
                url="https://www.openstreetmap.org/copyright",
                license="ODbL 1.0",
                attribution="Data © OpenStreetMap contributors under ODbL"
            ),
            DataSourceInfo(
                name="Telangana State Police & Emergency Services",
                url="https://tspolice.gov.in",
                license="Government Open Data",
                attribution="Telangana State Police & Emergency Services Directory"
            ),
            DataSourceInfo(
                name="National Crime Records Bureau (NCRB)",
                url="https://ncrb.gov.in",
                license="Open Government Data (OGD) Platform India",
                attribution="NCRB Crime in India Annual Publications"
            )
        ]

        nearest_dist = facilities[0].distance_m if facilities else None

        return ModuleResult[SafetyAndCrimeData](
            module="crime",
            status="available",
            provenance_kind="official_dataset",
            data=data,
            sources=sources,
            coverage=Coverage(
                granularity="nearby_place",
                radius_m=radius_m,
                result_count=len(facilities),
                nearest_distance_m=nearest_dist,
                note="Nearby emergency facilities retrieved from local spatial database; crime statistics compiled at macro tier."
            ),
            fetched_at=datetime.utcnow(),
            limitations=[
                "Locality-level crime statistics are unavailable from integrated sources.",
                "Official NCRB and police datasets are aggregated at district or commissionerate level and cannot be attributed to micro-neighborhoods.",
                "OpenStreetMap facility listings may be incomplete and do not confirm real-time operational staffing or immediate unit availability.",
                "The absence of published locality-level crime statistics does not imply that an area is safe."
            ],
            message="Safety infrastructure and emergency directory retrieved; locality-level crime statistics remain unavailable."
        )

    async def get_crime_data(self, lat: float, lng: float) -> ModuleResult[CrimeData]:
        """Backwards compatibility implementation of CrimeProvider abstract method."""
        res = await self.get_safety_and_crime_data(lat, lng, radius_m=3000)
        return res  # SafetyAndCrimeData is a subclass of CrimeData


# Module-level default
DefaultCrimeProvider = TelanganaSafetyProvider
