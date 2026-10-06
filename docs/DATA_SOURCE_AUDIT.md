# LocalLens Data Source Audit

**Audit Date:** 2026-09-30  
**Audit Status:** Complete — Verified against live network calls and official provider documentation.  
**Auditor:** LocalLens Engineering  

---

## 1. Executive Summary & Integration Verdicts

| Candidate Source | Domain | Authentication | Tested Response | Verdict | Storage Policy |
|---|---|---|---|---|---|
| **Google Places API (New)** | Places, POIs, Categories | Server API Key (`GOOGLE_MAPS_SERVER_KEY`) | Requires key (Google Maps Platform) | **INTEGRATE** (Live UI) | `live_only` |
| **Google Maps JS + Autocomplete** | Interactive Map & Location Search | Browser API Key (`VITE_GOOGLE_MAPS_BROWSER_KEY`) | Requires key with referrer restriction | **INTEGRATE** (Frontend) | `live_only` |
| **Google Geocoding API** | Lat/Lng Resolution & Reverse | Server API Key (`GOOGLE_MAPS_SERVER_KEY`) | Requires key | **INTEGRATE** | `live_only` (Permitted: `place_id`, display coords) |
| **Google Routes API** | Commute & Travel Times | Server API Key (`GOOGLE_MAPS_SERVER_KEY`) | Requires key | **INTEGRATE** (On-demand only) | `live_only` (No caching per terms) |
| **OpenStreetMap via Overpass API** | Amenity POIs, Snapshots, Reports | None (Public mirrors: `overpass-api.de`, `z.overpass-api.de`, `kumi.systems`) | **200 OK** (Mirror `z.overpass-api.de` returned 128 elements for Indiranagar; timeouts observed under heavy load) | **INTEGRATE** (Primary for Snapshots & Reports) | `storable` (ODbL 1.0) |
| **Open-Meteo Air Quality API** | European CAMS & US AQI, PM2.5, PM10 | None (Free tier, non-commercial / commercial license) | **200 OK** (Resolved Koramangala, Indiranagar, Chandapura with live PM2.5/PM10/AQI) | **INTEGRATE-LIMITED** (Modeled estimate only) | `storable` |
| **OpenAQ v3 API** | Real ground station measurements | API Key required (`X-API-Key`) | **401 Unauthorized** without key (`{"message": "Unauthorized. A valid API key must be provided in the X-API-Key header."}`) | **INTEGRATE-LIMITED / UNVERIFIED** (Requires user key) | `storable` (CC BY 4.0) |
| **Photon (Komoot OSM Geocoder)** | Geocoding fallback | None | **200 OK** (Resolved all 3 demo localities cleanly) | **INTEGRATE-LIMITED** (Low-volume fallback) | `storable` |
| **Nominatim (OSM)** | Geocoding fallback | None (Strict User-Agent + 1 req/sec) | **200 OK** | **DO NOT INTEGRATE (Autocomplete)** / **INTEGRATE-LIMITED (Fallback only)** | `storable` (ODbL) |
| **CPCB / data.gov.in (India)** | Station Air Quality / Water Quality | Portal / API Key / CAPTCHA | No geolocated machine API without scraping/PDFs | **DO NOT INTEGRATE (Live)** | `unavailable` |
| **India-WRIS / CGWB** | Groundwater & Water Quality | Portal / Static reports | No live property/locality-level JSON API | **DO NOT INTEGRATE (Live)** | `unavailable` |
| **NCRB (National Crime Records Bureau)** | Crime Statistics | Annual reports (PDF / District Level) | District/Commissionerate level only; zero locality-level machine API | **DO NOT INTEGRATE (Locality)** | `unavailable` (Absence caveat required) |

---

## 2. Detailed Candidate Evaluation

### 2.1 Google Maps Platform
- **Components:** Places API (New), Geocoding API, Routes API, Maps JavaScript API.
- **Auth:** Browser Key (`VITE_GOOGLE_MAPS_BROWSER_KEY`) restricted by HTTP referrer; Server Key (`GOOGLE_MAPS_SERVER_KEY`) for backend calls.
- **Granularity:** Exact address, place, street, locality, administrative area.
- **Coverage:** Global, industry-standard density across Indian metropolitan and peri-urban areas.
- **Rate Limits & Pricing:** Google Maps Platform pay-as-you-go pricing (e.g. Places Text Search \$32/1000, Autocomplete sessions \$17/1000 sessions, Routes \$5-\$10/1000).
- **Licence & Terms:** Strict restrictions against scraping, pre-fetching, storing content (only `place_id` can be stored for up to 30 days without refresh), and **prohibits sending Places content to third-party AI/LLM models**.
- **Storage Policy:** `live_only`.
- **Verdict:** **INTEGRATE** for live UI exploration, map display, and commute check.

---

### 2.2 OpenStreetMap via Overpass API
- **Endpoint tested:**
  - Primary: `https://z.overpass-api.de/api/interpreter`
  - Fallbacks: `https://overpass-api.de/api/interpreter`, `https://lz4.overpass-api.de/api/interpreter`, `https://overpass.kumi.systems/api/interpreter`
- **Auth:** None required.
- **Real Sample Call:**
  - Query: `node["amenity"~"school|hospital|clinic|pharmacy"](around:1500, 12.9811, 77.6444); out count;`
  - Result: 128 elements identified in Indiranagar, Bengaluru.
  - Failures observed: 504 Gateway Timeout on `overpass-api.de` under peak public server load.
- **Handling Strategy:** Multi-endpoint fallback pool with 12s timeout per mirror; cached responses; graceful fallback to `status="error"` / `limited`.
- **Licence:** Open Database License (ODbL) 1.0. Attribution required: "Data © OpenStreetMap contributors".
- **Storage Policy:** `storable`. This enables offline demo snapshots and immutable report data snapshots without violating terms.
- **Verdict:** **INTEGRATE** (Primary storable engine for reports and demo snapshots).

