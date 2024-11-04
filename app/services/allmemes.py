from sqlalchemy import text
from typing import Dict, Optional
import logging
from fastapi import HTTPException
from base64 import b64encode, b64decode
import json

logger = logging.getLogger(__name__)

class MemeDBService:
    def __init__(self, db):
        self.db = db

    def get_paginated_memes(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "created_at",
        order: str = "desc"
    ) -> Dict:
        try:
            # Validate sort field
            valid_sort_fields = ["created_at", "score", "reddit_created_at", "num_comments"]
            if sort_by not in valid_sort_fields:
                raise HTTPException(status_code=400, detail=f"Invalid sort field")

            # Parse cursor
            cursor_value = None
            if cursor:
                try:
                    cursor_data = json.loads(b64decode(cursor.encode()).decode())
                    cursor_value = cursor_data.get(sort_by)
                except:
                    raise HTTPException(status_code=400, detail="Invalid cursor")

            # Build query
            query = """
                SELECT 
                    id, reddit_id, title, url, score, 
                    upvote_ratio, created_at, reddit_created_at, 
                    author, num_comments, permalink, 
                    thumbnail, is_video
                FROM memes
            """
            
            params = {"limit": limit + 1}  # +1 to check if there are more pages
            
            if cursor_value:
                op = "<" if order.lower() == "desc" else ">"
                query += f" WHERE {sort_by} {op} :cursor"
                params["cursor"] = cursor_value

            query += f" ORDER BY {sort_by} {'DESC' if order.lower() == 'desc' else 'ASC'}"
            query += " LIMIT :limit"

            # Execute query
            result = self.db.execute(text(query), params)
            memes = result.mappings().all()

            # Check if there are more pages
            has_next = len(memes) > limit
            memes = memes[:limit]  # Remove the extra item we fetched

            # Create next cursor
            next_cursor = None
            if has_next and memes:
                last_item = memes[-1]
                cursor_data = {sort_by: str(last_item[sort_by])}
                next_cursor = b64encode(json.dumps(cursor_data).encode()).decode()

            return {
                "items": [dict(meme) for meme in memes],
                "next_cursor": next_cursor,
                "has_next": has_next
            }

        except Exception as e:
            logger.error(f"Error fetching paginated memes: {e}")
            raise