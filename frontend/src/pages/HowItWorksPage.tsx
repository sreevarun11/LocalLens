import React from 'react';
import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export const HowItWorksPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
      <div className="text-center space-y-3">
        <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">
          Product Guide
        </span>
        <h1 className="font-display font-bold text-3xl sm:text-4xl text-navy-900">
          How LocalLens Works
        </h1>
        <p className="text-sm text-slate-600 max-w-2xl mx-auto">
          LocalLens is not a property marketplace, listing broker, or review aggregator. It is an evidence-grounded neighborhood decision engine.
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm shrink-0">
            1
          </div>
          <div className="space-y-1">
            <h3 className="font-display font-bold text-base text-navy-900">
              Search Any Locality or PIN Code
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              We resolve real coordinates using geocoding engines. No hard-coded coordinates or demo fakes. We immediately query real nearby amenities and environmental models within a designated radius.
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm shrink-0">
            2
          </div>
          <div className="space-y-1">
            <h3 className="font-display font-bold text-base text-navy-900">
              Select Your Profile & Set Distance Preferences
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Whether you are a daily commuter, student, or family with school-going children, customize what matters to you. Set maximum comfortable straight-line distances (e.g., nearest hospital ≤ 2.5 km, nearest school ≤ 1 km).
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm shrink-0">
            3
          </div>
          <div className="space-y-1">
            <h3 className="font-display font-bold text-base text-navy-900">
              Inspect Evidence & Data Gaps Honestly
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              We explicitly label data depth. If a monitoring station is 8 km away, we label it as distant. If no integrated source exists for water quality or locality-level crime, we tell you clearly and supply practical "Verify on site" questions to ask during a visit.
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-sm shrink-0">
            4
          </div>
          <div className="space-y-1">
            <h3 className="font-display font-bold text-base text-navy-900">
              Generate an Immutable Decision Report
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Generate a permanent, QR-verified PDF Neighborhood Intelligence Report based entirely on storable datasets. Verify it publicly anytime.
            </p>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center pt-4">
        <Link
          to="/explore"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 shadow-md transition-all"
        >
          <Compass className="w-4 h-4" />
          <span>Start Exploring Now</span>
        </Link>
      </div>
    </div>
  );
};
