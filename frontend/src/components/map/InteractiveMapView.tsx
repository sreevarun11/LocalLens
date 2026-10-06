import React, { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { Layers, Navigation, MapPin, X } from 'lucide-react';
import { PlaceItem, LocationDetails, CategoryKey } from '../../types';

interface InteractiveMapViewProps {
  location: LocationDetails | null;
  places?: PlaceItem[];
  selectedPlace?: PlaceItem | null;
  onSelectPlace?: (place: PlaceItem | null) => void;
  radiusM?: number;
  activeCategories?: string[];
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

export const InteractiveMapView: React.FC<InteractiveMapViewProps> = ({
  location,
  places = [],
  selectedPlace = null,
  onSelectPlace,
  radiusM = 1500,
  activeCategories,
  className = ''
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [mapType, setMapType] = useState<'google' | 'osm'>('osm');
  const [googleMapLoaded, setGoogleMapLoaded] = useState(false);
  const googleMapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const circleRef = useRef<any>(null);
  const centerMarkerRef = useRef<any>(null);
  const [activePopupPlace, setActivePopupPlace] = useState<PlaceItem | null>(null);

  const googleKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY;

  // Filter places by active categories if specified
  const filteredPlaces = places.filter(
    (p) => !activeCategories || activeCategories.length === 0 || activeCategories.includes(p.category)
  );

  // Initialize Google Maps if key is available
  useEffect(() => {
    if (!googleKey) {
      setMapType('osm');
      return;
    }

    const loader = new Loader({
      apiKey: googleKey,
      version: 'weekly',
      libraries: ['places']
    });

    loader.load().then(() => {
      setGoogleMapLoaded(true);
      setMapType('google');
    }).catch((err) => {
      console.warn('Google Maps JS Loader failed, falling back to OSM view:', err);
      setMapType('osm');
    });
  }, [googleKey]);

  // Handle Google Maps updates
  useEffect(() => {
    if (mapType !== 'google' || !googleMapLoaded || !mapContainerRef.current || !location) return;

    const center = { lat: location.lat, lng: location.lng };
    const google = (window as any).google;

    if (!googleMapInstanceRef.current) {
      googleMapInstanceRef.current = new google.maps.Map(mapContainerRef.current, {
        center,
        zoom: 14,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        styles: [
          { featureType: 'poi', stylers: [{ visibility: 'simplified' }] }
        ]
      });
    } else {
      googleMapInstanceRef.current.panTo(center);
    }

    const map = googleMapInstanceRef.current;

    // Prominent Center marker for Selected Location (Beacon)
    if (centerMarkerRef.current) {
      centerMarkerRef.current.setMap(null);
    }
    centerMarkerRef.current = new google.maps.Marker({
      position: center,
      map,
      title: `Selected Location: ${location.name}`,
      zIndex: 999,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#0f766e',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 3.5
      }
    });

    // Update Radius Circle (1,500m survey boundary)
    if (circleRef.current) {
      circleRef.current.setMap(null);
    }
    circleRef.current = new google.maps.Circle({
      strokeColor: '#0f766e',
      strokeOpacity: 0.7,
      strokeWeight: 2,
      fillColor: '#0f766e',
      fillOpacity: 0.06,
      map,
      center,
      radius: radiusM
    });

    // Clear old place markers
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    // Create markers for filtered places
    filteredPlaces.forEach((p) => {
      const color = CATEGORY_COLORS[p.category]?.markerColor || '#475569';
      const isSelected = selectedPlace?.id === p.id;
      const marker = new google.maps.Marker({
        position: { lat: p.lat, lng: p.lng },
        map,
        title: p.name,
        zIndex: isSelected ? 500 : 100,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: isSelected ? 8 : 5.5,
          fillColor: color,
          fillOpacity: 0.95,
          strokeColor: isSelected ? '#0f172a' : '#ffffff',
          strokeWeight: isSelected ? 2.5 : 1.5
        }
      });

      marker.addListener('click', () => {
        setActivePopupPlace(p);
        if (onSelectPlace) onSelectPlace(p);
      });

      markersRef.current.push(marker);
    });
  }, [mapType, googleMapLoaded, location, filteredPlaces, radiusM, selectedPlace]);

  // Sync external selection with map
  useEffect(() => {
    if (selectedPlace) {
      setActivePopupPlace(selectedPlace);
      if (googleMapInstanceRef.current) {
        googleMapInstanceRef.current.panTo({ lat: selectedPlace.lat, lng: selectedPlace.lng });
      }
    }
  }, [selectedPlace]);

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

  // Bounding box for OSM tile embed
  const delta = 0.015;
  const minLng = location.lng - delta;
  const maxLng = location.lng + delta;
  const minLat = location.lat - delta;
  const maxLat = location.lat + delta;
  const bbox = `${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}`;
  const osmEmbedUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${location.lat}%2C${location.lng}`;

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
          <span className="font-semibold capitalize">
            {mapType === 'google' ? 'Google Maps' : 'OpenStreetMap'}
          </span>
        </div>
      </div>

      {/* Map Canvas / Frame */}
      {mapType === 'google' ? (
        <div ref={mapContainerRef} className="w-full h-full min-h-[460px]" />
      ) : (
        <div className="relative w-full h-full min-h-[460px] bg-slate-100 overflow-hidden">
          <iframe
            title="OpenStreetMap View"
            src={osmEmbedUrl}
            className="w-full h-full min-h-[460px] border-0 pointer-events-none"
            loading="lazy"
          />

          {/* Interactive Overlay for OSM Fallback: Prominent Selected Location Beacon */}
          <div
            className="absolute z-10 -translate-x-1/2 -translate-y-1/2 pointer-events-auto cursor-pointer"
            style={{ left: '50%', top: '50%' }}
            title={`Selected Location: ${location.name}`}
          >
            <div className="relative flex items-center justify-center">
              <span className="animate-ping absolute inline-flex h-10 w-10 rounded-full bg-teal-400 opacity-75" />
              <div className="relative z-10 w-6 h-6 rounded-full bg-teal-700 border-2 border-white shadow-lg flex items-center justify-center">
                <MapPin className="w-3.5 h-3.5 text-white" />
              </div>
            </div>
            <div className="absolute top-7 left-1/2 -translate-x-1/2 whitespace-nowrap bg-navy-900 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow">
              {location.name.split(',')[0]}
            </div>
          </div>

          {/* Survey Radius Boundary Overlay Ring */}
          <div
            className="absolute rounded-full border-2 border-teal-600/40 bg-teal-600/5 pointer-events-none -translate-x-1/2 -translate-y-1/2"
            style={{
              left: '50%',
              top: '50%',
              width: '64%',
              height: '64%'
            }}
          />

          {/* Interactive Nearby Place Pins Overlay in OSM mode */}
          {filteredPlaces.slice(0, 30).map((place) => {
            const leftPct = ((place.lng - minLng) / (2 * delta)) * 100;
            const topPct = ((maxLat - place.lat) / (2 * delta)) * 100;
            if (leftPct < 5 || leftPct > 95 || topPct < 5 || topPct > 95) return null;

            const isSelected = selectedPlace?.id === place.id;
            const catMeta = CATEGORY_COLORS[place.category];
            const markerColor = catMeta?.markerColor || '#475569';

            return (
              <button
                key={place.id}
                type="button"
                onClick={() => {
                  setActivePopupPlace(place);
                  if (onSelectPlace) onSelectPlace(place);
                }}
                className={`absolute z-10 -translate-x-1/2 -translate-y-1/2 transition-transform hover:scale-125 focus:outline-none cursor-pointer ${
                  isSelected ? 'scale-125 z-20' : ''
                }`}
                style={{ left: `${leftPct}%`, top: `${topPct}%` }}
                title={`${place.name} (${place.distance_m}m)`}
              >
                <div
                  className={`w-3.5 h-3.5 rounded-full border-2 ${
                    isSelected ? 'border-navy-900 shadow-md ring-2 ring-teal-400' : 'border-white shadow-xs'
                  }`}
                  style={{ backgroundColor: markerColor }}
                />
              </button>
            );
          })}

          {/* OpenStreetMap Attribution */}
          <div className="absolute bottom-2 left-2 z-10 bg-white/90 backdrop-blur-xs px-2 py-1 rounded-md text-[10px] text-slate-600 border border-slate-200">
            Map tiles © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" className="underline text-teal-700">OpenStreetMap contributors</a>
          </div>
        </div>
      )}

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
              className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
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
