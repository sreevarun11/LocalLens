export type StatusKind = 'available' | 'limited' | 'unavailable' | 'error';

export type ProvenanceKind =
  | 'station_measurement'
  | 'official_dataset'
  | 'map_listing'
  | 'modeled_estimate'
  | 'user_provided'
  | 'derived';

export type CategoryKey =
  | 'healthcare'
  | 'education'
  | 'safety_infrastructure'
  | 'daily_life'
  | 'transport'
  | 'lifestyle';

export interface DataSourceInfo {
  name: string;
  url?: string | null;
  license?: string | null;
  attribution?: string | null;
}

export interface Coverage {
  granularity:
    | 'exact_place'
    | 'nearby_place'
    | 'monitoring_station'
    | 'city'
    | 'district'
    | 'state'
    | 'unknown';
  radius_m?: number | null;
  result_count?: number | null;
  result_cap_reached?: boolean | null;
  nearest_distance_m?: number | null;
  station_distance_m?: number | null;
  note?: string | null;
}

export interface ModuleResult<T> {
  module: string;
  status: StatusKind;
  provenance_kind: ProvenanceKind;
  data: T | null;
  sources: DataSourceInfo[];
  coverage: Coverage;
  fetched_at: string;
  source_updated_at?: string | null;
  measured_at?: string | null;
  limitations: string[];
  message?: string | null;
  served_from: 'live' | 'demo_snapshot';
}

export interface Coordinates {
  lat: float;
  lng: float;
}

type float = number;

export interface AutocompletePrediction {
  place_id: string;
  description: string;
  main_text: string;
  secondary_text?: string | null;
  provider: string;
}

export interface CanonicalLocation {
  place_id: string;
  formatted_address: string;
  name: string;
  latitude: number;
  longitude: number;
  lat: number;
  lng: number;
  district?: string | null;
  locality?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
  provider: string;
}

export type LocationDetails = CanonicalLocation;

export interface PlaceItem {
  id: string;
  name: string;
  category: CategoryKey;
  subcategory?: string | null;
  lat: number;
  lng: number;
  distance_m: number;
  address?: string | null;
  rating?: number | null;
  user_ratings_total?: number | null;
  source_name: string;
  source_attribution?: string | null;
}

export interface PlacesData {
  places: PlaceItem[];
  counts_by_category: Record<string, number>;
  radius_m: number;
  cap_reached: boolean;
}

export interface AirQualityData {
  aqi?: number | null;
  aqi_scale: string;
  pm25?: number | null;
  pm10?: number | null;
  co?: number | null;
  no2?: number | null;
  o3?: number | null;
  so2?: number | null;
  station_name?: string | null;
  station_distance_m?: number | null;
  station_coordinates?: Coordinates | null;
  model_grid_resolution_km?: number | null;
  dominant_pollutant?: string | null;
  advisory?: string | null;
}

export interface WaterQualityData {
  sample_count: number;
  tds_mg_l?: number | null;
  ph?: number | null;
  hardness_mg_l?: number | null;
  sample_date?: string | null;
  data_level: string;
}

export interface CrimeData {
  incident_count?: number | null;
  rate_per_100k?: number | null;
  data_granularity: string;
  reporting_year?: number | null;
  source_agency?: string | null;
}

export interface CommuteModeResult {
  mode: 'driving' | 'transit' | 'walking' | 'two_wheeler';
  duration_min?: number | null;
  distance_km?: number | null;
  status: StatusKind;
  route_summary?: string | null;
  provider: string;
  fare?: string | null;
}

export interface CommuteData {
  destination_name: string;
  destination_coords?: Coordinates | null;
  modes: Record<string, CommuteModeResult>;
}

// User Profiles & Priorities (Section 8)
export type ProfileKey =
  | 'family'
  | 'commuter'
  | 'student'
  | 'elderly'
  | 'first_time_renter'
  | 'home_buyer'
  | 'relocation';

export type PriorityKey =
  | 'education'
  | 'healthcare'
  | 'transport'
  | 'daily_life'
  | 'parks'
  | 'lifestyle'
  | 'environment'
  | 'safety_infrastructure'
  | 'commute';

export interface DistancePreference {
  priority: PriorityKey;
  preferred_distance_m: number;
  label: string;
}

export interface FindingItem {
  id: string;
  priority: PriorityKey;
  status: StatusKind;
  headline: string;
  detail: string;
  metric_name: string;
  metric_value: string | number;
  within_preference?: 'yes' | 'no' | 'unknown';
  preference_note?: string;
  evidence_ids: string[];
  entities?: Array<{ name: string; distance_m: number }>;
}

export interface VerifyOnSiteQuestion {
  id: string;
  priority_or_gap: string;
  question: string;
  context: string;
}

export interface PriorityGapCallout {
  priority: PriorityKey;
  gap_description: string;
  available_facts: string;
  missing_data: string;
}

export interface EvidenceEntity {
  name: string;
  place_id?: string | null;
  lat: number;
  lng: number;
  distance_m: number;
  category: string;
}

export interface EvidenceItem {
  id: string;
  locality_key: string;
  module: string;
  metric: string;
  value?: number | string | null;
  unit?: string | null;
  radius_m?: number | null;
  result_cap_reached?: boolean | null;
  entities: EvidenceEntity[];
  provenance_kind: string;
  granularity: string;
  source: DataSourceInfo;
  fetched_at: string;
  measured_at?: string | null;
  source_updated_at?: string | null;
  limitations: string[];
}

export interface EvidenceGap {
  module: string;
  reason: string;
  granularity_needed: string;
}
