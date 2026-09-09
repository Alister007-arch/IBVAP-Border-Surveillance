import React, { useState } from 'react';
import { Smartphone, Video, Shield, Plus, Trash2, Radio, Server, Camera, ExternalLink, Copy, Check } from 'lucide-react';

export default function CameraGrid({
  cameras,
  cameraFrames,
  mobileStreamUrl,
  onOpenAddCamera,
  onRemoveCamera,
  onQuickStartWebcam,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopyMobileLink = async (e) => {
    e.preventDefault();
    try {
      await navigator.clipboard.writeText(mobileStreamUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.warn('Clipboard write failed:', err);
    }
  };

  const activePhoneCount = (cameras || []).filter(
    (c) => c.type === 'ws_phone' || c.camera_id?.startsWith('phone_')
  ).length;

  // Empty State: All cameras removed
  if (!cameras || cameras.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-2xl p-6 text-center bg-slate-950/40 backdrop-blur-sm">
        <div className="max-w-xl w-full bg-slate-900/90 border border-slate-700/80 p-8 rounded-2xl shadow-2xl flex flex-col items-center">
          {/* Radar icon badge */}
          <div className="relative mb-5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-30"></span>
            <div className="relative bg-blue-600/20 border border-blue-500 p-4 rounded-2xl text-blue-400">
              <Shield className="w-10 h-10" />
            </div>
          </div>

          <h3 className="text-xl font-bold text-slate-100 tracking-wide mb-1">
            IBVAP Tactical Surveillance Grid
          </h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed max-w-md">
            No dummy cameras loaded. Ingest live IP-based CCTV infrastructure, USB border cameras, or mobile patrol units without requiring dedicated FRS or ANPR hardware.
          </p>

          {/* 3 Quick Action Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full mb-6">
            {/* 1. Start Local Webcam */}
            <button
              onClick={onQuickStartWebcam}
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-blue-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-blue-600/20 text-blue-400 group-hover:scale-110 transition">
                <Camera className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Start Local Webcam</span>
              <span className="text-[10px] text-slate-500 leading-tight">Instant 1-click test with device index 0</span>
            </button>

            {/* 2. Add IP CCTV */}
            <button
              onClick={onOpenAddCamera}
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-blue-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-emerald-600/20 text-emerald-400 group-hover:scale-110 transition">
                <Server className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Add IP Camera (RTSP)</span>
              <span className="text-[10px] text-slate-500 leading-tight">Connect RTSP or HTTP CCTV feed</span>
            </button>

            {/* 3. Mobile Phone */}
            <a
              href={mobileStreamUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-cyan-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-cyan-600/20 text-cyan-400 group-hover:scale-110 transition">
                <Smartphone className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Mobile Patrol Phone</span>
              <span className="text-[10px] text-slate-500 leading-tight">Stream live camera from phone browser</span>
            </a>
          </div>

          {/* Direct Mobile URL Bar */}
          <div className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-left">
            <div className="flex items-center justify-between gap-2 text-[11px] text-slate-400 mb-1">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
                Mobile Patrol Streamer URL (Connect Multiple Phones):
              </span>
              <button
                onClick={handleCopyMobileLink}
                className="bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/80 px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
            </div>
            <div className="font-mono text-xs text-cyan-300 break-all select-all">
              {mobileStreamUrl}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Active Cameras Grid
  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Mobile Stream Quick Access Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between text-xs text-slate-300 gap-3 shrink-0 shadow-lg">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-1.5 rounded-lg bg-cyan-950 border border-cyan-800/60 text-cyan-400 shrink-0">
            <Smartphone className="w-4 h-4" />
          </div>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100">Mobile Patrol Ingestion:</span>
              {activePhoneCount > 0 ? (
                <span className="bg-emerald-950 border border-emerald-800/80 text-emerald-400 text-[10px] font-bold px-2 py-0.2 rounded-full flex items-center gap-1">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                  </span>
                  {activePhoneCount} {activePhoneCount === 1 ? 'Phone' : 'Phones'} Active
                </span>
              ) : (
                <span className="bg-slate-800 text-slate-400 text-[10px] font-medium px-2 py-0.2 rounded-full">
                  Connect Multiple Phones
                </span>
              )}
            </div>
            <a
              href={mobileStreamUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-300 font-mono text-[11px] hover:underline truncate max-w-sm sm:max-w-md"
            >
              {mobileStreamUrl}
            </a>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <div className="flex items-center bg-slate-950/80 border border-slate-700/80 rounded-lg p-1 gap-1">
            <span className="text-[10px] text-slate-400 font-semibold px-1">Connect Phones:</span>
            <a
              href={`${mobileStreamUrl}?id=phone_1`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-800/80 text-cyan-300 px-2 py-1 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
              title="Open stream for Phone 1 (Slot 1)"
            >
              📱 Phone 1
            </a>
            <a
              href={`${mobileStreamUrl}?id=phone_2`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-800/80 text-cyan-300 px-2 py-1 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
              title="Open stream for Phone 2 (Slot 2)"
            >
              📱 Phone 2
            </a>
            <a
              href={`${mobileStreamUrl}?id=phone_3`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-800/80 text-cyan-300 px-2 py-1 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
              title="Open stream for Phone 3 (Slot 3)"
            >
              📱 Phone 3
            </a>
          </div>

          <button
            onClick={handleCopyMobileLink}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
            title="Copy phone streamer link to clipboard"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            {copied ? 'Copied' : 'Copy Link'}
          </button>

          <button
            onClick={onOpenAddCamera}
            className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition shadow ml-1"
          >
            <Plus className="w-3.5 h-3.5" /> Add Camera
          </button>
        </div>
      </div>

      {/* Grid of active cameras */}
      {/* Grid of active cameras */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 flex-1 overflow-y-auto pb-4">
        {cameras.map((cam) => (
          <CameraCard
            key={cam.camera_id}
            cam={cam}
            frameSrc={cameraFrames[cam.camera_id]}
            onRemoveCamera={onRemoveCamera}
          />
        ))}
      </div>
    </div>
  );
}

const CameraCard = React.memo(function CameraCard({ cam, frameSrc, onRemoveCamera }) {
  const isPhone = cam.type === 'ws_phone' || cam.camera_id?.startsWith('phone_');
  const isWebcam = cam.type === 'webcam';
  const isIP = cam.type === 'ip_camera' || cam.type === 'rtsp';

  let typeBadge = 'Fixed CCTV';
  if (isPhone) typeBadge = 'Mobile Patrol';
  else if (isWebcam) typeBadge = 'USB Webcam';
  else if (isIP) typeBadge = 'IP Camera (RTSP)';

  const lastFrameRef = React.useRef(null);
  if (frameSrc) {
    lastFrameRef.current = frameSrc;
  }
  const effectiveSrc = frameSrc || lastFrameRef.current;

  return (
    <div
      className={`bg-slate-900 border rounded-xl overflow-hidden flex flex-col shadow-2xl relative transition ${
        isPhone
          ? 'border-cyan-700/80 shadow-cyan-950/20'
          : 'border-slate-700/80'
      }`}
    >
      {/* Camera Header Bar */}
      <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs select-none">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className={`font-mono font-bold tracking-wider truncate ${
            isPhone ? 'text-cyan-400' : 'text-blue-400'
          }`}>
            {cam.camera_id}
          </span>
          <span className="text-slate-400 font-medium truncate">{cam.location}</span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] border font-mono px-2 py-0.5 rounded font-semibold uppercase ${
            isPhone
              ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
              : isWebcam
              ? 'bg-purple-950 text-purple-300 border-purple-800/60'
              : 'bg-blue-950 text-blue-300 border-blue-800/60'
          }`}>
            {typeBadge}
          </span>

          <button
            onClick={() => onRemoveCamera && onRemoveCamera(cam.camera_id)}
            className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition"
            title="Remove Camera"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Video Feed Area */}
      <div className="flex-1 bg-black relative flex items-center justify-center min-h-[340px] overflow-hidden">
        {effectiveSrc ? (
          <img
            src={effectiveSrc}
            alt={`Feed for ${cam.camera_id}`}
            className="w-full h-full object-contain"
            decoding="sync"
            loading="eager"
          />
        ) : (
          <div className="text-center p-8 text-slate-500 flex flex-col items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3"></div>
            <p className="text-xs font-mono text-slate-400">Connecting to {cam.camera_id} video stream...</p>
            <p className="text-[11px] text-slate-600 mt-1">Acquiring video packets & initializing AI inference</p>
          </div>
        )}

        {/* HUD Sector Watermark */}
        <div className="absolute top-3 left-3 pointer-events-none flex flex-col gap-1">
          <div className="bg-black/75 backdrop-blur-sm text-slate-200 text-[10px] font-mono px-2 py-0.5 rounded border border-white/10 flex items-center gap-1.5">
            {isPhone ? (
              <Smartphone className="w-3 h-3 text-cyan-400" />
            ) : (
              <Shield className="w-3 h-3 text-blue-400" />
            )}
            <span>SECTOR: {cam.location}</span>
          </div>
        </div>
      </div>
    </div>
  );
});
