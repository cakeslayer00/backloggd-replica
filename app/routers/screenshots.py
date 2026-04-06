import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.backlog_entry import BacklogEntry
from app.models.screenshot import Screenshot
from app.models.user import User
from app.schemas.screenshot import ScreenshotResponse
from app.tasks.image_tasks import compress_and_upload_image

router = APIRouter(prefix="/api/backlog", tags=["screenshots"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
TMP_DIR = "/tmp/screenshots"


@router.get("/{entry_id}/screenshots", response_model=list[ScreenshotResponse])
async def list_screenshots(
        entry_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backlog entry not found")

    result = await db.execute(select(Screenshot).where(Screenshot.entry_id == entry_id))
    return result.scalars().all()


@router.post(
    "/{entry_id}/screenshots", response_model=ScreenshotResponse, status_code=202
)
async def upload_screenshot(
        entry_id: int,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backlog entry not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    contents = await file.read()

    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB")

    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_filename = f"{uuid.uuid4()}_{file.filename}"
    tmp_path = os.path.join(TMP_DIR, tmp_filename)

    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(contents)

    screenshot = Screenshot(
        entry_id=entry_id,
        file_url=tmp_path,
        file_size_bytes=len(contents),
        status="processing",
    )
    db.add(screenshot)
    await db.commit()
    await db.refresh(screenshot)

    compress_and_upload_image.delay(screenshot.id, tmp_path)

    return screenshot


@router.delete("/{entry_id}/screenshots/{screenshot_id}", status_code=204)
async def delete_screenshot(
        entry_id: int,
        screenshot_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backlog entry not found")

    result = await db.execute(
        select(Screenshot).where(
            Screenshot.id == screenshot_id,
            Screenshot.entry_id == entry_id,
        )
    )
    screenshot = result.scalar_one_or_none()
    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    await db.delete(screenshot)
    await db.commit()
