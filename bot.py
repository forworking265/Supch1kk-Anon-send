import os
from aiohttp import web
import asyncio
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------- НАСТРОЙКИ -----------------
BOT_TOKEN = "8700903890:AAH6dRxs0CchS7Cwfn_zL7CdX4RRXOTxAGk"  # Вставь сюда токен от BotFather
MY_ADMIN_ID = 5275055062              # Твой личный Telegram ID
OWNER_SECRET_PASS = "supchik123"      # Пароль для авторизации Владельца через /signin

ADMIN_LIST_TEXT = "@Alexandrr838, @admin2- Кто же это будет?? (надеюсь никто..))"

# Расширенный список банвордов
BAD_WORDS = [
    "уебище", "уродина", "кривлялка", "нищебродка", "нищета", "гнодина",
    "сучара", "сука", "жирная", "жиробасина", "скотина", "свинья",
    "свиноматочка", "скотомогильник", "прыщавая", "вскрой", "вскройся",
    "покончи с собой", "сонную артерию", "ебало снесу", "вычислим",
    "шлюха", "пидорасина", "мамка", "мать", "Джеймс",
    "разоблачение",
    "тупая",
    "дура",
    "курица",
    "лмао",
    "конченная",
    "подсосы",
    "подсоски",
    "слилась",
    "проблемы",
    "доказательства",
    "пруфы", "жир", "жировые складки"
]

