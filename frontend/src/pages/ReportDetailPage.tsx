import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Download,
  ExternalLink,
  ShieldCheck,
  ArrowLeft,
  Calendar,
  MapPin,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { api } from '../services/api';

export const ReportDetailPage: React.FC = () => {
  const { id, reportId } = useParams<{ id?: string; reportId?: string }>();
  const targetId = reportId || id;
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!targetId) return;
    setIsLoading(true);
    api.getReport(targetId)
      .then((data) => setReport(data))
      .catch((err) => setError(err.message || 'Report not found'))
      .finally(() => setIsLoading(false));
  }, [targetId]);

  const handleDownload = async () => {
    if (!report) return;
    setIsDownloading(true);
    try {
      await api.downloadReportPdf(report.id, `${report.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`);
    } catch {
      window.open(api.getPdfUrl(report.id, true), '_blank');
    } finally {
      setIsDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-teal-600 mx-auto" />
        <p className="text-xs text-slate-500">Loading decision report details…</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="font-display font-bold text-xl text-navy-900">Report Unavailable</h2>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          {error || 'Unable to locate this report on your account.'}
        </p>
        <button
          onClick={() => navigate('/reports')}
          className="px-4 py-2 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors"
        >
          View all reports
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Navigation */}
      <div>
        <Link
          to="/reports"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-navy-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to All Reports</span>
        </Link>
      </div>

      {/* Main Report Card */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-100">
                Verified Decision Report
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {report.id}
              </span>
            </div>
            <h1 className="font-display font-bold text-2xl text-navy-900 mt-2">
              {report.title}
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-teal-600" />
                <span>{report.locality_name}</span>
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>{new Date(report.created_at).toLocaleString()}</span>
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              <span>{isDownloading ? 'Downloading...' : 'Download PDF'}</span>
            </button>

            <a
              href={api.getPdfUrl(report.id, true)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Open in Tab</span>
            </a>

            <Link
              to={`/verify/${report.id}`}
              target="_blank"
              className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white border border-teal-200 hover:bg-teal-50 text-teal-800 rounded-xl text-xs font-semibold transition-colors"
            >
              <ShieldCheck className="w-4 h-4 text-teal-600" />
              <span>Verify Integrity</span>
            </Link>
          </div>
        </div>

        {/* Report Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Evaluation Context
            </span>
            <div className="space-y-1 text-slate-700">
              <p><strong>Household Profile:</strong> {report.user_profile ? report.user_profile.replace('_', ' ').toUpperCase() : 'FAMILY'}</p>
              <p><strong>Evaluated Radius:</strong> 1,500 meters (straight-line)</p>
              {report.comparison_locality_name && (
                <p><strong>Comparison Locality:</strong> {report.comparison_locality_name}</p>
              )}
            </div>
          </div>

          <div className="p-4 bg-teal-50/50 rounded-2xl border border-teal-200 space-y-2">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider block">
              Cryptographic Integrity
            </span>
            <div className="space-y-1 font-mono text-[11px] text-teal-950">
              <p className="break-all"><strong>Digest:</strong> {report.verification_hash}</p>
              <p className="font-sans text-teal-800 text-[11px]">
                Certified by LocalLens Independent Public Register. Unmodified since generation.
              </p>
            </div>
          </div>
        </div>

        {/* Re-Explore Link */}
        <div className="pt-2 flex justify-between items-center text-xs">
          <span className="text-slate-500">Need updated live data?</span>
          <Link
            to={`/explore?q=${encodeURIComponent(report.locality_name)}`}
            className="font-bold text-teal-700 hover:underline inline-flex items-center gap-1"
          >
            <span>Re-explore {report.locality_name} live</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
