import os
import sqlite3
import requests
import telebot
from datetime import datetime
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID is missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
users = {}

db = sqlite3.connect("leads.db", check_same_thread=False)
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    name TEXT,
    contact TEXT,
    service TEXT,
    project TEXT,
    deadline TEXT,
    ai_answer TEXT,
    ai_admin_note TEXT,
    status TEXT,
    date TEXT
)
""")
db.commit()


def clean(text):
    if text is None:
        return ""
    return str(text).replace("<", "&lt;").replace(">", "&gt;").strip()


def main_menu(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🚀 Оставить заявку"))
    kb.add(KeyboardButton("💼 Услуги"), KeyboardButton("👨‍💻 Об Идрисе"))
    kb.add(KeyboardButton("❓ FAQ"), KeyboardButton("📩 Контакты"))
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("🔐 Админ-панель"))
    return kb


def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("⬅️ Главное меню"))
    return kb


def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Все заявки"), KeyboardButton("🔥 Новые"))
    kb.add(KeyboardButton("✅ В работе"), KeyboardButton("🏁 Завершённые"))
    kb.add(KeyboardButton("📊 Статистика"), KeyboardButton("⬅️ Главное меню"))
    return kb


def services_inline():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🤖 Telegram-бот", callback_data="service|Telegram-бот"))
    kb.add(InlineKeyboardButton("🧠 AI-бот", callback_data="service|AI-бот"))
    kb.add(InlineKeyboardButton("🌐 Сайт / Лендинг", callback_data="service|Сайт / Лендинг"))
    kb.add(InlineKeyboardButton("🛠 Доработка / исправление", callback_data="service|Доработка / исправление"))
    kb.add(InlineKeyboardButton("⚙️ Автоматизация", callback_data="service|Автоматизация"))
    return kb


def deadline_inline():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Срочно", callback_data="deadline|Срочно"))
    kb.add(InlineKeyboardButton("За 3–5 дней", callback_data="deadline|За 3–5 дней"))
    kb.add(InlineKeyboardButton("За неделю", callback_data="deadline|За неделю"))
    kb.add(InlineKeyboardButton("Не знаю", callback_data="deadline|Не знаю"))
    return kb


def lead_actions(lead_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ В работу", callback_data=f"status|{lead_id}|В работе"),
        InlineKeyboardButton("🏁 Завершить", callback_data=f"status|{lead_id}|Завершено")
    )
    kb.add(InlineKeyboardButton("❌ Отказать", callback_data=f"status|{lead_id}|Отказано"))
    return kb


def ai_request(prompt):
    if not OPENROUTER_API_KEY:
        return None

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram.org",
                "X-Title": "Idris AI Manager Bot"
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты AI-менеджер разработчика Идриса. "
                            "Идрис делает Telegram-ботов, AI-ботов, сайты на HTML/CSS и автоматизацию. "
                            "Пиши кратко, уважительно, понятно и профессионально. "
                            "Не называй точную цену. Не обещай точные сроки. "
                            "Не говори слишком длинно. Пиши по-русски."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.45,
                "max_tokens": 450
            },
            timeout=35
        )

        data = r.json()

        if "choices" not in data:
            print("AI ERROR:", data)
            return None

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("AI REQUEST ERROR:", e)
        return None


def make_client_ai_answer(data):
    prompt = f"""
Клиент оставил заявку Идрису.

Имя: {data["name"]}
Контакт: {data["contact"]}
Услуга: {data["service"]}
Описание: {data["project"]}
Срок: {data["deadline"]}

Напиши короткий ответ клиенту ОТ ИМЕНИ ИДРИСА.

Важно:
- поблагодари
- скажи, что заявка получена
- скажи, что ты посмотришь задачу и свяжешься
- не называй цену
- не обещай точный срок
- максимум 700 символов
"""
    result = ai_request(prompt)

    if result:
        return result

    return f"""Спасибо за заявку, {data["name"]} ✅

Я получил описание проекта. Посмотрю задачу и свяжусь с тобой, чтобы уточнить детали и предложить лучший вариант решения."""


def make_admin_ai_note(data):
    prompt = f"""
Проанализируй заявку для Идриса.

Имя: {data["name"]}
Контакт: {data["contact"]}
Услуга: {data["service"]}
Описание: {data["project"]}
Срок: {data["deadline"]}

