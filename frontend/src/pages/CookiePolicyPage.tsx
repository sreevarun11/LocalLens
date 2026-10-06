import React from 'react';
import { Cookie } from 'lucide-react';

export const CookiePolicyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      <div className="space-y-2 border-b border-slate-200 pb-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <Cookie className="w-3.5 h-3.5 text-teal-600" />
          <span>Transparency</span>
        </div>
        <h1 className="font-display font-bold text-3xl text-navy-900">
          Cookie Policy
        </h1>
        <p className="text-xs text-slate-500">
          Last Updated: October 2026 · LocalLens Engineering Platform
        </p>
      </div>

      <div className="prose prose-slate prose-sm max-w-none text-xs text-slate-700 space-y-6 leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">1. How We Use Cookies</h2>
          <p>
            LocalLens uses minimal local storage and essential session tokens strictly required for authentication state persistence and session management. We do not use third-party behavioral advertising cookies or cross-site tracking trackers.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">2. Essential Storage Keys</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li><code>locallens_token</code>: Cryptographic JWT token for authenticating API requests to your personal dashboard and report history.</li>
            <li><code>locallens_preferences</code>: Optional caching of default household profile and distance filters.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">3. Managing Local Storage</h2>
          <p>
            You can clear your local credentials at any time by clicking "Sign Out" or clearing your browser's application storage. Logging out immediately destroys the client-side session token.
          </p>
        </section>
      </div>
    </div>
  );
};
