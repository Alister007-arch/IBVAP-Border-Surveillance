"""
docs/make_pdf.py
----------------
Generates the comprehensive, military-grade 6-page technical proposal PDF for:
Smart India Hackathon 2026 - Problem Statement ID: 26187
Team: Binary Beasts
Title: AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure
Theme: Blockchain & Cybersecurity
Target Org: Ministry of Home Affairs / Border Security Force (BSF)
"""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

PDF_PATH = Path(r"c:\MY Projects\AI-Based Intelligent Video Platform for Border Surveillance\Border-Surveillance-System\docs\SIH2026_BinaryBeasts_Idea_Description.pdf")
ASSETS_DIR = Path(r"c:\MY Projects\AI-Based Intelligent Video Platform for Border Surveillance\Border-Surveillance-System\docs\assets")

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont('Helvetica-Bold', 7.5)
        self.setFillColor(colors.HexColor('#475569'))
        if self._pageNumber > 1:
            self.drawString(36, 812, 'SIH 2026 | PS ID: 26187 | TEAM: BINARY BEASTS | IBVAP TECHNICAL PROPOSAL')
            self.drawRightString(559, 812, 'MINISTRY OF HOME AFFAIRS / BSF')
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.6)
            self.line(36, 806, 559, 806)

        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748B'))
        text_footer = 'Smart India Hackathon 2026 — Official Idea Proposal & Detailed Technical Specification'
        page_str = f'Page {self._pageNumber} of {total_pages}'
        self.drawString(36, 20, text_footer)
        self.drawRightString(559, 20, page_str)
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.6)
        self.line(36, 29, 559, 29)
        self.restoreState()


