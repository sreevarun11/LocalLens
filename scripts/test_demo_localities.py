import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()

localities = [
    {"name": "Locality A (Rich data)", "query": "Koramangala, Bengaluru"},
    {"name": "Locality B (Comparable)", "query": "Indiranagar, Bengaluru"},
    {"name": "Locality C (Data gaps)", "query": "Chandapura, Bengaluru"}
]

print("=== AUDITING DEMO LOCALITIES ===")

for loc in localities:
    q = loc["query"]
    print(f"\n--- {loc['name']}: '{q}' ---")
    
    # 1. Geocoding via Photon
    photon_url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=1"
    lat, lng = None, None
    try:
        req = urllib.request.Request(photon_url, headers={'User-Agent': 'LocalLens-Audit/1.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            feats = data.get("features", [])
            if feats:
                coords = feats[0]["geometry"]["coordinates"] # [lng, lat]
                lng, lat = coords[0], coords[1]
                props = feats[0]["properties"]
                print(f"Photon Geocode: lat={lat:.4f}, lng={lng:.4f}, name={props.get('name')}, city={props.get('city')}")
            else:
                print("Photon Geocode: No features found")
    except Exception as e:
        print(f"Photon Geocode error: {e}")

    if lat and lng:
        # 2. Open-Meteo Air Quality
        om_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&current=pm10,pm2_5,european_aqi,us_aqi"
        try:
            req = urllib.request.Request(om_url, headers={'User-Agent': 'LocalLens-Audit/1.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                curr = data.get("current", {})
                print(f"Open-Meteo AQ: US AQI={curr.get('us_aqi')}, PM2.5={curr.get('pm2_5')} ug/m3, PM10={curr.get('pm10')} ug/m3")
        except Exception as e:
            print(f"Open-Meteo error: {e}")
            
        # 3. Overpass OSM Places count (Schools and Hospitals within 1500m)
        op_q = f"""[out:json][timeout:15];
(
  node["amenity"~"school|hospital|clinic|pharmacy"](around:1500,{lat},{lng});
);
out count;"""
        try:
            req = urllib.request.Request(
                "https://z.overpass-api.de/api/interpreter",
                data=urllib.parse.urlencode({'data': op_q}).encode('utf-8'),
                headers={'User-Agent': 'LocalLens-Audit/1.0'}
            )
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                elems = data.get("elements", [])
                total = elems[0].get("tags", {}).get("total", "0") if elems else "0"
                print(f"Overpass OSM Amenity Count (1500m): {total}")
        except Exception as e:
            print(f"Overpass error: {e}")
