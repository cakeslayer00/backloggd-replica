import hashlib
import time
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.config import settings

CONFIRM_PREFIX = "email_confirm:"
RESET_PREFIX = "password_reset:"

TTL_CONFIRM = 24 * 60 * 60
TTL_RESET = 60 * 60


def generate_confirmation_token(user_id: int, email: str) -> str:
    data = f"{user_id}:{email}:{time.time()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def generate_reset_token(user_id: int, email: str) -> str:
    data = f"reset:{user_id}:{email}:{time.time()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]
