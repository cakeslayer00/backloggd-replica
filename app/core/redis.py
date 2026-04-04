from redis.asyncio import Redis
from app.core.config import settings

redis_client: Redis = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True
)

async def add_token_to_blocklist(jti: str, expires_in_seconds: int) -> None:
    await redis_client.setex(f"blocklist:{jti}", expires_in_seconds, "true")

async def is_token_blocked(jti: str) -> bool:
    return await redis_client.exists(f"blocklist:{jti}") == 1