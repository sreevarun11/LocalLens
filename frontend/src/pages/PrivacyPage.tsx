import React from 'react';
import { Shield } from 'lucide-react';

export const PrivacyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      <div className="space-y-2 border-b border-slate-200 pb-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <Shield className="w-3.5 h-3.5 text-teal-600" />
          <span>Legal & Data Governance</span>
        </div>
        <h1 className="font-display font-bold text-3xl text-navy-900">
          Privacy Policy
        </h1>
        <p className="text-xs text-slate-500">
          Last Updated: October 2026 · LocalLens Engineering Platform
        </p>
      </div>

      <div className="prose prose-slate prose-sm max-w-none text-xs text-slate-700 space-y-6 leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">1. Information We Collect</h2>
          <p>
            LocalLens is designed with privacy-by-design principles. We collect only the information strictly necessary to provide neighborhood intelligence reports:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Account Data:</strong> Email address and encrypted password credentials (via secure PBKDF2 with unique salts).</li>
            <li><strong>Exploration Preferences:</strong> Saved locality bookmarks, recent search history, and user-specified household profiles.</li>
            <li><strong>User Context:</strong> Optional user-supplied property attributes provided during report creation.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">2. How We Use Your Data</h2>
          <p>
            Your information is used strictly to compute personalized neighborhood evidence summaries and generate permanent PDF decision reports. We do not sell, rent, or monetize your search history or personal data to real estate brokers or advertisers.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">3. Public Report Verification Protection</h2>
          <p>
            When a report is verified publicly via its QR code or verification link, our systems strictly omit all user PII (including requester email, name, account ID, and private property notes). Only public cryptographic hashes and geographic evidence metadata are exposed.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">4. Third-Party Geospatial Providers</h2>
          <p>
            When querying map layers, requests are routed to OpenStreetMap (ODbL) and Open-Meteo in accordance with their respective privacy and attribution guidelines. Proprietary commercial data is not persistently stored.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">5. Contact Data Protection Officer</h2>
          <p>
            For data deletion inquiries or requests, contact our privacy desk at <code>privacy@locallens.app</code>.
          </p>
        </section>
      </div>
    </div>
  );
};
