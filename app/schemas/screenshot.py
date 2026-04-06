from pydantic import BaseModel
from datetime import datetime
from app.models.screenshot import ScreenshotStatus


class ScreenshotResponse(BaseModel):
    id: int
    entry_id: int
    file_url: str
    file_size_bytes: int | None
    status: ScreenshotStatus
    created_at: datetime

    model_config = {"from_attributes": True}
