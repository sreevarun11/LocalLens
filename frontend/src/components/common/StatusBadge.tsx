import React from 'react';
import { CheckCircle2, CircleDot, CircleSlash, AlertTriangle } from 'lucide-react';
import { StatusKind, ProvenanceKind } from '../../types';

interface StatusBadgeProps {
  status: StatusKind;
  provenanceKind?: ProvenanceKind;
  distanceNote?: string | null;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  provenanceKind,
  distanceNote,
  className = '',
  size = 'md'
}) => {
  const getStatusConfig = (st: StatusKind) => {
    switch (st) {
      case 'available':
        return {
          icon: CheckCircle2,
          text: 'Data available',
          bg: 'bg-emerald-50',
          border: 'border-emerald-200',
          textCol: 'text-emerald-800',
          iconCol: 'text-emerald-600',
        };
      case 'limited':
        return {
          icon: CircleDot,
          text: 'Limited data',
          bg: 'bg-amber-50',
          border: 'border-amber-200',
          textCol: 'text-amber-800',
          iconCol: 'text-amber-600',
        };
      case 'unavailable':
        return {
          icon: CircleSlash,
          text: 'No data found',
          bg: 'bg-slate-100',
          border: 'border-slate-300',
          textCol: 'text-slate-700',
          iconCol: 'text-slate-500',
        };
      case 'error':
        return {
          icon: AlertTriangle,
          text: 'Temporarily unavailable',
          bg: 'bg-rose-50',
          border: 'border-rose-200',
          textCol: 'text-rose-800',
          iconCol: 'text-rose-600',
        };
    }
  };

  const getProvenanceLabel = (prov?: ProvenanceKind) => {
    if (!prov) return null;
    switch (prov) {
      case 'station_measurement':
        return 'Station measurement';
      case 'official_dataset':
        return 'Official dataset';
      case 'map_listing':
        return 'Map listing';
      case 'modeled_estimate':
        return 'Modeled estimate';
      case 'user_provided':
        return 'User provided';
      case 'derived':
        return 'Derived';
      default:
        return prov;
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;
  const provLabel = getProvenanceLabel(provenanceKind);

  const isSmall = size === 'sm';

  return (
    <div className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      {/* Primary Status: Icon + Text + Color */}
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${config.bg} ${config.border} ${config.textCol} ${
          isSmall ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
        }`}
        title={`Status: ${config.text}`}
      >
        <Icon className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} ${config.iconCol}`} />
        <span>{config.text}</span>
      </span>

      {/* Provenance Tag */}
      {provLabel && (
        <span
          className={`inline-flex items-center text-slate-600 bg-white border border-slate-200 rounded-full font-normal ${
            isSmall ? 'px-2 py-0.5 text-[11px]' : 'px-2 py-0.5 text-xs'
          }`}
          title="Data provenance kind"
        >
          {provLabel}
        </span>
      )}

      {/* Distance / Extra note */}
      {distanceNote && (
        <span
          className={`text-slate-500 bg-slate-50 border border-slate-200 rounded-full font-normal ${
            isSmall ? 'px-2 py-0.5 text-[11px]' : 'px-2 py-0.5 text-xs'
          }`}
        >
          {distanceNote}
        </span>
      )}
    </div>
  );
};
