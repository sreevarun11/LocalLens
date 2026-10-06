import React from 'react';
import { FileText } from 'lucide-react';

export const TermsPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      <div className="space-y-2 border-b border-slate-200 pb-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <FileText className="w-3.5 h-3.5 text-teal-600" />
          <span>Terms of Service</span>
        </div>
        <h1 className="font-display font-bold text-3xl text-navy-900">
          Terms of Use & Disclaimer
        </h1>
        <p className="text-xs text-slate-500">
          Effective Date: October 2026 · LocalLens Engineering Platform
        </p>
      </div>

      <div className="prose prose-slate prose-sm max-w-none text-xs text-slate-700 space-y-6 leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">1. Nature of the Service</h2>
          <p>
            LocalLens is an independent information decision-support tool. It synthesizes open mapping datasets and atmospheric models. LocalLens is NOT a real estate brokerage, architectural inspector, legal advisor, or environmental certification authority.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">2. Mandatory Physical Inspection Caveat</h2>
          <p>
            Digital geospatial data cannot verify current operational status, structural safety, evening ambient lighting, physical water pressure, or neighborhood social atmosphere. Users must conduct in-person property and neighborhood inspections prior to signing leases, buying properties, or executing financial commitments.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">3. Absence of Data Disclosure</h2>
          <p>
            Missing records in open-source databases (such as OpenStreetMap or municipal archives) do NOT prove physical non-existence. Conversely, the absence of reported crime statistics does not guarantee personal or property safety.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">4. Intellectual Property & Report Usage</h2>
          <p>
            Generated PDF reports are intended for personal relocation evaluation. Commercial resale, scraping, or mass automated harvesting of report data without prior written authorization is strictly prohibited.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-bold text-navy-900">5. Limitation of Liability</h2>
          <p>
            In no event shall LocalLens or its contributors be liable for any direct, indirect, incidental, or consequential damages resulting from relocation or property purchase decisions made on the basis of retrieved evidence.
          </p>
        </section>
      </div>
    </div>
  );
};
