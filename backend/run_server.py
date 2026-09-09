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

logger = logging.getLogger("ServerLauncher")


def ensure_certs(host_ip: str):
    if not CERT_FILE.exists() or not KEY_FILE.exists() or not cert_covers_host(host_ip):
        print("Generating SSL certificates for mobile HTTPS streaming...")
        generate_self_signed_cert(host_ip)


async def main():
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

    print("=" * 60)
    print("[RUNNING] Border Surveillance System Dual Server")
    print("[HTTP Dashboard]   : http://localhost:8000")
    print(f"[HTTPS Mobile App] : https://{host_ip}:8443/phone_stream.html")
    print("=" * 60)

    await asyncio.gather(
        server_http.serve(),
        server_https.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
