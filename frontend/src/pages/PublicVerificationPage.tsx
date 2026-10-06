import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, AlertTriangle, Compass, ArrowRight, Hash, Clock, MapPin } from 'lucide-react';
import { api } from '../services/api';

export const PublicVerificationPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const [verification, setVerification] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;

    api.getPublicVerification(reportId)
      .then((data) => setVerification(data))
      .catch((err) => {
        console.error(err);
        setError('No verified report found matching this identifier or the verification record has expired.');
      })
      .finally(() => setIsLoading(false));
  }, [reportId]);

  return (
    <div className="min-h-[80vh] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto w-full space-y-6">
        {/* Top Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 bg-teal-50 text-teal-700 rounded-3xl mb-1">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-navy-900 tracking-tight">
            Decision Report Verification
          </h1>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Public authentication register verifying the integrity and provenance of LocalLens decision documents.
          </p>
        </div>

        {/* Verification Card */}
        {isLoading ? (
          <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm animate-pulse space-y-4">
            <div className="h-6 bg-slate-200 rounded w-1/3 mx-auto" />
            <div className="h-24 bg-slate-100 rounded-2xl" />
          </div>
        ) : error ? (
          <div className="bg-white p-8 rounded-3xl border border-rose-200 shadow-sm text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="font-display font-bold text-base text-rose-900">
              Invalid or Unregistered Report
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {error}
            </p>
            <div className="pt-2">
              <Link
                to="/explore"
                className="inline-flex items-center gap-2 px-4 py-2 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors"
              >
                <span>Search Neighborhoods</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-teal-200/80 shadow-sm overflow-hidden divide-y divide-slate-100">
            {/* Authenticity Banner */}
            <div className="p-6 bg-gradient-to-r from-teal-500/10 via-teal-500/5 to-transparent flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 text-emerald-700 rounded-2xl">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    Official Verification · Authentic
                  </span>
                  <h3 className="font-display font-bold text-base text-navy-900 mt-1">
                    {verification.title}
                  </h3>
                </div>
              </div>
              <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
                ID: {verification.report_id.slice(0, 8)}...
              </span>
            </div>

            {/* Details Table */}
            <div className="p-6 space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-500 font-semibold text-[11px]">
                    <MapPin className="w-3.5 h-3.5 text-teal-600" />
                    <span>Target Locality</span>
                  </div>
                  <p className="font-bold text-slate-900 text-sm">{verification.locality_name}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-500 font-semibold text-[11px]">
                    <Clock className="w-3.5 h-3.5 text-teal-600" />
                    <span>Generation Date</span>
                  </div>
                  <p className="font-bold text-slate-900 text-sm">
                    {new Date(verification.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {verification.comparison_locality_name && (
                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
                  <span className="text-slate-500 font-semibold text-[11px]">Comparison Locality</span>
                  <p className="font-bold text-slate-900">{verification.comparison_locality_name}</p>
                </div>
              )}

              {/* SHA-256 Fingerprint */}
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 space-y-1.5">
                <div className="flex items-center gap-1.5 text-slate-500 font-semibold text-[11px]">
                  <Hash className="w-3.5 h-3.5 text-teal-600" />
                  <span>Document Integrity Hash (SHA-256)</span>
                </div>
                <p className="font-mono text-[11px] text-teal-900 break-all bg-white p-2 rounded-xl border border-slate-200">
                  {verification.verification_hash}
                </p>
                <p className="text-[10px] text-slate-400">
                  Matches the cryptographic digest stamped on the official PDF document header.
                </p>
              </div>

              {/* Certified By */}
              <div className="p-3.5 bg-teal-50/50 rounded-2xl border border-teal-200/60 text-[11px] text-teal-950 space-y-1">
                <span className="font-bold text-teal-900">LocalLens Zero-Fabrication Registry:</span>
                <p>
                  This verification record confirms that the associated decision document was produced by LocalLens without fabricated livability scores, synthetic reviews, or unauthorized third-party data caching.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="p-4 bg-slate-50 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
              <span className="text-[11px] text-slate-400">
                Public register · Zero personal identifiable information
              </span>
              <Link
                to={`/explore?q=${encodeURIComponent(verification.locality_name)}`}
                className="flex items-center gap-1.5 px-4 py-2 bg-navy-900 text-white rounded-xl font-semibold hover:bg-navy-800 transition-colors shadow-xs"
              >
                <Compass className="w-4 h-4" />
                <span>Explore {verification.locality_name} Live</span>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
