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
import aiohttp

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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# Состояния для ConversationHandler
PHONE, CODE, PASSWORD = range(3)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  joined_date TIMESTAMP,
                  last_active TIMESTAMP)''')
    
    # Таблица каналов для постинга
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  channel_title TEXT,
                  channel_username TEXT,
                  added_date TIMESTAMP,
                  status TEXT DEFAULT 'active',
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Таблица тарифов
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY,
                  tariff TEXT DEFAULT 'free',
                  start_date TIMESTAMP,
                  end_date TIMESTAMP,
                  max_channels INTEGER DEFAULT 1,
                  repost_limit INTEGER DEFAULT 10,
                  post_interval INTEGER DEFAULT 3600,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Таблица источников для репостов
    c.execute('''CREATE TABLE IF NOT EXISTS sources
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  source_channel_id TEXT,
                  source_channel_title TEXT,
                  target_channel_id TEXT,
                  is_active INTEGER DEFAULT 1,
                  added_date TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  content TEXT,
                  media_file_id TEXT,
                  media_type TEXT,
                  post_type TEXT,
                  scheduled_time TIMESTAMP,
                  posted_time TIMESTAMP,
                  status TEXT DEFAULT 'pending',
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Таблица настроек автопостинга
    c.execute('''CREATE TABLE IF NOT EXISTS auto_posting_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  channel_id TEXT,
                  user_id INTEGER,
                  is_auto_active INTEGER DEFAULT 0,
                  auto_topic TEXT,
                  post_frequency INTEGER DEFAULT 3600,
                  last_post_time TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "price": "0 ₽",
        "max_channels": 2,
        "repost_limit": 20,
        "post_interval": 3600,
        "features": [
            "✅ 2 канала для постинга",
            "✅ 20 репостов в день",
            "✅ Интервал 1 час",
            "✅ Ручной постинг",
            "✅ Базовые темы"
        ]
    },
    "basic": {
        "name": "📘 Базовый",
        "price": "0 ₽ (Бесплатно)",
        "max_channels": 5,
        "repost_limit": 100,
        "post_interval": 1800,
        "features": [
            "✅ До 5 каналов",
            "✅ 100 репостов в день",
            "✅ Интервал 30 минут",
            "✅ Автопостинг",
            "✅ 5 тем для контента",
            "✅ Репосты из источников"
        ]
    },
    "pro": {
        "name": "💎 PRO",
        "price": "0 ₽ (Бесплатно)",
        "max_channels": 15,
        "repost_limit": 500,
        "post_interval": 600,
        "features": [
            "✅ До 15 каналов",
            "✅ 500 репостов в день",
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
    },
    "news": {
        "name": "📰 Новости",
        "keywords": ["новости", "события", "актуально", "тренды", "обзор"],
        "prompt": "Ты новостной обозреватель. Пиши актуальные новости, обзоры событий, тренды."
    },
    "cooking": {
        "name": "🍳 Кулинария",
        "keywords": ["рецепты", "готовка", "еда", "кулинария", "вкусно"],
        "prompt": "Ты шеф-повар. Делишься вкусными рецептами, кулинарными советами, секретами готовки."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "keywords": ["путешествия", "туризм", "страны", "достопримечательности", "отдых"],
        "prompt": "Ты опытный путешественник. Рассказываешь о странах, достопримечательностях, даешь советы по путешествиям."
    },
    "science": {
        "name": "🔬 Наука",
        "keywords": ["наука", "открытия", "исследования", "космос", "физика"],
        "prompt": "Ты ученый. Объясняешь научные открытия, исследования, явления простым языком."
    }
}

# ==================== ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.bot = None
        self.posting_tasks = {}
        
    def get_db_connection(self):
        return sqlite3.connect('posting_bot.db')
    
    async def send_post_to_channel(self, bot, channel_id: str, message: str, media_file_id=None, media_type=None):
        """Отправить пост в канал через бота"""
        try:
            if media_file_id and media_type:
                if media_type == 'photo':
                    await bot.send_photo(chat_id=channel_id, photo=media_file_id, caption=message)
                elif media_type == 'video':
                    await bot.send_video(chat_id=channel_id, video=media_file_id, caption=message)
                elif media_type == 'document':
                    await bot.send_document(chat_id=channel_id, document=media_file_id, caption=message)
                else:
                    await bot.send_message(chat_id=channel_id, text=message)
            else:
                await bot.send_message(chat_id=channel_id, text=message)
            
            # Сохраняем пост в БД
            conn = self.get_db_connection()
            c = conn.cursor()
            c.execute("""INSERT INTO posts (user_id, channel_id, content, media_file_id, media_type, post_type, posted_time, status) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (channel_id.split('_')[0] if '_' in channel_id else 0, channel_id, message, 
                       media_file_id or "", media_type or "", "manual", datetime.now(), "posted"))
            conn.commit()
            conn.close()
            
            return True, "✅ Пост успешно опубликован!"
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
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

async def get_topics_keyboard(channel_id: str = None):
    """Клавиатура выбора темы"""
    keyboard = []
    for topic_key, topic_info in TOPICS.items():
        callback = f"set_topic_{channel_id}_{topic_key}" if channel_id else f"topic_{topic_key}"
        keyboard.append([
            InlineKeyboardButton(f"{topic_info['name']}", callback_data=callback)
        ])
    
    if channel_id:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(keyboard)

async def get_repost_keyboard(user_id: int):
    """Клавиатура репостов"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить источник", callback_data="add_source")],
        [InlineKeyboardButton("📋 Мои источники", callback_data="my_sources")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Регистрируем пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
              (user.id, user.username or "", user.first_name or "", datetime.now(), datetime.now()))
    
    # Создаем подписку если нет
    c.execute("INSERT OR IGNORE INTO subscriptions (user_id, tariff, start_date, max_channels) VALUES (?, 'free', ?, 2)",
              (user.id, datetime.now()))
    conn.commit()
    conn.close()
    
    welcome_text = (
        f"✨ *Добро пожаловать, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автоматического постинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Писать посты в каналы\n"
        f"• 🔄 Делать репосты из других каналов\n"
        f"• ⚙️ Настраивать автопостинг по темам\n"
        f"• 📊 Смотреть статистику\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал через меню 'Мои каналы'\n"
        f"3️⃣ Начните публиковать контент!\n\n"
        f"💡 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления канала"""
    user = update.effective_user
    
    # Проверяем лимит каналов
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    tariff = sub[0] if sub else "free"
    max_channels = TARIFFS[tariff]["max_channels"]
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    current_count = c.fetchone()[0]
    conn.close()
    
    if current_count >= max_channels:
        await update.callback_query.edit_message_text(
            f"❌ Достигнут лимит каналов для тарифа '{TARIFFS[tariff]['name']}'\n"
            f"Максимум: {max_channels} каналов\n\n"
            f"Чтобы добавить больше, перейдите на другой тариф в меню 'Тарифы'"
        )
        return
    
    await update.callback_query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "Для добавления канала:\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID канала или ссылку\n\n"
        "📝 *Как получить ID канала:*\n"
        "• Форвардните любое сообщение из канала боту\n"
        "• Или отправьте ссылку вида: `@channel_username`\n"
        "• Или: `https://t.me/channel_username`\n\n"
        "⚠️ *Важно:* Бот должен быть администратором канала!\n\n"
        "Отправьте ID или ссылку на канал:",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    # Извлекаем ID канала
    channel_id = channel_input
    channel_username = None
    
    if "t.me/" in channel_input:
        channel_username = channel_input.split("t.me/")[-1]
        if "/" in channel_username:
            channel_username = channel_username.split("/")[0]
        channel_id = f"@{channel_username}"
    elif channel_input.startswith("@"):
        channel_username = channel_input[1:]
    
    try:
        # Пробуем получить информацию о канале через бота
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал. Пожалуйста, отправьте ссылку на канал.")
            return
        
        # Сохраняем канал
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        
        # Проверяем, не добавлен ли уже
        c.execute("SELECT * FROM channels WHERE user_id = ? AND channel_id = ?", (user.id, str(chat.id)))
        existing = c.fetchone()
        
        if existing:
            await update.message.reply_text("❌ Этот канал уже добавлен!")
            return
        
        c.execute("""INSERT INTO channels (user_id, channel_id, channel_title, channel_username, added_date) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (user.id, str(chat.id), chat.title, channel_username or "", datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Канал успешно добавлен!*\n\n"
            f"📢 Название: {chat.title}\n"
            f"🆔 ID: {chat.id}\n\n"
            f"Теперь вы можете публиковать посты в этот канал!",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_channel'] = False
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            f"Убедитесь что:\n"
            f"• Бот добавлен в канал как администратор\n"
            f"• Ссылка на канал введена верно\n"
            f"• Канал существует",
            parse_mode='Markdown'
        )

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Написать пост"""
    query = update.callback_query
    await query.answer()
    
    # Получаем список каналов пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", 
              (query.from_user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через меню 'Мои каналы'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel_id, channel_title in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel_title}", callback_data=f"select_channel_{channel_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
    result = c.fetchone()
    channel_title = result[0] if result else "канал"
    conn.close()
    
    await query.edit_message_text(
        f"📝 *Напишите пост для канала* `{channel_title}`\n\n"
        f"Вы можете отправить:\n"
        f"• 📝 Текст сообщения\n"
        f"• 🖼 Фото с подписью\n"
        f"• 🎥 Видео с подписью\n"
        f"• 📎 Документ с подписью\n\n"
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
    media_file_id = None
    media_type = None
    caption = None
    
    if update.message.photo:
        media_file_id = update.message.photo[-1].file_id
        media_type = 'photo'
        caption = update.message.caption
    elif update.message.video:
        media_file_id = update.message.video.file_id
        media_type = 'video'
        caption = update.message.caption
    elif update.message.document:
        media_file_id = update.message.document.file_id
        media_type = 'document'
        caption = update.message.caption
    elif update.message.text:
        caption = update.message.text
    else:
        await update.message.reply_text("❌ Неподдерживаемый тип сообщения")
        return
    
    # Отправляем пост
    success, message = await bot_manager.send_post_to_channel(
        context.bot, channel_id, caption or "", media_file_id, media_type
    )
    
    await update.message.reply_text(message)
    
    if success:
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
    
    context.user_data['awaiting_post'] = False
    context.user_data['post_channel_id'] = None

async def setup_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка автопостинга"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Получаем список каналов
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал для автопостинга",
            parse_mode='Markdown'
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
    
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "Выберите канал для настройки автоматической публикации:\n\n"
        "✅ - автопостинг активен\n"
        "❌ - автопостинг неактивен",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def configure_auto_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Конфигурация автопостинга для канала"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    context.user_data['auto_channel_id'] = channel_id
    
    # Получаем текущие настройки
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_auto_active, auto_topic, post_frequency FROM auto_posting_settings WHERE channel_id = ?", (channel_id,))
    settings = c.fetchone()
    conn.close()
    
    is_active = settings[0] if settings else 0
    current_topic = settings[1] if settings and settings[1] else "Не выбрана"
    frequency = settings[2] if settings else 3600
    
    # Получаем название темы
    topic_name = current_topic
    if current_topic in TOPICS:
        topic_name = TOPICS[current_topic]["name"]
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {frequency // 60} минут\n\n"
        f"Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 {'Выключить' if is_active else 'Включить'}", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("⏱ Изменить интервал", callback_data=f"change_freq_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_topic_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор темы для автопостинга"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_", "")
    context.user_data['topic_channel_id'] = channel_id
    
    keyboard = await get_topics_keyboard(channel_id)
    await query.edit_message_text(
        "📝 *Выберите тему для автоматических постов:*\n\n"
        "Посты будут генерироваться на выбранную тему",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка темы для автопостинга"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic_key = parts[3]
    
    # Сохраняем тему
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO auto_posting_settings (channel_id, user_id, auto_topic) 
                 VALUES (?, ?, ?)""",
              (channel_id, query.from_user.id, topic_key))
    conn.commit()
    conn.close()
    
    topic_name = TOPICS[topic_key]["name"]
    
    await query.edit_message_text(
        f"✅ *Тема установлена!*\n\n"
        f"📝 Тема: {topic_name}\n\n"
        f"Теперь включите автопостинг для начала публикаций",
        parse_mode='Markdown'
    )
    
    # Возвращаемся к настройкам
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def toggle_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение автопостинга"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_auto_active FROM auto_posting_settings WHERE channel_id = ?", (channel_id,))
    result = c.fetchone()
    
    new_status = 0 if result and result[0] else 1
    
    if new_status == 1:
        # Проверяем наличие темы
        c.execute("SELECT auto_topic FROM auto_posting_settings WHERE channel_id = ?", (channel_id,))
        topic = c.fetchone()
        if not topic or not topic[0]:
            conn.close()
            await query.edit_message_text(
                "❌ *Сначала выберите тему для автопостинга!*",
                parse_mode='Markdown'
            )
            await asyncio.sleep(2)
            await select_topic_for_channel(update, context)
            return
    
    c.execute("""INSERT OR REPLACE INTO auto_posting_settings (channel_id, user_id, is_auto_active, last_post_time) 
                 VALUES (?, ?, ?, ?)""",
              (channel_id, query.from_user.id, new_status, datetime.now() if new_status else None))
    conn.commit()
    conn.close()
    
    status_text = "включен" if new_status else "выключен"
    await query.edit_message_text(f"✅ *Автопостинг {status_text}!*", parse_mode='Markdown')
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def add_repost_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление источника для репостов"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Получаем каналы пользователя
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *У вас нет каналов для репостов!*\n\n"
            "Сначала добавьте канал",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel_id, channel_title in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel_title}", callback_data=f"target_{channel_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="reposts_menu")])
    
    await query.edit_message_text(
        "🔄 *Добавление источника для репостов*\n\n"
        "Выберите целевой канал (куда будут публиковаться репосты):",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_target_for_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор целевого канала для репостов"""
    query = update.callback_query
    await query.answer()
    
    target_channel = query.data.replace("target_", "")
    context.user_data['repost_target'] = target_channel
    
    await query.edit_message_text(
        "📢 *Укажите источник для репостов*\n\n"
        "Отправьте ID или ссылку на канал/чат, откуда будут браться посты:\n\n"
        "📝 Примеры:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "⚠️ Бот должен иметь доступ к этому каналу\n\n"
        "Отправьте ссылку на источник:",
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
    
    try:
        # Получаем информацию об источнике
        chat = await context.bot.get_chat(chat_id=source_input)
        
        # Сохраняем в БД
        conn = bot_manager.get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO sources (user_id, source_channel_id, source_channel_title, target_channel_id, added_date) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (user.id, str(chat.id), chat.title, target_channel, datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Источник репостов добавлен!*\n\n"
            f"📢 Источник: {chat.title}\n"
            f"🎯 Целевой канал: {target_channel}\n\n"
            f"Теперь вы можете делать репосты из этого канала!",
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_source'] = False
        
        # Показываем меню репостов
        keyboard = await get_repost_keyboard(user.id)
        await update.message.reply_text("🔄 Меню репостов:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            f"Убедитесь что:\n"
            f"• Бот имеет доступ к этому каналу\n"
            f"• Ссылка введена верно",
            parse_mode='Markdown'
        )

async def show_my_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать источники репостов"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = bot_manager.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT source_channel_title, target_channel_id FROM sources WHERE user_id = ? AND is_active = 1", (user.id,))
    sources = c.fetchall()
    conn.close()
    
    if not sources:
        await query.edit_message_text(
            "❌ *У вас нет добавленных источников*\n\n"
            "Добавьте источник через меню '➕ Добавить источник'",
            parse_mode='Markdown'
        )
        return
    
    text = "📋 *Ваши источники репостов:*\n\n"
    for i, (source_title, target) in enumerate(sources, 1):
        text += f"{i}. 📢 {source_title}\n   🎯 → {target}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="reposts_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
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
    
    text += "🎁 *Все тарифы полностью бесплатны!*\n"
    text += "Просто выберите подходящий тариф и пользуйтесь."
    
    keyboard = await get_tariff_keyboard()
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

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
        
        await asyncio.sleep(2)
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user_id)
        await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = bot_manager.get_db_connection()
    
    # Информация о пользователе
    c = conn.cursor()
    c.execute("SELECT joined_date, last_active FROM users WHERE user_id = ?", (user.id,))
    user_data = c.fetchone()
    
    # Информация о подписке
    c.execute("SELECT tariff, start_date, end_date FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    
    # Статистика
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM sources WHERE user_id = ? AND is_active = 1", (user.id,))
    sources_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND status='posted'", (user.id,))
    posts_count = c.fetchone()[0]
    
    conn.close()
    
    tariff = sub[0] if sub else "free"
    tariff_info = TARIFFS[tariff]
    
    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"🆔 ID: {user.id}\n"
        f"📝 Имя: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'нет'}\n\n"
        f"💎 Тариф: {tariff_info['name']}\n"
        f"📊 Статистика:\n"
        f"• Каналов: {channels_count}/{tariff_info['max_channels']}\n"
        f"• Источников: {sources_count}\n"
        f"• Постов: {posts_count}\n\n"
        f"📅 В системе с: {user_data[0] if user_data else 'сегодня'}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Сменить тариф", callback_data="tariffs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(profile_text, parse_mode='Markdown', reply_markup=keyboard)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
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
    
    # Посты по каналам
    c.execute("""SELECT c.channel_title, COUNT(p.id) 
                 FROM channels c 
                 LEFT JOIN posts p ON c.channel_id = p.channel_id 
                 WHERE c.user_id = ? 
                 GROUP BY c.channel_id""", (user.id,))
    channels_stats = c.fetchall()
    
    conn.close()
    
    stats_text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 *Посты:*\n"
        f"• Сегодня: {posts_today}\n"
        f"• За неделю: {posts_week}\n"
        f"• За месяц: {posts_month}\n\n"
    )
    
    if channels_stats:
        stats_text += "📢 *По каналам:*\n"
        for channel_title, count in channels_stats:
            stats_text += f"• {channel_title}: {count} постов\n"
    
    stats_text += "\n💡 *Совет:* Чем больше качественных постов, тем быстрее растет канал!"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*\n\nВыберите действие:", 
                                  parse_mode='Markdown', 
                                  reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text("❌ *Действие отменено*", parse_mode='Markdown')
    
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ГЛАВНЫЙ ОБРАБОТЧИК CALLBACK ====================
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
        await query.edit_message_text("📢 *Ваши каналы*\n\nВыберите канал для управления:", 
                                      parse_mode='Markdown', 
                                      reply_markup=keyboard)
    
    elif data == "add_channel":
        await add_channel_start(update, context)
    
    elif data == "reposts_menu":
        keyboard = await get_repost_keyboard(query.from_user.id)
        await query.edit_message_text("🔄 *Меню репостов*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_source":
        await add_repost_source(update, context)
    
    elif data == "my_sources":
        await show_my_sources(update, context)
    
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
            "1️⃣ *Добавьте канал*\n"
            "• Добавьте бота в канал как администратора\n"
            "• В меню 'Мои каналы' ➕ 'Добавить канал'\n"
            "• Отправьте ссылку на канал\n\n"
            "2️⃣ *Публикуйте посты*\n"
            "• 'Написать пост' ➡️ выберите канал\n"
            "• Отправьте текст, фото или видео\n\n"
            "3️⃣ *Настройте автопостинг*\n"
            "• В меню 'Автопостинг'\n"
            "• Выберите канал и тему\n"
            "• Включите автопостинг\n\n"
            "4️⃣ *Делайте репосты*\n"
            "• В меню 'Репосты'\n"
            "• Добавьте источник\n"
            "• Настройте автоматические репосты\n\n"
            "💡 *Советы:*\n"
            "• Используйте разные темы для контента\n"
            "• Регулярно публикуйте посты\n"
            "• Следите за статистикой\n\n"
            "🎁 *Все тарифы бесплатны!*\n"
            "❓ Вопросы и предложения: @support_bot"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif data.startswith("select_channel_"):
        await post_to_channel(update, context)
    
    elif data.startswith("auto_channel_"):
        await configure_auto_channel(update, context)
    
    elif data.startswith("select_topic_"):
        await select_topic_for_channel(update, context)
    
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    
    elif data.startswith("toggle_auto_"):
        await toggle_auto_posting(update, context)
    
    elif data.startswith("target_"):
        await select_target_for_repost(update, context)
    
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики для добавления каналов и постов
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel') 
        else (handle_post_content(u, c) if c.user_data.get('awaiting_post')
        else (save_repost_source(u, c) if c.user_data.get('awaiting_source')
        else None))
    ))
    
    # Обработчики медиа для постов (исправлено: используем filters.ATTACHMENT)
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.ATTACHMENT) & ~filters.COMMAND,
        handle_post_content
    ))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запуск бота
    logger.info("🚀 Бот для постинга запущен!")
    logger.info("📢 Работает через бота (не требует подключения аккаунта)")
    logger.info("💎 Все тарифы бесплатны!")
    logger.info("✅ Для работы добавьте бота в канал как администратора")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
