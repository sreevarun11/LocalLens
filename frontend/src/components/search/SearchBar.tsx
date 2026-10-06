import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Navigation, Loader2, X, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';
import { AutocompletePrediction, LocationDetails } from '../../types';

interface SearchBarProps {
  onLocationSelected: (location: LocationDetails) => void;
  placeholder?: string;
  initialValue?: string;
  className?: string;
  autoFocus?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onLocationSelected,
  placeholder = 'Search a locality, landmark or PIN code…',
  initialValue = '',
  className = '',
  autoFocus = false,
}) => {
  const [query, setQuery] = useState(initialValue);
  const [predictions, setPredictions] = useState<AutocompletePrediction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const sessionTokenRef = useRef<string>(Math.random().toString(36).substring(2, 15));
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search logic (350ms)
  useEffect(() => {
    if (query.trim().length < 2) {
      setPredictions([]);
      setIsOpen(false);
      setIsLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    const timeoutId = setTimeout(async () => {
      try {
        const results = await api.getAutocomplete(
          query,
          sessionTokenRef.current,
          abortControllerRef.current?.signal
        );
        setPredictions(results);
        setIsOpen(results.length > 0);
        setActiveIndex(-1);
      } catch (err) {
        console.error('Error in search debounce:', err);
      } finally {
        setIsLoading(false);
      }
    }, 350);

    return () => clearTimeout(timeoutId);
  }, [query]);

  const handleSelectPrediction = async (pred: AutocompletePrediction) => {
    setQuery(pred.description);
    setIsOpen(false);
    setIsLoading(true);
    setGeoError(null);

    try {
      const details = await api.getLocationDetails(pred.place_id, sessionTokenRef.current);
      // Reset session token after successful selection
      sessionTokenRef.current = Math.random().toString(36).substring(2, 15);
      onLocationSelected(details);
    } catch (err: any) {
      setGeoError('Could not load details for this location. Please try another.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseCurrentLocation = () => {
    setGeoError(null);

    // Browser restriction check (Geolocation requires HTTPS or localhost)
    if (typeof window !== 'undefined' && window.isSecureContext === false && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      setGeoError('Location access requires a secure connection (HTTPS) or localhost. Search for a location manually instead.');
      return;
    }

    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser. Search for a location manually instead.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          const details = await api.reverseGeocode(lat, lng);
          setQuery(details.formatted_address || details.name);
          setGeoError(null);
          onLocationSelected(details);
        } catch (err) {
          setGeoError('Unable to identify your locality from current coordinates. Search for a location manually instead.');
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError('Location access was denied. Search for a location manually instead.');
        } else if (err.code === err.TIMEOUT) {
          setGeoError('Location signal timed out. Search for a location manually instead.');
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          setGeoError('Location information is unavailable. Search for a location manually instead.');
        } else {
          setGeoError('Unable to detect your current location. Search for a location manually instead.');
        }
      },
      { timeout: 10000, enableHighAccuracy: true, maximumAge: 0 }
    );
  };

  const handleManualSearchFocus = () => {
    setGeoError(null);
    inputRef.current?.focus();
  };

  // Keyboard navigation for ARIA combobox
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || predictions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev < predictions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : predictions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < predictions.length) {
        handleSelectPrediction(predictions[activeIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const handleDemoSelect = (demoText: string) => {
    setQuery(demoText);
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      {/* Input container */}
      <div className="relative flex items-center">
        <div className="absolute left-4 pointer-events-none text-slate-400">
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-teal-600" />
          ) : (
            <Search className="w-5 h-5 text-teal-600" />
          )}
        </div>

        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-controls="location-results"
          aria-activedescendant={activeIndex >= 0 ? `loc-result-${activeIndex}` : undefined}
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => predictions.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-12 pr-28 py-3.5 bg-white text-slate-900 placeholder-slate-400 text-base rounded-2xl border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10 outline-none transition-all"
        />

        {/* Clear and GPS buttons */}
        <div className="absolute right-3 flex items-center gap-1.5">
          {query && (
            <button
              onClick={() => {
                setQuery('');
                setPredictions([]);
                setIsOpen(false);
              }}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg"
              title="Clear search"
              type="button"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={handleUseCurrentLocation}
            disabled={isLocating}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors disabled:opacity-50"
            title="Use current location"
            type="button"
          >
            {isLocating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-600" />
            ) : (
              <Navigation className="w-3.5 h-3.5 text-teal-600" />
            )}
            <span className="hidden sm:inline">GPS</span>
          </button>
        </div>
      </div>

      {/* Geolocation feedback / error */}
      {geoError && (
        <div className="mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span className="font-medium">{geoError}</span>
          </div>
          <button
            type="button"
            onClick={handleManualSearchFocus}
            className="px-3 py-1 bg-amber-800 hover:bg-amber-900 text-white rounded-lg text-[11px] font-semibold transition-colors shrink-0 self-start sm:self-auto cursor-pointer"
          >
            Search manually
          </button>
        </div>
      )}

      {/* Autocomplete Dropdown */}
      {isOpen && predictions.length > 0 && (
        <ul
          id="location-results"
          role="listbox"
          className="absolute z-50 left-0 right-0 mt-2 bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden divide-y divide-slate-100 animate-in fade-in-50 duration-150"
        >
          {predictions.map((pred, idx) => (
            <li
              key={pred.place_id}
              id={`loc-result-${idx}`}
              role="option"
              aria-selected={idx === activeIndex}
              onClick={() => handleSelectPrediction(pred)}
              onMouseEnter={() => setActiveIndex(idx)}
              className={`p-3.5 flex items-start gap-3 cursor-pointer transition-colors ${
                idx === activeIndex ? 'bg-teal-50/80 text-teal-950' : 'hover:bg-slate-50 text-slate-800'
              }`}
            >
              <MapPin className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate text-slate-900">
                  {pred.main_text}
                </p>
                {pred.secondary_text && (
                  <p className="text-xs text-slate-500 truncate mt-0.5">
                    {pred.secondary_text}
                  </p>
                )}
              </div>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full shrink-0">
                {pred.provider}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Demo Search Chips (Live resolution only, never hardcoded coordinates) */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <span className="font-medium text-slate-400">Demo localities:</span>
        <button
          type="button"
          onClick={() => handleDemoSelect('Koramangala, Bengaluru')}
          className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors font-medium shadow-2xs"
        >
          Koramangala, BLR (Rich)
        </button>
        <button
          type="button"
          onClick={() => handleDemoSelect('Indiranagar, Bengaluru')}
          className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors font-medium shadow-2xs"
        >
          Indiranagar, BLR (Comparable)
        </button>
        <button
          type="button"
          onClick={() => handleDemoSelect('Chandapura, Bengaluru')}
          className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors font-medium shadow-2xs"
        >
          Chandapura, BLR (Gaps)
        </button>
      </div>
    </div>
  );
};
