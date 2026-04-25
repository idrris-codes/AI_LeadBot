# Idris LeadBot AI

Профессиональный Telegram-бот для заявок на PyTelegramBotAPI.

## Что умеет бот

- Принимает заявки через кнопки
- Показывает услуги, портфолио, FAQ и контакты
- Отвечает клиенту через ИИ
- Отправляет заявку админу в Telegram
- Делает AI-анализ заявки для админа
- Имеет админ-панель через кнопки
- Сохраняет заявки в SQLite
- Позволяет менять статус заявки: Новая, В работе, Завершено, Отказано
- Готов для Railway + GitHub

## Файлы

- `main.py` — основной код бота
- `requirements.txt` — библиотеки
- `Procfile` — запуск на Railway
- `.env.example` — пример переменных

## Переменные Railway

Создай переменные:

```env
BOT_TOKEN=токен из BotFather
ADMIN_ID=твой Telegram ID
OPENROUTER_API_KEY=ключ OpenRouter
AI_MODEL=openai/gpt-4o-mini
```

`AI_MODEL` можно не добавлять. По умолчанию используется `openai/gpt-4o-mini`.

## Как узнать ADMIN_ID

Открой Telegram и напиши боту:

```text
@userinfobot
```

Он покажет твой ID.

## Запуск локально

```bash
pip install -r requirements.txt
python main.py
```

## Запуск на Railway

1. Создай GitHub репозиторий
2. Загрузи туда все файлы
3. Открой Railway
4. New Project
5. Deploy from GitHub repo
6. Добавь переменные в Variables
7. Deploy

## Важно

В GitHub не загружай настоящий `.env` с токенами.
Загружай только `.env.example`.
