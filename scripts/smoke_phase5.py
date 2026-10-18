import urllib.request
import json
import uuid

def post(url, data, headers=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json', **(headers or {})},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method='GET')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

print("=== 1. Check Profiles Endpoint ===")
profiles = get('http://127.0.0.1:8000/api/insights/profiles')
print(f"Profiles count: {len(profiles['profiles'])}")
for p in profiles['profiles']:
    print(f"  Profile: {p['id']} -> Defaults: {p['defaults']}")

print("\n=== 2. Check Charminar (Family Profile) ===")
charminar_places = get('http://127.0.0.1:8000/api/modules/places?lat=17.3616&lng=78.4747&radius_m=1500')
charminar_env = get('http://127.0.0.1:8000/api/modules/environment?lat=17.3616&lng=78.4747')
charminar_water = get('http://127.0.0.1:8000/api/modules/water?lat=17.3616&lng=78.4747&locality=Charminar')
charminar_safety = get('http://127.0.0.1:8000/api/modules/safety?lat=17.3616&lng=78.4747&radius_m=1500')

insights_payload = {
    'locality_key': 'charminar',
    'profile': 'family',
    'priorities': ['education', 'healthcare', 'transport', 'safety_infrastructure', 'water'],
    'places': charminar_places,
    'environment': charminar_env,
    'water': charminar_water,
    'crime': charminar_safety
}
insights_res = post('http://127.0.0.1:8000/api/insights', insights_payload)
print(f"Findings returned: {len(insights_res['findings'])}")
for f in insights_res['findings']:
    print(f"  • [{f['priority']}] ({f['status']}) {f['headline']}")
    print(f"    Detail: {f['detail'][:110]}...")
print(f"Evidence items: {len(insights_res['evidence_items'])}")
print(f"Gaps: {len(insights_res['gaps'])}")
for g in insights_res['gaps']:
    print(f"  - [{g['module']}] ({g['status']}) {g['reason'][:90]}...")
print(f"Verify on site questions: {len(insights_res['verify_on_site'])}")

print("\n=== 3. Check Gachibowli (Commuter Profile) ===")
gachi_places = get('http://127.0.0.1:8000/api/modules/places?lat=17.4401&lng=78.3489&radius_m=1500')
gachi_commute = post('http://127.0.0.1:8000/api/modules/commute', {
    'origin': {'lat': 17.4401, 'lng': 78.3489},
    'destination_coords': {'lat': 17.4504, 'lng': 78.3808},
    'destination_query': 'HITEC City'
})
gachi_safety = get('http://127.0.0.1:8000/api/modules/safety?lat=17.4401&lng=78.3489&radius_m=1500')

gachi_insights = post('http://127.0.0.1:8000/api/insights', {
    'locality_key': 'gachibowli',
    'profile': 'commuter',
    'priorities': ['transport', 'commute', 'daily_life', 'safety_infrastructure'],
    'places': gachi_places,
    'crime': gachi_safety,
    'commute': gachi_commute
})
print(f"Findings returned: {len(gachi_insights['findings'])}")
for f in gachi_insights['findings']:
    print(f"  • [{f['priority']}] ({f['status']}) {f['headline']}")

print("\n=== 4. Check Out-of-Coverage Location: Bengaluru ===")
blr_water = get('http://127.0.0.1:8000/api/modules/water?lat=12.9716&lng=77.5946&locality=Bengaluru')
blr_safety = get('http://127.0.0.1:8000/api/modules/safety?lat=12.9716&lng=77.5946&radius_m=1500')

blr_insights = post('http://127.0.0.1:8000/api/insights', {
    'locality_key': 'bengaluru',
    'profile': 'home_buyer',
    'priorities': ['water', 'safety_infrastructure'],
    'water': blr_water,
    'crime': blr_safety
})
print(f"Bengaluru Findings:")
for f in blr_insights['findings']:
    print(f"  • [{f['priority']}] ({f['status']}) {f['headline']}")
    print(f"    Detail: {f['detail']}")

print("\n=== 5. Check Live Report Generation, PDF Download, and QR Verification ===")
user_email = 'stage5_verifier@example.com'
try:
    reg = post('http://127.0.0.1:8000/api/auth/register', {
        'email': user_email,
        'password': 'Password123!',
        'display_name': 'Phase 5 Verifier'
    })
    token = reg['access_token']
except Exception:
    login = post('http://127.0.0.1:8000/api/auth/login', {
        'email': user_email,
        'password': 'Password123!'
    })
    token = login['access_token']

auth_headers = {'Authorization': f'Bearer {token}'}
post('http://127.0.0.1:8000/api/auth/verify-email-simulate', {}, headers=auth_headers)

gen_res = post('http://127.0.0.1:8000/api/reports/generate', {
    'locality_name': 'Gachibowli, Hyderabad',
    'lat': 17.4401,
    'lng': 78.3489,
    'user_profile': 'family',
    'user_priorities': ['education', 'healthcare', 'transport', 'safety_infrastructure', 'water'],
    'property_context': {
        'property_address': 'Flat 302, Phase 5 Tower',
        'rent_or_price': '42,000'
    }
}, headers=auth_headers)

print(f"Generated Report ID: {gen_res['id']}")
print(f"Verification Hash: {gen_res['verification_hash'][:30]}...")
print(f"PDF URL: {gen_res['pdf_url']}")

pdf_url = f"http://127.0.0.1:8000{gen_res['pdf_url']}"
pdf_req = urllib.request.Request(pdf_url, headers=auth_headers)
with urllib.request.urlopen(pdf_req) as resp:
    pdf_bytes = resp.read()
    print(f"PDF Download HTTP {resp.status}: Size {len(pdf_bytes)} bytes")

verify_res = get(f"http://127.0.0.1:8000/api/reports/verify/{gen_res['id']}")
print(f"Public Verification HTTP 200: Status={verify_res['status']} | CertifiedBy={verify_res['certified_by']}")
print(f"Integrity Status: {verify_res['integrity_status']}")

print("\n=== Smoke Test Complete ===")
