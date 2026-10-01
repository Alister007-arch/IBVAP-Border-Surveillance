import { useState, useEffect, useCallback, useRef } from "react";
import StatusStrip from "./components/StatusStrip";
import CameraGrid from "./components/CameraGrid";
import AlertFeed from "./components/AlertFeed";
import AddCameraModal from "./components/AddCameraModal";
import EventLogModal from "./components/EventLogModal";
import WatchlistModal from "./components/WatchlistModal";
import TacticalGISRadarModal from "./components/TacticalGISRadarModal";
import ForensicDossierModal from "./components/ForensicDossierModal";
import TacticalVoiceAssistant from "./components/TacticalVoiceAssistant";
import { useSystemWebSocket } from "./hooks/useSystemWebSocket";
import { useAlarmBeep } from "./hooks/useAlarmBeep";

// Centralized API Base URL configuration with strict URL guards
const getApiBaseUrl = () => {
  const rawApiUrl = import.meta.env.VITE_API_BASE_URL;
  if (
    rawApiUrl &&
    typeof rawApiUrl === "string" &&
    rawApiUrl.trim().startsWith("http") &&
    !rawApiUrl.includes("onrender.com")
  ) {
    return rawApiUrl.trim().replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location && window.location.origin) {
    return window.location.origin;
  }
  return "http://localhost:8000";
};

const API_BASE_URL = getApiBaseUrl();

/**
 * IBVAP Root Dashboard Component.
 * Intelligent Border Video Analytics Platform (SIH26187 / BSF / MHA).
 */
