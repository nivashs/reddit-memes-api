# app/services/reddit.py
import aiohttp
import base64
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RedditService:
    def __init__(self):
        # Only client credentials required
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("Missing required Reddit client credentials in environment variables")
        
        self.base_url = "https://oauth.reddit.com/r/memes"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        self.session = None
        self.access_token = None
        self.token_expiry = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        await self.ensure_valid_token()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if necessary."""
        if not self.access_token or not self.token_expiry or datetime.now() >= self.token_expiry:
            await self.refresh_access_token()

    async def refresh_access_token(self):
        """Obtain a new access token using client credentials."""
        try:
            auth_string = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            headers = {
                "Authorization": f"Basic {auth_string}",
                "User-Agent": "python:meme_app:v1.0"
            }

            data = {
                "grant_type": "client_credentials",
            }

            async with self.session.post(
                self.auth_url,
                headers=headers,
                data=data
            ) as response:
                response.raise_for_status()
                auth_data = await response.json()

                self.access_token = auth_data["access_token"]
                self.token_expiry = datetime.now() + timedelta(
                    seconds=auth_data["expires_in"] - 300
                )
                
                logger.info("Successfully refreshed Reddit access token")

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """Get headers with current access token."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "python:meme_app:v1.0"
        }

    async def fetch_top_memes(self, limit: int = 20) -> List[Dict]:
        """Fetch top memes, filtering for image posts only."""
        try:
            await self.ensure_valid_token()
            url = f"{self.base_url}/top"
            params = {"limit": limit, "t": "day"}
            
            async with self.session.get(
                url,
                headers=self.get_headers(),
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                memes = []
                for post in data['data']['children']:
                    post_data = post['data']
                    meme = {
                        "reddit_id": post_data['id'],
                        "title": post_data['title'],
                        "url": post_data.get('url_overridden_by_dest', post_data['url']),
                        "score": post_data['score'],
                        "upvote_ratio": post_data['upvote_ratio'],
                        "author": post_data['author'],
                        "num_comments": post_data['num_comments'],
                        "permalink": f"https://reddit.com{post_data['permalink']}",
                        "reddit_created_at": datetime.fromtimestamp(post_data['created_utc']),
                        "thumbnail": post_data.get('thumbnail'),
                        "is_video": post_data.get('is_video', False)
                    }
                    # if meme['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    memes.append(meme)
                        
                memes.sort(key=lambda x: x["score"], reverse=True)
                logger.info(f"Successfully fetched {len(memes)} memes")
                return memes

        except Exception as e:
            logger.error(f"Error fetching memes from Reddit: {e}")
            raise