Сделай коротко:
1. Что нужно клиенту
2. Какие вопросы задать
3. Сложность: низкая / средняя / высокая
4. Как лучше ответить клиенту
"""
    result = ai_request(prompt)

    if result:
        return result

    return "AI-анализ временно недоступен. Проверь заявку вручную."


def save_lead(chat_id, ai_answer, ai_admin_note):
    u = users[chat_id]
    date = datetime.now().strftime("%d.%m.%Y %H:%M")

    sql.execute("""
    INSERT INTO leads
    (user_id, username, name, contact, service, project, deadline, ai_answer, ai_admin_note, status, date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        u.get("username", "none"),
        u["name"],
        u["contact"],
        u["service"],
        u["project"],
        u["deadline"],
        ai_answer,
        ai_admin_note,
        "Новая",
        date
    ))
    db.commit()
    return sql.lastrowid


def lead_text(row):
    username = row[2]
    username_text = f"@{clean(username)}" if username != "none" else "не указан"

    return f"""
<b>Заявка #{row[0]}</b>

👤 <b>Имя:</b> {clean(row[3])}
🔗 <b>Username:</b> {username_text}
📞 <b>Контакт:</b> {clean(row[4])}
💼 <b>Услуга:</b> {clean(row[5])}
💡 <b>Описание:</b> {clean(row[6])}
⏳ <b>Срок:</b> {clean(row[7])}
📌 <b>Статус:</b> {clean(row[10])}
🕒 <b>Дата:</b> {clean(row[11])}
🆔 <b>User ID:</b> {row[1]}

<b>🧠 Ответ клиенту:</b>
{clean(row[8])}

<b>📌 AI-анализ:</b>
{clean(row[9])}
"""


@bot.message_handler(commands=["start"])
def start(message):
    text = """
<b>Здравствуйте 👋</b>

Я — AI-менеджер Идриса.

Помогу быстро оставить заявку на Telegram-бота, сайт или автоматизацию.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "⬅️ Главное меню")
def home(message):
    users.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "Главное меню 👇", reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "💼 Услуги")
def services(message):
    text = """
<b>💼 Услуги Идриса</b>

🤖 Telegram-боты для бизнеса  
🧠 AI-боты и AI-помощники  
🌐 Лендинги и сайты-визитки  
⚙️ Автоматизация заявок и процессов  
🛠 Доработка и исправление ботов
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "👨‍💻 Об Идрисе")
def about(message):
    text = """
<b>👨‍💻 Об Идрисе</b>

Идрис — разработчик Telegram-ботов и простых сайтов.

Опыт: около 5 лет.  
Работал с клиентами через Kwork, Upwork и ProfiRU.

Главный фокус: сделать проект понятным, удобным и рабочим.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "❓ FAQ")
def faq(message):
    text = """
<b>❓ FAQ</b>

<b>Можно заказать бота?</b>
Да. Для заявок, магазина, записи, AI и других задач.

<b>Можно заказать сайт?</b>
Да. Лендинг, визитка или простой сайт.

<b>Можно доработать старый бот?</b>
Да. Можно исправить ошибки или добавить функции.

