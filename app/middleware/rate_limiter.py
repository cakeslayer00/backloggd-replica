import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.redis import redis_client

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = get_client_ip(request)

        # check per-minute limit (60 req/min)
        minute_key = f"ratelimit:{ip}:minute"
        minute_count = await self._increment(minute_key, ttl=60)
        if minute_count > 60:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests — per minute limit exceeded"},
                headers={"Retry-After": "60"},
            )

        # check per-hour limit (1000 req/hr)
        hour_key = f"ratelimit:{ip}:hour"
        hour_count = await self._increment(hour_key, ttl=3600)
        if hour_count > 1000:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests — per hour limit exceeded"},
                headers={"Retry-After": "3600"},
            )

        # check write limit (50 writes/hr) — reads are unlimited
        if request.method in WRITE_METHODS:
            write_key = f"ratelimit:{ip}:write:hour"
            write_count = await self._increment(write_key, ttl=3600)
            if write_count > 50:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many write requests — hourly write limit exceeded"},
                    headers={"Retry-After": "3600"},
                )

        return await call_next(request)

    async def _increment(self, key: str, ttl: int) -> int:
        count = await redis_client.incr(key)
        if count == 1:
            # first request in this window — set the expiry
            await redis_client.expire(key, ttl)
        return count