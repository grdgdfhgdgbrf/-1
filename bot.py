import asyncio
import logging
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import re

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

# Для работы с Telegram Client
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# API ID и API Hash для Telethon (стандартные, можно использовать любые)
API_ID = 2040  # Стандартный ID для тестов
API_HASH = "b18441a1ff607e10a989891a5462e627"

# ==================== ТАРИФЫ ====================
class TariffPlan(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    VIP = "vip"

TARIFFS = {
    "free": {
        "name": "📢 Бесплатный",
        "price": 0,
        "channels_limit": 1,
        "posts_per_day": 5,
        "features": ["Добавление в 1 канал", "5 постов в день", "Ручной постинг"]
    },
    "basic": {
        "name": "⭐ Базовый",
        "price": 0,  # Бесплатно для теста
        "channels_limit": 3,
        "posts_per_day": 20,
        "features": ["Добавление в 3 канала", "20 постов в день", "Автопостинг", "Перепостинг"]
    },
    "pro": {
        "name": "💎 Про",
        "price": 0,  # Бесплатно для теста
        "channels_limit": 10,
        "posts_per_day": 100,
        "features": ["Добавление в 10 каналов", "100 постов в день", "Автопостинг", "Перепостинг", "Расписание"]
    },
    "vip": {
        "name": "👑 VIP",
        "price": 0,  # Бесплатно для теста
        "channels_limit": 999,
        "posts_per_day": 999,
        "features": ["Безлимит каналов", "Безлимит постов", "Автопостинг 24/7", "Перепостинг", "Расширенное расписание"]
    }
}

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  phone TEXT,
                  tariff TEXT DEFAULT 'free',
                  tariff_expiry TIMESTAMP,
                  session_string TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Подключенные аккаунты
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  phone TEXT,
                  session_string TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Каналы для постинга
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (channel_id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  channel_username TEXT,
                  channel_title TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Источники для перепостинга
    c.execute('''CREATE TABLE IF NOT EXISTS sources
                 (source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  source_channel TEXT,
                  target_channel INTEGER,
                  is_active BOOLEAN DEFAULT 1,
                  FOREIGN KEY (user_id) REFERENCES users (user_id),
                  FOREIGN KEY (target_channel) REFERENCES channels (channel_id))''')
    
    # Посты
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id INTEGER,
                  content TEXT,
                  media_url TEXT,
                  scheduled_time TIMESTAMP,
                  is_published BOOLEAN DEFAULT 0,
                  published_at TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id),
                  FOREIGN KEY (channel_id) REFERENCES channels (channel_id))''')
    
    # Расписание автопостинга
    c.execute('''CREATE TABLE IF NOT EXISTS schedules
                 (schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id INTEGER,
                  interval_minutes INTEGER,
                  last_post TIMESTAMP,
                  is_active BOOLEAN DEFAULT 1,
                  FOREIGN KEY (user_id) REFERENCES users (user_id),
                  FOREIGN KEY (channel_id) REFERENCES channels (channel_id))''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== УПРАВЛЕНИЕ АККАУНТАМИ ====================