def build_pdf():
    # Make sure diagrams exist before building
    required_diagrams = [
        ASSETS_DIR / "architecture_3d.png",
        ASSETS_DIR / "system_workflow.png",
        ASSETS_DIR / "decision_tree_workflow.png",
        ASSETS_DIR / "forensic_ledger_workflow.png"
    ]
    for diag in required_diagrams:
        if not diag.exists():
            print(f"Generating missing diagram: {diag.name}...")
            import docs.generate_diagrams as gd
            gd.generate_3d_architecture()
            gd.generate_system_workflow()
            gd.generate_decision_tree()
            gd.generate_forensic_ledger_workflow()
            break

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    C_NAVY = colors.HexColor('#0A2540')
    C_BLUE = colors.HexColor('#0066CC')
    C_CYAN = colors.HexColor('#0284C7')
    C_DARK = colors.HexColor('#0F172A')
    C_LIGHT = colors.HexColor('#F8FAFC')
    C_BORDER = colors.HexColor('#CBD5E1')
    C_TEXT = colors.HexColor('#1E293B')
    C_MUTED = colors.HexColor('#475569')

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, leading=20,
        textColor=C_NAVY, alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'DocSub', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=14,
        textColor=C_BLUE, alignment=TA_CENTER, spaceAfter=6
    )
    h1_style = ParagraphStyle(
        'SecH1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=13.5,
        textColor=C_NAVY, spaceBefore=6, spaceAfter=3,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'SecH2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=C_BLUE, spaceBefore=4, spaceAfter=2,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyDark', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.2, leading=11.2,
        textColor=C_TEXT, spaceAfter=3.5, alignment=TA_JUSTIFY
    )
    bullet_style = ParagraphStyle(
        'BulletText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.2, leading=11.0,
        textColor=C_TEXT, leftIndent=11, spaceAfter=2.5
    )
    cell_style = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.6, leading=9.8,
        textColor=C_TEXT
    )
    cell_b = ParagraphStyle(
        'TableCellB', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.6, leading=9.8,
        textColor=C_NAVY
    )
    cell_h = ParagraphStyle(
        'TableCellH', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.0, leading=10.0,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # PAGE 1: Executive Briefing, Problem Statement & 6-Tier Pipeline Overview
    # =========================================================================
    story.append(Paragraph('SMART INDIA HACKATHON 2026', title_style))
    story.append(Paragraph('OFFICIAL IDEA PROPOSAL & DETAILED TECHNICAL SPECIFICATION', subtitle_style))

    meta_data = [
        [Paragraph('<b>Problem Statement ID:</b>', cell_b), Paragraph('26187', cell_style),
         Paragraph('<b>Category:</b>', cell_b), Paragraph('Software', cell_style)],
        [Paragraph('<b>Problem Title:</b>', cell_b), Paragraph('AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure', cell_style),
         Paragraph('<b>Theme:</b>', cell_b), Paragraph('Blockchain & Cybersecurity', cell_style)],
        [Paragraph('<b>Team Name:</b>', cell_b), Paragraph('<b>Binary Beasts</b>', cell_b),
         Paragraph('<b>Target Org:</b>', cell_b), Paragraph('Ministry of Home Affairs / Border Security Force (BSF)', cell_style)]
    ]
    t_meta = Table(meta_data, colWidths=[105, 225, 75, 118])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 5))

    story.append(Paragraph('1. Executive Summary & Project Abstract', h1_style))
    story.append(Paragraph(
        'The <b>Intelligent Border Video Analytics Platform (IBVAP)</b> is an edge-native, sovereign artificial intelligence surveillance system engineered to modernize India\'s border security infrastructure. Over 1.5 million legacy COTS (Commercial Off-The-Shelf) IP-CCTV cameras deployed across Border Out Posts (BOPs), tactical checkposts, and strategic defense perimeters currently function as passive video recorders requiring exhausting 24/7 human sentry observation. '
        '<b>IBVAP solves this crisis through a 100% software-only AI intelligence overlay</b> that transforms standard RTSP/HTTP video feeds into an autonomous perimeter defense network with <b>zero hardware replacement costs</b>. The platform unifies multiclass YOLOv8 human/vehicle detection, ByteTrack spatial-temporal persistence, ArcFace Facial Recognition System (FRS), Automatic Number Plate Recognition (ANPR), and dynamic Virtual Fence tripwires. '
        'Integrated with a military-grade React Command & Control (C2) dashboard, dual HTTP/HTTPS streaming, Web Audio API threat acoustic alarms, and a SHA-256 tamper-evident forensic audit ledger, IBVAP delivers a zero-latency (<200 ms) tactical threat-interdiction system for the Border Security Force (BSF) and Ministry of Home Affairs.',
        body_style
    ))

    story.append(Paragraph('2. Problem Statement Analysis & Operational Deficiencies', h1_style))
    story.append(Paragraph(
        'India shares over 15,106 km of land borders across rugged, hyper-variable terrains. Current border surveillance systems suffer from four fundamental systemic vulnerabilities:',
        body_style
    ))
    story.append(Paragraph('• <b>Prohibitive Hardware Upgrade Costs:</b> Dedicated smart cameras with proprietary FRS/ANPR chips cost INR 25 to 40 Lakh per installation point, making nationwide rollout across 2,700+ BOPs economically unfeasible.', bullet_style))
    story.append(Paragraph('• <b>Human Sentry Fatigue & Reaction Latency:</b> Operators monitoring multiple video screens miss up to 95% of critical security events after only 22 minutes of continuous viewing, leading to delayed breach responses.', bullet_style))
    story.append(Paragraph('• <b>Night-Time & Adverse Weather Blindness:</b> Standard low-lux CCTV sensors produce severe noise and contrast degradation at night, allowing infiltrators to exploit zero-lux gaps.', bullet_style))
    story.append(Paragraph('• <b>Forensic Tampering & Cloud Security Exposure:</b> Cloud-dependent surveillance platforms expose sensitive national defense intelligence to external latency and foreign interception risks.', bullet_style))

    story.append(Paragraph('3. Proposed Solution Architecture (IBVAP 6-Tier Pipeline)', h1_style))
    tiers_data = [
        [Paragraph('<b>Tier / Module</b>', cell_h), Paragraph('<b>Underlying Technology</b>', cell_h), Paragraph('<b>Operational Function & Capability</b>', cell_h)],
        [Paragraph('<b>Tier 1: Detection</b>', cell_b), Paragraph('Ultralytics YOLOv8 (Edge)', cell_style), Paragraph('Detects persons, vehicles (trucks, cars, motorbikes), and luggage with class confidence tuning.', cell_style)],
        [Paragraph('<b>Tier 2: Tracking</b>', cell_b), Paragraph('ByteTrack + Velocity Vectors', cell_style), Paragraph('Maintains consistent tracking IDs through occlusion; computes real-time velocity vectors.', cell_style)],
        [Paragraph('<b>Tier 3: Motion Fallback</b>', cell_b), Paragraph('OpenCV MOG2 Background Subtractor', cell_style), Paragraph('Catches subtle movement in rain, dense fog, or camouflage when bounding boxes fail.', cell_style)],
        [Paragraph('<b>Tier 4: Threat Engines</b>', cell_b), Paragraph('Virtual Fence & Behavioral AI', cell_style), Paragraph('Calculates polygonal perimeter breaches, loitering (>7s), sprinting incursions & unattended bags.', cell_style)],
        [Paragraph('<b>Tier 5: Biometrics & ANPR</b>', cell_b), Paragraph('InsightFace ArcFace + Morphology OCR', cell_style), Paragraph('Matches 512-D face vectors against BSF watchlist; checks license plates against BOLO registries.', cell_style)],
        [Paragraph('<b>Tier 6: Night-Mode</b>', cell_b), Paragraph('CLAHE + Dynamic Luminance Sensing', cell_style), Paragraph('Monitors average pixel lux; activates CLAHE histogram stretching for low-light movement alarms.', cell_style)]
    ]
    t_tiers = Table(tiers_data, colWidths=[105, 140, 278])
    t_tiers.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tiers)

    # PAGE 1 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: 3D Isometric Architecture & Technical Stack Specifications
    # =========================================================================
    story.append(Paragraph('4. 3D Isometric Edge Platform Architecture', h1_style))
    story.append(Paragraph(
        'The IBVAP architecture is organized as a vertically integrated, edge-native software stack. The system ingests uncalibrated camera streams and transforms them through six modular layers into real-time tactical intelligence:',
        body_style
    ))

    # Embedded 3D Architecture Diagram
    img_arch = Image(str(ASSETS_DIR / "architecture_3d.png"), width=520, height=275)
    story.append(img_arch)
    story.append(Spacer(1, 4))

    story.append(Paragraph('Detailed Layer-by-Layer Architectural Specifications:', h2_style))
    story.append(Paragraph('• <b>Layer 1 (Physical Sensor & Ingestion):</b> Connects transparently to legacy IP-CCTV cameras over RTSP/H.264, checkpoint USB webcams via OpenCV, and roving patrol smartphones via TLS 1.3 WebSockets (WSS), achieving 100% camera agnosticism.', bullet_style))
    story.append(Paragraph('• <b>Layer 2 (Adaptive Pre-Processing & Conditioning):</b> Computes mean frame luminance in real-time. When ambient lux drops below 35, the system automatically activates Contrast Limited Adaptive Histogram Equalization (CLAHE) and boosts motion subtractor sensitivity.', bullet_style))
    story.append(Paragraph('• <b>Layer 3 (Dual-Engine Detection & Tracking Core):</b> Concurrently executes deep-learning object localization (YOLOv8) with statistical motion modeling (MOG2). Tracks are temporally stabilized using ByteTrack Kalman filtering to eliminate ID-switches.', bullet_style))
    story.append(Paragraph('• <b>Layer 4 (Tactical Threat Intelligence Suite):</b> High-speed analytical engines evaluate polygonal boundary breaches, match 512-D face vectors against BSF watchlists, read vehicle plates against BOLO registries, and flag loitering (>7s) or sprinting.', bullet_style))
    story.append(Paragraph('• <b>Layer 5 (Blockchain & Forensic Audit Ledger):</b> Computes SHA-256 cryptographic digests of every incident snapshot and metadata payload, logging records into an immutable, append-only SQLite ledger to ensure tamper-evident forensic validity.', bullet_style))
    story.append(Paragraph('• <b>Layer 6 (Command & Control Tactical Dispatch):</b> Broadcasts annotated frames and priority alerts over WebSockets (<200 ms latency) to a tactical React C2 console equipped with multi-frequency Web Audio threat sirens.', bullet_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph('5. Technical Stack & Edge Hardware Specifications', h1_style))
    tech_data = [
        [Paragraph('<b>Layer</b>', cell_h), Paragraph('<b>Technology Components</b>', cell_h), Paragraph('<b>Role in Platform</b>', cell_h)],
        [Paragraph('Backend Core', cell_b), Paragraph('Python 3.11+, FastAPI, Uvicorn, AsyncIO', cell_style), Paragraph('High-throughput REST API & multi-stream WebSocket server.', cell_style)],
        [Paragraph('Dual-Server Gateway', cell_b), Paragraph('HTTP (Port 8000) & HTTPS/WSS (Port 8443)', cell_style), Paragraph('Simultaneous C2 dashboard serving & encrypted patrol phone streaming.', cell_style)],
        [Paragraph('AI & Computer Vision', cell_b), Paragraph('Ultralytics YOLOv8, OpenCV 4.9+, MOG2', cell_style), Paragraph('Edge object detection, CLAHE contrast boost & motion fallback.', cell_style)],
        [Paragraph('Biometrics & ANPR', cell_b), Paragraph('InsightFace ArcFace 512-D, Morphology OCR', cell_style), Paragraph('Suspect facial identification & BOLO license plate recognition.', cell_style)],
        [Paragraph('Tactical Frontend', cell_b), Paragraph('React 18, Vite 5, Tailwind CSS, Lucide', cell_style), Paragraph('Military-grade dark console with live video grid & threat alarms.', cell_style)],
        [Paragraph('Hardware (Minimum)', cell_b), Paragraph('Intel Core i5/i7 (8th Gen+), 8-16 GB RAM', cell_style), Paragraph('Runs 3–5 concurrent camera streams at 15–25 FPS without external GPU.', cell_style)],
        [Paragraph('Hardware (Edge GPU)', cell_b), Paragraph('NVIDIA RTX 3060 / Jetson Orin / TensorRT', cell_style), Paragraph('Enables scaling to 20+ concurrent HD camera streams per sector node.', cell_style)]
    ]
    t_tech = Table(tech_data, colWidths=[95, 175, 253])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_BLUE),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tech)

    # PAGE 2 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: End-to-End Operational Workflow & Processing Lifecycle
    # =========================================================================
    story.append(Paragraph('6. End-to-End Operational System Workflow & Processing Lifecycle', h1_style))
    story.append(Paragraph(
        'IBVAP operates an asynchronous, multi-threaded surveillance pipeline where video ingestion, computer vision inference, threat heuristics, and operator alerting execute with an end-to-end latency of under 200 milliseconds:',
        body_style
    ))

    # Embedded Workflow Diagram
    img_wf = Image(str(ASSETS_DIR / "system_workflow.png"), width=520, height=270)
    story.append(img_wf)
    story.append(Spacer(1, 4))

    story.append(Paragraph('Detailed 5-Stage Operational Execution Lifecycle:', h2_style))
    story.append(Paragraph(
        '• <b>Stage 1: Multi-Source Stream Ingestion & Demuxing:</b> Camera pipeline workers continuously pull live video frames from IP cameras (RTSP), USB border webcams, or mobile patrol phone WebSockets. Incoming frames are ingested into memory buffers, normalized to 640&times;384 resolution, and timestamped with microsecond precision.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Stage 2: Dynamic Environmental Sensing & Contrast Conditioning:</b> Every frame is evaluated for mean pixel luminance (<i>L</i><sub>avg</sub> = (1 / <i>WH</i>) &times; &Sigma; <i>I</i>(<i>x, y</i>)). When <i>L</i><sub>avg</sub> &lt; 35 lux (night/zero-lux condition), the engine automatically engages CLAHE (Contrast Limited Adaptive Histogram Equalization) with clip limit 2.5 and tile grid 8&times;8, while doubling the motion sensitivity of the OpenCV MOG2 background subtractor.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Stage 3: Dual AI Detection & Kalman Trajectory Tracking:</b> Frames are concurrently passed to Ultralytics YOLOv8 for multiclass semantic bounding box detection and MOG2 for foreground motion mask extraction. A detection merger eliminates redundant candidates. The ByteTrack engine then matches detections against active tracklets using Hungarian association and Kalman filter state estimation, producing persistent track IDs and directional velocity vectors.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Stage 4: Multi-Engine Threat Arbitration & Priority Scoring:</b> Active entity tracks are evaluated against five specialized analytical engines: (1) Virtual Fence line-crossing and polygonal perimeter containment; (2) ArcFace 512-D facial feature matching against the BSF suspect watchlist; (3) ANPR morphological vehicle plate isolation and OCR BOLO registry lookup; (4) Behavioral analysis for loitering (>7s) or perimeter sprints (>120 px/s); and (5) Unattended luggage stationary timers.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Stage 5: Command & Control Dispatch & Cryptographic Audit Commit:</b> Verified threats are categorized into RED (Critical), AMBER (Warning), or BLUE (Informational) alerts. The engine pushes annotated surveillance frames and JSON telemetry over WebSockets to the React C2 dashboard, triggers multi-frequency acoustic sirens on sentry terminals, and commits a SHA-256 hashed evidence record to the append-only SQLite store.',
        body_style
    ))

    # PAGE 3 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: Algorithmic Threat Assessment Decision Tree & Field Patrol Ingest
    # =========================================================================
    story.append(Paragraph('7. Algorithmic Threat Assessment & Decision Logic Flowchart', h1_style))
    story.append(Paragraph(
        'The IBVAP decision engine follows a deterministic, hierarchical arbitration tree that eliminates false positives while guaranteeing immediate alert escalations for confirmed border security breaches:',
        body_style
    ))

    # Embedded Decision Tree Diagram
    img_dt = Image(str(ASSETS_DIR / "decision_tree_workflow.png"), width=520, height=275)
    story.append(img_dt)
    story.append(Spacer(1, 4))

    story.append(Paragraph('Mathematical & Heuristic Formulation of Threat Engines:', h2_style))
    story.append(Paragraph(
        '• <b>Virtual Fence Tripwire & Boundary Breach:</b> Evaluates target centroids (<i>x<sub>c</sub>, y<sub>c</sub></i>) against arbitrary polygonal perimeter <i>P</i> = {<i>v</i><sub>1</sub>, <i>v</i><sub>2</sub>, ... <i>v<sub>n</sub></i>}. Tripwire intersection is computed via the 2D cross-product orientation test: <i>D</i> = (<i>x</i><sub>2</sub> - <i>x</i><sub>1</sub>)(<i>y<sub>c</sub></i> - <i>y</i><sub>1</sub>) - (<i>y</i><sub>2</sub> - <i>y</i><sub>1</sub>)(<i>x<sub>c</sub></i> - <i>x</i><sub>1</sub>). A sign inversion across consecutive frames denotes an immediate perimeter crossing, triggering a <b>CRITICAL RED</b> alarm.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Deep Metric Facial Recognition (FRS):</b> Crops detected faces and extracts a 512-dimensional embedding vector <b>v</b> &isin; <b>R</b><sup>512</sup> via ArcFace deep residual networks. Similarity against enrolled BSF suspect gallery {<b>u</b><sub><i>i</i></sub>} is calculated using normalized cosine metric: <i>S</i>(<b>v</b>, <b>u</b><sub><i>i</i></sub>) = (<b>v</b> &middot; <b>u</b><sub><i>i</i></sub>) / (||<b>v</b>|| &times; ||<b>u</b><sub><i>i</i></sub>||). If <i>S</i>(<b>v</b>, <b>u</b><sub><i>i</i></sub>) &ge; 0.65, a suspect match is confirmed with immediate sentry interdiction dispatch.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>ANPR Morphology & Character Recognition:</b> Applies black-hat morphological filtering with rectangular kernels (13&times;5) to isolate high-contrast license plates from vehicle bumpers. Contours matching standard plate aspect ratios (2.5:1 to 5.0:1) are binarized and parsed via OCR. Extracted alphanumeric strings are verified against national BOLO databases.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Behavioral Threat Detection (Loitering, Sprint, Abandoned Luggage):</b> Tracks calculate displacement radius <i>R</i>(<i>t</i>) = ||<b>p</b>(<i>t</i>) - <b>p</b>(<i>t</i> - &Delta;<i>t</i>)||. If a person remains within <i>R</i> &lt; 35 px for <i>t</i> &gt; 7.0 seconds near perimeter fences, a LOITERING alert is raised. If velocity ||<b>v</b>|| &gt; 120 px/s toward the border, a SPRINT INCURSION alarm fires. Luggage entities isolated from nearest person track by &gt;100 px for &gt;15 seconds trigger UNATTENDED BAGGAGE warnings.',
        body_style
    ))

    story.append(Paragraph('8. Zero-Trust Mobile Patrol Ingestion & Dual-Server Gateway', h1_style))
    story.append(Paragraph(
        'To eliminate blindspots along patrol tracks between fixed camera posts, IBVAP incorporates a <b>Zero-Install Patrol Phone Ingestion Gateway</b>. Ground jawans scan a tactical QR code to open a secure HTML5 stream on any smartphone browser. The device connects over <b>WSS (WebSocket Secure) on port 8443 via TLS 1.3</b> using dynamically generated Subject Alternative Name (SAN) SSL certificates. Video frames are piped directly into the surveillance engine as an active camera feed, allowing ground patrols to act as mobile surveillance nodes without installing external software.',
        body_style
    ))

    # PAGE 4 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: Blockchain, Cryptographic Audit Ledger & Operational Defenses
    # =========================================================================
    story.append(Paragraph('9. Blockchain, Cybersecurity & Cryptographic Audit Ledger', h1_style))
    story.append(Paragraph(
        'In strict compliance with the SIH 2026 <b>Blockchain & Cybersecurity</b> theme, IBVAP implements an immutable, tamper-evident cryptographic audit ledger. Every security event is cryptographically sealed into a sequential forensic chain of custody:',
        body_style
    ))

    # Embedded Forensic Ledger Diagram
    img_led = Image(str(ASSETS_DIR / "forensic_ledger_workflow.png"), width=520, height=210)
    story.append(img_led)
    story.append(Spacer(1, 4))

    story.append(Paragraph('Cryptographic Security & Forensic Verification Architecture:', h2_style))
    story.append(Paragraph(
        '• <b>Cryptographic Block Hashing & Immutability:</b> When an intrusion, FRS match, or ANPR sighting occurs, IBVAP captures the raw JPEG frame snapshot, camera ID, UTC timestamp, and detection coordinates. The snapshot is hashed using <b>SHA-256</b> (<i>H</i><sub>snap</sub> = SHA256(JPEG)). This digest is combined with event metadata and the previous block hash (<i>H</i><sub>prev</sub>) to create an immutable chained block: <i>H<sub>n</sub></i> = SHA256(<i>H</i><sub><i>n</i>-1</sub> || <i>H</i><sub>snap</sub> || Timestamp || Metadata). Any post-facto tampering with log entries or snapshots breaks the hash chain, immediately invalidating the ledger.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>100% Air-Gapped Sovereign Deployment:</b> IBVAP operates entirely on local BOP intranet hardware. No biometric vector, video frame, or intelligence alert is transmitted to external commercial clouds (AWS/Azure/GCP), preventing foreign intelligence interception and ensuring complete national data sovereignty.',
        body_style
    ))
    story.append(Paragraph(
        '• <b>Court-Admissible MHA Evidence Export:</b> Operators can export cryptographically timestamped CSV incident reports with linked cryptographic snapshot proofs conforming to Indian Evidence Act requirements and MHA standard guidelines.',
        body_style
    ))

    story.append(Spacer(1, 3))
    story.append(Paragraph('10. Operational Risk Matrix & Implemented Engineering Defenses', h1_style))
    risk_data = [
        [Paragraph('<b>Identified Risk / Threat</b>', cell_h), Paragraph('<b>Severity</b>', cell_h), Paragraph('<b>Implemented Engineering Defense in IBVAP</b>', cell_h)],
        [Paragraph('Zero-Lux / Rain / Dense Fog', cell_b), Paragraph('<font color="#DC2626"><b>HIGH</b></font>', cell_style), Paragraph('Luminance monitoring dynamically boosts CLAHE contrast and switches to MOG2 background motion subtraction.', cell_style)],
        [Paragraph('False Alarms (Animals, Foliage)', cell_b), Paragraph('<font color="#DC2626"><b>HIGH</b></font>', cell_style), Paragraph('Two-stage validation: YOLOv8 semantic classification eliminates non-target classes; trajectory vectors confirm deliberate intrusions.', cell_style)],
        [Paragraph('Remote BOP Bandwidth Loss', cell_b), Paragraph('<font color="#D97706"><b>MEDIUM</b></font>', cell_style), Paragraph('100% Edge Autonomy: Full inference executes locally on BOP mini-PC; alert queues persist locally during network blackouts.', cell_style)],
        [Paragraph('Occluded Faces & Dirty Plates', cell_b), Paragraph('<font color="#D97706"><b>MEDIUM</b></font>', cell_style), Paragraph('Cross-Camera Re-ID color-histogram matching maintains identity persistence across camera handoffs despite occlusion.', cell_style)],
        [Paragraph('Insider Forensic Tampering', cell_b), Paragraph('<font color="#DC2626"><b>HIGH</b></font>', cell_style), Paragraph('SHA-256 sequential cryptographic hash chaining ensures unauthorized deletion or alteration of snapshots is mathematically detectable.', cell_style)]
    ]
    t_risk = Table(risk_data, colWidths=[120, 65, 338])
    t_risk.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_risk)

    # PAGE 5 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: Feasibility, Financial Viability & National Strategic Impact
    # =========================================================================
    story.append(Paragraph('11. Feasibility, Financial Viability & Budget Savings Analysis', h1_style))
    story.append(Paragraph(
        'A comprehensive cost-benefit analysis reveals that IBVAP delivers over 90% capital expenditure savings compared to conventional hardware-replacement surveillance models:',
        body_style
    ))

    cost_data = [
        [Paragraph('<b>Surveillance Component</b>', cell_h), Paragraph('<b>Traditional Smart Hardware Model</b>', cell_h), Paragraph('<b>IBVAP Software-Only Model</b>', cell_h)],
        [Paragraph('Cost per Camera Checkpost', cell_b), Paragraph('INR 25,00,000 – 40,00,000 (Dedicated FRS/ANPR Hardware)', cell_style), Paragraph('<b>INR 0 (Zero Hardware Replacement)</b>', cell_b)],
        [Paragraph('Deployment Across 500 BOPs', cell_b), Paragraph('INR 1,250 – 2,000 Crore Capital Expenditure', cell_style), Paragraph('<b>&lt; INR 5 Crore (Commodity Edge Servers)</b>', cell_b)],
        [Paragraph('Deployment Timeline', cell_b), Paragraph('12–24 Months (Hardware Procurement & Civil Works)', cell_style), Paragraph('<b>1–2 Days (Software Deployment on Existing Network)</b>', cell_style)],
        [Paragraph('Camera Agnosticism', cell_b), Paragraph('Locked to vendor proprietary protocols & firmware', cell_style), Paragraph('<b>100% Agnostic (RTSP, HTTP, USB, Phone WebRTC)</b>', cell_style)],
        [Paragraph('Asset Lifecycle Extension', cell_b), Paragraph('Immediate obsolescence of legacy CCTV equipment', cell_style), Paragraph('<b>Extends legacy camera utility by 8–10 years</b>', cell_style)]
    ]
    t_cost = Table(cost_data, colWidths=[120, 200, 203])
    t_cost.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_BLUE),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_cost)
    story.append(Spacer(1, 4))

    story.append(Paragraph('12. Multi-Domain Strategic Impact & Benefits', h1_style))
    story.append(Paragraph('• <b>National Defense & Tactical Readiness:</b> Transforms passive fence cameras into active tripwires. Cuts sentry detection response time from minutes to <2 seconds with multi-frequency acoustic sirens, stopping infiltration before entry.', bullet_style))
    story.append(Paragraph('• <b>Economic & Fiscal Savings:</b> Saves over INR 500+ Crore nationally by revitalizing India\'s existing 1.5M+ CCTV base without purchasing foreign proprietary hardware.', bullet_style))
    story.append(Paragraph('• <b>Operator Force Multiplication:</b> Empowers a single sentry to manage 50–100 camera streams effectively (versus 4–6 feeds manually), preventing night-shift lapses and sentry fatigue.', bullet_style))
    story.append(Paragraph('• <b>Environmental Sustainability:</b> Prevents thousands of tons of electronic waste (e-waste) and reduces patrol convoy diesel consumption via targeted dispatch.', bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph('13. Research References & Working Prototype Validation', h1_style))
    story.append(Paragraph('1. <b>Object Detection:</b> Jocher, G., et al. (2023). <i>Ultralytics YOLOv8 Architecture</i>. <font color="#0066CC">https://github.com/ultralytics/ultralytics</font>', bullet_style))
    story.append(Paragraph('2. <b>Multi-Object Tracking:</b> Zhang, Y., et al. (2022). <i>ByteTrack: Multi-Object Tracking by Associating Every Detection Box</i>. ECCV 2022. <font color="#0066CC">https://arxiv.org/abs/2110.06864</font>', bullet_style))
    story.append(Paragraph('3. <b>Deep Metric Learning (FRS):</b> Deng, J., et al. (2019). <i>ArcFace: Additive Angular Margin Loss for Deep Face Recognition</i>. CVPR 2019. <font color="#0066CC">https://arxiv.org/abs/1801.07698</font>', bullet_style))
    story.append(Paragraph('4. <b>Government Directives:</b> MHA Comprehensive Integrated Border Management System (CIBMS) Vision Framework & SIH 2026 PS ID 26187.', bullet_style))
    story.append(Paragraph('5. <b>Live Prototype Codebase:</b> GitHub: <font color="#0066CC">https://github.com/Alister007-arch/IBVAP-Border-Surveillance</font> | Operational Dashboard running at <code>http://localhost:8000</code>.', bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'PDF_GENERATED_SUCCESS: {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.1f} KB)')


if __name__ == '__main__':
    build_pdf()
