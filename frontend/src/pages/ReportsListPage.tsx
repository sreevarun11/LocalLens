import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Download,
  ExternalLink,
  ShieldCheck,
  Plus,
  Loader2,
  Calendar,
  MapPin,
  Scale
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [reports, setReports] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isAuthenticated) {
      api.listReports()
        .then((data) => setReports(data || []))
        .catch(console.error)
        .finally(() => setIsLoading(false));
    }
  }, [isAuthenticated, authLoading, navigate]);

  const handleDownloadPdf = async (reportId: string, title: string) => {
    setDownloadingId(reportId);
    try {
      await api.downloadReportPdf(reportId, `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`);
    } catch (e) {
      console.error('Download error:', e);
      window.open(api.getPdfUrl(reportId, true), '_blank');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-900 flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-teal-600" />
            <span>Decision Reports</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Archival, QR-verified neighborhood intelligence reports stored with cryptographic authenticity digests.
          </p>
        </div>

        <Link
          to="/reports/create"
          className="flex items-center gap-2 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Decision Report</span>
        </Link>
      </div>

      {/* Reports List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-slate-100 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <FileText className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="font-display font-semibold text-slate-800 text-base">
            No reports yet.
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            You haven't generated any neighborhood decision reports yet. Explore any locality and build an archival report.
          </p>
          <Link
            to="/reports/create"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Generate your first report</span>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-100">
                    Verified Report
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    ID: {report.id}
                  </span>
                </div>

                <Link
                  to={`/reports/${report.id}`}
                  className="font-display font-bold text-base text-navy-900 hover:text-teal-700 transition-colors block"
                >
                  {report.title}
                </Link>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>{report.locality_name}</span>
                  </span>
                  {report.comparison_locality_name && (
                    <span className="flex items-center gap-1 text-teal-700 font-medium">
                      <Scale className="w-3.5 h-3.5" />
                      <span>Compared with {report.comparison_locality_name}</span>
                    </span>
                  )}
                  <span className="flex items-center gap-1 text-slate-400">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{new Date(report.created_at).toLocaleDateString()}</span>
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
                <button
                  type="button"
                  onClick={() => handleDownloadPdf(report.id, report.title)}
                  disabled={downloadingId === report.id}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
                >
                  {downloadingId === report.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Download className="w-3.5 h-3.5" />
                  )}
                  <span>Download PDF</span>
                </button>

                <a
                  href={api.getPdfUrl(report.id, true)}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 text-slate-600 hover:text-navy-900 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200"
                  title="Open PDF in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>

                <Link
                  to={`/verify/${report.id}`}
                  target="_blank"
                  className="p-2 text-teal-700 hover:text-teal-900 hover:bg-teal-50 rounded-xl transition-colors border border-teal-200"
                  title="Public Verification"
                >
                  <ShieldCheck className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