class AccountManager:
    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}
        self.user_sessions: Dict[int, str] = {}
    
    def save_session(self, user_id: int, phone: str, session_string: str):
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO accounts (user_id, phone, session_string) VALUES (?, ?, ?)",
                  (user_id, phone, session_string))
        conn.commit()
        conn.close()
    
    def get_session(self, user_id: int) -> Optional[str]:
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("SELECT session_string FROM accounts WHERE user_id = ? AND is_active = 1", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    
    async def get_client(self, user_id: int) -> Optional[TelegramClient]:
        if user_id in self.clients and self.clients[user_id].is_connected():
            return self.clients[user_id]
        
        session_string = self.get_session(user_id)
        if not session_string:
            return None
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if await client.is_user_authorized():
            self.clients[user_id] = client
            return client
        
        return None
    
    async def add_channel(self, user_id: int, channel_identifier: str) -> tuple[bool, str]:
        """Добавление канала в список"""
        client = await self.get_client(user_id)
        if not client:
            return False, "❌ Аккаунт не подключен. Используйте /login"
        
        try:
            # Определяем тип ввода (username или invite link)
            if "t.me/+" in channel_identifier or "+" in channel_identifier:
                # Инвайт ссылка
                if "t.me/+" in channel_identifier:
                    hash_code = channel_identifier.split("t.me/+")[-1]
                else:
                    hash_code = channel_identifier.split("+")[-1]
                
                await client(ImportChatInviteRequest(hash_code))
                channel = await client.get_entity(channel_identifier)
            else:
                # Username
                username = channel_identifier.replace("@", "").replace("t.me/", "")
                channel = await client.get_entity(username)
                await client(JoinChannelRequest(channel))
            
            # Сохраняем в БД
            conn = sqlite3.connect('posting_bot.db')
            c = conn.cursor()
            
            # Проверяем лимит по тарифу
            c.execute("SELECT tariff FROM users WHERE user_id = ?", (user_id,))
            tariff = c.fetchone()[0]
            channels_limit = TARIFFS[tariff]["channels_limit"]
            
            c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ?", (user_id,))
            current_count = c.fetchone()[0]
            
            if current_count >= channels_limit and channels_limit != 999:
                conn.close()
                return False, f"❌ Достигнут лимит каналов для тарифа {TARIFFS[tariff]['name']} (макс: {channels_limit})"
            
            c.execute("INSERT OR REPLACE INTO channels (channel_id, user_id, channel_username, channel_title) VALUES (?, ?, ?, ?)",
                      (channel.id, user_id, channel.username or channel_identifier, channel.title))
            conn.commit()
            conn.close()
            
            return True, f"✅ Канал {channel.title} успешно добавлен!"
            
        except Exception as e:
            logger.error(f"Ошибка добавления канала: {e}")
            return False, f"❌ Ошибка: {str(e)}"
    
    async def post_to_channel(self, user_id: int, channel_id: int, message: str, media=None) -> tuple[bool, str]:
        """Постинг в канал"""
        client = await self.get_client(user_id)
        if not client:
            return False, "❌ Аккаунт не подключен"
        
        try:
            entity = await client.get_entity(channel_id)
            
            # Проверяем лимит постов
            conn = sqlite3.connect('posting_bot.db')
            c = conn.cursor()
            
            c.execute("SELECT tariff FROM users WHERE user_id = ?", (user_id,))
            tariff = c.fetchone()[0]
            posts_limit = TARIFFS[tariff]["posts_per_day"]
            
            today = datetime.now().date()
            c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND DATE(published_at) = ?", 
                     (user_id, today))
            posts_today = c.fetchone()[0]
            
            if posts_today >= posts_limit and posts_limit != 999:
                conn.close()
                return False, f"❌ Достигнут лимит постов для тарифа {TARIFFS[tariff]['name']} (макс: {posts_limit} в день)"
            
            if media:
                await client.send_file(entity, media, caption=message)
            else:
                await client.send_message(entity, message)
            
            # Сохраняем пост
            c.execute("INSERT INTO posts (user_id, channel_id, content, is_published, published_at) VALUES (?, ?, ?, 1, ?)",
                      (user_id, channel_id, message, datetime.now()))
            conn.commit()
            conn.close()
            
            return True, "✅ Пост успешно опубликован!"
            
        except Exception as e:
            logger.error(f"Ошибка постинга: {e}")
            return False, f"❌ Ошибка: {str(e)}"
    
    async def setup_reposting(self, user_id: int, source_channel: str, target_channel_id: int) -> tuple[bool, str]:
        """Настройка перепостинга"""
        client = await self.get_client(user_id)
        if not client:
            return False, "❌ Аккаунт не подключен"
        
        try:
            source_entity = await client.get_entity(source_channel)
            
            conn = sqlite3.connect('posting_bot.db')
            c = conn.cursor()
            
            c.execute("INSERT INTO sources (user_id, source_channel, target_channel) VALUES (?, ?, ?)",
                      (user_id, source_entity.id, target_channel_id))
            conn.commit()
            conn.close()
            
            return True, f"✅ Перепостинг из {source_entity.title} настроен!"
            
        except Exception as e:
            logger.error(f"Ошибка настройки перепостинга: {e}")
            return False, f"❌ Ошибка: {str(e)}"
    
    async def start_reposting_listener(self, user_id: int):
        """Запуск слушателя для перепостинга"""
        client = await self.get_client(user_id)
        if not client:
            return
        
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("SELECT source_channel, target_channel FROM sources WHERE user_id = ? AND is_active = 1", (user_id,))
        sources = c.fetchall()
        conn.close()
        
        @client.on(events.NewMessage(chats=[source[0] for source in sources]))
        async def handler(event):
            for source in sources:
                if event.chat_id == source[0]:
                    # Пересылаем пост
                    await self.post_to_channel(user_id, source[1], event.message.text or "", 
                                              event.message.media)
        
        # Запускаем клиент если не запущен
        if not client.is_connected():
            await client.start()

