from pydantic import BaseModel, field_validator
from app.schemas.platform import PlatformResponse


class GameCreate(BaseModel):
    title: str
    description: str | None = None
    release_year: int | None = None
    cover_image_url: str | None = None
    platform_ids: list[int] = []


class GameUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    release_year: int | None = None
    cover_image_url: str | None = None
    platform_ids: list[int] | None = None


class GameResponse(BaseModel):
    id: int
    title: str
    description: str | None
    release_year: int | None
    cover_image_url: str | None
    platforms: list[PlatformResponse] = []

    model_config = {"from_attributes": True}

    @field_validator("platforms", mode="before")
    @classmethod
    def extract_platforms(cls, v):
        from app.models.game import GamePlatform

        if v and isinstance(v, (list, tuple)):
            if len(v) > 0 and hasattr(v[0], "platform"):
                return [PlatformResponse.model_validate(gp.platform) for gp in v]
        return v
