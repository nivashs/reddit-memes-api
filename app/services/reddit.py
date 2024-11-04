# app/services/reddit.py
import requests
from datetime import datetime
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class RedditService:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://www.reddit.com/r/memes"

    async def fetch_top_memes(self, limit: int = 20) -> List[Dict]:
        try:
            url = f"{self.base_url}/top.json?limit={limit}&t=day"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
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
                
                if meme['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    memes.append(meme)
            memes = sorted(memes, key=lambda x: x["score"], reverse=True)
            logger.info(f"Successfully fetched {len(memes)} memes")
            return memes

        except requests.RequestException as e:
            logger.error(f"Error fetching memes from Reddit: {e}")
            raise

    async def fetch_with_pagination(self, limit: int = 100, after: str = None) -> Dict:
        try:
            url = f"{self.base_url}/top.json?limit={limit}&t=day"
            if after:
                url += f"&after={after}"

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
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
                memes.append(meme)

            return {
                "memes": memes,
                "next_page": data['data'].get('after'),
                "total": len(memes)
            }

        except requests.RequestException as e:
            logger.error(f"Error fetching memes with pagination: {e}")
            raise