import React, { useState } from 'react';
import {
  Video,
  X,
  Plus,
  Radio,
  Server,
  Shield,
  AlertTriangle,
  Smartphone,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  Info,
} from 'lucide-react';

const getApiBaseUrl = () => {
  const rawApiUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (
    rawApiUrl &&
    typeof rawApiUrl === 'string' &&
    rawApiUrl.trim().startsWith('http') &&
    !rawApiUrl.includes('onrender.com')
  ) {
    return rawApiUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin;
  }
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

export default function AddCameraModal({ isOpen, onClose, onCameraAdded }) {
  const [sourceType, setSourceType] = useState('phone');
  const [cameraId, setCameraId] = useState('');
  const [location, setLocation] = useState('');
  const [sourceVal, setSourceVal] = useState('rtsp://192.168.1.100:554/stream1');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const phoneStreamUrl = `${API_BASE_URL}/phone_stream.html`;

  const copyPhoneUrl = () => {
    navigator.clipboard.writeText(phoneStreamUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleSourceTypeChange = (type) => {
    setSourceType(type);
    setError(null);
    if (type === 'webcam') {
      setSourceVal('0');
    } else if (type === 'rtsp') {
      setSourceVal('rtsp://192.168.1.100:554/stream1');
    } else if (type === 'ipwebcam') {
      setSourceVal('http://192.168.1.50:8080/video');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // If phone type, guide user rather than error
    if (sourceType === 'phone') {
      window.open(phoneStreamUrl, '_blank');
      onClose();
      return;
    }

    if (sourceType === 'webcam' && (sourceVal === '0' || sourceVal === '1')) {
      if (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com')) {
        setError(
          'Local USB devices (index 0/1) cannot be accessed directly by the cloud server. Please use the Mobile Phone Stream or IP Camera feed.'
        );
        return;
      }
    }

    if (sourceVal.includes('phone_stream.html')) {
      setError(
        'phone_stream.html is the mobile streamer webpage, not a raw RTSP feed. Use the "Mobile Phone" tab above to stream from your phone!'
      );
      return;
    }

    setLoading(true);

    const cleanId = (
      cameraId.trim() || `cam_${Date.now().toString().slice(-4)}`
    )
      .replace(/\s+/g, '_')
      .toLowerCase();
    const cleanLoc = location.trim() || `Border Post (${cleanId})`;

    let typeStr = 'webcam';
    if (sourceType === 'rtsp' || sourceType === 'ipwebcam') typeStr = 'ip_camera';

    const payload = {
      camera_id: cleanId,
      location: cleanLoc,
      source: sourceVal.trim(),
      type: typeStr,
      enabled: true,
    };

    try {
      const res = await fetch(`${API_BASE_URL}/api/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const contentType = res.headers.get('content-type');
      if (res.ok && contentType && contentType.includes('application/json')) {
        onCameraAdded && onCameraAdded();
        onClose();
      } else if (!res.ok) {
        let errorMsg = `Server error (${res.status})`;
        if (contentType && contentType.includes('application/json')) {
          const data = await res.json();
          errorMsg = data.detail || errorMsg;
        }
        throw new Error(errorMsg);
      } else {
        throw new Error('Backend returned non-JSON response.');
      }
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? `Unable to reach API server at ${API_BASE_URL}. Verify backend status.`
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="bg-slate-950 px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-blue-600/20 border border-blue-500 p-2 rounded-lg text-blue-400">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Ingest Surveillance Camera
              </h3>
              <p className="text-[11px] text-slate-400">
                Connect mobile phone patrol, IP CCTV, RTSP feed, or USB camera
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Source Type Selector Tabs */}
        <div className="p-5 pb-2">
          <label className="text-xs font-semibold text-slate-300 block mb-2">
            Select Ingestion Method:
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <button
              type="button"
              onClick={() => handleSourceTypeChange('phone')}
              className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition ${
                sourceType === 'phone'
                  ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300 shadow-md shadow-cyan-950/50'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Smartphone className="w-4 h-4 text-cyan-400" /> Phone Camera
              </span>
              <span className="text-[10px] text-slate-400">
                Browser stream (Zero app)
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleSourceTypeChange('rtsp')}
              className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition ${
                sourceType === 'rtsp'
                  ? 'bg-blue-950/60 border-blue-500 text-blue-300 shadow-md shadow-blue-950/50'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Server className="w-4 h-4 text-blue-400" /> CCTV (RTSP)
              </span>
              <span className="text-[10px] text-slate-400">
                IP camera feed
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleSourceTypeChange('ipwebcam')}
              className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition ${
                sourceType === 'ipwebcam'
                  ? 'bg-blue-950/60 border-blue-500 text-blue-300 shadow-md shadow-blue-950/50'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Radio className="w-4 h-4 text-indigo-400" /> IP Webcam App
              </span>
              <span className="text-[10px] text-slate-400">
                MJPEG URL
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleSourceTypeChange('webcam')}
              className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition ${
                sourceType === 'webcam'
                  ? 'bg-blue-950/60 border-blue-500 text-blue-300 shadow-md shadow-blue-950/50'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Video className="w-4 h-4 text-amber-400" /> USB Hardware
              </span>
              <span className="text-[10px] text-slate-400">
                Direct device index
              </span>
            </button>
          </div>
        </div>

        {/* Modal Body */}
        {sourceType === 'phone' ? (
          /* Dedicated Phone Streamer View */
          <div className="p-5 pt-2 flex flex-col gap-4">
            <div className="bg-cyan-950/40 border border-cyan-800/60 rounded-xl p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2 text-cyan-300 font-bold text-xs">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Connect Multiple Phones Directly — No App Needed!</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Open this streamer link on any smartphone (Android or iOS) connected to WiFi or Mobile Data. Each connected phone streams directly into the tactical surveillance grid with full AI object detection, intrusion alerts, and facial recognition.
              </p>

              {/* URL Box */}
              <div className="flex items-center gap-2 bg-slate-950 border border-cyan-700/50 rounded-lg p-2">
                <input
                  type="text"
                  readOnly
                  value={phoneStreamUrl}
                  className="bg-transparent text-xs text-cyan-300 font-mono flex-1 outline-none select-all"
                />
                <button
                  type="button"
                  onClick={copyPhoneUrl}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md flex items-center gap-1.5 transition ${
                    copied
                      ? 'bg-emerald-600 text-white'
                      : 'bg-cyan-600 hover:bg-cyan-500 text-white'
                  }`}
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" /> Copy Link
                    </>
                  )}
                </button>
              </div>

              {/* Instructions */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-[11px] text-slate-300">
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5">
                  <span className="font-bold text-cyan-400 block mb-1">1. Open Link</span>
                  Open on 1 or more phones via Chrome, Safari, or Brave.
                </div>
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5">
                  <span className="font-bold text-cyan-400 block mb-1">2. Pick Unit</span>
                  Select Patrol 1, Patrol 2, or type a custom unit codename.
                </div>
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5">
                  <span className="font-bold text-cyan-400 block mb-1">3. Stream Live</span>
                  Tap "Start Patrol Stream". The live feed instantly appears on the grid!
                </div>
              </div>
            </div>

            {/* Test Simulation Tip */}
            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 flex items-start gap-2.5 text-xs text-slate-400">
              <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <span>
                Want to test multiple phone feeds right from this computer? Open the link in a new browser tab and click <strong>"Simulate Stream"</strong> to generate live moving patrol targets.
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
              >
                Close
              </button>
              <div className="flex items-center gap-2">
                <a
                  href={phoneStreamUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition flex items-center gap-1.5 shadow-lg shadow-cyan-600/30"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Launch Streamer (New Tab)
                </a>
              </div>
            </div>
          </div>
        ) : (
          /* Form for IP Camera / RTSP / Webcam */
          <form onSubmit={handleSubmit} className="p-5 pt-2 flex flex-col gap-4">
            {error && (
              <div className="bg-rose-950/60 border border-rose-700 p-3 rounded-lg text-xs text-rose-300 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Camera ID */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">
                Camera ID / Codename:
              </label>
              <input
                type="text"
                placeholder="e.g., bop_north_01, checkpost_alpha"
                value={cameraId}
                onChange={(e) => setCameraId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Location */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">
                Border Location / Sector:
              </label>
              <input
                type="text"
                placeholder="e.g., Border Out Post Alpha - Sector 7"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Source Value Input */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">
                {sourceType === 'webcam'
                  ? 'Webcam Device Index (e.g., 0 for default USB camera):'
                  : sourceType === 'ipwebcam'
                  ? 'IP Webcam App MJPEG Stream URL:'
                  : 'CCTV RTSP Network Stream URL:'}
              </label>
              <input
                type="text"
                value={sourceVal}
                onChange={(e) => setSourceVal(e.target.value)}
                placeholder={
                  sourceType === 'webcam'
                    ? '0'
                    : sourceType === 'ipwebcam'
                    ? 'http://192.168.1.50:8080/video'
                    : 'rtsp://user:pass@192.168.1.100:554/stream1'
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-blue-500"
                required
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                {sourceType === 'ipwebcam'
                  ? 'Tip: In the Android "IP Webcam" app, tap "Start Server" and use the URL ending with /video.'
                  : sourceType === 'rtsp'
                  ? 'Supports RTSP, H.264, and MJPEG security camera streams.'
                  : 'USB camera connected to the server host machine.'}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center gap-1.5 shadow-lg shadow-blue-600/30 disabled:opacity-50"
              >
                {loading ? (
                  <>Connecting...</>
                ) : (
                  <>
                    <Plus className="w-4 h-4" /> Start Ingestion
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
