"""
backend/run_server.py
---------------------
Starts the Border Surveillance System backend:
1. HTTP Server on port 8000 (Dashboard & Localhost)
2. HTTPS Server on port 8443 (Secure Mobile Camera Streaming for Android/iOS)
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import asyncio
import logging
import uvicorn

from backend.config.network import get_lan_ip
from backend.generate_ssl_certs import CERT_FILE, KEY_FILE, cert_covers_host, generate_self_signed_cert

import re
import subprocess
import time

logger = logging.getLogger("ServerLauncher")


def ensure_certs(host_ip: str):
    if not CERT_FILE.exists() or not KEY_FILE.exists() or not cert_covers_host(host_ip):
        print("Generating SSL certificates for mobile HTTPS streaming...")
        generate_self_signed_cert(host_ip)


_tunnel_proc = None
_tunnel_url = None
_running_server = True


def _run_tunnel_once():
    global _tunnel_proc, _tunnel_url
    cloudflared_bin = _PROJECT_ROOT / "cloudflared.exe"
    if not cloudflared_bin.exists():
        return None

    print("Initiating Cloudflare Live Tunnel for public access...")
    try:
        proc = subprocess.Popen(
            [str(cloudflared_bin), "tunnel", "--url", "http://localhost:8000"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        _tunnel_proc = proc

        tunnel_url = None
        start_time = time.time()
        while time.time() - start_time < 30:
            if proc.stderr is None:
                break
            line = proc.stderr.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if m:
                tunnel_url = m.group(0)
                break

        if tunnel_url:
            _tunnel_url = tunnel_url
            tunnel_file = _PROJECT_ROOT / "backend" / "config" / "tunnel_url.txt"
            tunnel_file.parent.mkdir(parents=True, exist_ok=True)
            tunnel_file.write_text(tunnel_url, encoding="utf-8")
            print(f"\n[TUNNEL] Live URL captured and registered: {tunnel_url}")
            print(f"[LIVE PUBLIC PREVIEW LINK] : {tunnel_url}")
            print(f"[LIVE MOBILE PATROL LINK]  : {tunnel_url}/phone_stream.html\n")

        import threading

        def _drain(pipe):
            try:
                for _ in iter(pipe.readline, ""):
                    pass
            except Exception:
                pass

        if proc.stderr:
            threading.Thread(target=_drain, args=(proc.stderr,), daemon=True).start()
        if proc.stdout:
            threading.Thread(target=_drain, args=(proc.stdout,), daemon=True).start()

        return proc
    except Exception as e:
        logger.error("Failed to start cloudflared tunnel: %s", e)
        return None


def tunnel_supervisor():
    """Continuously monitors cloudflared. If network drops or tunnel terminates, reconnects automatically."""
    while _running_server:
        proc = _run_tunnel_once()
        if not proc:
            time.sleep(5)
            continue
        while _running_server:
            if proc.poll() is not None:
                print("[TUNNEL] Cloudflare connection lost/disconnected. Re-establishing tunnel in 3s...")
                break
            time.sleep(2)
        if _running_server:
            time.sleep(3)


async def main():
    global _running_server
    host_ip = get_lan_ip()
    ensure_certs(host_ip)

    config_http = uvicorn.Config(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

    config_https = uvicorn.Config(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8443,
        ssl_keyfile=str(KEY_FILE),
        ssl_certfile=str(CERT_FILE),
        log_level="info",
    )

    server_http = uvicorn.Server(config_http)
    server_https = uvicorn.Server(config_https)

    print("=" * 70, flush=True)
    print("[RUNNING] Border Surveillance System (IBVAP) Dual Server", flush=True)
    print(f"[HTTP Dashboard (Local)]   : http://localhost:8000", flush=True)
    print(f"[HTTP Dashboard (LAN)]     : http://{host_ip}:8000", flush=True)
    print(f"[HTTPS Mobile App (LAN)]   : https://{host_ip}:8443/phone_stream.html", flush=True)
    print("=" * 70, flush=True)

    # Launch tunnel supervisor in background thread
    import threading
    supervisor_thread = threading.Thread(target=tunnel_supervisor, daemon=True, name="TunnelSupervisor")
    supervisor_thread.start()

    try:
        await asyncio.gather(
            server_http.serve(),
            server_https.serve(),
        )
    finally:
        _running_server = False
        if _tunnel_proc:
            print("Stopping Cloudflare tunnel...")
            _tunnel_proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())


