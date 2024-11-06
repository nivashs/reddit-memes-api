# app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from .services.reddit import RedditService
from .services.telegram_report import TelegramService
import os

logger = logging.getLogger(__name__)

async def send_scheduled_report():
    """Send periodic meme report to Telegram"""
    try:
        # Get credentials from environment
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            logger.error("Missing Telegram credentials in environment variables")
            return
        # Fetch memes
        async with RedditService() as reddit_service:
            memes = await reddit_service.fetch_top_memes(20)
        # Send report
        telegram_service = TelegramService(bot_token, chat_id)
        await telegram_service.send_meme_report(memes)
        
        logger.info("Successfully sent scheduled meme report")
            
    except Exception as e:
        logger.error(f"Error in scheduled meme report: {str(e)}")

def init_scheduler(app):
    """Initialize the scheduler"""
    scheduler = AsyncIOScheduler()
    # Schedule task to run every  minute
    scheduler.add_job(
        send_scheduled_report,
        CronTrigger(hour="0,8,16"),#IntervalTrigger(minutes=10)
        id="meme_report",
        name="Send meme report to Telegram",
        replace_existing=True
    )
    
    # Start scheduler on app startup
    @app.on_event("startup")
    async def start_scheduler():
        scheduler.start()
        logger.info("Started scheduled meme reports")
    
    # Shutdown scheduler when app stops
    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
        logger.info("Stopped scheduled meme reports")

    return scheduler