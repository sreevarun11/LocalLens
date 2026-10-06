import React, { useState } from 'react';
import { Layers, CheckCircle2, CircleDot, CircleSlash, AlertTriangle, HelpCircle } from 'lucide-react';
import { ModuleResult, StatusKind } from '../../types';

interface CoverageItem {
  id: string;
  label: string;
  status: StatusKind;
  depthText: string;
  sourceName: string;
  whyText: string;
}

interface DataCoveragePanelProps {
  placesResult?: ModuleResult<any> | null;
  envResult?: ModuleResult<any> | null;
  waterResult?: ModuleResult<any> | null;
  crimeResult?: ModuleResult<any> | null;
  className?: string;
}

export const DataCoveragePanel: React.FC<DataCoveragePanelProps> = ({
  placesResult,
  envResult,
  waterResult,
  crimeResult,
  className = ''
}) => {
  const [selectedWhy, setSelectedWhy] = useState<CoverageItem | null>(null);

  // Build items reflecting depth, not just presence
  const items: CoverageItem[] = [
    {
      id: 'places',
      label: 'Nearby Amenities',
      status: placesResult ? placesResult.status : 'unavailable',
      depthText: placesResult?.data?.places
        ? `${placesResult.data.places.length} listings within 1.5 km ${
            placesResult.coverage.result_cap_reached ? '(result limit reached — count is lower bound)' : '(complete within radius)'
          }`
        : 'Amenities not loaded',
      sourceName: placesResult?.sources[0]?.name || 'OpenStreetMap',
      whyText: 'POIs are queried live within a 1500m straight-line radius from OpenStreetMap or Google Places.'
    },
    {
      id: 'environment',
      label: 'Environment (Air)',
      status: envResult ? envResult.status : 'limited',
      depthText: envResult?.data
        ? `Modeled atmospheric reanalysis (~11 km grid)`
        : 'Modeled regional estimate',
      sourceName: envResult?.sources[0]?.name || 'Open-Meteo CAMS',
      whyText: 'Values represent European Copernicus atmospheric reanalysis. Ground monitoring station data is subject to sensor availability.'
    },
    {
      id: 'water',
      label: 'Water Quality',
      status: waterResult ? waterResult.status : 'unavailable',
      depthText: 'No integrated dataset for this locality',
      sourceName: 'CGWB / State Water Boards',
      whyText: 'Official water quality data is published periodically in static district reports rather than locality-level machine APIs.'
    },
    {
      id: 'crime',
      label: 'Crime Statistics',
      status: crimeResult ? crimeResult.status : 'unavailable',
      depthText: 'Locality-level statistics unavailable',
      sourceName: 'NCRB (National Crime Records Bureau)',
      whyText: 'Government crime records are aggregated annually by police commissionerate or district boundaries and cannot be reliably assigned to single neighborhoods.'
    }
  ];

  // Summary counts
  const counts = items.reduce(
    (acc, it) => {
      acc[it.status] = (acc[it.status] || 0) + 1;
      return acc;
    },
    { available: 0, limited: 0, unavailable: 0, error: 0 } as Record<StatusKind, number>
  );

  const getStatusIcon = (st: StatusKind) => {
    switch (st) {
      case 'available':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />;
      case 'limited':
        return <CircleDot className="w-3.5 h-3.5 text-amber-600 shrink-0" />;
      case 'unavailable':
        return <CircleSlash className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
      case 'error':
        return <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />;
    }
  };

  return (
    <div className={`p-5 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-teal-600" />
            <h3 className="font-display font-bold text-sm text-navy-900">
              Data Coverage & Depth Panel
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Transparent breakdown of dataset depth. Not a subjective quality score.
          </p>
        </div>

        <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md">
          Provenance
        </span>
      </div>

      {/* Summary Line */}
      <div className="flex flex-wrap items-center gap-2 text-xs font-medium p-2.5 bg-slate-50 rounded-2xl border border-slate-200/80">
        <span className="flex items-center gap-1 text-emerald-800">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          Available {counts.available}
        </span>
        <span className="text-slate-300">·</span>
        <span className="flex items-center gap-1 text-amber-800">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          Limited {counts.limited}
        </span>
        <span className="text-slate-300">·</span>
        <span className="flex items-center gap-1 text-slate-600">
          <span className="w-2 h-2 rounded-full bg-slate-400" />
          Unavailable {counts.unavailable}
        </span>
        <span className="text-slate-300">·</span>
        <span className="flex items-center gap-1 text-rose-800">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Error {counts.error}
        </span>
      </div>

      {/* Depth Rows */}
      <div className="divide-y divide-slate-100 text-xs">
        {items.map((item) => (
          <div
            key={item.id}
            className="py-2.5 flex items-center justify-between gap-3 group"
          >
            <div className="flex items-center gap-2 min-w-0">
              {getStatusIcon(item.status)}
              <span className="font-semibold text-slate-800 shrink-0">
                {item.label}:
              </span>
              <span className="text-slate-600 truncate">
                {item.depthText}
              </span>
            </div>

            <button
              onClick={() => setSelectedWhy(item)}
              className="text-[11px] font-medium text-teal-700 hover:text-teal-900 flex items-center gap-0.5 px-2 py-0.5 rounded hover:bg-teal-50 transition-colors shrink-0"
              title="Inspect coverage reasons"
            >
              <span>Why?</span>
              <HelpCircle className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Popover / Modal for "Why?" */}
      {selectedWhy && (
        <div className="p-3.5 bg-teal-50/70 border border-teal-200/80 rounded-2xl text-xs space-y-1 animate-in fade-in-50 duration-150">
          <div className="flex items-center justify-between text-teal-950 font-semibold">
            <span>Why is {selectedWhy.label} in this state?</span>
            <button
              onClick={() => setSelectedWhy(null)}
              className="text-teal-700 hover:text-teal-900 text-xs px-1"
            >
              ✕
            </button>
          </div>
          <p className="text-slate-700 leading-relaxed">
            {selectedWhy.whyText}
          </p>
          <p className="text-[10px] text-slate-500 font-mono mt-1">
            Provider: {selectedWhy.sourceName}
          </p>
        </div>
      )}
    </div>
  );
};
