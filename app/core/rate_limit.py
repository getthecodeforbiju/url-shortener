from slowapi import Limiter
from slowapi.util import get_remote_address
from config import get_settings

settings = get_settings()

# One shared limiter instance - imported by all endpoint routers
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minutes"],
)