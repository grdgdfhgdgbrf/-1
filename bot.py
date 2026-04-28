import asyncio
import logging
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Для работы с аккаунтами Telegram
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# API ID и API Hash для Telethon (нужны для работы с аккаунтами)
# Получить можно на my.telegram.org, но для работы без него используем альтернативный метод
API_ID = 24387534  # Стандартный ID для тестирования
API_HASH = "cde7f7a2b2c0a652f5e6d9a8b7c6d5e4"

# Состояния для ConversationHandler
PHONE, CODE, PASSWORD = range(3)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Таблица аккаунтов
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (user_id INTEGER PRIMARY KEY,
                  phone TEXT,
                  session_string TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  username TEXT,
                  added_date TIMESTAMP,
                  status TEXT DEFAULT 'active')''')
    
    # Таблица каналов для постинга
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  channel_title TEXT,
                  channel_username TEXT,
                  added_date TIMESTAMP,
                  status TEXT DEFAULT 'active',
                  FOREIGN KEY (user_id) REFERENCES accounts (user_id))''')
    
    # Таблица тарифов
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY,
                  tariff TEXT DEFAULT 'free',
                  start_date TIMESTAMP,
                  end_date TIMESTAMP,
                  max_channels INTEGER DEFAULT 1,
                  repost_limit INTEGER DEFAULT 10,
                  post_interval INTEGER DEFAULT 3600,
                  FOREIGN KEY (user_id) REFERENCES accounts (user_id))''')
    
    # Таблица источников для репостов
    c.execute('''CREATE TABLE IF NOT EXISTS sources
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  source_channel_id TEXT,
                  source_channel_title TEXT,
                  target_channel_id TEXT,
                  is_active INTEGER DEFAULT 1,
                  added_date TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES accounts (user_id))''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  content TEXT,
                  media_file_id TEXT,
                  post_type TEXT,
                  scheduled_time TIMESTAMP,
                  posted_time TIMESTAMP,
                  status TEXT DEFAULT 'pending',
                  FOREIGN KEY (user_id) REFERENCES accounts (user_id))''')
    
    # Таблица настроек автопостинга
    c.execute('''CREATE TABLE IF NOT EXISTS auto_posting_settings
                 (channel_id TEXT PRIMARY KEY,
                  user_id INTEGER,
                  is_auto_active INTEGER DEFAULT 0,
                  auto_topic TEXT,
                  post_frequency INTEGER DEFAULT 3600,
                  last_post_time TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES accounts (user_id))''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "price": "0 ₽",
        "max_channels": 1,
        "repost_limit": 10,
        "post_interval": 3600,
        "features": [
            "✅ 1 канал для постинга",
            "✅ 10 репостов в день",
            "✅ Интервал 1 час",
            "✅ Ручной постинг",
            "✅ Базовые темы"
        ]
    },
    "basic": {
        "name": "📘 Базовый",
        "price": "0 ₽ (Бесплатно)",
        "max_channels": 3,
        "repost_limit": 50,
        "post_interval": 1800,
        "features": [
            "✅ До 3 каналов",
            "✅ 50 репостов в день",
            "✅ Интервал 30 минут",
            "✅ Автопостинг",
            "✅ 5 тем для контента",
            "✅ Репосты из источников"
        ]
    },
    "pro": {
        "name": "💎 PRO",
        "price": "0 ₽ (Бесплатно)",
        "max_channels": 10,
        "repost_limit": 200,
        "post_interval": 600,
        "features": [
            "✅ До 10 каналов",
            "✅ 200 репостов в день",
            "✅ Интервал 10 минут",
            "✅ ИИ генерация контента",
            "✅ 15+ тем",
            "✅ Авторепосты 24/7",
            "✅ Приоритетная обработка"
        ]
    }
}

