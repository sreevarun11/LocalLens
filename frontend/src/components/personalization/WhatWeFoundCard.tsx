import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import { FindingItem } from '../../types';

interface WhatWeFoundCardProps {
  findings: FindingItem[];
  isLoading?: boolean;
}

export const WhatWeFoundCard: React.FC<WhatWeFoundCardProps> = ({
  findings,
  isLoading = false
}) => {
  const [activeEntityDrawerFinding, setActiveEntityDrawerFinding] = useState<FindingItem | null>(null);

  if (isLoading) {
    return (
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4 animate-pulse">
        <div className="h-5 bg-slate-200 rounded w-1/3"></div>
        <div className="space-y-3">
          <div className="h-14 bg-slate-100 rounded-2xl"></div>
          <div className="h-14 bg-slate-100 rounded-2xl"></div>
          <div className="h-14 bg-slate-100 rounded-2xl"></div>
        </div>
      </div>
    );
  }

  if (findings.length === 0) return null;

  return (
    <>
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <h3 className="font-display font-bold text-lg text-navy-900">
                What We Found For You
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic findings filtered strictly through your selected priorities and distance preferences.
            </p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 bg-teal-50 text-teal-800 border border-teal-200 rounded-full">
            Evidence-Grounded
          </span>
        </div>

        {/* Findings List */}
        <div className="space-y-3">
          {findings.map((item) => {
            const hasPref = item.within_preference !== undefined && item.within_preference !== null;
            return (
              <div
                key={item.id}
                className="p-4 rounded-2xl border border-slate-200/90 hover:border-slate-300 bg-slate-50/50 transition-all space-y-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-navy-900">
                        {item.headline}
                      </span>

                      {/* Distance Preference Pill */}
                      {hasPref && (
                        <span
                          className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-semibold border ${
                            item.within_preference === 'yes'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : item.within_preference === 'no'
                              ? 'bg-amber-50 text-amber-800 border-amber-200'
                              : 'bg-slate-100 text-slate-700 border-slate-300'
                          }`}
                        >
                          {item.within_preference === 'yes' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {item.within_preference === 'no' && <XCircle className="w-3 h-3 text-amber-600" />}
                          {item.within_preference === 'unknown' && <HelpCircle className="w-3 h-3 text-slate-500" />}
                          <span>
                            {item.within_preference === 'yes'
                              ? 'Within preference'
                              : item.within_preference === 'no'
                              ? 'Beyond preference'
                              : 'Unknown depth'}
                          </span>
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      {item.detail}
                    </p>

                    {item.preference_note && (
                      <p className="text-[11px] text-slate-500 italic mt-0.5">
                        {item.preference_note}
                      </p>
                    )}
                  </div>

                  {/* "Why?" Button to inspect entities */}
                  {item.entities && item.entities.length > 0 && (
                    <button
                      onClick={() => setActiveEntityDrawerFinding(item)}
                      className="text-xs font-semibold text-teal-700 hover:text-teal-900 bg-white border border-slate-200 px-2.5 py-1.5 rounded-xl shadow-2xs flex items-center gap-1 shrink-0 transition-colors"
                      title="Inspect underlying evidence entities"
                    >
                      <span>Why?</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* "Why?" Evidence Entities Drawer */}
      {activeEntityDrawerFinding && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <span className="text-xs font-semibold text-teal-700 uppercase tracking-wider">
                  Underlying Evidence Entities
                </span>
                <h3 className="font-display font-bold text-base text-navy-900 mt-0.5">
                  {activeEntityDrawerFinding.headline}
                </h3>
              </div>
              <button
                onClick={() => setActiveEntityDrawerFinding(null)}
                className="text-slate-400 hover:text-slate-700 text-sm px-2 py-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <p className="text-xs text-slate-500">
                Below are the physical listings retrieved for this priority. LocalLens derives all metric calculations directly from these authentic records without fabrication.
              </p>

              <div className="divide-y divide-slate-100 bg-white border border-slate-200 rounded-2xl overflow-hidden">
                {activeEntityDrawerFinding.entities?.map((ent, idx) => (
                  <div key={idx} className="p-3 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-800 block">
                        {ent.name}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        Listing #{idx + 1}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-teal-700 block">
                        {ent.distance_m}m
                      </span>
                      <span className="text-[10px] text-slate-400">straight-line</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-500 space-y-1">
                <span className="font-semibold text-slate-700 block">Licensing Notice:</span>
                <p>
                  Entity names and coordinates are retrieved for immediate user inspection and are never passed to third-party generative AI models.
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setActiveEntityDrawerFinding(null)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
