from redis.asyncio import Redis
from app.core.config import settings

redis_client: Redis = Redis.from_url(
    settings.redis_url, encoding="utf-8", decode_responses=True
)


async def add_token_to_blocklist(jti: str, expires_in_seconds: int) -> None:
    await redis_client.setex(f"blocklist:{jti}", expires_in_seconds, "true")


async def is_token_blocked(jti: str) -> bool:
    return await redis_client.exists(f"blocklist:{jti}") == 1


CONFIRM_TTL = 24 * 60 * 60
RESET_TTL = 60 * 60


async def store_confirmation_token(token: str, user_id: int, email: str) -> None:
    await redis_client.setex(f"confirm:{token}", CONFIRM_TTL, f"{user_id}:{email}")


async def verify_confirmation_token(token: str) -> dict | None:
    data = await redis_client.get(f"confirm:{token}")
    if not data:
        return None
    user_id, email = data.split(":")
    return {"user_id": int(user_id), "email": email}


async def delete_confirmation_token(token: str) -> None:
    await redis_client.delete(f"confirm:{token}")


async def store_reset_token(token: str, user_id: int) -> None:
    await redis_client.setex(f"reset:{token}", RESET_TTL, str(user_id))


async def verify_reset_token(token: str) -> int | None:
    user_id = await redis_client.get(f"reset:{token}")
    if not user_id:
        return None
    return int(user_id)


async def delete_reset_token(token: str) -> None:
    await redis_client.delete(f"reset:{token}")
