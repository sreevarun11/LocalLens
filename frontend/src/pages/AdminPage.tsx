import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  Server,
  Database,
  Shield,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Cpu,
  ExternalLink,
  Users,
  FileText,
  CreditCard,
  Lock,
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const AdminPage: React.FC = () => {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [health, setHealth] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const isAdmin = Boolean(user?.is_admin);

  const fetchHealthData = async () => {
    if (!isAuthenticated || !isAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const [hData, pData, aData] = await Promise.all([
        api.getHealth().catch((e) => ({ status: 'error', error: e.message })),
        api.getProviderHealth().catch(() => []),
        api.getAdminAnalytics().catch(() => null)
      ]);
      setHealth(hData);
      setProviders(Array.isArray(pData) ? pData : (pData?.providers || []));
      setAnalytics(aData);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve system diagnostics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && isAuthenticated && isAdmin) {
      fetchHealthData();
    }
  }, [authLoading, isAuthenticated, isAdmin]);

  const getStatusBadge = (status: string, configured: boolean) => {
    if (status === 'operational') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-xs font-semibold">
          <CheckCircle2 className="h-3.5 w-3.5" /> Operational
        </span>
      );
    }
    if (!configured || status?.includes('unconfigured')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded text-xs font-semibold">
          <AlertTriangle className="h-3.5 w-3.5" /> Config Required
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-semibold">
        <XCircle className="h-3.5 w-3.5" /> Degraded / Offline
      </span>
    );
  };

  // 1. Loading Authentication State
  if (authLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center space-y-4">
        <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-500 font-medium">Verifying administrator authorization…</p>
      </div>
    );
  }

  // 2. Access Guard for Non-Admin Users
  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16">
        <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-xs text-center space-y-5">
          <div className="w-14 h-14 bg-rose-50 border border-rose-100 rounded-2xl flex items-center justify-center text-rose-600 mx-auto">
            <Lock className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
              Access Restricted
            </span>
            <h1 className="font-display font-bold text-2xl text-navy-900 mt-2">
              Administrator Authorization Required
            </h1>
            <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
              The internal diagnostics console, real database tables, and metrics are protected by role-based authorization.
              Please sign in with the platform administrator account (<strong className="text-slate-700">sreevarun</strong>) to proceed.
            </p>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/profile"
              className="px-5 py-2.5 bg-teal-800 hover:bg-teal-900 text-white text-xs font-semibold rounded-xl transition-colors inline-flex items-center gap-2 shadow-xs"
            >
              <span>Sign In as Admin</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <Link
              to="/explore"
              className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-colors"
            >
              Return to Explore
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 3. Authorized Administrator View
  return (
    <div className="max-w-6xl mx-auto px-4 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-teal-50 text-teal-800 border border-teal-200 text-[10px] font-bold uppercase tracking-wider rounded-full">
              Platform Admin: {user?.username || 'sreevarun'}
            </span>
            <h1 className="text-2xl font-bold text-slate-900">System Administration & Analytics</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time diagnostics, live SQLite database records, recent activities, and transparency auditing.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastChecked && (
            <span className="text-xs text-slate-400">Last synced: {lastChecked}</span>
          )}
          <button
            onClick={fetchHealthData}
            disabled={loading}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-medium rounded-lg transition-colors flex items-center gap-2 shadow-2xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* System Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Server className="h-4 w-4 text-teal-700" /> Backend Core
          </div>
          <div className="text-lg font-bold text-slate-800">
            {health?.status === 'ok' ? 'Online' : 'Checking...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {health?.app || 'LocalLens API'} v{health?.version || '4.0.0'}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Database className="h-4 w-4 text-indigo-700" /> Primary Database
          </div>
          <div className="text-lg font-bold text-slate-800">SQLite 3 (WAL Mode)</div>
          <div className="text-[11px] text-slate-400 mt-1">backend/data/locallens_dev.db</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Cpu className="h-4 w-4 text-emerald-700" /> Spatial Intelligence
          </div>
          <div className="text-lg font-bold text-slate-800">
            {health?.flags?.FEATURE_AI ? 'Dual Model (Gemini + Deterministic)' : 'Deterministic Rules'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Zero synthetic hallucination</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Shield className="h-4 w-4 text-amber-700" /> Integrity Guard
          </div>
          <div className="text-lg font-bold text-slate-800">Active</div>
          <div className="text-[11px] text-slate-400 mt-1">Zero data fabrication policy</div>
        </div>
      </div>

      {/* Platform Analytics Cards */}
      {analytics && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Database className="h-4 w-4 text-teal-700" /> Platform Usage & Database Counts
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Live counts directly queried from the active database.</p>
            </div>
            <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              Live Database Metrics
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Registered Accounts</span>
              <span className="text-2xl font-bold text-navy-900 block mt-1">{analytics.users?.total_registered ?? 0}</span>
              <span className="text-[10px] text-slate-400">Total profiles</span>
            </div>

            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Searches Conducted</span>
              <span className="text-2xl font-bold text-navy-900 block mt-1">{analytics.activity?.total_searches ?? 0}</span>
              <span className="text-[10px] text-slate-400">Locality explorations</span>
            </div>

            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Reports Generated</span>
              <span className="text-2xl font-bold text-navy-900 block mt-1">{analytics.activity?.total_reports_generated ?? 0}</span>
              <span className="text-[10px] text-slate-400">{analytics.activity?.total_report_credits_used ?? 0} credits used</span>
            </div>

            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Successful Orders</span>
              <span className="text-2xl font-bold text-emerald-800 block mt-1">
                {analytics.payments?.successful_orders ?? 0} <span className="text-xs font-normal text-slate-500">(₹{analytics.payments?.total_revenue_inr ?? 0})</span>
              </span>
              <span className="text-[10px] text-slate-400">₹{analytics.payments?.report_price_inr ?? 29}/report tier</span>
            </div>
          </div>
        </div>
      )}

      {/* Real Live Database Tables */}
      {analytics && (
        <div className="space-y-6">
          {/* Table 1: Recent Registrations */}
          <div className="bg-white border border-slate-200 rounded-3xl shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-teal-700" />
                <h3 className="font-bold text-sm text-navy-900">Recent User Registrations</h3>
              </div>
              <span className="text-[11px] text-slate-500">Latest 10 Accounts</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Username</th>
                    <th className="py-3 px-4">Display Name</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Email Status</th>
                    <th className="py-3 px-4">Registered Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {analytics.users?.recent_registrations?.length > 0 ? (
                    analytics.users.recent_registrations.map((u: any) => (
                      <tr key={u.id} className="hover:bg-slate-50/70">
                        <td className="py-3 px-4 font-mono font-medium text-slate-800">
                          {u.username}
                        </td>
                        <td className="py-3 px-4 text-slate-700">
                          {u.display_name || '—'}
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {u.email || '—'}
                        </td>
                        <td className="py-3 px-4">
                          {u.is_admin ? (
                            <span className="px-2 py-0.5 bg-teal-50 text-teal-800 border border-teal-200 rounded text-[11px] font-bold">
                              Admin
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[11px]">
                              User
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {u.is_email_verified ? (
                            <span className="text-emerald-700 font-semibold">Verified</span>
                          ) : (
                            <span className="text-amber-700 font-semibold">Pending</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {u.created_at ? new Date(u.created_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-slate-400">
                        No user registrations recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Table 2: Recent Reports */}
          <div className="bg-white border border-slate-200 rounded-3xl shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-700" />
                <h3 className="font-bold text-sm text-navy-900">Recent Report Generation Activity</h3>
              </div>
              <span className="text-[11px] text-slate-500">Latest 10 Reports</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Locality / Title</th>
                    <th className="py-3 px-4">Coordinates</th>
                    <th className="py-3 px-4">User ID</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Generated Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {analytics.activity?.recent_reports?.length > 0 ? (
                    analytics.activity.recent_reports.map((r: any) => (
                      <tr key={r.id} className="hover:bg-slate-50/70">
                        <td className="py-3 px-4 font-semibold text-slate-800">
                          {r.locality_name || r.title || 'Untitled Report'}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-600">
                          {r.lat?.toFixed(4)}, {r.lng?.toFixed(4)}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                          {r.user_id ? `${r.user_id.slice(0, 8)}…` : 'Anonymous'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded text-[11px] font-semibold capitalize">
                            {r.status || 'generated'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-400">
                        No report generation events logged yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Table 3: Recent Payments */}
          <div className="bg-white border border-slate-200 rounded-3xl shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-teal-700" />
                <h3 className="font-bold text-sm text-navy-900">Recent Payment Records & Orders</h3>
              </div>
              <span className="text-[11px] text-slate-500">Latest 10 Transactions</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Order ID</th>
                    <th className="py-3 px-4">Payment ID</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {analytics.payments?.recent_payments?.length > 0 ? (
                    analytics.payments.recent_payments.map((p: any) => (
                      <tr key={p.id} className="hover:bg-slate-50/70">
                        <td className="py-3 px-4 font-mono font-medium text-slate-800">
                          {p.razorpay_order_id || p.id}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">
                          {p.razorpay_payment_id || '—'}
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-800">
                          ₹{p.amount_inr || 29}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold capitalize ${
                            p.status === 'paid'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border border-amber-200'
                          }`}>
                            {p.status || 'created'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {p.created_at ? new Date(p.created_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-400">
                        No transactions recorded in database yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Feature Flags Section */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-teal-700" /> Active Feature Flags & Runtime Configuration
        </h2>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {health?.flags ? (
            Object.entries(health.flags).map(([key, val]) => (
              <div key={key} className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <span className="text-[11px] font-mono text-slate-600 block truncate">{key}</span>
                <span className={`inline-block mt-1 text-xs font-bold ${val ? 'text-emerald-700' : 'text-slate-400'}`}>
                  {val ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 col-span-5">No flags loaded</p>
          )}
        </div>
      </div>

      {/* Data Providers Status Table */}
      <div className="bg-white border border-slate-200 rounded-3xl shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <h2 className="text-base font-bold text-slate-900">Integrated Providers & Transparency</h2>
            <p className="text-xs text-slate-500 mt-0.5">Live configuration, licensing terms, and caching compliance per provider.</p>
          </div>
          <Link to="/data-sources" className="text-xs text-teal-700 hover:underline flex items-center gap-1 font-semibold">
            Public Data Sources View <ExternalLink className="h-3 w-3" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Provider / API</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Storage Policy</th>
                <th className="py-3 px-4">License / Terms</th>
                <th className="py-3 px-4">Attribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {providers.length > 0 ? (
                providers.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70">
                    <td className="py-3 px-4 font-semibold text-slate-800">
                      {p.name}
                      <span className="block text-[10px] font-mono text-slate-400">{p.id}</span>
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(p.status, p.configured)}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      {p.storage_policy === 'live_only' ? (
                        <span className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded font-sans text-[11px] font-medium border border-amber-200">
                          Live Only (No caching)
                        </span>
                      ) : (
                        <span className="text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded font-sans text-[11px] font-medium border border-emerald-200">
                          Storable / Cached
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {p.license}
                    </td>
                    <td className="py-3 px-4 text-slate-500 italic">
                      {p.attribution}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    {loading ? 'Checking provider statuses...' : 'No provider metadata returned'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
