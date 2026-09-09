"""
demo_assets/generate_synthetic_demos.py
---------------------------------------
Generates synthetic MP4 test clips for testing the pipeline end-to-end:
1. demo_assets/sample.mp4         — daytime clip with objects moving & crossing
2. demo_assets/night_sample.mp4   — low-light/night clip for auto-switching test
3. demo_assets/crowd_sample.mp4   — multiple close objects for event grouping
4. demo_assets/drone_sample.mp4   — small aerial object moving across sky

Run:
    python demo_assets/generate_synthetic_demos.py
"""

import os
from pathlib import Path
import cv2
import numpy as np

OUTPUT_DIR = Path(__file__).parent


def create_daytime_clip(filename: str = "sample.mp4", duration_sec: int = 6, fps: int = 15):
    out_path = OUTPUT_DIR / filename
    w, h = 854, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for i in range(total_frames):
        # Daytime outdoor background (green/brown ground, blue sky)
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[: h // 2, :] = [210, 160, 100]  # Light sky (BGR)
        img[h // 2 :, :] = [60, 110, 60]  # Grass field (BGR)

        # Virtual border line (fence post markers)
        cv2.line(img, (0, 240), (w, 240), (40, 40, 180), 2)

        # Moving person (simulated person shape crossing from top to bottom)
        t = i / total_frames
        px = int(150 + t * 400)
        py = int(120 + t * 240)

        # Draw a humanoid silhouette
        cv2.circle(img, (px, py - 35), 12, (20, 20, 20), -1)  # head
        cv2.rectangle(img, (px - 14, py - 22), (px + 14, py + 20), (40, 50, 120), -1)  # torso
        cv2.line(img, (px - 8, py + 20), (px - 12, py + 55), (30, 30, 30), 5)  # leg 1
        cv2.line(img, (px + 8, py + 20), (px + 12, py + 55), (30, 30, 30), 5)  # leg 2

        # A moving vehicle (box shape)
        vx = int(700 - t * 500)
        vy = 360
        cv2.rectangle(img, (vx - 40, vy - 20), (vx + 40, vy + 20), (160, 60, 40), -1)
        cv2.circle(img, (vx - 25, vy + 20), 8, (10, 10, 10), -1)
        cv2.circle(img, (vx + 25, vy + 20), 8, (10, 10, 10), -1)

        writer.write(img)

    writer.release()
    print(f"Generated {out_path} ({total_frames} frames)")


def create_night_clip(filename: str = "night_sample.mp4", duration_sec: int = 6, fps: int = 15):
    out_path = OUTPUT_DIR / filename
    w, h = 854, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for i in range(total_frames):
        # Very dark background (mean brightness ~ 25)
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[: h // 2, :] = [30, 25, 20]  # Dark night sky
        img[h // 2 :, :] = [18, 22, 18]  # Dark ground

        # Border line faint
        cv2.line(img, (0, 240), (w, 240), (30, 30, 60), 1)

        # Faint low-contrast moving object
        t = i / total_frames
        px = int(200 + t * 300)
        py = int(180 + t * 100)

        cv2.circle(img, (px, py - 30), 10, (50, 50, 50), -1)
        cv2.rectangle(img, (px - 12, py - 18), (px + 12, py + 18), (45, 45, 55), -1)
        cv2.line(img, (px - 6, py + 18), (px - 10, py + 45), (40, 40, 40), 4)
        cv2.line(img, (px + 6, py + 18), (px + 10, py + 45), (40, 40, 40), 4)

        # Add camera sensor noise
        noise = np.random.normal(0, 5, img.shape).astype(np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        writer.write(noisy)

    writer.release()
    print(f"Generated {out_path} ({total_frames} frames)")


def create_crowd_clip(filename: str = "crowd_sample.mp4", duration_sec: int = 6, fps: int = 15):
    out_path = OUTPUT_DIR / filename
    w, h = 854, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for i in range(total_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[: h // 2, :] = [210, 160, 100]
        img[h // 2 :, :] = [60, 110, 60]

        cv2.line(img, (0, 240), (w, 240), (40, 40, 180), 2)

        t = i / total_frames
        base_x = int(100 + t * 400)
        base_y = int(140 + t * 180)

        # Three people moving closely together (Group of 3)
        offsets = [(0, 0), (35, 10), (-30, 20)]
        colors = [(30, 50, 120), (120, 40, 50), (40, 120, 60)]

        for (ox, oy), col in zip(offsets, colors):
            px = base_x + ox
            py = base_y + oy
            cv2.circle(img, (px, py - 30), 10, (20, 20, 20), -1)
            cv2.rectangle(img, (px - 10, py - 18), (px + 10, py + 18), col, -1)
            cv2.line(img, (px - 5, py + 18), (px - 8, py + 45), (30, 30, 30), 4)
            cv2.line(img, (px + 5, py + 18), (px + 8, py + 45), (30, 30, 30), 4)

        writer.write(img)

    writer.release()
    print(f"Generated {out_path} ({total_frames} frames)")


def create_drone_clip(filename: str = "drone_sample.mp4", duration_sec: int = 6, fps: int = 15):
    out_path = OUTPUT_DIR / filename
    w, h = 854, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for i in range(total_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[: h // 2, :] = [220, 180, 120]  # Clear sky
        img[h // 2 :, :] = [60, 110, 60]

        cv2.line(img, (0, 240), (w, 240), (40, 40, 180), 2)

        # Small drone quadcopter moving fast across the sky
        t = i / total_frames
        dx = int(50 + t * 700)
        dy = int(60 + np.sin(t * 6.28 * 2) * 20)

        # Draw small quadcopter (approx 24x12 px)
        cv2.rectangle(img, (dx - 10, dy - 3), (dx + 10, dy + 3), (40, 40, 40), -1)
        cv2.line(img, (dx - 14, dy - 8), (dx + 14, dy - 8), (20, 20, 20), 2)
        cv2.circle(img, (dx - 14, dy - 8), 3, (200, 200, 200), -1)
        cv2.circle(img, (dx + 14, dy - 8), 3, (200, 200, 200), -1)

        writer.write(img)

    writer.release()
    print(f"Generated {out_path} ({total_frames} frames)")


if __name__ == "__main__":
    print("Generating test video assets...")
    create_daytime_clip()
    create_night_clip()
    create_crowd_clip()
    create_drone_clip()
    print("All synthetic demo clips generated successfully!")
