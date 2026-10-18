import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Compass,
  Scale,
  Database,
  HelpCircle,
  ShieldCheck,
  Zap,
  Bookmark,
  History,
  LayoutDashboard,
  LogOut,
  AlertTriangle,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, credits, isAuthenticated, isEmailVerified, logout, verifyEmailSimulate } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const navLinks = [
    { to: '/explore', label: 'Explore', icon: Compass },
    { to: '/compare', label: 'Compare', icon: Scale },
    { to: '/data-sources', label: 'Data Sources', icon: Database },
    { to: '/how-it-works', label: 'How It Works', icon: HelpCircle },
  ];

  const handleSimulateVerify = async () => {
    setIsVerifying(true);
    try {
      await verifyEmailSimulate();
    } catch (e) {
      console.error(e);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <>
      {/* Email Verification Warning Banner (Section 11) */}
      {isAuthenticated && !isEmailVerified && (
        <div className="bg-amber-500 text-amber-950 px-4 py-2 text-xs font-medium flex items-center justify-between border-b border-amber-600/20">
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-950 shrink-0" />
              <span>
                Please verify your email address to generate your decision report. (3 free credits awarded upon verification)
              </span>
            </div>
            <button
              onClick={handleSimulateVerify}
              disabled={isVerifying}
              className="px-3 py-1 bg-amber-950 text-white rounded-lg text-[11px] font-semibold hover:bg-black transition-colors whitespace-nowrap"
            >
              {isVerifying ? 'Verifying...' : 'Verify Email Now'}
            </button>
          </div>
        </div>
      )}

      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo & Brand */}
            <Link to="/" className="flex items-center gap-3 group">
              <img
                src="/logo.png"
                alt="LocalLens Logo"
                className="h-9 w-auto object-contain transition-transform group-hover:scale-105"
              />
              <div className="flex flex-col">
                <span className="font-display font-bold text-xl text-navy-900 tracking-tight leading-none">
                  Local<span className="text-teal-600">Lens</span>
                </span>
                <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase mt-0.5">
                  Evidence-Grounded Intelligence
                </span>
              </div>
            </Link>

            {/* Navigation links */}
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = location.pathname.startsWith(link.to);
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-teal-50 text-teal-700 font-semibold'
                        : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                    {link.label}
                  </Link>
                );
              })}
            </nav>

            {/* User Account / Action CTAs */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  {/* Credits Badge */}
                  <Link
                    to="/dashboard"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-50 border border-teal-200/60 text-teal-800 text-xs font-semibold hover:bg-teal-100 transition-colors"
                    title="Report Credits remaining"
                  >
                    <Zap className="w-3.5 h-3.5 text-teal-600 fill-teal-600" />
                    <span>{credits?.credits_remaining ?? 0} Credits</span>
                  </Link>

                  {/* User Profile Dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => setDropdownOpen(!dropdownOpen)}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors text-xs font-medium text-slate-700"
                    >
                      <div className="w-6 h-6 rounded-full bg-navy-900 text-white flex items-center justify-center font-bold text-[10px]">
                        {user?.display_name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <span className="max-w-[100px] truncate">{user?.display_name}</span>
                      <ChevronDown className="w-3 h-3 text-slate-400" />
                    </button>

                    {dropdownOpen && (
                      <div
                        className="absolute right-0 mt-2 w-48 bg-white rounded-2xl border border-slate-200 shadow-xl py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100"
                        onMouseLeave={() => setDropdownOpen(false)}
                      >
                        <div className="px-3 py-2 border-b border-slate-100">
                          <p className="text-xs font-bold text-slate-900 truncate">{user?.display_name}</p>
                          <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                        </div>

                        <Link
                          to="/dashboard"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <LayoutDashboard className="w-4 h-4 text-slate-400" />
                          <span>Dashboard</span>
                        </Link>

                        <Link
                          to="/saved"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <Bookmark className="w-4 h-4 text-slate-400" />
                          <span>Saved Locations</span>
                        </Link>

                        <Link
                          to="/history"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <History className="w-4 h-4 text-slate-400" />
                          <span>Search History</span>
                        </Link>

                        <Link
                          to="/reports"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <ShieldCheck className="w-4 h-4 text-slate-400" />
                          <span>My Reports</span>
                        </Link>

                        <Link
                          to="/profile"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <LayoutDashboard className="w-4 h-4 text-slate-400" />
                          <span>Profile & Preferences</span>
                        </Link>

                        <Link
                          to="/payments"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <Zap className="w-4 h-4 text-slate-400" />
                          <span>Plans & Credits</span>
                        </Link>

                        {user?.is_admin && (
                          <Link
                            to="/admin"
                            onClick={() => setDropdownOpen(false)}
                            className="flex items-center gap-2 px-3 py-2 text-xs text-amber-700 bg-amber-50/60 hover:bg-amber-50 font-medium transition-colors"
                          >
                            <ShieldCheck className="w-4 h-4 text-amber-600" />
                            <span>Admin Console</span>
                          </Link>
                        )}

                        <div className="border-t border-slate-100 mt-1 pt-1">
                          <button
                            onClick={() => {
                              setDropdownOpen(false);
                              logout();
                              navigate('/');
                            }}
                            className="flex items-center gap-2 w-full px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors"
                          >
                            <LogOut className="w-4 h-4" />
                            <span>Sign Out</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <Link
                    to="/login"
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:text-navy-900 hover:bg-slate-100 transition-colors"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/register"
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-navy-900 hover:bg-navy-800 transition-colors shadow-xs"
                  >
                    Get Started
                  </Link>
                </div>
              )}

              <Link
                to="/reports/create"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>Create Report</span>
              </Link>
            </div>
          </div>
        </div>
      </header>
    </>
  );
};
