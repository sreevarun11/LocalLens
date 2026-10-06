import React from 'react';
import { Link } from 'react-router-dom';
import { Compass, Home, MapPinOff } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 py-16 space-y-6">
      <div className="w-16 h-16 bg-slate-100 border border-slate-200 rounded-3xl flex items-center justify-center text-slate-500 shadow-xs">
        <MapPinOff className="w-8 h-8 text-teal-600" />
      </div>

      <div className="space-y-2 max-w-md">
        <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
          404 Error
        </span>
        <h1 className="font-display font-bold text-2xl sm:text-3xl text-navy-900">
          Looks like this place doesn't exist.
        </h1>
        <p className="text-xs sm:text-sm text-slate-600">
          We couldn't locate the page you're searching for. Return to the home page or start exploring a verified locality.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 shadow-2xs transition-colors"
        >
          <Home className="w-4 h-4 text-slate-500" />
          <span>Go Home</span>
        </Link>
        <Link
          to="/explore"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 shadow-2xs transition-colors"
        >
          <Compass className="w-4 h-4" />
          <span>Explore an Area</span>
        </Link>
      </div>
    </div>
  );
};
