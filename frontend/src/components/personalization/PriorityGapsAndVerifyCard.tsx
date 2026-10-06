import React from 'react';
import { AlertCircle, CheckSquare } from 'lucide-react';
import { PriorityGapCallout, VerifyOnSiteQuestion } from '../../types';

interface PriorityGapsAndVerifyCardProps {
  callouts: PriorityGapCallout[];
  verifyQuestions: VerifyOnSiteQuestion[];
}

export const PriorityGapsAndVerifyCard: React.FC<PriorityGapsAndVerifyCardProps> = ({
  callouts,
  verifyQuestions
}) => {
  if (callouts.length === 0 && verifyQuestions.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Priority Gaps Callout */}
      {callouts.length > 0 && (
        <div className="p-5 bg-amber-50/70 rounded-3xl border border-amber-200/80 space-y-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-700" />
            <h4 className="font-display font-bold text-sm text-amber-950">
              Priority-Data Gap Callouts
            </h4>
          </div>
          <div className="space-y-2.5">
            {callouts.map((gap, idx) => (
              <div
                key={idx}
                className="p-3 bg-white/90 rounded-2xl border border-amber-200/60 text-xs space-y-1"
              >
                <div className="flex items-center justify-between text-amber-900 font-semibold">
                  <span className="capitalize">{gap.priority.replace('_', ' ')}: {gap.gap_description}</span>
                  <span className="text-[10px] text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">Gap Identified</span>
                </div>
                <p className="text-slate-600">
                  <strong className="text-slate-700">Available:</strong> {gap.available_facts}
                </p>
                <p className="text-slate-600">
                  <strong className="text-slate-700">Missing / Limited:</strong> {gap.missing_data}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verify On Site Checklist (Section 8.1) */}
      {verifyQuestions.length > 0 && (
        <div className="p-5 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-teal-600" />
              <h4 className="font-display font-bold text-sm text-navy-900">
                Verify On Site Checklist
              </h4>
            </div>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md">
              Suggested questions, not findings
            </span>
          </div>

          <p className="text-xs text-slate-500">
            Because online databases cannot confirm ground reality (like water timing, admission availability, or night security), ask these verified questions during your property visit:
          </p>

          <div className="space-y-2.5">
            {verifyQuestions.map((q) => (
              <div
                key={q.id}
                className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs space-y-1"
              >
                <div className="flex items-start gap-2">
                  <div className="w-4 h-4 rounded-full border border-teal-500 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">
                      {q.question}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Context: {q.context}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