# ==================== ТЕМЫ ДЛЯ КОНТЕНТА ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии",
        "keywords": ["IT", "программирование", "гаджеты", "AI", "роботы", "инновации"],
        "prompt": "Ты эксперт в области технологий. Пиши посты о новых технологиях, гаджетах, IT-трендах."
    },
    "business": {
        "name": "📊 Бизнес",
        "keywords": ["бизнес", "стартап", "маркетинг", "управление", "финансы"],
        "prompt": "Ты бизнес-эксперт. Делишься советами по бизнесу, маркетингу, управлению."
    },
    "health": {
        "name": "⚕️ Здоровье",
        "keywords": ["здоровье", "фитнес", "питание", "спорт", "wellness"],
        "prompt": "Ты эксперт по здоровью. Даешь советы по ЗОЖ, фитнесу, правильному питанию."
    },
    "education": {
        "name": "📚 Образование",
        "keywords": ["образование", "обучение", "курсы", "навыки", "саморазвитие"],
        "prompt": "Ты педагог. Делишься образовательным контентом, советами по обучению."
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "keywords": ["кино", "музыка", "игры", "юмор", "мемы"],
        "prompt": "Ты создатель развлекательного контента. Пишешь веселые и интересные посты."
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "keywords": ["лайфхак", "советы", "жизнь", "мотивация", "вдохновение"],
        "prompt": "Ты вдохновитель. Делишься полезными советами, идеями для жизни."
    }
}

