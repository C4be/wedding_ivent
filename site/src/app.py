import json
import io
import logging
import os
import random
import re
import shutil
import sqlite3
import time
import uuid
import zipfile
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

import qrcode
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from langchain_core.messages import HumanMessage

try:
    from langchain_gigachat.chat_models import GigaChat
except Exception:
    GigaChat = None

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, '..', 'materials', 'site.info.json')
SLIDER_PATH = os.path.join(BASE_DIR, 'static', 'images', 'slider')
DB_PATH = os.environ.get('SQLITE_DB_PATH', os.path.join(BASE_DIR, '..', 'materials', 'wedding.db'))
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change-me')
FAMILY_GALLERY_ROOT = os.path.join(BASE_DIR, 'static', 'images', 'family_gallery')
PHOTOGRAPHER_ROOT = os.path.join(BASE_DIR, 'static', 'images', 'photographer')
SECRET_VIDEO_ROOT = os.path.join(BASE_DIR, 'static', 'media', 'secret_video')
BACKGROUND_ROOT = os.path.join(BASE_DIR, 'static', 'images', 'backgrounds')
USERS_INFO_PATH = os.path.join(BASE_DIR, '..', 'materials', 'users_info.txt')
FONT_ROOT = os.path.join(BASE_DIR, '..', 'materials', 'fonts')
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.m4v', '.avi'}
CONTACT_EMAIL = 'dmitrycube@yandex.ru'
CONTACT_TELEGRAM = '@C4be74'
INVITATION_PROVIDER = os.environ.get('MODEL', 'giga').strip().lower()
GIGACHAT_MODEL = os.environ.get('GIGACHAT_MODEL', 'GigaChat-2')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-ai/DeepSeek-V4-Pro')
AGENT_CLOUD_API_KEY = os.environ.get('AGENT_CLOUD_API_KEY', '').strip()
AGENT_CLOUDRU_API_URL = os.environ.get('AGENT_CLOUDRU_API_URL', 'https://foundation-models.api.cloud.ru/v1').strip()
USE_LOG = os.environ.get('USE_LOG', '').strip().upper() == 'YES'
LOG_FILE_PATH = os.environ.get('SITE_LOG_PATH', os.path.join(BASE_DIR, '..', 'materials', 'site.log'))
INVITATION_BG_BLUR = os.environ.get('INVITATION_BG_BLUR', '6')
INVITATION_BG_DARKEN = os.environ.get('INVITATION_BG_DARKEN', '0.72')
MAX_CONTENT_LENGTH_MB = os.environ.get('MAX_CONTENT_LENGTH_MB', '250')
FONT_OPTIONS = {
    'Cormorant Garamond': 'serif',
    'Playfair Display': 'serif',
    'Lora': 'serif',
    'Montserrat': 'sans-serif',
    'Manrope': 'sans-serif',
    'Nunito Sans': 'sans-serif',
}
DEFAULT_THEME = {
    'primary_color': '#D4A574',
    'secondary_color': '#2C3E50',
    'accent_color': '#E8D5C4',
    'light_bg': '#FAF8F5',
    'dark_bg': '#1a1a2e',
    'display_font': 'Cormorant Garamond',
    'body_font': 'Montserrat',
}
DEFAULT_FEATURES = {
    'gallery_enabled': True,
    'gallery_max_uploads_per_family': 12,
    'secret_video_enabled': False,
}
INVITATION_PAGE_SIZE = (1152, 648)  # 16:9 in points


def init_request_logger() -> logging.Logger | None:
    if not USE_LOG:
        return None

    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    logger = logging.getLogger('site_requests')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        logger.addHandler(handler)
    return logger


REQUEST_LOGGER = init_request_logger()

try:
    _max_upload_mb = int(str(MAX_CONTENT_LENGTH_MB).strip())
except (TypeError, ValueError):
    _max_upload_mb = 250
_max_upload_mb = max(25, min(_max_upload_mb, 1024))


def log_site_event(message: str) -> None:
    if REQUEST_LOGGER:
        REQUEST_LOGGER.info(message)


def short_text(value: str, max_len: int = 800) -> str:
    text = (value or '').replace('\n', '\\n')
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...<truncated:{len(text) - max_len}>"


def request_payload_preview() -> str:
    try:
        if request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return '-'
        content_type = (request.content_type or '').lower()
        if 'application/json' in content_type or 'application/x-www-form-urlencoded' in content_type:
            return short_text(request.get_data(as_text=True), 1200)
        return f"<{content_type or 'unknown'} payload>"
    except Exception:
        return '<unavailable>'


def parse_float_env(value: str, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float((value or '').strip())
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))

app.config['MAX_CONTENT_LENGTH'] = _max_upload_mb * 1024 * 1024


def apply_config_defaults(config: dict) -> tuple[dict, bool]:
    changed = False

    theme = config.setdefault('theme', {})
    for key, value in DEFAULT_THEME.items():
        if key not in theme or theme[key] in (None, ''):
            theme[key] = value
            changed = True

    features = config.setdefault('features', {})
    for key, value in DEFAULT_FEATURES.items():
        if key not in features:
            features[key] = value
            changed = True

    event = config.setdefault('event', {})
    day1 = event.setdefault('timeline_day1', {'title': 'День 1', 'events': []})
    day2 = event.setdefault('timeline_day2', {'title': 'День 2', 'events': []})
    if 'title' not in day1:
        day1['title'] = 'День 1'
        changed = True
    if 'title' not in day2:
        day2['title'] = 'День 2'
        changed = True
    if not isinstance(day1.get('events'), list):
        day1['events'] = []
        changed = True
    if not isinstance(day2.get('events'), list):
        day2['events'] = []
        changed = True
    if 'ceremony_note' not in event:
        event['ceremony_note'] = ''
        changed = True

    return config, changed


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    ensure_default_contact_links(config)
    config, changed = apply_config_defaults(config)
    if changed:
        save_config(config)
    return config


