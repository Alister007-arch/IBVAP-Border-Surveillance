"""
docs/generate_diagrams.py
-------------------------
Generates high-resolution publication-quality diagrams for the IBVAP SIH 2026 Proposal:
1. 3D Isometric Layered Architecture Diagram (architecture_3d.png)
2. End-to-End System Operational Workflow Diagram (system_workflow.png)
3. Algorithmic Threat Assessment Decision Tree (decision_tree_workflow.png)
4. Cryptographic Blockchain & Forensic Audit Ledger Workflow (forensic_ledger_workflow.png)
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch, PathPatch
import matplotlib.patheffects as patheffects
import numpy as np

OUTPUT_DIR = Path(r"c:\MY Projects\AI-Based Intelligent Video Platform for Border Surveillance\Border-Surveillance-System\docs\assets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# DIAGRAM 1: 3D Isometric Layered System Architecture
# ---------------------------------------------------------------------------
def generate_3d_architecture():
    fig = plt.figure(figsize=(15, 12), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#080F21")
    fig.patch.set_facecolor("#080F21")

    cos30 = np.cos(np.radians(24))
    sin30 = np.sin(np.radians(24))

    def to_iso(u, v, z):
        x = (u - v) * cos30
        y = (u + v) * sin30 + z
        return x, y

    def draw_iso_slab(u_center, v_center, u_width, v_length, z_base, thickness, top_color, side_color1, side_color2, border_color):
        u1 = u_center - u_width / 2
        u2 = u_center + u_width / 2
        v1 = v_center - v_length / 2
        v2 = v_center + v_length / 2

        p1 = to_iso(u1, v1, z_base + thickness)
        p2 = to_iso(u2, v1, z_base + thickness)
        p3 = to_iso(u2, v2, z_base + thickness)
        p4 = to_iso(u1, v2, z_base + thickness)

        b1 = to_iso(u1, v1, z_base)
        b2 = to_iso(u2, v1, z_base)
        b3 = to_iso(u2, v2, z_base)
        b4 = to_iso(u1, v2, z_base)

        poly_right = Polygon([p2, p3, b3, b2], closed=True, facecolor=side_color1, edgecolor=border_color, linewidth=1.2)
        ax.add_patch(poly_right)

        poly_left = Polygon([p1, p2, b2, b1], closed=True, facecolor=side_color2, edgecolor=border_color, linewidth=1.2)
        ax.add_patch(poly_left)

        poly_top = Polygon([p1, p2, p3, p4], closed=True, facecolor=top_color, edgecolor=border_color, linewidth=1.6)
        ax.add_patch(poly_top)

        return (p1, p2, p3, p4)

    def draw_iso_module(u_center, v_center, u_w, v_l, z_base, color, label, sublabel=""):
        p1 = to_iso(u_center - u_w/2, v_center - v_l/2, z_base)
        p2 = to_iso(u_center + u_w/2, v_center - v_l/2, z_base)
        p3 = to_iso(u_center + u_w/2, v_center + v_l/2, z_base)
        p4 = to_iso(u_center - u_w/2, v_center + v_l/2, z_base)
        poly = Polygon([p1, p2, p3, p4], closed=True, facecolor=color, edgecolor="#FFFFFF", linewidth=1.0, alpha=0.95)
        ax.add_patch(poly)

        cx, cy = to_iso(u_center, v_center, z_base)
        ax.text(cx, cy + 0.10, label, ha="center", va="center", color="#FFFFFF", fontsize=8.2, fontweight="bold")
        if sublabel:
            ax.text(cx, cy - 0.13, sublabel, ha="center", va="center", color="#E2E8F0", fontsize=6.8)

    layers = [
        {
            "id": "LAYER 1",
            "title": "PHYSICAL SENSOR & INGESTION LAYER",
            "z": 0.0,
            "thick": 0.40,
            "top": "#162038",
            "side1": "#0B1224",
            "side2": "#10182E",
            "border": "#38BDF8",
            "modules": [
                (-3.4, 0, 2.1, 1.3, "#1D4ED8", "Legacy IP-CCTV", "RTSP / H.264 / ONVIF"),
                (-1.1, 0, 2.0, 1.3, "#0284C7", "Patrol Smartphones", "HTTPS / WSS Mobile Ingest"),
                (1.1, 0, 2.0, 1.3, "#0F766E", "Checkpoint Webcams", "USB Direct Feed / OpenCV"),
                (3.3, 0, 2.0, 1.3, "#4338CA", "Thermal / PTZ", "Analog / NVR Gateway"),
            ]
        },
        {
            "id": "LAYER 2",
            "title": "ADAPTIVE PRE-PROCESSING & CONDITIONING",
            "z": 2.1,
            "thick": 0.40,
            "top": "#18243E",
            "side1": "#0D1629",
            "side2": "#131C33",
            "border": "#38BDF8",
            "modules": [
                (-3.0, 0, 2.4, 1.3, "#0E7490", "Dynamic Lux Sensor", "Pixel Luminance Tracking"),
                (-0.4, 0, 2.4, 1.3, "#047857", "Adaptive CLAHE", "Histogram Contrast Boost"),
                (2.2, 0, 2.4, 1.3, "#4F46E5", "Night/Day Auto-Switch", "Zero-Lux Mode Switcher"),
            ]
        },
        {
            "id": "LAYER 3",
            "title": "DUAL-ENGINE DETECTION & TRACKING CORE",
            "z": 4.2,
            "thick": 0.40,
            "top": "#1A2542",
            "side1": "#0F182E",
            "side2": "#151F38",
            "border": "#00F0FF",
            "modules": [
                (-3.4, 0, 2.2, 1.3, "#B91C1C", "Ultralytics YOLOv8", "Multiclass Person/Vehicles"),
                (-1.1, 0, 2.1, 1.3, "#B45309", "OpenCV MOG2", "Weather Motion Fallback"),
                (1.1, 0, 2.1, 1.3, "#1D4ED8", "ByteTrack Engine", "Trajectory & Velocity Kalman"),
                (3.3, 0, 1.9, 1.3, "#6D28D9", "Cross-Cam Re-ID", "HSV Color Space Matching"),
            ]
        },
        {
            "id": "LAYER 4",
            "title": "TACTICAL THREAT INTELLIGENCE SUITE",
            "z": 6.3,
            "thick": 0.40,
            "top": "#1C2442",
            "side1": "#10162B",
            "side2": "#171E36",
            "border": "#EC4899",
            "modules": [
                (-3.4, 0, 2.1, 1.3, "#BE123C", "Virtual Fence AI", "Tripwire & Polygon Breach"),
                (-1.1, 0, 2.1, 1.3, "#7C3AED", "ArcFace 512-D FRS", "BSF Watchlist Cosine Sim"),
                (1.1, 0, 2.1, 1.3, "#0369A1", "Morphology ANPR", "BOLO License Plate OCR"),
                (3.3, 0, 2.0, 1.3, "#C2410C", "Behavioral Analyzer", "Loitering >7s / Rapid Sprint"),
            ]
        },
        {
            "id": "LAYER 5",
            "title": "BLOCKCHAIN & FORENSIC AUDIT LEDGER",
            "z": 8.4,
            "thick": 0.40,
            "top": "#19283C",
            "side1": "#0E1A2B",
            "side2": "#142135",
            "border": "#10B981",
            "modules": [
                (-3.0, 0, 2.4, 1.3, "#059669", "SHA-256 Evidence Hash", "Tamper-Evident Snapshot Proof"),
                (-0.4, 0, 2.4, 1.3, "#0D9488", "Immutable SQLite Ledger", "Append-Only Audit Chain"),
                (2.2, 0, 2.4, 1.3, "#0284C7", "MHA Forensic Exporter", "Court-Admissible Signed CSV"),
            ]
        },
        {
            "id": "LAYER 6",
            "title": "COMMAND & CONTROL (C2) TACTICAL DISPATCH",
            "z": 10.5,
            "thick": 0.40,
            "top": "#152E52",
            "side1": "#0B1D38",
            "side2": "#102545",
            "border": "#38BDF8",
            "modules": [
                (-3.3, 0, 2.2, 1.3, "#0284C7", "Dual HTTP/HTTPS Gateway", "Ports 8000 & 8443 (TLS 1.3)"),
                (-1.0, 0, 2.1, 1.3, "#059669", "WebSocket Telemetry", "<200ms Low-Latency Stream"),
                (1.1, 0, 2.1, 1.3, "#DC2626", "Acoustic Synthesizer", "3-Tier Alarms (RED/AMB/BLU)"),
                (3.2, 0, 2.0, 1.3, "#4F46E5", "React 18 C2 Console", "Multi-Grid Dark Tactical UI"),
            ]
        },
    ]

    slab_u_w = 9.8
    slab_v_l = 3.4

    for bus_u in [-4.0, 4.0]:
        p_bottom = to_iso(bus_u, 0, 0.40)
        p_top = to_iso(bus_u, 0, 10.9)
        ax.plot([p_bottom[0], p_top[0]], [p_bottom[1], p_top[1]], color="#38BDF8", linestyle="--", linewidth=1.5, alpha=0.55)

    for lyr in layers:
        z = lyr["z"]
        thick = lyr["thick"]
        top_pts = draw_iso_slab(0, 0, slab_u_w, slab_v_l, z, thick, lyr["top"], lyr["side1"], lyr["side2"], lyr["border"])

        p_corner = to_iso(-slab_u_w/2, -slab_v_l/2, z + thick/2)
        lbl_x = -6.4
        lbl_y = p_corner[1]

        # Tag box on left with 2-line title
        tag_box = FancyBboxPatch(
            (lbl_x - 3.4, lbl_y - 0.32), 3.4, 0.64,
            boxstyle="round,pad=0.06,rounding_size=0.12",
            facecolor="#0B132B", edgecolor=lyr["border"], linewidth=1.3, alpha=0.95
        )
        ax.add_patch(tag_box)
        ax.text(lbl_x - 1.7, lbl_y + 0.11, lyr["id"], ha="center", va="center", color=lyr["border"], fontsize=7.8, fontweight="bold")
        ax.text(lbl_x - 1.7, lbl_y - 0.13, lyr["title"], ha="center", va="center", color="#FFFFFF", fontsize=6.5, fontweight="bold")

        ax.plot([lbl_x, p_corner[0]], [lbl_y, p_corner[1]], color=lyr["border"], linestyle=":", linewidth=1.2, alpha=0.8)

        for mod in lyr["modules"]:
            draw_iso_module(mod[0], mod[1], mod[2], mod[3], z + thick + 0.02, mod[4], mod[5], mod[6])

    for i in range(len(layers) - 1):
        z_curr = layers[i]["z"] + layers[i]["thick"]
        z_next = layers[i+1]["z"]
        flow_x1, flow_y1 = to_iso(0, 0, z_curr + 0.05)
        flow_x2, flow_y2 = to_iso(0, 0, z_next - 0.05)
        ax.annotate(
            "", xy=(flow_x2, flow_y2), xytext=(flow_x1, flow_y1),
            arrowprops=dict(arrowstyle="-|>", color="#00F0FF", lw=2, mutation_scale=13, alpha=0.85)
        )

    ax.text(
        0, 13.3, "IBVAP 3D ISOMETRIC EDGE PLATFORM ARCHITECTURE",
        ha="center", va="center", color="#FFFFFF", fontsize=15, fontweight="bold",
        path_effects=[patheffects.withSimplePatchShadow()]
    )
    ax.text(
        0, 12.85, "Sovereign 6-Tier Pipeline: Standard CCTV Ingestion to Real-Time Military C2 & Cryptographic Ledger",
        ha="center", va="center", color="#94A3B8", fontsize=10.5
    )

    ax.set_xlim(-10.8, 9.2)
    ax.set_ylim(-3.0, 14.0)
    ax.axis("off")
    plt.tight_layout()
    out_path = OUTPUT_DIR / "architecture_3d.png"
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ---------------------------------------------------------------------------
# DIAGRAM 2: End-to-End Operational System Workflow
# ---------------------------------------------------------------------------
def generate_system_workflow():
    fig = plt.figure(figsize=(14, 8.5), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0F172A")
    fig.patch.set_facecolor("#0F172A")

    columns = [
        {
            "num": "STAGE 1",
            "title": "Stream Ingestion",
            "color": "#0284C7",
            "x": 1.2,
            "items": [
                ("RTSP / IP-CCTV", "Legacy border cameras (H.264/RTSP)"),
                ("Mobile Patrol WSS", "Smartphones via TLS 1.3 WebRTC"),
                ("Checkpoint Webcams", "USB OpenCV direct capture"),
                ("PTZ & Thermal", "Low-lux border sensors")
            ]
        },
        {
            "num": "STAGE 2",
            "title": "Adaptive Preprocessing",
            "color": "#0891B2",
            "x": 3.6,
            "items": [
                ("Luminance Sensor", "Calculates mean pixel lux in real-time"),
                ("Adaptive CLAHE", "Histogram equalization in low-light"),
                ("Night/Day Switcher", "Auto-activates night mode (<35 lux)"),
                ("Frame Normalization", "Resizes to 640x384 for low latency")
            ]
        },
        {
            "num": "STAGE 3",
            "title": "Dual AI Detection & Track",
            "color": "#7C3AED",
            "x": 6.0,
            "items": [
                ("Ultralytics YOLOv8", "Multiclass Person/Vehicles/Luggage"),
                ("OpenCV MOG2", "Motion subtraction for rain/fog"),
                ("Detection Merger", "Suppresses false positives & joins boxes"),
                ("ByteTrack Engine", "Kalman-filtered trajectory persistence")
            ]
        },
        {
            "num": "STAGE 4",
            "title": "Tactical Threat Intelligence",
            "color": "#B91C1C",
            "x": 8.4,
            "items": [
                ("Virtual Fence Breaches", "Tripwire & polygonal exclusion zone"),
                ("ArcFace 512-D Biometrics", "Cosine match vs BSF Suspect List"),
                ("Morphology ANPR OCR", "Plate crop & BOLO vehicle match"),
                ("Behavioral AI", "Loitering >7s & rapid sprint check")
            ]
        },
        {
            "num": "STAGE 5",
            "title": "C2 Dispatch & Ledger",
            "color": "#059669",
            "x": 10.8,
            "items": [
                ("Priority Classifier", "RED / AMBER / BLUE triage"),
                ("Acoustic Synthesizer", "Web Audio 880Hz/520Hz/330Hz"),
                ("WebSocket Broadcast", "<200ms annotated frame stream"),
                ("SHA-256 Audit Ledger", "Immutable court-admissible store")
            ]
        }
    ]

    card_w = 2.0
    card_h = 0.95
    y_starts = [6.0, 4.65, 3.3, 1.95]

    for col in columns:
        cx = col["x"]
        color = col["color"]

        hdr = FancyBboxPatch(
            (cx - card_w/2, 7.3), card_w, 0.7,
            boxstyle="round,pad=0.08,rounding_size=0.15",
            facecolor=color, edgecolor="#FFFFFF", linewidth=1.2, alpha=0.95
        )
        ax.add_patch(hdr)
        ax.text(cx, 7.75, col["num"], ha="center", va="center", color="#E2E8F0", fontsize=8, fontweight="bold")
        ax.text(cx, 7.48, col["title"], ha="center", va="center", color="#FFFFFF", fontsize=9.5, fontweight="bold")

        for idx, (head, desc) in enumerate(col["items"]):
            cy = y_starts[idx]
            box = FancyBboxPatch(
                (cx - card_w/2, cy - card_h/2), card_w, card_h,
                boxstyle="round,pad=0.06,rounding_size=0.12",
                facecolor="#1E293B", edgecolor=color, linewidth=1.2
            )
            ax.add_patch(box)
            ax.text(cx, cy + 0.22, head, ha="center", va="center", color="#38BDF8", fontsize=8.5, fontweight="bold")
            ax.text(cx, cy - 0.14, desc, ha="center", va="center", color="#94A3B8", fontsize=7.2, multialignment="center")

            if idx < 3:
                ax.annotate(
                    "", xy=(cx, y_starts[idx+1] + card_h/2), xytext=(cx, cy - card_h/2),
                    arrowprops=dict(arrowstyle="-|>", color="#64748B", lw=1.2, mutation_scale=10)
                )

    for i in range(len(columns) - 1):
        x1 = columns[i]["x"] + card_w/2
        x2 = columns[i+1]["x"] - card_w/2
        for y_pos in [4.65, 3.3]:
            ax.annotate(
                "", xy=(x2, y_pos), xytext=(x1, y_pos),
                arrowprops=dict(arrowstyle="-|>", color="#00D2FF", lw=2, mutation_scale=12, alpha=0.8)
            )

    ax.text(
        6.0, 8.8, "IBVAP END-TO-END SYSTEM OPERATIONAL WORKFLOW",
        ha="center", va="center", color="#FFFFFF", fontsize=15, fontweight="bold",
        path_effects=[patheffects.withSimplePatchShadow()]
    )
    ax.text(
        6.0, 8.4, "Real-Time Pipeline Execution Flow: Sensor Capture to Tactical Threat Interdiction (<200 ms Total Latency)",
        ha="center", va="center", color="#94A3B8", fontsize=10
    )

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(1.0, 9.3)
    ax.axis("off")
    plt.tight_layout()
    out_path = OUTPUT_DIR / "system_workflow.png"
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ---------------------------------------------------------------------------
# DIAGRAM 3: Algorithmic Threat Assessment & Decision Tree Flowchart
# ---------------------------------------------------------------------------
def generate_decision_tree():
    fig = plt.figure(figsize=(14, 10.0), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#071120")
    fig.patch.set_facecolor("#071120")

    def draw_node(x, y, w, h, text_title, text_sub, color, shape="box"):
        if shape == "box":
            patch = FancyBboxPatch(
                (x - w/2, y - h/2), w, h,
                boxstyle="round,pad=0.06,rounding_size=0.12",
                facecolor="#0E1E38", edgecolor=color, linewidth=1.5
            )
        elif shape == "diamond":
            pts = [(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)]
            patch = Polygon(pts, closed=True, facecolor="#0E1E38", edgecolor=color, linewidth=1.6)
        ax.add_patch(patch)
        ax.text(x, y + (0.11 if text_sub else 0), text_title, ha="center", va="center", color="#FFFFFF", fontsize=8.0, fontweight="bold")
        if text_sub:
            ax.text(x, y - 0.15, text_sub, ha="center", va="center", color="#94A3B8", fontsize=7.0)

    draw_node(6.0, 8.5, 3.0, 0.75, "Incoming Frame Stream", "RTSP / WSS Phone / USB Direct", "#38BDF8")

    draw_node(6.0, 7.15, 3.4, 0.95, "Mean Lux Check (L < 35?)", "Dynamic Luminance Analysis", "#F59E0B", shape="diamond")
    ax.annotate("", xy=(6.0, 7.65), xytext=(6.0, 8.12), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.5))

    draw_node(2.2, 7.15, 2.6, 0.75, "CLAHE Contrast Boost", "MOG2 Motion Sensitivity x2", "#06B6D4")
    ax.annotate("YES (NIGHT)", xy=(3.5, 7.15), xytext=(4.3, 7.15), arrowprops=dict(arrowstyle="-|>", color="#F59E0B", lw=1.5),
                ha="center", va="bottom", color="#F59E0B", fontsize=7.5, fontweight="bold")

    draw_node(6.0, 5.7, 3.4, 0.8, "YOLOv8 + MOG2 Detection", "Person, Vehicle, Bag, Motion", "#00D2FF")
    ax.annotate("NO (DAY)", xy=(6.0, 6.1), xytext=(6.0, 6.67), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.5),
                ha="right", va="center", color="#38BDF8", fontsize=7.5, fontweight="bold")
    ax.annotate("", xy=(4.8, 5.7), xytext=(2.2, 6.77), arrowprops=dict(arrowstyle="-|>", color="#06B6D4", lw=1.5))

    draw_node(2.2, 4.3, 2.2, 0.75, "Target: PERSON", "ByteTrack Trajectory", "#38BDF8")
    ax.annotate("", xy=(2.2, 4.7), xytext=(4.5, 5.3), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.5))

    draw_node(6.0, 4.3, 2.2, 0.75, "Target: VEHICLE", "Car, Truck, Bus, Motorcycle", "#38BDF8")
    ax.annotate("", xy=(6.0, 4.7), xytext=(6.0, 5.3), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.5))

    draw_node(9.8, 4.3, 2.2, 0.75, "Target: LUGGAGE", "Unattended Object Check", "#38BDF8")
    ax.annotate("", xy=(9.8, 4.7), xytext=(7.5, 5.3), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.5))

    draw_node(1.1, 2.95, 2.1, 0.95, "Virtual Fence Breach?", "Tripwire / Polygon Cross", "#EF4444", shape="diamond")
    draw_node(3.3, 2.95, 2.1, 0.95, "ArcFace FRS Match?", "512-D Cosine Sim > 0.65", "#A855F7", shape="diamond")
    ax.annotate("", xy=(1.1, 3.45), xytext=(1.8, 3.9), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.2))
    ax.annotate("", xy=(3.3, 3.45), xytext=(2.6, 3.9), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.2))

    draw_node(6.0, 2.95, 2.5, 0.95, "ANPR BOLO Match?", "Morphology OCR vs Registry", "#EF4444", shape="diamond")
    ax.annotate("", xy=(6.0, 3.45), xytext=(6.0, 3.9), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.2))

    draw_node(9.8, 2.95, 2.4, 0.95, "Owner Missing > 15s?", "Static Stationary Bag", "#F59E0B", shape="diamond")
    ax.annotate("", xy=(9.8, 3.45), xytext=(9.8, 3.9), arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=1.2))

    red_box = FancyBboxPatch(
        (0.8, 1.1), 4.8, 1.05,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#7F1D1D", edgecolor="#EF4444", linewidth=2.0
    )
    ax.add_patch(red_box)
    ax.text(3.2, 1.80, "CRITICAL RED THREAT INTERDICTION", ha="center", va="center", color="#FCA5A5", fontsize=9.5, fontweight="bold")
    ax.text(3.2, 1.38, "Tripwire Breach / Suspect Identified / BOLO Vehicle Match\n880Hz Double-Burst Audio + Auto Snapshot + SHA-256 Ledger Commit",
            ha="center", va="center", color="#FFFFFF", fontsize=7.5, multialignment="center")

    amber_box = FancyBboxPatch(
        (6.4, 1.1), 4.8, 1.05,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#78350F", edgecolor="#F59E0B", linewidth=2.0
    )
    ax.add_patch(amber_box)
    ax.text(8.8, 1.80, "AMBER / BLUE OPERATIONAL ALERT", ha="center", va="center", color="#FDE68A", fontsize=9.5, fontweight="bold")
    ax.text(8.8, 1.38, "Loitering (>7s) / Rapid Sprint / Unattended Bag / Night Motion\n520Hz Pulse Beep + Yellow Perimeter Overlay + Tactical Queue",
            ha="center", va="center", color="#FFFFFF", fontsize=7.5, multialignment="center")

    ax.annotate("YES", xy=(1.8, 2.15), xytext=(1.1, 2.45), arrowprops=dict(arrowstyle="-|>", color="#EF4444", lw=1.8),
                color="#EF4444", fontsize=7.5, fontweight="bold")
    ax.annotate("MATCH", xy=(3.2, 2.15), xytext=(3.3, 2.45), arrowprops=dict(arrowstyle="-|>", color="#EF4444", lw=1.8),
                color="#EF4444", fontsize=7.5, fontweight="bold")
    ax.annotate("MATCH", xy=(4.5, 2.15), xytext=(5.1, 2.45), arrowprops=dict(arrowstyle="-|>", color="#EF4444", lw=1.8),
                color="#EF4444", fontsize=7.5, fontweight="bold")
    ax.annotate("NO MATCH", xy=(7.2, 2.15), xytext=(6.9, 2.45), arrowprops=dict(arrowstyle="-|>", color="#F59E0B", lw=1.5),
                color="#F59E0B", fontsize=7.5, fontweight="bold")
    ax.annotate("YES", xy=(9.8, 2.15), xytext=(9.8, 2.45), arrowprops=dict(arrowstyle="-|>", color="#F59E0B", lw=1.5),
                color="#F59E0B", fontsize=7.5, fontweight="bold")

    ax.text(
        6.0, 9.65, "IBVAP THREAT DETECTION & CLASSIFICATION DECISION TREE",
        ha="center", va="center", color="#FFFFFF", fontsize=14, fontweight="bold",
        path_effects=[patheffects.withSimplePatchShadow()]
    )
    ax.text(
        6.0, 9.28, "Autonomous Multi-Tier Logic Tree Executing Across Edge Nodes (<50 ms Decision Cycle)",
        ha="center", va="center", color="#94A3B8", fontsize=9.5
    )

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(0.7, 10.0)
    ax.axis("off")
    plt.tight_layout()
    out_path = OUTPUT_DIR / "decision_tree_workflow.png"
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    print(f"Generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ---------------------------------------------------------------------------
# DIAGRAM 4: Cryptographic Blockchain & Forensic Audit Ledger Workflow
# ---------------------------------------------------------------------------
def generate_forensic_ledger_workflow():
    fig = plt.figure(figsize=(14, 6.5), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0D1B2A")
    fig.patch.set_facecolor("#0D1B2A")

    blocks = [
        {
            "step": "STEP 1: THREAT INGEST",
            "title": "Incident Capture",
            "color": "#38BDF8",
            "x": 1.5,
            "details": ["High-Res JPEG Snapshot", "Pixel Bounding Coordinates", "Camera ID & GPS Timestamp", "Track Velocity Vector"]
        },
        {
            "step": "STEP 2: HASH DIGEST",
            "title": "SHA-256 Computation",
            "color": "#10B981",
            "x": 4.5,
            "details": ["H_snap = SHA256(Raw JPEG)", "H_meta = SHA256(Telemetry)", "Prev Block Hash H_(n-1)", "Block H_n = SHA256(All)"]
        },
        {
            "step": "STEP 3: LEDGER COMMIT",
            "title": "Immutable SQLite Store",
            "color": "#8B5CF6",
            "x": 7.5,
            "details": ["Append-Only SQLite Table", "Local Air-Gapped BOP Storage", "Cryptographic Block Chaining", "Zero Foreign Cloud Exposure"]
        },
        {
            "step": "STEP 4: EVIDENCE DISPATCH",
            "title": "Court-Admissible Export",
            "color": "#F59E0B",
            "x": 10.5,
            "details": ["Digitally Signed CSV Logs", "Timestamped Proof Manifest", "Conforms to MHA Evidence Acts", "Tamper-Verification Tool"]
        }
    ]

    bw = 2.4
    bh = 3.6
    y_center = 3.0

    for i, blk in enumerate(blocks):
        bx = blk["x"]
        col = blk["color"]

        card = FancyBboxPatch(
            (bx - bw/2, y_center - bh/2), bw, bh,
            boxstyle="round,pad=0.08,rounding_size=0.15",
            facecolor="#1B263B", edgecolor=col, linewidth=1.8
        )
        ax.add_patch(card)

        tag = FancyBboxPatch(
            (bx - bw/2 + 0.1, y_center + bh/2 - 0.65), bw - 0.2, 0.55,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=col, edgecolor="#FFFFFF", linewidth=1.0, alpha=0.9
        )
        ax.add_patch(tag)
        ax.text(bx, y_center + bh/2 - 0.27, blk["step"], ha="center", va="center", color="#0F172A", fontsize=7.5, fontweight="bold")
        ax.text(bx, y_center + bh/2 - 0.48, blk["title"], ha="center", va="center", color="#0F172A", fontsize=9, fontweight="bold")

        for d_idx, d_text in enumerate(blk["details"]):
            item_y = y_center + 0.65 - (d_idx * 0.65)
            sub_box = FancyBboxPatch(
                (bx - bw/2 + 0.15, item_y - 0.22), bw - 0.3, 0.48,
                boxstyle="round,pad=0.04,rounding_size=0.08",
                facecolor="#0D1B2A", edgecolor="#415A77", linewidth=1.0
            )
            ax.add_patch(sub_box)
            ax.text(bx, item_y, d_text, ha="center", va="center", color="#E0E1DD", fontsize=7.5)

        if i < len(blocks) - 1:
            ax.annotate(
                "", xy=(blocks[i+1]["x"] - bw/2 - 0.05, y_center), xytext=(bx + bw/2 + 0.05, y_center),
                arrowprops=dict(arrowstyle="-|>", color="#00F0FF", lw=2.2, mutation_scale=14)
            )

    ax.text(
        6.0, 5.8, "CRYPTOGRAPHIC AUDIT LEDGER & EVIDENCE CHAIN-OF-CUSTODY",
        ha="center", va="center", color="#FFFFFF", fontsize=14, fontweight="bold",
        path_effects=[patheffects.withSimplePatchShadow()]
    )
    ax.text(
        6.0, 5.4, "SIH 2026 Blockchain & Cybersecurity Theme Alignment: Mathematical Proof of Tamper-Free Surveillance",
        ha="center", va="center", color="#778DA9", fontsize=9.5
    )

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(0.7, 6.3)
    ax.axis("off")
    plt.tight_layout()
    out_path = OUTPUT_DIR / "forensic_ledger_workflow.png"
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    print("Generating all high-resolution IBVAP architecture and workflow diagrams...")
    generate_3d_architecture()
    generate_system_workflow()
    generate_decision_tree()
    generate_forensic_ledger_workflow()
    print("ALL DIAGRAMS SUCCESSFULLY GENERATED!")