account_manager = AccountManager()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
# Состояния для разговора
PHONE, CODE, TARIFF_SELECTION, ADD_CHANNEL, POST_CONTENT, POST_MEDIA, SCHEDULE_TIME, REPOST_SOURCE, REPOST_TARGET = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Регистрируем пользователя
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, tariff) VALUES (?, ?, ?, 'free')",
              (user.id, user.username or "", user.first_name or ""))
    conn.commit()
    conn.close()
    
    welcome_text = (
        f"✨ *Добро пожаловать, {user.first_name}!*\n\n"
        f"🤖 *Бот для автопостинга в Telegram*\n\n"
        f"📢 *Возможности:*\n"
        f"• Подключение аккаунта по номеру телефона\n"
        f"• Добавление в каналы\n"
        f"• Автоматический постинг\n"
        f"• Перепостинг из других каналов\n"
        f"• Гибкие тарифы\n\n"
        f"🎯 *Чтобы начать, выполните вход:*\n"
        f"🔑 Используйте команду /login"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Войти", callback_data="login")],
        [InlineKeyboardButton("📊 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📖 Помощь", callback_data="help")]
    ])
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса входа"""
    await update.message.reply_text(
        "🔐 *Вход в аккаунт Telegram*\n\n"
        "📱 *Инструкция:*\n"
        "1. Введите номер телефона в международном формате\n"
        "2. Пример: +79123456789\n\n"
        "⚠️ *Важно:* Бот работает через официальное API Telegram\n\n"
        "📞 Введите номер телефона:",
        parse_mode='Markdown'
    )
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    phone = update.message.text.strip()
    
    # Простая валидация номера
    if not re.match(r'^\+?\d{10,15}$', phone):
        await update.message.reply_text("❌ Неверный формат номера. Введите номер в формате +79123456789")
        return PHONE
    
    context.user_data['phone'] = phone
    
    try:
        # Создаем временный клиент
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        # Отправляем код
        await client.send_code_request(phone)
        context.user_data['temp_client'] = client
        
        await update.message.reply_text(
            "✅ Код подтверждения отправлен!\n\n"
            "📝 Введите код из SMS или Telegram:",
            parse_mode='Markdown'
        )
        return CODE
        
    except Exception as e:
        logger.error(f"Ошибка отправки кода: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз /login")
        return ConversationHandler.END

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода подтверждения"""
    code = update.message.text.strip()
    client = context.user_data.get('temp_client')
    phone = context.user_data.get('phone')
    
    if not client:
        await update.message.reply_text("❌ Сессия истекла. Начните заново /login")
        return ConversationHandler.END
    
    try:
        await client.sign_in(phone, code)
        
        # Сохраняем сессию
        session_string = client.session.save()
        user_id = update.effective_user.id
        
        account_manager.save_session(user_id, phone, session_string)
        
        # Обновляем информацию о пользователе
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        conn.commit()
        conn.close()
        
        await client.disconnect()
        
        await update.message.reply_text(
            "✅ *Аккаунт успешно подключен!*\n\n"
            "🎉 Теперь вы можете:\n"
            "• /addchannel - добавить канал\n"
            "• /post - создать пост\n"
            "• /repost - настроить перепостинг\n"
            "• /status - статус аккаунта",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз /login")
        return ConversationHandler.END

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    tariffs_text = "💎 *Наши тарифы*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        tariffs_text += f"**{tariff['name']}**\n"
        tariffs_text += f"💰 Цена: {tariff['price']} руб.\n"
        tariffs_text += f"📊 Лимит каналов: {tariff['channels_limit']}\n"
        tariffs_text += f"📝 Постов в день: {tariff['posts_per_day']}\n"
        tariffs_text += "✨ Возможности:\n"
        for feature in tariff['features']:
            tariffs_text += f"  • {feature}\n"
        tariffs_text += "\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Базовый", callback_data="tariff_basic")],
        [InlineKeyboardButton("💎 Про", callback_data="tariff_pro")],
        [InlineKeyboardButton("👑 VIP", callback_data="tariff_vip")]
    ])
    
    await update.message.reply_text(tariffs_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление канала"""
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "Введите ссылку или username канала:\n"
        "• @username\n"
        "• https://t.me/username\n"
        "• https://t.me/+invitecode\n\n"
        "Пример: @durov",
        parse_mode='Markdown'
    )
    return ADD_CHANNEL

async def handle_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    channel_input = update.message.text.strip()
    user_id = update.effective_user.id
    
    success, message = await account_manager.add_channel(user_id, channel_input)
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    if success:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить еще", callback_data="add_more_channel")],
            [InlineKeyboardButton("📝 Создать пост", callback_data="create_post")]
        ])
        await update.message.reply_text("Что делаем дальше?", reply_markup=keyboard)
    
    return ConversationHandler.END

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание поста"""
    # Показываем список каналов
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND is_active = 1", 
              (update.effective_user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await update.message.reply_text(
            "❌ У вас нет добавленных каналов.\n\n"
            "Добавьте канал командой /addchannel"
        )
        return ConversationHandler.END
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"post_channel_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_post")])
    
    await update.message.reply_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return POST_CONTENT

