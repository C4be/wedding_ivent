# AGENTS.md

## Scope and layout
- Runtime is now **single-service Flask** in `site/` (`site/src/app.py`) with SQLite storage.
- `database_service/` and `tg_bot/` are legacy and not used by current `docker-compose.yml`.
- There is no CI/test/lint/typecheck config in this repo.

## Commands (run from repo root)
- Production stack:
  - `docker compose up -d --build wedding-site`
  - URL: `http://localhost:8080`
- Dev hot reload:
  - `docker compose --profile dev up --build wedding-site-dev`
  - URL: `http://localhost:5050`
- Config check:
  - `docker compose config`

## Source of truth
- Site content config: `site/materials/site.info.json`.
- Runtime DB: `site/materials/wedding.db` (SQLite, auto-created).
- Family registration and preferences are persisted in SQLite via `site/src/app.py`.
- Slider images are folder-driven: `site/src/static/images/slider`.
- Family gallery images live in `site/src/static/images/family_gallery/<family_id>/`.
- Photographer images live in `site/src/static/images/photographer/`.
- Invitation PDF backgrounds live in `site/src/static/images/backgrounds/`.
- Invitation extra prompt context lives in `site/materials/users_info.txt` (manual file).

## Current public API contracts
- Family flow uses:
  - `POST /api/families/register`
  - `GET /api/families/by-head`
  - `POST /api/families/member`
  - `DELETE /api/families/member`
  - `GET /api/preferences`
  - `POST /api/preferences`
- Family gallery flow uses:
  - `GET /api/family-gallery/settings`
  - `GET /api/family-gallery/by-head`
  - `GET /api/family-gallery/collage`
  - `POST /api/family-gallery/upload`
  - `DELETE /api/family-gallery/image/<id>`
  - `GET /api/family-gallery/download`
- Photographer gallery uses:
  - `GET /api/photographer/images`
- Invitation flow uses:
  - `GET /api/invitation/download`
- Deprecated endpoints return `410`:
  - `POST /api/rsvp`
  - `POST /api/question`

## Admin panel
- Admin page: `/admin` (`site/src/templates/admin.html`).
- Admin API auth is header-based: `X-Admin-Password`.
- Password source: `ADMIN_PASSWORD` env var (compose default is placeholder `change-me`; replace for real use).
- Admin has dedicated APIs for timeline/theme/content/features; JSON editor is fallback only.
- Invitation generation status is available in admin API (`/api/admin/invitation/settings`).

## Runtime gotchas
- If using local Python (outside Docker), set `SQLITE_DB_PATH` if default path is not desired.
- `SBER_API_KEY` is optional: if missing, invitation PDF uses fallback text instead of GigaChat.
- Keep `.venv/` under `database_service/` and `tg_bot/` out of searches/edits.
