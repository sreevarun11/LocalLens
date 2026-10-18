"""
LocalLens — Telangana-Wide OpenStreetMap Places Database Builder.
Downloads, verifies, extracts, and indexes all 6 facility categories
across the entire state of Telangana, India into an SQLite R*Tree database.
"""

import os
import sys
import json
import hashlib
import sqlite3
import urllib.request
import logging
from datetime import datetime
from typing import Literal

import osmium
import shapely.wkb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("build_telangana_db")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data")
TMP_DIR = os.path.join(DATA_DIR, "tmp")
DB_PATH = os.path.join(DATA_DIR, "telangana_places.db")
TMP_DB_PATH = os.path.join(DATA_DIR, "telangana_places.db.tmp")
PBF_PATH = os.path.join(TMP_DIR, "telangana.osm.pbf")
DOWNLOAD_PBF_PATH = os.path.join(TMP_DIR, "telangana.osm.pbf.download")

PBF_URL = "https://download.openstreetmap.fr/extracts/asia/india/telangana.osm.pbf"
MD5_URL = "https://download.openstreetmap.fr/extracts/asia/india/telangana.osm.pbf.md5"
STATE_URL = "https://download.openstreetmap.fr/extracts/asia/india/telangana.state.txt"

# Expected Telangana geographic bounding envelope
TELANGANA_BBOX = {
    "min_lat": 15.80,
    "max_lat": 19.92,
    "min_lng": 77.24,
    "max_lng": 81.32
}

CATEGORIES = [
    "healthcare",
    "education",
    "safety_infrastructure",
    "daily_life",
    "transport",
    "lifestyle"
]


def map_osm_tags(tags) -> tuple[str | None, str | None]:
    """
    Maps OSM tags to one of the 6 defined categories and subcategory.
    """
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")
    shop = tags.get("shop", "")
    leisure = tags.get("leisure", "")
    highway = tags.get("highway", "")
    railway = tags.get("railway", "")
    public_transport = tags.get("public_transport", "")
    building = tags.get("building", "")

    # 1. Healthcare
    if (
        amenity in ("hospital", "clinic", "pharmacy", "doctors", "dentist", "health_post", "nursing_home") or
        healthcare in ("hospital", "clinic", "centre", "doctor", "pharmacy", "alternative", "laboratory") or
        shop == "chemist"
    ):
        subcat = amenity or healthcare or shop
        return "healthcare", subcat

    # 2. Education
    if (
        amenity in ("school", "college", "university", "kindergarten") or
        building in ("school", "college", "university", "kindergarten")
    ):
        subcat = amenity or building
        return "education", subcat

    # 3. Safety Infrastructure
    if amenity in ("police", "fire_station"):
        return "safety_infrastructure", amenity

    # 4. Daily Essentials
    if (
        shop in ("supermarket", "convenience", "grocery", "greengrocer", "general", "department_store", "dairy", "bakery", "butcher") or
        amenity in ("marketplace", "bank", "atm", "fuel")
    ):
        subcat = shop or amenity
        return "daily_life", subcat

    # 5. Connectivity
    if (
        highway == "bus_stop" or
        amenity == "bus_station" or
        railway in ("station", "halt", "subway_entrance") or
        public_transport in ("stop_position", "platform", "station")
    ):
        subcat = railway or highway or amenity or public_transport
        return "transport", subcat

    # 6. Lifestyle
    if (
        leisure in ("park", "playground", "garden", "sports_centre", "fitness_centre", "pitch", "swimming_pool", "nature_reserve") or
        amenity in ("community_centre", "library", "cafe", "restaurant", "fast_food", "theatre", "cinema")
    ):
        subcat = leisure or amenity
        return "lifestyle", subcat

    return None, None


