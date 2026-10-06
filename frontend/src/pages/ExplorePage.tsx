import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SearchBar } from '../components/search/SearchBar';
import { InteractiveMapView } from '../components/map/InteractiveMapView';
import { DataSourceDrawer } from '../components/common/DataSourceDrawer';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  LocationDetails,
  ModuleResult,
  PlacesData,
  PlaceItem,
  AirQualityData,
  WaterQualityData,
  CrimeData,
  CategoryKey,
  ProfileKey,
  PriorityKey,
  FindingItem,
  PriorityGapCallout,
  VerifyOnSiteQuestion
} from '../types';
import {
  HeartPulse,
  GraduationCap,
  Shield,
  ShoppingBag,
  Bus,
  Coffee,
  Bookmark,
  Scale,
  FileText,
  ChevronDown,
  ChevronUp,
  Info,
  CheckCircle2,
  AlertTriangle,
  CircleSlash,
  Sparkles,
  Droplets,
  Wind,
  Search
} from 'lucide-react';

const CATEGORIES: { key: CategoryKey; label: string; icon: any; color: string; bg: string }[] = [
  { key: 'healthcare', label: 'Healthcare', icon: HeartPulse, color: 'text-rose-600', bg: 'bg-rose-50 border-rose-200' },
  { key: 'education', label: 'Education', icon: GraduationCap, color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200' },
  { key: 'safety_infrastructure', label: 'Safety Infra', icon: Shield, color: 'text-purple-600', bg: 'bg-purple-50 border-purple-200' },
  { key: 'daily_life', label: 'Daily Essentials', icon: ShoppingBag, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' },
  { key: 'transport', label: 'Connectivity', icon: Bus, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200' },
  { key: 'lifestyle', label: 'Lifestyle', icon: Coffee, color: 'text-teal-600', bg: 'bg-teal-50 border-teal-200' }
];

const PROFILES: { key: ProfileKey; label: string; desc: string }[] = [
  { key: 'family', label: 'Family with Children', desc: 'Prioritizes schools, pediatric clinics, daily groceries, and parks.' },
  { key: 'student', label: 'Student', desc: 'Focuses on universities, transit halts, affordable eateries, and libraries.' },
  { key: 'commuter', label: 'Daily Commuter', desc: 'Prioritizes arterial transit, metro stops, and predictable commute routes.' },
  { key: 'home_buyer', label: 'Home Buyer', desc: 'Broad evaluation of long-term civic infrastructure and environmental depth.' },
  { key: 'first_time_renter', label: 'First-time Renter', desc: 'Convenience essentials, connectivity, and local lifestyle spots.' },
  { key: 'elderly', label: 'Elderly Household', desc: 'Immediate proximity to healthcare, emergency services, and quiet parks.' },
  { key: 'relocation', label: 'General Relocation', desc: 'Complete baseline survey of unknown neighborhood evidence.' }
];

const PRIORITIES: { key: PriorityKey; label: string }[] = [
  { key: 'education', label: 'Education' },
  { key: 'healthcare', label: 'Healthcare' },
  { key: 'transport', label: 'Transport' },
  { key: 'daily_life', label: 'Daily Essentials' },
  { key: 'parks', label: 'Parks & Green' },
  { key: 'lifestyle', label: 'Lifestyle & Cafes' },
  { key: 'environment', label: 'Environment' },
  { key: 'safety_infrastructure', label: 'Safety Infrastructure' }
];

export const ExplorePage: React.FC = () => {
  const navigate = useNavigate();
  const routeLocation = useLocation();
  const { isAuthenticated } = useAuth();

  const [selectedLocation, setSelectedLocation] = useState<LocationDetails | null>(null);
  const [isChangingLocation, setIsChangingLocation] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // User Profile & Priorities
  const [currentProfile, setCurrentProfile] = useState<ProfileKey>('family');
  const [selectedPriorities, setSelectedPriorities] = useState<PriorityKey[]>([
    'education',
    'healthcare',
    'transport',
    'daily_life',
    'parks'
  ]);

  // Progressive loading states for modules
  const [placesResult, setPlacesResult] = useState<ModuleResult<PlacesData> | null>(null);
  const [envResult, setEnvResult] = useState<ModuleResult<AirQualityData> | null>(null);
  const [waterResult, setWaterResult] = useState<ModuleResult<WaterQualityData> | null>(null);
  const [crimeResult, setCrimeResult] = useState<ModuleResult<CrimeData> | null>(null);

  const [isLoadingInsights, setIsLoadingInsights] = useState(false);

  // Deterministic Insights & AI state
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [gapCallouts, setGapCallouts] = useState<PriorityGapCallout[]>([]);
  const [verifyQuestions, setVerifyQuestions] = useState<VerifyOnSiteQuestion[]>([]);
  const [aiHeadline, setAiHeadline] = useState<string | null>(null);
  const [aiSynthesisText, setAiSynthesisText] = useState<string | null>(null);

  // Map & category filtering
  const [selectedCategory, setSelectedCategory] = useState<CategoryKey | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<PlaceItem | null>(null);

  // Collapsible category accordions (collapsed by default to prevent evaluator boredom)
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    essential_services: false,
    connectivity: false,
    lifestyle: false,
    environment: false,
    water: false,
    safety_crime: false
  });

  const [activeDrawer, setActiveDrawer] = useState<boolean>(false);

  // Abort controller ref to cancel stale requests (prevents race condition e.g. Kukatpally vs Madhapur)
  const abortControllerRef = useRef<AbortController | null>(null);

  // Preload location from query parameter if provided (e.g. from Dashboard or Compare)
  useEffect(() => {
    const params = new URLSearchParams(routeLocation.search);
    const queryName = params.get('q');
    if (queryName && !selectedLocation) {
      api.getAutocomplete(queryName).then((preds) => {
        if (preds && preds.length > 0) {
          api.getLocationDetails(preds[0].place_id).then((details) => {
            setSelectedLocation(details);
          });
        }
      }).catch(console.error);
    }
  }, [routeLocation.search]);

  // When location changes: cancel old requests and progressively fetch data
  useEffect(() => {
    if (!selectedLocation) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setSelectedPlace(null);
    setIsSaved(false);
    setWaterResult(null);
    setCrimeResult(null);

    // Record Search History if authenticated
    if (isAuthenticated) {
      api.addSearchHistory(selectedLocation.name, selectedLocation.lat, selectedLocation.lng, selectedLocation.provider)
        .catch(() => {});
      api.getSavedLocations().then((saved) => {
        const found = saved.some((s: any) => s.locality_name.toLowerCase() === selectedLocation.name.toLowerCase());
        setIsSaved(found);
      }).catch(() => {});
    }

    // 1. Initial Load: Nearby places
    api.getPlaces(selectedLocation.lat, selectedLocation.lng, 1500, undefined, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setPlacesResult(res);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') console.error('Places fetch error:', err);
      });

    // 2. Progressive Load: Environment
    api.getEnvironment(selectedLocation.lat, selectedLocation.lng, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setEnvResult(res);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') console.error('Environment fetch error:', err);
      });

    // 3. Progressive Load: Water & Crime (independent background load)
    api.getWater(selectedLocation.lat, selectedLocation.lng, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setWaterResult(res);
      })
      .catch(() => {});

    api.getCrime(selectedLocation.lat, selectedLocation.lng, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setCrimeResult(res);
      })
      .catch(() => {});

    return () => {
      controller.abort();
    };
  }, [selectedLocation, isAuthenticated]);

  // When module results or profile change, evaluate Locality Insights
  useEffect(() => {
    if (!selectedLocation) return;

    setIsLoadingInsights(true);
    const payload = {
      locality_key: 'loc1',
      profile: currentProfile,
      priorities: selectedPriorities,
      distance_preferences: [],
      places: placesResult,
      environment: envResult,
      water: waterResult,
      crime: crimeResult
    };

    api.getInsights(payload)
      .then((data) => {
        setFindings(data.findings || []);
        setGapCallouts(data.gap_callouts || []);
        setVerifyQuestions(data.verify_on_site || []);
      })
      .catch(console.error)
      .finally(() => setIsLoadingInsights(false));

    // Grounded AI synthesis with automatic deterministic fallback
    api.getAISummary({
      locality_name: selectedLocation.name,
      ...payload
    })
      .then((aiData) => {
        setAiHeadline(aiData.headline);
        // Find observation or interpretation statements
        const statements: string[] = [];
        (aiData.sections || []).forEach((sec: any) => {
          (sec.statements || []).forEach((st: any) => {
            if (st.kind === 'observation' || st.kind === 'interpretation') {
              statements.push(st.text);
            }
          });
        });
        setAiSynthesisText(statements.slice(0, 3).join(' '));
      })
      .catch(() => {
        // AI failure is non-fatal: graceful deterministic fallback
        setAiHeadline(`Evidence Summary for ${selectedLocation.name}`);
        setAiSynthesisText(null);
      });
  }, [selectedLocation, placesResult, envResult, waterResult, crimeResult, currentProfile, selectedPriorities]);

  const handleProfileSelect = (p: ProfileKey) => {
    setCurrentProfile(p);
    const defaultsMap: Record<ProfileKey, PriorityKey[]> = {
      family: ['education', 'healthcare', 'transport', 'daily_life', 'parks'],
      commuter: ['transport', 'daily_life', 'safety_infrastructure'],
      student: ['education', 'transport', 'daily_life', 'lifestyle'],
      elderly: ['healthcare', 'daily_life', 'parks', 'safety_infrastructure'],
      first_time_renter: ['transport', 'daily_life', 'lifestyle'],
      home_buyer: ['education', 'healthcare', 'transport', 'environment', 'safety_infrastructure'],
      relocation: ['healthcare', 'education', 'transport', 'daily_life', 'environment']
    };
    setSelectedPriorities(defaultsMap[p] || ['healthcare', 'education', 'transport']);
  };

  const togglePriority = (pr: PriorityKey) => {
    setSelectedPriorities((prev) =>
      prev.includes(pr) ? prev.filter((k) => k !== pr) : [...prev, pr]
    );
  };

  const toggleAccordion = (key: string) => {
    setExpandedCategories((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSaveToggle = async () => {
    if (!selectedLocation) return;
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    setIsSaving(true);
    try {
      if (isSaved) {
        const savedList = await api.getSavedLocations();
        const item = savedList.find((s: any) => s.locality_name.toLowerCase() === selectedLocation.name.toLowerCase());
        if (item) await api.deleteSavedLocation(item.id);
        setIsSaved(false);
      } else {
        await api.addSavedLocation(selectedLocation.name, selectedLocation.lat, selectedLocation.lng, 'Explored Area');
        setIsSaved(true);
      }
    } catch (e) {
      console.error('Save location toggle error:', e);
    } finally {
      setIsSaving(false);
    }
  };

  const places = placesResult?.data?.places || [];
  const filteredPlaces = selectedCategory
    ? places.filter((p) => p.category === selectedCategory)
    : places;

  // Category counts
  const categoryCounts = placesResult?.data?.counts_by_category || {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* ========================================================
          1. LOCATION HEADER
          ======================================================== */}
      <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-100">
                Neighborhood Intelligence
              </span>
              {selectedLocation && (
                <span className="text-[11px] text-slate-500 font-mono">
                  {selectedLocation.lat.toFixed(4)}° N, {selectedLocation.lng.toFixed(4)}° E
                </span>
              )}
            </div>

            <h1 className="font-display font-bold text-2xl text-navy-900 mt-1">
              {selectedLocation ? selectedLocation.name : 'Explore Any Neighborhood'}
            </h1>

            {selectedLocation ? (
              <p className="text-xs text-slate-500 mt-0.5 max-w-2xl line-clamp-1">
                {selectedLocation.formatted_address}
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-0.5">
                Search a locality, metro station or PIN code to inspect real neighborhood evidence.
              </p>
            )}
          </div>

          {/* Location Actions: Change, Save, Compare, Report */}
          {selectedLocation && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setIsChangingLocation(!isChangingLocation)}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
                type="button"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{isChangingLocation ? 'Close Search' : 'Change Location'}</span>
              </button>

              <button
                onClick={handleSaveToggle}
                disabled={isSaving}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                  isSaved
                    ? 'bg-amber-50 text-amber-900 border-amber-300'
                    : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
                }`}
                type="button"
              >
                <Bookmark className={`w-3.5 h-3.5 ${isSaved ? 'fill-amber-600 text-amber-600' : ''}`} />
                <span>{isSaved ? 'Saved' : 'Save'}</span>
              </button>

              <button
                onClick={() => navigate('/compare', { state: { locationA: selectedLocation } })}
                className="flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold border border-slate-200 transition-colors"
                type="button"
              >
                <Scale className="w-3.5 h-3.5 text-teal-600" />
                <span>Compare</span>
              </button>

              <button
                onClick={() =>
                  navigate(
                    `/reports/create?name=${encodeURIComponent(selectedLocation.name)}&lat=${selectedLocation.lat}&lng=${selectedLocation.lng}&profile=${currentProfile}`
                  )
                }
                className="flex items-center gap-1.5 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold shadow-xs transition-colors"
                type="button"
              >
                <FileText className="w-3.5 h-3.5 text-teal-400" />
                <span>Generate Report</span>
              </button>
            </div>
          )}
        </div>

        {/* Search Bar (visible if no location or if user clicks 'Change Location') */}
        {(!selectedLocation || isChangingLocation) && (
          <div className="pt-2 border-t border-slate-100">
            <SearchBar
              onLocationSelected={(loc) => {
                setSelectedLocation(loc);
                setIsChangingLocation(false);
              }}
              autoFocus={!selectedLocation || isChangingLocation}
              placeholder="Search locality name, landmark or PIN code..."
            />
          </div>
        )}

        {/* Differentiator Section Banner (Section 7) */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded text-[11px]">
              Why LocalLens?
            </span>
            <span className="italic text-slate-600">
              "Maps show what's around you. LocalLens helps you understand the available neighborhood evidence."
            </span>
          </div>
          {placesResult && (
            <button
              onClick={() => setActiveDrawer(true)}
              className="text-teal-700 hover:text-teal-800 font-semibold inline-flex items-center gap-1 text-[11px]"
            >
              <Info className="w-3.5 h-3.5" />
              <span>Provenance & Sources</span>
            </button>
          )}
        </div>
      </div>

      {selectedLocation && (
        <>
          {/* ========================================================
              2. LARGE INTERACTIVE MAP
              ======================================================== */}
          <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-3">
            <InteractiveMapView
              location={selectedLocation}
              places={filteredPlaces}
              selectedPlace={selectedPlace}
              onSelectPlace={(p) => setSelectedPlace(p)}
              activeCategories={selectedCategory ? [selectedCategory] : undefined}
              className="h-[480px] w-full"
            />

            {/* Category Filter Pills on/under the Map */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-none">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                  selectedCategory === null
                    ? 'bg-navy-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                All Places ({places.length})
              </button>
              {CATEGORIES.map((cat) => {
                const count = categoryCounts[cat.key] || 0;
                const isSelected = selectedCategory === cat.key;
                const Icon = cat.icon;
                return (
                  <button
                    key={cat.key}
                    onClick={() => setSelectedCategory(isSelected ? null : cat.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all border ${
                      isSelected
                        ? 'bg-teal-700 text-white border-teal-800 shadow-xs font-semibold'
                        : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-200'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-teal-200' : cat.color}`} />
                    <span>{cat.label}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                        isSelected ? 'bg-teal-900/40 text-teal-100' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ========================================================
              3. "WHAT MATTERS TO YOU?" (PERSONALIZATION)
              ======================================================== */}
          <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-4">
            <div>
              <h2 className="font-display font-bold text-base text-navy-900">
                What Matters to You?
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Select your household profile or toggle specific priority categories to customize evidence evaluation.
              </p>
            </div>

            {/* Profile Selection Chips */}
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Household Profile:
              </span>
              <div className="flex flex-wrap gap-2">
                {PROFILES.map((p) => {
                  const isSelected = currentProfile === p.key;
                  return (
                    <button
                      key={p.key}
                      onClick={() => handleProfileSelect(p.key)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                        isSelected
                          ? 'bg-navy-900 text-white border-navy-900 shadow-xs'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                      title={p.desc}
                      type="button"
                    >
                      {p.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Priority Selection Chips */}
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Evaluated Priorities:
              </span>
              <div className="flex flex-wrap gap-2">
                {PRIORITIES.map((pr) => {
                  const isSelected = selectedPriorities.includes(pr.key);
                  return (
                    <button
                      key={pr.key}
                      onClick={() => togglePriority(pr.key)}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs transition-all border ${
                        isSelected
                          ? 'bg-teal-50 text-teal-800 border-teal-300 font-semibold'
                          : 'bg-white text-slate-500 hover:text-slate-700 border-slate-200'
                      }`}
                      type="button"
                    >
                      <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-teal-600' : 'bg-slate-300'}`} />
                      <span>{pr.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ========================================================
              4. LOCALITY INSIGHT (MAIN DIFFERENTIATOR - THE HERO)
              ======================================================== */}
          <div className="bg-white p-6 rounded-3xl border border-teal-200/80 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-teal-600" />
                  <h2 className="font-display font-bold text-lg text-navy-900">
                    Locality Insight
                  </h2>
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-teal-50 text-teal-800 border border-teal-200 rounded-full">
                    Evidence-Based Analysis
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Synthesized directly from retrieved geospatial facilities and atmospheric models. Never speculative.
                </p>
              </div>

              {isLoadingInsights && (
                <div className="flex items-center gap-1.5 text-xs text-teal-700">
                  <div className="w-4 h-4 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
                  <span>Evaluating…</span>
                </div>
              )}
            </div>

            {/* AI / Grounded Synthesis Statement */}
            {aiSynthesisText && (
              <div className="p-3.5 bg-teal-50/60 border border-teal-200/60 rounded-2xl text-xs text-teal-950 leading-relaxed">
                <span className="font-bold text-teal-900 block mb-0.5">
                  {aiHeadline || 'Key Locality Takeaway:'}
                </span>
                <span>{aiSynthesisText}</span>
              </div>
            )}

            {/* Three Compact Columns: What We Found | What Is Limited | What Is Unavailable */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Column 1: WHAT WE FOUND */}
              <div className="p-4 bg-emerald-50/60 border border-emerald-200/80 rounded-2xl space-y-2.5">
                <div className="flex items-center gap-1.5 text-emerald-900 font-bold text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>WHAT WE FOUND</span>
                </div>
                <ul className="space-y-2 text-xs text-slate-700">
                  {findings.length > 0 ? (
                    findings.slice(0, 4).map((f) => (
                      <li key={f.id} className="leading-snug">
                        <span className="font-semibold text-slate-900 block">{f.headline}</span>
                        <span className="text-[11px] text-slate-600">{f.detail}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-[11px] text-slate-500">
                      {places.length > 0
                        ? `${places.length} mapped facilities identified within 1,500m radius.`
                        : 'Awaiting local amenity survey results.'}
                    </li>
                  )}
                </ul>
              </div>

              {/* Column 2: WHAT IS LIMITED */}
              <div className="p-4 bg-amber-50/60 border border-amber-200/80 rounded-2xl space-y-2.5">
                <div className="flex items-center gap-1.5 text-amber-900 font-bold text-xs">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>WHAT IS LIMITED</span>
                </div>
                <ul className="space-y-2 text-[11px] text-slate-700 leading-snug">
                  <li>
                    <span className="font-semibold text-slate-900 block">Straight-Line Distances</span>
                    Straight-line metric shown; actual walking or driving paths may be longer.
                  </li>
                  <li>
                    <span className="font-semibold text-slate-900 block">Atmospheric Grid Model</span>
                    Air quality derived from European CAMS ~11 km grid resolution, not an on-site property sensor.
                  </li>
                  <li>
                    <span className="font-semibold text-slate-900 block">Map Coverage Density</span>
                    Completeness depends on active community mapping in this specific area.
                  </li>
                </ul>
              </div>

              {/* Column 3: WHAT IS UNAVAILABLE */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2.5">
                <div className="flex items-center gap-1.5 text-slate-800 font-bold text-xs">
                  <CircleSlash className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>WHAT IS UNAVAILABLE</span>
                </div>
                <ul className="space-y-2 text-[11px] text-slate-600 leading-snug">
                  <li>
                    <span className="font-semibold text-slate-800 block">Locality Crime Records</span>
                    NCRB publishes data at district/city level; micro-neighborhood crime statistics are unavailable.
                  </li>
                  <li>
                    <span className="font-semibold text-slate-800 block">Continuous Piped Water Quality</span>
                    Public machine-readable municipal tap TDS/pH data is not published.
                  </li>
                  <li>
                    <span className="font-semibold text-slate-800 block">Absence Caveat</span>
                    Missing records in digital databases do not prove physical absence. Verify on site.
                  </li>
                </ul>
              </div>
            </div>

            {/* Evidence Callouts & On-Site Verification Checklist */}
            {gapCallouts.length > 0 && (
              <div className="p-3.5 bg-rose-50/70 border border-rose-200/80 rounded-2xl space-y-1.5">
                <span className="text-xs font-bold text-rose-900 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  Priority Evidence Gaps:
                </span>
                <ul className="text-xs text-rose-800 space-y-1">
                  {gapCallouts.map((g, idx) => (
                    <li key={idx} className="leading-snug">
                      <strong className="capitalize">{g.priority.replace('_', ' ')}:</strong> {g.gap_description || g.missing_data}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {verifyQuestions.length > 0 && (
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl space-y-1.5">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-slate-600 shrink-0" />
                  Recommended On-Site Verification Checklist:
                </span>
                <ul className="text-xs text-slate-700 list-disc list-inside space-y-0.5">
                  {verifyQuestions.slice(0, 3).map((q, idx) => (
                    <li key={idx}>{q.question}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* ========================================================
              5. DATA COVERAGE (NOT A LOCALITY SCORE)
              ======================================================== */}
          <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div>
                <h3 className="font-display font-bold text-sm text-navy-900">
                  Data Coverage & Confidence
                </h3>
                <p className="text-[11px] text-slate-500">
                  This measures verified information depth. It is strictly NOT a livability score, ranking, or endorsement.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
              <div className="p-3 rounded-2xl bg-emerald-50/50 border border-emerald-200/60">
                <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                  Places & Amenities
                </span>
                <span className="font-display font-bold text-base text-navy-900 block mt-0.5">
                  {places.length} Verified
                </span>
                <span className="text-[10px] text-slate-500">OpenStreetMap ODbL</span>
              </div>

              <div className="p-3 rounded-2xl bg-teal-50/50 border border-teal-200/60">
                <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider block">
                  Atmosphere / AQI
                </span>
                <span className="font-display font-bold text-base text-navy-900 block mt-0.5">
                  {envResult?.data?.aqi ? `AQI ${envResult.data.aqi}` : 'Estimated'}
                </span>
                <span className="text-[10px] text-slate-500">Open-Meteo Model Grid</span>
              </div>

              <div className="p-3 rounded-2xl bg-amber-50/50 border border-amber-200/60">
                <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider block">
                  Water Quality
                </span>
                <span className="font-display font-bold text-base text-slate-700 block mt-0.5">
                  Limited / On-Site
                </span>
                <span className="text-[10px] text-slate-500">Sensor data unavailable</span>
              </div>

              <div className="p-3 rounded-2xl bg-slate-100 border border-slate-200">
                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">
                  Safety / Crime
                </span>
                <span className="font-display font-bold text-base text-slate-700 block mt-0.5">
                  District Tier Only
                </span>
                <span className="text-[10px] text-slate-500">Micro stats unavailable</span>
              </div>
            </div>
          </div>

          {/* ========================================================
              6. CATEGORY DETAILS (COLLAPSIBLE ACCORDIONS)
              ======================================================== */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h3 className="font-display font-bold text-base text-navy-900">
                Category Details
              </h3>
              <span className="text-xs text-slate-500">
                Click any section to inspect specific facilities and sources
              </span>
            </div>

            {/* Accordion 1: Essential Services */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('essential_services')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-rose-50 text-rose-600 border border-rose-100">
                    <HeartPulse className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Essential Services (Healthcare, Education, Daily Life)
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {(categoryCounts['healthcare'] || 0) + (categoryCounts['education'] || 0) + (categoryCounts['daily_life'] || 0)} mapped facilities within 1,500m
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-800 rounded-md">
                    Verified Available
                  </span>
                  {expandedCategories['essential_services'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['essential_services'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-1">
                    {places
                      .filter((p) => ['healthcare', 'education', 'daily_life'].includes(p.category))
                      .map((p) => (
                        <div
                          key={p.id}
                          onClick={() => setSelectedPlace(p)}
                          className={`p-3 rounded-xl border bg-white cursor-pointer transition-all flex items-start justify-between gap-2 ${
                            selectedPlace?.id === p.id ? 'border-teal-500 ring-2 ring-teal-200' : 'border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <div>
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                              {p.subcategory || p.category}
                            </span>
                            <h5 className="font-bold text-xs text-navy-900 mt-0.5">{p.name}</h5>
                            {p.address && <p className="text-[11px] text-slate-500 mt-0.5 truncate">{p.address}</p>}
                          </div>
                          <span className="text-xs font-bold text-slate-700 shrink-0">{p.distance_m}m</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 2: Connectivity & Transport */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('connectivity')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                    <Bus className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Connectivity & Transport
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {categoryCounts['transport'] || 0} transit nodes mapped within survey radius
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-800 rounded-md">
                    Verified Available
                  </span>
                  {expandedCategories['connectivity'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['connectivity'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[250px] overflow-y-auto pr-1">
                    {places
                      .filter((p) => p.category === 'transport')
                      .map((p) => (
                        <div
                          key={p.id}
                          onClick={() => setSelectedPlace(p)}
                          className={`p-3 rounded-xl border bg-white cursor-pointer transition-all flex items-start justify-between gap-2 ${
                            selectedPlace?.id === p.id ? 'border-teal-500 ring-2 ring-teal-200' : 'border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <div>
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                              {p.subcategory || 'Transit Stop'}
                            </span>
                            <h5 className="font-bold text-xs text-navy-900 mt-0.5">{p.name}</h5>
                          </div>
                          <span className="text-xs font-bold text-slate-700 shrink-0">{p.distance_m}m</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 3: Lifestyle & Recreation */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('lifestyle')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-teal-50 text-teal-600 border border-teal-100">
                    <Coffee className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Lifestyle & Recreation (Parks, Fitness, Cafes)
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {categoryCounts['lifestyle'] || 0} recreational locations mapped within 1,500m
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-800 rounded-md">
                    Verified Available
                  </span>
                  {expandedCategories['lifestyle'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['lifestyle'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[250px] overflow-y-auto pr-1">
                    {places
                      .filter((p) => p.category === 'lifestyle')
                      .map((p) => (
                        <div
                          key={p.id}
                          onClick={() => setSelectedPlace(p)}
                          className={`p-3 rounded-xl border bg-white cursor-pointer transition-all flex items-start justify-between gap-2 ${
                            selectedPlace?.id === p.id ? 'border-teal-500 ring-2 ring-teal-200' : 'border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <div>
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                              {p.subcategory || 'Recreation'}
                            </span>
                            <h5 className="font-bold text-xs text-navy-900 mt-0.5">{p.name}</h5>
                          </div>
                          <span className="text-xs font-bold text-slate-700 shrink-0">{p.distance_m}m</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 4: Environment & Air Quality */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('environment')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-blue-50 text-blue-600 border border-blue-100">
                    <Wind className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Environment & Atmosphere
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {envResult?.data?.aqi ? `AQI ${envResult.data.aqi} (PM2.5: ${envResult.data.pm25} µg/m³)` : 'Atmospheric model estimate'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-amber-50 text-amber-800 rounded-md">
                    Model Grid Estimate
                  </span>
                  {expandedCategories['environment'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['environment'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  <div className="p-3 bg-white rounded-2xl border border-slate-200 text-xs text-slate-700 space-y-2">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div>
                        <span className="text-[10px] text-slate-400 block">Air Quality Index</span>
                        <span className="font-bold text-base text-navy-900">{envResult?.data?.aqi ?? 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">PM2.5 Level</span>
                        <span className="font-bold text-base text-navy-900">{envResult?.data?.pm25 ?? 'N/A'} µg/m³</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">PM10 Level</span>
                        <span className="font-bold text-base text-navy-900">{envResult?.data?.pm10 ?? 'N/A'} µg/m³</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">Model Resolution</span>
                        <span className="font-bold text-base text-navy-900">~11 km grid</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                      <strong>Mandatory Disclosure:</strong> Data derived from Open-Meteo European CAMS atmospheric model grid estimates. This reflects regional air currents rather than an on-site physical sensor.
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 5: Water Quality Disclosures */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('water')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-cyan-50 text-cyan-600 border border-cyan-100">
                    <Droplets className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Piped Water Information
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Municipal continuous piped sensor records are currently not published
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                    Unavailable Publicly
                  </span>
                  {expandedCategories['water'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['water'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-2">
                  <div className="p-3 bg-white rounded-2xl border border-slate-200 text-xs text-slate-700 space-y-2">
                    <p className="font-medium">
                      Municipal water supply agencies (such as BWSSB / HMWSSB / DJB) do not publish real-time, machine-readable tap quality data for micro-localities.
                    </p>
                    <div className="text-[11px] text-slate-500 space-y-1">
                      <p>• Verify apartment society water source: Municipal Cauvery/Krishna pipe vs private borewell vs tanker reliance.</p>
                      <p>• Carry an on-site portable TDS meter during your physical property inspection visit.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 6: Safety Infrastructure & Crime Statistics */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('safety_crime')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-purple-50 text-purple-600 border border-purple-100">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Safety Infrastructure & Crime Statistics Disclosure
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {categoryCounts['safety_infrastructure'] || 0} police/fire facilities mapped · Crime data district-tier only
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                    Disclosure Required
                  </span>
                  {expandedCategories['safety_crime'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['safety_crime'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  <div className="p-3.5 bg-rose-50/70 border border-rose-200 rounded-2xl text-xs text-rose-950 space-y-1.5">
                    <span className="font-bold block">Official Crime Statistics Disclosure:</span>
                    <p className="text-[11px] leading-relaxed">
                      Locality-level micro crime statistics were not available from configured verified sources. In India, official crime data (NCRB) is published aggregated at the state or district level, not by neighborhood or street.
                    </p>
                    <p className="text-[11px] font-semibold text-rose-800">
                      Crucial: Absence of published digital crime data does not imply absence of crime or guarantee personal safety.
                    </p>
                  </div>

                  {/* Physical Checklist */}
                  <div className="p-3 bg-white rounded-2xl border border-slate-200 text-xs space-y-2">
                    <span className="font-bold text-slate-800 block">Physical On-Site Verification Checklist:</span>
                    <ul className="text-[11px] text-slate-600 space-y-1">
                      <li>• Assess street lighting along pedestrian paths between 7:30 PM and 9:30 PM.</li>
                      <li>• Observe pedestrian foot traffic density and operational commercial activity after dusk.</li>
                      <li>• Confirm presence of 24/7 security or gated access at specific residential complexes.</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Data Source Drawer */}
      {placesResult && (
        <DataSourceDrawer
          isOpen={activeDrawer}
          onClose={() => setActiveDrawer(false)}
          title="Data Provenance & Source Attributions"
          status={placesResult.status}
          provenanceKind={placesResult.provenance_kind}
          sources={placesResult.sources}
          coverage={placesResult.coverage}
          fetchedAt={placesResult.fetched_at}
          sourceUpdatedAt={placesResult.source_updated_at}
          measuredAt={placesResult.measured_at}
          limitations={placesResult.limitations}
          absenceCaveat="Notice: Missing records in an external map database do not establish physical non-existence. OpenStreetMap and third-party listings are subject to mapping coverage density."
        />
      )}
    </div>
  );
};
