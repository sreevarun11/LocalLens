import React, { useEffect, useRef, useState } from 'react';
import {
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  NavigationControl,
  GeoJSONSource,
  LngLatBounds,
  setWorkerUrl
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import maplibreglWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { Layers, Navigation, X, AlertCircle } from 'lucide-react';
import { PlaceItem, LocationDetails, CategoryKey } from '../../types';

// Explicitly configure worker URL for Vite bundler compatibility
setWorkerUrl(maplibreglWorkerUrl);

interface InteractiveMapViewProps {
  location: LocationDetails | null;
  places?: PlaceItem[];
  selectedPlace?: PlaceItem | null;
  onSelectPlace?: (place: PlaceItem | null) => void;
  radiusM?: number;
  activeCategories?: string[];
  routeGeometry?: [number, number][] | null;
  routeDestinationName?: string | null;
  className?: string;
}

const CATEGORY_COLORS: Record<CategoryKey, { bg: string; border: string; markerColor: string; label: string }> = {
  healthcare: { bg: 'bg-rose-500', border: 'border-rose-600', markerColor: '#e11d48', label: 'Healthcare' },
  education: { bg: 'bg-blue-500', border: 'border-blue-600', markerColor: '#2563eb', label: 'Education' },
  safety_infrastructure: { bg: 'bg-purple-500', border: 'border-purple-600', markerColor: '#9333ea', label: 'Safety Infra' },
  daily_life: { bg: 'bg-amber-500', border: 'border-amber-600', markerColor: '#d97706', label: 'Daily Life' },
  transport: { bg: 'bg-emerald-500', border: 'border-emerald-600', markerColor: '#059669', label: 'Transport' },
  lifestyle: { bg: 'bg-teal-500', border: 'border-teal-600', markerColor: '#0d9488', label: 'Lifestyle' }
};

/**
 * Generates an accurate GeoJSON circle polygon (64 vertices)
 * using standard spherical geodesic formulas.
 */
function createGeoJSONCircle(
  center: [number, number],
  radiusInMeters: number,
  points = 64
): GeoJSON.Feature<GeoJSON.Polygon> {
  const coords: [number, number][] = [];
  const [lng, lat] = center;
  const earthRadius = 6371008.8; // meters
  const latRad = (lat * Math.PI) / 180;
  const lngRad = (lng * Math.PI) / 180;
  const dByR = radiusInMeters / earthRadius;

  for (let i = 0; i <= points; i++) {
    const bearing = (i * 2 * Math.PI) / points;
    const pointLatRad = Math.asin(
      Math.sin(latRad) * Math.cos(dByR) +
      Math.cos(latRad) * Math.sin(dByR) * Math.cos(bearing)
    );
    const pointLngRad = lngRad + Math.atan2(
      Math.sin(bearing) * Math.sin(dByR) * Math.cos(latRad),
      Math.cos(dByR) - Math.sin(latRad) * Math.sin(pointLatRad)
    );
    coords.push([(pointLngRad * 180) / Math.PI, (pointLatRad * 180) / Math.PI]);
  }

  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Polygon',
      coordinates: [coords]
    }
  };
}

