import React from 'react';
import { X, ExternalLink, Info, AlertCircle, Clock, ShieldCheck, Layers } from 'lucide-react';
import { DataSourceInfo, Coverage, StatusKind, ProvenanceKind } from '../../types';
import { StatusBadge } from './StatusBadge';

interface DataSourceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  moduleName?: string;
  status: StatusKind;
  provenanceKind: ProvenanceKind;
  sources: DataSourceInfo[];
  coverage: Coverage;
  fetchedAt: string;
  sourceUpdatedAt?: string | null;
  measuredAt?: string | null;
  limitations: string[];
  absenceCaveat?: string | null;
}

export const DataSourceDrawer: React.FC<DataSourceDrawerProps> = ({
  isOpen,
  onClose,
  title,
  status,
  provenanceKind,
  sources,
  coverage,
  fetchedAt,
  sourceUpdatedAt,
  measuredAt,
  limitations,
  absenceCaveat
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end transition-opacity">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <span className="text-xs font-semibold text-teal-700 uppercase tracking-wider">
              Data Provenance & Coverage
            </span>
            <h3 className="font-display font-bold text-lg text-navy-900 mt-0.5">
              {title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
            aria-label="Close drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Status & Provenance */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Integration Status
            </h4>
            <StatusBadge
              status={status}
              provenanceKind={provenanceKind}
              size="md"
            />
          </div>

          {/* Granularity & Coverage */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center gap-2 text-slate-700 font-medium text-sm">
              <Layers className="w-4 h-4 text-teal-600" />
              <span>Coverage & Granularity</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500 block">Granularity:</span>
                <span className="font-semibold text-slate-800 capitalize">
                  {coverage.granularity.replace('_', ' ')}
                </span>
              </div>
              {coverage.radius_m && (
                <div>
                  <span className="text-slate-500 block">Search Radius:</span>
                  <span className="font-semibold text-slate-800">
                    {coverage.radius_m} meters
                  </span>
                </div>
              )}
              {coverage.result_count !== undefined && coverage.result_count !== null && (
                <div>
                  <span className="text-slate-500 block">Results Found:</span>
                  <span className="font-semibold text-slate-800">
                    {coverage.result_cap_reached
                      ? `≥ ${coverage.result_count} (Cap Reached)`
                      : coverage.result_count}
                  </span>
                </div>
              )}
              {coverage.nearest_distance_m !== undefined && coverage.nearest_distance_m !== null && (
                <div>
                  <span className="text-slate-500 block">Nearest Facility:</span>
                  <span className="font-semibold text-slate-800">
                    {coverage.nearest_distance_m}m straight-line
                  </span>
                </div>
              )}
            </div>
            {coverage.note && (
              <p className="text-xs text-slate-600 border-t border-slate-200/80 pt-2 italic">
                {coverage.note}
              </p>
            )}
          </div>

          {/* Timestamps */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Timestamps & Freshness</span>
            </h4>
            <div className="text-xs space-y-1.5 bg-white p-3 rounded-lg border border-slate-200">
              <div className="flex justify-between">
                <span className="text-slate-500">Retrieved by LocalLens:</span>
                <span className="font-medium text-slate-800">
                  {new Date(fetchedAt).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Source Updated:</span>
                <span className="font-medium text-slate-800">
                  {sourceUpdatedAt
                    ? new Date(sourceUpdatedAt).toLocaleDateString()
                    : 'Update information not provided by source'}
                </span>
              </div>
              {measuredAt && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Measured At:</span>
                  <span className="font-medium text-slate-800">
                    {new Date(measuredAt).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Sources & Licensing */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Integrated Sources & License</span>
            </h4>
            {sources.map((src, idx) => (
              <div key={idx} className="p-3 bg-white border border-slate-200 rounded-lg text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900">{src.name}</span>
                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-600 hover:text-teal-700 flex items-center gap-1"
                    >
                      <span>Terms</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
                {src.license && (
                  <p className="text-slate-500">License: <span className="font-medium text-slate-700">{src.license}</span></p>
                )}
                {src.attribution && (
                  <p className="text-slate-500 text-[11px] mt-1 italic">{src.attribution}</p>
                )}
              </div>
            ))}
          </div>

          {/* Limitations */}
          {limitations && limitations.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>Known Limitations</span>
              </h4>
              <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
                {limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Absence Semantics Note */}
          {absenceCaveat && (
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                <Info className="w-3.5 h-3.5 text-slate-500" />
                <span>Absence Semantics</span>
              </div>
              <p>{absenceCaveat}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-lg text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
