import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/common/Navbar';

// Core Pages
import { LandingPage } from './pages/LandingPage';
import { ExplorePage } from './pages/ExplorePage';
import { ComparePage } from './pages/ComparePage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { HowItWorksPage } from './pages/HowItWorksPage';

// Reports
import { ReportBuilderPage } from './pages/ReportBuilderPage';
import { ReportsListPage } from './pages/ReportsListPage';
import { ReportDetailPage } from './pages/ReportDetailPage';
import { PublicVerificationPage } from './pages/PublicVerificationPage';

// Auth & Account
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { SavedLocationsPage } from './pages/SavedLocationsPage';
import { SearchHistoryPage } from './pages/SearchHistoryPage';
import { ProfilePage } from './pages/ProfilePage';
import { PaymentsPage } from './pages/PaymentsPage';

// Admin / Diagnostics
import { AdminPage } from './pages/AdminPage';

// Legal & Info
import { AboutPage } from './pages/AboutPage';
import { ContactPage } from './pages/ContactPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { TermsPage } from './pages/TermsPage';
import { CookiePolicyPage } from './pages/CookiePolicyPage';

// Fallback
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <div className="min-h-screen flex flex-col bg-slate-50 font-sans text-slate-800">
        <Navbar />

        <main className="flex-1">
          <Routes>
            {/* Core Exploration & Intelligence */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/data-sources" element={<DataSourcesPage />} />
            <Route path="/how-it-works" element={<HowItWorksPage />} />

            {/* Reports & Verification */}
            <Route path="/reports" element={<ReportsListPage />} />
            <Route path="/reports/create" element={<ReportBuilderPage />} />
            <Route path="/reports/:reportId" element={<ReportDetailPage />} />
            <Route path="/verify/:reportId" element={<PublicVerificationPage />} />

            {/* Account & Auth */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/saved" element={<SavedLocationsPage />} />
            <Route path="/history" element={<SearchHistoryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/payments" element={<PaymentsPage />} />

            {/* Administration / System Diagnostics */}
            <Route path="/admin" element={<AdminPage />} />

            {/* Legal, Support & Transparency */}
            <Route path="/about" element={<AboutPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/cookie-policy" element={<CookiePolicyPage />} />

            {/* 404 Fallback */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>

        {/* Global Footer */}
        <footer className="bg-white border-t border-slate-200 mt-16 py-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <img src="/logo.png" alt="LocalLens" className="h-6 w-auto" />
                <div>
                  <span className="font-bold text-slate-800 text-sm">LocalLens v4.0</span>
                  <p className="text-xs text-slate-500">Evidence-grounded neighborhood intelligence & verifiable dossiers.</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-600">
                <Link to="/explore" className="hover:text-teal-700">Explore</Link>
                <Link to="/compare" className="hover:text-teal-700">Compare</Link>
                <Link to="/reports" className="hover:text-teal-700">Reports</Link>
                <Link to="/payments" className="hover:text-teal-700">Plans & Credits</Link>
                <Link to="/data-sources" className="hover:text-teal-700">Data Sources</Link>
                <Link to="/how-it-works" className="hover:text-teal-700">How It Works</Link>
                <Link to="/admin" className="hover:text-teal-700">Admin</Link>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
              <div className="space-y-0.5 text-center sm:text-left">
                <p className="font-medium text-slate-700">Created with purpose by Maheshwaram Sree Varun</p>
                <p className="text-slate-400">© 2026 LocalLens. All rights reserved.</p>
              </div>

              <div className="flex items-center gap-4 text-slate-400">
                <Link to="/about" className="hover:text-slate-600">About</Link>
                <Link to="/contact" className="hover:text-slate-600">Contact</Link>
                <Link to="/privacy" className="hover:text-slate-600">Privacy Policy</Link>
                <Link to="/terms" className="hover:text-slate-600">Terms of Service</Link>
                <Link to="/cookie-policy" className="hover:text-slate-600">Cookie Policy</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </AuthProvider>
  );
};

export default App;
