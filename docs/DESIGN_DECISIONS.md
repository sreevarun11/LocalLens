# LocalLens Architectural & Design Decisions

This document records the core product, architectural, and ethical decisions behind LocalLens.

---

## 1. Why No Overall Locality Score?

Most real estate and neighborhood portals assign a single composite score (e.g. "8.6/10 Livability" or "Safety: 4.5 Stars"). LocalLens explicitly forbids this.

### The Reasoning:
1. **False Equivalence & Hidden Trade-offs:** A single numerical score flattens disparate dimensions into an arbitrary formula. For a student without a car, proximity to a metro station matters far more than hospital density. For an elderly couple, emergency healthcare access is paramount while school counts are irrelevant. An aggregate number obscures these vital personal trade-offs.
2. **Fabrication of Precision:** Real-world neighborhood data is fundamentally incomplete and heterogeneous. Assigning an exact decimal number creates an illusion of scientific certainty where none exists.
3. **Misleading Safety Claims:** No public open data source provides real-time, neighborhood-level safety ratings. Synthesizing a "safety score" gives users a false sense of security or unjustifiably stigmatizes developing communities.

**Our Alternative:**  
Deterministic evidence metrics filtered through **User Priorities** and **User-Set Distance Preferences** (e.g., "Is there a school within my preferred 1.5 km distance? Yes, 820m away").

---

## 2. Why "Available", Not "Verified"?

Many services advertise their data as "verified". LocalLens strictly avoids this word for third-party datasets.

### The Reasoning:
- A point of interest returned by Google Places or OpenStreetMap simply proves that an entity was submitted or cataloged in that database. It is **not proof** that the school is currently operating, has open admissions, or that the clinic is staffed 24/7.
- Ground station environmental sensors or modeled meteorological grids are measurements or simulations, not absolute verifications of ambient air inside an individual apartment.
- Calling external data "verified" overclaims credibility and misleads homebuyers and renters making life-altering decisions.

### Our Vocabulary:
- `available`: An integrated external source returned matching data for this radius.
- `limited`: Partial, distant, coarse, capped, or modeled data.
- `unavailable`: No integrated source has data for this location.
- `error`: The external provider failed, timed out, or is unconfigured.

---

## 3. Absence Semantics: "Not Found" ≠ "Does Not Exist"

When a search reveals zero hospitals within 1 km, LocalLens outputs:  
*"No healthcare listing found within 1 km in this map database."*  
It never outputs: *"No healthcare exists."*

### Why this distinction matters:
- OpenStreetMap and commercial map databases are contributor and crawler-driven. Freshly opened or unmapped local clinics may exist despite not appearing in an API query.
- Absence of crime data at the locality level simply reflects government reporting granularity (district/commissionerate), **not** the absence of crime.

---

## 4. What the LLM Adds (and What It Is Forbidden to Add)

Generative AI in LocalLens is constrained to a narrow, high-value function:
- **What it adds:**
  1. A coherent, priority-ordered narrative synthesizing how the user's specific priorities interact with the evidence.
  2. Clearly distinguished interpretations of trade-offs (e.g., high transit accessibility paired with elevated ambient PM2.5).
  3. Contextual selection and phrasing of "Verify on site" questions.
- **What it is forbidden to add:**
  1. Facts, place names, numbers, distances, or ratings not explicitly provided in the deterministic evidence input.
  2. Unverifiable safety, crime, or quality judgments.
  3. Banned judgmental phrases ("perfect for families", "ideal location", "safe neighborhood").

Every statement output by the LLM is deterministically audited by the `ClaimValidator`. Statements failing evidence link checks or hallucinating numbers are stripped immediately.

---

## 5. Why Reports Use Storable Providers (OpenStreetMap)

### Legal and Reproducibility Rationale:
- Under Google Maps Platform terms of service, persisting POI listings, places text searches, and routes in permanent databases is strictly prohibited.
- A PDF report is an immutable legal decision record that must remain verifiable years later via its public verification page (`/verify/:reportId`).
- To guarantee 100% legal compliance and permanence, report snapshots are drawn from `storable` open providers (OpenStreetMap under ODbL 1.0; Open-Meteo / OpenAQ under open terms).
- Users are transparently informed in the builder and report:  
  *"This report uses OpenStreetMap-based place data, which can differ from the live Google map view."*

---

## 6. Deterministic Fallback Architecture

If an external provider suffers an outage, if an API quota is exhausted, or if the LLM fails validation:
- The user is **never** presented with a broken screen or fabricated filler.
- The UI immediately renders deterministic findings generated from the core `EvidenceBuilder` with explicit status badges (`◐ Limited`, `○ No data found`, `⚠ Temporarily unavailable`).
- The application remains 100% functional, trustworthy, and actionable.
