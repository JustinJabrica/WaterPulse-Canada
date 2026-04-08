from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage (default). For AWS with multiple replicas, swap to Redis:
# limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379")
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
