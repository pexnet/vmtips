"""
Shared rate limiter instance for the VMTips application.

All routers and main.py import limiter from this module to avoid circular
imports (routers can't import from main.py since main.py imports routers).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)