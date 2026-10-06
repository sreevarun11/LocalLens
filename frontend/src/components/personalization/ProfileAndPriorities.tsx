import React, { useState } from 'react';
import {
  Users,
  Briefcase,
  GraduationCap,
  Heart,
  Key,
  Home,
  Compass,
  Sliders,
  Check,
  ChevronDown,
  ChevronUp,
  MapPin,
  Car,
  Bus,
  Footprints
} from 'lucide-react';
import {
  ProfileKey,
  PriorityKey,
  DistancePreference,
  CommuteData,
  Coordinates
} from '../../types';
import { SearchBar } from '../search/SearchBar';
import { api } from '../../services/api';

interface ProfileAndPrioritiesProps {
  currentProfile: ProfileKey;
  onProfileChange: (p: ProfileKey) => void;
  selectedPriorities: PriorityKey[];
  onPrioritiesChange: (priorities: PriorityKey[]) => void;
  distancePreferences: DistancePreference[];
  onDistancePreferencesChange: (prefs: DistancePreference[]) => void;
  localityCoords?: Coordinates | null;
  commuteData?: CommuteData | null;
  onCommuteUpdated?: (data: CommuteData | null) => void;
}

const PROFILES: { id: ProfileKey; label: string; icon: any; desc: string }[] = [
  { id: 'family', label: 'Family with Children', icon: Users, desc: 'Schools, healthcare, parks, daily essentials' },
  { id: 'commuter', label: 'Daily Commuter', icon: Briefcase, desc: 'Transit accessibility, commute time, arterial roads' },
  { id: 'student', label: 'Student', icon: GraduationCap, desc: 'Colleges, budget essentials, lifestyle, transit' },
  { id: 'elderly', label: 'Elderly Household', icon: Heart, desc: 'Quiet streets, hospitals, clinics, parks' },
  { id: 'first_time_renter', label: 'First-Time Renter', icon: Key, desc: 'Transit, supermarkets, cafes, commute' },
  { id: 'home_buyer', label: 'Home Buyer', icon: Home, desc: 'Long-term infrastructure, schools, hospitals, environment' },
  { id: 'relocation', label: 'Relocating', icon: Compass, desc: 'Balanced overview of healthcare, schools, and transport' },
];

const ALL_PRIORITIES: { key: PriorityKey; label: string; defaultDistM: number }[] = [
  { key: 'education', label: 'Education & Schools', defaultDistM: 1500 },
  { key: 'healthcare', label: 'Healthcare & Hospitals', defaultDistM: 3000 },
  { key: 'transport', label: 'Public Transit & Metro', defaultDistM: 800 },
  { key: 'daily_life', label: 'Daily Essentials & Groceries', defaultDistM: 1000 },
  { key: 'parks', label: 'Parks & Green Spaces', defaultDistM: 1200 },
  { key: 'lifestyle', label: 'Lifestyle & Cafes', defaultDistM: 1500 },
  { key: 'environment', label: 'Environment & Air', defaultDistM: 2000 },
  { key: 'safety_infrastructure', label: 'Safety Infrastructure', defaultDistM: 2500 },
  { key: 'commute', label: 'Work/College Commute', defaultDistM: 15000 },
];

