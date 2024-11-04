from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDDIT_BASE_URL: str = "https://www.reddit.com/r/memes"
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_EXPIRE_MINUTES: int = 5
    
    # Rate limiting
    RATE_LIMIT_SECONDS: int = 1
    
    class Config:
        env_file = ".env"

settings = Settings()