def verify_remote_metadata() -> dict:
    """Verifies the remote dataset headers, MD5 checksum file, and state timestamp."""
    logger.info("Checking remote OpenStreetMap metadata...")
    headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}

    # 1. Check HEAD on PBF URL
    req = urllib.request.Request(PBF_URL, headers=headers, method="HEAD")
    with urllib.request.urlopen(req, timeout=15) as resp:
        content_length = int(resp.headers.get("Content-Length", 0))
        last_modified = resp.headers.get("Last-Modified", "Unknown")
        etag = resp.headers.get("ETag", "Unknown")

    logger.info(f"Remote PBF Size: {content_length:,} bytes ({content_length / (1024*1024):.1f} MB)")
    logger.info(f"Remote PBF Last-Modified: {last_modified}, ETag: {etag}")

    # 2. Check MD5 checksum file
    req_md5 = urllib.request.Request(MD5_URL, headers=headers)
    with urllib.request.urlopen(req_md5, timeout=15) as resp:
        md5_text = resp.read().decode("utf-8").strip()
        expected_md5 = md5_text.split()[0]
    logger.info(f"Remote MD5 Checksum: {expected_md5}")

    # 3. Check state timestamp file
    req_state = urllib.request.Request(STATE_URL, headers=headers)
    state_meta = {}
    with urllib.request.urlopen(req_state, timeout=15) as resp:
        for line in resp.read().decode("utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                state_meta[k.strip()] = v.strip().replace(r"\:", ":")
    logger.info(f"Remote State Metadata: {state_meta}")

    return {
        "content_length": content_length,
        "last_modified": last_modified,
        "etag": etag,
        "expected_md5": expected_md5,
        "state_meta": state_meta
    }


def download_with_checksum(meta: dict):
    """Downloads the PBF extract and verifies its MD5 checksum."""
    os.makedirs(TMP_DIR, exist_ok=True)

    # Check if existing verified PBF is present and matches MD5
    if os.path.exists(PBF_PATH):
        logger.info("Existing PBF file found. Verifying checksum...")
        hasher = hashlib.md5()
        with open(PBF_PATH, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        if hasher.hexdigest().lower() == meta["expected_md5"].lower():
            logger.info("Existing PBF matches expected MD5. Skipping download.")
            return
        else:
            logger.info("Existing PBF does not match current remote MD5. Re-downloading...")

    logger.info(f"Downloading {PBF_URL} to {DOWNLOAD_PBF_PATH}...")
    headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}
    req = urllib.request.Request(PBF_URL, headers=headers)

    hasher = hashlib.md5()
    total_bytes = meta["content_length"]
    downloaded = 0
    last_reported = 0

    with urllib.request.urlopen(req, timeout=30) as resp, open(DOWNLOAD_PBF_PATH, "wb") as out_f:
        while chunk := resp.read(256 * 1024):
            out_f.write(chunk)
            hasher.update(chunk)
            downloaded += len(chunk)
            percent = (downloaded / total_bytes) * 100 if total_bytes else 0
            if percent - last_reported >= 10:
                logger.info(f"Download progress: {downloaded:,} / {total_bytes:,} bytes ({percent:.1f}%)")
                last_reported = percent

    downloaded_md5 = hasher.hexdigest().lower()
    logger.info(f"Download complete. Computed MD5: {downloaded_md5}")

    if downloaded_md5 != meta["expected_md5"].lower():
        if os.path.exists(DOWNLOAD_PBF_PATH):
            os.remove(DOWNLOAD_PBF_PATH)
        raise ValueError(
            f"MD5 mismatch! Expected: {meta['expected_md5']}, got: {downloaded_md5}"
        )

    # Move verified download to final PBF_PATH
    if os.path.exists(PBF_PATH):
        os.remove(PBF_PATH)
    os.rename(DOWNLOAD_PBF_PATH, PBF_PATH)
    logger.info(f"PBF verified and saved to {PBF_PATH}")


class TelanganaFacilityCollector(osmium.SimpleHandler):
    """
    Osmium handler that collects genuine facilities across Telangana.
    Uses geometry-aware coordinate derivation (representative points on polygons).
    """
    def __init__(self):
        super().__init__()
        self.wkbf = osmium.geom.WKBFactory()
        self.facilities: list[dict] = []
        self.min_lat = 90.0
        self.max_lat = -90.0
        self.min_lng = 180.0
        self.max_lng = -180.0
        self.state_boundary_found = False
        self.category_counts = {c: 0 for c in CATEGORIES}

    def _record_point(self, lat: float, lng: float):
        if lat < self.min_lat: self.min_lat = lat
        if lat > self.max_lat: self.max_lat = lat
        if lng < self.min_lng: self.min_lng = lng
        if lng > self.max_lng: self.max_lng = lng

    def node(self, n):
        cat, subcat = map_osm_tags(n.tags)
        if not cat:
            return

        if not n.location.valid():
            return

        lat = n.location.lat
        lng = n.location.lon

        # Check inside Telangana geographic envelope
        if not (TELANGANA_BBOX["min_lat"] - 0.1 <= lat <= TELANGANA_BBOX["max_lat"] + 0.1 and
                TELANGANA_BBOX["min_lng"] - 0.1 <= lng <= TELANGANA_BBOX["max_lng"] + 0.1):
            return

        self._record_point(lat, lng)

        name = n.tags.get("name")
        display_name = name or f"Unnamed {subcat.replace('_', ' ').title() if subcat else cat.replace('_', ' ').title()}"
        address = n.tags.get("addr:full") or n.tags.get("addr:street")

        self.facilities.append({
            "id": f"osm_node_{n.id}",
            "name": display_name,
            "category": cat,
            "subcategory": subcat,
            "lat": lat,
            "lng": lng,
            "address": address,
            "osm_type": "node",
            "osm_id": n.id,
            "tags_json": json.dumps(dict(n.tags))
        })
        self.category_counts[cat] += 1

    def way(self, w):
        cat, subcat = map_osm_tags(w.tags)
        if not cat:
            return

        # Geometry-aware coordinate derivation:
        lat, lng = None, None
        try:
            if w.is_closed():
                # Closed polygon (building, campus, park, etc.)
                try:
                    wkb = self.wkbf.create_multipolygon(w)
                    geom = shapely.wkb.loads(bytes.fromhex(wkb))
                    # Representative point is guaranteed to be within the geometry surface
                    pt = geom.representative_point()
                    lat, lng = pt.y, pt.x
                except Exception:
                    wkb = self.wkbf.create_linestring(w)
                    geom = shapely.wkb.loads(bytes.fromhex(wkb))
                    pt = geom.representative_point()
                    lat, lng = pt.y, pt.x
            else:
                wkb = self.wkbf.create_linestring(w)
                geom = shapely.wkb.loads(bytes.fromhex(wkb))
                pt = geom.representative_point()
                lat, lng = pt.y, pt.x
        except Exception:
            # Fallback to mean of valid node locations
            valid_coords = [(n.lat, n.lon) for n in w.nodes if n.valid()]
            if valid_coords:
                lat = sum(c[0] for c in valid_coords) / len(valid_coords)
                lng = sum(c[1] for c in valid_coords) / len(valid_coords)

        if lat is None or lng is None:
            return

        if not (TELANGANA_BBOX["min_lat"] - 0.1 <= lat <= TELANGANA_BBOX["max_lat"] + 0.1 and
                TELANGANA_BBOX["min_lng"] - 0.1 <= lng <= TELANGANA_BBOX["max_lng"] + 0.1):
            return

        self._record_point(lat, lng)

        name = w.tags.get("name")
        display_name = name or f"Unnamed {subcat.replace('_', ' ').title() if subcat else cat.replace('_', ' ').title()}"
        address = w.tags.get("addr:full") or w.tags.get("addr:street")

        self.facilities.append({
            "id": f"osm_way_{w.id}",
            "name": display_name,
            "category": cat,
            "subcategory": subcat,
            "lat": lat,
            "lng": lng,
            "address": address,
            "osm_type": "way",
            "osm_id": w.id,
            "tags_json": json.dumps(dict(w.tags))
        })
        self.category_counts[cat] += 1

    def relation(self, r):
        # Check for Telangana state boundary relation
        if r.tags.get("admin_level") == "4" and "Telangana" in (r.tags.get("name:en") or r.tags.get("name") or ""):
            self.state_boundary_found = True


def build_sqlite_database(collector: TelanganaFacilityCollector, meta: dict):
    """
    Builds the temporary SQLite database with R*Tree index and metadata.
    """
    if os.path.exists(TMP_DB_PATH):
        os.remove(TMP_DB_PATH)

    logger.info(f"Building temporary database at {TMP_DB_PATH}...")
    conn = sqlite3.connect(TMP_DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    PRAGMA synchronous = OFF;
    PRAGMA journal_mode = MEMORY;

    CREATE TABLE IF NOT EXISTS osm_places (
        id TEXT PRIMARY KEY,
        name TEXT,
        category TEXT NOT NULL,
        subcategory TEXT,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        address TEXT,
        osm_type TEXT NOT NULL,
        osm_id INTEGER NOT NULL,
        tags_json TEXT
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS osm_places_rtree USING rtree(
        id_int,
        min_lng, max_lng,
        min_lat, max_lat
    );

    CREATE TABLE IF NOT EXISTS dataset_metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Strict, safe deduplication:
    # 1. Reject identical OSM entities (same osm_type + osm_id).
    # 2. Only merge cross-type duplicates (a node POI inside a way building polygon)
    #    if they share identical non-empty normalized name, category, subcategory, and distance < 15m.
    # 3. NEVER merge two nodes (preserving opposite-direction bus stops, adjacent ATMs, etc.).
    # 4. NEVER merge facilities with different names or categories.
    seen_osm_ids = set()
    # Track existing ways by (category, subcategory, norm_name) -> list of (lat, lng)
    seen_way_facilities: dict[tuple[str, str, str], list[tuple[float, float]]] = {}
    seen_unnamed_ways: dict[tuple[str, str], list[tuple[float, float]]] = {}

    places_batch = []
    rtree_batch = []
    row_id = 1

    # First pass: index ways so node POIs can check for duplicate building representations
    for f in collector.facilities:
        if f["osm_type"] == "way":
            name = f["name"].strip()
            if not name.startswith("Unnamed "):
                key = (f["category"], f["subcategory"] or "", name.lower())
                seen_way_facilities.setdefault(key, []).append((f["lat"], f["lng"]))
            else:
                key = (f["category"], f["subcategory"] or "")
                seen_unnamed_ways.setdefault(key, []).append((f["lat"], f["lng"]))

    for f in collector.facilities:
        fid = f["id"]
        if fid in seen_osm_ids:
            continue
        seen_osm_ids.add(fid)

        # If this is a node, check if it duplicates an already-represented way building polygon
        if f["osm_type"] == "node":
            name = f["name"].strip()
            cat = f["category"]
            subcat = f["subcategory"] or ""
            lat, lng = f["lat"], f["lng"]

            if not name.startswith("Unnamed "):
                way_key = (cat, subcat, name.lower())
                if way_key in seen_way_facilities:
                    # Check if within 15 meters of the building way centroid
                    is_dup_way = any(
                        abs(lat - w_lat) < 0.00015 and abs(lng - w_lng) < 0.00015
                        for w_lat, w_lng in seen_way_facilities[way_key]
                    )
                    if is_dup_way:
                        continue
            else:
                unnamed_way_key = (cat, subcat)
                if unnamed_way_key in seen_unnamed_ways:
                    # Check if within 5 meters of the unnamed building way centroid
                    is_dup_unnamed = any(
                        abs(lat - w_lat) < 0.00005 and abs(lng - w_lng) < 0.00005
                        for w_lat, w_lng in seen_unnamed_ways[unnamed_way_key]
                    )
                    if is_dup_unnamed:
                        continue

        # Explicitly assign rowid to guarantee 1:1 match with rtree.id_int
        places_batch.append((
            row_id, f["id"], f["name"], f["category"], f["subcategory"],
            f["lat"], f["lng"], f["address"], f["osm_type"], f["osm_id"], f["tags_json"]
        ))
        rtree_batch.append((
            row_id, f["lng"], f["lng"], f["lat"], f["lat"]
        ))
        row_id += 1

        if len(places_batch) >= 10000:
            cursor.executemany(
                "INSERT INTO osm_places (rowid, id, name, category, subcategory, lat, lng, address, osm_type, osm_id, tags_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                places_batch
            )
            cursor.executemany(
                "INSERT INTO osm_places_rtree (id_int, min_lng, max_lng, min_lat, max_lat) VALUES (?, ?, ?, ?, ?)",
                rtree_batch
            )
            places_batch.clear()
            rtree_batch.clear()

    if places_batch:
        cursor.executemany(
            "INSERT INTO osm_places (rowid, id, name, category, subcategory, lat, lng, address, osm_type, osm_id, tags_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            places_batch
        )
        cursor.executemany(
            "INSERT INTO osm_places_rtree (id_int, min_lng, max_lng, min_lat, max_lat) VALUES (?, ?, ?, ?, ?)",
            rtree_batch
        )

    # Insert metadata
    metadata = {
        "dataset_source": PBF_URL,
        "dataset_timestamp": meta.get("state_meta", {}).get("timestamp", "Unknown"),
        "sequence_number": meta.get("state_meta", {}).get("sequenceNumber", "Unknown"),
        "md5_checksum": meta.get("expected_md5", "Unknown"),
        "total_facilities": str(row_id - 1),
        "build_timestamp": datetime.utcnow().isoformat(),
        "license": "Open Database License (ODbL) 1.0",
        "attribution": "Data (c) OpenStreetMap contributors",
        "coverage_bbox": json.dumps({
            "min_lat": collector.min_lat,
            "max_lat": collector.max_lat,
            "min_lng": collector.min_lng,
            "max_lng": collector.max_lng
        }),
        "category_counts": json.dumps(collector.category_counts),
        "state_boundary_verified": str(collector.state_boundary_found)
    }

    for k, v in metadata.items():
        cursor.execute("INSERT INTO dataset_metadata (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()
    logger.info(f"Temporary database built with {row_id - 1:,} facilities.")


def validate_database() -> bool:
    """
    Validates the temporary database integrity and tests the 3 statewide locations:
    1. Hyderabad (urban)
    2. Warangal (town)
    3. Alampur (rural)
    """
    logger.info("Validating temporary database...")
    conn = sqlite3.connect(TMP_DB_PATH)
    cursor = conn.cursor()

    # 1. Integrity check
    cursor.execute("PRAGMA integrity_check;")
    check = cursor.fetchone()[0]
    if check != "ok":
        logger.error(f"PRAGMA integrity_check failed: {check}")
        conn.close()
        return False

    # 2. Total count check
    cursor.execute("SELECT COUNT(*) FROM osm_places;")
    count = cursor.fetchone()[0]
    logger.info(f"Validated total facilities: {count:,}")
    if count < 20000:
        logger.error(f"Facility count too low ({count})!")
        conn.close()
        return False

    # 3. Category count check
    cursor.execute("SELECT category, COUNT(*) FROM osm_places GROUP BY category;")
    cat_counts = dict(cursor.fetchall())
    logger.info(f"Category distribution: {cat_counts}")
    for cat in CATEGORIES:
        if cat_counts.get(cat, 0) == 0:
            logger.error(f"Missing records for category: {cat}")
            conn.close()
            return False

    # 4. Spot check test locations
    test_locations = [
        ("Hyderabad (Charminar)", 17.3616, 78.4747, 1500),
        ("Warangal (Hanamkonda)", 17.9784, 79.5941, 2000),
        ("Alampur (Jogulamba Gadwal)", 15.8778, 78.1311, 2500)
    ]

    for name, lat, lng, rad in test_locations:
        delta_lat = rad / 111139.0
        delta_lng = rad / (111139.0 * 0.95)
        cursor.execute("""
            SELECT p.id, p.name, p.category, p.lat, p.lng
            FROM osm_places_rtree r
            JOIN osm_places p ON p.rowid = r.id_int
            WHERE r.min_lng >= ? AND r.max_lng <= ?
              AND r.min_lat >= ? AND r.max_lat <= ?
            LIMIT 10;
        """, (lng - delta_lng, lng + delta_lng, lat - delta_lat, lat + delta_lat))
        results = cursor.fetchall()
        logger.info(f"Test query [{name}]: found {len(results)} sample facilities within bounding box.")
        if len(results) == 0:
            logger.warning(f"No sample facilities returned for {name}! (Check bounding box parameters)")

    conn.close()
    return True


def atomic_replace():
    """Safely replaces the active database with the validated temporary database."""
    logger.info(f"Replacing active database {DB_PATH} with validated {TMP_DB_PATH}...")
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(DB_PATH, backup_path)
    os.rename(TMP_DB_PATH, DB_PATH)
    logger.info(f"[SUCCESS] Telangana places database active at {DB_PATH}!")


def main():
    logger.info("=== Starting Telangana Places Database Build ===")
    meta = verify_remote_metadata()
    download_with_checksum(meta)

    logger.info("Parsing OSM PBF extract with Osmium...")
    collector = TelanganaFacilityCollector()
    collector.apply_file(PBF_PATH, locations=True, idx="flex_mem")

    logger.info(f"Parsing complete. Extracted {len(collector.facilities):,} facilities.")
    logger.info(f"Geographic Extents: Lat [{collector.min_lat:.4f}, {collector.max_lat:.4f}], Lng [{collector.min_lng:.4f}, {collector.max_lng:.4f}]")
    logger.info(f"State Boundary Relation Found: {collector.state_boundary_found}")
    logger.info(f"Category Summary: {collector.category_counts}")

    build_sqlite_database(collector, meta)

    if not validate_database():
        logger.error("Validation failed! Aborting database replacement.")
        if os.path.exists(TMP_DB_PATH):
            os.remove(TMP_DB_PATH)
        sys.exit(1)

    atomic_replace()
    logger.info("=== Build and Validation Completed Successfully ===")


if __name__ == "__main__":
    main()
