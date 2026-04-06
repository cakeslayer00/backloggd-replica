from pydantic import BaseModel, Field
from datetime import datetime


class ReviewCreate(BaseModel):
    game_id: int
    score: int = Field(ge=1, le=10)
    body: str | None = None
    is_spoiler: bool = False


class ReviewUpdate(BaseModel):
    score: int | None = Field(default=None, ge=1, le=10)
    body: str | None = None
    is_spoiler: bool | None = None


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    game_id: int
    score: int
    body: str | None
    is_spoiler: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}