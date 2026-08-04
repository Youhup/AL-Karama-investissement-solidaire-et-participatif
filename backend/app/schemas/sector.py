from pydantic import BaseModel


class SectorOut(BaseModel):
    id: int
    name: str
    description: str | None

    class Config:
        from_attributes = True
