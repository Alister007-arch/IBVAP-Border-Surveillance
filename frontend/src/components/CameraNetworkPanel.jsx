import React from 'react';
import { Smartphone, Radio, Shield, MapPin, Wifi } from 'lucide-react';

export default function CameraNetworkPanel({ cameras = [], mobileStreamUrl = '' }) {
  return (
    <div className="bg-slate-900/90 flex flex-col h-1/2 border-b border-slate-700/80">
      {/* Header */}
      <div className="px-3.5 py-2.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-blue-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Surveillance Nodes
          </h2>
        </div>
        <span className="text-[11px] bg-blue-950 text-blue-300 border border-blue-800/60 px-2 py-0.5 rounded-full font-mono">
          {cameras.length} active
        </span>
      </div>

      {/* Camera List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-2">
        {cameras.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500 space-y-2">
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40">
              <p className="font-semibold text-slate-400">No Mobile Cameras Active</p>
              <p className="text-[11px] text-slate-500 mt-1">
                Open <span className="text-cyan-300 font-mono break-all">{mobileStreamUrl || 'mobile stream link'}</span> on your phone.
              </p>
            </div>
          </div>
        ) : (
          cameras.map((cam) => {
            return (
              <div
                key={cam.camera_id}
                className="p-2.5 bg-slate-950/40 hover:bg-slate-800/50 rounded-lg transition-colors flex items-center justify-between text-xs border border-slate-800/50 mb-1.5"
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <div className="mt-1">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                    </span>
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 font-semibold text-slate-100 truncate">
                      <span className="font-mono text-cyan-300">{cam.camera_id}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-0.5 truncate">
                      <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                      <span className="truncate">{cam.location}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1 shrink-0 ml-2">
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                    ONLINE
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono">15 FPS Live</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
