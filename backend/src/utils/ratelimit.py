from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings

# Use Redis as the backend so limits survive restarts and work across multiple instances.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url or None,
)
