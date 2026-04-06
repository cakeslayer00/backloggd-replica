from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.core.redis import (
    add_token_to_blocklist,
    is_token_blocked,
    verify_confirmation_token,
    delete_confirmation_token,
    verify_reset_token,
    delete_reset_token,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.dependencies import get_current_user, http_bearer
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserRegister, UserResponse, UserLogin
from app.tasks.email_tasks import send_confirmation_email, send_password_reset_email
from app.tasks.export_tasks import export_user_backlog_to_csv

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        is_active=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    send_confirmation_email.delay(user.id, user.email, user.username)

    return user


@router.post("/confirm-email")
async def confirm_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    token_data = await verify_confirmation_token(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == token_data["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()
    await delete_confirmation_token(token)

    return {"detail": "Email confirmed successfully"}


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(
            status_code=403, detail="Please confirm your email before logging in"
        )

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", status_code=200)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
):
    token = credentials.credentials
    payload = decode_access_token(token)

    jti: str = payload.get("jti")
    exp: int = payload.get("exp")

    if await is_token_blocked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    now = int(datetime.now(timezone.utc).timestamp())
    remaining_seconds = exp - now

    if remaining_seconds > 0:
        await add_token_to_blocklist(jti, remaining_seconds)

    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user:
        send_password_reset_email.delay(user.id, user.email, user.username)

    return {"detail": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = await verify_reset_token(payload.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    await delete_reset_token(payload.token)

    return {"detail": "Password has been reset successfully"}


@router.post("/export-backlog")
async def request_backlog_export(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = export_user_backlog_to_csv.delay(
        current_user.id, current_user.username, current_user.email
    )
    return {
        "task_id": task.id,
        "detail": "Export requested. Check your email for the CSV file.",
    }
