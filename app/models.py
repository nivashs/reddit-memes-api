from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from .database import Base
from datetime import datetime

class Meme(Base):
    __tablename__ = "memes"

    id = Column(Integer, primary_key=True, index=True)
    reddit_id = Column(String, unique=True, index=True)
    title = Column(String)
    url = Column(String)
    score = Column(Integer)
    upvote_ratio = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    reddit_created_at = Column(DateTime)
    author = Column(String)
    num_comments = Column(Integer)
    permalink = Column(String)
    thumbnail = Column(String, nullable=True)
    is_video = Column(Boolean, default=False)