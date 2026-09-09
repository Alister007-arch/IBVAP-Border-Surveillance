# Border Surveillance System — Setup & Execution Guide
### Smart India Hackathon Problem Statement SIH26187 (Ministry of Home Affairs)

An AI-based intelligent video analytics platform for border surveillance that runs on existing CCTV infrastructure.

---

## 1. Prerequisites

| Requirement | Recommendation |
|---|---|
| **Python** | Python 3.10 – 3.14 |
| **Node.js** | Node.js 18+ & npm |
| **Operating System** | Windows, Linux, or macOS |
| **Hardware** | 4GB RAM minimum (8GB+ recommended); CUDA GPU optional |

---

## 2. Quick Start: Full System Execution

### Option A: Run Full System (Backend + Live React Dashboard)

The FastAPI server automatically serves the compiled production React dashboard at `http://localhost:8000`:

```bash
# 1. Start the backend & surveillance engine
python backend/run_server.py
```

Then open your browser and navigate to:
👉 **`http://localhost:8000`**

You will see:
- **Top Status Strip**: Engine link status, camera online counters, active alerts, last sync time.
- **Camera Network Panel**: Live status, camera IDs, locations, and type badges.
- **Live Camera Grid**: Live annotated streams with bounding boxes, day/night CLAHE badges, and boundary lines.
- **Live Alert Feed**: Real-time prioritized alerts (RED = Boundary Crossing, AMBER = Group/Track, GRAY = Unidentified Motion).

---

### Option B: Frontend Development Mode (Vite Hot-Reload)

To run the React frontend in development mode with hot-reloading:

```bash
# Terminal 1: Start Backend
python backend/run_server.py

# Terminal 2: Start Vite Dev Server
cd frontend
npm run dev
```

Open **`http://localhost:3000`** in your browser (Vite proxies all API & WebSocket requests to port 8000).

---

### Option C: Phase 1 Standalone Pipeline Runner (OpenCV Preview)

To run detection and tracking directly on a single camera/video with an OpenCV window:

```bash
# Run with sample daytime video:
python backend/pipeline.py --source demo_assets/sample.mp4

# Run with your local webcam:
python backend/pipeline.py --source 0

# Run with virtual boundary line overlay:
python backend/pipeline.py --source demo_assets/sample.mp4 --boundary 0,240,854,240

# Run headless (prints metrics only):
python backend/pipeline.py --source demo_assets/sample.mp4 --no-preview
```
*(Press `Q` or `Esc` in the OpenCV preview window to exit).*

---

## 3. Demo Assets & Synthetic Video Generator

Sample CCTV test clips are included in `demo_assets/`. If you want to regenerate or customize them:

```bash
python demo_assets/generate_synthetic_demos.py
```

This generates:
- `demo_assets/sample.mp4` — Daytime border crossing scenario
- `demo_assets/night_sample.mp4` — Low-light night scenario (triggers CLAHE auto-switch)
- `demo_assets/crowd_sample.mp4` — Multiple moving objects (triggers Group clustering)
- `demo_assets/drone_sample.mp4` — Small aerial object scenario

---

## 4. Multi-Camera Configuration

Edit `backend/config/camera_registry.json` to configure cameras:

```json
{
  "cameras": [
    {
      "camera_id": "cam_01",
      "location": "North Gate (Day)",
      "source": "demo_assets/sample.mp4",
      "type": "file",
      "enabled": true
    },
    {
      "camera_id": "cam_02",
      "location": "South Perimeter (Night)",
      "source": "demo_assets/night_sample.mp4",
      "type": "file",
      "enabled": true
    },
    {
      "camera_id": "cam_03",
      "location": "Sector 4 Checkpoint (Crowd)",
      "source": "demo_assets/crowd_sample.mp4",
      "type": "file",
      "enabled": true
    }
  ]
}
```

---

## 5. Phone Camera Ingestion (Demos)

### 1. iOS / Cross-Platform Browser Ingestion
1. Ensure your phone and laptop are on the same Wi-Fi network.
2. Find your laptop's local IP (e.g. `192.168.1.10`).
3. On the phone browser (Safari/Chrome), open:
   `http://<laptop-ip>:8000/phone_stream.html`
4. Tap **Start Streaming**. The stream connects directly to the backend over WebSocket and appears in the dashboard.

### 2. Android IP Webcam App
1. Install **IP Webcam** from Google Play.
2. Start the server and copy the RTSP/MJPEG URL (e.g., `http://192.168.1.5:8080/video`).
3. Add an entry to `camera_registry.json` with `"type": "ip_webcam"` and `"source": "http://192.168.1.5:8080/video"`.

---

## 6. Automated Verification Tests

Run the built-in test suite to verify WebSocket streaming, frame encoding, and alert propagation:

```bash
python backend/test_ws.py
```

---

## 7. Roadmap — Explicit Scope & Non-Goals

In accordance with project guidelines, the following capabilities are **intentionally out of scope** for this software-only CCTV analytics platform:

1. **Full Geometric Multi-Camera 3D Stitching**: By design, the system uses **topology-based handoff** with adjacency maps and travel-time windows rather than complex geometric stitching, avoiding the need for strict physical camera calibration.
2. **Thermal & Radar Hardware Sensor Fusion**: Operates strictly on RGB and infrared CCTV video feeds.
3. **Guaranteed Zero-Visibility Detection**: While automatic CLAHE contrast enhancement dynamically boosts low-light detection, software algorithms cannot replace specialized hardware sensors in 100% pitch-black or heavy fog conditions.
