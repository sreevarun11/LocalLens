import React, { useState } from 'react';
import { Star, MessageSquare, Check, X } from 'lucide-react';
import { api } from '../../services/api';

interface ReportFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId?: string;
  localityName?: string;
}

export const ReportFeedbackModal: React.FC<ReportFeedbackModalProps> = ({
  isOpen,
  onClose,
  reportId,
  localityName
}) => {
  const [rating, setRating] = useState<number>(5);
  const [willingToPay, setWillingToPay] = useState<string>('yes');
  const [comments, setComments] = useState<string>('');
  const [submitted, setSubmitted] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const description = `Rating: ${rating}/5 Stars | Willing to pay Rs 29: ${willingToPay} | Notes: ${comments.trim() || 'None'}`;
      await api.submitFeedback({
        report_id: reportId,
        locality_name: localityName,
        feedback_type: 'general',
        description
      });
      setSubmitted(true);
      setTimeout(() => {
        onClose();
        setSubmitted(false);
      }, 1800);
    } catch (err) {
      console.error(err);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-teal-50 text-teal-700 rounded-xl">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-display font-bold text-sm text-navy-900">Report Feedback</h3>
              <p className="text-[11px] text-slate-500">Help improve LocalLens evidence quality</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {submitted ? (
          <div className="py-8 text-center space-y-2">
            <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-5 h-5" />
            </div>
            <h4 className="font-display font-bold text-sm text-slate-900">Thank You!</h4>
            <p className="text-xs text-slate-500">Your feedback helps refine our evidence synthesis algorithms.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 1. Star Rating */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Was this decision report useful?
              </label>
              <div className="flex items-center gap-1.5">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className="p-1 transition-transform hover:scale-110 focus:outline-none"
                  >
                    <Star
                      className={`w-6 h-6 ${
                        star <= rating
                          ? 'text-amber-400 fill-amber-400'
                          : 'text-slate-200'
                      }`}
                    />
                  </button>
                ))}
                <span className="text-xs font-semibold text-slate-600 ml-2">
                  {rating} of 5
                </span>
              </div>
            </div>

            {/* 2. Willingness to Pay Rs 29 */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Would you pay ₹29 (approx 35¢) for a comprehensive report like this?
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: 'yes', label: 'Yes' },
                  { value: 'maybe', label: 'Maybe' },
                  { value: 'no', label: 'No' }
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setWillingToPay(opt.value)}
                    className={`py-2 px-3 text-xs font-semibold rounded-xl border transition-all ${
                      willingToPay === opt.value
                        ? 'bg-teal-50 border-teal-600 text-teal-800 shadow-2xs'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 3. Additional Comments */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Any specific data gaps or feedback? (Optional)
              </label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="e.g., Would love water tanker dependency data..."
                rows={2}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Skip
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-xl shadow-xs disabled:opacity-50"
              >
                {isLoading ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
