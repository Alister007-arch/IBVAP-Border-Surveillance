import React, { useState, useEffect } from "react";
import {
  Shield,
  Radio,
  Crosshair,
  Compass,
  AlertTriangle,
  Users,
  Car,
  Plane,
  X,
  Navigation,
  Layers,
  Activity,
  Flame,
  CheckCircle2,
  Send,
  Eye,
} from "lucide-react";

export default function TacticalGISRadarModal({ isOpen, onClose, alerts = [], cameras = [] }) {
  const [mapMode, setMapMode] = useState("RADAR"); // RADAR, TOPO, THERMAL
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [qrfDispatched, setQrfDispatched] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState("STANDBY");
  const [radarAngle, setRadarAngle] = useState(0);

  // Rotate radar sweep
  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setRadarAngle((prev) => (prev + 3) % 360);
    }, 40);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  // Static + dynamic tactical map entities
  const cameraNodes = [
    { id: "webcam_local_01", name: "Command Post CP-1", x: 250, y: 260, fovAngle: 45, fovDir: 290, type: "cctv", status: "ONLINE" },
    { id: "cam_sector_02", name: "Tower Alpha (North Ridge)", x: 140, y: 150, fovAngle: 60, fovDir: 330, type: "thermal", status: "ONLINE" },
    { id: "cam_sector_03", name: "Outpost Bravo (Riverine)", x: 370, y: 180, fovAngle: 55, fovDir: 40, type: "ptz", status: "ONLINE" },
    { id: "phone_1", name: "Mobile Patrol Unit-1", x: 210, y: 350, fovAngle: 70, fovDir: 270, type: "mobile", status: "PATROLLING" },
  ];

  const tacticalTargets = [
    {
      id: "TGT-4821",
      name: "Suspect Track #1 (Ayush - WANTED)",
      type: "SUSPECT",
      x: 185,
      y: 195,
      heading: "315° NW",
      speed: "14.2 km/h",
      eta: "34s",
      threat: "CRITICAL",
      sector: "Sector-4 Buffer Line",
      weapon: "Concealed Blade",
    },
    {
      id: "TGT-9014",
      name: "Unidentified Low-Flying UAV",
      type: "DRONE",
      x: 320,
      y: 130,
      heading: "240° SW",
      speed: "42.0 km/h",
      eta: "22s",
      threat: "HIGH",
      sector: "Airspace Corridor Bravo",
      weapon: "Surveillance Payload",
    },
    {
      id: "QRF-VEH-1",
      name: "QRF Fast Intercept Vehicle (4x4)",
      type: "FRIENDLY",
      x: qrfDispatched ? 210 : 280,
      y: qrfDispatched ? 230 : 380,
      heading: qrfDispatched ? "315° NW (Intercept Course)" : "0° Stationary",
      speed: qrfDispatched ? "55 km/h" : "0 km/h",
      eta: qrfDispatched ? "48s to Target" : "Standby",
      threat: "SAFE",
      sector: "Main Access Trail",
    },
  ];

  const handleDispatchQRF = () => {
    setQrfDispatched(true);
    setDispatchStatus("INTERCEPTING");
    setTimeout(() => {
      setDispatchStatus("ENGAGING");
    }, 4500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-fadeIn select-none">
      <div className="bg-slate-950 border border-slate-700/80 w-full max-w-6xl h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100">
        
        {/* Header HUD Bar */}
        <div className="bg-slate-900/90 border-b border-slate-800 px-5 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-500/60 text-emerald-400 shadow-md shadow-emerald-950">
              <Crosshair className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-mono font-bold tracking-wider text-sm sm:text-base text-slate-100">
                  TACTICAL GIS C2 RADAR
                </h2>
                <span className="text-[10px] font-mono bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-700 font-bold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                  LIVE TELEMETRY
                </span>
                <span className="text-[10px] font-mono bg-rose-950 text-rose-300 px-2 py-0.5 rounded border border-rose-700 font-bold hidden sm:inline">
                  DEFCON-2 ELEVATED
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
                <span>SECTOR: Border North (Alpha-7)</span>
                <span>•</span>
                <span>GPS: 34°14'28"N, 74°21'05"E</span>
                <span>•</span>
                <span>ELV: 1,840m</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Map Mode Selector */}
            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-1 text-xs">
              <button
                onClick={() => setMapMode("RADAR")}
                className={`px-2.5 py-1 rounded font-mono font-semibold transition ${
                  mapMode === "RADAR" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                RADAR
              </button>
              <button
                onClick={() => setMapMode("TOPO")}
                className={`px-2.5 py-1 rounded font-mono font-semibold transition ${
                  mapMode === "TOPO" ? "bg-cyan-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                SATELLITE
              </button>
              <button
                onClick={() => setMapMode("THERMAL")}
                className={`px-2.5 py-1 rounded font-mono font-semibold transition ${
                  mapMode === "THERMAL" ? "bg-rose-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                FLIR HEAT
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Close Tactical Map"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          
          {/* Main Map View (SVG Interactive Radar) */}
          <div className="flex-1 bg-slate-950 relative overflow-hidden flex items-center justify-center p-4">
            
            {/* Background Grid Texture */}
            <div
              className={`absolute inset-0 transition-opacity duration-500 pointer-events-none ${
                mapMode === "RADAR"
                  ? "opacity-30 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:24px_24px]"
                  : mapMode === "TOPO"
                  ? "opacity-25 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:20px_20px]"
                  : "opacity-35 bg-[radial-gradient(#f43f5e_1px,transparent_1px)] [background-size:16px_16px]"
              }`}
            />

            {/* Radar Viewport SVG */}
            <svg viewBox="0 0 500 500" className="w-full h-full max-w-[560px] max-h-[560px] relative z-10 drop-shadow-2xl">
              <defs>
                {/* Radar Sweep Gradient */}
                <linearGradient id="sweepGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </linearGradient>
                {/* Thermal Gradient */}
                <radialGradient id="thermalCenter" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.35" />
                  <stop offset="60%" stopColor="#f59e0b" stopOpacity="0.15" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </radialGradient>
              </defs>

              {/* Thermal Heatmap Background Overlay if in THERMAL mode */}
              {mapMode === "THERMAL" && (
                <rect x="0" y="0" width="500" height="500" fill="url(#thermalCenter)" />
              )}

              {/* Concentric Range Rings */}
              <circle cx="250" cy="250" r="230" fill="none" stroke="#1e293b" strokeWidth="1.5" />
              <circle cx="250" cy="250" r="175" fill="none" stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />
              <circle cx="250" cy="250" r="115" fill="none" stroke="#1e293b" strokeWidth="1" />
              <circle cx="250" cy="250" r="55" fill="none" stroke="#1e293b" strokeWidth="1" strokeDasharray="3 3" />

              {/* Range Distance Labels */}
              <text x="254" y="80" fill="#64748b" fontSize="8" fontFamily="monospace">1,000m OUTER PERIMETER</text>
              <text x="254" y="138" fill="#64748b" fontSize="8" fontFamily="monospace">500m BUFFER ZONE</text>
              <text x="254" y="198" fill="#64748b" fontSize="8" fontFamily="monospace">250m INNER DEFENSE</text>

              {/* Crosshair Center Lines */}
              <line x1="20" y1="250" x2="480" y2="250" stroke="#1e293b" strokeWidth="1" strokeDasharray="2 4" />
              <line x1="250" y1="20" x2="250" y2="480" stroke="#1e293b" strokeWidth="1" strokeDasharray="2 4" />

              {/* Rotating Radar Sweep Cone */}
              <g transform={`rotate(${radarAngle}, 250, 250)`}>
                <path
                  d="M 250 250 L 250 20 A 230 230 0 0 1 412 87 Z"
                  fill="url(#sweepGrad)"
                  pointerEvents="none"
                />
                <line x1="250" y1="250" x2="250" y2="20" stroke="#34d399" strokeWidth="1.5" opacity="0.8" />
              </g>

              {/* Zero Line (International Border Smart Fence) */}
              <path
                d="M 20 110 Q 160 140 250 115 T 480 130"
                fill="none"
                stroke="#e11d48"
                strokeWidth="2.5"
                strokeDasharray="6 3"
              />
              <text x="50" y="105" fill="#f43f5e" fontSize="9" fontWeight="bold" fontFamily="monospace">
                ── ZERO LINE (INTERNATIONAL BORDER FENCE) ──
              </text>

              {/* Buffer Zone Patrol Track */}
              <path
                d="M 20 230 Q 180 250 300 220 T 480 240"
                fill="none"
                stroke="#0ea5e9"
                strokeWidth="1"
                strokeDasharray="3 3"
                opacity="0.4"
              />
              <text x="310" y="248" fill="#38bdf8" fontSize="8" fontFamily="monospace" opacity="0.7">
                PATROL BUFFER CORRIDOR
              </text>

              {/* Camera Field-of-View (FOV) Cones */}
              {cameraNodes.map((cam) => {
                const angleRad = (cam.fovDir * Math.PI) / 180;
                const spreadRad = ((cam.fovAngle / 2) * Math.PI) / 180;
                const r = 70;
                const x1 = cam.x + r * Math.cos(angleRad - spreadRad);
                const y1 = cam.y + r * Math.sin(angleRad - spreadRad);
                const x2 = cam.x + r * Math.cos(angleRad + spreadRad);
                const y2 = cam.y + r * Math.sin(angleRad + spreadRad);

                return (
                  <g key={cam.id} className="cursor-pointer group" onClick={() => setSelectedEntity(cam)}>
                    <path
                      d={`M ${cam.x} ${cam.y} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`}
                      fill="#0284c7"
                      fillOpacity="0.12"
                      stroke="#0284c7"
                      strokeWidth="1"
                      strokeDasharray="2 2"
                    />
                    <circle cx={cam.x} cy={cam.y} r="5" fill="#0284c7" stroke="#38bdf8" strokeWidth="1.5" />
                    <text
                      x={cam.x + 8}
                      y={cam.y + 3}
                      fill="#bae6fd"
                      fontSize="8"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {cam.id}
                    </text>
                  </g>
                );
              })}

              {/* Target Entities (Infiltrators / UAV / Friendly QRF) */}
              {tacticalTargets.map((tgt) => {
                const isSuspect = tgt.type === "SUSPECT";
                const isDrone = tgt.type === "DRONE";
                const isFriendly = tgt.type === "FRIENDLY";

                const color = isSuspect ? "#f43f5e" : isDrone ? "#c084fc" : "#10b981";

                return (
                  <g key={tgt.id} className="cursor-pointer" onClick={() => setSelectedEntity(tgt)}>
                    {/* Pulsing ring */}
                    <circle cx={tgt.x} cy={tgt.y} r="12" fill={color} fillOpacity="0.18">
                      <animate attributeName="r" values="8;16;8" dur="2s" repeatCount="indefinite" />
                      <animate attributeName="fill-opacity" values="0.3;0.05;0.3" dur="2s" repeatCount="indefinite" />
                    </circle>

                    {/* Target Icon Node */}
                    <circle cx={tgt.x} cy={tgt.y} r="4.5" fill={color} stroke="#ffffff" strokeWidth="1.2" />

                    {/* Vector Arrow Line (Predictive Heading) */}
                    <line
                      x1={tgt.x}
                      y1={tgt.y}
                      x2={tgt.x - 22}
                      y2={tgt.y - 18}
                      stroke={color}
                      strokeWidth="1.5"
                      markerEnd="url(#arrow)"
                    />

                    {/* Target Label HUD */}
                    <rect
                      x={tgt.x + 8}
                      y={tgt.y - 14}
                      width="105"
                      height="20"
                      rx="3"
                      fill="#020617"
                      fillOpacity="0.85"
                      stroke={color}
                      strokeWidth="0.8"
                    />
                    <text x={tgt.x + 12} y={tgt.y - 4} fill="#f1f5f9" fontSize="7.5" fontWeight="bold" fontFamily="monospace">
                      {tgt.id} [{tgt.type}]
                    </text>
                    <text x={tgt.x + 12} y={tgt.y + 3} fill={color} fontSize="6.5" fontFamily="monospace">
                      ETA: {tgt.eta} | {tgt.heading}
                    </text>
                  </g>
                );
              })}

              {/* Intercept Line when QRF Dispatched */}
              {qrfDispatched && (
                <path
                  d="M 210 230 Q 195 210 185 195"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                >
                  <animate attributeName="stroke-dashoffset" values="20;0" dur="1s" repeatCount="indefinite" />
                </path>
              )}
            </svg>

            {/* Compass Rose Overlay */}
            <div className="absolute bottom-4 left-4 pointer-events-none bg-slate-900/80 border border-slate-700/80 rounded-lg p-2 flex items-center gap-2 font-mono text-[10px] text-slate-300">
              <Compass className="w-4 h-4 text-emerald-400 animate-spin-slow" />
              <span>HEADING: 358° N</span>
              <span className="text-slate-600">|</span>
              <span className="text-emerald-400 font-bold">GRID CALIBRATED</span>
            </div>

            {/* Tactical Legend */}
            <div className="absolute top-4 right-4 pointer-events-none bg-slate-900/85 border border-slate-700/80 rounded-lg p-2.5 flex flex-col gap-1.5 font-mono text-[10px] text-slate-300">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span>Hostile Infiltrator / Wanted</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span>
                <span>Airspace Incursion / UAV</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400"></span>
                <span>Optical & Thermal CCTV</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                <span>QRF Intercept Squad</span>
              </div>
            </div>
          </div>

          {/* Right Tactical Sidebar (Telemetry & QRF Controller) */}
          <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-slate-800 bg-slate-950/90 p-4 flex flex-col gap-4 overflow-y-auto">
            
            {/* Intercept / QRF Command Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 shadow-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" />
                  QRF TACTICAL INTERCEPT
                </span>
                <span
                  className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    qrfDispatched
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-700 animate-pulse"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {dispatchStatus}
                </span>
              </div>

              <p className="text-xs text-slate-400 mb-3 leading-snug">
                Immediate armed tactical interception for breach at{" "}
                <span className="text-rose-400 font-bold">Sector-4 Buffer Line</span>.
              </p>

              <button
                onClick={handleDispatchQRF}
                disabled={qrfDispatched}
                className={`w-full py-2.5 px-3 rounded-lg text-xs font-mono font-bold flex items-center justify-center gap-2 shadow-lg transition ${
                  qrfDispatched
                    ? "bg-emerald-950/60 border border-emerald-700/80 text-emerald-300 cursor-not-allowed"
                    : "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/40 active:scale-95"
                }`}
              >
                {qrfDispatched ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    QRF SQUAD DEPLOYED (ETA 48s)
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    DISPATCH QRF INTERCEPT SQUAD
                  </>
                )}
              </button>
            </div>

            {/* Selected Entity Inspector */}
            {selectedEntity ? (
              <div className="bg-slate-900/90 border border-cyan-800/80 rounded-xl p-3.5 shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase">
                    TARGET TELEMETRY INSPECTOR
                  </span>
                  <button
                    onClick={() => setSelectedEntity(null)}
                    className="text-slate-400 hover:text-white text-xs"
                  >
                    ✕
                  </button>
                </div>
                <h4 className="font-bold text-slate-100 text-xs mb-1">{selectedEntity.name}</h4>
                <div className="flex flex-col gap-1 text-[11px] font-mono text-slate-300 mt-2">
                  {selectedEntity.threat && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Threat Level:</span>
                      <span className="text-rose-400 font-bold">{selectedEntity.threat}</span>
                    </div>
                  )}
                  {selectedEntity.heading && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Vector Heading:</span>
                      <span>{selectedEntity.heading}</span>
                    </div>
                  )}
                  {selectedEntity.speed && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Speed Est:</span>
                      <span>{selectedEntity.speed}</span>
                    </div>
                  )}
                  {selectedEntity.eta && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Perimeter ETA:</span>
                      <span className="text-amber-400 font-bold">{selectedEntity.eta}</span>
                    </div>
                  )}
                  {selectedEntity.sector && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Sector:</span>
                      <span className="truncate">{selectedEntity.sector}</span>
                    </div>
                  )}
                  {selectedEntity.weapon && (
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-500">Armed Status:</span>
                      <span className="text-rose-400 font-bold">{selectedEntity.weapon}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-slate-800 rounded-xl p-4 text-center text-slate-500 font-mono text-xs">
                Click any radar blip or camera tower to inspect live telemetry.
              </div>
            )}

            {/* Live Border Sensor Health */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
              <span className="text-[10px] font-mono font-bold tracking-wider text-slate-400">
                ELECTRONIC SMART FENCE STATUS
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-slate-950 p-2 rounded border border-slate-800 flex flex-col">
                  <span className="text-[10px] text-slate-500">Vibration Sensor</span>
                  <span className="text-emerald-400 font-bold">ARMED (100%)</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800 flex flex-col">
                  <span className="text-[10px] text-slate-500">Thermal Barrier</span>
                  <span className="text-emerald-400 font-bold">ACTIVE</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800 flex flex-col">
                  <span className="text-[10px] text-slate-500">Anti-Drone Radar</span>
                  <span className="text-purple-400 font-bold">TRACKING (1)</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800 flex flex-col">
                  <span className="text-[10px] text-slate-500">Edge AI Engine</span>
                  <span className="text-cyan-400 font-bold">180 FPS LOW-LAT</span>
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
