import React from 'react';
import { Link } from 'react-router-dom';
import { Eye, CheckCircle2 } from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <Eye className="w-3.5 h-3.5 text-teal-600" />
          <span>About LocalLens</span>
        </div>
        <h1 className="font-display font-bold text-3xl sm:text-4xl text-navy-900">
          Know Your Neighbourhood Before You Move
        </h1>
        <p className="text-sm text-slate-600 max-w-2xl mx-auto leading-relaxed">
          LocalLens is an independent neighborhood decision engine engineered to give home seekers, renters, and families factual, evidence-grounded locality intelligence.
        </p>
      </div>

      {/* Core Mission */}
      <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-xs space-y-6">
        <h2 className="font-display font-bold text-xl text-navy-900">
          The Problem We Solve
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-600 leading-relaxed">
          <div className="p-5 bg-slate-50 rounded-2xl border border-slate-200 space-y-2">
            <h3 className="font-bold text-sm text-slate-800">What Traditional Maps Show</h3>
            <p>
              "What places exist around this coordinate?" Traditional maps are search engines for POIs and driving turn-by-turn directions. They do not evaluate evidence depth, municipal data limitations, or household priorities.
            </p>
          </div>
          <div className="p-5 bg-teal-50/60 rounded-2xl border border-teal-200 space-y-2">
            <h3 className="font-bold text-sm text-teal-950">What LocalLens Delivers</h3>
            <p>
              "What does the available neighborhood evidence mean for you?" We synthesize verified open-source amenities, atmospheric model data, and transparent data absence disclosures to enable high-confidence relocation decisions.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100">
          <h3 className="font-bold text-sm text-navy-900 mb-3">Our Core Engineering Principles</h3>
          <ul className="space-y-2.5 text-xs text-slate-700">
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
              <span><strong>Zero Data Fabrication:</strong> We never generate fake ratings, speculative scores, or pseudo-safety rankings. When data is unavailable, we explicitly state it.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
              <span><strong>Exact Geospatial Provenance:</strong> Every coordinate, straight-line distance, and facility count is derived from verified open platforms (OpenStreetMap, Open-Meteo).</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
              <span><strong>Permanent Verifiable Records:</strong> Generated decision reports include cryptographic hashes and public QR codes for independent verification.</span>
            </li>
          </ul>
        </div>
      </div>

      {/* CTA */}
      <div className="p-6 bg-navy-900 text-white rounded-3xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="font-display font-bold text-lg">Ready to inspect a neighborhood?</h3>
          <p className="text-xs text-slate-300 mt-0.5">Explore any locality, pin code, or metro stop across India.</p>
        </div>
        <Link
          to="/explore"
          className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-navy-950 font-bold text-xs rounded-xl transition-colors shadow-xs whitespace-nowrap"
        >
          Explore Neighborhoods
        </Link>
      </div>
    </div>
  );
};
