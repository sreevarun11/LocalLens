import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  FileText,
  ShieldCheck,
  Zap,
  Download,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  Scale,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { SearchBar } from '../components/search/SearchBar';
import { ReportFeedbackModal } from '../components/reports/ReportFeedbackModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { LocationDetails, ProfileKey, PriorityKey } from '../types';

export const ReportBuilderPage: React.FC = () => {
  const location = useLocation();
  const { credits, isAuthenticated, isEmailVerified, verifyEmailSimulate, refreshCredits } = useAuth();

  // 1. Locality State
  const [selectedLocality, setSelectedLocality] = useState<LocationDetails | null>(null);

  // 2. Profile & Priorities State
  const [profile, setProfile] = useState<ProfileKey>('family');
  const [priorities, setPriorities] = useState<PriorityKey[]>([
    'education',
    'healthcare',
    'transport',
    'daily_life'
  ]);

  // 3. Property Details (Optional Context)
  const [address, setAddress] = useState('');
  const [floorLevel, setFloorLevel] = useState('');
  const [facing, setFacing] = useState('');
  const [waterSource, setWaterSource] = useState('Cauvery + Borewell');
  const [powerBackup, setPowerBackup] = useState('Full Backup');
  const [rentPrice, setRentPrice] = useState('');
  const [notes, setNotes] = useState('');
  const [showPropertyDetails, setShowPropertyDetails] = useState(false);

  // 4. Comparison locality (Optional)
  const [compareLocality, setCompareLocality] = useState<LocationDetails | null>(null);
  const [includeComparison, setIncludeComparison] = useState(false);

  // 5. Sections to Include
  const [sections, setSections] = useState<string[]>([
    'summary',
    'amenities',
    'environment',
    'checklist',
    'sources'
  ]);

  // Generation status
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Default selection from query params or geocoding
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const nameParam = params.get('name') || params.get('q');
    const latParam = params.get('lat');
    const lngParam = params.get('lng');
    const profileParam = params.get('profile');

    if (profileParam) {
      setProfile(profileParam as ProfileKey);
    }

    if (nameParam && latParam && lngParam) {
      const lat = parseFloat(latParam);
      const lng = parseFloat(lngParam);
      setSelectedLocality({
        place_id: `canonical_${lat.toFixed(4)}_${lng.toFixed(4)}`,
        name: nameParam,
        formatted_address: nameParam,
        latitude: lat,
        longitude: lng,
        lat,
        lng,
        provider: 'Geocoded Selection'
      });
    } else if (nameParam) {
      api.getAutocomplete(nameParam).then((preds) => {
        if (preds && preds.length > 0) {
          api.getLocationDetails(preds[0].place_id).then((loc) => {
            setSelectedLocality(loc);
          });
        }
      }).catch(console.error);
    }
  }, [location.search]);

  const handleDownloadPdf = async (reportId: string, filename?: string) => {
    setIsDownloading(true);
    setDownloadError(null);
    try {
      await api.downloadReportPdf(reportId, filename);
    } catch (e: any) {
      console.error('PDF download error:', e);
      setDownloadError(e.message || 'Failed to download PDF. Opening in new tab instead...');
      window.open(api.getPdfUrl(reportId, true), '_blank');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedLocality) {
      setError('Please select a target locality before generating report');
      return;
    }

    setError(null);
    setIsGenerating(true);

    try {
      const payload = {
        locality_name: selectedLocality.name,
        lat: selectedLocality.lat,
        lng: selectedLocality.lng,
        comparison_locality_name: includeComparison && compareLocality ? compareLocality.name : null,
        comparison_lat: includeComparison && compareLocality ? compareLocality.lat : null,
        comparison_lng: includeComparison && compareLocality ? compareLocality.lng : null,
        user_profile: profile,
        user_priorities: priorities,
        sections_included: sections,
        property_context: {
          property_address: address.trim() || null,
          floor_level: floorLevel.trim() || null,
          unit_facing: facing.trim() || null,
          water_source_declared: waterSource,
          power_backup_declared: powerBackup,
          rent_or_price: rentPrice.trim() || null,
          user_notes: notes.trim() || null
        }
      };

      const result = await api.generateReport(payload);
      setGeneratedReport(result);
      await refreshCredits();
      setShowFeedbackModal(true);
    } catch (err: any) {
      console.error('Report generation error:', err);
      setError(err.message || 'Failed to generate report. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Feedback Modal */}
      <ReportFeedbackModal
        isOpen={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        reportId={generatedReport?.id}
        localityName={selectedLocality?.name}
      />

      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-50 text-teal-800 rounded-full text-xs font-semibold mb-2">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span>Independent Locality Decision Report</span>
          </div>
          <h1 className="font-display text-2xl font-bold text-navy-900 tracking-tight">
            Decision Report Builder
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Generate an archival, publication-grade PDF report capturing live open-source evidence from OpenStreetMap and atmospheric models at this exact moment.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 p-3 rounded-2xl">
          <Zap className="w-5 h-5 text-teal-600 fill-teal-600" />
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Your Balance</p>
            <p className="text-xs font-bold text-slate-900">
              {credits?.credits_remaining ?? 0} Credits
            </p>
          </div>
        </div>
      </div>

      {/* Success View if Report is Generated */}
      {generatedReport && (
        <div className="p-6 bg-gradient-to-br from-emerald-50 via-teal-50/40 to-white rounded-3xl border border-teal-300 shadow-sm space-y-5 animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-600 text-white rounded-2xl shadow-xs">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded-full">
                  Report Generated Successfully
                </span>
                <h3 className="font-display font-bold text-lg text-navy-900 mt-1">
                  {generatedReport.title}
                </h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  ID: {generatedReport.id}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => handleDownloadPdf(generatedReport.id, `LocalLens_Report_${generatedReport.id.slice(0, 8)}.pdf`)}
                disabled={isDownloading}
                className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                <span>{isDownloading ? 'Downloading...' : 'Download PDF'}</span>
              </button>

              <a
                href={api.getPdfUrl(generatedReport.id, true)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
              >
                <ExternalLink className="w-4 h-4 text-slate-400" />
                <span>Open in Tab</span>
              </a>

              <Link
                to={`/verify/${generatedReport.id}`}
                target="_blank"
                className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-teal-800 rounded-xl text-xs font-semibold transition-colors"
              >
                <ShieldCheck className="w-4 h-4 text-teal-600" />
                <span>Public Verification</span>
              </Link>
            </div>
          </div>

          {downloadError && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>{downloadError}</span>
            </div>
          )}

          <div className="p-4 bg-white/80 rounded-2xl border border-teal-200/60 text-xs text-slate-600 flex items-center justify-between">
            <span className="font-mono text-[11px] text-slate-500">
              Integrity Hash: {generatedReport.verification_hash.slice(0, 24)}...
            </span>
            <button
              onClick={() => setShowFeedbackModal(true)}
              className="text-xs font-semibold text-teal-800 hover:underline cursor-pointer"
            >
              Give Report Feedback
            </button>
          </div>
        </div>
      )}

      {/* Main Form */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200 shadow-xs space-y-6">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 1. Locality Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-navy-900 uppercase tracking-wider">
            1. Target Locality
          </label>
          <SearchBar
            onLocationSelected={(loc) => setSelectedLocality(loc)}
            initialValue={selectedLocality?.name}
          />
          {selectedLocality && (
            <p className="text-[11px] text-slate-500">
              Selected: <span className="font-semibold text-slate-800">{selectedLocality.name}</span> ({selectedLocality.lat.toFixed(4)}, {selectedLocality.lng.toFixed(4)})
            </p>
          )}
        </div>

        {/* 2. Profile & Priorities */}
        <div className="space-y-4 pt-4 border-t border-slate-100">
          <label className="block text-xs font-bold text-navy-900 uppercase tracking-wider">
            2. Decision Profile & Priorities
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { id: 'family', label: 'Family with Kids' },
              { id: 'commuter', label: 'Daily Commuter' },
              { id: 'student', label: 'Student' },
              { id: 'elderly', label: 'Retiree / Elderly' },
              { id: 'first_time_renter', label: 'First-time Renter' },
              { id: 'home_buyer', label: 'Home Buyer' },
              { id: 'relocation', label: 'City Relocation' }
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setProfile(p.id as ProfileKey)}
                className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-left ${
                  profile === p.id
                    ? 'bg-navy-900 text-white border-navy-900 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div>
            <span className="text-[11px] font-semibold text-slate-500 block mb-1.5">
              Included Priority Focus Areas:
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'education', label: 'Education & Schools' },
                { id: 'healthcare', label: 'Hospitals & Clinics' },
                { id: 'transport', label: 'Transit & Metro' },
                { id: 'daily_life', label: 'Groceries & Daily' },
                { id: 'parks', label: 'Parks & Open Green' },
                { id: 'lifestyle', label: 'Cafes & Dining' },
                { id: 'environment', label: 'Air & Environment' },
                { id: 'safety_infrastructure', label: 'Safety Infrastructure' }
              ].map((cat) => {
                const isChecked = priorities.includes(cat.id as PriorityKey);
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      if (isChecked) {
                        setPriorities(priorities.filter((p) => p !== cat.id));
                      } else {
                        setPriorities([...priorities, cat.id as PriorityKey]);
                      }
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors ${
                      isChecked
                        ? 'bg-teal-50 text-teal-800 border-teal-600 font-semibold'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {isChecked ? '✓ ' : '+ '}
                    {cat.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 3. Optional Property Details (Collapsed by default) */}
        <div className="space-y-4 pt-4 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-xs font-bold text-navy-900 uppercase tracking-wider">
                3. Property Specifics (Optional Context)
              </label>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Add optional property-specific details to include in your personalized report.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowPropertyDetails(!showPropertyDetails)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-colors flex items-center gap-1.5 ${
                showPropertyDetails
                  ? 'bg-teal-50 text-teal-800 border-teal-300'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <span>{showPropertyDetails ? 'Hide property details' : 'Add property details (optional)'}</span>
              {showPropertyDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {showPropertyDetails && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-[11px] text-slate-600 flex items-start gap-2">
                <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <span>
                  <b>Legal Notice:</b> Any property details entered below are printed in the report with the explicit disclosure: <span className="italic">"Information provided by report creator — not independently verified by LocalLens."</span>
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Address / Project Name
                  </label>
                  <input
                    type="text"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="e.g. Prestige Greenwoods, Flat 402"
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Floor Level
                  </label>
                  <input
                    type="text"
                    value={floorLevel}
                    onChange={(e) => setFloorLevel(e.target.value)}
                    placeholder="e.g. 4th Floor of 14"
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Unit Facing
                  </label>
                  <input
                    type="text"
                    value={facing}
                    onChange={(e) => setFacing(e.target.value)}
                    placeholder="e.g. East facing balcony"
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Water Source (Declared)
                  </label>
                  <select
                    value={waterSource}
                    onChange={(e) => setWaterSource(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 bg-white"
                  >
                    <option value="Cauvery / Municipal piped">Cauvery / Municipal piped</option>
                    <option value="Cauvery + Borewell">Cauvery + Borewell</option>
                    <option value="Borewell only">Borewell only</option>
                    <option value="Tanker dependent">Tanker dependent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Power Backup (Declared)
                  </label>
                  <select
                    value={powerBackup}
                    onChange={(e) => setPowerBackup(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 bg-white"
                  >
                    <option value="Full Backup (incl AC)">Full Backup (incl AC)</option>
                    <option value="Partial (Lights & Fans only)">Partial (Lights & Fans only)</option>
                    <option value="None">None</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Quoted Rent / Price
                  </label>
                  <input
                    type="text"
                    value={rentPrice}
                    onChange={(e) => setRentPrice(e.target.value)}
                    placeholder="e.g. 45,000 / month"
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Personal Property Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Notes on maintenance charges, landlord terms, physical inspection notes..."
                  rows={2}
                  className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>
          )}
        </div>

        {/* 4. Optional Comparison Locality */}
        <div className="space-y-3 pt-4 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-navy-900 uppercase tracking-wider flex items-center gap-2">
              <Scale className="w-4 h-4 text-teal-600" />
              <span>4. Dual Comparison Locality (Optional)</span>
            </label>
            <button
              type="button"
              onClick={() => setIncludeComparison(!includeComparison)}
              className={`text-xs font-semibold px-3 py-1 rounded-lg border transition-colors ${
                includeComparison
                  ? 'bg-teal-50 text-teal-800 border-teal-300'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {includeComparison ? '✓ Included' : '+ Add Comparison'}
            </button>
          </div>

          {includeComparison && (
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 animate-in fade-in duration-150">
              <span className="text-[11px] text-slate-500 font-semibold block">Select comparison neighborhood:</span>
              <SearchBar
                onLocationSelected={(loc) => setCompareLocality(loc)}
                initialValue={compareLocality?.name}
                placeholder="Search second locality to compare..."
              />
              {compareLocality && (
                <p className="text-[11px] text-slate-600 font-medium">
                  Comparing with: <b>{compareLocality.name}</b>
                </p>
              )}
            </div>
          )}
        </div>

        {/* 5. Sections to Include */}
        <div className="space-y-3 pt-4 border-t border-slate-100">
          <label className="block text-xs font-bold text-navy-900 uppercase tracking-wider">
            5. Sections Included in Archival PDF
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            {[
              { id: 'summary', label: 'Executive Summary & Findings' },
              { id: 'amenities', label: 'Priority Amenities Breakdown' },
              { id: 'environment', label: 'Air Quality & Environment' },
              { id: 'checklist', label: 'Physical Site Checklist' },
              { id: 'sources', label: 'Licence & Data Provenance' }
            ].map((sec) => {
              const checked = sections.includes(sec.id);
              return (
                <label key={sec.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded-xl cursor-pointer hover:bg-slate-100 transition-colors">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      if (checked) {
                        setSections(sections.filter((s) => s !== sec.id));
                      } else {
                        setSections([...sections, sec.id]);
                      }
                    }}
                    className="h-4 w-4 rounded text-teal-600 border-slate-300 focus:ring-teal-500"
                  />
                  <span className="text-slate-700 font-medium text-[11px]">{sec.label}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* 6. Generation Authorization & CTA */}
        <div className="pt-6 border-t border-slate-100 space-y-4">
          {!isAuthenticated ? (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-navy-900">Sign in to generate report</p>
                <p className="text-[11px] text-slate-500">Every new account receives 3 free verified decision report credits.</p>
              </div>
              <Link
                to="/register"
                className="px-4 py-2 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors whitespace-nowrap"
              >
                Create Account (3 Free Credits)
              </Link>
            </div>
          ) : !isEmailVerified ? (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-amber-900">Email Verification Required</p>
                  <p className="text-[11px] text-amber-800">
                    To maintain report register authenticity, please verify your email before generating.
                  </p>
                </div>
              </div>
              <button
                onClick={() => verifyEmailSimulate()}
                className="px-4 py-2 bg-amber-800 text-white rounded-xl text-xs font-semibold hover:bg-amber-900 transition-colors whitespace-nowrap"
              >
                Simulate Verification
              </button>
            </div>
          ) : (credits?.credits_remaining ?? 0) <= 0 ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-rose-900">Zero Credits Remaining</p>
                <p className="text-[11px] text-rose-700">
                  You have used all 3 free report credits. Purchase additional reports for ₹29 each.
                </p>
              </div>
              <button
                disabled
                className="px-4 py-2 bg-rose-200 text-rose-700 rounded-xl text-xs font-semibold cursor-not-allowed"
              >
                Purchase Credits (₹29)
              </button>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-xs text-slate-500">
                <span>Cost: <b className="text-navy-900">1 Credit</b></span>
                <span className="mx-2">·</span>
                <span>Remaining after generation: <b className="text-teal-700">{(credits?.credits_remaining ?? 0) - 1}</b></span>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating || !selectedLocality}
                className="w-full sm:w-auto px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <FileText className="w-4 h-4" />
                <span>{isGenerating ? 'Generating Decision Document...' : 'Generate Decision Report (1 Credit)'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
