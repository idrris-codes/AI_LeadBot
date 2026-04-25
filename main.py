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

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing. AI answers will use fallback text.")

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
    budget TEXT,
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
    kb.add(KeyboardButton("💼 Услуги"), KeyboardButton("🔥 Примеры работ"))
    kb.add(KeyboardButton("👨‍💻 Обо мне"), KeyboardButton("❓ FAQ"))
    kb.add(KeyboardButton("📩 Контакты"))
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("🔐 Админ-панель"))
    return kb


def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("⬅️ Главное меню"))
    return kb


def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Все заявки"), KeyboardButton("🔥 Новые заявки"))
    kb.add(KeyboardButton("✅ В работе"), KeyboardButton("🏁 Завершённые"))
    kb.add(KeyboardButton("📊 Статистика"), KeyboardButton("⬅️ Главное меню"))
    return kb


def services_inline():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🤖 Telegram-бот", callback_data="service|Telegram-бот"))
    kb.add(InlineKeyboardButton("🌐 Сайт / Лендинг", callback_data="service|Сайт / Лендинг"))
    kb.add(InlineKeyboardButton("🛠 Исправить бота", callback_data="service|Исправление бота"))
    kb.add(InlineKeyboardButton("⚙️ Автоматизация", callback_data="service|Автоматизация"))
    kb.add(InlineKeyboardButton("🧠 AI-бот", callback_data="service|AI-бот"))
    return kb


def budget_inline():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("До 100$", callback_data="budget|До 100$"))
    kb.add(InlineKeyboardButton("100$–300$", callback_data="budget|100$–300$"))
    kb.add(InlineKeyboardButton("300$–500$", callback_data="budget|300$–500$"))
    kb.add(InlineKeyboardButton("500$+", callback_data="budget|500$+"))
    kb.add(InlineKeyboardButton("Пока не знаю", callback_data="budget|Пока не знаю"))
    return kb


def deadline_inline():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Срочно", callback_data="deadline|Срочно"))
    kb.add(InlineKeyboardButton("За 3–5 дней", callback_data="deadline|За 3–5 дней"))
    kb.add(InlineKeyboardButton("За неделю", callback_data="deadline|За неделю"))
    kb.add(InlineKeyboardButton("За месяц", callback_data="deadline|За месяц"))
    kb.add(InlineKeyboardButton("Пока не знаю", callback_data="deadline|Пока не знаю"))
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
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram.org",
                "X-Title": "Idris LeadBot AI"
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты вежливый AI-менеджер разработчика Идриса. "
                            "Идрис делает Telegram-ботов на Python, AI-ботов, сайты на HTML/CSS, "
                            "лендинги, сайты-визитки и автоматизацию для бизнеса. "
                            "Он работает около 5 лет, раньше брал клиентов с Kwork, Upwork и ProfiRU. "
                            "Пиши уважительно, понятно, уверенно, но без пустых обещаний. "
                            "Не называй точную цену и точный срок без анализа. Пиши на русском."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.55,
                "max_tokens": 800
            },
            timeout=35
        )

        data = response.json()

        if "choices" not in data:
            print("AI ERROR:", data)
            return None

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("AI REQUEST ERROR:", e)
        return None


def make_client_ai_answer(data):
    prompt = f"""
Клиент оставил заявку разработчику Идрису.

Имя: {data["name"]}
Контакт: {data["contact"]}
Услуга: {data["service"]}
Описание проекта: {data["project"]}
Бюджет: {data["budget"]}
Срок: {data["deadline"]}

Напиши клиенту красивый ответ от имени Идриса.

Требования:
- поблагодари за заявку
- покажи, что заявка понята
- объясни, что Идрис посмотрит детали
- скажи, что лучше уточнить функции и примеры
- не называй точную цену
- не обещай точный срок
- скажи, что Идрис скоро свяжется
- тон: уважительный, уверенный, человеческий
- не больше 1200 символов
"""
    result = ai_request(prompt)

    if result:
        return result

    return f"""Спасибо за заявку, {data["name"]} ✅

Я получил информацию по проекту и посмотрю детали. После этого свяжусь с тобой, чтобы уточнить функции, сроки и примерную стоимость.

Если есть пример похожего бота или сайта — можешь сразу отправить его мне. Так будет легче понять задачу и предложить лучший вариант.

Спасибо за доверие 🙌"""


def make_admin_ai_note(data):
    prompt = f"""
Проанализируй заявку для разработчика Идриса.

Имя: {data["name"]}
Контакт: {data["contact"]}
Услуга: {data["service"]}
Описание проекта: {data["project"]}
Бюджет: {data["budget"]}
Срок: {data["deadline"]}

Сделай короткий анализ для админа:
1. Насколько заявка перспективная
2. Что клиенту, скорее всего, нужно
3. Какие вопросы задать клиенту
4. Какой ответ лучше отправить вручную
5. Сложность проекта: низкая / средняя / высокая
"""
    result = ai_request(prompt)

    if result:
        return result

    return "ИИ-анализ временно недоступен. Проверь заявку вручную."


