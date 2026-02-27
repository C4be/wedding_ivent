import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()
]
SITE_API_URL: str = os.getenv("SITE_API_URL", "http://localhost:5000")
SITE_API_KEY: str = os.getenv("SITE_API_KEY", "")
DB_PATH: str = os.getenv("DB_PATH", "./data/wedding_bot.db")
LOG_DIR: str = os.getenv("LOG_DIR", "./logs")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
