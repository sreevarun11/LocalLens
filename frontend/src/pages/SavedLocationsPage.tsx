import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bookmark,
  Trash2,
  Edit2,
  Check,
  Compass,
  Scale,
  ArrowRight,
  MapPin
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const SavedLocationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [locations, setLocations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isAuthenticated) {
      loadSaved();
    }
  }, [isAuthenticated, authLoading, navigate]);

  const loadSaved = () => {
    setIsLoading(true);
    api.getSavedLocations()
      .then((data) => setLocations(data || []))
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Remove this locality from your saved list?')) return;
    try {
      await api.deleteSavedLocation(id);
      setLocations(locations.filter((l) => l.id !== id));
      setSelectedForCompare(selectedForCompare.filter((item) => item !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const startEdit = (item: any) => {
    setEditingId(item.id);
    setEditLabel(item.label || '');
    setEditNotes(item.notes || '');
  };

  const saveEdit = async (id: string) => {
    try {
      await api.updateSavedLocation(id, editLabel, editNotes);
      setLocations(locations.map((l) => (l.id === id ? { ...l, label: editLabel, notes: editNotes } : l)));
      setEditingId(null);
    } catch (e) {
      console.error(e);
    }
  };

  const toggleSelectForCompare = (id: string) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((i) => i !== id));
    } else {
      if (selectedForCompare.length >= 2) {
        setSelectedForCompare([selectedForCompare[1], id]);
      } else {
        setSelectedForCompare([...selectedForCompare, id]);
      }
    }
  };

  const handleLaunchCompare = () => {
    if (selectedForCompare.length !== 2) return;
    const loc1 = locations.find((l) => l.id === selectedForCompare[0]);
    const loc2 = locations.find((l) => l.id === selectedForCompare[1]);
    if (!loc1 || !loc2) return;
    navigate(`/compare?loc1=${encodeURIComponent(loc1.locality_name)}&loc2=${encodeURIComponent(loc2.locality_name)}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-900 flex items-center gap-2.5">
            <Bookmark className="w-6 h-6 text-teal-600" />
            <span>Saved Neighborhoods</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Track neighborhoods of interest, record private notes, and select two to compare side by side.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedForCompare.length === 2 && (
            <button
              onClick={handleLaunchCompare}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-semibold shadow-xs animate-in fade-in"
            >
              <Scale className="w-4 h-4" />
              <span>Compare Selected (2)</span>
            </button>
          )}

          <Link
            to="/explore"
            className="flex items-center gap-2 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors"
          >
            <Compass className="w-4 h-4" />
            <span>Search & Save</span>
          </Link>
        </div>
      </div>

      {/* Comparison Selection Hint */}
      {locations.length >= 2 && selectedForCompare.length < 2 && (
        <div className="p-3 bg-teal-50/70 border border-teal-200/70 rounded-2xl text-xs text-teal-900 flex items-center gap-2">
          <Scale className="w-4 h-4 text-teal-600 shrink-0" />
          <span>
            Tip: Select the checkbox on any two neighborhoods to launch a structured, score-free comparison. ({selectedForCompare.length}/2 selected)
          </span>
        </div>
      )}

      {/* Main List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-40 bg-slate-100 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : locations.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <Bookmark className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="font-display font-semibold text-slate-800 text-base">
            No saved locations yet
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            When exploring any locality, click the bookmark icon on the top search bar to save it to your account for comparison and reference.
          </p>
          <Link
            to="/explore"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy-900 text-white rounded-xl text-xs font-semibold hover:bg-navy-800 transition-colors shadow-xs"
          >
            <span>Explore neighborhoods</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {locations.map((item) => {
            const isEditing = editingId === item.id;
            const isSelected = selectedForCompare.includes(item.id);

            return (
              <div
                key={item.id}
                className={`p-5 rounded-3xl border transition-all space-y-3 bg-white ${
                  isSelected
                    ? 'border-teal-500 ring-2 ring-teal-500/20 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300 shadow-xs'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectForCompare(item.id)}
                      className="mt-1 h-4 w-4 rounded text-teal-600 focus:ring-teal-500 border-slate-300"
                    />
                    <div>
                      <h3 className="font-display font-bold text-sm text-navy-900 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-teal-600" />
                        <span>{item.locality_name}</span>
                      </h3>
                      {item.label && !isEditing && (
                        <span className="text-[10px] font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full inline-block mt-1">
                          {item.label}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    {!isEditing && (
                      <button
                        onClick={() => startEdit(item)}
                        className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition-colors"
                        title="Edit label & notes"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {isEditing ? (
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Label (e.g. Shortlist #1)</label>
                      <input
                        type="text"
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value)}
                        placeholder="Label"
                        className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Private Notes</label>
                      <textarea
                        value={editNotes}
                        onChange={(e) => setEditNotes(e.target.value)}
                        placeholder="Add notes about rent quotes, visit dates, etc."
                        rows={2}
                        className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => saveEdit(item.id)}
                        className="px-3 py-1 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-lg flex items-center gap-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Save</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {item.notes ? (
                      <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                        {item.notes}
                      </p>
                    ) : (
                      <p className="text-[11px] text-slate-400 italic">No notes added.</p>
                    )}
                  </>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px]">
                  <span className="text-slate-400">
                    Saved on {new Date(item.created_at).toLocaleDateString()}
                  </span>
                  <Link
                    to={`/explore?q=${encodeURIComponent(item.locality_name)}`}
                    className="font-semibold text-teal-700 hover:text-teal-900 flex items-center gap-1"
                  >
                    <span>Re-explore</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