export const InteractiveMapView: React.FC<InteractiveMapViewProps> = ({
  location,
  places = [],
  selectedPlace = null,
  onSelectPlace,
  radiusM = 1500,
  activeCategories,
  routeGeometry = null,
  routeDestinationName = null,
  className = ''
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<MapLibreMarker[]>([]);
  const centerMarkerRef = useRef<MapLibreMarker | null>(null);
  const routeDestMarkerRef = useRef<MapLibreMarker | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [activePopupPlace, setActivePopupPlace] = useState<PlaceItem | null>(null);

  const styleUrl = import.meta.env.VITE_MAP_STYLE_URL || 'https://tiles.openfreemap.org/styles/liberty';

  // Filter places by active categories if specified
  const filteredPlaces = places.filter(
    (p) => !activeCategories || activeCategories.length === 0 || activeCategories.includes(p.category)
  );

  // Initialize MapLibre map instance
  useEffect(() => {
    if (!mapContainerRef.current || !location) return;

    setMapError(null);
    setMapLoaded(false);

    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container: mapContainerRef.current,
        style: styleUrl,
        center: [location.lng, location.lat],
        zoom: 14,
        attributionControl: false
      });
    } catch (err: any) {
      console.error('Failed to initialize MapLibre GL:', err);
      setMapError('Unable to initialize WebGL map canvas. Please verify hardware acceleration is enabled.');
      return;
    }

    // Add navigation controls (zoom in/out)
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');

    map.on('load', () => {
      // Add survey radius circle polygon source and layers
      if (!map.getSource('survey-radius')) {
        map.addSource('survey-radius', {
          type: 'geojson',
          data: createGeoJSONCircle([location.lng, location.lat], radiusM)
        });

        map.addLayer({
          id: 'survey-radius-fill',
          type: 'fill',
          source: 'survey-radius',
          paint: {
            'fill-color': '#0f766e',
            'fill-opacity': 0.08
          }
        });

        map.addLayer({
          id: 'survey-radius-stroke',
          type: 'line',
          source: 'survey-radius',
          paint: {
            'line-color': '#0f766e',
            'line-width': 2,
            'line-opacity': 0.65
          }
        });

        // Commute Road Route GeoJSON Source and Layers
        map.addSource('commute-route', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'LineString',
              coordinates: []
            }
          }
        });

        map.addLayer({
          id: 'commute-route-casing',
          type: 'line',
          source: 'commute-route',
          layout: {
            'line-join': 'round',
            'line-cap': 'round'
          },
          paint: {
            'line-color': '#0f172a',
            'line-width': 6,
            'line-opacity': 0.7
          }
        });

        map.addLayer({
          id: 'commute-route-line',
          type: 'line',
          source: 'commute-route',
          layout: {
            'line-join': 'round',
            'line-cap': 'round'
          },
          paint: {
            'line-color': '#0284c7',
            'line-width': 4,
            'line-opacity': 0.95
          }
        });
      }

      setMapLoaded(true);
    });

    map.on('error', (e: { error?: { message?: string } }) => {
      const msg = e.error?.message || '';
      console.warn('MapLibre error event:', e);
      if (msg.includes('WebGL')) {
        setMapError('WebGL rendering error. Your browser may have disabled hardware acceleration.');
      } else if (msg.includes('Worker failed to load')) {
        setMapError(`MapLibre Web Worker failed to load: ${msg}`);
      } else if (msg.toLowerCase().includes('style') && (msg.includes('fetch') || msg.includes('parse') || msg.includes('Failed'))) {
        setMapError(`Failed to load map style (${styleUrl}): ${msg}`);
      }
    });

    mapInstanceRef.current = map;

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      if (centerMarkerRef.current) {
        centerMarkerRef.current.remove();
        centerMarkerRef.current = null;
      }
      if (routeDestMarkerRef.current) {
        routeDestMarkerRef.current.remove();
        routeDestMarkerRef.current = null;
      }
      map.remove();
      mapInstanceRef.current = null;
      setMapLoaded(false);
    };
  }, [location?.place_id, styleUrl]);

  // Update center position and survey radius when location or radius changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapLoaded || !location) return;

    const centerCoords: [number, number] = [location.lng, location.lat];

    // Fly to updated coordinates
    map.flyTo({
      center: centerCoords,
      essential: true
    });

    // Update survey radius GeoJSON polygon
    const circleSource = map.getSource('survey-radius') as GeoJSONSource | undefined;
    if (circleSource) {
      circleSource.setData(createGeoJSONCircle(centerCoords, radiusM));
    }

    // Update center beacon marker
    if (centerMarkerRef.current) {
      centerMarkerRef.current.remove();
      centerMarkerRef.current = null;
    }

    const beaconEl = document.createElement('div');
    beaconEl.className = 'relative flex items-center justify-center cursor-pointer';
    beaconEl.title = `Selected Location: ${location.name}`;
    beaconEl.innerHTML = `
      <span class="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-teal-400 opacity-75"></span>
      <div class="relative z-10 w-6 h-6 rounded-full bg-teal-700 border-2 border-white shadow-lg flex items-center justify-center">
        <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
        </svg>
      </div>
    `;

    centerMarkerRef.current = new MapLibreMarker({ element: beaconEl, anchor: 'center' })
      .setLngLat(centerCoords)
      .addTo(map);
  }, [location, radiusM, mapLoaded]);

  // Update place markers when places, active categories, or selection changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapLoaded) return;

    // Clear old place markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    filteredPlaces.forEach((place) => {
      if (
        typeof place.lat !== 'number' ||
        typeof place.lng !== 'number' ||
        isNaN(place.lat) ||
        isNaN(place.lng)
      ) {
        return;
      }

      const isSelected = selectedPlace?.id === place.id;
      const catMeta = CATEGORY_COLORS[place.category];
      const markerColor = catMeta?.markerColor || '#475569';

      const markerEl = document.createElement('button');
      markerEl.type = 'button';
      markerEl.title = `${place.name} (${place.distance_m}m)`;
      markerEl.className = `group cursor-pointer transition-transform duration-150 hover:scale-125 focus:outline-none ${
        isSelected ? 'scale-125 z-20' : 'z-10'
      }`;

      const pinDot = document.createElement('div');
      pinDot.className = `w-4 h-4 rounded-full border-2 ${
        isSelected
          ? 'border-slate-900 shadow-md ring-2 ring-teal-400 scale-110'
          : 'border-white shadow-xs'
      }`;
      pinDot.style.backgroundColor = markerColor;
      markerEl.appendChild(pinDot);

      markerEl.addEventListener('click', (e) => {
        e.stopPropagation();
        setActivePopupPlace(place);
        if (onSelectPlace) onSelectPlace(place);
      });

      const marker = new MapLibreMarker({ element: markerEl, anchor: 'center' })
        .setLngLat([place.lng, place.lat])
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [filteredPlaces, selectedPlace?.id, mapLoaded, onSelectPlace]);

  // Pan to externally selected place
  useEffect(() => {
    if (selectedPlace) {
      setActivePopupPlace(selectedPlace);
      const map = mapInstanceRef.current;
      if (map && mapLoaded && typeof selectedPlace.lng === 'number' && typeof selectedPlace.lat === 'number') {
        map.flyTo({
          center: [selectedPlace.lng, selectedPlace.lat],
          zoom: Math.max(map.getZoom(), 14.5),
          essential: true
        });
      }
    }
  }, [selectedPlace, mapLoaded]);

  // Handle route geometry updates and bounds fitting
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapLoaded) return;

    const routeSource = map.getSource('commute-route') as GeoJSONSource | undefined;
    if (!routeSource) return;

    if (routeGeometry && routeGeometry.length > 1) {
      routeSource.setData({
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: routeGeometry
        }
      });

      // Fit bounds to encompass the entire route
      const bounds = routeGeometry.reduce(
        (b, coord) => b.extend(coord as [number, number]),
        new LngLatBounds(routeGeometry[0] as [number, number], routeGeometry[0] as [number, number])
      );
      map.fitBounds(bounds, { padding: 60, maxZoom: 15 });

      // Add/update destination marker at the last coordinate
      if (routeDestMarkerRef.current) {
        routeDestMarkerRef.current.remove();
        routeDestMarkerRef.current = null;
      }
      const destCoord = routeGeometry[routeGeometry.length - 1];
      const destEl = document.createElement('div');
      destEl.className = 'w-6 h-6 rounded-full bg-rose-600 border-2 border-white shadow-lg flex items-center justify-center text-white text-[10px] font-bold';
      destEl.title = routeDestinationName || 'Route Destination';
      destEl.innerHTML = '★';

      const destMarker = new MapLibreMarker({ element: destEl, anchor: 'center' })
        .setLngLat(destCoord as [number, number])
        .addTo(map);
      routeDestMarkerRef.current = destMarker;

    } else {
      routeSource.setData({
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: []
        }
      });
      if (routeDestMarkerRef.current) {
        routeDestMarkerRef.current.remove();
        routeDestMarkerRef.current = null;
      }
    }
  }, [routeGeometry, routeDestinationName, mapLoaded]);

  // If no location has been selected yet
  if (!location) {
    return (
      <div className={`relative bg-slate-100 rounded-3xl border border-slate-200 flex flex-col items-center justify-center p-8 text-center min-h-[440px] ${className}`}>
        <div className="w-14 h-14 bg-teal-50 border border-teal-200 rounded-2xl flex items-center justify-center text-teal-600 mb-3 shadow-xs">
          <Navigation className="w-7 h-7" />
        </div>
        <h3 className="font-display font-semibold text-base text-slate-800">
          No Locality Selected
        </h3>
        <p className="text-xs text-slate-500 max-w-xs mt-1">
          Search for an area or PIN code above to view interactive map boundaries, amenities, and evidence data.
        </p>
      </div>
    );
  }

  return (
    <div className={`relative bg-slate-900 rounded-3xl border border-slate-200 overflow-hidden shadow-xs flex flex-col ${className}`}>
      {/* Map Header Status & Mode Info */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        <div className="pointer-events-auto bg-white/95 backdrop-blur-xs px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-2 text-xs">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-bold text-slate-900 truncate max-w-[200px]">
            {location.name}
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-600 font-medium">
            {(radiusM / 1000).toFixed(1)} km Survey Radius
          </span>
        </div>

        <div className="pointer-events-auto bg-white/95 backdrop-blur-xs px-2.5 py-1.5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-1.5 text-xs text-slate-600">
          <Layers className="w-3.5 h-3.5 text-teal-600" />
          <span className="font-semibold">
            OpenFreeMap / OSM
          </span>
        </div>
      </div>

      {/* Map Canvas / Error State */}
      {mapError ? (
        <div className="w-full h-full min-h-[460px] bg-slate-100 flex flex-col items-center justify-center p-6 text-center">
          <AlertCircle className="w-8 h-8 text-amber-600 mb-2" />
          <p className="text-sm font-semibold text-slate-800">{mapError}</p>
          <p className="text-xs text-slate-500 max-w-xs mt-1">
            OpenStreetMap vector tiles require WebGL support.
          </p>
        </div>
      ) : (
        <div ref={mapContainerRef} className="w-full h-full min-h-[460px]" />
      )}

      {/* OpenFreeMap / OpenStreetMap Attribution */}
      <div className="absolute bottom-2 left-2 z-10 bg-white/90 backdrop-blur-xs px-2 py-1 rounded-md text-[10px] text-slate-600 border border-slate-200">
        Map tiles ©{' '}
        <a
          href="https://openfreemap.org"
          target="_blank"
          rel="noopener noreferrer"
          className="underline text-teal-700"
        >
          OpenFreeMap
        </a>{' '}
        | Data ©{' '}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noopener noreferrer"
          className="underline text-teal-700"
        >
          OpenStreetMap contributors
        </a>
      </div>

      {/* Selected Marker Popup / Details Card */}
      {activePopupPlace && (
        <div className="absolute bottom-4 left-4 right-4 z-30 sm:left-auto sm:right-4 sm:max-w-xs bg-white p-4 rounded-2xl border border-slate-200 shadow-xl animate-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full text-white ${
                  CATEGORY_COLORS[activePopupPlace.category]?.bg || 'bg-slate-600'
                }`}
              >
                {CATEGORY_COLORS[activePopupPlace.category]?.label || activePopupPlace.category}
              </span>
              <h4 className="font-display font-bold text-sm text-navy-900 mt-1 line-clamp-1">
                {activePopupPlace.name}
              </h4>
            </div>
            <button
              onClick={() => {
                setActivePopupPlace(null);
                if (onSelectPlace) onSelectPlace(null);
              }}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 cursor-pointer"
              title="Close popup"
              type="button"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-2 text-xs text-slate-600 space-y-1">
            {activePopupPlace.address && (
              <p className="text-[11px] text-slate-500 line-clamp-1">
                {activePopupPlace.address}
              </p>
            )}
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100 mt-2">
              <span className="font-semibold text-navy-900">
                {activePopupPlace.distance_m} m straight-line
              </span>
              <span className="text-slate-400">
                Source: {activePopupPlace.source_name}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
