import React, { useMemo, useState } from 'react';
import {
  ShieldAlert,
  User,
  Car,
  Plane,
  Users,
  Eye,
  Clock,
  MapPin,
  Radio,
  SearchCheck,
  AlertTriangle,
  Moon,
  Footprints,
} from 'lucide-react';

const SECTIONS = [
  { id: 1, title: 'Virtual Fence & Intrusion', detail: 'Perimeter Breaches & Tripwires', icon: ShieldAlert, color: 'text-rose-400' },
  { id: 2, title: 'Facial Recognition (FRS)', detail: 'Watchlist & Suspect Matches', icon: User, color: 'text-cyan-400' },
  { id: 3, title: 'ANPR License Plates', detail: 'BOLO & Vehicle Tracking', icon: Car, color: 'text-yellow-400' },
  { id: 4, title: 'Suspicious Activities', detail: 'Loitering, Sprint, Abandoned', icon: Footprints, color: 'text-amber-400' },
  { id: 5, title: 'Night-Time Movements', detail: 'Low-Light & IR Movement', icon: Moon, color: 'text-indigo-400' },
  { id: 6, title: 'Airspace Threats', detail: 'Drone & Aerial Incursions', icon: Plane, color: 'text-purple-400' },
  { id: 7, title: 'Mass Incursion Clusters', detail: 'Group Gatherings & Formations', icon: Users, color: 'text-emerald-400' },
];

const PRIORITIES = ['ALL', 'RED', 'AMBER', 'BLUE'];

function priorityClasses(priority) {
  if (priority === 'RED') return 'bg-rose-950 text-rose-300 border-rose-700/80';
  if (priority === 'AMBER') return 'bg-amber-950 text-amber-300 border-amber-700/80';
  if (priority === 'BLUE') return 'bg-blue-950 text-blue-300 border-blue-700/80';
  return 'bg-slate-800 text-slate-300 border-slate-700';
}

function filterButtonClasses(priority, active) {
  if (!active) return 'bg-slate-800 text-slate-400 hover:text-slate-200 border-slate-700';
  if (priority === 'RED') return 'bg-rose-600 text-white border-rose-500';
  if (priority === 'AMBER') return 'bg-amber-600 text-white border-amber-500';
  if (priority === 'BLUE') return 'bg-blue-600 text-white border-blue-500';
  return 'bg-cyan-600 text-white border-cyan-500';
}

function AlertCard({ alert }) {
  const timeStr = alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : '--:--:--';
  const priorityBadge = priorityClasses(alert.priority);
  const cardTone = alert.priority === 'RED' ? 'bg-rose-950/20 border-rose-900/60' : 'bg-slate-950/45 border-slate-800';

  return (
    <div className={`p-2.5 rounded-lg border ${cardTone} flex flex-col gap-1.5 shadow-md`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <span className="font-bold text-slate-100 text-[11px] truncate">{alert.category}</span>

          {alert.plate_number && (
            <span className="text-[9px] font-mono bg-yellow-950 text-yellow-300 px-1.5 py-0.2 rounded border border-yellow-700 font-bold">
              {alert.plate_number}
            </span>
          )}

          {alert.face_name && (
            <span className="text-[9px] font-mono bg-cyan-950 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-700 font-bold">
              {alert.face_name}
            </span>
          )}

          {alert.group_size > 1 && (
            <span className="text-[9px] font-mono bg-amber-950 text-amber-300 px-1.5 py-0.2 rounded border border-amber-700">
              Qty {alert.group_size}
            </span>
          )}
        </div>
        <span className={`shrink-0 text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${priorityBadge}`}>
          {alert.priority}
        </span>
      </div>

      <p className="text-[11px] text-slate-200 leading-snug font-medium">{alert.description}</p>

      <div className="flex items-center justify-between gap-2 text-[10px] text-slate-400 pt-1 border-t border-slate-800/50">
        <div className="flex items-center gap-1 min-w-0">
          <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
          <span className="truncate">{alert.location}</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono flex items-center gap-0.5 shrink-0">
          <Clock className="w-2.5 h-2.5" />
          {timeStr}
        </span>
      </div>
    </div>
  );
}

export default function AlertFeed({ alerts }) {
  const [priorityFilter, setPriorityFilter] = useState('ALL');

  const visibleAlerts = useMemo(() => {
    if (priorityFilter === 'ALL') return alerts;
    return alerts.filter((alert) => alert.priority === priorityFilter);
  }, [alerts, priorityFilter]);

  const mapCategoryToSection = (cat) => {
    if (cat === 'Virtual Fence') return 1;
    if (cat === 'Face Recognition') return 2;
    if (cat === 'ANPR Plate') return 3;
    if (cat === 'Suspicious Activity') return 4;
    if (cat === 'Night Movement') return 5;
    if (cat === 'Drone') return 6;
    if (cat === 'Group') return 7;
    return 1;
  };

  const alertsBySection = useMemo(() => {
    const grouped = {};
    SECTIONS.forEach((s) => {
      grouped[s.id] = visibleAlerts.filter((alert) => {
        const sid = mapCategoryToSection(alert.category);
        return sid === s.id;
      });
    });
    return grouped;
  }, [visibleAlerts]);

  return (
    <div className="bg-slate-900/95 flex flex-col h-full overflow-hidden border-t border-slate-800">
      <div className="bg-slate-950 px-3.5 py-2.5 border-b border-slate-800 flex flex-col gap-2 select-none shrink-0">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 truncate">
              Tactical Intelligence Stream
            </h2>
          </div>
          <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-800/60 rounded px-2 py-0.5 shrink-0">
            {visibleAlerts.length} active
          </span>
        </div>

        <div className="flex items-center gap-1 overflow-x-auto">
          {PRIORITIES.map((priority) => (
            <button
              key={priority}
              onClick={() => setPriorityFilter(priority)}
              className={`text-[10px] px-2 py-0.5 rounded border font-mono font-bold transition-colors ${filterButtonClasses(
                priority,
                priorityFilter === priority,
              )}`}
            >
              {priority}
            </button>
          ))}
        </div>
      </div>

      {/* Categorized Feed Sections */}
      <div className="flex-1 overflow-y-auto p-2 grid grid-cols-1 gap-2 content-start">
        {SECTIONS.map((section) => {
          const sectionAlerts = alertsBySection[section.id] || [];
          const Icon = section.icon;

          return (
            <section key={section.id} className="bg-slate-950/40 border border-slate-800 rounded-lg overflow-hidden">
              <div className="px-2.5 py-1.5 bg-slate-950/80 border-b border-slate-800/80 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${section.color}`} />
                  <div className="min-w-0">
                    <h3 className="text-[11px] font-bold text-slate-200 truncate">{section.title}</h3>
                    <p className="text-[9px] text-slate-500 truncate">{section.detail}</p>
                  </div>
                </div>
                <span className="text-[9px] font-mono text-slate-300 bg-slate-900 border border-slate-700 rounded px-1.5 py-0.2 shrink-0">
                  {sectionAlerts.length}
                </span>
              </div>

              <div className="p-2 flex flex-col gap-1.5">
                {sectionAlerts.length === 0 ? (
                  <div className="py-2.5 text-center text-[10px] text-slate-600 flex items-center justify-center gap-1.5 font-mono">
                    <Radio className="w-3 h-3 text-slate-700" />
                    <span>Sector normal — listening</span>
                  </div>
                ) : (
                  sectionAlerts.slice(0, 5).map((alert, idx) => (
                    <AlertCard key={alert.alert_id || `${section.id}-${idx}`} alert={alert} />
                  ))
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