def save_lead(chat_id, ai_answer, ai_admin_note):
    u = users[chat_id]
    date = datetime.now().strftime("%d.%m.%Y %H:%M")

    sql.execute("""
    INSERT INTO leads
    (user_id, username, name, contact, service, project, budget, deadline, ai_answer, ai_admin_note, status, date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        u.get("username", "none"),
        u["name"],
        u["contact"],
        u["service"],
        u["project"],
        u["budget"],
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
💡 <b>Проект:</b> {clean(row[6])}
💰 <b>Бюджет:</b> {clean(row[7])}
⏳ <b>Срок:</b> {clean(row[8])}
📌 <b>Статус:</b> {clean(row[11])}
🕒 <b>Дата:</b> {clean(row[12])}
🆔 <b>User ID:</b> {row[1]}

<b>🧠 Ответ ИИ клиенту:</b>
{clean(row[9])}

<b>📌 Анализ ИИ для тебя:</b>
{clean(row[10])}
"""


@bot.message_handler(commands=["start"])
def start(message):
    text = """
<b>Привет 👋</b>

Я — <b>Идрис</b>, разработчик Telegram-ботов, AI-ботов и простых сайтов для бизнеса.

Здесь ты можешь:
— посмотреть мои услуги
— увидеть примеры работ
— оставить заявку на проект
— получить быстрый ответ от AI-помощника

Если тебе нужен бот, сайт или автоматизация — нажми кнопку ниже 👇
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "⬅️ Главное меню")
def home(message):
    users.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "Главное меню 👇", reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "💼 Услуги")
def services(message):
    text = """
<b>💼 Мои услуги</b>

<b>🤖 Telegram-боты</b>
Боты для заявок, магазинов, записи, доставки, консультаций, обучения и автоматизации.

<b>🧠 AI-боты</b>
Боты с искусственным интеллектом: ответы клиентам, помощники, FAQ, консультации и обработка заявок.

<b>🌐 Сайты</b>
Лендинги, сайты-визитки, портфолио и простые сайты для бизнеса на HTML/CSS.

<b>🛠 Исправление ботов</b>
Исправление ошибок, запуск, Railway, GitHub, токены, базы данных и подключение ИИ.

<b>⚙️ Автоматизация</b>
Заявки, уведомления, базы данных, таблицы, админ-панель и удобные кнопки.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "🔥 Примеры работ")
def portfolio(message):
    text = """
<b>🔥 Мои проекты</b>

<b>1. AI Telegram Bot</b>
Бот как ChatGPT внутри Telegram. Пользователь задаёт вопрос, а бот отвечает через ИИ.

<b>2. UniHelper Bot</b>
Бот для помощи студентам с поступлением. Есть выбор языка, меню, инструкции, заявки и AI-помощник.

<b>3. Сайт-резюме</b>
Личный сайт-портфолио с услугами, проектами, опытом и контактами.

<b>4. LeadBot AI</b>
Бот для заявок. Принимает данные клиента, отвечает через ИИ и отправляет заявку администратору.

<b>5. Бот-магазин</b>
Каталог, корзина, оформление заказа и уведомление владельцу.

<b>6. Бот записи</b>
Выбор услуги, времени, контакта клиента и отправка записи администратору.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "👨‍💻 Обо мне")
def about(message):
    text = """
<b>👨‍💻 Обо мне</b>

Меня зовут <b>Идрис</b>.

Я занимаюсь разработкой Telegram-ботов и простых сайтов около <b>5 лет</b>.

Раньше я работал через:
— Kwork
— Upwork
— ProfiRU

Сейчас развиваю личное портфолио и принимаю заказы напрямую.

Мой подход:
— понять задачу клиента
— сделать удобную структуру
— написать понятные тексты
— создать рабочий проект
— помочь с запуском
— внести правки после сдачи

После завершения проекта могу бесплатно внести до <b>3 дополнительных изменений</b>. Мелкие исправления текста не считаются.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "❓ FAQ")
def faq(message):
    text = """
<b>❓ Частые вопросы</b>

<b>Сколько стоит бот?</b>
Цена зависит от функций. Простой бот стоит дешевле, бот с ИИ, базой данных и админ-панелью — дороже.

<b>Можно ли добавить ИИ?</b>
Да. Можно сделать AI-помощника, который отвечает клиентам внутри Telegram.

<b>Ты делаешь сайты?</b>
Да. Делаю лендинги, сайты-визитки и простые сайты на HTML/CSS.

<b>Ты помогаешь с запуском?</b>
Да. Могу помочь с GitHub, Railway, переменными, токенами и запуском проекта.

<b>Можно ли доработать старого бота?</b>
Да. Можно исправить ошибки или добавить новые функции.
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.chat.id))


@bot.message_handler(func=lambda m: m.text == "📩 Контакты")
def contacts(message):
    text = """
