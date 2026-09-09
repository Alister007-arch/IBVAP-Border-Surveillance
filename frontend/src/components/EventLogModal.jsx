import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Search,
  Filter,
  Trash2,
  X,
  ShieldAlert,
  Clock,
  MapPin,
  Image as ImageIcon,
  ExternalLink,
} from 'lucide-react';

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().startsWith('http') && !envUrl.includes('onrender.com')) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin;
  }
  return 'http://localhost:8000';
};
const API_BASE_URL = getApiBaseUrl();

export default function EventLogModal({ isOpen, onClose }) {
  const [events, setEvents] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', '100');
      if (priorityFilter !== 'ALL') params.set('priority', priorityFilter);
      if (categoryFilter !== 'ALL') params.set('category', categoryFilter);
      if (searchTerm.trim()) params.set('search', searchTerm.trim());

      const res = await fetch(`${API_BASE_URL}/api/events?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
        setTotalCount(data.total || 0);
      }
    } catch (err) {
      console.error('Failed to fetch audit events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchEvents();
    }
  }, [isOpen, priorityFilter, categoryFilter, searchTerm]);

  if (!isOpen) return null;

  const handleExportCSV = () => {
    const url = `${API_BASE_URL}/api/events/export?format=csv&priority=${priorityFilter}&category=${categoryFilter}`;
    window.open(url, '_blank');
  };

  const handleClearLog = async () => {
    if (window.confirm('Are you sure you want to clear all forensic incident logs?')) {
      await fetch(`${API_BASE_URL}/api/events`, { method: 'DELETE' });
      fetchEvents();
    }
  };

  const priorityBadge = (p) => {
    if (p === 'RED') return 'bg-rose-950 text-rose-300 border-rose-700';
    if (p === 'AMBER') return 'bg-amber-950 text-amber-300 border-amber-700';
    if (p === 'BLUE') return 'bg-blue-950 text-blue-300 border-blue-700';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-5xl h-[88vh] shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="bg-amber-600/20 border border-amber-500 p-2.5 rounded-lg text-amber-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                  Tactical Incident Log & Forensic Audit Trail
                </h3>
                <span className="text-[10px] bg-slate-800 text-cyan-300 font-mono px-2 py-0.5 rounded border border-slate-700 font-bold">
                  {totalCount} Total Incidents
                </span>
              </div>
              <p className="text-xs text-slate-400">Persistent SQLite audit records with timestamp, metadata & forensic evidence</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCSV}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow-lg shadow-emerald-600/20"
            >
              <Download className="w-4 h-4" /> Export CSV
            </button>
            <button
              onClick={handleClearLog}
              className="bg-slate-800 hover:bg-rose-950 hover:text-rose-300 text-slate-400 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
              title="Clear log"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Toolbar & Filters */}
        <div className="bg-slate-950/70 p-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 shrink-0">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search description, camera, license plate, or face name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
              <Filter className="w-3 h-3" /> Priority:
            </span>
            {['ALL', 'RED', 'AMBER', 'BLUE'].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border transition ${
                  priorityFilter === p
                    ? 'bg-blue-600 text-white border-blue-500'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Incidents Table */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
              Loading incident log records...
            </div>
          ) : events.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
              <ShieldAlert className="w-8 h-8 text-slate-600 mb-2" />
              <p className="font-semibold text-slate-400">No security incidents recorded matching filters</p>
              <p className="text-[11px] text-slate-600 mt-1">Live camera events and intrusion breaches will be logged here automatically.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
              <div className="grid grid-cols-12 bg-slate-950 px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <div className="col-span-2">Timestamp</div>
                <div className="col-span-1 text-center">Priority</div>
                <div className="col-span-2">Category</div>
                <div className="col-span-2">Location</div>
                <div className="col-span-4">Incident Description</div>
                <div className="col-span-1 text-center">Evidence</div>
              </div>

              {events.map((ev) => (
                <div
                  key={ev.event_id}
                  className="grid grid-cols-12 items-center px-4 py-3 text-xs hover:bg-slate-800/40 transition-colors"
                >
                  {/* Timestamp */}
                  <div className="col-span-2 font-mono text-[11px] text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>{new Date(ev.timestamp).toLocaleString()}</span>
                  </div>

                  {/* Priority */}
                  <div className="col-span-1 text-center">
                    <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${priorityBadge(ev.priority)}`}>
                      {ev.priority}
                    </span>
                  </div>

                  {/* Category */}
                  <div className="col-span-2 font-semibold text-slate-200 truncate">
                    {ev.category}
                  </div>

                  {/* Location */}
                  <div className="col-span-2 text-slate-400 text-[11px] truncate flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                    <span className="truncate">{ev.location}</span>
                  </div>

                  {/* Description & metadata tags */}
                  <div className="col-span-4 flex flex-col gap-1 pr-2">
                    <span className="text-slate-100 font-medium leading-snug">{ev.description}</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {ev.plate_number && (
                        <span className="text-[10px] bg-yellow-950 text-yellow-300 border border-yellow-700/60 font-mono px-1.5 py-0.2 rounded font-bold">
                          Plate: {ev.plate_number}
                        </span>
                      )}
                      {ev.face_name && (
                        <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-mono px-1.5 py-0.2 rounded font-bold">
                          FRS: {ev.face_name}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Snapshot Preview */}
                  <div className="col-span-1 flex justify-center">
                    {ev.has_snapshot ? (
                      <button
                        onClick={() => setSelectedSnapshot(ev.event_id)}
                        className="p-1.5 bg-blue-950/60 hover:bg-blue-900 border border-blue-800 text-blue-300 rounded-md transition"
                        title="View Snapshot"
                      >
                        <ImageIcon className="w-4 h-4" />
                      </button>
                    ) : (
                      <span className="text-[10px] text-slate-600 font-mono">-</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Snapshot Modal Preview */}
        {selectedSnapshot && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/90 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Incident Evidence Snapshot</span>
                <button onClick={() => setSelectedSnapshot(null)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-black rounded-lg overflow-hidden border border-slate-800 max-h-[60vh] flex items-center justify-center">
                <img
                  src={`${API_BASE_URL}/api/events/${selectedSnapshot}/snapshot`}
                  alt="Incident snapshot"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
