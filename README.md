# Idris AI Manager Bot

Минималистичный профессиональный Telegram-бот на PyTelegramBotAPI.

## Что умеет

- AI-менеджер Идриса
- Короткое и аккуратное меню
- Заявки через кнопки
- Без вопроса о бюджете
- Без раздела примеров работ
- AI-ответ клиенту после заявки
- AI-анализ заявки для админа
- Отправка заявки админу в Telegram
- Админ-панель через кнопки
- Статусы заявок
- SQLite база данных
- Готов для Railway и GitHub

## Переменные

Добавь в Railway Variables:

```env
BOT_TOKEN=токен из BotFather
ADMIN_ID=твой Telegram ID
OPENROUTER_API_KEY=ключ OpenRouter
AI_MODEL=openai/gpt-4o-mini
```

`AI_MODEL` можно не добавлять. По умолчанию используется `openai/gpt-4o-mini`.

## Как узнать ADMIN_ID

Напиши в Telegram боту:

```text
@userinfobot
```

Он покажет твой Telegram ID.

## Railway

1. Загрузи проект в GitHub
2. Открой Railway
3. New Project
4. Deploy from GitHub repo
5. Добавь Variables
6. Deploy

## Важно

Не загружай настоящий `.env` в GitHub.
