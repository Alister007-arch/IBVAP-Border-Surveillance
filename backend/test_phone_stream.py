"""
backend/test_phone_stream.py
----------------------------
Simulates a phone streaming video frames to /ws/phone/phone_01.
"""

import asyncio
import base64
import cv2
import numpy as np
import websockets


async def stream_synthetic_phone():
    uri = "ws://127.0.0.1:8000/ws/phone/phone_01"
    print(f"Connecting to phone stream endpoint: {uri}...")
    async with websockets.connect(uri) as ws:
        print("Connected as phone_01. Sending test frames...")
        for i in range(10):
            # Create a test frame
            img = np.zeros((480, 854, 3), dtype=np.uint8)
            img[:240, :] = [200, 150, 100]
            img[240:, :] = [50, 100, 50]
            # Draw person
            px = int(100 + i * 40)
            py = int(240)
            cv2.circle(img, (px, py - 30), 15, (20, 20, 20), -1)
            cv2.rectangle(img, (px - 15, py - 15), (px + 15, py + 30), (30, 40, 120), -1)

            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
            await ws.send(b64)
            await asyncio.sleep(0.1)
        print("Successfully sent 10 phone frames!")


if __name__ == "__main__":
    asyncio.run(stream_synthetic_phone())
