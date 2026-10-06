# LocalLens Compliance & Data Policy

**Effective Date:** 2026-09-30  
**Version:** 4.0  

---

## 1. Provider Storage Policies & Licensing

LocalLens strictly categorizes all data providers into two architectural storage tiers:

| Provider | Storage Policy | Permitted Storage | Prohibited Storage | License / Terms Basis |
|---|---|---|---|---|
| **Google Maps Platform** (Places, Routes, Maps JS) | `live_only` | `place_id` (temporary reference), live session display in memory. | Permanent database storage of business listings, reviews, ratings, geometries, or Route paths. **Never sent to third-party LLMs.** | Google Maps Platform Terms of Service |
| **OpenStreetMap** (Overpass API) | `storable` | Full node/way amenity geometries, tags, counts, distances, and snapshot archives. | Modifying data without attributing OpenStreetMap contributors under ODbL. | Open Database License (ODbL) 1.0 |
| **Open-Meteo Air Quality** | `storable` | Atmospheric model outputs (AQI, PM2.5, PM10) with generation timestamp. | Misrepresenting modeled estimates as physical station ground sensors. | Open-Meteo Free / Commercial Terms |
| **OpenAQ** | `storable` | Ground station readings, station names, coordinates, and measurement timestamps. | Stripping attribution or claiming proprietary ownership. | Creative Commons Attribution 4.0 (CC BY 4.0) |

---

## 2. Google Maps Platform Content & AI Isolation

### 2.1 Storage & Caching Restrictions
1. **Places Data:** LocalLens does not store Google Places POI results in persistent storage tables (e.g. `report_data_snapshots`). Live exploration fetches places dynamically via client/server calls for immediate session rendering.
2. **Routes Data:** Google Routes travel times and directions are fetched **strictly on-demand** when the user requests a commute check. Routes responses are **never cached** or persisted.
3. **Identifier Caching:** Only `place_id` and basic geocoding center coordinates for user-searched localities are persisted in user search history and saved locations, complying with Google's allowance for user location identifiers.

### 2.2 Third-Party LLM Exclusion
Google's Terms of Service and data protection guidelines prohibit passing proprietary Places details (business names, user reviews, aggregate ratings, editorial summaries) to third-party generative AI models.

**Enforcement in LocalLens:**
- The LLM synthesis engine (`app/ai/`) receives **only derived, anonymized numeric and categorical facts** produced by the pure `EvidenceBuilder`:
  ```python
  # Allowed input to LLM:
  {
    "module": "education",
    "metric": "nearest_distance_m",
    "value": 450,
    "unit": "meters",
    "radius_m": 2000,
    "provenance_kind": "map_listing",
    "granularity": "exact_place",
    "status": "available",
    "evidence_id": "loc1:education:nearest_distance_m"
  }
  ```
- Specific business names, merchant titles, photos, user comments, reviews, and user notes are **strictly stripped and never transmitted** to the LLM.
- The `ClaimValidator` rejects any statement containing proper nouns other than the user's explicit locality query.

---

## 3. Report Generation & Snapshot Architecture

LocalLens reports are permanent, immutable decision documents. To ensure 100% legal compliance with third-party data licenses:

1. **Storable Data Engine for Reports:**  
   When a user generates a PDF report, the backend queries **`storable` providers only** (OpenStreetMap via Overpass for POIs; Open-Meteo / OpenAQ for environmental data).
2. **Immutable Snapshots:**  
   The resulting `ModuleResult` and `EvidenceItem` datasets are permanently archived in `report_data_snapshots` (JSONB) to guarantee the report remains reproducible.
3. **Clear User Disclosure:**  
   Every report builder and preview displays the required notice:  
   > *"This report uses OpenStreetMap-based place data, which can differ from the live Google map view."*
4. **Report Map Rendering:**  
   Map imagery embedded in generated PDFs utilizes compliant OpenStreetMap tile renders with standard attribution (`© OpenStreetMap contributors`) or vector coordinate diagrams.

---

## 4. Attribution Requirements

Every UI view and PDF report includes clear, non-negotiable attribution:

1. **Google Maps Platform:**  
   - Google logo rendered natively on the Maps JavaScript view.  
   - "Powered by Google" badge on autocomplete search results.
2. **OpenStreetMap:**  
   - "Data © OpenStreetMap contributors, ODbL 1.0 (http://osm.org/copyright)" rendered on Overpass-sourced cards, snapshots, and PDF reports.
3. **Open-Meteo:**  
   - "Air quality estimates courtesy of Open-Meteo (Copernicus Atmosphere Monitoring Service reanalysis)."
4. **OpenAQ:**  
   - "Ground station measurements sourced from OpenAQ contributors under CC BY 4.0."
