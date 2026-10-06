import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { CreditCard, CheckCircle2, ShieldCheck, Zap, AlertTriangle, ArrowRight, RefreshCw, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export const PaymentsPage: React.FC = () => {
  const { token } = useAuth();
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

  const handlePurchase = async (packName: string, amount: number) => {
    if (!token) {
      setErrorMsg('Please sign in to purchase or add report credits.');
      return;
    }
    setPurchasing(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await api.addCredits(amount, 'simulation');
      if (res && res.credits) {
        setCredits(res.credits);
      } else {
        await loadCredits();
      }
      setSuccessMsg(`Successfully added ${amount} credit(s) from the "${packName}". Your account has been credited.`);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment simulation failed. Please try again.');
    } finally {
      setPurchasing(false);
    }
  };

  const tiers = [
    {
      name: 'Single Locality Audit',
      credits: 1,
      price: '₹99',
      unit: 'one-time',
      popular: false,
      features: [
        '1 Full Comprehensive Dossier',
        'Official Multi-Page PDF Download',
        'SHA-256 Public QR Verification',
        'Real Geospatial & Air Quality Snapshot',
        'Permanent Archive'
      ]
    },
    {
      name: 'House Hunter Pack',
      credits: 5,
      price: '₹299',
      unit: 'one-time',
      popular: true,
      features: [
        '5 Full Comprehensive Dossiers',
        'Side-by-side comparative matrices',
        'Official Multi-Page PDF Downloads',
        'SHA-256 Public QR Verification',
        'Priority Overpass & OpenAQ ground data',
        'Save ₹200 vs single audit'
      ]
    },
    {
      name: 'Relocation Enterprise',
      credits: 15,
      price: '₹749',
      unit: 'one-time',
      popular: false,
      features: [
        '15 Full Comprehensive Dossiers',
        'Multi-city cross comparisons',
        'Complete evidence provenance audit',
        'Official Multi-Page PDF Downloads',
        'Permanent public QR verification',
        'Direct developer API access support'
      ]
    }
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="text-center max-w-2xl mx-auto mb-12">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Locality Report Credits & Plans</h1>
        <p className="mt-3 text-base text-slate-600">
          Professional, multi-page neighborhood intelligence dossiers backed by verifiable geospatial evidence. Zero fabrication.
        </p>
      </div>

      {/* Credit Balance Card */}
      <div className="mb-10 bg-gradient-to-r from-teal-900 to-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-md">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-teal-300 font-semibold flex items-center gap-1.5">
              <Zap className="h-4 w-4" /> Account Balance
            </span>
            <div className="mt-2 flex items-baseline gap-3">
              <span className="text-4xl font-black">
                {token ? (loading ? '...' : (credits?.credits_remaining ?? 0)) : '0'}
              </span>
              <span className="text-slate-300 text-sm">report credits remaining</span>
            </div>
            {token && credits && (
              <p className="text-xs text-slate-400 mt-1">
                You have generated {credits.credits_used || 0} verified reports to date.
              </p>
            )}
            {!token && (
              <p className="text-xs text-slate-300 mt-2">
                Every newly registered account automatically receives <strong>3 free evaluation credits</strong>!
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            {token ? (
              <Link
                to="/reports/create"
                className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-900 font-semibold rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                <FileText className="h-4 w-4" /> Create New Report
              </Link>
            ) : (
              <Link
                to="/register"
                className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-900 font-semibold rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                Sign Up for 3 Free Credits <ArrowRight className="h-4 w-4" />
              </Link>
            )}
            <Link
              to="/reports"
              className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm font-medium transition-colors"
            >
              View My Reports
            </Link>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="mb-8 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="mb-8 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {tiers.map((tier) => (
          <div
            key={tier.name}
            className={`relative rounded-2xl bg-white p-6 shadow-sm border transition-all flex flex-col justify-between ${
              tier.popular
                ? 'border-teal-600 ring-2 ring-teal-600/30'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            {tier.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-teal-600 text-white text-[11px] font-bold uppercase tracking-wider rounded-full shadow">
                Recommended
              </span>
            )}

            <div>
              <h3 className="text-lg font-bold text-slate-800">{tier.name}</h3>
              <p className="text-xs text-slate-500 mt-1">{tier.credits} Full Locality Dossier{tier.credits > 1 ? 's' : ''}</p>

              <div className="my-6">
                <span className="text-3xl font-extrabold text-slate-900">{tier.price}</span>
                <span className="text-slate-500 text-xs ml-1.5">/ {tier.unit}</span>
              </div>

              <ul className="space-y-2.5 text-xs text-slate-600 mb-6">
                {tier.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={() => handlePurchase(tier.name, tier.credits)}
              disabled={purchasing}
              className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs transition-colors flex items-center justify-center gap-2 ${
                tier.popular
                  ? 'bg-teal-700 hover:bg-teal-800 text-white'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
              }`}
            >
              {purchasing ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Processing...
                </>
              ) : (
                <>
                  <CreditCard className="h-3.5 w-3.5" /> Purchase & Top-up
                </>
              )}
            </button>
          </div>
        ))}
      </div>

      {/* Guarantee & Verification banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-teal-700 shrink-0" />
          <div>
            <h4 className="font-semibold text-slate-800 text-sm">100% Cryptographic Verification Guarantee</h4>
            <p className="mt-0.5">Every PDF report comes with an immutable SHA-256 hash and public verification URL. Anyone scanning the QR code sees the exact frozen snapshot.</p>
          </div>
        </div>
        <div className="text-slate-400 shrink-0 text-center sm:text-right">
          <span>Prices in INR (₹)</span> &bull; <span>Instant credit activation</span>
        </div>
      </div>
    </div>
  );
};

export default PaymentsPage;