<b>Как начать?</b>
Нажмите «🚀 Оставить заявку».
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "📩 Контакты")
def contacts(message):
    text = """
<b>📩 Контакты</b>

Чтобы связаться с Идрисом, оставьте заявку через кнопку ниже.

После заявки Идрис получит все данные в Telegram.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "🚀 Оставить заявку")
def new_lead(message):
    users[message.chat.id] = {
        "step": "name",
        "username": message.from_user.username or "none"
    }

    bot.send_message(
        message.chat.id,
        "Как вас зовут?",
        reply_markup=back_menu()
    )


@bot.message_handler(func=lambda m: m.chat.id in users)
def lead_process(message):
    chat_id = message.chat.id

    if message.text == "⬅️ Главное меню":
        users.pop(chat_id, None)
        bot.send_message(chat_id, "Заявка отменена.", reply_markup=main_menu(chat_id))
        return

    step = users[chat_id]["step"]

    if step == "name":
        users[chat_id]["name"] = message.text
        users[chat_id]["step"] = "contact"
        bot.send_message(chat_id, "Оставьте контакт для связи.\n\nНапример: username или номер телефона.")

    elif step == "contact":
        users[chat_id]["contact"] = message.text
        users[chat_id]["step"] = "service"
        bot.send_message(chat_id, "Что нужно сделать?", reply_markup=services_inline())

    elif step == "project":
        users[chat_id]["project"] = message.text
        users[chat_id]["step"] = "deadline"
        bot.send_message(chat_id, "Когда желательно получить проект?", reply_markup=deadline_inline())


@bot.callback_query_handler(func=lambda c: c.data.startswith("service|"))
def choose_service(call):
    chat_id = call.message.chat.id

    if chat_id not in users:
        bot.answer_callback_query(call.id, "Начните заявку заново")
        return

    service = call.data.split("|", 1)[1]
    users[chat_id]["service"] = service
    users[chat_id]["step"] = "project"

    bot.edit_message_text(
        f"Выбрано: <b>{clean(service)}</b> ✅",
        chat_id,
        call.message.message_id
    )

    bot.send_message(chat_id, "Коротко опишите задачу.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("deadline|"))
def choose_deadline(call):
    chat_id = call.message.chat.id

    if chat_id not in users:
        bot.answer_callback_query(call.id, "Начните заявку заново")
        return

    deadline = call.data.split("|", 1)[1]
    users[chat_id]["deadline"] = deadline

    bot.edit_message_text(
        f"Срок: <b>{clean(deadline)}</b> ✅",
        chat_id,
        call.message.message_id
    )

    bot.send_message(chat_id, "Заявка обрабатывается...")

    ai_answer = make_client_ai_answer(users[chat_id])
    ai_admin_note = make_admin_ai_note(users[chat_id])
    lead_id = save_lead(chat_id, ai_answer, ai_admin_note)

    sql.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    row = sql.fetchone()

    bot.send_message(chat_id, ai_answer, reply_markup=main_menu(chat_id))

    bot.send_message(
        ADMIN_ID,
        "🔥 <b>Новая заявка</b>\n" + lead_text(row),
        reply_markup=lead_actions(lead_id)
    )

    users.pop(chat_id, None)


@bot.message_handler(func=lambda m: m.text == "🔐 Админ-панель")
def admin(message):
    if message.chat.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "🔐 Админ-панель", reply_markup=admin_menu())


@bot.message_handler(func=lambda m: m.text in ["📋 Все заявки", "🔥 Новые", "✅ В работе", "🏁 Завершённые"])
def show_leads(message):
    if message.chat.id != ADMIN_ID:
        return

    if message.text == "📋 Все заявки":
        sql.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 10")
    elif message.text == "🔥 Новые":
        sql.execute("SELECT * FROM leads WHERE status='Новая' ORDER BY id DESC LIMIT 10")
    elif message.text == "✅ В работе":
        sql.execute("SELECT * FROM leads WHERE status='В работе' ORDER BY id DESC LIMIT 10")
    else:
        sql.execute("SELECT * FROM leads WHERE status='Завершено' ORDER BY id DESC LIMIT 10")

    rows = sql.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "Заявок нет.", reply_markup=admin_menu())
        return

    for row in rows:
        bot.send_message(message.chat.id, lead_text(row), reply_markup=lead_actions(row[0]))


@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def statistics(message):
    if message.chat.id != ADMIN_ID:
        return

    sql.execute("SELECT COUNT(*) FROM leads")
    total = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM leads WHERE status='Новая'")
    new = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM leads WHERE status='В работе'")
    work = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM leads WHERE status='Завершено'")
    done = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM leads WHERE status='Отказано'")
    refused = sql.fetchone()[0]

    text = f"""
<b>📊 Статистика</b>

Всего: <b>{total}</b>
🔥 Новые: <b>{new}</b>
✅ В работе: <b>{work}</b>
🏁 Завершённые: <b>{done}</b>
❌ Отказано: <b>{refused}</b>
"""
    bot.send_message(message.chat.id, text, reply_markup=admin_menu())


@bot.callback_query_handler(func=lambda c: c.data.startswith("status|"))
def change_status(call):
    if call.message.chat.id != ADMIN_ID:
        return

    _, lead_id, status = call.data.split("|", 2)

    sql.execute("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
    db.commit()

    sql.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    row = sql.fetchone()

    bot.edit_message_text(
        lead_text(row),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=lead_actions(lead_id)
    )

    bot.answer_callback_query(call.id, f"Статус: {status}")


@bot.message_handler(content_types=["text"])
def unknown(message):
    bot.send_message(message.chat.id, "Выберите действие через меню 👇", reply_markup=main_menu(message.chat.id))


print("Idris AI Manager Bot started")
bot.infinity_polling(skip_pending=True)
