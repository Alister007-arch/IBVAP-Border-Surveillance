# IBVAP — Intelligent Border Video Analytics Platform

**Problem Statement SIH26187 (Ministry of Home Affairs / Border Security Forces)**

An AI-driven software platform that transforms standard IP-based CCTV cameras at Border Out Posts (BOPs), check posts, and strategic perimeters into an intelligent surveillance network without requiring dedicated FRS, ANPR, or smart-camera hardware.

---

## Capabilities Overview

| Capability | Module | Status | Description |
|---|---|---|---|
| **Human Detection & Tracking** | `tier1_yolo.py` + `tracker.py` | ✅ Ready | Real-time person detection (YOLOv8) with persistent ByteTrack tracking and trajectory history. |
| **Vehicle Detection & Classification** | `tier1_yolo.py` | ✅ Ready | Detection and explicit classification (`Truck`, `Car`, `Bus`, `Motorcycle`, `Bicycle`) with visual badges. |
| **Face Detection & FRS** | `face_detector.py` | ✅ Ready | Software-based face localization + signature extraction; matches against BSF/MHA Suspect Watchlist. |
| **Automatic Number Plate Recognition (ANPR)** | `anpr.py` | ✅ Ready | Vehicle plate localization via aspect-ratio morphology + character extraction + BOLO watchlist checking. |
| **Virtual Fence Intrusion Detection** | `virtual_fence.py` | ✅ Ready | Configurable tripwires & polygonal exclusion corridors; triggers instant critical `RED` intrusion alerts. |
| **Suspicious Activity Detection** | `suspicious_activity.py` | ✅ Ready | Detects loitering (> 7s), rapid perimeter sprints / incursion runs, and abandoned / unattended luggage. |
| **Night-Time Movement Detection** | `night_switch.py` | ✅ Ready | Dynamic luminance tracking + CLAHE contrast boost + low-light movement alarms and thermal simulation. |
| **Real-Time Alerting & Event Logging** | `event_store.py` | ✅ Ready | Zero-latency WebSocket broadcast + persistent SQLite audit trail with forensic snapshots & CSV export. |
| **Dynamic Camera Management** | `engine.py` + `app.py` | ✅ Ready | Ingest live IP CCTV (RTSP/HTTP), USB border webcams, or mobile patrol phones without dummy video files. |
| **Cross-Platform Patrol Ingestion** | `phone_stream.html` | ✅ Ready | Mobile patrol units stream live camera via secure WebSocket directly to the surveillance engine. |

---

## Platform Architecture

```
Camera Feeds (IP CCTV / Webcam / Mobile Patrol)
   │
   ▼
Ingestion Layer (RTSP / OpenCV / WebSocket)
   │
   ▼
Night/Day Auto-Switch (Luminance + CLAHE Enhancement)
   │
   ▼
Detection Tier (YOLOv8 Multiclass + MOG2 Motion Catch-All)
   │
   ▼
Tracking Tier (ByteTrack Within-Camera Persistence)
   │
   ▼
IBVAP Threat Intelligence Suite:
   ├── Face Detection & FRS Matcher (Suspect Watchlist)
   ├── ANPR Engine (BOLO License Plates)
   ├── Virtual Fence & Tripwire Intrusion Analyzer
   ├── Suspicious Behavioral Detector (Loitering / Sprint / Abandoned)
   └── Night Movement Alarms
   │
   ▼
Persistent Event Store (SQLite DB + Forensic Snapshots)
   │
   ▼
Dual-Channel Broadcast (HTTP/HTTPS + WebSocket)
   │
   ▼
Command & Control Tactical Dashboard (React + Tailwind)
```
