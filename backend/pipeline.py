"""
backend/pipeline.py
---------------------
Phase 1 pipeline runner: ingestion → Tier-1 detection → OpenCV preview window.

Usage
-----
  python backend/pipeline.py                          # uses demo_assets/sample.mp4
  python backend/pipeline.py --source path/to/clip.mp4
  python backend/pipeline.py --source 0              # webcam index 0
  python backend/pipeline.py --camera-id cam_01 --location "North Gate"
  python backend/pipeline.py --no-preview            # headless, prints stats only
  python backend/pipeline.py --save-output out.mp4   # write annotated video to file

Exit the preview window by pressing Q.

Architecture
------------
This module is intentionally simple and self-contained for Phase 1.
Phase 2 will replace the OpenCV preview with a FastAPI + WebSocket pipeline
and wrap this logic inside an async pipeline runner.

The ingestion → detection → visualiser pattern established here is the
same one used in all later phases — later phases only add stages *after*
detection (tracking, re-ID, alerts) and inject results *before* the
visualiser.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2

# Ensure project root is on sys.path when run directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.ingestion.video_source import VideoFileSource, WebcamSource
from backend.detection.tier1_yolo import Tier1Detector
from backend.detection.visualizer import draw_detections
from backend.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Border Surveillance — Phase 1 pipeline (ingestion + detection preview)"
    )
    p.add_argument(
        "--source",
        default="demo_assets/sample.mp4",
        help="Video source: path to a video file, or an integer webcam index (default: demo_assets/sample.mp4)",
    )
    p.add_argument("--camera-id", default="cam_01", help="Camera ID label (default: cam_01)")
    p.add_argument("--location", default="North Gate", help="Location name (default: North Gate)")
    p.add_argument(
        "--model",
        default=None,
        help="Path to a YOLO .pt model file (default: yolov8n.pt, auto-downloaded)",
    )
    p.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Override detection confidence threshold (0-1)",
    )
    p.add_argument(
        "--no-preview",
        action="store_true",
        help="Disable the OpenCV window; only print statistics to stdout",
    )
    p.add_argument(
        "--save-output",
        default=None,
        help="If set, write the annotated frames to this path (e.g. out.mp4)",
    )
    p.add_argument(
        "--show-tier",
        action="store_true",
        help="Show source tier in each detection label",
    )
    p.add_argument(
        "--boundary",
        default=None,
        help=(
            "Draw a virtual boundary line as 'x1,y1,x2,y2' in pixel coords "
            "(e.g. --boundary 0,240,854,240 for a horizontal line at y=240)"
        ),
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Boundary line parser
# ---------------------------------------------------------------------------

def parse_boundary(spec: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    if spec is None:
        return None
    try:
        parts = [int(v) for v in spec.split(",")]
        assert len(parts) == 4
        return (parts[0], parts[1]), (parts[2], parts[3])
    except Exception:
        logger.warning("Invalid --boundary spec '%s'. Expected 'x1,y1,x2,y2'. Ignoring.", spec)
        return None


# ---------------------------------------------------------------------------
# Source factory
# ---------------------------------------------------------------------------

def build_source(source_str: str, camera_id: str, location: str):
    try:
        idx = int(source_str)
        logger.info("Source detected as webcam index %d", idx)
        return WebcamSource(camera_id=camera_id, location=location, device_index=idx)
    except ValueError:
        path = Path(source_str)
        logger.info("Source detected as video file: %s", path)
        return VideoFileSource(camera_id=camera_id, location=location, source_path=path, loop=True)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    # Build source adapter
    source = build_source(args.source, args.camera_id, args.location)

    # Load detector
    detector = Tier1Detector(model_path=args.model or "yolov8n.pt")

    # Optional boundary line
    boundary = parse_boundary(args.boundary) if args.boundary else None

    # Optional output video writer (initialised on first frame)
    writer = None

    # Preview window name
    win_name = f"Border Surveillance — {args.camera_id} [{args.location}]"
    preview = not args.no_preview

    if preview:
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 960, 540)

    # Stats
    frame_count = 0
    total_detections = 0
    t_start = time.perf_counter()
    fps_report_interval = 30   # print FPS every N frames

    logger.info("=" * 60)
    logger.info("Border Surveillance System — Phase 1")
    logger.info("Source   : %s", args.source)
    logger.info("Camera   : %s | %s", args.camera_id, args.location)
    logger.info("Preview  : %s", "ON" if preview else "OFF (headless)")
    logger.info("Boundary : %s", boundary or "none")
    logger.info("=" * 60)
    logger.info("Press Q in the preview window to quit.")

    try:
        for frame in source.frames():
            # ── Tier-1 detection ────────────────────────────────────────────
            detections = detector.detect(frame, confidence=args.confidence)
            total_detections += len(detections)
            frame_count += 1

            # ── Visualise ───────────────────────────────────────────────────
            annotated = draw_detections(
                frame, detections,
                boundary_line=boundary,
                show_tier=args.show_tier,
            )

            # ── FPS HUD overlay ─────────────────────────────────────────────
            elapsed = time.perf_counter() - t_start
            avg_fps = frame_count / elapsed if elapsed > 0 else 0
            cv2.putText(
                annotated,
                f"FPS: {avg_fps:.1f}",
                (annotated.shape[1] - 110, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA,
            )

            # ── OpenCV preview ──────────────────────────────────────────────
            if preview:
                cv2.imshow(win_name, annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:   # Q or Escape to quit
                    logger.info("User requested quit (key press).")
                    break

            # ── Optional file output ────────────────────────────────────────
            if args.save_output:
                if writer is None:
                    h, w = annotated.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(
                        args.save_output, fourcc,
                        settings.pipeline.target_fps, (w, h)
                    )
                    logger.info("Writing output to: %s", args.save_output)
                writer.write(annotated)

            # ── Periodic stats ──────────────────────────────────────────────
            if frame_count % fps_report_interval == 0:
                brightness = frame.compute_brightness()
                night_mode = brightness < settings.detection.night_brightness_threshold
                logger.info(
                    "Frame %5d | %5.1f fps | brightness %.0f (%s) | detections this run: %d",
                    frame_count, avg_fps, brightness,
                    "NIGHT" if night_mode else "DAY",
                    total_detections,
                )

    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C).")

    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    finally:
        if preview:
            cv2.destroyAllWindows()
        if writer is not None:
            writer.release()
            logger.info("Output video saved to: %s", args.save_output)

        elapsed = time.perf_counter() - t_start
        logger.info(
            "Done.  Processed %d frames in %.1fs (avg %.1f fps).  Total detections: %d",
            frame_count, elapsed, frame_count / elapsed if elapsed > 0 else 0,
            total_detections,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run(parse_args())
