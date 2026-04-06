from pydantic import BaseModel
from app.models.backlog_entry import BacklogStatus, BacklogPriority
from app.schemas.game import GameResponse


class BacklogEntryCreate(BaseModel):
    game_id: int
    status: BacklogStatus = BacklogStatus.want_to_play
    priority: BacklogPriority = BacklogPriority.medium
    hours_played: int | None = None


class BacklogEntryUpdate(BaseModel):
    status: BacklogStatus | None = None
    priority: BacklogPriority | None = None
    hours_played: int | None = None


class BacklogEntryResponse(BaseModel):
    id: int
    game_id: int
    status: BacklogStatus
    priority: BacklogPriority
    hours_played: int | None
    game: GameResponse

    model_config = {"from_attributes": True}