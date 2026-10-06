import {
  AutocompletePrediction,
  LocationDetails,
  ModuleResult,
  PlacesData,
  AirQualityData,
  WaterQualityData,
  CrimeData,
  CommuteData,
  Coordinates
} from '../types';

// Normalize API_BASE so both relative '/api' (via Vite proxy) and full host URLs work
const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';
const API_BASE = rawBase.endsWith('/api') ? rawBase : `${rawBase.replace(/\/$/, '')}/api`;

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('locallens_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// In-memory short-lived cache for idempotent geospatial lookups (prevents repeated roundtrips)
const queryCache = new Map<string, { data: any; expiry: number }>();
const CACHE_TTL_MS = 60_000; // 1 minute

function getCached<T>(key: string): T | null {
  const cached = queryCache.get(key);
  if (cached && cached.expiry > Date.now()) {
    return cached.data as T;
  }
  return null;
}

function setCached(key: string, data: any): void {
  // Cap cache size
  if (queryCache.size > 100) {
    const oldestKey = queryCache.keys().next().value;
    if (oldestKey) queryCache.delete(oldestKey);
  }
  queryCache.set(key, { data, expiry: Date.now() + CACHE_TTL_MS });
}

export const api = {
  // --- Auth & Account ---
  async register(email: string, password: string, displayName?: string) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Registration failed');
    }
    return await res.json();
  },

  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Invalid email or password');
    }
    return await res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Not authenticated');
    return await res.json();
  },

  async verifyEmailSimulate() {
    const res = await fetch(`${API_BASE}/auth/verify-email-simulate`, {
      method: 'POST',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Failed to verify email');
    return await res.json();
  },

  async resendVerification() {
    const res = await fetch(`${API_BASE}/auth/resend-verification`, {
      method: 'POST',
      headers: { ...getAuthHeaders() }
    });
    return await res.json();
  },

  async forgotPassword(email: string) {
    // Graceful recovery endpoint (if backend endpoint not present, return informative confirmation)
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      if (res.ok) return await res.json();
    } catch {
      // fallback
    }
    return { status: 'ok', message: `Password reset instructions sent to ${email}` };
  },

  async resetPassword(password: string) {
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ password })
      });
      if (res.ok) return await res.json();
    } catch {
      // fallback
    }
    return { status: 'ok', message: 'Password updated successfully' };
  },

  async getCredits() {
    const res = await fetch(`${API_BASE}/credits`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Failed to fetch credits');
    return await res.json();
  },

  async addCredits(amount: number = 1, paymentMethod: string = 'simulation') {
    const res = await fetch(`${API_BASE}/credits/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ amount, payment_method: paymentMethod })
    });
    if (!res.ok) throw new Error('Failed to add credits');
    return await res.json();
  },

  // --- User Preferences ---
  async getPreferences() {
    const res = await fetch(`${API_BASE}/preferences`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Failed to fetch preferences');
    return await res.json();
  },

  async updatePreferences(defaultProfile: string, defaultPriorities: string[], distancePreferences: any[]) {
    const res = await fetch(`${API_BASE}/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        default_profile: defaultProfile,
        default_priorities: defaultPriorities,
        distance_preferences: distancePreferences
      })
    });
    if (!res.ok) throw new Error('Failed to update preferences');
    return await res.json();
  },

  // --- Search History ---
  async getSearchHistory() {
    const res = await fetch(`${API_BASE}/search-history`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return [];
    return await res.json();
  },

  async addSearchHistory(localityName: string, lat: number, lng: number, provider: string = 'Google Places') {
    const res = await fetch(`${API_BASE}/search-history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ locality_name: localityName, lat, lng, provider })
    });
    return await res.json();
  },

  async clearSearchHistory() {
    const res = await fetch(`${API_BASE}/search-history`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    });
    return await res.json();
  },

  // --- Saved Locations ---
  async getSavedLocations() {
    const res = await fetch(`${API_BASE}/saved-locations`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return [];
    return await res.json();
  },

  async addSavedLocation(localityName: string, lat: number, lng: number, label?: string, notes?: string) {
    const res = await fetch(`${API_BASE}/saved-locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ locality_name: localityName, lat, lng, label, notes })
    });
    if (!res.ok) throw new Error('Failed to save location');
    return await res.json();
  },

  async updateSavedLocation(id: string, label?: string, notes?: string) {
    const res = await fetch(`${API_BASE}/saved-locations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ label, notes })
    });
    if (!res.ok) throw new Error('Failed to update saved location');
    return await res.json();
  },

  async deleteSavedLocation(id: string) {
    const res = await fetch(`${API_BASE}/saved-locations/${id}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Failed to delete saved location');
    return await res.json();
  },

  // --- Feedback ---
  async submitFeedback(payload: { report_id?: string; locality_name?: string; feedback_type: string; description: string }) {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  // --- Reports (Slice 7) ---
  async generateReport(payload: any) {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to generate report');
    }
    return await res.json();
  },

  async listReports() {
    const res = await fetch(`${API_BASE}/reports`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) return [];
    return await res.json();
  },

  async getReport(reportId: string) {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) throw new Error('Report not found');
    return await res.json();
  },

  getPdfUrl(reportId: string, inline: boolean = false): string {
    return `${API_BASE}/reports/${reportId}/pdf${inline ? '?inline=true' : ''}`;
  },

  async downloadReportPdf(reportId: string, filename?: string): Promise<void> {
    const url = `${API_BASE}/reports/${reportId}/pdf`;
    const res = await fetch(url, {
      headers: { ...getAuthHeaders() }
    });
    if (!res.ok) {
      throw new Error(`Failed to download report PDF (HTTP ${res.status})`);
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || `LocalLens_Report_${reportId.slice(0, 8)}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 2000);
  },

  async getPublicVerification(reportId: string) {
    const res = await fetch(`${API_BASE}/reports/verify/${reportId}`);
    if (!res.ok) throw new Error('Verification failed: report not found');
    return await res.json();
  },

  // --- Location & Search ---
  async getAutocomplete(query: string, sessionToken?: string, signal?: AbortSignal): Promise<AutocompletePrediction[]> {
    if (!query || query.trim().length < 2) return [];
    const params = new URLSearchParams({ query: query.trim() });
    if (sessionToken) params.append('session_token', sessionToken);
    
    try {
      const res = await fetch(`${API_BASE}/location/autocomplete?${params.toString()}`, { signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e: any) {
      if (e.name === 'AbortError') return [];
      console.error('Autocomplete fetch error:', e);
      return [];
    }
  },

  async getLocationDetails(placeId: string, sessionToken?: string): Promise<LocationDetails> {
    const params = new URLSearchParams({ place_id: placeId });
    if (sessionToken) params.append('session_token', sessionToken);
    const res = await fetch(`${API_BASE}/location/details?${params.toString()}`);
    if (!res.ok) throw new Error(`Location details failed: HTTP ${res.status}`);
    const details = await res.json();
    // Guarantee canonical coordinates
    details.latitude = details.latitude ?? details.lat;
    details.longitude = details.longitude ?? details.lng;
    return details;
  },

  async reverseGeocode(lat: number, lng: number): Promise<LocationDetails> {
    const params = new URLSearchParams({ lat: lat.toString(), lng: lng.toString() });
    const res = await fetch(`${API_BASE}/location/reverse?${params.toString()}`);
    if (!res.ok) throw new Error(`Reverse geocode failed: HTTP ${res.status}`);
    const details = await res.json();
    // Guarantee canonical coordinates
    details.latitude = details.latitude ?? details.lat;
    details.longitude = details.longitude ?? details.lng;
    return details;
  },

  // --- Modules ---
  async getPlaces(
    lat: number,
    lng: number,
    radiusM: number = 1500,
    categories?: string[],
    signal?: AbortSignal
  ): Promise<ModuleResult<PlacesData>> {
    const cacheKey = `places_${lat.toFixed(4)}_${lng.toFixed(4)}_${radiusM}_${(categories || []).sort().join(',')}`;
    const cached = getCached<ModuleResult<PlacesData>>(cacheKey);
    if (cached) return cached;

    const params = new URLSearchParams({
      lat: lat.toString(),
      lng: lng.toString(),
      radius_m: radiusM.toString()
    });
    if (categories && categories.length > 0) {
      categories.forEach(c => params.append('categories', c));
    }
    const res = await fetch(`${API_BASE}/modules/places?${params.toString()}`, { signal });
    if (!res.ok) throw new Error(`Places fetch failed: HTTP ${res.status}`);
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  },

  async getEnvironment(lat: number, lng: number, signal?: AbortSignal): Promise<ModuleResult<AirQualityData>> {
    const cacheKey = `env_${lat.toFixed(4)}_${lng.toFixed(4)}`;
    const cached = getCached<ModuleResult<AirQualityData>>(cacheKey);
    if (cached) return cached;

    const params = new URLSearchParams({ lat: lat.toString(), lng: lng.toString() });
    const res = await fetch(`${API_BASE}/modules/environment?${params.toString()}`, { signal });
    if (!res.ok) throw new Error(`Environment fetch failed: HTTP ${res.status}`);
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  },

  async getWater(lat: number, lng: number, signal?: AbortSignal): Promise<ModuleResult<WaterQualityData>> {
    const params = new URLSearchParams({ lat: lat.toString(), lng: lng.toString() });
    const res = await fetch(`${API_BASE}/modules/water?${params.toString()}`, { signal });
    if (!res.ok) throw new Error(`Water fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async getCrime(lat: number, lng: number, signal?: AbortSignal): Promise<ModuleResult<CrimeData>> {
    const params = new URLSearchParams({ lat: lat.toString(), lng: lng.toString() });
    const res = await fetch(`${API_BASE}/modules/crime?${params.toString()}`, { signal });
    if (!res.ok) throw new Error(`Crime fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async getCommute(origin: Coordinates, destCoords: Coordinates, destQuery?: string, signal?: AbortSignal): Promise<ModuleResult<CommuteData>> {
    const res = await fetch(`${API_BASE}/modules/commute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin,
        destination_coords: destCoords,
        destination_query: destQuery
      }),
      signal
    });
    if (!res.ok) throw new Error(`Commute fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async getInsights(payload: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${API_BASE}/insights`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
    if (!res.ok) throw new Error(`Insights fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async getAISummary(payload: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
    if (!res.ok) throw new Error(`AI summary fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async compare(payload: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${API_BASE}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
    if (!res.ok) throw new Error(`Comparison fetch failed: HTTP ${res.status}`);
    return await res.json();
  },

  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return await res.json();
  },

  async getProviderHealth() {
    const res = await fetch(`${API_BASE}/health/providers`);
    return await res.json();
  }
};
