import React, { useState } from 'react';
import { Droplets, ShieldAlert, Info, AlertCircle } from 'lucide-react';
import { ModuleResult, WaterQualityData, CrimeData } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { DataSourceDrawer } from '../common/DataSourceDrawer';

interface WaterCardProps {
  result: ModuleResult<WaterQualityData> | null;
  isLoading: boolean;
  onLoadRequested?: () => void;
}

export const WaterCard: React.FC<WaterCardProps> = ({
  result,
  isLoading,
  onLoadRequested
}) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!result && !isLoading) {
    return (
      <div className="p-4 bg-white rounded-2xl border border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-blue-50 text-blue-700 rounded-xl">
            <Droplets className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-semibold text-xs text-slate-800">Water Quality</h4>
            <p className="text-[11px] text-slate-500">Central Ground Water Board (CGWB)</p>
          </div>
        </div>
        {onLoadRequested && (
          <button
            onClick={onLoadRequested}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition-colors"
          >
            Check Status
          </button>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 bg-white rounded-2xl border border-slate-200 animate-pulse space-y-2">
        <div className="h-4 bg-slate-200 rounded w-1/4"></div>
        <div className="h-6 bg-slate-100 rounded w-3/4"></div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <>
      <div className="p-5 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-50 text-blue-700 rounded-xl">
              <Droplets className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-display font-bold text-sm text-navy-900">
                Water Quality
              </h4>
              <p className="text-[11px] text-slate-500">
                Official groundwater bulletins & municipal data
              </p>
            </div>
          </div>

          <button
            onClick={() => setDrawerOpen(true)}
            className="text-[11px] font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1 bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-100"
          >
            <Info className="w-3 h-3" />
            <span>Why?</span>
          </button>
        </div>

        <StatusBadge
          status={result.status}
          provenanceKind={result.provenance_kind}
          size="sm"
        />

        <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-600 space-y-1.5">
          <p className="font-medium text-slate-800">
            No integrated water-quality dataset covers this specific location.
          </p>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Water quality varies drastically by individual society: municipal pipeline (e.g. Cauvery), private tanker supply, or borewell TDS levels.
          </p>
        </div>

        <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
          <span>Granularity: District level</span>
          <span className="font-medium text-teal-700">Verify on site recommended</span>
        </div>
      </div>

      <DataSourceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Water Quality Coverage"
        status={result.status}
        provenanceKind={result.provenance_kind}
        sources={result.sources}
        coverage={result.coverage}
        fetchedAt={result.fetched_at}
        sourceUpdatedAt={result.source_updated_at}
        measuredAt={result.measured_at}
        limitations={result.limitations}
        absenceCaveat="Water-quality information is based on available public sample bulletins and does not represent every apartment or villa in this locality."
      />
    </>
  );
};

interface CrimeCardProps {
  result: ModuleResult<CrimeData> | null;
  isLoading: boolean;
  onLoadRequested?: () => void;
}

export const CrimeCard: React.FC<CrimeCardProps> = ({
  result,
  isLoading,
  onLoadRequested
}) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!result && !isLoading) {
    return (
      <div className="p-4 bg-white rounded-2xl border border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-purple-50 text-purple-700 rounded-xl">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-semibold text-xs text-slate-800">Crime Statistics Availability</h4>
            <p className="text-[11px] text-slate-500">National Crime Records Bureau (NCRB)</p>
          </div>
        </div>
        {onLoadRequested && (
          <button
            onClick={onLoadRequested}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition-colors"
          >
            Check Status
          </button>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 bg-white rounded-2xl border border-slate-200 animate-pulse space-y-2">
        <div className="h-4 bg-slate-200 rounded w-1/4"></div>
        <div className="h-6 bg-slate-100 rounded w-3/4"></div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <>
      <div className="p-5 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-purple-50 text-purple-700 rounded-xl">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-display font-bold text-sm text-navy-900">
                Crime Data Availability
              </h4>
              <p className="text-[11px] text-slate-500">
                Official police commissionerate statistics
              </p>
            </div>
          </div>

          <button
            onClick={() => setDrawerOpen(true)}
            className="text-[11px] font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1 bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-100"
          >
            <Info className="w-3 h-3" />
            <span>Why?</span>
          </button>
        </div>

        <StatusBadge
          status={result.status}
          provenanceKind={result.provenance_kind}
          size="sm"
        />

        <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-600 space-y-2">
          <p className="font-medium text-slate-800">
            Locality-level crime statistics are unavailable from integrated sources.
          </p>
          <div className="flex items-start gap-1.5 p-2 bg-amber-50 rounded-xl border border-amber-200/80 text-[11px] text-amber-900">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
            <p className="font-medium">
              Absence caveat: The absence of reported crime statistics does not imply an area is safe.
            </p>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Official NCRB statistics are compiled annually at the district or police commissionerate boundary and cannot be attributed to individual neighborhoods.
          </p>
        </div>

        <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
          <span>Physical police stations: Listed under Safety Infra</span>
          <span className="font-medium text-teal-700">Check local station</span>
        </div>
      </div>

      <DataSourceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Crime Statistics Limitations"
        status={result.status}
        provenanceKind={result.provenance_kind}
        sources={result.sources}
        coverage={result.coverage}
        fetchedAt={result.fetched_at}
        sourceUpdatedAt={result.source_updated_at}
        measuredAt={result.measured_at}
        limitations={result.limitations}
        absenceCaveat="Locality-level crime statistics are unavailable from integrated sources. The absence of data does not indicate security or safety."
      />
    </>
  );
};
