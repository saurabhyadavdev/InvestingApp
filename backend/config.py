"""
Application configuration loaded from environment / .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_PATH: str = os.getenv("DB_PATH", "data/app.db")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Kolkata")
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")
    FINNHUB_KEY: str = os.getenv("FINNHUB_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")


settings = Settings()
