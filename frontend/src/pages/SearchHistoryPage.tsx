import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { History, Trash2, ArrowRight, MapPin, Compass } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const SearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [history, setHistory] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isAuthenticated) {
      loadHistory();
    }
  }, [isAuthenticated, authLoading, navigate]);

  const loadHistory = () => {
    setIsLoading(true);
    api.getSearchHistory()
      .then((data) => setHistory(data || []))
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  };

  const handleClearHistory = async () => {
    if (!confirm('Clear all your search history?')) return;
    try {
      await api.clearSearchHistory();
      setHistory([]);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-900 flex items-center gap-2.5">
            <History className="w-6 h-6 text-teal-600" />
            <span>Search History</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Review past neighborhood queries and quickly resume exploration.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1.5 px-3.5 py-2 text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-xl text-xs font-semibold transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear History</span>
            </button>
          )}

          <Link
            to="/explore"
            className="flex items-center gap-2 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors"
          >
            <Compass className="w-4 h-4" />
            <span>New Search</span>
          </Link>
        </div>
      </div>

      {/* History List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-slate-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : history.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <History className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="font-display font-semibold text-slate-800 text-base">
            No recent searches yet.
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Your recent locality searches will automatically be listed here for quick re-exploration.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-xs divide-y divide-slate-100 overflow-hidden">
          {history.map((item) => (
            <div
              key={item.id}
              className="p-4 hover:bg-slate-50/80 transition-colors flex items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 bg-slate-100 text-slate-600 rounded-xl mt-0.5">
                  <MapPin className="w-4 h-4 text-teal-600" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-navy-900">{item.locality_name}</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Searched on {new Date(item.searched_at).toLocaleString()} · Resolved via {item.provider}
                  </p>
                </div>
              </div>

              <Link
                to={`/explore?q=${encodeURIComponent(item.locality_name)}`}
                className="px-3.5 py-1.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:text-teal-700 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <span>Re-explore</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