<b>📩 Контакты</b>

Чтобы заказать Telegram-бота, сайт или автоматизацию, нажми:

<b>🚀 Оставить заявку</b>

Бот задаст несколько вопросов, AI-помощник ответит тебе, а я получу заявку в Telegram.
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
        "Отлично 🚀\n\nКак тебя зовут?",
        reply_markup=back_menu()
    )


@bot.message_handler(func=lambda m: m.chat.id in users)
def lead_process(message):
    chat_id = message.chat.id

    if message.text == "⬅️ Главное меню":
        users.pop(chat_id, None)
        bot.send_message(chat_id, "Заявка отменена. Главное меню 👇", reply_markup=main_menu(chat_id))
        return

    step = users[chat_id]["step"]

    if step == "name":
        users[chat_id]["name"] = message.text
        users[chat_id]["step"] = "contact"
        bot.send_message(chat_id, "Оставь контакт для связи.\n\nНапример: Telegram username или номер телефона.")

    elif step == "contact":
        users[chat_id]["contact"] = message.text
        users[chat_id]["step"] = "service"
        bot.send_message(chat_id, "Что тебе нужно?", reply_markup=services_inline())

    elif step == "project":
        users[chat_id]["project"] = message.text
        users[chat_id]["step"] = "budget"
        bot.send_message(chat_id, "Какой примерно бюджет?", reply_markup=budget_inline())


@bot.callback_query_handler(func=lambda c: c.data.startswith("service|"))
def choose_service(call):
    chat_id = call.message.chat.id

    if chat_id not in users:
        bot.answer_callback_query(call.id, "Начни заявку заново")
        return

    service = call.data.split("|", 1)[1]
    users[chat_id]["service"] = service
    users[chat_id]["step"] = "project"

    bot.edit_message_text(
        f"Выбрано: <b>{clean(service)}</b> ✅",
        chat_id,
        call.message.message_id
    )

    bot.send_message(
        chat_id,
        "Опиши проект простыми словами.\n\nНапример: нужен бот для заявок, сайт для услуг, бот-магазин, AI-бот и т.д."
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("budget|"))
def choose_budget(call):
    chat_id = call.message.chat.id

    if chat_id not in users:
        bot.answer_callback_query(call.id, "Начни заявку заново")
        return

    budget = call.data.split("|", 1)[1]
    users[chat_id]["budget"] = budget
    users[chat_id]["step"] = "deadline"

    bot.edit_message_text(
        f"Бюджет: <b>{clean(budget)}</b> ✅",
        chat_id,
        call.message.message_id
    )

    bot.send_message(chat_id, "Когда нужно получить готовый проект?", reply_markup=deadline_inline())


@bot.callback_query_handler(func=lambda c: c.data.startswith("deadline|"))
def choose_deadline(call):
    chat_id = call.message.chat.id

    if chat_id not in users:
        bot.answer_callback_query(call.id, "Начни заявку заново")
        return

    deadline = call.data.split("|", 1)[1]
    users[chat_id]["deadline"] = deadline

    bot.edit_message_text(
        f"Срок: <b>{clean(deadline)}</b> ✅",
        chat_id,
        call.message.message_id
    )

    bot.send_message(chat_id, "Спасибо. AI-помощник обрабатывает заявку... 🧠")

    ai_answer = make_client_ai_answer(users[chat_id])
    ai_admin_note = make_admin_ai_note(users[chat_id])
    lead_id = save_lead(chat_id, ai_answer, ai_admin_note)

    sql.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    row = sql.fetchone()

    bot.send_message(chat_id, ai_answer, reply_markup=main_menu(chat_id))

    bot.send_message(
        ADMIN_ID,
        "🔥 <b>Новая заявка от клиента</b>\n" + lead_text(row),
        reply_markup=lead_actions(lead_id)
    )

    users.pop(chat_id, None)


@bot.message_handler(func=lambda m: m.text == "🔐 Админ-панель")
def admin(message):
    if message.chat.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "🔐 Админ-панель", reply_markup=admin_menu())


@bot.message_handler(func=lambda m: m.text in ["📋 Все заявки", "🔥 Новые заявки", "✅ В работе", "🏁 Завершённые"])
def show_leads(message):
    if message.chat.id != ADMIN_ID:
        return

    if message.text == "📋 Все заявки":
        sql.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 10")
    elif message.text == "🔥 Новые заявки":
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

Всего заявок: <b>{total}</b>

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

    bot.answer_callback_query(call.id, f"Статус изменён: {status}")


@bot.message_handler(content_types=["text"])
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Выбери действие через кнопки 👇",
        reply_markup=main_menu(message.chat.id)
    )


print("Idris LeadBot AI started")
bot.infinity_polling(skip_pending=True)
