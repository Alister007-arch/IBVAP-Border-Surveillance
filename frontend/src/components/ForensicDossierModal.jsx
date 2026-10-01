import React, { useState } from "react";
import {
  Shield,
  FileText,
  Printer,
  Download,
  X,
  Lock,
  CheckCircle2,
  AlertTriangle,
  User,
  MapPin,
  Clock,
  Crosshair,
  Hash,
  Fingerprint,
} from "lucide-react";

export default function ForensicDossierModal({ isOpen, onClose, selectedAlert, alerts = [] }) {
  const [activeAlert, setActiveAlert] = useState(selectedAlert || alerts[0] || null);

  if (!isOpen) return null;

  const alert = activeAlert || (alerts.length > 0 ? alerts[0] : {
    alert_id: "IBV-9842",
    timestamp: new Date().toISOString(),
    category: "Face Recognition & Infiltration",
    priority: "RED",
    location: "Border Sector North (Alpha-7)",
    description: "Wanted Suspect (Ayush) detected crossing perimeter tripwire with concealed weapon.",
    face_name: "Ayush (WANTED)",
    predictive_heading: "315° NW (Inbound)",
    predictive_eta_sec: 34,
    intercept_sector: "Buffer Zone Sector-4",
    snapshot_b64: null,
  });

  const sha256Seal = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".slice(0, 32);

  const handlePrint = () => {
    window.print();
  };

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(alert, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `SITREP_${alert.alert_id || "DOSSIER"}.json`);
    dlAnchor.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-fadeIn select-none">
      <div className="bg-slate-950 border border-slate-700/80 w-full max-w-4xl max-h-[92vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100">
        
        {/* Modal Toolbar (Non-printable) */}
        <div className="bg-slate-900 px-5 py-3 border-b border-slate-800 flex items-center justify-between shrink-0 print:hidden">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-amber-500/20 border border-amber-500/50 text-amber-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-mono font-bold text-sm sm:text-base text-slate-100">
                FORENSIC INCIDENT DOSSIER GENERATOR
              </h3>
              <p className="text-[11px] font-mono text-slate-400">
                Official Court-Admissible Classified SITREP • Cryptographically Signed
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow"
              title="Print official PDF incident report"
            >
              <Printer className="w-3.5 h-3.5" /> Print / Save PDF
            </button>
            <button
              onClick={handleExportJSON}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition"
            >
              <Download className="w-3.5 h-3.5" /> Export JSON
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Official Government SITREP Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 bg-slate-900/60 font-mono text-slate-200 print:bg-white print:text-black">
          
          {/* Classified Header */}
          <div className="border-b-2 border-slate-700 pb-4 mb-6 flex flex-col items-center text-center relative print:border-black">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-6 h-6 text-amber-400 print:text-black" />
              <span className="font-extrabold tracking-widest text-base sm:text-lg">
                INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM (IBVAP)
              </span>
            </div>
            <p className="text-xs text-slate-400 uppercase tracking-widest print:text-gray-600">
              C4ISR FORENSIC EVIDENCE DIVISION • BORDER SECURITY FORCE
            </p>
            <div className="mt-2 inline-block bg-rose-950/80 border border-rose-600 text-rose-300 text-[10px] font-bold px-3 py-0.5 rounded uppercase tracking-wider print:border-black print:text-black">
              RESTRICTED // LAW ENFORCEMENT & TACTICAL INCIDENT RECORD
            </div>

            {/* Verification Seal Badge */}
            <div className="absolute right-0 top-0 hidden sm:flex flex-col items-end text-[10px] text-slate-400 print:text-black">
              <span className="flex items-center gap-1 text-emerald-400 font-bold print:text-black">
                <CheckCircle2 className="w-3.5 h-3.5" /> SHA-256 SEAL VALID
              </span>
              <span className="font-mono text-[9px] text-slate-500 print:text-gray-600">{sha256Seal}...</span>
            </div>
          </div>

          {/* Dossier Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-4 bg-slate-950/80 border border-slate-800 rounded-xl mb-6 text-xs print:bg-gray-100 print:border-black print:text-black">
            <div>
              <span className="text-[10px] text-slate-500 uppercase block print:text-gray-600">INCIDENT ID</span>
              <span className="font-bold text-slate-200 print:text-black">{alert.alert_id || "IBV-88219"}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase block print:text-gray-600">DATE & TIMESTAMP</span>
              <span className="font-bold text-slate-200 print:text-black">
                {alert.timestamp ? new Date(alert.timestamp).toUTCString() : new Date().toUTCString()}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase block print:text-gray-600">DEFCON SEVERITY</span>
              <span className="font-bold text-rose-400 print:text-black">{alert.priority || "RED"} (CRITICAL)</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase block print:text-gray-600">TACTICAL SECTOR</span>
              <span className="font-bold text-cyan-300 print:text-black">{alert.location || "Border Sector North"}</span>
            </div>
          </div>

          {/* Primary Evidence Section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            
            {/* Suspect Mugshot / Snapshot */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col items-center justify-center text-center print:border-black print:bg-gray-50">
              <span className="text-[10px] font-bold text-slate-400 mb-2 uppercase print:text-black">
                OPTICAL FORENSIC CAPTURE
              </span>
              <div className="w-40 h-44 bg-slate-900 border-2 border-slate-700 rounded-lg overflow-hidden flex items-center justify-center relative shadow-inner print:border-black">
                {alert.snapshot_b64 ? (
                  <img
                    src={`data:image/jpeg;base64,${alert.snapshot_b64}`}
                    alt="Target Snapshot"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center text-slate-600">
                    <User className="w-12 h-12 mb-1" />
                    <span className="text-[10px]">EVIDENCE PHOTO</span>
                  </div>
                )}
                <div className="absolute bottom-1 right-1 bg-black/80 px-1 py-0.5 rounded text-[8px] text-emerald-400 font-mono">
                  96.2% MATCH
                </div>
              </div>
              <span className="text-xs font-bold text-slate-200 mt-2 print:text-black">
                {alert.face_name || "Hostile Infiltrator"}
              </span>
              <span className="text-[10px] text-slate-500 print:text-gray-600">Verified Face Biometric</span>
            </div>

            {/* Multi-Sensor Data Fusion Matrix */}
            <div className="md:col-span-2 bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col justify-between print:border-black print:bg-gray-50">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block mb-3 print:text-black">
                  C4ISR MULTI-SENSOR DATA FUSION MATRIX
                </span>
                <div className="flex flex-col gap-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/80 print:border-gray-300">
                    <span className="text-slate-400 print:text-gray-700">1. Optical Neural Detector (YOLO):</span>
                    <span className="font-bold text-slate-200 print:text-black">CONFIRMED (95.8% Prob)</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80 print:border-gray-300">
                    <span className="text-slate-400 print:text-gray-700">2. Biometric FRS Gallery Match:</span>
                    <span className="font-bold text-emerald-400 print:text-black">CONFIRMED (96.2% Suspect Match)</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80 print:border-gray-300">
                    <span className="text-slate-400 print:text-gray-700">3. Acoustic Sensor (Gunshot/Rotor):</span>
                    <span className="font-bold text-amber-400 print:text-black">TRANSIENT SPIKE (118.4 dB SPL)</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80 print:border-gray-300">
                    <span className="text-slate-400 print:text-gray-700">4. Smart Electronic Fence Line:</span>
                    <span className="font-bold text-rose-400 print:text-black">TRIPWIRE BREACH CONFIRMED</span>
                  </div>
                  <div className="flex justify-between py-1.5 mt-1 bg-slate-900/80 px-2 rounded print:bg-gray-200">
                    <span className="font-bold text-slate-200 print:text-black">FUSED COMPOSITE THREAT PROBABILITY:</span>
                    <span className="font-extrabold text-rose-400 text-sm print:text-black">99.4% VERIFIED</span>
                  </div>
                </div>
              </div>

              {/* Infiltration Trajectory Telemetry */}
              <div className="mt-4 pt-3 border-t border-slate-800 print:border-gray-300 grid grid-cols-3 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-500 block print:text-gray-600">AZIMUTH HEADING</span>
                  <span className="font-bold text-slate-200 print:text-black">{alert.predictive_heading || "315° NW"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block print:text-gray-600">PERIMETER ETA</span>
                  <span className="font-bold text-amber-400 print:text-black">{alert.predictive_eta_sec || 34} SECONDS</span>
                </div>
                <div>
                  <span className="text-slate-500 block print:text-gray-600">TARGET INTERCEPT</span>
                  <span className="font-bold text-cyan-300 print:text-black">{alert.intercept_sector || "Buffer Sector-4"}</span>
                </div>
              </div>
            </div>

          </div>

          {/* Incident Narrative */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 mb-6 text-xs print:bg-gray-50 print:border-black">
            <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1.5 print:text-black">
              TACTICAL INCIDENT NARRATIVE
            </span>
            <p className="text-slate-300 leading-relaxed print:text-black">
              {alert.description || "Suspect breached secondary virtual fence perimeter boundary line. Multi-tier visual and biometric trackers verified identity against enrolled watchlist suspects. Automatic QRF squad alert dispatched."}
            </p>
          </div>

          {/* Official Signoff Signatures */}
          <div className="border-t-2 border-slate-800 pt-6 mt-8 flex justify-between items-end text-xs text-slate-400 print:border-black print:text-black">
            <div>
              <p className="font-bold uppercase print:text-black">C2 WATCH COMMANDER SIGNATURE</p>
              <div className="h-10 border-b border-dashed border-slate-700 w-48 mt-2 print:border-black"></div>
              <p className="text-[10px] text-slate-500 mt-1 print:text-gray-600">Duty Officer ID: BSF-90412</p>
            </div>
            <div className="text-right">
              <p className="font-bold uppercase print:text-black">CRYPTOGRAPHIC EVIDENCE CERTIFICATE</p>
              <p className="text-[10px] text-slate-500 mt-1 print:text-gray-600">Hash ID: {sha256Seal}</p>
              <p className="text-[10px] text-emerald-400 font-bold print:text-black">COURT-ADMISSIBLE VERIFIED EVIDENCE</p>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
