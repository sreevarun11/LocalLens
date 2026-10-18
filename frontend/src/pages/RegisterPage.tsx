import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus, AlertCircle, ArrowRight, ShieldCheck, Copy, Download, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Recovery codes modal/screen
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [hasCopied, setHasCopied] = useState(false);
  const [hasConfirmedSaved, setHasConfirmedSaved] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 10) {
      setError('Password must be at least 10 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      const codes = await register(username.trim(), password, displayName.trim() || undefined, email.trim() || undefined);
      if (codes && codes.length > 0) {
        setRecoveryCodes(codes);
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyCodes = () => {
    if (!recoveryCodes) return;
    const text = `LocalLens Account Recovery Codes for @${username.trim()}:\n\n` + recoveryCodes.join('\n') + '\n\nEach code can be used once to regain access if you forget your password.';
    navigator.clipboard.writeText(text);
    setHasCopied(true);
    setTimeout(() => setHasCopied(false), 2500);
  };

  const handleDownloadCodes = () => {
    if (!recoveryCodes) return;
    const text = `LocalLens Account Recovery Codes for @${username.trim()}\nGenerated: ${new Date().toISOString()}\n\n` +
      recoveryCodes.map((c, i) => `${i + 1}. ${c}`).join('\n') +
      '\n\nIMPORTANT: Each code is single-use. Store these codes securely. If you forget your password, these codes are the ONLY way to regain access to your account.';
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `LocalLens_Recovery_Codes_${username.trim()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (recoveryCodes && recoveryCodes.length > 0) {
    return (
      <div className="min-h-[80vh] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-3xl sm:px-10 space-y-6">
            <div className="text-center space-y-2">
              <div className="inline-flex p-3 bg-amber-50 text-amber-700 rounded-2xl mb-1">
                <ShieldCheck className="w-7 h-7" />
              </div>
              <h2 className="font-display text-2xl font-bold text-navy-900 tracking-tight">
                Save Your Recovery Codes
              </h2>
              <p className="text-xs text-slate-600 leading-relaxed max-w-md mx-auto">
                LocalLens uses secure cryptographic recovery codes. We do not use email reset links. <b>These 10 single-use codes are the only way to recover your account if you forget your password.</b>
              </p>
            </div>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl">
              <div className="grid grid-cols-2 gap-2 font-mono text-xs text-slate-800">
                {recoveryCodes.map((code, idx) => (
                  <div key={idx} className="p-2 bg-white border border-slate-200 rounded-xl text-center font-bold tracking-wider select-all">
                    {code}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCopyCodes}
                className="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                {hasCopied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-slate-600" />}
                <span>{hasCopied ? 'Copied to Clipboard!' : 'Copy All Codes'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadCodes}
                className="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Download className="w-4 h-4 text-slate-600" />
                <span>Download (.txt)</span>
              </button>
            </div>

            <div className="pt-2 border-t border-slate-100 space-y-4">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasConfirmedSaved}
                  onChange={(e) => setHasConfirmedSaved(e.target.checked)}
                  className="mt-0.5 rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="text-xs text-slate-600">
                  I have saved these 10 recovery codes in a secure password manager or physical note.
                </span>
              </label>

              <button
                type="button"
                disabled={!hasConfirmedSaved}
                onClick={() => navigate('/dashboard', { replace: true })}
                className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-navy-900 hover:bg-navy-800 transition-colors shadow-xs flex items-center justify-center gap-2 disabled:opacity-40 cursor-pointer"
              >
                <span>Continue to Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <div className="inline-flex p-3 bg-teal-50 text-teal-700 rounded-2xl mb-3">
            <UserPlus className="w-6 h-6" />
          </div>
          <h2 className="font-display text-2xl font-bold text-navy-900 tracking-tight">
            Create your account
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Sign up to receive 3 free verified decision report credits.
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-3xl sm:px-10 space-y-6">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="p-3 bg-teal-50/60 border border-teal-200/80 rounded-2xl flex items-start gap-2.5 text-xs text-teal-900">
            <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
            <span>
              Direct account creation with Argon2id cryptographic hashing. 3 free decision reports granted immediately upon sign up.
            </span>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Username <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                minLength={3}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. ganeshthedev"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Display Name (Optional)
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Ganesh The Dev (optional)"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@gmail.com (optional)"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                required
                minLength={10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 10 characters"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Minimum 10 characters required.</span>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-navy-900 hover:bg-navy-800 transition-colors shadow-xs flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              <span>{isLoading ? 'Creating account...' : 'Create Account'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="text-center pt-2 border-t border-slate-100 text-xs text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-teal-700 hover:underline">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
