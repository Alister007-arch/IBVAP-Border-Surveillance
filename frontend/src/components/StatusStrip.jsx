import React, { useState, useEffect } from "react";
import {
  Shield,
  AlertTriangle,
  Clock,
  Plus,
  FileText,
  UserCheck,
  Power,
  PowerOff,
  RotateCcw,
  Volume2,
  VolumeX,
  Radio,
} from "lucide-react";

/**
 * StatusStrip — top header bar for IBVAP dashboard.
 *
 * Additions (v2):
 *  - System START / STOP master toggle button
 *  - Full System RESET button
 *  - RED / AMBER / BLUE pulsing threat indicator dots with beep notification
 *  - Mute/Unmute alarm button
 */
export default function StatusStrip({
  status,
  connected,
  systemRunning,
  latestAlertPriority,   // most recent non-system alert priority ('RED'|'AMBER'|'BLUE'|null)
  muted,
  onToggleMute,
  onOpenAddCamera,
  onOpenEventLog,
  onOpenWatchlist,
  onSystemStart,
  onSystemStop,
  onSystemReset,
}) {
  const formattedTime = status.last_update
    ? new Date(status.last_update).toLocaleTimeString()
    : "--:--:--";

  const [confirmReset, setConfirmReset] = useState(false);

  // Auto-dismiss the "click again to confirm" reset prompt after 4 s
  useEffect(() => {
    if (!confirmReset) return;
    const t = setTimeout(() => setConfirmReset(false), 4000);
    return () => clearTimeout(t);
  }, [confirmReset]);

  const handleResetClick = () => {
    if (!confirmReset) {
      setConfirmReset(true);
    } else {
      setConfirmReset(false);
      onSystemReset();
    }
  };

  // Threat indicator dot config
  const threatDots = [
    {
      priority: "RED",
      label: "CRITICAL",
      pulse: latestAlertPriority === "RED",
      dotBg: "bg-rose-500",
      pingShadow: "bg-rose-400",
      labelColor: "text-rose-400",
    },
    {
      priority: "AMBER",
      label: "WARNING",
      pulse: latestAlertPriority === "AMBER",
      dotBg: "bg-amber-400",
      pingShadow: "bg-amber-300",
      labelColor: "text-amber-400",
    },
    {
      priority: "BLUE",
      label: "INFO",
      pulse: latestAlertPriority === "BLUE",
      dotBg: "bg-blue-400",
      pingShadow: "bg-blue-300",
      labelColor: "text-blue-400",
    },
  ];

  return (
    <header className="bg-slate-950 border-b border-slate-800 px-4 py-2 flex items-center justify-between shadow-xl select-none shrink-0 gap-2 flex-wrap">
      {/* Brand */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="bg-blue-600/20 border border-blue-500/50 p-2 rounded-lg text-blue-400 shadow-md shadow-blue-500/10">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold tracking-wider text-slate-100 text-sm">IBVAP</span>
            <span className="text-[10px] bg-slate-800 text-slate-300 font-medium px-2 py-0.5 rounded border border-slate-700 hidden sm:inline">
              Intelligent Border Video Analytics Platform
            </span>
            <span className="text-[10px] bg-blue-900/60 text-blue-300 font-mono px-1.5 py-0.5 rounded border border-blue-700/50 font-bold">
              SIH26187
            </span>
            <span className="text-[10px] bg-emerald-950 text-emerald-300 font-mono px-1.5 py-0.5 rounded border border-emerald-700/50 font-semibold hidden md:inline">
              FRS &amp; ANPR READY
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">{status.zone_name}</p>
        </div>
      </div>

      {/* Right side controls */}
      <div className="flex items-center gap-2 text-xs flex-wrap">

        {/* ── Threat Indicator Dots ── */}
        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5">
          {threatDots.map(({ priority, label, pulse, dotBg, pingShadow, labelColor }) => (
            <div key={priority} className="flex items-center gap-1 group" title={`${priority} priority threat`}>
              <span className="relative flex h-2.5 w-2.5">
                {pulse && (
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${pingShadow} opacity-80`} />
                )}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${dotBg} ${pulse ? "shadow-lg" : "opacity-30"}`} />
              </span>
              <span className={`hidden sm:inline text-[9px] font-bold font-mono ${pulse ? labelColor : "text-slate-600"}`}>
                {priority}
              </span>
            </div>
          ))}
        </div>

        {/* ── Action Buttons ── */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={onOpenAddCamera}
            className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow-md shadow-blue-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ingest Camera</span>
          </button>

          <button
            onClick={onOpenEventLog}
            className="bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold px-2.5 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition"
          >
            <FileText className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Event Log</span>
          </button>

          <button
            onClick={onOpenWatchlist}
            className="bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold px-2.5 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition"
          >
            <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden lg:inline">Watchlist</span>
          </button>
        </div>

        {/* ── System Start / Stop ── */}
        {systemRunning ? (
          <button
            onClick={onSystemStop}
            className="bg-rose-900/70 hover:bg-rose-800 border border-rose-700 text-rose-300 font-bold px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow-md"
            title="Pause all surveillance camera workers"
          >
            <PowerOff className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Stop System</span>
          </button>
        ) : (
          <button
            onClick={onSystemStart}
            className="bg-emerald-800/70 hover:bg-emerald-700 border border-emerald-600 text-emerald-200 font-bold px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow-md"
            title="Resume all surveillance camera workers"
          >
            <Power className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Start System</span>
          </button>
        )}

        {/* ── Reset Button ── */}
        <button
          onClick={handleResetClick}
          className={`font-bold px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow-md border ${
            confirmReset
              ? "bg-rose-600 hover:bg-rose-500 border-rose-400 text-white animate-pulse"
              : "bg-slate-900 hover:bg-slate-800 border-slate-700 text-slate-300"
          }`}
          title="Reset surveillance — clears all cameras, alerts & logs"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{confirmReset ? "Confirm Reset?" : "Reset"}</span>
        </button>

        {/* ── Mute / Unmute alarm ── */}
        <button
          onClick={onToggleMute}
          className={`px-2 py-1.5 rounded-lg border flex items-center gap-1 transition ${
            muted
              ? "bg-slate-800 border-slate-700 text-slate-500 hover:text-slate-300"
              : "bg-slate-900 border-slate-700 text-amber-400 hover:bg-slate-800"
          }`}
          title={muted ? "Unmute alarm beeps" : "Mute alarm beeps"}
        >
          {muted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
        </button>

        {/* ── WebSocket link status ── */}
        <div className="flex items-center gap-2 bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-800">
          <span className="relative flex h-2 w-2">
            {connected ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
            )}
          </span>
          <span className={connected ? "text-emerald-400 font-semibold font-mono text-[11px]" : "text-rose-400 font-semibold font-mono text-[11px]"}>
            {connected ? "LINK LIVE" : "OFFLINE"}
          </span>
        </div>

        {/* ── Cameras count ── */}
        <div className="flex items-center gap-1.5 text-slate-300 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
          <span className="text-slate-400">Cameras:</span>
          <span className="font-bold text-cyan-300 font-mono">{status.total_cameras}</span>
        </div>

        {/* ── Alert count ── */}
        <div className="flex items-center gap-1.5 text-slate-300 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="font-bold text-amber-300 font-mono">{status.active_alerts}</span>
        </div>

        {/* ── Clock ── */}
        <div className="hidden xl:flex items-center gap-1 text-slate-500 font-mono text-[11px]">
          <Clock className="w-3 h-3" />
          <span>{formattedTime}</span>
        </div>
      </div>
    </header>
  );
}