BAN_TIME_SECONDS = 86400  # Автобаны при 3 варнах: 24 часа
# ----------------------------------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AnonymState(StatesGroup):
    waiting_for_message = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            warnings INTEGER DEFAULT 0,
            blocked_until INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reply_links (
            chat_id INTEGER,
            message_id INTEGER,
            sender_id INTEGER,
            PRIMARY KEY (chat_id, message_id)
        )
    """)
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT warnings, blocked_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, warnings, blocked_until) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        row = (0, 0)
    conn.close()
    return row

def update_user_warnings(user_id, warnings, blocked_until=0):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET warnings = ?, blocked_until = ? WHERE user_id = ?", (warnings, blocked_until, user_id))
    conn.commit()
    conn.close()

def set_owner_id(owner_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('owner_id', ?)", (owner_id,))
    conn.commit()
    conn.close()

def get_owner_id():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'owner_id'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_reply_link(chat_id, message_id, sender_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO reply_links (chat_id, message_id, sender_id) VALUES (?, ?, ?)", (chat_id, message_id, sender_id))
    conn.commit()
    conn.close()

def get_sender_by_reply(chat_id, message_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sender_id FROM reply_links WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def contains_bad_words(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(bad_word in text_lower for bad_word in BAD_WORDS)


# --- ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Доброго времени суток.\n"
        "С вами анонимный чат-бот супчика!\n\n"
        "В этом чате нужно писать сообщения супчику.\n"
        "Негативные сообщения НЕ принимаются (цензура бота).\n\n"
        "Поскорее пиши свое смс, используя команду /writeananonsms 🤗"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Приветик!\n"
        "Это анонимный чат-бот супчика!\n\n"
        "Желаешь написать сообщение? Убедительная просьба, соблюдайте правила бота:\n"
        "______________________\n\n"
        "⛔️ В БОТЕ ПРИСУТСТВУЕТ ЦЕНЗУРА!\n"
        "• За написание нецензурных комментариев (травля, нагота, клевета) выдается 3 ВАРНА!\n"
        "• Если вы получаете 3 варна, вас банит бот.\n\n"
        "🤖 ВЫБИВАЕТ ОШИБКУ ИЛИ НЕ ОТПРАВЛЯЕТСЯ СООБЩЕНИЕ?\n"
        "• Попробуйте отправить повторно, либо перезагрузите Телеграм.\n"
        "• Если не помогает, повторите попытку позже.\n\n"
        "🤔 ЧТО ПРОИСХОДИТ С СООБЩЕНИЕМ ПОСЛЕ ЕГО ОТПРАВКИ?\n"
        "• Ваше сообщение отправляется прямиком в чат к супчику и публикуется в тгк.\n"
        "• В самом сообщении вашего юзернейма/номера НЕ будет видно. Все абсолютно конфиденциально.\n\n"
        "На этом все, пользуйтесь этим ботом и соблюдайте правила его использования! 🙂"
    )

@dp.message(Command("writeananonsms"))
async def cmd_write_anon(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    warnings, blocked_until = get_user_data(user_id)
    now = int(time.time())

    if blocked_until > now:
        remaining_minutes = (blocked_until - now) // 60
        await message.answer(f"⛔️ Вы заблокированы за нарушение правил. Осталось: {remaining_minutes} мин.")
        return

    await state.set_state(AnonymState.waiting_for_message)
    await message.answer("Жду твоего сообщения! Постараюсь как можно скорее прочитать и ответить!\n\nИ помни про цензуру!🙂")

@dp.message(Command("signin"))
async def cmd_signin(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Введите команду с паролем: `/signin ваш_пароль`", parse_mode="Markdown")
        return

    if args[1] == OWNER_SECRET_PASS:
        set_owner_id(message.from_user.id)
        await message.answer(
            "Ну наконец-то владелец пришел! 🥱\n"
            "Мы тебя ждали.\n"
            f"Список админов: {ADMIN_LIST_TEXT}\n\n"
            "💡 Чтобы ответить анониму, просто используй функцию 'Ответить' (Reply) на пришедшее сообщение!"
        )
    else:
        await message.answer("❌ Неверный пароль!")


# --- АДМИН-ПАНЕЛЬ И БЛОКИРОВКА ---

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    owner_id = get_owner_id()
    
    if user_id != MY_ADMIN_ID and user_id != owner_id:
        await message.answer(f"❌ Доступ запрещен! Ваш ID: `{user_id}`", parse_mode="Markdown")
        return

    owner_status = f"Подключен (`{owner_id}`)" if owner_id else "❌ Не авторизован"
    
    await message.answer(
        f"⚙️ **Панель Главного Админа**\n\n"
        f"Статус Владельца: {owner_status}\n"
        f"Загруженные стоп-слова: {len(BAD_WORDS)} шт.\n\n"
        f"✅ **Вы верифицированы как Админ!**",
        parse_mode="Markdown"
    )


@dp.message(Command("ban"))
async def cmd_ban_user(message: types.Message):
    owner_id = get_owner_id()
    if message.from_user.id != MY_ADMIN_ID and message.from_user.id != owner_id:
        return

    if not message.reply_to_message:
        await message.answer("⚠️ Ответьте этой командой (/ban) на анонимное сообщение, чтобы забанить на 24 часа!")
        return

    target_sender_id = get_sender_by_reply(message.chat.id, message.reply_to_message.message_id)
    if not target_sender_id:
        await message.answer("❌ Не удалось найти автора этого сообщения в базе.")
        return

    ban_until = int(time.time()) + 86400  # 24 часа
    update_user_warnings(target_sender_id, 3, ban_until)

    await message.answer(f"⏳ Пользователь (ID: `{target_sender_id}`) заблокирован на **24 часа**!", parse_mode="Markdown")
    
    try:
        await bot.send_message(target_sender_id, "⛔️ Вы были временно заблокированы администратором на 24 часа.")
    except Exception:
        pass


@dp.message(Command("banforever"))
async def cmd_ban_forever(message: types.Message):
    owner_id = get_owner_id()
    if message.from_user.id != MY_ADMIN_ID and message.from_user.id != owner_id:
        return

    if not message.reply_to_message:
        await message.answer("⚠️ Ответьте этой командой (/banforever) на анонимное сообщение, чтобы забанить навсегда!")
        return

    target_sender_id = get_sender_by_reply(message.chat.id, message.reply_to_message.message_id)
    if not target_sender_id:
        await message.answer("❌ Не удалось найти автора этого сообщения в базе.")
        return

    far_future = int(time.time()) + (86400 * 365 * 100)  # Пермабан на 100 лет
    update_user_warnings(target_sender_id, 3, far_future)

    await message.answer(f"🚫 Пользователь (ID: `{target_sender_id}`) заблокирован **навсегда**!", parse_mode="Markdown")
    
    try:
        await bot.send_message(target_sender_id, "⛔️ Вы были заблокированы администратором навсегда.")
    except Exception:
        pass


# --- ОБРАБОТКА И ПЕРЕСЫЛКА АНОНИМНЫХ СООБЩЕНИЙ ---

async def handle_anon_sending(message: types.Message, user_id: int):
    warnings, blocked_until = get_user_data(user_id)
    now = int(time.time())

    if blocked_until > now:
        await message.answer("⛔️ Вы заблокированы.")
        return

    is_bad = contains_bad_words(message.text)
    owner_id = get_owner_id()

    # 1. Лог Админу
    bad_flag = "🚨 [БЛОКИРОВКА ЦЕНЗУРОЙ]" if is_bad else "✅ [ПРОШЛО ФИЛЬТР]"
    if MY_ADMIN_ID:
        try:
            admin_msg = await bot.send_message(
                chat_id=MY_ADMIN_ID,
                text=f"🕵️‍♂️ **Лог Цензуры** {bad_flag}\n**От ID:** `{user_id}`\n**Текст:** {message.text}\n\n_(Ответьте на сообщение командой /ban, /banforever или текстом ответа)_",
                parse_mode="Markdown"
            )
            save_reply_link(MY_ADMIN_ID, admin_msg.message_id, user_id)
        except Exception as e:
            print(f"Ошибка отправки лога админу: {e}")

    # 2. Обработка нарушений
    if is_bad:
        warnings += 1
        if warnings >= 3:
            unban_time = now + BAN_TIME_SECONDS
            update_user_warnings(user_id, 0, unban_time)
            await message.answer("⛔️ Вы получили 3/3 предупреждений и заблокированы на 24 часа!")
        else:
            update_user_warnings(user_id, warnings, 0)
            await message.answer(f"⚠️ Сообщение содержит цензуру! Предупреждение {warnings}/3.")
        return

    # 3. Отправка Владельцу
    if owner_id:
        try:
            owner_msg = await bot.send_message(
                chat_id=owner_id,
                text=f"📥 **Новое анонимное сообщение:**\n\n{message.text}\n\n_(Ответьте на это сообщение, чтобы вступить в диалог)_",
                parse_mode="Markdown"
            )
            # Сохраняем связку ID сообщения владельца -> ID анонима
            save_reply_link(owner_id, owner_msg.message_id, user_id)
        except Exception:
            pass

    await message.answer("✅ Ваше сообщение успешно отправлено анонимно!")


@dp.message(AnonymState.waiting_for_message)
async def process_anon_message_state(message: types.Message, state: FSMContext):
    await handle_anon_sending(message, message.from_user.id)
    await state.clear()


# --- ОБРАБОТКА ОТВЕТОВ (REPLY) И ПРОДОЛЖЕНИЯ ДИАЛОГА ---

@dp.message(F.reply_to_message)
async def handle_replies(message: types.Message):
    sender_id = message.from_user.id
    owner_id = get_owner_id()

    # 1. Если отвечает Админ или Владелец
    if sender_id == MY_ADMIN_ID or sender_id == owner_id:
        target_user_id = get_sender_by_reply(message.chat.id, message.reply_to_message.message_id)
        if not target_user_id:
            await message.answer("❌ Не удалось отправить ответ: сообщение слишком старое или автору нельзя ответить.")
            return

        role_title = "👑 Владельца" if sender_id == owner_id else "🛡 Модератора"

        try:
            sent_msg = await bot.send_message(
                chat_id=target_user_id,
                text=f"💬 **Ответ от {role_title}:**\n\n{message.text}\n\n_(Просто ответьте на это сообщение, чтобы продолжить диалог)_",
                parse_mode="Markdown"
            )
            # Запоминаем ID сообщения, доставленного анониму, чтобы он мог ответить через Reply
            save_reply_link(target_user_id, sent_msg.message_id, sender_id)
            await message.answer("✅ Ваш ответ успешно доставлен анониму!")
        except Exception:
            await message.answer("❌ Не удалось доставить сообщение (возможно, пользователь заблокировал бота).")
        return

    # 2. Если аноним отвечает через «Ответить» (Reply) на сообщение Владельца/Админа
    target_recipient_id = get_sender_by_reply(message.chat.id, message.reply_to_message.message_id)
    if target_recipient_id:
        await handle_anon_sending(message, sender_id)


# --- АВТОМАТИЧЕСКАЯ ПЕРЕСЫЛКА ОБЫЧНЫХ СООБЩЕНИЙ ---

@dp.message(~F.text.startswith("/"))
async def handle_plain_text(message: types.Message):
    sender_id = message.from_user.id
    owner_id = get_owner_id()

    # Игнорируем обычный текст от админа и владельца (им нужен Reply)
    if sender_id == MY_ADMIN_ID or sender_id == owner_id:
        return

    # Пересылаем обычные сообщения пользователей владельцу
    await handle_anon_sending(message, sender_id)


async def handle_ping(request):
    return web.Response(text="OK")

async def main():
    init_db()
    
    # Запускаем фоновый веб-сервер для прохождения проверки порта на Render
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Запуск Telegram-бота
    await dp.start_polling(bot)