async def handle_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка контента поста"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_post":
        await query.edit_message_text("❌ Создание поста отменено")
        return ConversationHandler.END
    
    if query.data.startswith("post_channel_"):
        channel_id = int(query.data.replace("post_channel_", ""))
        context.user_data['post_channel_id'] = channel_id
        
        await query.edit_message_text(
            "📝 *Напишите текст поста:*\n\n"
            "Вы можете использовать Markdown форматирование:\n"
            "*жирный*\n"
            "_курсив_\n"
            "```код```\n\n"
            "Отправьте текст сообщением:",
            parse_mode='Markdown'
        )
        return POST_MEDIA

async def handle_post_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка медиа для поста"""
    content = update.message.text
    context.user_data['post_content'] = content
    
    await update.message.reply_text(
        "🖼 *Добавить медиа?*\n\n"
        "Отправьте фото, видео или документ.\n"
        "Или нажмите /skip чтобы пропустить:",
        parse_mode='Markdown'
    )
    return SCHEDULE_TIME

async def handle_post_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка расписания"""
    media = None
    if update.message.photo:
        media = await update.message.photo[-1].get_file()
    elif update.message.video:
        media = await update.message.video.get_file()
    elif update.message.document:
        media = await update.message.document.get_file()
    
    context.user_data['post_media'] = media
    
    await update.message.reply_text(
        "⏰ *Когда опубликовать?*\n\n"
        "Выберите вариант:\n"
        "• /now - опубликовать сейчас\n"
        "• /schedule - запланировать\n\n"
        "Или нажмите /skip для отмены:",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def publish_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация сейчас"""
    user_id = update.effective_user.id
    channel_id = context.user_data.get('post_channel_id')
    content = context.user_data.get('post_content', '')
    media = context.user_data.get('post_media')
    
    if media:
        # Скачиваем медиа
        media_path = f"temp/{user_id}_{datetime.now().timestamp()}.jpg"
        await media.download_to_drive(media_path)
        
        success, message = await account_manager.post_to_channel(user_id, channel_id, content, media_path)
    else:
        success, message = await account_manager.post_to_channel(user_id, channel_id, content)
    
    await update.message.reply_text(message, parse_mode='Markdown')
    return ConversationHandler.END

async def repost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка перепостинга"""
    await update.message.reply_text(
        "🔄 *Настройка перепостинга*\n\n"
        "Введите ссылку или username канала-источника:\n"
        "• @username\n"
        "• https://t.me/username\n\n"
        "Пример: @durov",
        parse_mode='Markdown'
    )
    return REPOST_SOURCE

async def handle_repost_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка источника перепостинга"""
    source = update.message.text.strip()
    context.user_data['repost_source'] = source
    
    # Показываем список целевых каналов
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND is_active = 1", 
              (update.effective_user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await update.message.reply_text(
            "❌ У вас нет добавленных каналов.\n\n"
            "Добавьте канал командой /addchannel"
        )
        return ConversationHandler.END
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"target_{channel_id}")])
    
    await update.message.reply_text(
        "🎯 *Выберите целевой канал для перепостинга:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return REPOST_TARGET

async def handle_repost_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка целевого канала для перепостинга"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("target_"):
        target_channel = int(query.data.replace("target_", ""))
        source = context.user_data.get('repost_source')
        user_id = update.effective_user.id
        
        success, message = await account_manager.setup_reposting(user_id, source, target_channel)
        
        await query.edit_message_text(message, parse_mode='Markdown')
        
        if success:
            await account_manager.start_reposting_listener(user_id)
            await query.message.reply_text(
                "✅ *Перепостинг активирован!*\n\n"
                "Все новые посты из канала-источника будут автоматически публиковаться в вашем канале."
            )
        
        return ConversationHandler.END

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статус аккаунта"""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Информация о пользователе
    c.execute("SELECT phone, tariff FROM users WHERE user_id = ?", (user_id,))
    user_info = c.fetchone()
    
    # Аккаунты
    c.execute("SELECT COUNT(*) FROM accounts WHERE user_id = ? AND is_active = 1", (user_id,))
    accounts_count = c.fetchone()[0]
    
    # Каналы
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND is_active = 1", (user_id,))
    channels_count = c.fetchone()[0]
    
    # Источники перепостинга
    c.execute("SELECT COUNT(*) FROM sources WHERE user_id = ? AND is_active = 1", (user_id,))
    sources_count = c.fetchone()[0]
    
    # Посты сегодня
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND DATE(published_at) = ?", (user_id, today))
    posts_today = c.fetchone()[0]
    
    conn.close()
    
    tariff_info = TARIFFS.get(user_info[1] if user_info else 'free', TARIFFS['free'])
    
    status_text = (
        f"📊 *Статус аккаунта*\n\n"
        f"👤 *Пользователь:* {update.effective_user.first_name}\n"
        f"📞 *Телефон:* {user_info[0] if user_info else 'Не подключен'}\n"
        f"💎 *Тариф:* {tariff_info['name']}\n"
        f"🔑 *Аккаунтов:* {accounts_count}\n"
        f"📢 *Каналов:* {channels_count}/{tariff_info['channels_limit']}\n"
        f"🔄 *Перепостингов:* {sources_count}\n"
        f"📝 *Постов сегодня:* {posts_today}/{tariff_info['posts_per_day']}\n\n"
        f"📋 *Доступные команды:*\n"
        f"• /addchannel - добавить канал\n"
        f"• /post - создать пост\n"
        f"• /repost - настроить перепостинг\n"
        f"• /tariffs - тарифы"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "login":
        await login_command(update, context)
    
    elif query.data == "tariffs":
        await show_tariffs(update, context)
    
    elif query.data == "help":
        help_text = (
            "📖 *Помощь*\n\n"
            "🔑 *Команды:*\n"
            "/login - подключить аккаунт\n"
            "/addchannel - добавить канал\n"
            "/post - создать пост\n"
            "/repost - настроить перепостинг\n"
            "/tariffs - просмотр тарифов\n"
            "/status - статус аккаунта\n\n"
            "❓ *Вопросы:*\n"
            "• Как войти? Используйте /login\n"
            "• Как добавить канал? /addchannel\n"
            "• Как настроить автопостинг? /repost"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif query.data.startswith("tariff_"):
        tariff_key = query.data.replace("tariff_", "")
        if tariff_key in TARIFFS:
            conn = sqlite3.connect('posting_bot.db')
            c = conn.cursor()
            c.execute("UPDATE users SET tariff = ? WHERE user_id = ?", 
                     (tariff_key, query.from_user.id))
            conn.commit()
            conn.close()
            
            await query.edit_message_text(
                f"✅ Тариф изменен на {TARIFFS[tariff_key]['name']}!\n"
                f"Новый лимит каналов: {TARIFFS[tariff_key]['channels_limit']}\n"
                f"Новый лимит постов: {TARIFFS[tariff_key]['posts_per_day']} в день"
            )
    
    elif query.data == "add_more_channel":
        await add_channel_command(update, context)
    
    elif query.data == "create_post":
        await post_command(update, context)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handlers
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_command)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    
    add_channel_conv = ConversationHandler(
        entry_points=[CommandHandler("addchannel", add_channel_command)],
        states={
            ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_channel)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    
    post_conv = ConversationHandler(
        entry_points=[CommandHandler("post", post_command)],
        states={
            POST_CONTENT: [CallbackQueryHandler(handle_post_content)],
            POST_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_media)],
            SCHEDULE_TIME: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.DOCUMENT | filters.TEXT, handle_post_schedule)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    
    repost_conv = ConversationHandler(
        entry_points=[CommandHandler("repost", repost_command)],
        states={
            REPOST_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_repost_source)],
            REPOST_TARGET: [CallbackQueryHandler(handle_repost_target)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(login_conv)
    application.add_handler(add_channel_conv)
    application.add_handler(post_conv)
    application.add_handler(repost_conv)
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tariffs", show_tariffs))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Быстрые команды
    application.add_handler(CommandHandler("now", publish_now))
    
    logger.info("🚀 Бот для автопостинга запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
