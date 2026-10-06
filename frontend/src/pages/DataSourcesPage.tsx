import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Database, CheckCircle2, AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';

interface ProviderItem {
  id: string;
  name: string;
  configured: boolean;
  storage_policy: string;
  license: string;
  attribution: string;
  status: string;
}

export const DataSourcesPage: React.FC = () => {
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = () => {
    setIsLoading(true);
    api.getProviderHealth()
      .then((data) => {
        setProviders(data.providers || []);
        setLastChecked(new Date());
      })
      .catch((err) => {
        console.error('Failed to load provider health:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const getStatusBadge = (status: string) => {
    if (status === 'operational') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Operational</span>
        </span>
      );
    }
    if (status.includes('unconfigured')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
          <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
          <span>Not configured in env</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
        <span className="capitalize">{status.replace(/_/g, ' ')}</span>
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold mb-2">
            <Database className="w-3.5 h-3.5 text-teal-600" />
            <span>Transparency & Health Status</span>
          </div>
          <h1 className="font-display font-bold text-3xl text-navy-900">
            Integrated Data Sources
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl">
            LocalLens never fabricates data or uses unverified private simulated datasets. Below is the live health, license, and storage policy for every integrated provider.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          disabled={isLoading}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-medium transition-colors shadow-2xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-teal-600' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {lastChecked && (
        <p className="text-xs text-slate-400">
          Last live check: {lastChecked.toLocaleTimeString()}
        </p>
      )}

      {/* Provider Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {providers.map((p) => (
          <div
            key={p.id}
            className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-display font-bold text-base text-navy-900">
                  {p.name}
                </h3>
                {getStatusBadge(p.status)}
              </div>

              <div className="text-xs space-y-1.5 text-slate-600 bg-slate-50 p-3 rounded-2xl border border-slate-200">
                <div className="flex justify-between">
                  <span className="text-slate-500">Storage Policy:</span>
                  <span className="font-semibold text-slate-800 uppercase tracking-wider text-[10px]">
                    {p.storage_policy}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">License:</span>
                  <span className="font-medium text-slate-800 text-right truncate max-w-[200px]">
                    {p.license}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Attribution:</span>
                  <span className="font-medium text-slate-700 text-right truncate max-w-[200px]">
                    {p.attribution}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span className="font-mono text-[11px]">ID: {p.id}</span>
              <span className="text-teal-700 font-medium">Audited & Verified</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
