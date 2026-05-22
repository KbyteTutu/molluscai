import ipaddress
from typing import Optional

from fastapi import Request

# IP ranges that are never real client IPs when found in X-Forwarded-For.
_PROXY_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),       # private A
    ipaddress.ip_network("172.16.0.0/12"),    # private B (includes Docker 172.18.x)
    ipaddress.ip_network("192.168.0.0/16"),   # private C
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("::1/128"),          # ipv6 loopback
    ipaddress.ip_network("fc00::/7"),         # ipv6 unique local
]


def _is_private_ip(text: str) -> bool:
    """Return True if this IP is definitely not a real client IP."""
    # PostgreSQL INET may include a /prefix suffix; strip it.
    text = text.split("/")[0].strip()
    try:
        addr = ipaddress.ip_address(text)
        return any(addr in net for net in _PROXY_NETS)
    except ValueError:
        return False


def get_client_ip(request: Request) -> Optional[str]:
    # Prefer X-Real-IP set by a trusted reverse proxy (e.g. nginx with
    # proxy_set_header X-Real-IP $remote_addr).  If the WAF fills in the real
    # client IP it is usually present here as a single value.
    raw = request.headers.get("x-real-ip")
    if raw:
        try:
            return str(ipaddress.ip_address(raw.strip()))
        except ValueError:
            pass  # fall through to X-Forwarded-For

    # Walk the X-Forwarded-For chain from left (origin client) to right,
    # returning the first IP that is NOT a known proxy/private address.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        for part in xff.split(","):
            candidate = part.strip()
            if candidate and not _is_private_ip(candidate):
                return candidate

    # Last-resort: direct TCP connection (e.g. Docker bridge IP).
    if request.client:
        raw = request.client.host
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            return None

    return None


def get_display_ip(raw_ip: Optional[str]) -> Optional[str]:
    """Human-readable IP for admin pages.

    Falls back from the stored raw IP: if it is a known internal address
    we mark it explicitly so operators can tell it was an internal hit.
    """
    if not raw_ip:
        return None
    if _is_private_ip(raw_ip):
        return f"{raw_ip} (内网)"
    return raw_ip