export default function App() {
  const { beep, toggleMute } = useAlarmBeep();
  const [muted, setMuted] = useState(false);

  // Latest non-system alert priority for the threat dot indicator
  const [latestAlertPriority, setLatestAlertPriority] = useState(null);
  const latestPriorityTimerRef = useRef(null);

  const handleNewAlert = useCallback((alert) => {
    const p = alert.priority;
    const cat = (alert.category || "").toLowerCase();
    const desc = (alert.description || "").toLowerCase();

    // Specific verified threat conditions: Human, Weapon (knife/gun/blade), Infiltration
    const isWeaponThreat =
      cat === "weapon" ||
      /weapon|knife|blade|gun|pistol|rifle|firearm/i.test(desc) ||
      (alert.bboxes && alert.bboxes.some((b) => /weapon|knife|gun/i.test(b.category || "") || /weapon|knife|gun/i.test(b.sub_category || "")));

    const isInfiltration =
      cat === "infiltration" ||
      cat === "intrusion" ||
      alert.is_crossing === true ||
      /infiltration|breach|boundary line|tripwire|perimeter incursion/i.test(desc);

    const isHumanThreat =
      cat === "person" ||
      cat === "face recognition" ||
      /human|person|suspect|intruder|pedestrian|infiltrator|watchlist|frs/i.test(desc) ||
      (alert.bboxes && alert.bboxes.some((b) => b.category === "Person" || b.class_name === "person"));

    const isAirThreat =
      cat === "drone" ||
      /drone|uav|air threat|aerial|airspace|low-flying/i.test(desc) ||
      (alert.bboxes && alert.bboxes.some((b) => /drone/i.test(b.category || "") || /drone/i.test(b.sub_category || "")));

    // ONLY BEEP if a human, weapon, knife, infiltration, or drone/air threat is actively detected!
    // When no one is here or alert is low-level informational / background vehicle, DO NOT BEEP!
    const shouldBeep = (isWeaponThreat || isInfiltration || isHumanThreat || isAirThreat) && (p === "RED" || p === "AMBER");

    if (shouldBeep) {
      beep(p);
    }

    if (p === "RED" || p === "AMBER" || p === "BLUE") {
      setLatestAlertPriority(p);
      // Clear the dot highlight after a few seconds so it resets when quiet
      if (latestPriorityTimerRef.current) clearTimeout(latestPriorityTimerRef.current);
      latestPriorityTimerRef.current = setTimeout(() => setLatestAlertPriority(null), 4000);
    }
  }, [beep]);

  const {
    connected,
    status,
    alerts,
    setAlerts,
    cameraFrames,
    cameraList,
    refreshCameras,
    systemRunning,
    setSystemRunning,
  } = useSystemWebSocket({ onNewAlert: handleNewAlert });

  const [mobileStreamUrl, setMobileStreamUrl] = useState(() => {
    if (typeof window !== "undefined" && window.location) {
      return `${window.location.origin}/phone_stream.html`;
    }
    return "http://localhost:8000/phone_stream.html";
  });

  const [isAddCameraOpen, setIsAddCameraOpen] = useState(false);
  const [isEventLogOpen, setIsEventLogOpen] = useState(false);
  const [isWatchlistOpen, setIsWatchlistOpen] = useState(false);
  const [isTacticalMapOpen, setIsTacticalMapOpen] = useState(false);
  const [isDossierOpen, setIsDossierOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [globalVisionMode, setGlobalVisionMode] = useState("OPTICAL");

  const handleVoiceSwitchTab = (tab) => {
    if (tab === "RADAR") setIsTacticalMapOpen(true);
    else if (tab === "DOSSIER") setIsDossierOpen(true);
    else if (tab === "WATCHLIST") setIsWatchlistOpen(true);
    else if (tab === "GRID") {
      setIsTacticalMapOpen(false);
      setIsDossierOpen(false);
      setIsWatchlistOpen(false);
    }
  };

  const handleVoiceDispatchQRF = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/sos/trigger-qrf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: "VOICE AI ACTIVATED: QRF Squad Dispatched" }),
      });
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    let cancelled = false;
    async function loadMobileStreamInfo() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/mobile-stream-info`);
        if (!res.ok) return;
        const text = await res.text();
        const info = text ? JSON.parse(text) : {};
        if (!cancelled) {
          // If accessing over non-localhost (tunnel or LAN), use current origin!
          if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
            setMobileStreamUrl(`${window.location.origin}/phone_stream.html`);
          } else if (info.https_url && info.https_url.startsWith("https://") && !info.https_url.includes(":8443")) {
            setMobileStreamUrl(info.https_url);
          } else if (info.lan_url) {
            setMobileStreamUrl(info.lan_url);
          } else if (info.direct_url) {
            setMobileStreamUrl(info.direct_url);
          }
        }
      } catch (err) {
        console.warn("Mobile stream info unavailable, using browser host fallback.", err);
      }
    }
    loadMobileStreamInfo();
    return () => { cancelled = true; };
  }, []);

  // ── System Controls ──────────────────────────────────────────────────

  const handleSystemStop = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/system/stop`, { method: "POST" });
      if (res.ok) setSystemRunning(false);
    } catch (err) { console.error("System stop failed:", err); }
  };

  const handleSystemStart = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/system/start`, { method: "POST" });
      if (res.ok) { setSystemRunning(true); refreshCameras(); }
    } catch (err) { console.error("System start failed:", err); }
  };

  const handleSystemReset = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/system/reset`, { method: "POST" });
      if (res.ok) {
        setAlerts([]);
        setSystemRunning(true);
        refreshCameras();
      }
    } catch (err) { console.error("System reset failed:", err); }
  };

  const handleToggleMute = () => {
    const nowMuted = toggleMute();
    setMuted(nowMuted);
  };

  // ── Camera Controls ──────────────────────────────────────────────────

  const handleQuickStartWebcam = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/cameras`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_id: "webcam_local_01",
          location: "Command Post (Integrated USB Webcam)",
          type: "webcam",
          source: "0",
          enabled: true,
        }),
      });
      if (res.ok) refreshCameras();
    } catch (err) { console.error("Failed to quick-start webcam:", err); }
  };

  const handleRemoveCamera = async (cameraId) => {
    if (window.confirm(`Remove camera '${cameraId}'?`)) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/cameras/${cameraId}`, { method: "DELETE" });
        if (res.ok) refreshCameras();
      } catch (err) { console.error("Failed to remove camera:", err); }
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-950 text-slate-100 select-none">
      {/* Top status strip */}
      <StatusStrip
        status={status}
        connected={connected}
        systemRunning={systemRunning}
        latestAlertPriority={latestAlertPriority}
        muted={muted}
        onToggleMute={handleToggleMute}
        onOpenAddCamera={() => setIsAddCameraOpen(true)}
        onOpenEventLog={() => setIsEventLogOpen(true)}
        onOpenWatchlist={() => setIsWatchlistOpen(true)}
        onOpenTacticalMap={() => setIsTacticalMapOpen(true)}
        onOpenDossier={() => setIsDossierOpen(true)}
        voiceAssistant={
          <TacticalVoiceAssistant
            onSwitchTab={handleVoiceSwitchTab}
            onToggleThermal={setGlobalVisionMode}
            onDispatchQRF={handleVoiceDispatchQRF}
            cameraList={cameraList}
            alerts={alerts}
          />
        }
        onSystemStart={handleSystemStart}
        onSystemStop={handleSystemStop}
        onSystemReset={handleSystemReset}
      />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Left sidebar: tactical alert feed */}
        {isSidebarOpen && (
          <div className="w-[26rem] xl:w-[28rem] flex-shrink-0 flex flex-col border-r border-slate-800 overflow-hidden shadow-xl z-10 transition-all">
            <AlertFeed alerts={alerts} />
          </div>
        )}

        {/* Sidebar Toggle Handle */}
        <button
          onClick={() => setIsSidebarOpen((prev) => !prev)}
          className="absolute z-20 left-0 top-1/2 -translate-y-1/2 bg-slate-800/90 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 rounded-r px-1 py-3 text-[10px] font-mono shadow-xl transition"
          style={isSidebarOpen ? { left: "calc(26rem - 1px)" } : { left: "0px" }}
          title={isSidebarOpen ? "Collapse Tactical Alert Feed" : "Expand Tactical Alert Feed"}
        >
          {isSidebarOpen ? "◀" : "▶"}
        </button>

        {/* Main area: camera grid */}
        <div className="flex-1 overflow-auto p-3 bg-slate-950/60">
          <CameraGrid
            cameras={cameraList}
            cameraFrames={cameraFrames}
            mobileStreamUrl={mobileStreamUrl}
            onOpenAddCamera={() => setIsAddCameraOpen(true)}
            onRemoveCamera={handleRemoveCamera}
            onQuickStartWebcam={handleQuickStartWebcam}
            globalVisionMode={globalVisionMode}
          />
        </div>
      </div>

      {/* Modals */}
      <AddCameraModal
        isOpen={isAddCameraOpen}
        onClose={() => setIsAddCameraOpen(false)}
        onCameraAdded={refreshCameras}
      />
      <EventLogModal
        isOpen={isEventLogOpen}
        onClose={() => setIsEventLogOpen(false)}
      />
      <WatchlistModal
        isOpen={isWatchlistOpen}
        onClose={() => setIsWatchlistOpen(false)}
      />
      <TacticalGISRadarModal
        isOpen={isTacticalMapOpen}
        onClose={() => setIsTacticalMapOpen(false)}
        alerts={alerts}
        cameras={cameraList}
      />
      <ForensicDossierModal
        isOpen={isDossierOpen}
        onClose={() => setIsDossierOpen(false)}
        alerts={alerts}
      />
    </div>
  );
}
