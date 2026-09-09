"""
Network helpers for dashboard/mobile pairing.
"""

from __future__ import annotations

import socket


def get_lan_ip(default: str = "127.0.0.1") -> str:
    """
    Return the local IPv4 address other devices on the LAN should use.

    The UDP connect does not send traffic; it asks the OS which interface would
    be used for an external route. Fallbacks keep local-only demos working.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    return default


def get_local_ipv4_addresses() -> list[str]:
    addresses = {"127.0.0.1", get_lan_ip()}
    try:
        hostname = socket.gethostname()
        addresses.update(socket.gethostbyname_ex(hostname)[2])
    except OSError:
        pass
    return sorted(ip for ip in addresses if ip)
