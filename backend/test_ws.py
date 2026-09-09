"""
backend/test_ws.py
------------------
Automated verification script for WebSocket frame and alert streaming.
"""

import asyncio
import json
import websockets


async def test_alerts():
    uri = "ws://127.0.0.1:8000/ws/alerts"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        for i in range(3):
            # Wait for alert message or timeout
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            print(f"[WS Alert Received #{i+1}]: Type={data.get('type')}, Category={data.get('payload', {}).get('category')}, Priority={data.get('payload', {}).get('priority')}")
    print("Alert WebSocket test PASSED!")


async def test_frames():
    uri = "ws://127.0.0.1:8000/ws/frames/cam_01"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        for i in range(3):
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            data_len = len(data.get("data", ""))
            print(f"[WS Frame Received #{i+1}]: Camera={data.get('camera_id')}, Base64 JPEG Length={data_len} bytes")
    print("Frame WebSocket test PASSED!")


async def main():
    print("--- Running WebSocket Verification ---")
    await test_frames()
    await test_alerts()
    print("All WebSocket tests PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
