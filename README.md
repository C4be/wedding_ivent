# Wedding Invitation Site 💒

Одностраничный сайт-приглашение на свадебное торжество.

## Запуск

### Production
```bash
docker-compose up -d wedding-site
```
Сайт будет доступен по адресу: http://localhost:8080

### Development (с hot reload)
```bash
docker-compose --profile dev up wedding-site-dev
```
Сайт будет доступен по адресу: http://localhost:5000

## Структура

```
wedding_ivent/
├── site/
│   ├── src/
│   │   ├── app.py              # Flask приложение
│   │   ├── templates/
│   │   │   └── index.html      # Главный шаблон
│   │   └── static/
│   │       ├── css/style.css   # Стили
│   │       ├── js/main.js      # Скрипты
│   │       └── images/         # Изображения для сайта
│   ├── materials/
│   │   ├── site.info.json      # Конфигурация сайта
│   │   └── imgs/               # Исходные изображения
│   ├── Dockerfile
│   └── requirements.txt
├── marks/
│   └── site.md                 # Описание сайта
├── docker-compose.yml
└── README.md
```

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Получить конфигурацию |
| PUT | `/api/config` | Обновить конфигурацию |
| PATCH | `/api/config/<section>` | Обновить секцию |
| POST | `/api/rsvp` | Отправить анкету |
| POST | `/api/question` | Отправить вопрос |
| GET | `/api/gallery` | Получить галерею |
| POST | `/api/gallery` | Добавить фото в галерею |
| POST | `/api/faq` | Добавить FAQ |

## Настройка Telegram бота

1. Создайте бота через @BotFather
2. Получите токен и chat_id
3. Обновите `site/materials/site.info.json`:
```json
"telegram_bot": {
    "token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
}
```

## Добавление изображений

1. Поместите фото в `site/src/static/images/`
2. Обновите `site.info.json` с именами файлов
3. Для hero-изображения: `hero.jpg`

# Запуск БД

Для того, чтобы запустить БД нужно запустить командой

```bash
docker-compose --env-file ./database_service/.env up -d --build db
```

Проверить настроечные файлы 

```bash
docker exec -it wedding-db ls -la /docker-entrypoint-initdb.d
```

# Запуск DB_SERVICE

```bash
docker-compose --env-file ./database_service/.env up -d db_service --build
```