import ipaddress
from typing import Optional

from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    raw = request.headers.get("x-real-ip")
    if not raw:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            raw = xff.split(",")[0].strip()
    if not raw and request.client:
        raw = request.client.host
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None
