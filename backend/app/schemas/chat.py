from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
