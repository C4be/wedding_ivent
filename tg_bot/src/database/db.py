import aiosqlite
import os
from src.config import DB_PATH
from src.utils.logger import logger


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    logger.info("Initializing database...")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS members (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER REFERENCES users(telegram_id),
                full_name       TEXT NOT NULL,
                partner_name    TEXT,
                phone           TEXT,
                email           TEXT,
                attendance_day1 INTEGER DEFAULT 0,
                attendance_day2 INTEGER DEFAULT 0,
                drink_pref      TEXT,
                wishes          TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gallery_links (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL,
                caption    TEXT,
                added_by   INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS message_templates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                body       TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS drinks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT UNIQUE NOT NULL,
                emoji TEXT DEFAULT ''
            );

            INSERT OR IGNORE INTO drinks (name, emoji) VALUES
                ('Вино красное', '🍷'),
                ('Вино белое', '🥂'),
                ('Шампанское', '🍾'),
                ('Пиво', '🍺'),
                ('Виски', '🥃'),
                ('Безалкогольное', '🧃'),
                ('Вода', '💧');
        """)
        await db.commit()
    logger.info("Database initialized successfully")
