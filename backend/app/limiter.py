import os
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)

limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED,
)
