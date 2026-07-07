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


def _parse_ip(text: str) -> Optional[str]:
    """Return a normalized IP address, or None for malformed proxy values."""
    text = (text or "").strip().strip('"')
    if not text:
        return None

    # PostgreSQL INET may include a /prefix suffix; strip it.
    text = text.split("/")[0].strip()

    # Some proxies append a port to IPv4 addresses in X-Forwarded-For.
    if text.count(":") == 1 and "." in text:
        host, port = text.rsplit(":", 1)
        if port.isdigit():
            text = host

    # Bracketed IPv6 with port, e.g. [2001:db8::1]:443.
    if text.startswith("[") and "]" in text:
        text = text[1:text.index("]")]

    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def _is_private_ip(text: str) -> bool:
    """Return True if this IP is definitely not a real client IP."""
    parsed = _parse_ip(text)
    if parsed is None:
        return False
    addr = ipaddress.ip_address(parsed)
    return any(addr in net for net in _PROXY_NETS)


def get_client_ip(request: Request) -> Optional[str]:
    # Prefer X-Real-IP set by a trusted reverse proxy (e.g. nginx with
    # proxy_set_header X-Real-IP $remote_addr).  If the WAF fills in the real
    # client IP it is usually present here as a single value.
    raw = request.headers.get("x-real-ip")
    if raw:
        parsed = _parse_ip(raw)
        if parsed:
            return parsed

    # Walk the X-Forwarded-For chain from left (origin client) to right,
    # returning the first IP that is NOT a known proxy/private address.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        for part in xff.split(","):
            candidate = _parse_ip(part)
            if candidate and not _is_private_ip(candidate):
                return candidate

    # Last-resort: direct TCP connection (e.g. Docker bridge IP).
    if request.client:
        return _parse_ip(request.client.host)

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
