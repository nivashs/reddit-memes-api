# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get Supabase connection string
DATABASE_URL = os.getenv("DATABASE_URL")

# Configure SQLAlchemy for Supabase
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Supabase free tier limit
    max_overflow=0,      # Don't exceed pool size
    pool_timeout=30,     # Connection timeout
    pool_recycle=1800,   # Recycle connections every 30 minutes
    pool_pre_ping=True,  # Check connection health
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()