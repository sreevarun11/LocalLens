import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { SearchBar } from '../components/search/SearchBar';
import { LocationDetails } from '../types';
import {
  Compass,
  Scale,
  ShieldCheck,
  Info
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const handleLocationSelected = (location: LocationDetails) => {
    // Navigate directly to explore with state
    navigate('/explore', { state: { location } });
  };

  return (
    <div className="space-y-16 py-10">
      {/* Hero Section */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
          <span>No fabricated scores · Zero invented data · Complete provenance</span>
        </div>

        <h1 className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl text-navy-900 tracking-tight leading-tight sm:leading-tight">
          Know your neighbourhood <br className="hidden sm:inline" />
          <span className="text-teal-600">before you move.</span>
        </h1>

        <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Explore real neighbourhood information, understand what matters to you, compare locations, and generate an evidence-backed locality report.
        </p>

        {/* Hero Search Box above the fold */}
        <div className="max-w-2xl mx-auto pt-2">
          <div className="bg-white p-2.5 sm:p-3 rounded-3xl shadow-xl shadow-slate-200/60 border border-slate-200">
            <SearchBar onLocationSelected={handleLocationSelected} autoFocus />
          </div>
        </div>

        {/* Direct CTAs */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Link
            to="/explore"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 shadow-md shadow-teal-600/20 transition-all hover:-translate-y-0.5"
          >
            <Compass className="w-4 h-4" />
            <span>Explore Area</span>
          </Link>
          <Link
            to="/compare"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 shadow-xs transition-all hover:-translate-y-0.5"
          >
            <Scale className="w-4 h-4 text-teal-600" />
            <span>Compare Locations</span>
          </Link>
        </div>
      </section>

      {/* The 4 Architectural Layers */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center max-w-3xl mx-auto mb-12 space-y-2">
          <span className="text-xs font-bold text-teal-700 tracking-wider uppercase">
            Product Architecture
          </span>
          <h2 className="font-display font-bold text-2xl sm:text-3xl text-navy-900">
            Four Layers of Honest Intelligence
          </h2>
          <p className="text-sm text-slate-600">
            Every screen and insight belongs to one clear, verifiable layer.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Layer 1 */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs hover:border-teal-200 transition-colors space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm">
              1
            </div>
            <h3 className="font-display font-bold text-base text-navy-900">
              Real Location Data
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Real search, real interactive map, real nearby places, and environmental station data where integrated sources exist.
            </p>
          </div>

          {/* Layer 2 */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs hover:border-teal-200 transition-colors space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm">
              2
            </div>
            <h3 className="font-display font-bold text-base text-navy-900">
              Coverage & Provenance
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              For every single dataset: exact source, spatial granularity, freshness timestamps, depth, and documented limitations.
            </p>
          </div>

          {/* Layer 3 */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs hover:border-teal-200 transition-colors space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm">
              3
            </div>
            <h3 className="font-display font-bold text-base text-navy-900">
              User Priorities
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Tailored profiles + editable priority weights + user-set distance preferences + optional commute destination check.
            </p>
          </div>

          {/* Layer 4 */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs hover:border-teal-200 transition-colors space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm">
              4
            </div>
            <h3 className="font-display font-bold text-base text-navy-900">
              Grounded Synthesis
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Deterministic findings, claim-validated AI narrative, side-by-side comparability checks, and reproducible PDF reports.
            </p>
          </div>
        </div>
      </section>

      {/* Positioning & Absence Semantics Notice */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-slate-100 rounded-3xl p-6 sm:p-8 border border-slate-200 flex flex-col sm:flex-row items-start gap-4">
          <div className="p-3 bg-white rounded-2xl border border-slate-200 text-teal-700 shrink-0">
            <Info className="w-6 h-6" />
          </div>
          <div className="space-y-2">
            <h4 className="font-display font-bold text-sm text-navy-900">
              Our Non-Negotiable Commitment: Zero Fabrication
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Google Maps shows what is around a place. LocalLens shows what the available evidence means for <em>your</em> priorities, how deep and trustworthy that evidence is, and what you must verify on site. We never output an arbitrary composite "locality score", and we never equate missing map listings with non-existence.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
