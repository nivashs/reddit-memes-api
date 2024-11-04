# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
import logging
from . import models
from .database import get_db, engine
from .services.reddit import RedditService
from .services.allmemes import MemeDBService
from .services.telegram_report import TelegramService
from dotenv import load_dotenv
from .schemas import MemeReportRequest 
import os


load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class TelegramCredentials(BaseModel):
    bot_token: Optional[str] = Field(None, description="Telegram Bot Token")
    chat_id: Optional[str] = Field(None, description="Telegram Chat ID")



@app.get("/")
def read_root():
    return {"message": "Reddit Memes API"}

@app.get("/memes/top")
async def get_top_memes(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get top memes and store them in database"""
    try:
        reddit_service = RedditService()
        memes = await reddit_service.fetch_top_memes(limit)
        
        # Store in database
        for meme_data in memes:
            # Check if meme exists
            existing_meme = db.query(models.Meme).filter(
                models.Meme.reddit_id == meme_data["reddit_id"]
            ).first()
            
            if not existing_meme:
                meme = models.Meme(**meme_data)
                db.add(meme)
            else:
                # Update existing meme
                for key, value in meme_data.items():
                    setattr(existing_meme, key, value)
        db.commit()
        return memes
    except Exception as e:
        logger.error(f"Error in get_top_memes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memes/paginated")
async def get_paginated_memes(
    limit: int = Query(50, ge=1, le=100),
    after: Optional[str] = None
):
    """Get paginated memes"""
    try:
        reddit_service = RedditService()
        return await reddit_service.fetch_with_pagination(limit, after)
    except Exception as e:
        logger.error(f"Error in get_paginated_memes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/memes/allmemes")
async def get_meme_history(
    cursor: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(created_at|score|reddit_created_at|num_comments)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Get cursor-paginated meme history"""
    try:
        db_service = MemeDBService(db)
        return db_service.get_paginated_memes(cursor, limit, sort_by, order)
    except Exception as e:
        logger.error(f"Error in get_meme_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/memes/send-report",
    summary="Send meme report to Telegram",
    description="""
    Sends a report of top memes to a Telegram chat.
    
    If no parameters are provided, uses:
    - Default application owner's Telegram bot for Telegram credentials
    - Default limit of 20 memes
    
    You can either:
    1. Send no request body (uses environment variables)
    2. Send only 'limit' to customize number of memes
    3. Provide full credentials in request body
    """,
    response_description="Report sending confirmation"
)
async def send_meme_report(
    background_tasks: BackgroundTasks,
    request: Optional[MemeReportRequest] = None,
    db: Session = Depends(get_db)
):
    """Send meme report to Telegram"""
    try:
        # Handle case when no request body is sent
        if request is None:
            request = MemeReportRequest()

        # Get credentials from request or environment
        bot_token = (request.credentials.bot_token 
                    if request.credentials 
                    else TELEGRAM_BOT_TOKEN)
        chat_id = (request.credentials.chat_id 
                  if request.credentials 
                  else TELEGRAM_CHAT_ID)

        # Use default limit if none provided
        limit = request.limit if request.limit else 20

        # Validate credentials
        if not bot_token:
            raise HTTPException(
                status_code=400,
                detail="Please provide a valid Telegram bot token or set TELEGRAM_BOT_TOKEN environment variable"
            )
        if not chat_id:
            raise HTTPException(
                status_code=400,
                detail="Please provide a valid Telegram chat ID or set TELEGRAM_CHAT_ID environment variable"
            )

        # Get memes
        reddit_service = RedditService()
        memes = await reddit_service.fetch_top_memes(limit)

        # Initialize Telegram service
        telegram_service = TelegramService(bot_token, chat_id)
        
        # Send report in background
        background_tasks.add_task(telegram_service.send_meme_report, memes)
        
        return {
            "message": "Meme report is being sent to Telegram",
            "using_env_credentials": not request.credentials,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"Error in send_meme_report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))