export const ProfileAndPriorities: React.FC<ProfileAndPrioritiesProps> = ({
  currentProfile,
  onProfileChange,
  selectedPriorities,
  onPrioritiesChange,
  distancePreferences,
  onDistancePreferencesChange,
  localityCoords,
  commuteData,
  onCommuteUpdated,
}) => {
  const [showPreferences, setShowPreferences] = useState(false);
  const [showCommuteInput, setShowCommuteInput] = useState(false);
  const [isCalculatingCommute, setIsCalculatingCommute] = useState(false);

  const togglePriority = (key: PriorityKey) => {
    if (selectedPriorities.includes(key)) {
      if (selectedPriorities.length > 1) {
        onPrioritiesChange(selectedPriorities.filter((p) => p !== key));
      }
    } else {
      onPrioritiesChange([...selectedPriorities, key]);
    }
  };

  const handleDistanceChange = (key: PriorityKey, distM: number) => {
    const existing = distancePreferences.filter((p) => p.priority !== key);
    onDistancePreferencesChange([
      ...existing,
      { priority: key, preferred_distance_m: distM, label: `${(distM / 1000).toFixed(1)} km` }
    ]);
  };

  const getDistanceValue = (key: PriorityKey) => {
    const pref = distancePreferences.find((p) => p.priority === key);
    if (pref) return pref.preferred_distance_m;
    const defaultMeta = ALL_PRIORITIES.find((p) => p.key === key);
    return defaultMeta?.defaultDistM || 1500;
  };

  const handleCommuteSelected = async (destinationLocation: any) => {
    if (!localityCoords) return;
    setIsCalculatingCommute(true);
    try {
      const res = await api.getCommute(
        localityCoords,
        { lat: destinationLocation.lat, lng: destinationLocation.lng },
        destinationLocation.name
      );
      if (res.data && onCommuteUpdated) {
        onCommuteUpdated(res.data);
        if (!selectedPriorities.includes('commute')) {
          onPrioritiesChange([...selectedPriorities, 'commute']);
        }
      }
    } catch (err) {
      console.error('Commute calculation error:', err);
    } finally {
      setIsCalculatingCommute(false);
    }
  };

  return (
    <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-5">
      {/* Profiles Carousel / Chips */}
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            1. Your Persona / Profile
          </span>
          <span className="text-[11px] text-slate-400">Pre-selects priorities</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {PROFILES.map((prof) => {
            const Icon = prof.icon;
            const isSelected = currentProfile === prof.id;
            return (
              <button
                key={prof.id}
                onClick={() => onProfileChange(prof.id)}
                className={`p-2.5 rounded-2xl text-left border transition-all flex flex-col justify-between ${
                  isSelected
                    ? 'bg-teal-50/80 border-teal-500 text-teal-950 shadow-xs ring-1 ring-teal-500/30'
                    : 'bg-slate-50/70 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300'
                }`}
                title={prof.desc}
              >
                <div className="flex items-center justify-between w-full mb-1.5">
                  <Icon className={`w-4 h-4 ${isSelected ? 'text-teal-600' : 'text-slate-500'}`} />
                  {isSelected && <Check className="w-3.5 h-3.5 text-teal-600" />}
                </div>
                <span className="text-xs font-semibold leading-tight line-clamp-1">
                  {prof.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Priorities Selection */}
      <div className="pt-2 border-t border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            2. What Matters To You (Priorities)
          </span>
          <button
            onClick={() => setShowPreferences(!showPreferences)}
            className="text-xs text-teal-700 hover:text-teal-800 font-semibold flex items-center gap-1"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>{showPreferences ? 'Hide distance preferences' : 'Set distance preferences'}</span>
            {showPreferences ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {ALL_PRIORITIES.map((prio) => {
            const isSelected = selectedPriorities.includes(prio.key);
            return (
              <button
                key={prio.key}
                onClick={() => togglePriority(prio.key)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all border flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-navy-900 border-navy-900 text-white shadow-xs'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {isSelected && <Check className="w-3 h-3 text-teal-400" />}
                <span>{prio.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* User-Set Distance Preferences Panel (Section 8) */}
      {showPreferences && (
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3 animate-in fade-in-50 duration-150">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-xs text-slate-800 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-teal-600" />
              <span>Custom Comfortable Straight-Line Distances</span>
            </h4>
            <span className="text-[11px] text-slate-500 italic">
              Editable preferences, not universal standards
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {selectedPriorities.filter(p => p !== 'commute').map((prio) => {
              const curDist = getDistanceValue(prio);
              return (
                <div key={prio} className="bg-white p-2.5 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex justify-between text-xs font-medium text-slate-700">
                    <span className="capitalize">{prio.replace('_', ' ')}</span>
                    <span className="text-teal-700 font-bold">≤ {(curDist / 1000).toFixed(1)} km</span>
                  </div>
                  <input
                    type="range"
                    min={400}
                    max={5000}
                    step={100}
                    value={curDist}
                    onChange={(e) => handleDistanceChange(prio, parseInt(e.target.value, 10))}
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
                  />
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span>400m</span>
                    <span>5 km</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Commute Destination Section (Section 9) */}
      <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-teal-600" />
            <span>Commute Destination Check</span>
          </span>
          <p className="text-[11px] text-slate-500">
            {commuteData
              ? `Destination set: ${commuteData.destination_name}`
              : 'Add your workplace or college to evaluate door-to-door transit & driving times.'}
          </p>
        </div>

        <button
          onClick={() => setShowCommuteInput(!showCommuteInput)}
          className="self-start sm:self-auto px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
        >
          {commuteData ? 'Change Destination' : '+ Add Destination'}
        </button>
      </div>

      {showCommuteInput && (
        <div className="p-3.5 bg-teal-50/50 rounded-2xl border border-teal-200/60 space-y-2">
          <span className="text-xs font-medium text-slate-700 block">
            Search Destination (Workplace / College)
          </span>
          <SearchBar
            placeholder="e.g. Manyata Tech Park, Bengaluru or Electronic City"
            onLocationSelected={handleCommuteSelected}
          />
          {isCalculatingCommute && (
            <p className="text-xs text-teal-700 animate-pulse">
              Calculating multi-modal travel times…
            </p>
          )}
        </div>
      )}

      {/* Render Commute Summary if set */}
      {commuteData && (
        <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-xs text-slate-700">
              <Car className="w-4 h-4 text-teal-600" />
              <span className="font-semibold">
                Drive: {commuteData.modes?.driving?.duration_min ? `~${commuteData.modes.driving.duration_min} min` : 'Unavailable'}
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-slate-700">
              <Bus className="w-4 h-4 text-blue-600" />
              <span className="font-semibold">
                Transit: {commuteData.modes?.transit?.duration_min ? `~${commuteData.modes.transit.duration_min} min` : 'Unavailable'}
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-slate-700">
              <Footprints className="w-4 h-4 text-purple-600" />
              <span className="font-semibold">
                Walk: {commuteData.modes?.walking?.duration_min ? `~${commuteData.modes.walking.duration_min} min` : 'Unavailable'}
              </span>
            </div>
          </div>
          <span className="text-[10px] text-slate-400 italic">
            Travel times vary by traffic and peak hours
          </span>
        </div>
      )}
    </div>
  );
};