# ==================== ХРАНИЛИЩЕ СЕССИЙ ====================
class PostingBot:
    def __init__(self):
        self.user_sessions = {}  # Временные сессии для авторизации
        self.bot_clients = {}  # Активные клиенты Telethon для пользователей
        self.posting_tasks = {}  # Задачи автопостинга
        
    def get_db_connection(self):
        return sqlite3.connect('posting_bot.db')
    
    async def get_user_client(self, user_id: int) -> Optional[TelegramClient]:
        """Получить или создать клиента для пользователя"""
        if user_id in self.bot_clients:
            return self.bot_clients[user_id]
        
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT session_string FROM accounts WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            try:
                client = TelegramClient(StringSession(result[0]), API_ID, API_HASH)
                await client.start()
                self.bot_clients[user_id] = client
                return client
            except Exception as e:
                logger.error(f"Ошибка подключения: {e}")
                return None
        return None
    
    async def send_post_to_channel(self, user_id: int, channel_id: str, message: str, media=None):
        """Отправить пост в канал"""
        client = await self.get_user_client(user_id)
        if not client:
            return False, "❌ Аккаунт не подключен"
        
        try:
            if media:
                await client.send_file(int(channel_id), media, caption=message)
            else:
                await client.send_message(int(channel_id), message)
            
            # Сохраняем пост в БД
            conn = self.get_db_connection()
            c = conn.cursor()
            c.execute("""INSERT INTO posts (user_id, channel_id, content, post_type, posted_time, status) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                      (user_id, channel_id, message, "manual", datetime.now(), "posted"))
            conn.commit()
            conn.close()
            
            return True, "✅ Пост успешно опубликован!"
        except Exception as e:
            return False, f"❌ Ошибка: {str(e)}"

bot_manager = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    """Главная клавиатура"""
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    
    # Проверяем подписку
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user_id,))
    sub = c.fetchone()
    tariff = sub[0] if sub else "free"
    
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🔄 Репосты", callback_data="reposts_menu")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

async def get_tariff_keyboard():
    """Клавиатура с тарифами"""
    keyboard = []
    for tariff_key, tariff_info in TARIFFS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff_info['name']} - {tariff_info['price']}", 
                callback_data=f"select_tariff_{tariff_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    """Клавиатура со списком каналов"""
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status = 'active'", (user_id,))
    channels = c.fetchall()
    conn.close()
    
    keyboard = []
    for channel_id, channel_title in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel_title}", callback_data=f"channel_{channel_id}")
        ])
    
    if not channels:
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_posting_keyboard(channel_id: str, is_active: bool):
    """Клавиатура настроек автопостинга"""
    status_text = "✅ Активен" if is_active else "❌ Неактивен"
    keyboard = [
        [InlineKeyboardButton(f"🔄 Статус: {status_text}", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("⏱ Частота постинга", callback_data=f"frequency_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str):
    """Клавиатура выбора темы"""
    keyboard = []
    for topic_key, topic_info in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{topic_info['name']}", 
                callback_data=f"set_topic_{channel_id}_{topic_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Создаем подписку если нет
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscriptions (user_id, tariff, start_date, max_channels) VALUES (?, 'free', ?, 1)",
              (user.id, datetime.now()))
    conn.commit()
    conn.close()
    
    welcome_text = (
        f"✨ *Добро пожаловать, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автоматического постинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Писать посты в каналы\n"
        f"• 🔄 Делать репосты из других каналов\n"
        f"• ⚙️ Настраивать автопостинг\n"
        f"• 💎 Подключать неограниченное количество аккаунтов\n\n"
        f"🚀 *Для начала работы:*\n"
        f"1️⃣ Подключите аккаунт Telegram\n"
        f"2️⃣ Добавьте каналы для постинга\n"
        f"3️⃣ Начните публиковать контент!\n\n"
        f"💡 *Используйте кнопки меню для управления*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подключение аккаунта через телефон"""
    user = update.effective_user
    
    # Проверяем есть ли уже аккаунт
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT phone FROM accounts WHERE user_id = ?", (user.id,))
    existing = c.fetchone()
    conn.close()
    
    if existing:
        await update.message.reply_text(
            "ℹ️ У вас уже подключен аккаунт!\n"
            f"📱 Телефон: {existing[0]}\n\n"
            "Чтобы подключить новый, сначала отвяжите текущий."
        )
        return
    
    context.user_data['auth_step'] = 'phone'
    await update.message.reply_text(
        "📱 *Подключение аккаунта Telegram*\n\n"
        "Введите номер телефона в международном формате:\n"
        "Пример: `+79123456789`\n\n"
        "⚠️ *Важно:* На этот номер придет код подтверждения",
        parse_mode='Markdown'
    )
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    user = update.effective_user
    phone = update.message.text.strip()
    
    # Создаем временный клиент
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    try:
        # Отправляем запрос на код
        await client.send_code_request(phone)
        context.user_data['temp_client'] = client
        context.user_data['phone'] = phone
        
        await update.message.reply_text(
            "📨 *Код подтверждения отправлен!*\n\n"
            "Проверьте Telegram на указанном номере\n"
            "и введите код из сообщения:\n\n"
            "Пример: `12345`",
            parse_mode='Markdown'
        )
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз /start")
        return ConversationHandler.END

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода подтверждения"""
    user = update.effective_user
    code = update.message.text.strip()
    
    client = context.user_data.get('temp_client')
    phone = context.user_data.get('phone')
    
    if not client:
        await update.message.reply_text("❌ Сессия истекла. Начните заново /start")
        return ConversationHandler.END
    
    try:
        # Вход с кодом
        await client.sign_in(phone, code)
        
        # Получаем информацию об аккаунте
        me = await client.get_me()
        session_string = client.session.save()
        
        # Сохраняем в БД
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO accounts (user_id, phone, session_string, first_name, last_name, username, added_date) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (user.id, phone, session_string, me.first_name, me.last_name or "", me.username or "", datetime.now()))
        conn.commit()
        conn.close()
        
        await client.disconnect()
        
        await update.message.reply_text(
            "✅ *Аккаунт успешно подключен!*\n\n"
            f"👤 Имя: {me.first_name}\n"
            f"📱 Телефон: {phone}\n"
            f"🔗 Username: @{me.username if me.username else 'нет'}\n\n"
            "Теперь вы можете добавлять каналы и писать посты!",
            parse_mode='Markdown'
        )
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз /start")
        return ConversationHandler.END

async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена авторизации"""
    await update.message.reply_text("❌ Авторизация отменена")
    return ConversationHandler.END

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление канала"""
    user = update.effective_user
    
    # Проверяем лимит каналов по тарифу
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tariff, max_channels FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    tariff = sub[0] if sub else "free"
    max_channels = TARIFFS[tariff]["max_channels"]
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    current_count = c.fetchone()[0]
    conn.close()
    
    if current_count >= max_channels:
        await update.callback_query.edit_message_text(
            f"❌ Достигнут лимит каналов для вашего тарифа ({tariff})\n"
            f"Максимум: {max_channels} каналов\n"
            f"Чтобы добавить больше, перейдите на другой тариф /tariffs"
        )
        return
    
    await update.callback_query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "Для добавления канала:\n"
        "1. Добавьте бота в канал как администратора\n"
        "2. Отправьте ссылку на канал или его ID\n\n"
        "Примеры:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n"
        "• `-1001234567890`\n\n"
        "⚠️ Бот должен быть администратором канала!",
        parse_mode='Markdown'
    )
    
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    # Извлекаем ID канала
    channel_id = channel_input
    if "t.me/" in channel_input:
        channel_id = channel_input.split("t.me/")[-1]
    
    client = await bot_manager.get_user_client(user.id)
    if not client:
        await update.message.reply_text("❌ Аккаунт не подключен. Используйте /connect")
        return
    
    try:
        # Получаем информацию о канале
        entity = await client.get_entity(channel_id)
        
        # Проверяем, является ли пользователь администратором
        if hasattr(entity, 'megagroup') and entity.megagroup:
            # Это группа
            await update.message.reply_text("❌ Это группа, а не канал. Бот работает только с каналами.")
            return
        
        # Сохраняем канал
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO channels (user_id, channel_id, channel_title, channel_username, added_date) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (user.id, str(entity.id), entity.title, entity.username or "", datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 Название: {entity.title}\n"
            f"🔗 ID: {entity.id}\n\n"
            f"Теперь вы можете публиковать посты в этот канал!",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_channel'] = False
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\n\n"
                                       f"Убедитесь что:\n"
                                       f"• Бот добавлен в канал как администратор\n"
                                       f"• Аккаунт имеет права на управление каналом\n"
                                       f"• Ссылка на канал введена верно")

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Написать пост"""
    # Получаем список каналов пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", 
              (update.effective_user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await update.callback_query.edit_message_text(
            "❌ У вас нет добавленных каналов!\n"
            "Сначала добавьте канал через меню 'Мои каналы' ➕"
        )
        return
    
    keyboard = []
    for channel_id, channel_title in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel_title}", callback_data=f"select_channel_{channel_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.callback_query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['selecting_channel'] = True

async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация поста в канал"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_channel_", "")
    context.user_data['post_channel_id'] = channel_id
    
    # Получаем информацию о канале
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_title FROM channels WHERE channel_id = ?", (channel_id,))
    channel_title = c.fetchone()[0]
    conn.close()
    
    await query.edit_message_text(
        f"📝 *Напишите пост для канала* `{channel_title}`\n\n"
        f"Вы можете отправить:\n"
        f"• Текст сообщения\n"
        f"• Фото/видео с подписью\n"
        f"• Документ\n\n"
        f"Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_post'] = True

async def handle_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка контента для поста"""
    user = update.effective_user
    channel_id = context.user_data.get('post_channel_id')
    
    if not channel_id:
        await update.message.reply_text("❌ Сессия истекла. Начните заново /start")
        return
    
    # Определяем тип контента
    media = None
    caption = update.message.caption or update.message.text
    
    if update.message.photo:
        media = await update.message.photo[-1].get_file()
        media = await media.download_as_bytearray()
    elif update.message.video:
        media = await update.message.video.get_file()
        media = await media.download_as_bytearray()
    elif update.message.document:
        media = await update.message.document.get_file()
        media = await media.download_as_bytearray()
    elif update.message.text:
        caption = update.message.text
    else:
        await update.message.reply_text("❌ Неподдерживаемый тип сообщения")
        return
    
    # Отправляем пост
    success, message = await bot_manager.send_post_to_channel(user.id, channel_id, caption, media)
    
    await update.message.reply_text(message)
    
    if success:
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
    
    context.user_data['awaiting_post'] = False
    context.user_data['post_channel_id'] = None

async def setup_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка автопостинга"""
    user = update.effective_user
    
    # Получаем список каналов
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await update.callback_query.edit_message_text(
            "❌ У вас нет добавленных каналов!\n"
            "Сначала добавьте канал для автопостинга"
        )
        return
    
    keyboard = []
    for channel_id, channel_title in channels:
        # Проверяем активен ли автопостинг
        conn2 = bot_manager.get_db_connection()
        c2 = conn2.cursor()
        c2.execute("SELECT is_auto_active FROM auto_posting_settings WHERE channel_id = ?", (channel_id,))
        result = c2.fetchone()
        conn2.close()
        
        status = "✅" if result and result[0] else "❌"
        keyboard.append([
            InlineKeyboardButton(f"{status} {channel_title}", callback_data=f"auto_channel_{channel_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.callback_query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "Выберите канал для настройки:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_repost_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление источника для репостов"""
    user = update.effective_user
    
    # Получаем каналы пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await update.callback_query.edit_message_text(
            "❌ У вас нет каналов для репостов!\n"
            "Сначала добавьте канал"
        )
        return
    
    keyboard = []
    for channel_id, channel_title in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel_title}", callback_data=f"source_target_{channel_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.callback_query.edit_message_text(
        "🔄 *Добавление источника для репостов*\n\n"
        "Выберите целевой канал (куда будут публиковаться репосты):",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['selecting_source_target'] = True

async def process_repost_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора целевого канала для репостов"""
    query = update.callback_query
    await query.answer()
    
    target_channel = query.data.replace("source_target_", "")
    context.user_data['repost_target'] = target_channel
    
    await query.edit_message_text(
        "📢 *Теперь укажите источник для репостов*\n\n"
        "Отправьте ссылку или ID канала/чата, откуда будут браться посты:\n\n"
        "Примеры:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "⚠️ Аккаунт должен иметь доступ к этому каналу",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_source'] = True

async def save_repost_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение источника репостов"""
    user = update.effective_user
    source_input = update.message.text.strip()
    target_channel = context.user_data.get('repost_target')
    
    if not target_channel:
        await update.message.reply_text("❌ Сессия истекла. Начните заново")
        return
    
    client = await bot_manager.get_user_client(user.id)
    if not client:
        await update.message.reply_text("❌ Аккаунт не подключен")
        return
    
    try:
        # Получаем информацию об источнике
        source_entity = await client.get_entity(source_input)
        
        # Сохраняем в БД
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO sources (user_id, source_channel_id, source_channel_title, target_channel_id, added_date) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (user.id, str(source_entity.id), source_entity.title, target_channel, datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Источник репостов добавлен!*\n\n"
            f"📢 Источник: {source_entity.title}\n"
            f"🎯 Целевой канал: {target_channel}\n\n"
            f"Теперь можно настроить автоматические репосты",
            parse_mode='Markdown'
        )
        
        context.user_data['selecting_source_target'] = False
        context.user_data['awaiting_source'] = False
        
        # Показываем меню репостов
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Настроить авторепосты", callback_data="auto_reposts")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")]
        ])
        await update.message.reply_text("Что дальше?", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    user = update.effective_user
    
    # Получаем текущий тариф пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    current = c.fetchone()
    current_tariff = current[0] if current else "free"
    conn.close()
    
    text = "💎 *Доступные тарифы*\n\n"
    
    for tariff_key, tariff_info in TARIFFS.items():
        is_current = "✅ *Текущий* " if tariff_key == current_tariff else ""
        text += f"{is_current}{tariff_info['name']}\n"
        text += f"💰 {tariff_info['price']}\n"
        text += "📋 Возможности:\n"
        for feature in tariff_info['features']:
            text += f"{feature}\n"
        text += "\n"
    
    keyboard = await get_tariff_keyboard()
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор тарифа"""
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    if tariff_key in TARIFFS:
        # Обновляем тариф
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        c.execute("""UPDATE subscriptions 
                     SET tariff = ?, start_date = ?, end_date = ?, max_channels = ?
                     WHERE user_id = ?""",
                  (tariff_key, datetime.now(), datetime.now() + timedelta(days=30), 
                   TARIFFS[tariff_key]["max_channels"], user_id))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            f"✅ *Тариф обновлен!*\n\n"
            f"Ваш новый тариф: {TARIFFS[tariff_key]['name']}\n"
            f"Действует до: {(datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')}\n\n"
            f"Теперь вам доступны новые возможности!",
            parse_mode='Markdown'
        )
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user_id)
        await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    user = update.effective_user
    
    conn = bot_manager.get_db_connection()
    
    # Информация об аккаунте
    c = conn.cursor()
    c.execute("SELECT phone, first_name, added_date FROM accounts WHERE user_id = ?", (user.id,))
    account = c.fetchone()
    
    # Информация о подписке
    c.execute("SELECT tariff, start_date, end_date FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    
    # Статистика
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM sources WHERE user_id = ?", (user.id,))
    sources_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND status='posted'", (user.id,))
    posts_count = c.fetchone()[0]
    
    conn.close()
    
    tariff = sub[0] if sub else "free"
    tariff_info = TARIFFS[tariff]
    
    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"📱 Аккаунт: {'✅ Подключен' if account else '❌ Не подключен'}\n"
        f"💎 Тариф: {tariff_info['name']}\n"
        f"📊 Статистика:\n"
        f"• Каналов: {channels_count}/{tariff_info['max_channels']}\n"
        f"• Источников: {sources_count}\n"
        f"• Постов: {posts_count}\n\n"
        f"📅 Подписка до: {sub[2] if sub else 'Не активна'}\n\n"
        f"🔄 Подключите аккаунт для начала работы!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Подключить аккаунт", callback_data="connect_account")],
        [InlineKeyboardButton("💎 Сменить тариф", callback_data="tariffs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await update.callback_query.edit_message_text(profile_text, parse_mode='Markdown', reply_markup=keyboard)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    user = update.effective_user
    
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    
    # Посты за день/неделю/месяц
    today = datetime.now().date()
    week_ago = datetime.now() - timedelta(days=7)
    month_ago = datetime.now() - timedelta(days=30)
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND DATE(posted_time) = ?", 
              (user.id, today))
    posts_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND posted_time >= ?", 
              (user.id, week_ago))
    posts_week = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND posted_time >= ?", 
              (user.id, month_ago))
    posts_month = c.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 Посты:\n"
        f"• Сегодня: {posts_today}\n"
        f"• За неделю: {posts_week}\n"
        f"• За месяц: {posts_month}\n\n"
        f"🎯 *Совет:* Чем больше качественных постов, тем быстрее растет канал!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Подробная статистика", callback_data="detailed_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await update.callback_query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

# ==================== ОБРАБОТЧИК CALLBACK ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик callback запросов"""
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    
    elif data == "write_post":
        await write_post(update, context)
    
    elif data == "my_channels":
        keyboard = await get_channels_keyboard(query.from_user.id)
        await query.edit_message_text("📢 *Мои каналы*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_channel":
        await add_channel(update, context)
    
    elif data == "reposts_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить источник", callback_data="add_source")],
            [InlineKeyboardButton("🔄 Настроить репосты", callback_data="setup_reposts")],
            [InlineKeyboardButton("📋 Мои источники", callback_data="my_sources")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
        ])
        await query.edit_message_text("🔄 *Меню репостов*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_source":
        await add_repost_source(update, context)
    
    elif data == "auto_posting":
        await setup_auto_posting(update, context)
    
    elif data == "tariffs":
        await show_tariffs(update, context)
    
    elif data == "profile":
        await show_profile(update, context)
    
    elif data == "stats":
        await show_stats(update, context)
    
    elif data == "help":
        help_text = (
            "ℹ️ *Помощь*\n\n"
            "📋 *Как пользоваться ботом:*\n\n"
            "1️⃣ *Подключите аккаунт*\n"
            "Нажмите 'Профиль' ➡️ 'Подключить аккаунт'\n\n"
            "2️⃣ *Добавьте канал*\n"
            "Добавьте бота в канал как администратора\n"
            "В меню 'Мои каналы' ➕ 'Добавить канал'\n\n"
            "3️⃣ *Публикуйте контент*\n"
            "'Написать пост' ➡️ выберите канал ➡️ отправьте сообщение\n\n"
            "4️⃣ *Настройте автопостинг*\n"
            "В меню 'Автопостинг' выберите канал и тему\n\n"
            "5️⃣ *Делайте репосты*\n"
            "В меню 'Репосты' добавьте источники\n\n"
            "💡 *Советы:*\n"
            "• Используйте разные темы для контента\n"
            "• Регулярно публикуйте посты\n"
            "• Следите за статистикой\n\n"
            "❓ Вопросы: @support_bot"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif data.startswith("select_channel_"):
        await post_to_channel(update, context)
    
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)
    
    elif data == "connect_account":
        await connect_account(update, context)

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("connect", connect_account))
    
    # ConversationHandler для авторизации
    auth_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(connect_account, pattern="^connect_account$")],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel_auth)]
    )
    application.add_handler(auth_handler)
    
    # Обработчики для добавления каналов и постов
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel') 
        else (handle_post_content(u, c) if c.user_data.get('awaiting_post')
        else (save_repost_source(u, c) if c.user_data.get('awaiting_source')
        else None))
    ))
    
    # Обработчики медиа для постов
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.DOCUMENT) & ~filters.COMMAND,
        handle_post_content
    ))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запуск бота
    logger.info("🚀 Бот для постинга запущен!")
    logger.info("📱 Поддерживает подключение аккаунтов через телефон")
    logger.info("💎 Доступны бесплатные тарифы")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
