import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()

def test_endpoint(name, url, headers=None):
    print(f"\n--- Testing: {name} ---")
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'LocalLens-Audit/1.0 (contact: audit@locallens.app)'})
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            code = resp.getcode()
            body = resp.read().decode('utf-8', errors='replace')
            print(f"STATUS: {code}")
            try:
                parsed = json.loads(body)
                print(f"RESPONSE JSON keys / summary: {list(parsed.keys()) if isinstance(parsed, dict) else len(parsed)}")
                if isinstance(parsed, dict):
                    for k in list(parsed.keys())[:4]:
                        val = str(parsed[k])
                        print(f"  {k}: {val[:120]}")
                elif isinstance(parsed, list) and len(parsed) > 0:
                    print(f"  First item: {str(parsed[0])[:120]}")
            except Exception:
                print(f"BODY (text): {body[:200]}")
            return True
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR: {e.code} - {e.reason}")
        err_body = e.read().decode('utf-8', errors='replace')[:250]
        print(f"Error body: {err_body}")
        return False
    except Exception as e:
        print(f"REQUEST FAILED: {type(e).__name__}: {e}")
        return False

# 1. Open-Meteo Air Quality
test_endpoint(
    "Open-Meteo Air Quality (Koramangala 12.9352, 77.6245)",
    "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=12.9352&longitude=77.6245&current=pm10,pm2_5,european_aqi,us_aqi"
)

# 2. OpenAQ v3 API
test_endpoint(
    "OpenAQ v3 API (Public without key)",
    "https://api.openaq.org/v3/locations?coordinates=12.9352,77.6245&radius=25000"
)

# 3. Overpass API de
overpass_q = """[out:json][timeout:10];
(
  node["amenity"="school"](around:1000,12.9352,77.6245);
  way["amenity"="school"](around:1000,12.9352,77.6245);
);
out center 5;"""
test_endpoint(
    "Overpass API (overpass-api.de)",
    "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(overpass_q)
)

# 4. Overpass API kumi mirror
test_endpoint(
    "Overpass API (kumi mirror)",
    "https://overpass.kumi.systems/api/interpreter?data=" + urllib.parse.quote(overpass_q)
)

# 5. Nominatim OpenStreetMap (search)
test_endpoint(
    "Nominatim Search (OSM)",
    "https://nominatim.openstreetmap.org/search?q=Koramangala+Bengaluru&format=json&limit=1"
)

# 6. Photon Komoot Geocoder
test_endpoint(
    "Photon Geocoder (komoot)",
    "https://photon.komoot.io/api/?q=Koramangala+Bengaluru&limit=2"
)
