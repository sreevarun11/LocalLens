import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Zap,
  Bookmark,
  History,
  ChevronRight,
  ExternalLink,
  Plus,
  Compass,
  AlertTriangle,
  Clock,
  FileText,
  Download,
  ShieldCheck,
  Loader2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, credits, isEmailVerified, isAuthenticated, isLoading: authLoading, verifyEmailSimulate } = useAuth();
  
  const [savedLocations, setSavedLocations] = useState<any[]>([]);
  const [searchHistory, setSearchHistory] = useState<any[]>([]);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isAuthenticated) {
      Promise.all([
        api.getSavedLocations().catch(() => []),
        api.getSearchHistory().catch(() => []),
        api.listReports().catch(() => [])
      ]).then(([saved, history, reports]) => {
        setSavedLocations(saved || []);
        setSearchHistory(history || []);
        setRecentReports(reports || []);
      }).finally(() => setIsLoadingData(false));
    }
  }, [isAuthenticated, authLoading, navigate]);

  const handleDownloadPdf = async (reportId: string, title: string) => {
    setDownloadingId(reportId);
    try {
      await api.downloadReportPdf(reportId, `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`);
    } catch (e) {
      console.error('PDF download error:', e);
      window.open(api.getPdfUrl(reportId, true), '_blank');
    } finally {
      setDownloadingId(null);
    }
  };

  if (authLoading || isLoadingData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-slate-200 rounded w-1/4" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="h-32 bg-slate-100 rounded-3xl" />
            <div className="h-32 bg-slate-100 rounded-3xl" />
            <div className="h-32 bg-slate-100 rounded-3xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-900">
            Welcome back, {user?.display_name}!
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage your saved neighborhoods, decision reports, and account credits.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/explore"
            className="flex items-center gap-2 px-4 py-2 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors shadow-xs"
          >
            <Compass className="w-4 h-4" />
            <span>Explore Locality</span>
          </Link>
          <Link
            to="/reports/create"
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-xl text-xs font-semibold hover:bg-teal-700 transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Generate Report</span>
          </Link>
        </div>
      </div>

      {/* Verification Notice */}
      {!isEmailVerified && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-3xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
            <div>
              <p className="text-xs font-bold text-amber-900">Email Verification Pending</p>
              <p className="text-[11px] text-amber-800 mt-0.5">
                Verify your email address ({user?.email}) to unlock your 3 free decision report credits.
              </p>
            </div>
          </div>
          <button
            onClick={() => verifyEmailSimulate()}
            className="px-4 py-2 bg-amber-800 text-white rounded-xl text-xs font-semibold hover:bg-amber-900 transition-colors whitespace-nowrap self-start sm:self-auto cursor-pointer"
          >
            Simulate Verification
          </button>
        </div>
      )}

      {/* Key Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Credits Card (Reports Remaining) */}
        <div className="p-6 bg-gradient-to-br from-teal-500/10 via-teal-500/5 to-transparent bg-white rounded-3xl border border-teal-200/60 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800">
              Reports Remaining
            </span>
            <div className="p-2 bg-teal-100 text-teal-700 rounded-xl">
              <Zap className="w-4 h-4 fill-teal-600" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-3xl font-extrabold text-navy-900">
              {credits?.credits_remaining ?? 0}
            </span>
            <span className="text-xs text-slate-500 font-medium">credits available</span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
            <span>{credits?.credits_used ?? 0} reports generated</span>
            <Link to="/payments" className="text-teal-700 font-bold hover:underline">
              Add Credits
            </Link>
          </div>
        </div>

        {/* Saved Locations Summary */}
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Saved Locations
            </span>
            <div className="p-2 bg-slate-100 text-slate-700 rounded-xl">
              <Bookmark className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-3xl font-extrabold text-navy-900">
              {savedLocations.length}
            </span>
            <span className="text-xs text-slate-500 font-medium">bookmarked</span>
          </div>
          <Link
            to="/saved"
            className="text-xs font-semibold text-teal-700 hover:text-teal-800 inline-flex items-center gap-1"
          >
            <span>Manage saved locations</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Recent Search History Summary */}
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Recent Searches
            </span>
            <div className="p-2 bg-slate-100 text-slate-700 rounded-xl">
              <History className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-3xl font-extrabold text-navy-900">
              {searchHistory.length}
            </span>
            <span className="text-xs text-slate-500 font-medium">recent lookups</span>
          </div>
          <Link
            to="/history"
            className="text-xs font-semibold text-teal-700 hover:text-teal-800 inline-flex items-center gap-1"
          >
            <span>View all search history</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Recent Reports Section (Section 13) */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display text-base font-bold text-navy-900">
                Recent Reports
              </h2>
              <p className="text-xs text-slate-500">
                Permanent, QR-verified neighborhood decision reports generated on your account.
              </p>
            </div>
          </div>
          <Link to="/reports" className="text-xs text-teal-700 font-semibold hover:underline">
            View All Reports
          </Link>
        </div>

        {recentReports.length === 0 ? (
          <div className="text-center py-8 text-slate-400 space-y-2">
            <FileText className="w-8 h-8 mx-auto text-slate-300" />
            <p className="text-xs font-medium text-slate-600">No reports yet.</p>
            <Link
              to="/reports/create"
              className="text-xs font-semibold text-teal-700 hover:underline inline-block"
            >
              Generate your first decision report
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {recentReports.slice(0, 4).map((report) => (
              <div key={report.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 p-2 rounded-xl transition-colors">
                <div>
                  <h4 className="font-bold text-sm text-navy-900">{report.title}</h4>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                    <span>{report.locality_name}</span>
                    <span>·</span>
                    <span>{new Date(report.created_at).toLocaleDateString()}</span>
                    <span>·</span>
                    <span className="font-mono text-slate-400 text-[10px]">
                      Hash: {report.verification_hash ? report.verification_hash.slice(0, 12) : ''}...
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleDownloadPdf(report.id, report.title)}
                    disabled={downloadingId === report.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
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
                    className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Open PDF in new tab"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>

                  <Link
                    to={`/verify/${report.id}`}
                    target="_blank"
                    className="p-1.5 text-teal-700 hover:text-teal-900 hover:bg-teal-50 rounded-lg transition-colors"
                    title="Public QR Verification"
                  >
                    <ShieldCheck className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Saved Locations & History Grids */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Saved Locations Box */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-display text-base font-bold text-navy-900 flex items-center gap-2">
              <Bookmark className="w-4 h-4 text-teal-600" />
              <span>Saved Locations</span>
            </h2>
            <Link to="/saved" className="text-xs text-teal-700 font-semibold hover:underline">
              View All
            </Link>
          </div>

          {savedLocations.length === 0 ? (
            <div className="text-center py-6 text-slate-400 space-y-2">
              <Bookmark className="w-8 h-8 mx-auto text-slate-300" />
              <p className="text-xs font-medium text-slate-600">No saved locations yet.</p>
              <Link
                to="/explore"
                className="text-xs font-semibold text-teal-700 hover:underline inline-block"
              >
                Search and bookmark an area
              </Link>
            </div>
          ) : (
            <div className="space-y-2.5">
              {savedLocations.slice(0, 4).map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors flex items-center justify-between gap-3"
                >
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">{item.locality_name}</h4>
                    {item.label && (
                      <span className="text-[10px] text-teal-800 bg-teal-50 px-2 py-0.5 rounded-md font-medium inline-block mt-0.5">
                        {item.label}
                      </span>
                    )}
                  </div>
                  <Link
                    to={`/explore?q=${encodeURIComponent(item.locality_name)}`}
                    className="p-2 text-slate-400 hover:text-teal-700 hover:bg-white rounded-lg transition-colors"
                    title="Explore again"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Search History Box */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-display text-base font-bold text-navy-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-600" />
              <span>Recent Searches</span>
            </h2>
            <Link to="/history" className="text-xs text-teal-700 font-semibold hover:underline">
              View All
            </Link>
          </div>

          {searchHistory.length === 0 ? (
            <div className="text-center py-6 text-slate-400 space-y-2">
              <History className="w-8 h-8 mx-auto text-slate-300" />
              <p className="text-xs font-medium text-slate-600">No recent searches yet.</p>
              <Link
                to="/explore"
                className="text-xs font-semibold text-teal-700 hover:underline inline-block"
              >
                Start exploring
              </Link>
            </div>
          ) : (
            <div className="space-y-2.5">
              {searchHistory.slice(0, 4).map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors flex items-center justify-between gap-3"
                >
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">{item.locality_name}</h4>
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      {new Date(item.searched_at).toLocaleDateString()} · {item.provider}
                    </span>
                  </div>
                  <Link
                    to={`/explore?q=${encodeURIComponent(item.locality_name)}`}
                    className="text-xs font-semibold text-teal-700 hover:underline flex items-center gap-1"
                  >
                    <span>Re-explore</span>
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
