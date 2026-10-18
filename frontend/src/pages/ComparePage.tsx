import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { SearchBar } from '../components/search/SearchBar';
import {
  LocationDetails
} from '../types';
import {
  Scale,
  CheckCircle2,
  AlertTriangle,
  CircleSlash,
  ArrowRightLeft,
  Layers,
  Sparkles,
  AlertCircle
} from 'lucide-react';

interface ComparisonRow {
  category: string;
  priority: string;
  metric: string;
  label: string;
  val_a: string | number | null;
  val_b: string | number | null;
  unit: string | null;
  comparability: 'comparable' | 'partly_comparable' | 'not_comparable';
  comparability_reason: string | null;
  difference_statement: string | null;
  source_a: string;
  source_b: string;
  caveat: string | null;
}

interface ComparisonSummary {
  locality_a_name: string;
  locality_b_name: string;
  key_differences: string[];
  data_gaps: string[];
  coverage_differences: string[];
  rows: ComparisonRow[];
}

export const ComparePage: React.FC = () => {
  const routerState = useLocation().state as { locationA?: LocationDetails } | undefined;

  const [locA, setLocA] = useState<LocationDetails | null>(routerState?.locationA || null);
  const [locB, setLocB] = useState<LocationDetails | null>(null);

  const [summary, setSummary] = useState<ComparisonSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadWaterCrime, setLoadWaterCrime] = useState(false);
  const [radiusM, setRadiusM] = useState<number>(1500);

  const runComparison = async (locationA: LocationDetails, locationB: LocationDetails, customRadius?: number) => {
    setIsLoading(true);
    const effectiveRadius = customRadius ?? radiusM;
    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loc_a_name: locationA.name,
          loc_a_lat: locationA.lat,
          loc_a_lng: locationA.lng,
          loc_b_name: locationB.name,
          loc_b_lat: locationB.lat,
          loc_b_lng: locationB.lng,
          radius_m: effectiveRadius,
          load_water_crime: loadWaterCrime
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (err) {
      console.error('Comparison error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLocASelected = (l: LocationDetails) => {
    setLocA(l);
    if (locB) {
      runComparison(l, locB);
    }
  };

  const handleLocBSelected = (l: LocationDetails) => {
    setLocB(l);
    if (locA) {
      runComparison(locA, l);
    }
  };

  const getComparabilityBadge = (status: string, reason: string | null) => {
    switch (status) {
      case 'comparable':
        return (
          <span
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full"
            title="Directly comparable (same source, radius, and query)"
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Comparable</span>
          </span>
        );
      case 'partly_comparable':
        return (
          <span
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full"
            title={reason || 'Partly comparable'}
          >
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Partly comparable</span>
          </span>
        );
      default:
        return (
          <span
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-700 bg-slate-100 border border-slate-300 px-2 py-0.5 rounded-full"
            title={reason || 'Not comparable'}
          >
            <CircleSlash className="w-3 h-3 text-slate-500" />
            <span>Not comparable</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <Scale className="w-3.5 h-3.5 text-teal-600" />
          <span>Side-by-Side Evidence Analysis</span>
        </div>
        <h1 className="font-display font-bold text-3xl sm:text-4xl text-navy-900">
          Compare Two Localities
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          LocalLens evaluates both areas against identical criteria. We show concrete differences and data depth — never declaring subjective "winners" or calculating composite scores.
        </p>
      </div>

      {/* Survey Radius Selector */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-navy-900 uppercase tracking-wider">Survey Radius:</span>
          <span className="text-xs text-slate-500">Evaluates both localities with the exact same straight-line radius</span>
        </div>
        <div className="flex items-center gap-2">
          {[500, 1000, 1500, 2000, 3000].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setRadiusM(r);
                if (locA && locB) {
                  runComparison(locA, locB, r);
                }
              }}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                radiusM === r
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {r >= 1000 ? `${r / 1000} km` : `${r} m`}
            </button>
          ))}
        </div>
      </div>

      {/* Dual Search Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Locality A */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">
              Locality A (Base)
            </span>
            {locA && (
              <span className="text-[11px] text-slate-500 font-mono">
                {locA.lat.toFixed(4)}, {locA.lng.toFixed(4)}
              </span>
            )}
          </div>
          <SearchBar
            placeholder="Search first locality (e.g. Hyderabad)"
            initialValue={locA?.formatted_address || ''}
            onLocationSelected={handleLocASelected}
          />
          {locA && (
            <p className="text-xs text-slate-700 font-semibold mt-1">
              Selected: {locA.name}
            </p>
          )}
        </div>

        {/* Locality B */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">
              Locality B (Comparison)
            </span>
            {locB && (
              <span className="text-[11px] text-slate-500 font-mono">
                {locB.lat.toFixed(4)}, {locB.lng.toFixed(4)}
              </span>
            )}
          </div>
          <SearchBar
            placeholder="Search second locality (e.g. Nizamabad)"
            initialValue={locB?.formatted_address || ''}
            onLocationSelected={handleLocBSelected}
          />
          {locB && (
            <p className="text-xs text-slate-700 font-semibold mt-1">
              Selected: {locB.name}
            </p>
          )}
        </div>
      </div>

      {/* Loading Indicator */}
      {isLoading && (
        <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <h3 className="font-semibold text-sm text-navy-900">
            Comparing Both Localities in Parallel…
          </h3>
          <p className="text-xs text-slate-500">
            Querying identical {radiusM >= 1000 ? `${radiusM / 1000} km` : `${radiusM} m`} radii from spatial providers and validating comparability rules.
          </p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!locA || !locB) && (
        <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500 mx-auto">
            <ArrowRightLeft className="w-6 h-6" />
          </div>
          <h3 className="font-display font-semibold text-base text-slate-800">
            Select Two Localities to Begin
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Choose both a base area and comparison target (for example, <span className="font-semibold text-slate-700">"Koramangala"</span> vs <span className="font-semibold text-slate-700">"Indiranagar"</span>) to view objective side-by-side differences.
          </p>
        </div>
      )}

      {/* Comparison Results */}
      {!isLoading && summary && locA && locB && (
        <div className="space-y-6">
          {/* Key Differences Callout */}
          <div className="flex justify-end">
            <button
              onClick={() => {
                const nextVal = !loadWaterCrime;
                setLoadWaterCrime(nextVal);
                if (locA && locB) runComparison(locA, locB);
              }}
              className="px-3.5 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 shadow-2xs transition-colors flex items-center gap-1.5"
            >
              <span>{loadWaterCrime ? 'Hide Water & Crime Data' : 'Load water & crime for both'}</span>
            </button>
          </div>

          {summary.key_differences.length > 0 && (
            <div className="p-6 bg-teal-50/70 rounded-3xl border border-teal-200/80 space-y-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-teal-700" />
                <h3 className="font-display font-bold text-base text-teal-950">
                  Key Differences
                </h3>
              </div>
              <ul className="space-y-1.5 text-xs text-slate-700 pl-4 list-disc">
                {summary.key_differences.map((diff, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {diff}
                  </li>
                ))}
              </ul>
              <p className="text-[11px] text-teal-800 italic pt-1">
                Notice: These differences reflect mapped proximity in integrated databases. Neither locality is judged as "better".
              </p>
            </div>
          )}

          {/* Side-by-Side Comparison Table */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h3 className="font-display font-bold text-base text-navy-900">
                  Side-by-Side Metrics & Comparability
                </h3>
                <p className="text-xs text-slate-500">
                  Identical radius: {radiusM >= 1000 ? `${radiusM / 1000} km` : `${radiusM} m`} straight-line distance
                </p>
              </div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Enforced comparability rules
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs divide-y divide-slate-200">
                <thead className="bg-slate-100/70 text-slate-700 font-semibold">
                  <tr>
                    <th className="p-4 w-1/4">Metric / Dimension</th>
                    <th className="p-4 w-1/4 text-teal-900 bg-teal-50/40">
                      {locA.name}
                    </th>
                    <th className="p-4 w-1/4 text-navy-900">
                      {locB.name}
                    </th>
                    <th className="p-4 w-1/4">Comparability & Difference</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="p-4 font-semibold text-slate-800 align-top">
                        {row.label}
                        {row.caveat && (
                          <span className="block text-[10px] text-slate-400 font-normal mt-0.5 italic">
                            {row.caveat}
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-slate-900 font-bold bg-teal-50/20 align-top">
                        {row.val_a !== null && row.val_a !== undefined ? (
                          <span>
                            {row.val_a} {row.unit || ''}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-normal">No data found</span>
                        )}
                      </td>
                      <td className="p-4 text-slate-900 font-bold align-top">
                        {row.val_b !== null && row.val_b !== undefined ? (
                          <span>
                            {row.val_b} {row.unit || ''}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-normal">No data found</span>
                        )}
                      </td>
                      <td className="p-4 align-top space-y-1.5">
                        <div>{getComparabilityBadge(row.comparability, row.comparability_reason)}</div>
                        {row.difference_statement && (
                          <p className="text-[11px] text-slate-600 leading-snug">
                            {row.difference_statement}
                          </p>
                        )}
                        {row.comparability_reason && row.comparability !== 'comparable' && (
                          <p className="text-[10px] text-amber-800 italic">
                            {row.comparability_reason}
                          </p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Gaps & Coverage Differences */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Common Data Gaps */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <h4 className="font-display font-bold text-sm text-navy-900">
                  Shared Data Gaps
                </h4>
              </div>
              <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
                {summary.data_gaps.map((gap, idx) => (
                  <li key={idx}>{gap}</li>
                ))}
              </ul>
            </div>

            {/* Coverage Differences */}
            <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-teal-600" />
                <h4 className="font-display font-bold text-sm text-navy-900">
                  Coverage Differences
                </h4>
              </div>
              <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
                {summary.coverage_differences.map((diff, idx) => (
                  <li key={idx}>{diff}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
