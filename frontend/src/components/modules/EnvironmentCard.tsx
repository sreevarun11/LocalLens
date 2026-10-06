import React, { useState } from 'react';
import { Wind, Info, AlertTriangle } from 'lucide-react';
import { ModuleResult, AirQualityData } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { DataSourceDrawer } from '../common/DataSourceDrawer';

interface EnvironmentCardProps {
  result: ModuleResult<AirQualityData> | null;
  isLoading: boolean;
  onLoadRequested?: () => void;
}

export const EnvironmentCard: React.FC<EnvironmentCardProps> = ({
  result,
  isLoading,
  onLoadRequested
}) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!result && !isLoading) {
    return (
      <div className="p-4 bg-white rounded-2xl border border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl">
            <Wind className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-semibold text-xs text-slate-800">Air Quality & Environment</h4>
            <p className="text-[11px] text-slate-500">Copernicus CAMS atmospheric model</p>
          </div>
        </div>
        {onLoadRequested && (
          <button
            onClick={onLoadRequested}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition-colors"
          >
            Load Data
          </button>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-5 bg-white rounded-2xl border border-slate-200 animate-pulse space-y-3">
        <div className="h-4 bg-slate-200 rounded w-1/3"></div>
        <div className="h-8 bg-slate-100 rounded w-1/2"></div>
        <div className="grid grid-cols-3 gap-2">
          <div className="h-10 bg-slate-100 rounded"></div>
          <div className="h-10 bg-slate-100 rounded"></div>
          <div className="h-10 bg-slate-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const data = result.data;
  const isModeled = result.provenance_kind === 'modeled_estimate';

  const getAqiCategory = (aqi?: number | null) => {
    if (aqi === null || aqi === undefined) return { label: 'Unknown', color: 'text-slate-600 bg-slate-100' };
    if (aqi <= 50) return { label: 'Good', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (aqi <= 100) return { label: 'Moderate', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    if (aqi <= 150) return { label: 'Unhealthy for Sensitive Groups', color: 'text-orange-700 bg-orange-50 border-orange-200' };
    if (aqi <= 200) return { label: 'Unhealthy', color: 'text-rose-700 bg-rose-50 border-rose-200' };
    return { label: 'Very Unhealthy', color: 'text-purple-700 bg-purple-50 border-purple-200' };
  };

  const aqiCategory = getAqiCategory(data?.aqi);

  return (
    <>
      <div className="p-5 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-teal-50 text-teal-700 rounded-2xl">
              <Wind className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-display font-bold text-sm text-navy-900">
                Air Quality & Environment
              </h4>
              <p className="text-[11px] text-slate-500">
                {isModeled
                  ? 'Copernicus CAMS European atmospheric reanalysis'
                  : `Ground station: ${data?.station_name || 'Nearest station'}`}
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

        {/* Status & Provenance */}
        <div className="flex items-center justify-between">
          <StatusBadge
            status={result.status}
            provenanceKind={result.provenance_kind}
            size="sm"
          />
          {result.measured_at && (
            <span className="text-[10px] text-slate-400">
              Measured: {new Date(result.measured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        {/* Primary AQI Display */}
        {data && (
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 flex items-center justify-between">
            <div>
              <span className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold block">
                {data.aqi_scale}
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="font-display font-bold text-3xl text-navy-900">
                  {data.aqi ?? '—'}
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${aqiCategory.color}`}>
                  {aqiCategory.label}
                </span>
              </div>
            </div>

            {/* Micro Pollutants Grid */}
            <div className="flex items-center gap-3 text-right">
              {data.pm25 !== null && data.pm25 !== undefined && (
                <div className="px-2.5 py-1 bg-white rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-medium">PM2.5</span>
                  <span className="text-xs font-bold text-slate-800">
                    {data.pm25} <span className="text-[9px] font-normal text-slate-500">µg/m³</span>
                  </span>
                </div>
              )}
              {data.pm10 !== null && data.pm10 !== undefined && (
                <div className="px-2.5 py-1 bg-white rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-medium">PM10</span>
                  <span className="text-xs font-bold text-slate-800">
                    {data.pm10} <span className="text-[9px] font-normal text-slate-500">µg/m³</span>
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mandatory Limitations Disclosure */}
        <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200/60 text-[11px] text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-amber-800">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>{isModeled ? 'Modeled estimate — not a station measurement' : 'Station measurement disclosure'}</span>
          </div>
          <p className="leading-relaxed">
            {isModeled
              ? 'Measurement is based on an 11 km regional atmospheric model grid. It may not represent conditions or microclimates at the exact property.'
              : `Station is ${data?.station_distance_m ? `${(data.station_distance_m / 1000).toFixed(1)} km away` : 'at a distance'}. Microclimates may vary.`}
          </p>
        </div>
      </div>

      <DataSourceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Air Quality & Atmosphere"
        status={result.status}
        provenanceKind={result.provenance_kind}
        sources={result.sources}
        coverage={result.coverage}
        fetchedAt={result.fetched_at}
        sourceUpdatedAt={result.source_updated_at}
        measuredAt={result.measured_at}
        limitations={result.limitations}
        absenceCaveat="Local ambient air quality varies depending on surrounding road traffic, building density, wind patterns, and season."
      />
    </>
  );
};
