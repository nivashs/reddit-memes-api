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
from sqlalchemy import text
from datetime import datetime
from .scheduler import init_scheduler
import os


load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
scheduler = init_scheduler(app)

# Get origins from environment variables
ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5173,https://reddit-memes-ui.vercel.app')
allowed_origins = ORIGINS.split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class TelegramCredentials(BaseModel):
    bot_token: Optional[str] = Field(None, description="Telegram Bot Token")
    chat_id: Optional[str] = Field(None, description="Telegram Chat ID")

@app.get("/health",
    summary="Check API health status",
    description="Checks the health of the API including Reddit API and database connections",
    response_description="Health status of different components"
)
async def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": {
                "status": "healthy",
                "details": "FastAPI server is running"
            },
            "reddit_api": {
                "status": "unknown",
                "details": None
            },
            "database": {
                "status": "unknown",
                "details": None
            }
        }
    }
    
    # Check Reddit API
    try:
        async with RedditService() as reddit_service:
            await reddit_service.fetch_top_memes(1)
            health_status["components"]["reddit_api"] = {
                "status": "healthy",
                "details": "Successfully connected to Reddit API"
            }
    except Exception as e:
        health_status["components"]["reddit_api"] = {
            "status": "unhealthy",
            "details": f"Failed to connect to Reddit API: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Check database
    try:
        # Simple query to check database connection
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "details": "Successfully connected to database"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "details": f"Failed to connect to database: {str(e)}"
        }
        health_status["status"] = "degraded"

    # If any component is unhealthy, set response code to 503
    if health_status["status"] != "healthy":
        raise HTTPException(
            status_code=503,
            detail=health_status
        )

    return health_status

@app.get("/memes/top")
async def get_top_memes(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get top memes and store them in database"""
    try:
        # Use async context manager for RedditService
        async with RedditService() as reddit_service:
            memes = await reddit_service.fetch_top_memes(limit)
            
            # Store in database
            for meme_data in memes:
                existing_meme = db.query(models.Meme).filter(
                    models.Meme.reddit_id == meme_data["reddit_id"]
                ).first()
                
                if not existing_meme:
                    meme = models.Meme(**meme_data)
                    db.add(meme)
                else:
                    for key, value in meme_data.items():
                        setattr(existing_meme, key, value)
            db.commit()
            return memes
    except Exception as e:
        logger.error(f"Error in get_top_memes: {e}")
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
        async with RedditService() as reddit_service:
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