# app/services/telegram.py
import requests
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_meme_report(self, memes: List[Dict]) -> bool:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"🎯 Top {len(memes)} Memes Report - {current_time}\n\n"

            for i, meme in enumerate(memes, 1):
                message += (
                    f"{i}. {meme['title']}\n"
                    f"👍 Score: {meme['score']} | 💬 Comments: {meme['num_comments']}\n"
                    f"🔗 {meme['permalink']}\n\n"
                )

            # Split message if it's too long (Telegram has 4096 characters limit)
            if len(message) > 4000:
                message = message[:4000] + "\n\n... (message truncated)"

            # Send message
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            logger.info("Successfully sent meme report to Telegram")
            return True

        except requests.RequestException as e:
            logger.error(f"Error sending message to Telegram: {e}")
            raise