import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { User, ShieldCheck, Mail, Sliders, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ProfilePage: React.FC = () => {
  const { user, token, verifyEmailSimulate } = useAuth();
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Preference state
  const [defaultProfile, setDefaultProfile] = useState('family');
  const [priorities, setPriorities] = useState<string[]>(['education', 'healthcare', 'transport', 'daily_life']);

  const availableProfiles = [
    { id: 'family', label: 'Family with Children', desc: 'Focuses on schools, parks, healthcare, daily essentials' },
    { id: 'student', label: 'Student / Young Professional', desc: 'Focuses on transit, cafes, walkability, essentials' },
    { id: 'commuter', label: 'Daily Commuter', desc: 'Focuses on metro/bus transit, highway connectivity' },
    { id: 'home_buyer', label: 'Home Buyer / Long-term Resident', desc: 'Focuses on water reliability, environment, safety' },
    { id: 'elderly', label: 'Elderly Household', desc: 'Focuses on hospitals, quiet parks, flat terrain, clinics' },
    { id: 'general', label: 'General Relocation', desc: 'Balanced assessment across all available categories' }
  ];

  const availablePriorities = [
    { id: 'education', label: 'Education & Schools' },
    { id: 'healthcare', label: 'Healthcare & Hospitals' },
    { id: 'transport', label: 'Public Transit & Commute' },
    { id: 'daily_life', label: 'Groceries & Daily Essentials' },
    { id: 'parks', label: 'Parks & Green Spaces' },
    { id: 'environment', label: 'Air Quality & Greenery' },
    { id: 'water', label: 'Water Sources & Flooding' },
    { id: 'safety', label: 'Safety Infrastructure & Lighting' }
  ];

  useEffect(() => {
    if (token) {
      loadPreferences();
    }
  }, [token]);

  const loadPreferences = async () => {
    try {
      const data = await api.getPreferences();
      if (data) {
        if (data.default_profile) setDefaultProfile(data.default_profile);
        if (Array.isArray(data.default_priorities)) setPriorities(data.default_priorities);
      }
    } catch (err: any) {
      console.warn('Could not load preferences:', err);
    }
  };

  const togglePriority = (id: string) => {
    setPriorities(prev => 
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await api.updatePreferences(defaultProfile, priorities, []);
      setSuccessMsg('Default evaluation preferences updated successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleSimulateVerification = async () => {
    try {
      await verifyEmailSimulate();
      setSuccessMsg('Email marked as verified in the local database.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Verification failed');
    }
  };

  if (!token) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm">
          <User className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-800 mb-2">Sign in to view your profile</h2>
          <p className="text-slate-600 mb-6">Manage your default locality priorities, saved search preferences, and report history.</p>
          <div className="flex justify-center gap-3">
            <Link to="/login" className="px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg font-medium">
              Sign In
            </Link>
            <Link to="/register" className="px-5 py-2.5 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg font-medium">
              Create Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Account Profile & Preferences</h1>
          <p className="text-slate-600 text-sm mt-1">Configure your default household profile and baseline priorities for locality intelligence.</p>
        </div>
        <Link to="/dashboard" className="text-sm font-medium text-teal-700 hover:underline">
          &larr; Back to Dashboard
        </Link>
      </div>

      {successMsg && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3 text-emerald-800 text-sm">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* User Info Card */}
        <div className="md:col-span-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
              <User className="h-4 w-4" /> User Information
            </h3>
            
            <div className="space-y-3">
              <div>
                <span className="text-xs text-slate-400 block">Display Name</span>
                <span className="font-semibold text-slate-800 text-sm">{user?.display_name || 'User'}</span>
              </div>

              <div>
                <span className="text-xs text-slate-400 block">Email Address</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <Mail className="h-3.5 w-3.5 text-slate-400" />
                  <span className="text-sm text-slate-700 font-mono break-all">{user?.email}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100">
                <span className="text-xs text-slate-400 block mb-1">Verification Status</span>
                {user?.is_email_verified ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-xs font-medium">
                    <ShieldCheck className="h-3.5 w-3.5" /> Email Verified
                  </span>
                ) : (
                  <div className="space-y-2">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded text-xs font-medium">
                      Unverified
                    </span>
                    <button
                      onClick={handleSimulateVerification}
                      className="block text-xs text-teal-700 hover:text-teal-800 hover:underline font-medium"
                    >
                      Verify Now (Simulated)
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-500 space-y-2">
            <p className="font-semibold text-slate-700">Privacy & Data Storage</p>
            <p>Your search history and saved locations are stored locally in your private database account.</p>
            <p>LocalLens never sells or syndicates your searches to third-party data brokers.</p>
          </div>
        </div>

        {/* Preferences Form */}
        <div className="md:col-span-2">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Sliders className="h-4 w-4 text-teal-700" /> Default Exploration Preferences
            </h3>
            <p className="text-xs text-slate-600 mb-6">
              These defaults are automatically pre-selected whenever you open the Explore or Compare views.
            </p>

            <form onSubmit={handleSavePreferences} className="space-y-6">
              {/* Default Profile */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2">
                  Household Persona
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {availableProfiles.map(p => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setDefaultProfile(p.id)}
                      className={`text-left p-3 rounded-lg border text-xs transition-all ${
                        defaultProfile === p.id
                          ? 'border-teal-600 bg-teal-50 text-teal-900 font-medium ring-1 ring-teal-600'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                      }`}
                    >
                      <div className="font-semibold">{p.label}</div>
                      <div className="text-[11px] text-slate-500 mt-1">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Default Priorities */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2">
                  Key Priorities
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {availablePriorities.map(p => {
                    const active = priorities.includes(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => togglePriority(p.id)}
                        className={`text-left p-2.5 rounded-lg border text-xs transition-all ${
                          active
                            ? 'border-teal-600 bg-teal-600 text-white font-medium'
                            : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                        }`}
                      >
                        {p.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors flex items-center gap-2"
                >
                  {saving && <RefreshCw className="h-4 w-4 animate-spin" />}
                  Save Preferences
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
