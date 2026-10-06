# LocalLens Unit Economics & Pricing Model

**Price per Paid Report:** ₹29.00 (`2900` paise)  
**Free Allowance:** 3 Reports upon verified email registration  
**Calculation Date:** 2026-09-30  
**Currency Conversion:** 1 USD ≈ 83.50 INR  

---

## 1. Cost per Paid Report Generation

When a user requests a generated Neighborhood Intelligence Report, the backend fetches storable evidence, synthesizes an AI summary, renders the PDF, generates a verification QR code, and uploads the immutable document to private cloud storage.

| Expense Category | Item / Provider | Official Rate Basis | Unit Cost (USD) | Unit Cost (INR) | Notes |
|---|---|---|---|---|---|
| **Payment Gateway** | Razorpay Standard Pricing | 2.0% + 18% GST on fee | — | ₹0.68 | 2% of ₹29 = ₹0.58; GST = ₹0.104 |
| **POIs & Places Data** | OpenStreetMap (Overpass) | Open source / ODbL | $0.0000 | ₹0.00 | Storable provider, zero query fee |
| **Environmental Data** | Open-Meteo Air Quality | Commercial tier | $0.0000 | ₹0.00 | Within baseline commercial limits |
| **AI Synthesis** | Gemini 1.5/2.5 Flash | Input: $0.075 / 1M tokens; Output: $0.30 / 1M tokens | $0.0002 | ₹0.02 | ~1,200 input tokens (~$0.00009) + ~400 output tokens (~$0.00012) |
| **PDF Generation** | ReportLab / WeasyPrint | In-process Python engine | — | ₹0.05 | Serverless/container CPU allocation (~1.2s execution) |
| **Document Storage** | Supabase Storage (Private) | $0.021 / GB-month | $0.00001 | ₹0.001 | ~350 KB compressed PDF |
| **Total Marginal Cost** | | | | **₹0.75** | |
| **Net Contribution** | | **₹29.00 – ₹0.75** | | **₹28.25** | **~97.4% Gross Margin** |

---

## 2. Cost per Live Exploration Session (Frontend)

During interactive exploration on the web app, live Google Maps Platform APIs are used for real-time map rendering and interactive nearby places exploration:

| Action | Provider API | Rate (per 1,000 requests) | Cost per Action (INR) | Monthly Free Allowance |
|---|---|---|---|---|
| Address Autocomplete | Google Places Autocomplete (Session-based) | $17.00 / 1k sessions | ₹1.42 per session | First ~11,700 sessions covered by Google's $200 monthly credit |
| Geocoding | Google Geocoding API | $5.00 / 1k requests | ₹0.42 per lookup | Covered by Google monthly credit |
| Nearby POIs (Live Map) | Google Places API (New) | $32.00 / 1k requests | ₹2.67 per search | Progressive loading minimizes unnecessary calls |
| Commute Estimation | Google Routes API | $5.00 – $10.00 / 1k requests | ₹0.42 – ₹0.84 | **Strictly on-demand**; only triggered when user submits a destination |

### Optimization & Cost Control Measures:
1. **Debounce Autocomplete:** 350ms debounce with minimum 3-character threshold prevents wasteful keystroke calls.
2. **Session Tokens:** Autocomplete uses session tokens so that all keystrokes in a single search count as one billing session.
3. **Progressive Loading:** Environmental and secondary layers load only on card expansion. Routes API is strictly user-invoked.
4. **Storable Cache for Fallback:** OpenStreetMap / Photon geocoding serves as low-volume fallback when Google API quotas are restricted.

---

## 3. Free Credits & Abuse Control

1. **3 Free Reports per User:** Granted strictly upon email verification (`auth.users.email_confirmed_at`).
2. **Atomic Credit Deduction:** Executed inside a PostgreSQL database transaction to prevent concurrent deduction race conditions.
3. **AI Daily Rate Limits:** Enforced via `AI_DAILY_LIMIT_PER_USER` (default: 10 syntheses/day) to prevent API budget exhaustion.
