import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()

endpoints = [
    'https://overpass-api.de/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter',
    'https://z.overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter'
]

# Simple query for Koramangala
query = '[out:json][timeout:20];node["amenity"="school"](around:1000,12.9352,77.6245);out 5;'
encoded_data = urllib.parse.urlencode({'data': query}).encode('utf-8')

for ep in endpoints:
    print(f"Trying {ep}...")
    try:
        req = urllib.request.Request(
            ep,
            data=encoded_data,
            headers={'User-Agent': 'LocalLens-Test/1.0 (contact: info@locallens.app)'}
        )
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            raw = resp.read().decode('utf-8')
            res = json.loads(raw)
            elements = res.get("elements", [])
            print(f"SUCCESS {ep}: found {len(elements)} elements")
            if elements:
                print("Sample element:", elements[0].get("tags", {}).get("name", "unnamed"))
    except Exception as e:
        print(f"FAILED {ep}: {e}")