def save_config(config):
    config, _ = apply_config_defaults(config)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with get_db_connection() as conn:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_key TEXT NOT NULL UNIQUE,
                head_first_name TEXT NOT NULL,
                head_second_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                second_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                phone TEXT,
                attending INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(family_id, first_name, second_name),
                FOREIGN KEY(family_id) REFERENCES families(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS family_preferences (
                family_id INTEGER PRIMARY KEY,
                drinks TEXT,
                music TEXT,
                food TEXT,
                notes TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(family_id) REFERENCES families(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS family_gallery_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_name TEXT,
                photographer_name TEXT,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY(family_id) REFERENCES families(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS photographer_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT,
                uploaded_at TEXT NOT NULL
            );
            '''
        )

        gallery_columns = {
            row['name'] for row in conn.execute('PRAGMA table_info(family_gallery_images)').fetchall()
        }
        if 'photographer_name' not in gallery_columns:
            conn.execute('ALTER TABLE family_gallery_images ADD COLUMN photographer_name TEXT')


def init_storage() -> None:
    os.makedirs(FAMILY_GALLERY_ROOT, exist_ok=True)
    os.makedirs(PHOTOGRAPHER_ROOT, exist_ok=True)
    os.makedirs(SECRET_VIDEO_ROOT, exist_ok=True)
    os.makedirs(BACKGROUND_ROOT, exist_ok=True)


def normalize_text(value: str) -> str:
    return ' '.join((value or '').strip().split())


def build_family_key(head_first_name: str, head_second_name: str) -> str:
    return f"{normalize_text(head_first_name).casefold()}::{normalize_text(head_second_name).casefold()}"


def parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on', 'да'}
    return default


def parse_int(value, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    if min_value is not None:
        parsed = max(parsed, min_value)
    if max_value is not None:
        parsed = min(parsed, max_value)
    return parsed


def allowed_image_file(filename: str) -> bool:
    ext = Path(filename or '').suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def allowed_video_file(filename: str) -> bool:
    ext = Path(filename or '').suffix.lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS


def color_is_valid(value: str) -> bool:
    value = (value or '').strip()
    if len(value) != 7 or not value.startswith('#'):
        return False
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False


def sanitize_timeline_events(events) -> list[dict]:
    if not isinstance(events, list):
        return []

    clean = []
    for item in events:
        if not isinstance(item, dict):
            continue
        icon = normalize_text(item.get('icon', ''))
        time = normalize_text(item.get('time', ''))
        title = normalize_text(item.get('title', ''))
        description = normalize_text(item.get('description', ''))
        if not any([icon, time, title, description]):
            continue
        clean.append(
            {
                'icon': icon,
                'time': time,
                'title': title,
                'description': description,
            }
        )
    return clean


def family_gallery_dir(family_id: int) -> str:
    return os.path.join(FAMILY_GALLERY_ROOT, str(family_id))


def family_image_url(family_id: int, filename: str) -> str:
    return f'/static/images/family_gallery/{family_id}/{filename}'


def photographer_image_url(filename: str) -> str:
    return f'/static/images/photographer/{filename}'


def get_gallery_settings(config: dict) -> dict:
    features = config.get('features', {})
    return {
        'gallery_enabled': parse_bool(features.get('gallery_enabled', True), True),
        'gallery_max_uploads_per_family': parse_int(features.get('gallery_max_uploads_per_family', 12), 12, 1, 100),
        'secret_video_enabled': parse_bool(features.get('secret_video_enabled', False), False),
    }


def get_secret_video_state() -> dict:
    os.makedirs(SECRET_VIDEO_ROOT, exist_ok=True)
    files = []
    for filename in os.listdir(SECRET_VIDEO_ROOT):
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_VIDEO_EXTENSIONS:
            path = os.path.join(SECRET_VIDEO_ROOT, filename)
            files.append((os.path.getmtime(path), filename))

    if not files:
        return {'has_video': False, 'filename': '', 'url': ''}

    files.sort(reverse=True)
    latest = files[0][1]
    return {
        'has_video': True,
        'filename': latest,
        'url': f'/static/media/secret_video/{latest}',
    }


def get_theme_payload(config: dict) -> dict:
    theme = config.get('theme', {})
    display_font = theme.get('display_font', DEFAULT_THEME['display_font'])
    body_font = theme.get('body_font', DEFAULT_THEME['body_font'])
    if display_font not in FONT_OPTIONS:
        display_font = DEFAULT_THEME['display_font']
    if body_font not in FONT_OPTIONS:
        body_font = DEFAULT_THEME['body_font']
    return {
        'primary_color': theme.get('primary_color', DEFAULT_THEME['primary_color']),
        'secondary_color': theme.get('secondary_color', DEFAULT_THEME['secondary_color']),
        'accent_color': theme.get('accent_color', DEFAULT_THEME['accent_color']),
        'light_bg': theme.get('light_bg', DEFAULT_THEME['light_bg']),
        'dark_bg': theme.get('dark_bg', DEFAULT_THEME['dark_bg']),
        'display_font': display_font,
        'body_font': body_font,
        'display_font_fallback': FONT_OPTIONS[display_font],
        'body_font_fallback': FONT_OPTIONS[body_font],
    }


def get_admin_content_payload(config: dict) -> dict:
    meta = config.get('meta', {})
    couple = config.get('couple', {})
    event = config.get('event', {})
    story = config.get('story', {})
    location = config.get('location', {})
    dresscode = config.get('dresscode', {})
    contacts = config.get('contacts', {})

    return {
        'meta_title': meta.get('title', ''),
        'meta_description': meta.get('description', ''),
        'groom': couple.get('groom', ''),
        'bride': couple.get('bride', ''),
        'hashtag': couple.get('hashtag', ''),
        'event_date': event.get('date', ''),
        'event_date_display': event.get('date_display', ''),
        'story_title': story.get('title', ''),
        'story_text': story.get('text', ''),
        'location_name': location.get('name', ''),
        'location_address': location.get('address', ''),
        'dresscode_title': dresscode.get('title', ''),
        'dresscode_text': dresscode.get('text', ''),
        'organizer_name': contacts.get('organizer_name', ''),
        'organizer_phone': contacts.get('organizer_phone', ''),
    }


def apply_admin_content_payload(config: dict, data: dict) -> None:
    config.setdefault('meta', {})
    config.setdefault('couple', {})
    config.setdefault('event', {})
    config.setdefault('story', {})
    config.setdefault('location', {})
    config.setdefault('dresscode', {})
    config.setdefault('contacts', {})
    config['contacts'].setdefault('telegram', CONTACT_TELEGRAM)
    config['contacts'].setdefault('telegram_channel', f"https://t.me/{CONTACT_TELEGRAM.lstrip('@')}")

    config['meta']['title'] = normalize_text(data.get('meta_title', config['meta'].get('title', '')))
    config['meta']['description'] = normalize_text(data.get('meta_description', config['meta'].get('description', '')))
    config['couple']['groom'] = normalize_text(data.get('groom', config['couple'].get('groom', '')))
    config['couple']['bride'] = normalize_text(data.get('bride', config['couple'].get('bride', '')))
    config['couple']['hashtag'] = normalize_text(data.get('hashtag', config['couple'].get('hashtag', '')))
    config['event']['date'] = normalize_text(data.get('event_date', config['event'].get('date', '')))
    config['event']['date_display'] = normalize_text(data.get('event_date_display', config['event'].get('date_display', '')))
    config['story']['title'] = normalize_text(data.get('story_title', config['story'].get('title', '')))
    config['story']['text'] = normalize_text(data.get('story_text', config['story'].get('text', '')))
    config['location']['name'] = normalize_text(data.get('location_name', config['location'].get('name', '')))
    config['location']['address'] = normalize_text(data.get('location_address', config['location'].get('address', '')))
    config['dresscode']['title'] = normalize_text(data.get('dresscode_title', config['dresscode'].get('title', '')))
    config['dresscode']['text'] = normalize_text(data.get('dresscode_text', config['dresscode'].get('text', '')))
    config['contacts']['organizer_name'] = normalize_text(data.get('organizer_name', config['contacts'].get('organizer_name', '')))
    config['contacts']['organizer_phone'] = normalize_text(data.get('organizer_phone', config['contacts'].get('organizer_phone', '')))


def ensure_default_contact_links(config: dict) -> None:
    contacts = config.setdefault('contacts', {})
    contacts.setdefault('telegram', CONTACT_TELEGRAM)
    contacts.setdefault('telegram_channel', f"https://t.me/{CONTACT_TELEGRAM.lstrip('@')}")


def get_or_create_family(conn: sqlite3.Connection, head_first_name: str, head_second_name: str) -> dict:
    first = normalize_text(head_first_name)
    second = normalize_text(head_second_name)
    family_key = build_family_key(first, second)

    row = conn.execute(
        'SELECT id, family_key, head_first_name, head_second_name, created_at FROM families WHERE family_key = ?',
        (family_key,),
    ).fetchone()

    if row:
        return dict(row)

    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        'INSERT INTO families (family_key, head_first_name, head_second_name, created_at) VALUES (?, ?, ?, ?)',
        (family_key, first, second, now),
    )
    family_id = cursor.lastrowid
    conn.execute(
        '''
        INSERT INTO family_members (family_id, first_name, second_name, role, phone, attending, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (family_id, first, second, 'head', None, 1, now),
    )

    created = conn.execute(
        'SELECT id, family_key, head_first_name, head_second_name, created_at FROM families WHERE id = ?',
        (family_id,),
    ).fetchone()
    return dict(created)


def get_family_by_head(conn: sqlite3.Connection, head_first_name: str, head_second_name: str):
    family_key = build_family_key(head_first_name, head_second_name)
    row = conn.execute(
        'SELECT id, family_key, head_first_name, head_second_name, created_at FROM families WHERE family_key = ?',
        (family_key,),
    ).fetchone()
    return dict(row) if row else None


def fetch_family_payload(conn: sqlite3.Connection, family_id: int) -> dict:
    family_row = conn.execute(
        'SELECT id, family_key, head_first_name, head_second_name, created_at FROM families WHERE id = ?',
        (family_id,),
    ).fetchone()
    if not family_row:
        return {}

    member_rows = conn.execute(
        '''
        SELECT id, first_name, second_name, role, phone, attending, created_at
        FROM family_members
        WHERE family_id = ?
        ORDER BY
            CASE role WHEN 'head' THEN 0 WHEN 'partner' THEN 1 WHEN 'child' THEN 2 ELSE 3 END,
            second_name,
            first_name
        ''',
        (family_id,),
    ).fetchall()

    family_created_at = family_row['created_at']

    members = []
    for row in member_rows:
        item = dict(row)
        item['attending'] = bool(item['attending'])
        item['created_at_display'] = format_dt_for_humans(item.get('created_at'))
        members.append(item)

    pref_row = conn.execute(
        'SELECT drinks, music, food, notes, updated_at FROM family_preferences WHERE family_id = ?',
        (family_id,),
    ).fetchone()
    preferences = dict(pref_row) if pref_row else None
    if preferences is not None:
        preferences['updated_at_display'] = format_dt_for_humans(preferences.get('updated_at'))

    return {
        'id': family_row['id'],
        'family_key': family_row['family_key'],
        'head_first_name': family_row['head_first_name'],
        'head_second_name': family_row['head_second_name'],
        'created_at': family_created_at,
        'created_at_display': format_dt_for_humans(family_created_at),
        'members': members,
        'preferences': preferences,
    }


def fetch_family_gallery_images(conn: sqlite3.Connection, family_id: int) -> list[dict]:
    rows = conn.execute(
        '''
        SELECT id, filename, original_name, photographer_name, uploaded_at
        FROM family_gallery_images
        WHERE family_id = ?
        ORDER BY datetime(uploaded_at) DESC, id DESC
        ''',
        (family_id,),
    ).fetchall()

    items = []
    for row in rows:
        items.append(
            {
                'id': row['id'],
                'filename': row['filename'],
                'original_name': row['original_name'],
                'photographer_name': row['photographer_name'],
                'uploaded_at': row['uploaded_at'],
                'uploaded_at_display': format_dt_for_humans(row['uploaded_at']),
                'url': family_image_url(family_id, row['filename']),
            }
        )
    return items


def fetch_all_family_gallery_images(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        '''
        SELECT g.id,
               g.family_id,
               g.filename,
               g.original_name,
               g.photographer_name,
               g.uploaded_at,
               f.head_first_name,
               f.head_second_name
        FROM family_gallery_images g
        JOIN families f ON f.id = g.family_id
        ORDER BY datetime(g.uploaded_at) DESC, g.id DESC
        '''
    ).fetchall()

    items = []
    for row in rows:
        display_photographer = row['photographer_name']
        if not display_photographer:
            display_photographer = f"{row['head_first_name']} {row['head_second_name']}"

        items.append(
            {
                'id': row['id'],
                'family_id': row['family_id'],
                'head_first_name': row['head_first_name'],
                'head_second_name': row['head_second_name'],
                'filename': row['filename'],
                'original_name': row['original_name'],
                'photographer_name': display_photographer,
                'uploaded_at': row['uploaded_at'],
                'uploaded_at_display': format_dt_for_humans(row['uploaded_at']),
                'url': family_image_url(row['family_id'], row['filename']),
            }
        )
    return items


def fetch_photographer_images(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        '''
        SELECT id, filename, original_name, uploaded_at
        FROM photographer_images
        ORDER BY datetime(uploaded_at) DESC, id DESC
        '''
    ).fetchall()

    items = []
    for row in rows:
        items.append(
            {
                'id': row['id'],
                'filename': row['filename'],
                'original_name': row['original_name'],
                'uploaded_at': row['uploaded_at'],
                'uploaded_at_display': format_dt_for_humans(row['uploaded_at']),
                'url': photographer_image_url(row['filename']),
            }
        )
    return items


def remove_file_if_exists(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def read_users_info_raw() -> str:
    if not os.path.exists(USERS_INFO_PATH):
        return ''
    try:
        with open(USERS_INFO_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''


def write_users_info_raw(content: str) -> None:
    parent_dir = os.path.dirname(USERS_INFO_PATH)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(USERS_INFO_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


def get_family_members(conn: sqlite3.Connection, family_id: int) -> list[dict]:
    rows = conn.execute(
        '''
        SELECT first_name, second_name, role, phone, attending
        FROM family_members
        WHERE family_id = ?
        ORDER BY
            CASE role WHEN 'head' THEN 0 WHEN 'partner' THEN 1 WHEN 'child' THEN 2 ELSE 3 END,
            second_name,
            first_name
        ''',
        (family_id,),
    ).fetchall()

    return [dict(row) for row in rows]


def read_users_info() -> str:
    return read_users_info_raw().strip()


def normalize_person_name(value: str) -> str:
    return ' '.join((value or '').strip().split()).casefold()


def member_full_name(member: dict) -> str:
    first = normalize_text(member.get('first_name', ''))
    second = normalize_text(member.get('second_name', ''))
    return normalize_text(f"{first} {second}")


def get_family_recipients(family_head: dict, members: list[dict]) -> list[str]:
    names = []
    for member in members:
        full = member_full_name(member)
        if full:
            names.append(full)

    if not names:
        head = normalize_text(
            f"{family_head.get('head_first_name', '')} {family_head.get('head_second_name', '')}"
        )
        if head:
            names.append(head)

    uniq = []
    seen = set()
    for name in names:
        key = normalize_person_name(name)
        if key and key not in seen:
            seen.add(key)
            uniq.append(name)
    return uniq


def parse_users_info_entries(users_info: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    if not users_info:
        return entries

    current_name = ''
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_name, current_parts
        key = normalize_person_name(current_name)
        text = ' '.join(p for p in current_parts if p).strip()
        if key and text:
            entries[key] = text
        current_name = ''
        current_parts = []

    for raw in users_info.splitlines():
        line = raw.strip()
        if not line:
            continue

        match = re.match(r'^\d+\.\s*(.+?)\s*-\s*(.+)$', line)
        if match:
            flush_current()
            current_name = match.group(1).strip()
            current_parts = [match.group(2).strip()]
            continue

        if current_name:
            current_parts.append(line)

    flush_current()
    return entries


def get_relevant_users_info(users_info: str, recipients: list[str]) -> list[tuple[str, str]]:
    entries = parse_users_info_entries(users_info)
    if not entries or not recipients:
        return []

    selected: list[tuple[str, str]] = []
    added = set()
    for person in recipients:
        key = normalize_person_name(person)
        note = entries.get(key)
        if note and key not in added:
            selected.append((person, note))
            added.add(key)
    return selected


def strip_markdown_artifacts(text: str) -> str:
    candidate = (text or '').strip()
    if not candidate:
        return ''

    candidate = re.sub(r'```[\s\S]*?```', ' ', candidate)
    candidate = re.sub(r'`([^`]*)`', r'\1', candidate)
    candidate = re.sub(r'^\s{0,3}#{1,6}\s*', '', candidate, flags=re.MULTILINE)
    candidate = re.sub(r'^\s*[-*+]\s+', '', candidate, flags=re.MULTILINE)
    candidate = re.sub(r'^\s*\d+[\.)]\s+', '', candidate, flags=re.MULTILINE)
    candidate = re.sub(r'\*\*(.*?)\*\*', r'\1', candidate)
    candidate = re.sub(r'__(.*?)__', r'\1', candidate)
    candidate = re.sub(r'\*(.*?)\*', r'\1', candidate)
    candidate = re.sub(r'_(.*?)_', r'\1', candidate)
    candidate = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', candidate)
    candidate = re.sub(r'\|', ' ', candidate)
    candidate = re.sub(r'\n{3,}', '\n\n', candidate)
    candidate = re.sub(r' {2,}', ' ', candidate)
    return candidate.strip()


def invitation_text_is_valid(text: str) -> bool:
    candidate = (text or '').strip()
    if len(candidate) < 160:
        return False

    forbidden_tokens = ('```', '# ', '##', '*', '[', ']', '|')
    if any(token in candidate for token in forbidden_tokens):
        return False

    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    if not lines:
        return False

    for line in lines:
        if re.match(r'^[-*]\s+', line):
            return False
        if re.match(r'^\d+\.\s+', line):
            return False

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', candidate) if p.strip()]
    return 2 <= len(paragraphs) <= 8


def telegram_profile_url(config: dict) -> str:
    contacts = config.get('contacts', {}) if isinstance(config, dict) else {}
    raw = normalize_text(contacts.get('telegram', '')) or CONTACT_TELEGRAM
    username = raw.lstrip('@')
    return f"https://t.me/{username}"


def choose_background_file() -> str | None:
    if not os.path.isdir(BACKGROUND_ROOT):
        return None

    files = []
    for filename in os.listdir(BACKGROUND_ROOT):
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_IMAGE_EXTENSIONS:
            files.append(os.path.join(BACKGROUND_ROOT, filename))

    if not files:
        return None
    return random.choice(files)


def build_family_prompt(
    config: dict,
    family_head: dict,
    members: list[dict],
    recipients: list[str],
    relevant_notes: list[tuple[str, str]],
) -> str:
    couple = config.get('couple', {})
    event = config.get('event', {})
    location = config.get('location', {})

    member_lines = []
    for m in members:
        member_lines.append(
            f"- {m.get('first_name', '')} {m.get('second_name', '')} ({m.get('role', 'member')}, attending={m.get('attending', True)})"
        )

    recipients_line = ', '.join(recipients) if recipients else 'нет данных'
    notes_block = 'Нет персональных заметок для этих людей.'
    if relevant_notes:
        notes_block = '\n'.join([f"- {name}: {note}" for name, note in relevant_notes])

    return (
        "Составь красивый, теплый и современный текст персонального приглашения на свадьбу для семьи на русском языке.\n"
        "Обращайся к людям из блока 'Кому' по именам (или по отношению к кому то жениху/невесте), упоминая их в тексте приглашения, если это уместно.\n"
        "Отчества нельзя упоменать при обращении\n"
        "Торжество - Свадьба. Жених - Гимазетдинов Дмитрий. Невеста - Наталья Заиченко.\n"
        "Текст должен быть живым и личным, но аккуратным по стилю.\n"
        "Строгие правила формата (обязательно):\n"
        "1) Только plain text, без markdown и списков.\n"
        "2) 2-3 абзаца.\n"
        "3) Никаких символов #, *, `, [ ], таблиц, буллетов и нумерации.\n"
        "4) Упомяни обращение к людям из блока 'Кому'.\n"
        "5) Если есть персональные заметки по людям из блока 'Кому', аккуратно и уместно вплети их в текст.\n\n"
        f"Пара: {couple.get('groom', 'Жених')} и {couple.get('bride', 'Невеста')}\n"
        f"Хэштег: {couple.get('hashtag', '')}\n"
        f"Дата: {event.get('date_display', event.get('date', ''))}\n"
        f"Место: {location.get('name', '')}, {location.get('address', '')}\n"
        f"Глава семьи: {family_head.get('head_first_name', '')} {family_head.get('head_second_name', '')}\n"
        f"Кому: {recipients_line}\n"
        "Состав приглашенной семьи:\n"
        f"{chr(10).join(member_lines) if member_lines else '- Нет данных'}\n\n"
        "Персональные заметки только про людей из блока 'Кому':\n"
        f"{notes_block}\n"
    )


def generate_invitation_text_with_llm(prompt_text: str) -> str:
    provider = INVITATION_PROVIDER
    llm = None
    model_name = ''

    if provider == 'giga':
        api_key = os.environ.get('SBER_API_KEY', '').strip()
        if not api_key or GigaChat is None:
            return ''
        model_name = GIGACHAT_MODEL
        try:
            llm = GigaChat(
                credentials=api_key,
                model=model_name,
                verify_ssl_certs=False,
            )
        except Exception:
            return ''
    elif provider == 'deepseek':
        if not AGENT_CLOUD_API_KEY or not AGENT_CLOUDRU_API_URL or ChatOpenAI is None:
            return ''
        model_name = DEEPSEEK_MODEL
        try:
            llm = ChatOpenAI(
                api_key=AGENT_CLOUD_API_KEY,
                base_url=AGENT_CLOUDRU_API_URL,
                model=model_name,
                use_responses_api=False,
            )
        except Exception:
            return ''
    else:
        return ''

    log_site_event(
        f"invitation.prompt provider={provider} model={model_name} text={short_text(prompt_text, 2000)}"
    )

    attempt_prompt = prompt_text
    for attempt in range(3):
        try:
            try:
                response = llm.invoke(attempt_prompt)
            except Exception:
                if provider == 'deepseek':
                    response = llm.invoke([HumanMessage(content=attempt_prompt)])
                else:
                    raise
            if hasattr(response, 'content'):
                raw_candidate = str(response.content or '').strip()
            else:
                raw_candidate = str(response or '').strip()

            candidate = strip_markdown_artifacts(raw_candidate)
            valid = invitation_text_is_valid(candidate)

            log_site_event(
                (
                    f"invitation.response attempt={attempt + 1} valid={valid} "
                    f"raw={short_text(raw_candidate, 1500)} cleaned={short_text(candidate, 1500)}"
                )
            )

            if valid:
                return candidate

            attempt_prompt = (
                prompt_text
                + "\n\nТвой прошлый ответ не прошел валидацию формата. "
                  "Перепиши строго по правилам: только plain text, 2-4 абзаца, "
                  "без markdown, без списков, без спецсимволов форматирования."
            )
        except Exception as e:
            log_site_event(
                f"invitation.response attempt={attempt + 1} error=llm_exception detail={short_text(repr(e), 600)}"
            )
            continue

    return ''


def fallback_invitation_text(config: dict, family_head: dict, members: list[dict], recipients: list[str]) -> str:
    couple = config.get('couple', {})
    event = config.get('event', {})
    location = config.get('location', {})

    recipient_text = ', '.join(recipients) if recipients else (
        family_head.get('head_second_name', '').strip() or family_head.get('head_first_name', '').strip()
    )

    first_line = (
        f"Дорогие {recipient_text}, мы, {couple.get('groom', 'жених')} и {couple.get('bride', 'невеста')}, "
        "будем счастливы видеть вас на нашем свадебном торжестве."
    )

    people = [f"{m.get('first_name', '')} {m.get('second_name', '')}".strip() for m in members]
    people = [p for p in people if p]
    family_line = "Кому: " + (', '.join(recipients) if recipients else ', '.join(people)) + "."

    event_line = (
        f"Праздник состоится {event.get('date_display', event.get('date', 'в назначенную дату'))} "
        f"по адресу: {location.get('name', 'место проведения')}, {location.get('address', '')}."
    )

    closing = "Будем рады разделить этот день вместе с вами!"

    return "\n\n".join([line for line in [first_line, family_line, event_line, closing] if line])


def prepare_background_image(page_width: float, page_height: float) -> Image.Image | None:
    background_path = choose_background_file()
    if not background_path:
        return None

    try:
        blur_radius = parse_float_env(INVITATION_BG_BLUR, default=6.0, min_value=0.0, max_value=20.0)
        darken_factor = parse_float_env(INVITATION_BG_DARKEN, default=0.72, min_value=0.3, max_value=1.0)
        image = Image.open(background_path).convert('RGB')
        image = image.resize((int(page_width), int(page_height)), Image.Resampling.LANCZOS)
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        image = ImageEnhance.Brightness(image).enhance(darken_factor)
        return image
    except Exception:
        return None


def prepare_qr_image(site_url: str) -> Image.Image:
    qr = qrcode.QRCode(box_size=8, border=1)
    qr.add_data(site_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    if hasattr(img, 'convert'):
        return img.convert('RGB')
    return img


def wrap_text_for_canvas(
    c: canvas.Canvas,
    text: str,
    max_width: float,
    font_name: str = 'Helvetica',
    font_size: int = 12,
) -> list[str]:
    lines = []
    paragraphs = [p.strip() for p in (text or '').split('\n')]
    for para in paragraphs:
        if not para:
            lines.append('')
            continue

        words = para.split()
        current = ''
        for word in words:
            candidate = (current + ' ' + word).strip()
            if c.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        lines.append('')

    if lines and lines[-1] == '':
        lines.pop()
    return lines


def register_pdf_fonts() -> str:
    registered = set(pdfmetrics.getRegisteredFontNames())
    calligraphy_candidates = [
        ('BakinskayRegular', os.path.join(FONT_ROOT, 'Bakinskay  Regular.otf')),
        ('LadyMarmalade', os.path.join(FONT_ROOT, 'Lady Marmalade.otf')),
        ('MagnoliaScript', os.path.join(FONT_ROOT, 'Magnolia_Script.otf')),
        ('RumRaisin', os.path.join(FONT_ROOT, 'rum-raisin.otf')),
        ('SweetMavkaScript', os.path.join(FONT_ROOT, 'Sweet_Mavka_Script.otf')),
    ]

    random.shuffle(calligraphy_candidates)
    selected_font = None
    for alias, path in calligraphy_candidates:
        if not os.path.exists(path):
            continue
        try:
            if alias not in registered:
                pdfmetrics.registerFont(TTFont(alias, path))
            selected_font = alias
            break
        except Exception:
            continue

    if selected_font:
        return selected_font

    fallback_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]
    for path in fallback_paths:
        if not os.path.exists(path):
            continue
        try:
            if 'InvitationFallback' not in registered:
                pdfmetrics.registerFont(TTFont('InvitationFallback', path))
            return 'InvitationFallback'
        except Exception:
            continue

    return 'Helvetica'


def render_invitation_pdf(
    config: dict,
    family_head: dict,
    recipients: list[str],
    invitation_text: str,
    tg_url: str,
    site_url: str,
) -> io.BytesIO:
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=INVITATION_PAGE_SIZE)
    page_width, page_height = INVITATION_PAGE_SIZE
    margin_x = 52

    bg = prepare_background_image(page_width, page_height)
    if bg is not None:
        c.drawImage(ImageReader(bg), 0, 0, width=page_width, height=page_height)
    else:
        c.setFillColorRGB(0.98, 0.96, 0.93)
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    common_font = register_pdf_fonts()
    log_site_event(f"invitation.fonts common={common_font}")
    title_font_size = 28
    meta_font_size = 14
    invitation_font_size = 21

    c.setFillColorRGB(0.97, 0.96, 0.93)
    c.setFont(common_font, title_font_size)
    c.drawString(
        margin_x,
        page_height - 72,
        f"Приглашение на свадьбу {config.get('couple', {}).get('groom', '')} и {config.get('couple', {}).get('bride', '')}",
    )

    recipients_line = ', '.join(recipients) if recipients else (
        f"{family_head.get('head_first_name', '')} {family_head.get('head_second_name', '')}".strip()
    )
    location = config.get('location', {})

    info_line = (
        f"{recipients_line} | "
        f"{config.get('event', {}).get('date_display', config.get('event', {}).get('date', ''))} | "
        f"{location.get('name', '')}, {location.get('address', '')}"
    )

    header_lines = wrap_text_for_canvas(
        c,
        info_line,
        max_width=page_width - margin_x * 2,
        font_name=common_font,
        font_size=meta_font_size,
    )
    c.setFont(common_font, meta_font_size)
    c.setFillColorRGB(0.96, 0.95, 0.93)
    header_y = page_height - 110
    for line in header_lines:
        if not line:
            continue
        c.drawString(margin_x, header_y, line)
        header_y -= 22

    qr_size = 82
    qr_gap = 18
    qr_y = 44
    text_y = header_y - 10
    text_bottom_limit = qr_y + qr_size + 24
    wrapped = wrap_text_for_canvas(
        c,
        invitation_text,
        max_width=page_width - margin_x * 2,
        font_name=common_font,
        font_size=invitation_font_size,
    )
    c.setFont(common_font, invitation_font_size)
    for line in wrapped:
        if text_y < text_bottom_limit:
            break
        if line.strip():
            c.drawString(margin_x, text_y, line)
            text_y -= 22
        else:
            text_y -= 12

    qr_tg = prepare_qr_image(tg_url)
    qr_site = prepare_qr_image(site_url)
    qr_tg_x = page_width - margin_x - qr_size
    qr_site_x = qr_tg_x - qr_gap - qr_size
    c.drawImage(ImageReader(qr_site), qr_site_x, qr_y, width=qr_size, height=qr_size)
    c.drawImage(ImageReader(qr_tg), qr_tg_x, qr_y, width=qr_size, height=qr_size)
    c.setFont(common_font, 11)
    c.drawString(qr_site_x + 20, qr_y - 14, 'Сайт')
    c.drawString(qr_tg_x + 10, qr_y - 14, 'Telegram')

    c.setFont(common_font, 14)
    c.drawString(margin_x, 88, f"Контакты: {CONTACT_EMAIL} | {CONTACT_TELEGRAM}")
    c.drawString(margin_x, 68, f"{config.get('couple', {}).get('hashtag', '')}")

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def format_dt_for_humans(value: str | None) -> str:
    if not value:
        return ''
    try:
        normalized = value.strip()
        if normalized.endswith('Z'):
            normalized = f"{normalized[:-1]}+00:00"
        dt = datetime.fromisoformat(normalized)
        return dt.strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return value


def require_admin(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        password = request.headers.get('X-Admin-Password', '')
        if password != ADMIN_PASSWORD:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return view_func(*args, **kwargs)

    return wrapped


@app.before_request
def log_request_start():
    g._req_started_at = time.time()


@app.after_request
def log_request_finish(response):
    if not REQUEST_LOGGER:
        return response

    started = getattr(g, '_req_started_at', None)
    elapsed_ms = int((time.time() - started) * 1000) if started else -1
    log_site_event(
        (
            f"request method={request.method} path={request.path} status={response.status_code} "
            f"remote={request.remote_addr} duration_ms={elapsed_ms} "
            f"query={short_text(request.query_string.decode('utf-8', errors='ignore'), 300)} "
            f"payload={request_payload_preview()}"
        )
    )
    return response


init_db()
init_storage()


@app.route('/')
def index():
    config = load_config()
    ensure_default_contact_links(config)
    return render_template('index.html', config=config, gallery_settings=get_gallery_settings(config), theme_payload=get_theme_payload(config))


@app.route('/admin')
def admin_page():
    config = load_config()
    ensure_default_contact_links(config)
    return render_template('admin.html', config=config, theme_payload=get_theme_payload(config))


@app.route('/gallery')
def family_gallery_page():
    config = load_config()
    ensure_default_contact_links(config)
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return render_template('400.html', error_text='Галерея временно недоступна'), 404

    with get_db_connection() as conn:
        collage_images = fetch_all_family_gallery_images(conn)

    return render_template(
        'gallery.html',
        config=config,
        gallery_settings=settings,
        theme_payload=get_theme_payload(config),
        collage_images=collage_images,
    )


@app.route('/photographer')
def photographer_page():
    config = load_config()
    ensure_default_contact_links(config)
    return render_template('photographer.html', config=config, theme_payload=get_theme_payload(config))


@app.route('/secret_video')
def secret_video_page():
    config = load_config()
    ensure_default_contact_links(config)
    settings = get_gallery_settings(config)
    if not settings['secret_video_enabled']:
        return render_template('400.html', error_text='Секретный раздел скрыт'), 404

    secret_video = get_secret_video_state()
    return render_template(
        'secret_video.html',
        config=config,
        theme_payload=get_theme_payload(config),
        gallery_settings=settings,
        secret_video=secret_video,
    )


# ============ Public API ============

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())


@app.route('/api/config', methods=['PUT'])
def update_config():
    try:
        new_config = request.json
        if not isinstance(new_config, dict):
            return jsonify({'status': 'error', 'message': 'JSON object expected'}), 400
        save_config(new_config)
        return jsonify({'status': 'success', 'message': 'Config updated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/config/<section>', methods=['PATCH'])
def update_section(section):
    try:
        patch = request.json
        if not isinstance(patch, dict):
            return jsonify({'status': 'error', 'message': 'JSON object expected'}), 400
        config = load_config()
        if section not in config or not isinstance(config[section], dict):
            return jsonify({'status': 'error', 'message': 'Section not found or not object'}), 404
        config[section].update(patch)
        save_config(config)
        return jsonify({'status': 'success', 'message': f'Section {section} updated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/families/register', methods=['POST'])
def register_family():
    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    try:
        with get_db_connection() as conn:
            family = get_or_create_family(conn, head_first_name, head_second_name)
            payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/families/by-head', methods=['GET'])
def get_family():
    head_first_name = normalize_text(request.args.get('head_first_name', ''))
    head_second_name = normalize_text(request.args.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404
        payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload})


@app.route('/api/families/register', methods=['DELETE'])
def delete_family_group():
    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    try:
        with get_db_connection() as conn:
            family = get_family_by_head(conn, head_first_name, head_second_name)
            if not family:
                return jsonify({'status': 'error', 'message': 'Family not found'}), 404

            family_id = family['id']
            conn.execute('DELETE FROM families WHERE id = ?', (family_id,))

        gallery_path = family_gallery_dir(family_id)
        if os.path.isdir(gallery_path):
            shutil.rmtree(gallery_path, ignore_errors=True)

        return jsonify({'status': 'success', 'message': 'Family group deleted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/families/member', methods=['POST'])
def add_or_update_member():
    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))
    member_first_name = normalize_text(data.get('member_first_name', ''))
    member_second_name = normalize_text(data.get('member_second_name', ''))
    role = normalize_text(data.get('role', 'member')).lower() or 'member'
    phone = normalize_text(data.get('phone', '')) or None
    attending = parse_bool(data.get('attending'), True)

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'Head first/second name are required'}), 400

    if not member_first_name or not member_second_name:
        return jsonify({'status': 'error', 'message': 'Member first/second name are required'}), 400

    if build_family_key(head_first_name, head_second_name) == build_family_key(member_first_name, member_second_name):
        return jsonify({'status': 'error', 'message': 'Head member cannot be edited from this section'}), 400

    if role not in {'head', 'partner', 'child', 'guest', 'member'}:
        role = 'member'

    try:
        with get_db_connection() as conn:
            family = get_or_create_family(conn, head_first_name, head_second_name)
            now = datetime.utcnow().isoformat()
            conn.execute(
                '''
                INSERT INTO family_members (family_id, first_name, second_name, role, phone, attending, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(family_id, first_name, second_name)
                DO UPDATE SET role = excluded.role,
                              phone = excluded.phone,
                              attending = excluded.attending
                ''',
                (family['id'], member_first_name, member_second_name, role, phone, int(attending), now),
            )
            payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/families/member', methods=['DELETE'])
def remove_member():
    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))
    member_first_name = normalize_text(data.get('member_first_name', ''))
    member_second_name = normalize_text(data.get('member_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'Head first/second name are required'}), 400
    if not member_first_name or not member_second_name:
        return jsonify({'status': 'error', 'message': 'Member first/second name are required'}), 400

    if build_family_key(head_first_name, head_second_name) == build_family_key(member_first_name, member_second_name):
        return jsonify({'status': 'error', 'message': 'Head member cannot be deleted'}), 400

    try:
        with get_db_connection() as conn:
            family = get_family_by_head(conn, head_first_name, head_second_name)
            if not family:
                return jsonify({'status': 'error', 'message': 'Family not found'}), 404

            cursor = conn.execute(
                '''
                DELETE FROM family_members
                WHERE family_id = ? AND first_name = ? AND second_name = ?
                ''',
                (family['id'], member_first_name, member_second_name),
            )
            if cursor.rowcount == 0:
                return jsonify({'status': 'error', 'message': 'Member not found'}), 404

            payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    head_first_name = normalize_text(request.args.get('head_first_name', ''))
    head_second_name = normalize_text(request.args.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404
        payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload, 'preferences': payload.get('preferences')})


@app.route('/api/preferences', methods=['POST'])
def save_preferences():
    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'Head first/second name are required'}), 400

    drinks = normalize_text(data.get('drinks', ''))
    music = normalize_text(data.get('music', ''))
    food = normalize_text(data.get('food', ''))
    notes = normalize_text(data.get('notes', ''))

    try:
        with get_db_connection() as conn:
            family = get_or_create_family(conn, head_first_name, head_second_name)
            now = datetime.utcnow().isoformat()
            conn.execute(
                '''
                INSERT INTO family_preferences (family_id, drinks, music, food, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(family_id)
                DO UPDATE SET drinks = excluded.drinks,
                              music = excluded.music,
                              food = excluded.food,
                              notes = excluded.notes,
                              updated_at = excluded.updated_at
                ''',
                (family['id'], drinks or None, music or None, food or None, notes or None, now),
            )
            payload = fetch_family_payload(conn, family['id'])
        return jsonify({'status': 'success', 'family': payload, 'message': 'Preferences saved'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    config = load_config()
    return jsonify(config.get('images', {}).get('gallery', []))


@app.route('/api/gallery', methods=['POST'])
def add_to_gallery():
    try:
        data = request.json or {}
        config = load_config()
        config.setdefault('images', {})
        config['images'].setdefault('gallery', [])
        config['images']['gallery'].append(
            {
                'url': data.get('url'),
                'caption': data.get('caption', ''),
                'added_at': datetime.utcnow().isoformat(),
            }
        )
        save_config(config)
        return jsonify({'status': 'success', 'message': 'Image added to gallery'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/faq', methods=['POST'])
def add_faq():
    try:
        data = request.json or {}
        config = load_config()
        config.setdefault('faq', [])
        config['faq'].append({'question': data.get('question', ''), 'answer': data.get('answer', '')})
        save_config(config)
        return jsonify({'status': 'success', 'message': 'FAQ added'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/slider-images', methods=['GET'])
def get_slider_images():
    try:
        images = []
        if os.path.exists(SLIDER_PATH):
            for filename in sorted(os.listdir(SLIDER_PATH)):
                ext = os.path.splitext(filename)[1].lower()
                if ext in ALLOWED_IMAGE_EXTENSIONS:
                    images.append({'url': f'/static/images/slider/{filename}', 'filename': filename})
        return jsonify(images)
    except Exception:
        return jsonify([])


@app.route('/api/family-gallery/settings', methods=['GET'])
def family_gallery_settings():
    config = load_config()
    return jsonify({'status': 'success', 'settings': get_gallery_settings(config)})


@app.route('/api/family-gallery/by-head', methods=['GET'])
def get_family_gallery_by_head():
    config = load_config()
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return jsonify({'status': 'error', 'message': 'Gallery is disabled'}), 404

    head_first_name = normalize_text(request.args.get('head_first_name', ''))
    head_second_name = normalize_text(request.args.get('head_second_name', ''))
    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404
        images = fetch_family_gallery_images(conn, family['id'])

    return jsonify(
        {
            'status': 'success',
            'family': {
                'id': family['id'],
                'head_first_name': family['head_first_name'],
                'head_second_name': family['head_second_name'],
            },
            'images': images,
            'upload_limit': settings['gallery_max_uploads_per_family'],
        }
    )


@app.route('/api/family-gallery/upload', methods=['POST'])
def upload_family_gallery_image():
    config = load_config()
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return jsonify({'status': 'error', 'message': 'Gallery is disabled'}), 404

    head_first_name = normalize_text(request.form.get('head_first_name', ''))
    head_second_name = normalize_text(request.form.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'status': 'error', 'message': 'Image file is required'}), 400

    if not allowed_image_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Unsupported image extension'}), 400

    photographer_first_name = normalize_text(request.form.get('photographer_first_name', ''))
    photographer_second_name = normalize_text(request.form.get('photographer_second_name', ''))

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404

        if not photographer_first_name:
            photographer_first_name = family['head_first_name']
        if not photographer_second_name:
            photographer_second_name = family['head_second_name']

        photographer_name = normalize_text(f"{photographer_first_name} {photographer_second_name}")

        current_images = fetch_family_gallery_images(conn, family['id'])
        if len(current_images) >= settings['gallery_max_uploads_per_family']:
            return jsonify({'status': 'error', 'message': 'Family gallery upload limit reached'}), 400

        original_name = secure_filename(file.filename)
        ext = Path(original_name).suffix.lower()
        new_name = f"{uuid.uuid4().hex}{ext}"

        target_dir = family_gallery_dir(family['id'])
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, new_name)
        file.save(target_path)

        now = datetime.utcnow().isoformat()
        conn.execute(
            '''
            INSERT INTO family_gallery_images (family_id, filename, original_name, photographer_name, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (family['id'], new_name, original_name, photographer_name, now),
        )

        images = fetch_family_gallery_images(conn, family['id'])

    return jsonify(
        {
            'status': 'success',
            'message': 'Image uploaded',
            'images': images,
            'upload_limit': settings['gallery_max_uploads_per_family'],
        }
    )


@app.route('/api/family-gallery/image/<int:image_id>', methods=['DELETE'])
def delete_family_gallery_image(image_id: int):
    config = load_config()
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return jsonify({'status': 'error', 'message': 'Gallery is disabled'}), 404

    data = request.json or {}
    head_first_name = normalize_text(data.get('head_first_name', ''))
    head_second_name = normalize_text(data.get('head_second_name', ''))
    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404

        row = conn.execute(
            'SELECT id, filename FROM family_gallery_images WHERE id = ? AND family_id = ?',
            (image_id, family['id']),
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Image not found'}), 404

        conn.execute('DELETE FROM family_gallery_images WHERE id = ?', (image_id,))

        file_path = os.path.join(family_gallery_dir(family['id']), row['filename'])
        remove_file_if_exists(file_path)

        images = fetch_family_gallery_images(conn, family['id'])

    return jsonify({'status': 'success', 'message': 'Image deleted', 'images': images})


@app.route('/api/family-gallery/collage', methods=['GET'])
def family_gallery_collage():
    config = load_config()
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return jsonify({'status': 'error', 'message': 'Gallery is disabled'}), 404

    with get_db_connection() as conn:
        images = fetch_all_family_gallery_images(conn)

    return jsonify({'status': 'success', 'images': images})


@app.route('/api/family-gallery/download', methods=['GET'])
def download_family_gallery_zip():
    config = load_config()
    settings = get_gallery_settings(config)
    if not settings['gallery_enabled']:
        return jsonify({'status': 'error', 'message': 'Gallery is disabled'}), 404

    with get_db_connection() as conn:
        images = fetch_all_family_gallery_images(conn)

    if not images:
        return jsonify({'status': 'error', 'message': 'No images available for download'}), 404

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        used_names = set()

        for image in images:
            file_path = os.path.join(family_gallery_dir(image['family_id']), image['filename'])
            if not os.path.exists(file_path):
                continue

            source_name = image['original_name'] or image['filename']
            ext = Path(source_name).suffix.lower() or Path(image['filename']).suffix.lower() or '.jpg'
            base = secure_filename(Path(source_name).stem) or 'photo'
            zip_name = f"{base}{ext}"
            idx = 1
            while zip_name in used_names:
                idx += 1
                zip_name = f"{base}_{idx}{ext}"
            used_names.add(zip_name)
            archive.write(file_path, arcname=zip_name)

    buffer.seek(0)
    stamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'wedding_family_gallery_{stamp}.zip',
    )


@app.route('/api/invitation/download', methods=['GET'])
def download_family_invitation_pdf():
    head_first_name = normalize_text(request.args.get('head_first_name', ''))
    head_second_name = normalize_text(request.args.get('head_second_name', ''))

    if not head_first_name or not head_second_name:
        return jsonify({'status': 'error', 'message': 'head_first_name and head_second_name are required'}), 400

    with get_db_connection() as conn:
        family = get_family_by_head(conn, head_first_name, head_second_name)
        if not family:
            return jsonify({'status': 'error', 'message': 'Family not found'}), 404
        members = get_family_members(conn, family['id'])

    config = load_config()
    recipients = get_family_recipients(family, members)
    users_info = read_users_info()
    relevant_notes = get_relevant_users_info(users_info, recipients)
    prompt = build_family_prompt(config, family, members, recipients, relevant_notes)

    text = generate_invitation_text_with_llm(prompt)
    if not text:
        text = fallback_invitation_text(config, family, members, recipients)

    tg_url = telegram_profile_url(config)
    site_url = request.url_root.rstrip('/')
    pdf_bytes = render_invitation_pdf(config, family, recipients, text, tg_url, site_url)

    filename = '♥️ Приглашение на свадьбу.pdf'

    return send_file(
        pdf_bytes,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@app.route('/api/admin/invitation/settings', methods=['GET'])
@require_admin
def admin_get_invitation_settings():
    sber_api_key_set = bool(os.environ.get('SBER_API_KEY', '').strip())
    cloud_api_key_set = bool(AGENT_CLOUD_API_KEY)

    if INVITATION_PROVIDER == 'deepseek':
        provider_name = 'DeepSeek'
        model_name = DEEPSEEK_MODEL
        ready = bool(cloud_api_key_set and AGENT_CLOUDRU_API_URL and ChatOpenAI is not None)
    else:
        provider_name = 'GigaChat'
        model_name = GIGACHAT_MODEL
        ready = bool(sber_api_key_set and GigaChat is not None)

    return jsonify(
        {
            'status': 'success',
            'invitation': {
                'users_info_path': USERS_INFO_PATH,
                'backgrounds_path': BACKGROUND_ROOT,
                'llm_provider': provider_name,
                'llm_model': model_name,
                'model_selector': INVITATION_PROVIDER,
                'sber_api_key_set': sber_api_key_set,
                'agent_cloud_api_key_set': cloud_api_key_set,
                'agent_cloudru_api_url': AGENT_CLOUDRU_API_URL,
                'llm_ready': ready,
            },
        }
    )


@app.route('/api/photographer/images', methods=['GET'])
def get_photographer_images():
    with get_db_connection() as conn:
        images = fetch_photographer_images(conn)
    return jsonify({'status': 'success', 'images': images})


@app.route('/api/rsvp', methods=['POST'])
def deprecated_rsvp():
    return jsonify({'status': 'error', 'message': 'Deprecated. Use /api/families/* endpoints.'}), 410


@app.route('/api/question', methods=['POST'])
def deprecated_question():
    return jsonify({'status': 'error', 'message': 'Deprecated. Telegram integration removed.'}), 410


# ============ Admin API ============

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    with get_db_connection() as conn:
        families_count = conn.execute('SELECT COUNT(*) AS cnt FROM families').fetchone()['cnt']
        members_count = conn.execute('SELECT COUNT(*) AS cnt FROM family_members').fetchone()['cnt']
        attending_count = conn.execute('SELECT COUNT(*) AS cnt FROM family_members WHERE attending = 1').fetchone()['cnt']
        preferences_count = conn.execute('SELECT COUNT(*) AS cnt FROM family_preferences').fetchone()['cnt']
        family_gallery_images_count = conn.execute('SELECT COUNT(*) AS cnt FROM family_gallery_images').fetchone()['cnt']
        photographer_images_count = conn.execute('SELECT COUNT(*) AS cnt FROM photographer_images').fetchone()['cnt']

    return jsonify(
        {
            'status': 'success',
            'stats': {
                'families_count': families_count,
                'members_count': members_count,
                'attending_count': attending_count,
                'preferences_count': preferences_count,
                'family_gallery_images_count': family_gallery_images_count,
                'photographer_images_count': photographer_images_count,
            },
        }
    )


@app.route('/api/admin/families', methods=['GET'])
@require_admin
def admin_families():
    with get_db_connection() as conn:
        family_rows = conn.execute(
            'SELECT id FROM families ORDER BY datetime(created_at) DESC, id DESC'
        ).fetchall()
        families = [fetch_family_payload(conn, row['id']) for row in family_rows]

    return jsonify({'status': 'success', 'families': families})


@app.route('/api/admin/site-config', methods=['GET'])
@require_admin
def admin_get_config():
    return jsonify({'status': 'success', 'config': load_config()})


@app.route('/api/admin/site-config', methods=['PUT'])
@require_admin
def admin_save_config():
    data = request.json
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'JSON object expected'}), 400

    save_config(data)
    return jsonify({'status': 'success', 'message': 'Site config saved'})


@app.route('/api/admin/timeline', methods=['GET'])
@require_admin
def admin_get_timeline():
    config = load_config()
    event = config.get('event', {})
    day1 = event.get('timeline_day1', {})
    day2 = event.get('timeline_day2', {})

    return jsonify(
        {
            'status': 'success',
            'timeline': {
                'day1_title': day1.get('title', 'День 1'),
                'day2_title': day2.get('title', 'День 2'),
                'day1_events': day1.get('events', []),
                'day2_events': day2.get('events', []),
                'ceremony_note': event.get('ceremony_note', ''),
            },
        }
    )


@app.route('/api/admin/timeline', methods=['PUT'])
@require_admin
def admin_save_timeline():
    data = request.json or {}

    day1_title = normalize_text(data.get('day1_title', 'День 1')) or 'День 1'
    day2_title = normalize_text(data.get('day2_title', 'День 2')) or 'День 2'
    ceremony_note = normalize_text(data.get('ceremony_note', ''))
    day1_events = sanitize_timeline_events(data.get('day1_events', []))
    day2_events = sanitize_timeline_events(data.get('day2_events', []))

    config = load_config()
    config.setdefault('event', {})
    config['event'].setdefault('timeline_day1', {})
    config['event'].setdefault('timeline_day2', {})
    config['event']['timeline_day1']['title'] = day1_title
    config['event']['timeline_day2']['title'] = day2_title
    config['event']['timeline_day1']['events'] = day1_events
    config['event']['timeline_day2']['events'] = day2_events
    config['event']['ceremony_note'] = ceremony_note
    save_config(config)

    return jsonify({'status': 'success', 'message': 'Timeline updated'})


@app.route('/api/admin/features', methods=['GET'])
@require_admin
def admin_get_features():
    config = load_config()
    return jsonify({'status': 'success', 'features': get_gallery_settings(config)})


@app.route('/api/admin/features', methods=['PUT'])
@require_admin
def admin_save_features():
    data = request.json or {}
    gallery_enabled = parse_bool(data.get('gallery_enabled'), True)
    gallery_limit = parse_int(data.get('gallery_max_uploads_per_family'), 12, 1, 100)
    secret_video_enabled = parse_bool(data.get('secret_video_enabled'), False)

    config = load_config()
    config.setdefault('features', {})
    config['features']['gallery_enabled'] = gallery_enabled
    config['features']['gallery_max_uploads_per_family'] = gallery_limit
    config['features']['secret_video_enabled'] = secret_video_enabled
    save_config(config)
    return jsonify({'status': 'success', 'message': 'Features updated', 'features': get_gallery_settings(config)})


@app.route('/api/admin/theme', methods=['GET'])
@require_admin
def admin_get_theme():
    config = load_config()
    payload = get_theme_payload(config)
    payload['font_options'] = list(FONT_OPTIONS.keys())
    return jsonify({'status': 'success', 'theme': payload})


@app.route('/api/admin/theme', methods=['PUT'])
@require_admin
def admin_save_theme():
    data = request.json or {}

    primary_color = normalize_text(data.get('primary_color', DEFAULT_THEME['primary_color']))
    secondary_color = normalize_text(data.get('secondary_color', DEFAULT_THEME['secondary_color']))
    accent_color = normalize_text(data.get('accent_color', DEFAULT_THEME['accent_color']))
    light_bg = normalize_text(data.get('light_bg', DEFAULT_THEME['light_bg']))
    dark_bg = normalize_text(data.get('dark_bg', DEFAULT_THEME['dark_bg']))
    display_font = normalize_text(data.get('display_font', DEFAULT_THEME['display_font']))
    body_font = normalize_text(data.get('body_font', DEFAULT_THEME['body_font']))

    for color in [primary_color, secondary_color, accent_color, light_bg, dark_bg]:
        if not color_is_valid(color):
            return jsonify({'status': 'error', 'message': f'Invalid color value: {color}'}), 400

    if display_font not in FONT_OPTIONS:
        return jsonify({'status': 'error', 'message': 'Unsupported display font'}), 400
    if body_font not in FONT_OPTIONS:
        return jsonify({'status': 'error', 'message': 'Unsupported body font'}), 400

    config = load_config()
    config.setdefault('theme', {})
    config['theme']['primary_color'] = primary_color
    config['theme']['secondary_color'] = secondary_color
    config['theme']['accent_color'] = accent_color
    config['theme']['light_bg'] = light_bg
    config['theme']['dark_bg'] = dark_bg
    config['theme']['display_font'] = display_font
    config['theme']['body_font'] = body_font
    save_config(config)
    return jsonify({'status': 'success', 'message': 'Theme updated', 'theme': get_theme_payload(config)})


@app.route('/api/admin/content', methods=['GET'])
@require_admin
def admin_get_content():
    config = load_config()
    return jsonify({'status': 'success', 'content': get_admin_content_payload(config)})


@app.route('/api/admin/content', methods=['PUT'])
@require_admin
def admin_save_content():
    data = request.json or {}
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'JSON object expected'}), 400

    config = load_config()
    apply_admin_content_payload(config, data)
    save_config(config)
    return jsonify({'status': 'success', 'message': 'Content updated', 'content': get_admin_content_payload(config)})


@app.route('/api/admin/users-info', methods=['GET'])
@require_admin
def admin_get_users_info():
    return jsonify({'status': 'success', 'users_info': read_users_info_raw(), 'path': USERS_INFO_PATH})


@app.route('/api/admin/users-info', methods=['PUT'])
@require_admin
def admin_save_users_info():
    data = request.json or {}
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'JSON object expected'}), 400

    users_info = data.get('users_info', '')
    if not isinstance(users_info, str):
        return jsonify({'status': 'error', 'message': 'users_info must be a string'}), 400

    write_users_info_raw(users_info)
    return jsonify({'status': 'success', 'message': 'users_info.txt updated', 'path': USERS_INFO_PATH})


@app.route('/api/admin/database/reset', methods=['POST'])
@require_admin
def admin_reset_database():
    with get_db_connection() as conn:
        conn.execute('DELETE FROM photographer_images')
        conn.execute('DELETE FROM families')
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('families', 'family_members', 'family_preferences', 'family_gallery_images', 'photographer_images')"
        )

    shutil.rmtree(FAMILY_GALLERY_ROOT, ignore_errors=True)
    shutil.rmtree(PHOTOGRAPHER_ROOT, ignore_errors=True)
    os.makedirs(FAMILY_GALLERY_ROOT, exist_ok=True)
    os.makedirs(PHOTOGRAPHER_ROOT, exist_ok=True)

    return jsonify({'status': 'success', 'message': 'Database cleared. Site data reset to empty state.'})


@app.route('/api/admin/family-gallery', methods=['GET'])
@require_admin
def admin_family_gallery_images():
    with get_db_connection() as conn:
        images = fetch_all_family_gallery_images(conn)
    return jsonify({'status': 'success', 'images': images})


@app.route('/api/admin/family-gallery/collage', methods=['GET'])
@require_admin
def admin_family_gallery_collage():
    with get_db_connection() as conn:
        images = fetch_all_family_gallery_images(conn)
    return jsonify({'status': 'success', 'images': images})


@app.route('/api/admin/family-gallery/<int:image_id>', methods=['DELETE'])
@require_admin
def admin_delete_family_gallery_image(image_id: int):
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT id, family_id, filename FROM family_gallery_images WHERE id = ?',
            (image_id,),
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Image not found'}), 404

        conn.execute('DELETE FROM family_gallery_images WHERE id = ?', (image_id,))
        file_path = os.path.join(family_gallery_dir(row['family_id']), row['filename'])
        remove_file_if_exists(file_path)

    return jsonify({'status': 'success', 'message': 'Image deleted'})


@app.route('/api/admin/photographer/upload', methods=['POST'])
@require_admin
def admin_upload_photographer_image():
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'status': 'error', 'message': 'Image file is required'}), 400
    if not allowed_image_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Unsupported image extension'}), 400

    original_name = secure_filename(file.filename)
    ext = Path(original_name).suffix.lower()
    new_name = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(PHOTOGRAPHER_ROOT, new_name)
    file.save(target_path)

    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO photographer_images (filename, original_name, uploaded_at) VALUES (?, ?, ?)',
            (new_name, original_name, now),
        )
        images = fetch_photographer_images(conn)

    return jsonify({'status': 'success', 'message': 'Image uploaded', 'images': images})


@app.route('/api/admin/photographer/<int:image_id>', methods=['DELETE'])
@require_admin
def admin_delete_photographer_image(image_id: int):
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT id, filename FROM photographer_images WHERE id = ?',
            (image_id,),
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Image not found'}), 404

        conn.execute('DELETE FROM photographer_images WHERE id = ?', (image_id,))
        file_path = os.path.join(PHOTOGRAPHER_ROOT, row['filename'])
        remove_file_if_exists(file_path)
        images = fetch_photographer_images(conn)

    return jsonify({'status': 'success', 'message': 'Image deleted', 'images': images})


@app.route('/api/admin/secret-video', methods=['GET'])
@require_admin
def admin_get_secret_video():
    return jsonify({'status': 'success', 'secret_video': get_secret_video_state()})


@app.route('/api/admin/secret-video/upload', methods=['POST'])
@require_admin
def admin_upload_secret_video():
    file = request.files.get('video')
    if not file or not file.filename:
        return jsonify({'status': 'error', 'message': 'Video file is required'}), 400

    if not allowed_video_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Unsupported video extension'}), 400

    os.makedirs(SECRET_VIDEO_ROOT, exist_ok=True)
    for filename in os.listdir(SECRET_VIDEO_ROOT):
        path = os.path.join(SECRET_VIDEO_ROOT, filename)
        if os.path.isfile(path):
            remove_file_if_exists(path)

    safe_name = secure_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    target_name = f"secret_video_{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(SECRET_VIDEO_ROOT, target_name)
    file.save(target_path)

    return jsonify({'status': 'success', 'message': 'Secret video uploaded', 'secret_video': get_secret_video_state()})


@app.route('/api/admin/secret-video', methods=['DELETE'])
@require_admin
def admin_delete_secret_video():
    state = get_secret_video_state()
    if not state['has_video']:
        return jsonify({'status': 'error', 'message': 'Secret video not found'}), 404

    remove_file_if_exists(os.path.join(SECRET_VIDEO_ROOT, state['filename']))
    return jsonify({'status': 'success', 'message': 'Secret video deleted', 'secret_video': get_secret_video_state()})


@app.errorhandler(400)
def bad_request(error):
    err_text = request.args.get('error')
    if not err_text:
        err_text = getattr(error, 'description', None) or str(error)
    return render_template('400.html', error_text=err_text), 400


@app.errorhandler(413)
def payload_too_large(error):
    err_text = (
        f"Файл слишком большой. Максимальный размер: {_max_upload_mb} MB "
        f"(MAX_CONTENT_LENGTH_MB={_max_upload_mb})."
    )
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': err_text}), 413
    return render_template('400.html', error_text=err_text), 413


@app.route('/400')
def show_400():
    err_text = request.args.get('error', '')
    return render_template('400.html', error_text=err_text), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
