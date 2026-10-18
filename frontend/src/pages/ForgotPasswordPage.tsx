import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { KeyRound, ShieldCheck, ArrowLeft, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';

export const ForgotPasswordPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !recoveryCode.trim() || !newPassword) return;

    if (newPassword.length < 10) {
      setError('New password must be at least 10 characters long.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const res = await api.recoverPassword(username.trim(), recoveryCode.trim(), newPassword);
      setMessage(res.message || 'Password reset successfully. You can now sign in with your new password.');
    } catch (err: any) {
      setError(err.message || 'Password recovery failed. Please verify your username and recovery code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-teal-50 border border-teal-200 text-teal-600 mx-auto flex items-center justify-center">
          <KeyRound className="w-6 h-6" />
        </div>
        <h2 className="font-display text-2xl font-bold text-navy-900">
          Account Password Recovery
        </h2>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Use one of your 10 single-use recovery codes generated at registration to reset your account password.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-3xl border border-slate-200 shadow-xs space-y-5">
          {message ? (
            <div className="text-center space-y-4 py-2">
              <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center mx-auto text-emerald-600">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-base text-navy-900">Password Reset Complete</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {message}
              </p>
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors shadow-xs"
              >
                <span>Sign in with New Password</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-2xl text-[11px] text-amber-950 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  Each recovery code can only be used once. Resetting your password immediately revokes all currently active sessions.
                </span>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Account Username
                </label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. sreecharan"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Single-Use Recovery Code
                </label>
                <input
                  type="text"
                  required
                  value={recoveryCode}
                  onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
                  placeholder="e.g. LL-8B2F-9A1C"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10 font-mono tracking-wider"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  required
                  minLength={10}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 10 characters"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition-colors cursor-pointer shadow-xs disabled:opacity-50"
              >
                {isSubmitting ? 'Resetting Password...' : 'Reset Password with Recovery Code'}
              </button>

              <div className="text-center pt-2">
                <Link
                  to="/login"
                  className="text-xs font-semibold text-teal-700 hover:underline inline-flex items-center gap-1"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Sign In</span>
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
