# Reddit Memes API
A FastAPI application that fetches and stores top memes from r/memes.

## Setup
1. Create virtual environment in Windows:
```
python -m venv venv
```
venv\Scripts\activate

# Install dependencies
```
pip install -r requirements.txt
```

# Run the application
```
uvicorn app.main:app --reload
```

API Endpoints
Get top memes:
http://localhost:8000/memes/top
Get top memes with a limit: http://localhost:8000/memes/top?limit=10
Get paginated memes: http://localhost:8000/memes/paginated
Get paginated memes with parameters: http://localhost:8000/memes/paginated?limit=50&after=t3_someRedditId
API Documentation
API documentation is available at: http://localhost:8000/docs



## Supabase Commands
supabase init
supabase migration new <migration_name>
supabase migration new create_memes_table
supabase db push
supabase db reset