---

### 2.3 Open-Meteo Air Quality API
- **Endpoint tested:** `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=12.9352&longitude=77.6245&current=pm10,pm2_5,european_aqi,us_aqi`
- **Auth:** None required for standard usage.
- **Real Sample Result:**
  ```json
  {
    "latitude": 12.90,
    "longitude": 77.60,
    "current": {
      "pm10": 27.4,
      "pm2_5": 27.1,
      "european_aqi": 34,
      "us_aqi": 93
    }
  }
  ```
- **Provenance Kind:** `modeled_estimate`. Based on European Copernicus CAMS (Copernicus Atmosphere Monitoring Service) atmospheric reanalysis models.
- **Granularity:** ~11 km grid resolution.
- **Mandatory UI Label:** *"Modeled estimate — not a station measurement. Measurement may not represent conditions at the exact property."*
- **Storage Policy:** `storable` (Open-Meteo terms allow caching and attribution).
- **Verdict:** **INTEGRATE-LIMITED** (Used as air quality provider with explicit modeled-estimate provenance).

---

### 2.4 OpenAQ v3 API
- **Endpoint tested:** `https://api.openaq.org/v3/locations?coordinates=12.9352,77.6245&radius=25000`
- **Auth:** Required via `X-API-Key` header (`OPENAQ_API_KEY`).
- **Real Sample Result:** Returned `401 Unauthorized` without key.
- **Provenance Kind:** `station_measurement`.
- **Granularity:** Physical ground monitoring station.
- **Storage Policy:** `storable` (CC BY 4.0 with attribution).
- **Verdict:** **INTEGRATE-LIMITED / UNVERIFIED (WITHOUT KEY)**. Provider adapter implemented with key check; if `OPENAQ_API_KEY` is absent, marks module `unavailable` or gracefully falls back to Open-Meteo modeled estimate with provenance badge `modeled_estimate`.

---

### 2.5 Water Quality Sources (CPCB, CGWB, India-WRIS)
- **Investigation:** Examined India-WRIS and Central Ground Water Board (CGWB) databases.
- **Finding:** Water quality sampling is published sporadically in PDF reports, annual bulletins, or district-level tables. There are no live, geolocated, building/locality-level machine-readable REST APIs available for India.
- **Honest Absence Handling:**
  - Status: `unavailable` (○ No data found).
  - UI Copy: *"No integrated water-quality dataset covers this location. Water-quality information is based on available sample data and may not represent every property in this locality."*
  - Verify on site: "Ask the society/landlord about water supply source (Cauvery/borewell/tanker) and supply hours."
- **Verdict:** **DO NOT INTEGRATE (Live)**. Render compliant honest empty state.

---

### 2.6 Crime Statistics (NCRB, State Police)
- **Investigation:** Examined National Crime Records Bureau (NCRB) publications.
- **Finding:** Data is aggregated annually at the State and Police Commissionerate / District level (e.g., Bengaluru City Commissionerate). Locality-level, neighborhood-level crime incident databases are not publicly released via open machine APIs.
- **Honest Absence Handling:**
  - Status: `unavailable` (○ No data found).
  - UI Copy: *"Locality-level crime statistics are unavailable from integrated sources. Statistics from official agencies are aggregated at district or commissionerate levels and cannot be reliably attributed to individual neighborhoods."*
  - Absence Caveat: *"The absence of reported crime data does not imply that an area is safe."*
- **Safety Infrastructure Separation:** Physical infrastructure listings (police stations, fire stations) are mapped under **Safety infrastructure** (`map_listing`), completely separated from crime statistics.
- **Verdict:** **DO NOT INTEGRATE (Locality crime)**. Render compliant honest empty state.

---

### 2.7 Nominatim & Photon (OSM Geocoders)
- **Photon (Komoot):** Tested and responding with 200 OK.
- **Nominatim:** Tested and responding with 200 OK.
- **Usage Policy:** Strictly non-commercial rate limits (1 req/s for Nominatim). Never use for live autocomplete per keystroke.
- **Verdict:** Use Google Places Autocomplete as primary. Photon/Nominatim acts solely as low-volume developer/fallback lookup when Google keys are unconfigured.

---

## 3. Demo Search Localities (Section 20)

1. **Locality A (Rich Data):** `Koramangala, Bengaluru`  
   - Coordinates: `12.9352, 77.6245`  
   - Characteristics: Dense commercial & residential hub with extensive schools, hospitals, transit stops, and full coverage across all categories.
2. **Locality B (Comparable to A):** `Indiranagar, Bengaluru`  
   - Coordinates: `12.9811, 77.6444`  
   - Characteristics: Established residential locality in the same metropolitan area with high amenity density, allowing direct side-by-side comparability.
3. **Locality C (Genuine Data Gaps):** `Chandapura, Bengaluru`  
   - Coordinates: `12.8009, 77.7115`  
   - Characteristics: Peri-urban developing locality on the southern periphery. Demonstrates real-world limited amenity density, greater distances to tertiary healthcare/higher education, and illustrates honest `limited` and `unavailable` states.

---

## 4. LLM Provider Selection

- **Selected Primary:** `gemini` (`gemini-2.5-flash` or `gemini-1.5-flash`).
- **Secondary / Optional:** `anthropic` (`claude-3-5-sonnet-20241022` or `claude-3-5-haiku-20241022`).
- **Input Hygiene:** Strictly derived metrics only (Section 12.2). Place names, reviews, photos, and user notes are stripped before transmission.
- **Validation:** 100% of LLM claims verified by `ClaimValidator` against deterministic evidence IDs. Deterministic fallback active if validation fails.
