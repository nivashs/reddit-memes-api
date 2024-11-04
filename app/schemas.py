from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class MemeBase(BaseModel):
    title: str
    url: str
    score: int
    upvote_ratio: float
    author: str
    num_comments: int
    permalink: str
    thumbnail: Optional[str]
    is_video: bool = False

class MemeCreate(MemeBase):
    reddit_id: str
    reddit_created_at: datetime

class Meme(MemeBase):
    id: int
    reddit_id: str
    created_at: datetime
    reddit_created_at: datetime

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    memes: List[Meme]
    next_page: Optional[str]
    total: int

class TelegramCredentials(BaseModel):
    bot_token: Optional[str] = Field(
        None,
        description="Telegram Bot Token obtained from BotFather",
        example="1234567890:ABCdefGHIjklMNOpqrSTUVwxyz"
    )
    chat_id: Optional[str] = Field(
        None,
        description="Telegram Chat ID where the report will be sent",
        example="-100123456789"
    )

class MemeReportRequest(BaseModel):
    credentials: Optional[TelegramCredentials] = None
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Number of memes to include in the report (default: 20)"
    )