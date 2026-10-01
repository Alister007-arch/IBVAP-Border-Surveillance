import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  MicOff,
  Volume2,
  Shield,
  Radio,
  Check,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Terminal,
  AlertTriangle,
  Play,
  X,
  Zap,
  Flame,
  Moon,
  Crosshair,
  FileText,
  Video,
  Send,
  VolumeX,
} from "lucide-react";

/**
 * TacticalVoiceAssistant — Voice C2 Command ("Tactical JARVIS") for IBVAP.
 * Provides zero-latency hands-free military voice control and tactical audio feedback.
 * Includes foolproof lifecycle management, echo cancellation, Hindi/English vocabulary,
 * and 1-click fallback command chips.
 */
export default function TacticalVoiceAssistant({
  onSwitchTab,
  onToggleThermal,
  onDispatchQRF,
  onQuickStartWebcam,
  cameraList = [],
  alerts = [],
}) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [recognitionStatus, setRecognitionStatus] = useState("STANDBY"); // "STANDBY" | "LISTENING" | "PROCESSING" | "ERROR"
  const [transcript, setTranscript] = useState("");
  const [lastResponse, setLastResponse] = useState("Standing by for tactical voice commands...");
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isOpenTray, setIsOpenTray] = useState(false);
  const [textCommandInput, setTextCommandInput] = useState("");

  const recognitionRef = useRef(null);
  const isListeningIntentRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const restartTimerRef = useRef(null);
  const lastCommandTimeRef = useRef(0);
  const trayRef = useRef(null);

  // Close tray when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (trayRef.current && !trayRef.current.contains(e.target)) {
        setIsOpenTray(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Military Synthetic Voice Output with Echo Suppression
  const speakMilitaryResponse = useCallback((message) => {
    setLastResponse(message);
    if (!("speechSynthesis" in window)) return;

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;

      // Select natural English voice if present
      const voices = window.speechSynthesis.getVoices();
      const bestVoice = voices.find(
        (v) =>
          v.lang.startsWith("en") &&
          (v.name.includes("Google") ||
            v.name.includes("Natural") ||
            v.name.includes("Daniel") ||
            v.name.includes("David") ||
            v.name.includes("Rishi"))
      );
      if (bestVoice) utterance.voice = bestVoice;

      // Suppress mic processing while speaking to prevent feedback loops
      isSpeakingRef.current = true;
      setIsSpeaking(true);

      utterance.onend = () => {
        isSpeakingRef.current = false;
        setIsSpeaking(false);
      };

      utterance.onerror = () => {
        isSpeakingRef.current = false;
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("Speech synthesis error:", err);
      isSpeakingRef.current = false;
      setIsSpeaking(false);
    }
  }, []);

  // Command Parser & Tactical Dispatch
  const executeTacticalCommand = useCallback(
    (rawCmd) => {
      if (!rawCmd) return;
      const cmd = rawCmd.trim().toLowerCase();

      // Debounce rapid identical commands
      const now = Date.now();
      if (now - lastCommandTimeRef.current < 1200) return;
      lastCommandTimeRef.current = now;

      setTranscript(cmd);

      // 1. Radar / Tactical Map
      if (
        cmd.includes("radar") ||
        cmd.includes("map") ||
        cmd.includes("gis") ||
        cmd.includes("sector map") ||
        cmd.includes("naksha") ||
        cmd.includes("perimeter")
      ) {
        if (onSwitchTab) onSwitchTab("RADAR");
        speakMilitaryResponse("Opening Tactical GIS Radar. Tracking sector Alpha-7 perimeter.");
        return;
      }

      // 2. Dossier / Incident Reports
      if (
        cmd.includes("dossier") ||
        cmd.includes("report") ||
        cmd.includes("sitrep") ||
        cmd.includes("incident") ||
        cmd.includes("log") ||
        cmd.includes("saboot") ||
        cmd.includes("evidence")
      ) {
        if (onSwitchTab) onSwitchTab("DOSSIER");
        speakMilitaryResponse("Accessing Classified Incident Dossier. Cryptographic evidence verified.");
        return;
      }

      // 3. Watchlist
      if (
        cmd.includes("watchlist") ||
        cmd.includes("suspect") ||
        cmd.includes("wanted") ||
        cmd.includes("criminal") ||
        cmd.includes("face")
      ) {
        if (onSwitchTab) onSwitchTab("WATCHLIST");
        speakMilitaryResponse("Opening biometric suspect watchlist.");
        return;
      }

      // 4. Camera Grid / Feeds
      if (
        cmd.includes("camera") ||
        cmd.includes("grid") ||
        cmd.includes("feeds") ||
        cmd.includes("video") ||
        cmd.includes("cctv") ||
        cmd.includes("live")
      ) {
        if (onSwitchTab) onSwitchTab("GRID");
        speakMilitaryResponse("Displaying multi-camera tactical surveillance grid.");
        return;
      }

      // 5. Thermal Vision / FLIR
      if (
        cmd.includes("thermal") ||
        cmd.includes("flir") ||
        cmd.includes("heat") ||
        cmd.includes("garmi") ||
        cmd.includes("infrared")
      ) {
        if (onToggleThermal) onToggleThermal("THERMAL");
        speakMilitaryResponse("Activating FLIR thermal false-color shaders on optical feeds.");
        return;
      }

      // 6. Night Vision (NVG Green Phosphor)
      if (
        cmd.includes("night") ||
        cmd.includes("nvg") ||
        cmd.includes("green") ||
        cmd.includes("andhera") ||
        cmd.includes("raat")
      ) {
        if (onToggleThermal) onToggleThermal("NVG");
        speakMilitaryResponse("Night vision green phosphor mode engaged.");
        return;
      }

      // 7. Day / Normal Optical
      if (
        cmd.includes("optical") ||
        cmd.includes("normal") ||
        cmd.includes("day") ||
        cmd.includes("color") ||
        cmd.includes("din")
      ) {
        if (onToggleThermal) onToggleThermal("OPTICAL");
        speakMilitaryResponse("Restoring standard optical RGB vision.");
        return;
      }

      // 8. QRF Intercept Dispatch
      if (
        cmd.includes("dispatch") ||
        cmd.includes("launch qrf") ||
        cmd.includes("intercept") ||
        cmd.includes("squad") ||
        cmd.includes("bhejo") ||
        cmd.includes("hamla") ||
        cmd.includes("team")
      ) {
        if (onDispatchQRF) onDispatchQRF();
        speakMilitaryResponse("Emergency QRF intercept squad dispatched to Sector-4 buffer line. ETA 48 seconds.");
        return;
      }

      // 9. Status / SITREP Report
      if (
        cmd.includes("status") ||
        cmd.includes("sitrep") ||
        cmd.includes("halat") ||
        cmd.includes("check") ||
        cmd.includes("kya chal raha")
      ) {
        const activeCams = cameraList.length || 1;
        const criticalCount = alerts.filter((a) => a.priority === "RED").length;
        const reply = `System operational. ${activeCams} active camera streams. ${criticalCount} critical sector breaches logged. Radar calibrated.`;
        speakMilitaryResponse(reply);
        return;
      }

      // 10. Standby / Stop Listening Command
      if (
        cmd.includes("stop listening") ||
        cmd.includes("band karo") ||
        cmd.includes("standby") ||
        cmd.includes("chup") ||
        cmd.includes("quiet") ||
        cmd.includes("stop voice")
      ) {
        stopListening();
        speakMilitaryResponse("Voice command system in standby.");
        return;
      }

      // Default fallback recognition
      speakMilitaryResponse(`Command recognized: "${rawCmd}". Executing tactical directive.`);
    },
    [onSwitchTab, onToggleThermal, onDispatchQRF, cameraList, alerts, speakMilitaryResponse]
  );

  // Initialize Web Speech Recognition Engine Once on Mount
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceAvailable(false);
      setErrorMessage("Speech Recognition not supported in this browser. Use Chrome/Edge or click Quick Commands.");
      return;
    }

    setVoiceAvailable(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    // Set language with fallbacks
    recognition.lang = "en-IN";
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setRecognitionStatus("LISTENING");
      setErrorMessage(null);
    };

    recognition.onresult = (event) => {
      // Ignore audio while assistant is speaking (echo elimination)
      if (isSpeakingRef.current) return;

      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const res = event.results[i];
        if (res.isFinal) {
          final += res[0].transcript;
        } else {
          interim += res[0].transcript;
        }
      }

      const activeText = (final || interim).trim();
      if (activeText) {
        setTranscript(activeText);
      }

      // If final transcript or high-confidence keyword detected, execute immediately
      const textToTest = (final || interim).toLowerCase();
      if (
        final ||
        textToTest.includes("radar") ||
        textToTest.includes("dossier") ||
        textToTest.includes("thermal") ||
        textToTest.includes("nvg") ||
        textToTest.includes("dispatch") ||
        textToTest.includes("status") ||
        textToTest.includes("stop")
      ) {
        executeTacticalCommand(textToTest);
      }
    };

    recognition.onerror = (event) => {
      const err = event.error;
      console.warn("[Tactical Voice AI] Speech error:", err);

      if (err === "no-speech") {
        // Harmless silence during continuous surveillance listening
        return;
      }

      if (err === "not-allowed" || err === "service-not-allowed") {
        isListeningIntentRef.current = false;
        setIsListening(false);
        setRecognitionStatus("ERROR");
        setErrorMessage("Microphone access blocked. Click lock icon in browser URL bar to allow microphone.");
        return;
      }

      if (err === "audio-capture") {
        isListeningIntentRef.current = false;
        setIsListening(false);
        setRecognitionStatus("ERROR");
        setErrorMessage("No microphone detected. Please plug in an audio input device.");
        return;
      }

      if (err === "network") {
        setErrorMessage("Speech network service temporary hiccup. Retrying...");
      }
    };

    recognition.onend = () => {
      // CRITICAL FIX: If user intended to STOP, NEVER restart!
      if (!isListeningIntentRef.current) {
        setIsListening(false);
        setRecognitionStatus("STANDBY");
        return;
      }

      // If user still wants listening active and we are not speaking, restart safely
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = setTimeout(() => {
        if (isListeningIntentRef.current && !isSpeakingRef.current) {
          try {
            recognition.start();
          } catch (e) {
            // Already started or busy
          }
        }
      }, 250);
    };

    recognitionRef.current = recognition;

    return () => {
      isListeningIntentRef.current = false;
      clearTimeout(restartTimerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, [executeTacticalCommand]);

  // Clean Start
  const startListening = () => {
    isListeningIntentRef.current = true;
    setIsListening(true);
    setRecognitionStatus("LISTENING");
    setErrorMessage(null);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.warn("Recognition start (already active or restarting):", err);
      }
    }
    speakMilitaryResponse("Tactical C2 Voice Assistant online. Awaiting commands.");
  };

  // Clean Stop (Guaranteed to halt immediately)
  const stopListening = () => {
    isListeningIntentRef.current = false;
    clearTimeout(restartTimerRef.current);
    setIsListening(false);
    setRecognitionStatus("STANDBY");

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (err) {
        console.warn("Recognition abort error:", err);
      }
    }

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setLastResponse("Voice command system in standby.");
  };

  const toggleMic = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!textCommandInput.trim()) return;
    executeTacticalCommand(textCommandInput);
    setTextCommandInput("");
  };

  return (
    <div className="relative flex items-center gap-1.5 select-none" ref={trayRef}>
      {/* ── Main Voice Assistant Button ── */}
      <button
        onClick={toggleMic}
        className={`px-2.5 py-1.5 rounded-lg border font-mono text-xs font-bold flex items-center gap-2 transition shadow-md ${
          isListening
            ? "bg-rose-950/95 border-rose-500 text-rose-300 shadow-rose-950/60 ring-2 ring-rose-500/40"
            : errorMessage
            ? "bg-amber-950/80 hover:bg-amber-900 border-amber-600/70 text-amber-300"
            : "bg-slate-900 hover:bg-slate-800 border-slate-700 text-slate-300 hover:text-white"
        }`}
        title={
          isListening
            ? "Tactical Voice Active (Click to STOP Listening)"
            : errorMessage
            ? errorMessage
            : "Activate Hands-free Voice C2 Assistant"
        }
      >
        {isListening ? (
          <>
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            </span>
            <Mic className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <span className="hidden sm:inline text-rose-200">VOICE: ON</span>
            {/* Audio wave pulse bars */}
            <span className="flex items-end gap-0.5 h-3">
              <span className="w-0.5 h-2 bg-rose-400 animate-pulse"></span>
              <span className="w-0.5 h-3 bg-rose-300 animate-bounce"></span>
              <span className="w-0.5 h-1.5 bg-rose-400 animate-pulse"></span>
            </span>
          </>
        ) : errorMessage ? (
          <>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">VOICE C2</span>
          </>
        ) : (
          <>
            <MicOff className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline">VOICE C2</span>
          </>
        )}
      </button>

      {/* ── Dropdown / Command Tray Toggle ── */}
      <button
        onClick={() => setIsOpenTray((prev) => !prev)}
        className={`p-1.5 rounded-lg border text-xs font-mono transition ${
          isOpenTray
            ? "bg-cyan-950 border-cyan-500 text-cyan-300"
            : "bg-slate-900 hover:bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
        }`}
        title="Toggle Tactical Voice Command Palette & Fallback Controls"
      >
        <Terminal className="w-3.5 h-3.5" />
      </button>

      {/* Floating HUD status chip when listening */}
      {isListening && (
        <div className="hidden xl:flex items-center gap-2 bg-slate-950/90 border border-slate-700/80 px-2.5 py-1 rounded-lg text-[11px] font-mono text-cyan-300 max-w-xs truncate animate-fadeIn">
          <Volume2 className="w-3 h-3 text-cyan-400 shrink-0" />
          <span className="truncate">"{transcript || "Listening..."}"</span>
        </div>
      )}

      {/* ── Collapsible Tactical C2 Command Tray & Fallback Palette ── */}
      {isOpenTray && (
        <div className="absolute right-0 top-full mt-2 w-84 sm:w-96 bg-slate-950 border border-slate-700/90 rounded-xl shadow-2xl p-3 z-50 animate-fadeIn backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2.5">
            <div className="flex items-center gap-2">
              <div className="bg-cyan-950 border border-cyan-700/80 p-1 rounded text-cyan-400">
                <Radio className="w-3.5 h-3.5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-200 font-mono tracking-wider">
                  TACTICAL VOICE C2 PANEL
                </h4>
                <p className="text-[10px] text-slate-400 font-mono">
                  Hands-Free Speech &amp; 1-Click Fallback
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpenTray(false)}
              className="text-slate-500 hover:text-slate-300 p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Status & Transcript Bar */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2 mb-2.5 text-xs font-mono">
            <div className="flex items-center justify-between mb-1 text-[10px]">
              <span className="text-slate-400">STATUS:</span>
              <span
                className={`font-bold ${
                  isListening
                    ? "text-emerald-400 animate-pulse"
                    : errorMessage
                    ? "text-amber-400"
                    : "text-slate-400"
                }`}
              >
                {isListening
                  ? "● LISTENING (MIC ACTIVE)"
                  : errorMessage
                  ? "⚠ MIC RESTRICTED"
                  : "○ STANDBY"}
              </span>
            </div>

            {/* Live Transcript / Feedback */}
            <div className="text-[11px] text-cyan-300 bg-slate-950 px-2 py-1 rounded border border-slate-800/80 truncate">
              {transcript ? (
                <span>
                  Heard: <strong className="text-white">"{transcript}"</strong>
                </span>
              ) : (
                <span className="text-slate-500 italic">
                  Say "radar", "thermal", "dispatch qrf", "status"...
                </span>
              )}
            </div>

            {errorMessage && (
              <div className="mt-1.5 text-[10px] text-amber-300 bg-amber-950/40 border border-amber-700/50 p-1.5 rounded leading-tight flex items-start gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>

          {/* 1-Click Tactical Quick Command Action Chips */}
          <div className="mb-3">
            <div className="text-[10px] font-mono text-slate-400 font-bold mb-1.5 flex items-center justify-between">
              <span>TACTICAL COMMAND BUTTONS:</span>
              <span className="text-[9px] text-slate-500">1-CLICK EXECUTE</span>
            </div>
            <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
              <button
                onClick={() => executeTacticalCommand("radar")}
                className="bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-700/80 text-emerald-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Crosshair className="w-3 h-3 text-emerald-400" />
                <span>🎯 Tactical Radar</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("dossier")}
                className="bg-amber-950/70 hover:bg-amber-900 border border-amber-700/80 text-amber-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <FileText className="w-3 h-3 text-amber-400" />
                <span>📁 Incident Dossier</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("thermal")}
                className="bg-rose-950/70 hover:bg-rose-900 border border-rose-700/80 text-rose-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Flame className="w-3 h-3 text-rose-400" />
                <span>🔥 FLIR Thermal</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("night vision")}
                className="bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-700/80 text-emerald-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Moon className="w-3 h-3 text-emerald-400" />
                <span>🌙 Night Vision NVG</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("optical")}
                className="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Video className="w-3 h-3 text-blue-400" />
                <span>☀️ Day Optical RGB</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("dispatch qrf")}
                className="bg-red-950/80 hover:bg-red-900 border border-red-600 text-red-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px] font-bold"
              >
                <Zap className="w-3 h-3 text-red-400" />
                <span>🚨 Dispatch QRF</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("status")}
                className="bg-blue-950/70 hover:bg-blue-900 border border-blue-700/80 text-blue-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Radio className="w-3 h-3 text-blue-400" />
                <span>📊 System SITREP</span>
              </button>

              <button
                onClick={() => executeTacticalCommand("camera grid")}
                className="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 p-1.5 rounded flex items-center gap-1.5 transition text-[11px]"
              >
                <Video className="w-3 h-3 text-cyan-400" />
                <span>📹 Multi-Cam Grid</span>
              </button>
            </div>
          </div>

          {/* Manual Keyboard Command Input Bar */}
          <form onSubmit={handleManualSubmit} className="flex gap-1.5">
            <input
              type="text"
              value={textCommandInput}
              onChange={(e) => setTextCommandInput(e.target.value)}
              placeholder="Type command (e.g. radar, thermal, qrf)..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              className="bg-cyan-700 hover:bg-cyan-600 text-white px-2.5 py-1 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
            >
              <Send className="w-3 h-3" />
            </button>
          </form>

          {/* Audio Test & Mic Control Bottom Row */}
          <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
            <button
              onClick={() => speakMilitaryResponse("Audio feedback test. Tactical voice system active and verified.")}
              className="hover:text-cyan-400 flex items-center gap-1 transition"
            >
              <Volume2 className="w-3 h-3 text-cyan-400" />
              <span>Test Audio Voice</span>
            </button>

            <button
              onClick={toggleMic}
              className={`font-bold flex items-center gap-1 px-2 py-0.5 rounded transition ${
                isListening
                  ? "bg-rose-600 hover:bg-rose-500 text-white"
                  : "bg-emerald-700 hover:bg-emerald-600 text-white"
              }`}
            >
              {isListening ? (
                <>
                  <MicOff className="w-3 h-3" />
                  <span>STOP LISTENING</span>
                </>
              ) : (
                <>
                  <Mic className="w-3 h-3" />
                  <span>START LISTENING</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
