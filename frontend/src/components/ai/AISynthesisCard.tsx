import React, { useState } from 'react';
import {
  Bot,
  RefreshCw,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { EvidenceItem } from '../../types';

interface AIStatement {
  text: string;
  kind: string;
  evidence_ids: string[];
}

interface AISection {
  priority: string;
  statements: AIStatement[];
}

export interface AISummaryData {
  headline: string;
  sections: AISection[];
  verify_on_site: Array<{ suggestion_id: string }>;
  mode: string;
  evidence_items?: EvidenceItem[];
}

interface AISynthesisCardProps {
  summary: AISummaryData | null;
  isLoading: boolean;
  onRefresh?: () => void;
  localityName: string;
}

export const AISynthesisCard: React.FC<AISynthesisCardProps> = ({
  summary,
  isLoading,
  onRefresh,
  localityName
}) => {
  const [selectedStatement, setSelectedStatement] = useState<AIStatement | null>(null);

  if (isLoading) {
    return (
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4 animate-pulse">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-slate-200 rounded-full" />
          <div className="h-4 bg-slate-200 rounded w-1/3" />
        </div>
        <div className="h-6 bg-slate-100 rounded w-3/4" />
        <div className="space-y-2">
          <div className="h-4 bg-slate-100 rounded w-full" />
          <div className="h-4 bg-slate-100 rounded w-5/6" />
        </div>
      </div>
    );
  }

  if (!summary) return null;

  const isAi = summary.mode === 'ai_grounded';

  const getKindBadge = (kind: string) => {
    switch (kind) {
      case 'interpretation':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-800 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
            Interpretation
          </span>
        );
      case 'gap':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
            Data Gap
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
            Observation
          </span>
        );
    }
  };

  return (
    <>
      <div className="p-6 bg-gradient-to-br from-white via-slate-50 to-teal-50/20 rounded-3xl border border-slate-200 shadow-xs space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-slate-200/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-navy-900 text-white rounded-2xl shadow-xs">
              <Bot className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display font-bold text-base text-navy-900">
                  Evidence-Grounded Synthesis
                </h3>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                    isAi
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-slate-100 text-slate-700 border-slate-300'
                  }`}
                >
                  {isAi ? '✓ Validated AI' : 'Deterministic Mode'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {isAi
                  ? 'LLM narrative verified against deterministic evidence by ClaimValidator'
                  : 'Automated synthesis generated directly from structured findings'}
              </p>
            </div>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 text-slate-400 hover:text-teal-700 hover:bg-white rounded-xl border border-transparent hover:border-slate-200 transition-all"
              title="Regenerate synthesis"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Headline */}
        <div className="p-3.5 bg-white rounded-2xl border border-teal-200/60 shadow-2xs">
          <span className="text-[10px] uppercase tracking-wider font-bold text-teal-700 block mb-1">
            Executive Summary · {localityName}
          </span>
          <p className="text-sm font-semibold text-slate-900 leading-snug">
            {summary.headline}
          </p>
        </div>

        {/* Priority-by-Priority Sections */}
        <div className="space-y-4">
          {summary.sections.map((sec, sIdx) => (
            <div key={sIdx} className="space-y-2">
              <span className="text-xs font-bold text-slate-600 uppercase tracking-wider block">
                {sec.priority.replace(/_/g, ' ')}
              </span>

              <div className="space-y-2">
                {sec.statements.map((stmt, stIdx) => (
                  <div
                    key={stIdx}
                    className="p-3.5 bg-white rounded-2xl border border-slate-200/90 text-xs space-y-1.5 hover:border-teal-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-slate-800 leading-relaxed font-normal flex-1">
                        {stmt.text}
                      </p>
                      {getKindBadge(stmt.kind)}
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px]">
                      <span className="text-slate-400 font-mono text-[10px]">
                        Ref: {stmt.evidence_ids.join(', ')}
                      </span>

                      <button
                        onClick={() => setSelectedStatement(stmt)}
                        className="text-teal-700 hover:text-teal-900 font-semibold flex items-center gap-0.5"
                      >
                        <span>Why?</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer Notice on Zero Fabrication */}
        <div className="p-3 bg-slate-100/70 rounded-2xl text-[11px] text-slate-500 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0" />
          <span>
            Every observation was verified against live external coordinates and station data before display.
          </span>
        </div>
      </div>

      {/* "Why?" Drawer for Specific Statement */}
      {selectedStatement && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <span className="text-xs font-semibold text-teal-700 uppercase tracking-wider">
                  Statement Verification
                </span>
                <h3 className="font-display font-bold text-sm text-navy-900 mt-0.5">
                  Evidence Citation
                </h3>
              </div>
              <button
                onClick={() => setSelectedStatement(null)}
                className="text-slate-400 hover:text-slate-700 text-sm px-2 py-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-800 space-y-1">
                <span className="font-bold text-slate-500 uppercase text-[10px]">Synthesized Statement:</span>
                <p className="italic">"{selectedStatement.text}"</p>
                <div className="pt-1">{getKindBadge(selectedStatement.kind)}</div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Referenced Evidence IDs:
                </h4>
                <div className="space-y-1.5">
                  {selectedStatement.evidence_ids.map((eid) => (
                    <div key={eid} className="p-2.5 bg-white border border-slate-200 rounded-xl text-xs flex items-center justify-between">
                      <span className="font-mono text-teal-800 text-[11px] truncate max-w-[240px]">
                        {eid}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full">
                        Audited
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-teal-50/50 rounded-xl border border-teal-200 text-xs text-slate-600 space-y-1">
                <span className="font-semibold text-teal-900">ClaimValidator Policy:</span>
                <p>
                  Any statement referencing non-existent evidence IDs or unverified numbers is rejected prior to render.
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedStatement(null)}
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
