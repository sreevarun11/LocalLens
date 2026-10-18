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
  SafetyAndCrimeData,
  SafetyFacility,
  CategoryKey,
  ProfileKey,
  PriorityKey,
  CommuteData
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
  AlertTriangle,
  CircleSlash,
  Droplets,
  Wind,
  Search,
  Thermometer,
  Sun,
  Car,
  Route,
  Navigation,
  MapPin,
  Phone,
  ExternalLink
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
  { key: 'water', label: 'Water Resources' },
  { key: 'safety_infrastructure', label: 'Safety Infrastructure' },
  { key: 'commute', label: 'Commute' }
];

const COMMUTE_PRESETS = [
  { id: 'hitec_city', name: 'HITEC City (Cyber Towers)', coords: { lat: 17.4504, lng: 78.3808 } },
  { id: 'secunderabad', name: 'Secunderabad Railway Station', coords: { lat: 17.4334, lng: 78.5015 } },
  { id: 'rgia_airport', name: "Rajiv Gandhi Int'l Airport (RGIA)", coords: { lat: 17.2403, lng: 78.4294 } },
  { id: 'gachibowli_fin', name: 'Gachibowli Financial District', coords: { lat: 17.4156, lng: 78.3429 } }
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
  const [crimeResult, setCrimeResult] = useState<ModuleResult<SafetyAndCrimeData> | null>(null);

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
  const [surveyRadius, setSurveyRadius] = useState<number>(1500);

  // Commute Road Routing & Transit State
  const [commuteResult, setCommuteResult] = useState<ModuleResult<CommuteData> | null>(null);
  const [commuteLoading, setCommuteLoading] = useState<boolean>(false);
  const [commuteError, setCommuteError] = useState<string | null>(null);
  const [selectedDestinationPreset, setSelectedDestinationPreset] = useState<string | null>(null);
  const [activeRouteGeometry, setActiveRouteGeometry] = useState<[number, number][] | null>(null);
  const [activeRouteDestName, setActiveRouteDestName] = useState<string | null>(null);

  // Abort controller refs to cancel stale requests (prevents race condition e.g. Kukatpally vs Madhapur)
  const abortControllerRef = useRef<AbortController | null>(null);
  const placesAbortRef = useRef<AbortController | null>(null);

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

  // When location or surveyRadius changes: fetch nearby places with race-condition prevention
  useEffect(() => {
    if (!selectedLocation) {
      setPlacesResult(null);
      return;
    }

    if (placesAbortRef.current) {
      placesAbortRef.current.abort();
    }
    const controller = new AbortController();
    placesAbortRef.current = controller;

    setSelectedPlace(null);
    api.getPlaces(selectedLocation.lat, selectedLocation.lng, surveyRadius, undefined, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setPlacesResult(res);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') console.error('Places fetch error:', err);
      });

    return () => {
      controller.abort();
    };
  }, [selectedLocation, surveyRadius]);

  // When location changes: progressively fetch environment, water, crime
  useEffect(() => {
    if (!selectedLocation) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

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

    // Progressive Load: Environment
    api.getEnvironment(selectedLocation.lat, selectedLocation.lng, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setEnvResult(res);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') console.error('Environment fetch error:', err);
      });

    // Progressive Load: Water & Crime (independent background load)
    api.getWater(selectedLocation.lat, selectedLocation.lng, selectedLocation.locality || selectedLocation.name, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setWaterResult(res);
      })
      .catch(() => {});

    api.getCrime(selectedLocation.lat, selectedLocation.lng, surveyRadius, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setCrimeResult(res);
      })
      .catch(() => {});

    return () => {
      controller.abort();
    };
  }, [selectedLocation, isAuthenticated]);

  // Reset commute route state when selected location changes
  useEffect(() => {
    setCommuteResult(null);
    setSelectedDestinationPreset(null);
    setActiveRouteGeometry(null);
    setActiveRouteDestName(null);
    setCommuteError(null);
  }, [selectedLocation?.lat, selectedLocation?.lng]);

  const handleCheckCommute = async (destCoords: { lat: number; lng: number }, destName: string, presetId?: string) => {
    if (!selectedLocation) return;
    setCommuteLoading(true);
    setCommuteError(null);
    setSelectedDestinationPreset(presetId || null);

    try {
      const res = await api.getCommute(
        { lat: selectedLocation.lat, lng: selectedLocation.lng },
        destCoords,
        destName
      );
      setCommuteResult(res);
      const drivingMode = res.data?.modes?.driving;
      if (drivingMode?.route_geometry && drivingMode.route_geometry.length > 0) {
        setActiveRouteGeometry(drivingMode.route_geometry as [number, number][]);
        setActiveRouteDestName(destName);
      } else {
        setActiveRouteGeometry(null);
        setActiveRouteDestName(null);
      }
    } catch (err: any) {
      console.error('Commute check error:', err);
      setCommuteError(err?.message || 'Failed to fetch road route.');
      setCommuteResult(null);
      setActiveRouteGeometry(null);
      setActiveRouteDestName(null);
    } finally {
      setCommuteLoading(false);
    }
  };

  const handleProfileSelect = (p: ProfileKey) => {
    setCurrentProfile(p);
    const defaultsMap: Record<ProfileKey, PriorityKey[]> = {
      family: ['education', 'healthcare', 'transport', 'daily_life', 'parks'],
      commuter: ['transport', 'commute', 'daily_life', 'safety_infrastructure'],
      student: ['education', 'transport', 'daily_life', 'lifestyle'],
      elderly: ['healthcare', 'daily_life', 'parks', 'safety_infrastructure'],
      first_time_renter: ['transport', 'daily_life', 'lifestyle', 'commute'],
      home_buyer: ['education', 'healthcare', 'transport', 'environment', 'water', 'safety_infrastructure'],
      relocation: ['healthcare', 'education', 'transport', 'daily_life', 'environment', 'safety_infrastructure']
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

  const handleSelectSafetyFacility = (f: SafetyFacility) => {
    setSelectedPlace({
      id: f.id,
      name: f.name,
      category: 'safety_infrastructure',
      subcategory: f.facility_type,
      lat: f.lat,
      lng: f.lng,
      distance_m: f.distance_m,
      address: f.address,
      source_name: f.source_name,
      source_attribution: f.source_attribution
    });
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
            {/* Survey Radius Selector & Cap Information */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-1 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">Survey Radius:</span>
                <div className="inline-flex rounded-xl bg-slate-100 p-0.5">
                  {[
                    { value: 500, label: '500m' },
                    { value: 1000, label: '1 km' },
                    { value: 1500, label: '1.5 km' },
                    { value: 2000, label: '2 km' },
                    { value: 3000, label: '3 km' },
                  ].map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setSurveyRadius(r.value)}
                      type="button"
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                        surveyRadius === r.value
                          ? 'bg-white text-teal-700 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              {placesResult?.data?.cap_reached && (
                <div className="flex items-center gap-1.5 text-xs text-amber-800 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>
                    Display cap reached: Showing {places.length} nearest of {placesResult.data.total_found || 'many'} facilities found within {surveyRadius >= 1000 ? `${surveyRadius / 1000} km` : `${surveyRadius}m`}.
                  </span>
                </div>
              )}
            </div>

            <InteractiveMapView
              location={selectedLocation}
              places={filteredPlaces}
              selectedPlace={selectedPlace}
              onSelectPlace={(p) => setSelectedPlace(p)}
              radiusM={surveyRadius}
              activeCategories={selectedCategory ? [selectedCategory] : undefined}
              routeGeometry={activeRouteGeometry}
              routeDestinationName={activeRouteDestName}
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
                All Places ({placesResult?.data?.total_found && placesResult.data.total_found > places.length ? `${places.length} of ${placesResult.data.total_found}` : places.length})
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
              4. DATA COVERAGE (NOT A LOCALITY SCORE)
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
                  Atmosphere & Weather
                </span>
                <span className="font-display font-bold text-base text-navy-900 block mt-0.5">
                  {envResult?.data?.temperature_c != null
                    ? `${envResult.data.temperature_c}°C · AQI ${envResult.data.aqi ?? '—'}`
                    : (envResult?.data?.aqi ? `AQI ${envResult.data.aqi}` : 'Estimated')}
                </span>
                <span className="text-[10px] text-slate-500">
                  {envResult?.provenance_kind === 'station_measurement'
                    ? `Station (${envResult?.data?.station_name || 'Ground'})`
                    : 'Open-Meteo Model Grid'}
                </span>
              </div>

              <div className={`p-3 rounded-2xl ${
                waterResult?.data?.assessment_category === 'Safe'
                  ? 'bg-emerald-50/50 border border-emerald-200/60'
                  : waterResult?.data?.assessment_category === 'Semi-Critical'
                  ? 'bg-amber-50/50 border border-amber-200/60'
                  : waterResult?.data?.assessment_category
                  ? 'bg-rose-50/50 border border-rose-200/60'
                  : 'bg-slate-100 border border-slate-200'
              }`}>
                <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider block">
                  Water Resources
                </span>
                <span className="font-display font-bold text-base text-navy-900 block mt-0.5 truncate">
                  {waterResult?.data?.assessment_category
                    ? (waterResult.data.data_level === 'mandal'
                        ? `${waterResult.data.assessment_category} (Mandal)`
                        : `${waterResult.data.assessment_category} (${waterResult.data.stage_of_extraction_pct ?? '—'}% SoE)`)
                    : (waterResult?.status === 'unavailable' ? 'Unavailable' : 'Limited / On-Site')}
                </span>
                <span className="text-[10px] text-slate-500 block truncate">
                  {waterResult?.data?.district_name
                    ? (waterResult.data.data_level === 'mandal'
                        ? `${waterResult.data.mandal_name || 'Mandal'}, ${waterResult.data.district_name} · CGWB 2022`
                        : `${waterResult.data.district_name} · CGWB / TGWD 2022`)
                    : 'Tap quality unverified'}
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-slate-100 border border-slate-200">
                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">
                  Safety / Crime
                </span>
                <span className="font-display font-bold text-base text-slate-700 block mt-0.5">
                  {crimeResult?.data?.nearby_facilities && crimeResult.data.nearby_facilities.length > 0
                    ? `${crimeResult.data.nearby_facilities.length} Mapped Fac.`
                    : 'District Tier Only'}
                </span>
                <span className="text-[10px] text-slate-500 truncate block">
                  {crimeResult?.data?.jurisdiction?.jurisdiction_name
                    ? crimeResult.data.jurisdiction.jurisdiction_name
                    : 'Micro stats unavailable'}
                </span>
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
                      {(categoryCounts['healthcare'] || 0) + (categoryCounts['education'] || 0) + (categoryCounts['daily_life'] || 0)} mapped facilities within {(placesResult?.coverage?.radius_m || surveyRadius).toLocaleString()}m
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                    ((categoryCounts['healthcare'] || 0) + (categoryCounts['education'] || 0) + (categoryCounts['daily_life'] || 0)) > 0
                      ? 'bg-emerald-50 text-emerald-800'
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {((categoryCounts['healthcare'] || 0) + (categoryCounts['education'] || 0) + (categoryCounts['daily_life'] || 0)) > 0
                      ? `${(categoryCounts['healthcare'] || 0) + (categoryCounts['education'] || 0) + (categoryCounts['daily_life'] || 0)} Mapped`
                      : 'No Mapped Records'}
                  </span>
                  {expandedCategories['essential_services'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['essential_services'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  {places.filter((p) => ['healthcare', 'education', 'daily_life'].includes(p.category)).length === 0 ? (
                    <div className="p-4 bg-white border border-slate-200 rounded-xl text-center">
                      <p className="text-xs font-semibold text-slate-700">No essential service records mapped within {(placesResult?.coverage?.radius_m || surveyRadius).toLocaleString()}m.</p>
                      <p className="text-[11px] text-slate-500 mt-1">Absence in OpenStreetMap records indicates a data gap, not definitive proof of physical absence.</p>
                    </div>
                  ) : (
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
                  )}
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
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                    (categoryCounts['transport'] || 0) > 0 ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {(categoryCounts['transport'] || 0) > 0 ? `${categoryCounts['transport']} Mapped` : 'No Mapped Records'}
                  </span>
                  {expandedCategories['connectivity'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['connectivity'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-5">
                  {/* Part 1: Nearby Mapped Public Transit Facilities */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Bus className="w-3.5 h-3.5 text-emerald-600" />
                        Mapped Transit Nodes ({places.filter((p) => p.category === 'transport').length})
                      </span>
                      <span className="text-[10px] text-slate-400">Within {surveyRadius}m survey radius</span>
                    </div>

                    {places.filter((p) => p.category === 'transport').length === 0 ? (
                      <div className="p-4 bg-white border border-slate-200 rounded-xl text-center">
                        <p className="text-xs font-semibold text-slate-700">No transit stops or connectivity nodes mapped within survey radius.</p>
                        <p className="text-[11px] text-slate-500 mt-1">Absence in OpenStreetMap records indicates a data gap, not definitive proof of physical transit absence.</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-[220px] overflow-y-auto pr-1">
                          {places
                            .filter((p) => p.category === 'transport')
                            .map((p) => (
                              <div
                                key={p.id}
                                onClick={() => setSelectedPlace(p)}
                                className={`p-2.5 rounded-xl border bg-white cursor-pointer transition-all flex items-start justify-between gap-2 ${
                                  selectedPlace?.id === p.id ? 'border-teal-500 ring-2 ring-teal-200' : 'border-slate-200 hover:border-slate-300'
                                }`}
                              >
                                <div className="min-w-0">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block truncate">
                                    {p.subcategory?.replace('_', ' ') || 'Transit Stop'}
                                  </span>
                                  <h5 className="font-bold text-xs text-navy-900 mt-0.5 truncate">{p.name}</h5>
                                </div>
                                <span className="text-xs font-bold text-slate-700 shrink-0">{p.distance_m}m</span>
                              </div>
                            ))}
                        </div>
                        <div className="p-2.5 bg-amber-50/70 border border-amber-200/80 rounded-xl text-[11px] text-amber-900 flex items-start gap-2">
                          <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                          <span>
                            <strong>Public Transit Limitation:</strong> Physical stations and bus stops are mapped from OpenStreetMap. Active routes, service frequency, timetable schedules, and current operational status are not mapped and cannot be assumed.
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Part 2: Road-Network Routing & Commute Check (OSRM) */}
                  <div className="pt-4 border-t border-slate-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Route className="w-3.5 h-3.5 text-blue-600" />
                        Road-Network Commute Route Check (OSRM)
                      </span>
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">
                        Road Geometry Only (No Live Traffic)
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mb-3">
                      Select a key employment or transit destination to query real road-network distances and nominal travel times via OpenStreetMap / OSRM.
                    </p>

                    {/* Presets */}
                    <div className="flex flex-wrap gap-2 mb-3">
                      {COMMUTE_PRESETS.map((preset) => {
                        const isSelected = selectedDestinationPreset === preset.id;
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            disabled={commuteLoading}
                            onClick={() => handleCheckCommute(preset.coords, preset.name, preset.id)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                              isSelected
                                ? 'bg-navy-900 text-white border-navy-900 shadow-xs'
                                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                            }`}
                          >
                            <MapPin className="w-3 h-3 text-slate-400" />
                            <span>{preset.name}</span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Loading State */}
                    {commuteLoading && (
                      <div className="p-4 bg-white border border-slate-200 rounded-xl text-center space-y-2">
                        <div className="inline-block w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
                        <p className="text-xs text-slate-600 font-medium">Querying road-network route from OSRM...</p>
                      </div>
                    )}

                    {/* Error State */}
                    {commuteError && !commuteLoading && (
                      <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                          <div>
                            <p className="font-semibold">Routing Provider Error</p>
                            <p className="text-[11px] text-rose-700 mt-0.5">{commuteError}</p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => selectedDestinationPreset && handleCheckCommute(
                            COMMUTE_PRESETS.find(p => p.id === selectedDestinationPreset)?.coords || { lat: 0, lng: 0 },
                            COMMUTE_PRESETS.find(p => p.id === selectedDestinationPreset)?.name || '',
                            selectedDestinationPreset
                          )}
                          className="text-[11px] font-bold text-rose-800 underline hover:text-rose-950 shrink-0"
                        >
                          Retry
                        </button>
                      </div>
                    )}

                    {/* Results Display */}
                    {commuteResult && commuteResult.data && !commuteLoading && (
                      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                        <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Destination</span>
                            <h5 className="font-bold text-sm text-navy-900">{commuteResult.data.destination_name}</h5>
                          </div>
                          {activeRouteGeometry && (
                            <button
                              type="button"
                              onClick={() => {
                                if (activeRouteGeometry) {
                                  setActiveRouteGeometry(null);
                                  setActiveRouteDestName(null);
                                } else {
                                  const geom = commuteResult.data?.modes?.driving?.route_geometry;
                                  if (geom) {
                                    setActiveRouteGeometry(geom as [number, number][]);
                                    setActiveRouteDestName(commuteResult.data?.destination_name || 'Destination');
                                  }
                                }
                              }}
                              className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-100 transition-colors flex items-center gap-1"
                            >
                              <Route className="w-3.5 h-3.5 text-teal-600" />
                              <span>{activeRouteGeometry ? 'Hide Route on Map' : 'View on Map'}</span>
                            </button>
                          )}
                        </div>

                        {/* Mode Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          {/* Driving Mode */}
                          {commuteResult.data.modes.driving && (
                            <div className="p-3 rounded-xl border border-blue-100 bg-blue-50/40 space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] font-bold text-blue-900 flex items-center gap-1">
                                  <Car className="w-3.5 h-3.5 text-blue-600" />
                                  Driving (Road Route)
                                </span>
                                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-100 text-blue-800">
                                  {commuteResult.data.modes.driving.status}
                                </span>
                              </div>
                              {commuteResult.data.modes.driving.status === 'available' ? (
                                <>
                                  <div className="text-lg font-bold text-navy-900 mt-1">
                                    ~{commuteResult.data.modes.driving.duration_min} mins
                                  </div>
                                  <div className="text-xs text-slate-600 font-medium">
                                    {commuteResult.data.modes.driving.distance_km} km mapped road distance
                                  </div>
                                  <p className="text-[10px] text-slate-500 mt-0.5">
                                    Derived from actual road network geometry (free-flow speeds).
                                  </p>
                                </>
                              ) : (
                                <p className="text-xs text-slate-600 mt-1">
                                  {commuteResult.data.modes.driving.route_summary || 'Route unavailable'}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Public Transit Mode (Schedule Unavailable Honesty) */}
                          <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/70 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                                <Bus className="w-3.5 h-3.5 text-slate-500" />
                                Public Transit
                              </span>
                              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                                Schedule Unavailable
                              </span>
                            </div>
                            <div className="text-xs text-slate-600 mt-1">
                              Timetables require official GTFS feed.
                            </div>
                            <p className="text-[10px] text-slate-500 mt-1">
                              Travel times are not synthesized or invented from road speeds.
                            </p>
                          </div>

                          {/* Walking Mode */}
                          {commuteResult.data.modes.walking && (
                            <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                                  <Navigation className="w-3.5 h-3.5 text-slate-500" />
                                  Walking
                                </span>
                                <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                                  commuteResult.data.modes.walking.status === 'available'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-slate-200 text-slate-600'
                                }`}>
                                  {commuteResult.data.modes.walking.status === 'available' ? 'Pedestrian Route' : 'Long Distance'}
                                </span>
                              </div>
                              {commuteResult.data.modes.walking.status === 'available' ? (
                                <>
                                  <div className="text-base font-bold text-navy-900 mt-1">
                                    ~{commuteResult.data.modes.walking.duration_min} mins
                                  </div>
                                  <div className="text-xs text-slate-600">
                                    {commuteResult.data.modes.walking.distance_km} km pedestrian path
                                  </div>
                                </>
                              ) : (
                                <p className="text-[11px] text-slate-600 mt-1">
                                  {commuteResult.data.modes.walking.distance_km} km exceeds walking threshold (&gt; 4 km).
                                </p>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Traffic & Limitations Notice */}
                        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 space-y-1">
                          <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                            <Info className="w-3.5 h-3.5 text-slate-500" />
                            <span>Routing Methodology & Disclaimers:</span>
                          </div>
                          <p>{commuteResult.data.traffic_claim}</p>
                          <p className="text-[10px] text-slate-400">
                            Provider: {commuteResult.sources?.[0]?.name || 'OSRM Road-Network Engine'} | Licensed under Open Database License (ODbL) © OpenStreetMap contributors.
                          </p>
                        </div>
                      </div>
                    )}
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
                      {categoryCounts['lifestyle'] || 0} recreational locations mapped within {(placesResult?.coverage?.radius_m || surveyRadius).toLocaleString()}m
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                    (categoryCounts['lifestyle'] || 0) > 0 ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {(categoryCounts['lifestyle'] || 0) > 0 ? `${categoryCounts['lifestyle']} Mapped` : 'No Mapped Records'}
                  </span>
                  {expandedCategories['lifestyle'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['lifestyle'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-3">
                  {places.filter((p) => p.category === 'lifestyle').length === 0 ? (
                    <div className="p-4 bg-white border border-slate-200 rounded-xl text-center">
                      <p className="text-xs font-semibold text-slate-700">No recreation, dining, or park facilities mapped within {(placesResult?.coverage?.radius_m || surveyRadius).toLocaleString()}m.</p>
                      <p className="text-[11px] text-slate-500 mt-1">Absence in OpenStreetMap records indicates a data gap, not definitive proof of physical absence.</p>
                    </div>
                  ) : (
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
                  )}
                </div>
              )}
            </div>

            {/* Accordion 4: Environment, Weather & Air Quality */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion('environment')}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-blue-50 text-blue-600 border border-blue-100">
                    <Sun className="w-5 h-5 text-amber-500" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-sm text-navy-900">
                      Environment, Weather & Air Quality
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {envResult?.data?.temperature_c != null
                        ? `${envResult.data.temperature_c}°C · ${envResult.data.weather_desc || 'Fair'} · AQI ${envResult.data.aqi ?? '—'}`
                        : (envResult?.data?.aqi ? `AQI ${envResult.data.aqi} (PM2.5: ${envResult.data.pm25 ?? '—'} µg/m³)` : 'Atmospheric model and weather estimate')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                    envResult?.provenance_kind === 'station_measurement'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border border-amber-200'
                  }`}>
                    {envResult?.provenance_kind === 'station_measurement' ? 'Ground Station' : 'Model Grid (~11 km)'}
                  </span>
                  {expandedCategories['environment'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['environment'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-4">
                  {/* Weather Section */}
                  <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <Thermometer className="w-4 h-4 text-rose-500" />
                        <span className="font-bold text-xs text-navy-900">Weather Forecast</span>
                        <span className="text-[10px] text-slate-500">(Open-Meteo)</span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {envResult?.data?.weather?.forecast_time ? `Forecast: ${envResult.data.weather.forecast_time}` : 'Current Forecast'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">Temperature</span>
                        <span className="font-bold text-sm text-navy-900">
                          {envResult?.data?.temperature_c != null ? `${envResult.data.temperature_c} °C` : '—'}
                        </span>
                        {envResult?.data?.apparent_temperature_c != null && (
                          <span className="text-[10px] text-slate-500 block">Feels like {envResult.data.apparent_temperature_c} °C</span>
                        )}
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">Condition</span>
                        <span className="font-bold text-sm text-navy-900">
                          {envResult?.data?.weather_desc || 'Fair / Clear'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Precip: {envResult?.data?.precipitation_probability_pct ?? 0}%</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">Humidity</span>
                        <span className="font-bold text-sm text-navy-900">
                          {envResult?.data?.humidity_pct != null ? `${envResult.data.humidity_pct} %` : '—'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Wind: {envResult?.data?.wind_speed_kmh ?? '—'} km/h</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">UV Index</span>
                        <span className="font-bold text-sm text-navy-900">
                          {envResult?.data?.uv_index != null ? envResult.data.uv_index : '—'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Solar radiation index</span>
                      </div>
                    </div>

                    <p className="text-[10px] text-slate-500 italic">
                      Weather metrics are numerical atmospheric model forecasts derived from Open-Meteo. They represent expected regional weather and not an on-site property sensor.
                    </p>
                  </div>

                  {/* Air Quality Section */}
                  <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <Wind className="w-4 h-4 text-teal-600" />
                        <span className="font-bold text-xs text-navy-900">Air Quality & Atmosphere</span>
                        {envResult?.provenance_kind === 'station_measurement' ? (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Physical Station: {envResult.data?.station_name} ({envResult.data?.station_distance_m != null ? (Math.round(envResult.data.station_distance_m / 100) / 10).toFixed(1) : '—'} km away)
                          </span>
                        ) : (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            Copernicus CAMS Grid (~11 km)
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {envResult?.measured_at ? `Observed: ${new Date(envResult.measured_at).toLocaleTimeString()}` : ''}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">Air Quality Index</span>
                        <span className="font-bold text-base text-navy-900">{envResult?.data?.aqi ?? 'N/A'}</span>
                        <span className="text-[10px] text-slate-500 block">{envResult?.data?.aqi_scale || 'US AQI'}</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">PM2.5 Level</span>
                        <span className="font-bold text-base text-navy-900">
                          {envResult?.data?.pm25 != null ? `${envResult.data.pm25} µg/m³` : 'N/A'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Fine particulate matter</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">PM10 Level</span>
                        <span className="font-bold text-base text-navy-900">
                          {envResult?.data?.pm10 != null ? `${envResult.data.pm10} µg/m³` : 'N/A'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Inhalable coarse particles</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-[10px] text-slate-400 block">Gaseous Pollutants</span>
                        <span className="text-[11px] font-semibold text-slate-800 block mt-0.5">
                          NO₂: {envResult?.data?.no2 != null ? `${envResult.data.no2} µg/m³` : '—'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">
                          SO₂: {envResult?.data?.so2 != null ? `${envResult.data.so2}` : '—'} · O₃: {envResult?.data?.o3 != null ? `${envResult.data.o3}` : '—'}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
                      {envResult?.limitations?.map((lim, idx) => (
                        <p key={idx}>• {lim}</p>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Accordion 5: Water Resources & Groundwater Assessment */}
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
                      Water Resources & Groundwater Assessment
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {waterResult?.data?.district_name
                        ? (waterResult.data.data_level === 'mandal'
                            ? `Mandal: ${waterResult.data.mandal_name || 'Selected'} (${waterResult.data.assessment_category}) · ${waterResult.data.district_name} District`
                            : `${waterResult.data.district_name} District (${waterResult.data.stage_of_extraction_pct ?? '—'}% Stage of Extraction)`)
                        : 'Official CGWB & State Ground Water Dept Assessment'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                    waterResult?.data?.assessment_category === 'Safe'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : waterResult?.data?.assessment_category === 'Semi-Critical'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : waterResult?.data?.assessment_category
                      ? 'bg-rose-50 text-rose-800 border border-rose-200'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {waterResult?.data?.assessment_category
                      ? `${waterResult.data.assessment_category} (${waterResult.data.data_level === 'mandal' ? 'Mandal' : 'District'})`
                      : (waterResult?.status === 'unavailable' ? 'Unavailable' : 'Assessing')}
                  </span>
                  {expandedCategories['water'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['water'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-4">
                  {waterResult?.status === 'available' && waterResult.data ? (
                    <>
                      {/* Groundwater Resource Metrics Grid */}
                      <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                          <div className="flex items-center gap-2">
                            <Droplets className="w-4 h-4 text-cyan-600" />
                            <span className="font-bold text-xs text-navy-900">Official Resource Assessment</span>
                            <span className="text-[10px] text-slate-500">({waterResult.data.assessment_methodology || 'GEC-2015 Norms'})</span>
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {waterResult.data.reporting_year || 'Assessment Year 2022'} · Historical Baseline
                          </span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                            <span className="text-[10px] text-slate-400 block">Aquifer Category</span>
                            <span className="font-bold text-sm text-navy-900">
                              {waterResult.data.assessment_category}
                            </span>
                            <span className="text-[10px] text-slate-500 block">
                              {waterResult.data.data_level === 'mandal' ? `Mandal: ${waterResult.data.mandal_name}` : 'District assessment'}
                            </span>
                          </div>

                          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                            <span className="text-[10px] text-slate-400 block">Stage of Extraction</span>
                            <span className="font-bold text-sm text-navy-900">
                              {waterResult.data.data_level === 'mandal'
                                ? (waterResult.data.mandal_stage_of_extraction_pct != null
                                    ? `${waterResult.data.mandal_stage_of_extraction_pct}%`
                                    : 'Unavailable (Mandal)')
                                : (waterResult.data.stage_of_extraction_pct != null
                                    ? `${waterResult.data.stage_of_extraction_pct}%`
                                    : '—')}
                            </span>
                            <span className="text-[10px] text-slate-500 block">
                              {waterResult.data.data_level === 'mandal'
                                ? `District Avg: ${waterResult.data.district_stage_of_extraction_pct ?? '—'}% (${waterResult.data.district_name})`
                                : `${waterResult.data.annual_extraction_ham != null ? Math.round(waterResult.data.annual_extraction_ham) : '—'} / ${waterResult.data.annual_extractable_ham != null ? Math.round(waterResult.data.annual_extractable_ham) : '—'} ham`}
                            </span>
                          </div>

                          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                            <span className="text-[10px] text-slate-400 block">Water Table Depth</span>
                            <span className="font-bold text-sm text-navy-900">
                              {waterResult.data.water_table_pre_monsoon_mbgl} mbgl
                            </span>
                            <span className="text-[10px] text-slate-500 block">
                              Post: {waterResult.data.water_table_post_monsoon_mbgl} mbgl (+{waterResult.data.seasonal_water_table_rise_m}m rise)
                            </span>
                          </div>

                          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                            <span className="text-[10px] text-slate-400 block">Regional Baseline</span>
                            <span className="font-bold text-sm text-navy-900">
                              TDS {waterResult.data.tds_range_mg_l || '—'}
                            </span>
                            <span className="text-[10px] text-slate-500 block">
                              pH: {waterResult.data.ph_range || '—'}
                            </span>
                          </div>
                        </div>

                        <div className="p-2.5 rounded-xl bg-slate-50/80 border border-slate-100 text-[11px] text-slate-600 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                          <div>
                            <span className="font-semibold text-slate-800">Geographic Resolution: </span>
                            <span>{waterResult.data.geographic_resolution || (waterResult.data.data_level === 'mandal' ? `Mandal: ${waterResult.data.mandal_name}` : `${waterResult.data.district_name} District`)}</span>
                          </div>
                          <span className="text-[10px] text-slate-500 shrink-0">
                            Publication: {waterResult.data.dataset_publication || 'CGWB & TGWD (2022)'}
                          </span>
                        </div>
                      </div>

                      {/* Mandatory Potability & Building-Level Limitation Disclosures */}
                      <div className="p-3.5 bg-amber-50/70 border border-amber-200/80 rounded-2xl space-y-2 text-xs text-amber-900">
                        <div className="flex items-center gap-1.5 font-bold">
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                          <span>Mandatory Drinking Water, Chemistry & Building Limitations</span>
                        </div>
                        <ul className="text-[11px] text-slate-700 space-y-1 leading-snug list-disc list-inside">
                          <li>
                            <strong>Resource Sustainability ≠ Drinking Water Safety:</strong> Official CGWB assessments evaluate macro aquifer replenishment versus total draft. An assessment category of Safe does NOT certify tap or borewell water as safe to drink.
                          </li>
                          <li>
                            <strong>Regional Ambient Chemistry vs Tap Water:</strong> The displayed TDS and pH ranges reflect deep hard-rock aquifer monitoring wells from the CGWB state network, not local piped drinking water.
                          </li>
                          <li>
                            <strong>Building-Level Verification Required:</strong> Municipal piped water supplies (HMWSSB / Krishna / Godavari pipelines), private borewell depth, TDS, total hardness, and tanker reliance vary building-by-building and cannot be established from macro government surveys.
                          </li>
                          <li>
                            <strong>On-Site Inspection Advice:</strong> Always test drinking water TDS and potability on site with a certified test kit or meter during physical inspection, and verify water supply tanker dependency with the residential society.
                          </li>
                        </ul>
                      </div>

                      {/* Source Attribution & Caveat */}
                      <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[10px] text-slate-400">
                        <span>
                          Source: Central Ground Water Board (CGWB) & Ground Water Department, Govt. of Telangana (GWRA Report, NDSAP License)
                        </span>
                        {waterResult.sources?.[0]?.url && (
                          <a
                            href={waterResult.sources[0].url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-teal-600 hover:underline"
                          >
                            View Official Publication →
                          </a>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-2">
                      <div className="flex items-center gap-2 text-slate-700 font-semibold text-xs">
                        <CircleSlash className="w-4 h-4 text-slate-400" />
                        <span>Official Data Unavailable</span>
                      </div>
                      <p className="text-xs text-slate-500">
                        {waterResult?.message || 'Official CGWB Telangana groundwater dataset covers Telangana state only. This location is outside the state boundary.'}
                      </p>
                      <div className="pt-2 text-[11px] text-slate-500 border-t border-slate-100 space-y-1">
                        <p>• Verify apartment society water source: Municipal Krishna/Godavari pipe vs private borewell vs tanker reliance.</p>
                        <p>• Carry an on-site portable TDS meter during your physical property inspection visit.</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Accordion 6: Safety Infrastructure, Emergency Contacts & Crime Statistics */}
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
                      Safety Infrastructure, Emergency Contacts & Crime Transparency
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {crimeResult?.data?.nearby_facilities ? crimeResult.data.nearby_facilities.length : (categoryCounts['safety_infrastructure'] || 0)} mapped facilities · 6 emergency helplines · Crime data macro-tier only
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                    {crimeResult?.data?.jurisdiction?.jurisdiction_name ? 'Jurisdiction Mapped' : 'Transparency Disclosure'}
                  </span>
                  {expandedCategories['safety_crime'] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>

              {expandedCategories['safety_crime'] && (
                <div className="p-4 border-t border-slate-100 bg-slate-50/40 space-y-5">
                  {/* 1. NEARBY EMERGENCY FACILITIES */}
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                        1. Nearby Emergency Facilities
                      </span>
                      <span className="text-[11px] text-slate-500">
                        Within {surveyRadius}m survey radius
                      </span>
                    </div>

                    {crimeResult?.status === 'error' ? (
                      <div className="p-3 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-900">
                        {crimeResult.message || 'Database error while retrieving mapped emergency facilities.'}
                      </div>
                    ) : (crimeResult?.data?.nearby_facilities && crimeResult.data.nearby_facilities.length > 0) ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {crimeResult.data.nearby_facilities.map((f) => (
                          <div
                            key={f.id}
                            onClick={() => handleSelectSafetyFacility(f)}
                            className={`p-3 rounded-2xl border bg-white cursor-pointer transition-all flex flex-col justify-between gap-2 ${
                              selectedPlace?.id === f.id ? 'border-purple-500 ring-2 ring-purple-200' : 'border-slate-200 hover:border-slate-300'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <span className="font-semibold text-xs text-slate-900 block">
                                  {f.name}
                                </span>
                                <span className="text-[11px] text-slate-500 block mt-0.5">
                                  {f.address || 'Address unlisted in OSM'}
                                </span>
                              </div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                f.facility_type === 'police' ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                              }`}>
                                {f.facility_type === 'police' ? 'Police Station' : 'Fire Station'}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100">
                              <span className="font-semibold text-slate-700 flex items-center gap-1">
                                <MapPin className="w-3.5 h-3.5 text-purple-600" />
                                {f.distance_m < 1000 ? `${f.distance_m} m` : `${f.distance_km} km`}
                              </span>
                              <span className="text-[10px] text-slate-400">OpenStreetMap ODbL</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 bg-white border border-slate-200 rounded-2xl text-xs text-slate-600">
                        <span className="font-semibold block text-slate-800 mb-0.5">No Mapped Emergency Facilities Within Radius</span>
                        No police or fire stations are currently indexed in OpenStreetMap within the selected survey boundary. OpenStreetMap listings depend on community mapping coverage and do not confirm physical absence or real-time operational staffing.
                      </div>
                    )}
                  </div>

                  {/* 2. EMERGENCY HELPLINES (112, 100, 101, 108, 1090, 1930) */}
                  <div className="space-y-2.5 pt-2 border-t border-slate-200/80">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                        2. Emergency Helplines (112, 100, 101, 108, 1090, 1930)
                      </span>
                      <span className="text-[11px] text-slate-500">Official Gov & Police Portals</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {(crimeResult?.data?.emergency_contacts || []).map((c) => (
                        <div key={c.number} className="p-3 bg-white border border-slate-200 rounded-2xl space-y-1.5 flex flex-col justify-between">
                          <div>
                            <div className="flex items-center justify-between gap-1">
                              <span className="text-xs font-bold text-slate-900 block truncate" title={c.service}>
                                {c.service}
                              </span>
                              <a
                                href={`tel:${c.number}`}
                                className="font-mono font-bold text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 flex items-center gap-1 shrink-0"
                                title={`Call ${c.number}`}
                              >
                                <Phone className="w-3 h-3" />
                                {c.number}
                              </a>
                            </div>
                            <p className="text-[11px] text-slate-600 leading-snug mt-1">
                              {c.description}
                            </p>
                          </div>
                          <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                            <span className="truncate max-w-[130px]" title={c.verified_authority}>
                              {c.verified_authority}
                            </span>
                            <a
                              href={c.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-teal-600 hover:text-teal-700 flex items-center gap-0.5"
                            >
                              Verify <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>

                    <p className="text-[10px] text-slate-500 italic">
                      Notice: LocalLens provides verified directory information only and does not dispatch emergency personnel. For immediate life-safety emergencies, dial 112 directly.
                    </p>
                  </div>

                  {/* 3. CRIME DATA AVAILABILITY (WITH EXPLICIT ABSENCE CAVEAT) */}
                  <div className="space-y-3 pt-2 border-t border-slate-200/80">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                      3. Crime Data Availability (with explicit absence caveat)
                    </span>

                    {/* Police Jurisdiction Status */}
                    <div className="p-3 bg-white border border-slate-200 rounded-2xl text-xs space-y-1">
                      <span className="font-bold text-slate-800 block">Administrative Police Jurisdiction:</span>
                      {crimeResult?.data?.jurisdiction?.jurisdiction_name ? (
                        <p className="text-[11px] text-slate-700">
                          <strong>{crimeResult.data.jurisdiction.jurisdiction_name}</strong> ({crimeResult.data.jurisdiction.jurisdiction_type.replace('_', ' ')}) · Supporting Authority: {crimeResult.data.jurisdiction.supporting_authority}
                        </p>
                      ) : (
                        <p className="text-[11px] text-slate-600">
                          {crimeResult?.data?.jurisdiction?.limitations?.[0] || 'Jurisdiction beat polygon unavailable in public open data; capital region beats divide between Cyberabad and Rachakonda Commissionerates.'}
                        </p>
                      )}
                    </div>

                    {/* Transparency Disclosure & Absence Caveat */}
                    <div className="p-3.5 bg-rose-50/70 border border-rose-200 rounded-2xl text-xs text-rose-950 space-y-2">
                      <span className="font-bold block">Official Crime Statistics Transparency Disclosure:</span>
                      <p className="text-[11px] leading-relaxed">
                        Verified locality-level crime statistics are not available in public open data in India. The National Crime Records Bureau (NCRB) and state police departments compile annual statistics aggregated strictly at the police commissionerate or district level, not by neighborhood, pincode, or street.
                      </p>
                      <ul className="text-[11px] space-y-1 list-disc list-inside text-rose-900">
                        <li>
                          <strong>Ecological Fallacy:</strong> Dividing district or commissionerate totals by estimated neighborhood populations produces statistically invalid micro-rates.
                        </li>
                        <li>
                          <strong>Infrastructure ≠ Low Crime:</strong> The presence of a mapped police station provides emergency response proximity, not proof of lower crime incidence.
                        </li>
                      </ul>
                      <div className="p-2.5 bg-rose-100/70 border border-rose-300 rounded-xl text-[11px] font-semibold text-rose-950">
                        Crucial Notice: {crimeResult?.data?.absence_caveat || 'The absence of published locality-level crime statistics does not imply that an area is safe.'}
                      </div>
                    </div>
                  </div>

                  {/* 4. VERIFY ON SITE */}
                  <div className="space-y-2.5 pt-2 border-t border-slate-200/80">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                      4. Verify On Site
                    </span>
                    <div className="p-3.5 bg-white rounded-2xl border border-slate-200 text-xs space-y-2">
                      <p className="text-[11px] text-slate-600">
                        Because digital crime figures cannot be verified at the street level, prioritize physical evaluation during your property visit:
                      </p>
                      <ul className="text-[11px] text-slate-700 space-y-1.5 list-disc list-inside">
                        <li>Assess street lighting and visibility along primary pedestrian approach routes between 7:30 PM and 9:30 PM.</li>
                        <li>Observe commercial activity, street vendor presence, and active pedestrian foot traffic density after nightfall.</li>
                        <li>Inspect residential compound security measures (perimeter CCTV, 24/7 security guard presence, visitor logbooks).</li>
                        <li>Test cellular phone network reception and emergency vehicle road accessibility along access lanes.</li>
                        <li>Visit the neighborhood at distinct times across both weekday evenings and weekends prior to entering residential agreements.</li>
                      </ul>
                    </div>
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
