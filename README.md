# Wedding Invitation Site 💒

Одностраничный сайт-приглашение на свадебное торжество.

Проект упрощен до одного сервиса `site`:
- Flask приложение
- SQLite (`site/materials/wedding.db`)
- формы регистрации семьи и предпочтений
- админ-панель `/admin` для статистики и интерактивного управления контентом

## Запуск

### Production
```bash
docker compose up -d --build wedding-site
```
Сайт будет доступен по адресу: http://localhost:8080

### Development (с hot reload)
```bash
docker compose --profile dev up --build wedding-site-dev
```
Сайт будет доступен по адресу: http://localhost:5050

## Важные переменные окружения

- `SQLITE_DB_PATH` - путь к SQLite БД (по умолчанию `/app/materials/wedding.db` в контейнере).
- `ADMIN_PASSWORD` - пароль для API админ-панели (header `X-Admin-Password`).
- `MODEL` - провайдер LLM для приглашений: `giga` или `deepseek`.
- `GIGACHAT_MODEL` - модель для GigaChat (по умолчанию `GigaChat-2`).
- `SBER_API_KEY` - ключ для генерации персональных PDF-приглашений через GigaChat.
- `DEEPSEEK_MODEL` - модель для DeepSeek (по умолчанию `deepseek-ai/DeepSeek-V4-Pro`).
- `AGENT_CLOUD_API_KEY` - API-ключ Cloud.ru для DeepSeek.
- `AGENT_CLOUDRU_API_URL` - базовый URL Cloud.ru API (по умолчанию `https://foundation-models.api.cloud.ru/v1`).
- `MAX_CONTENT_LENGTH_MB` - максимальный размер загружаемых файлов в MB (по умолчанию `250`).

В `docker-compose.yml` по умолчанию стоит `ADMIN_PASSWORD=change-me`; перед публичным запуском обязательно смените значение.

## Основные страницы

- `/` - основной сайт
- `/admin` - админ-панель
- `/gallery` - семейная галерея (можно скрыть через админ-панель)
- `/photographer` - фотографии от профессионального фотографа
- `/secret_video` - страница "Секретный подарок жене" (показывается по флагу в админке)

## REST API (текущее)

### Публичные

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Получить конфигурацию сайта |
| PUT | `/api/config` | Полностью обновить конфигурацию |
| PATCH | `/api/config/<section>` | Обновить секцию конфигурации |
| POST | `/api/families/register` | Найти/создать семейную группу по ФИО главы |
| DELETE | `/api/families/register` | Удалить семейную группу по ФИО главы |
| GET | `/api/families/by-head` | Получить семью по ФИО главы |
| POST | `/api/families/member` | Добавить/обновить участника семьи |
| DELETE | `/api/families/member` | Удалить участника семьи |
| GET | `/api/preferences` | Получить предпочтения семьи |
| POST | `/api/preferences` | Сохранить предпочтения семьи |
| GET | `/api/family-gallery/settings` | Получить настройки семейной галереи |
| GET | `/api/family-gallery/by-head` | Получить фото семьи по ФИО главы |
| GET | `/api/family-gallery/collage` | Получить общий коллаж всех семейных фото |
| POST | `/api/family-gallery/upload` | Загрузить фото в галерею семьи |
| DELETE | `/api/family-gallery/image/<id>` | Удалить фото из галереи семьи |
| GET | `/api/family-gallery/download` | Скачать все семейные фото архивом |
| GET | `/api/photographer/images` | Список фото профессионального фотографа |
| GET | `/api/invitation/download` | Скачать персональное PDF-приглашение для семьи |
| GET | `/api/gallery` | Получить галерею |
| POST | `/api/gallery` | Добавить фото в галерею |
| POST | `/api/faq` | Добавить FAQ |
| GET | `/api/slider-images` | Получить изображения слайдера |

### Админ API (требуют `X-Admin-Password`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Сводная статистика |
| GET | `/api/admin/families` | Список всех семей и участников |
| GET | `/api/admin/timeline` | Загрузить программу дня |
| PUT | `/api/admin/timeline` | Сохранить программу дня |
| GET | `/api/admin/features` | Загрузить фичи сайта (галерея, лимиты) |
| PUT | `/api/admin/features` | Сохранить фичи сайта |
| GET | `/api/admin/theme` | Загрузить стили сайта |
| PUT | `/api/admin/theme` | Сохранить стили сайта |
| GET | `/api/admin/content` | Загрузить основной контент сайта |
| PUT | `/api/admin/content` | Сохранить основной контент сайта |
| GET | `/api/admin/family-gallery` | Список фото из семейной галереи |
| GET | `/api/admin/family-gallery/collage` | Коллаж фото семейной галереи |
| DELETE | `/api/admin/family-gallery/<id>` | Удалить фото из семейной галереи |
| POST | `/api/admin/photographer/upload` | Загрузить фото фотографа |
| DELETE | `/api/admin/photographer/<id>` | Удалить фото фотографа |
| GET | `/api/admin/secret-video` | Статус секретного видео |
| POST | `/api/admin/secret-video/upload` | Загрузить секретное видео |
| DELETE | `/api/admin/secret-video` | Удалить секретное видео |
| GET | `/api/admin/invitation/settings` | Проверить настройки генерации PDF-приглашений |
| GET | `/api/admin/site-config` | Получить конфиг сайта |
| PUT | `/api/admin/site-config` | Сохранить конфиг сайта |

## Добавление изображений

- Слайдер: `site/src/static/images/slider`
- Семейная галерея: `site/src/static/images/family_gallery/<family_id>/`
- Фото фотографа: `site/src/static/images/photographer/`
- Секретное видео: `site/src/static/media/secret_video/`
- Фоны для PDF-приглашений: `site/src/static/images/backgrounds/`
- Основные изображения сайта: `site/src/static/images/`

## Персональные приглашения (PDF)

- На главной странице в конце добавлен блок "Скачать пригласительное".
- В шаблон приглашения включаются: дата, мероприятие, текст приглашения, QR-код на сайт, контакты.
- Дополнительный контекст для генерации хранится в `site/materials/users_info.txt` (создается вручную).
- Если ключ для выбранной модели не задан или модель недоступна, используется локальный fallback-текст.

## Замечания

- Старые Telegram-эндпоинты (`/api/rsvp`, `/api/question`) оставлены как deprecated (возвращают `410`).
- База SQLite создается автоматически при первом запуске.
