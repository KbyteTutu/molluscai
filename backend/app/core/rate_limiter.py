"""
Rate limiter stub using slowapi.
Full integration with role-based dynamic limits comes in P5.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
