import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { CreditCard, CheckCircle2, ShieldCheck, Zap, AlertTriangle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

declare global {
  interface Window {
    Razorpay?: any;
  }
}

export const PaymentsPage: React.FC = () => {
  const { user, token, refreshCredits } = useAuth();
  const [credits, setCredits] = useState<{ credits_remaining: number; credits_used: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      loadCredits();
    }
  }, [token]);

  const loadCredits = async () => {
    try {
      setLoading(true);
      const data = await api.getCredits();
      setCredits(data);
    } catch (err: any) {
      console.warn('Could not load credits:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    if (!token) {
      setErrorMsg('Please sign in to purchase report credits.');
      return;
    }
    setPurchasing(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const order = await api.createPaymentOrder();

      if (order.is_free_allowance) {
        setSuccessMsg(`You have ${order.credits_remaining} free report credit(s) available in your allowance.`);
        await loadCredits();
        setPurchasing(false);
        return;
      }

      if (window.Razorpay && order.key_id && !order.key_id.includes('test_LocalLensDevKey')) {
        const options = {
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: 'LocalLens Neighborhood Intelligence',
          description: 'Single Locality Decision Report Credit',
          order_id: order.order_id,
          handler: async (response: any) => {
            try {
              await api.verifyPayment(
                response.razorpay_order_id,
                response.razorpay_payment_id,
                response.razorpay_signature
              );
              setSuccessMsg('Payment verified successfully! 1 report credit has been added to your balance.');
              await loadCredits();
              await refreshCredits();
            } catch (vErr: any) {
              setErrorMsg(vErr.message || 'Payment signature verification failed.');
            }
          },
          prefill: {
            name: user?.display_name || user?.username,
            email: user?.email
          },
          theme: {
            color: '#0d9488'
          }
        };
        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
  setErrorMsg(
    'Razorpay checkout is unavailable or payment configuration is incomplete. No payment was made. Please try again later.'
  );
  return;
}
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment request failed. Please try again.');
    } finally {
      setPurchasing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 text-teal-800 text-xs font-semibold mb-2">
            <CreditCard className="w-4 h-4 text-teal-600" />
            <span>Honest & Transparent Pricing</span>
          </div>
          <h1 className="font-display font-bold text-2xl text-navy-900">
            Report Credits & Payments
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Every registered user receives 3 free decision reports. Additional comprehensive dossiers are available at ₹29 per report with no hidden subscriptions.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 p-4 rounded-2xl">
          <Zap className="w-6 h-6 text-teal-600 fill-teal-600 shrink-0" />
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Available Balance</p>
            <p className="text-sm font-bold text-slate-900">
              {loading ? '...' : `${credits?.credits_remaining ?? 0} Report Credits`}
            </p>
            <p className="text-[10px] text-slate-500">{credits?.credits_used ?? 0} reports generated</p>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2.5 text-xs text-emerald-800 font-semibold animate-in fade-in duration-150">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-2.5 text-xs text-rose-800 font-semibold">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Tier 1: Free Allowance */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <span className="text-[11px] font-bold text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200 uppercase tracking-wider inline-block">
              Free Allowance
            </span>
            <h3 className="font-display font-bold text-lg text-navy-900">3 Free Decision Reports</h3>
            <div className="text-3xl font-display font-bold text-navy-900">
              ₹0 <span className="text-xs text-slate-400 font-normal">/ included on sign up</span>
            </div>
            <p className="text-xs text-slate-600">
              Every newly registered account automatically receives 3 full decision report credits with zero payment details required.
            </p>
            <ul className="text-xs text-slate-700 space-y-2 pt-2 border-t border-slate-100">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Full comprehensive PDF dossier</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>SHA-256 Public QR verification registry</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Real spatial, weather, groundwater, and safety data</span>
              </li>
            </ul>
          </div>

          <Link
            to="/reports/create"
            className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold transition-colors text-center block"
          >
            Create Report Now
          </Link>
        </div>

        {/* Tier 2: Single Report Purchase */}
        <div className="bg-white p-6 rounded-3xl border-2 border-teal-500 shadow-xs flex flex-col justify-between space-y-4 relative">
          <div className="absolute top-4 right-4">
            <span className="text-[10px] font-bold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200 uppercase tracking-wider">
              Pay As You Go
            </span>
          </div>

          <div className="space-y-3">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider inline-block">
              Additional Report
            </span>
            <h3 className="font-display font-bold text-lg text-navy-900">Single Decision Report</h3>
            <div className="text-3xl font-display font-bold text-navy-900">
              ₹29 <span className="text-xs text-slate-400 font-normal">/ report credit (2,900 paise)</span>
            </div>
            <p className="text-xs text-slate-600">
              Purchase extra decision report credits whenever needed. Instant credit allocation, no monthly lock-in, and secured via Razorpay.
            </p>
            <ul className="text-xs text-slate-700 space-y-2 pt-2 border-t border-slate-100">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>1 Additional Decision Report credit</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Never expires once purchased</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>UPI, Debit/Credit Card, Netbanking accepted</span>
              </li>
            </ul>
          </div>

          <button
            type="button"
            onClick={handlePurchase}
            disabled={purchasing}
            className="w-full py-2.5 px-4 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition-colors shadow-xs flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            <span>{purchasing ? 'Initiating Order...' : 'Pay ₹29 & Add 1 Credit'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Security & Guarantee Banner */}
      <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex items-start gap-3 text-xs text-slate-600">
        <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <b>Payment Security Notice:</b> All payments are processed through Razorpay's PCI-DSS compliant gateway in test mode / secure environment with server-side HMAC-SHA256 signature verification. LocalLens never stores raw credit card numbers or UPI PINs.
        </p>
      </div>
    </div>
  );
};
