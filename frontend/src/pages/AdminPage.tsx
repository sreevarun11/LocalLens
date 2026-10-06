import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Activity, Server, Database, Shield, CheckCircle2, AlertTriangle, XCircle, RefreshCw, Cpu, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export const AdminPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const fetchHealthData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hData, pData] = await Promise.all([
        api.getHealth().catch(e => ({ status: 'error', error: e.message })),
        api.getProviderHealth().catch(() => [])
      ]);
      setHealth(hData);
      setProviders(Array.isArray(pData) ? pData : (pData?.providers || []));
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve system diagnostics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

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

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-6 border-b border-slate-200 gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 bg-slate-200 text-slate-700 text-[10px] font-bold uppercase tracking-wider rounded">Internal Diagnostics</span>
            <h1 className="text-2xl font-bold text-slate-800">System & Provider Health</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time status of data providers, live API connectors, caching policies, and runtime feature flags.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastChecked && (
            <span className="text-xs text-slate-400">Last checked: {lastChecked}</span>
          )}
          <button
            onClick={fetchHealthData}
            disabled={loading}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Diagnostics
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* System Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
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

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Database className="h-4 w-4 text-indigo-700" /> Primary Database
          </div>
          <div className="text-lg font-bold text-slate-800">SQLite 3 (WAL Mode)</div>
          <div className="text-[11px] text-slate-400 mt-1">Automatic schema auto-init</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Cpu className="h-4 w-4 text-emerald-700" /> Intelligence Engine
          </div>
          <div className="text-lg font-bold text-slate-800">
            {health?.flags?.FEATURE_AI ? 'Dual Model (Gemini + Local)' : 'Deterministic Rules'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Always available fallback</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-medium mb-1">
            <Shield className="h-4 w-4 text-amber-700" /> Integrity Guard
          </div>
          <div className="text-lg font-bold text-slate-800">Active</div>
          <div className="text-[11px] text-slate-400 mt-1">Zero data fabrication policy</div>
        </div>
      </div>

      {/* Feature Flags Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-8">
        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-teal-700" /> Active Feature Flags
        </h2>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {health?.flags ? (
            Object.entries(health.flags).map(([key, val]) => (
              <div key={key} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
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
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-8">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-800">Integrated Providers & Transparency</h2>
            <p className="text-xs text-slate-500 mt-0.5">Live configuration, licensing terms, and caching compliance per provider.</p>
          </div>
          <Link to="/data-sources" className="text-xs text-teal-700 hover:underline flex items-center gap-1 font-medium">
            Public Data Sources View <ExternalLink className="h-3 w-3" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
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
                        <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded font-sans text-[11px] font-medium">
                          Live Only (No caching)
                        </span>
                      ) : (
                        <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-sans text-[11px] font-medium">
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
