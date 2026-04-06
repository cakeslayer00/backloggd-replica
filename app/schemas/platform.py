from pydantic import BaseModel


class PlatformCreate(BaseModel):
    name: str


class PlatformResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}