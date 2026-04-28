import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 2,
        "min_interval": 60,  # 1 минута в секундах
        "features": ["✅ 2 канала", "✅ Интервал от 1 минуты", "✅ Автопостинг"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 5,
        "min_interval": 30,  # 30 секунд
        "features": ["✅ 5 каналов", "✅ Интервал от 30 секунд", "✅ Автопостинг", "✅ Репосты"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 15,
        "min_interval": 10,  # 10 секунд
        "features": ["✅ 15 каналов", "✅ Интервал от 10 секунд", "✅ Автопостинг", "✅ Репосты", "✅ ИИ контент"]
    }
}

# ==================== ТЕМЫ ДЛЯ КОНТЕНТА ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии",
        "posts": [
            "🚀 Новый смартфон от Samsung представили с уникальным дизайном!",
            "💡 Искусственный интеллект теперь может создавать видео по тексту",
            "🔋 Разработана батарея, которая заряжается за 5 минут!",
            "🌐 Интернет вещей: умный дом становится доступнее",
            "🎮 NVIDIA представила новое поколение видеокарт"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "posts": [
            "💰 5 способов увеличить продажи в малом бизнесе",
            "📈 Криптовалюты: новый виток развития",
            "🏢 Как открыть свое дело с нуля: пошаговая инструкция",
            "💼 Фриланс: как зарабатывать удаленно",
            "📊 10 ошибок начинающих предпринимателей"
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "posts": [
            "🏃‍♂️ 10 минут зарядки в день изменят вашу жизнь",
            "🥗 Правильное питание: простые рецепты",
            "💪 Как сохранить здоровье на работе",
            "🧘‍♀️ Медитация для начинающих: первые шаги",
            "😴 8 часов сна - миф или необходимость?"
        ]
    },
    "education": {
        "name": "📚 Образование",
        "posts": [
            "📖 Как выучить английский за 3 месяца",
            "🧠 5 техник быстрого запоминания информации",
            "💡 Искусство публичных выступлений",
            "📚 Топ-10 книг для саморазвития",
            "🎓 Бесплатные курсы от лучших университетов"
        ]
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "posts": [
            "🍿 10 фильмов, которые стоит посмотреть",
            "🎮 Новые игры 2024: что поиграть",
            "🎵 Музыкальные новинки этой недели",
            "😂 Самые смешные мемы месяца",
            "📺 Лучшие сериалы для вечернего просмотра"
        ]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "posts": [
            "✨ 10 привычек успешных людей",
            "🏡 Как создать уют в доме за 1 день",
            "💃 Мода 2024: главные тренды",
            "✈️ Путешествие мечты: куда поехать",
            "🎨 Хобби, которое может приносить доход"
        ]
    }
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
class BotData:
    def __init__(self):
        self.users = {}  # user_id -> user_data
        self.channels = {}  # user_id -> [channels]
        self.auto_posting = {}  # channel_id -> auto_settings
        self.posting_tasks = {}  # channel_id -> task
        self.user_tariffs = {}  # user_id -> tariff
        self.sources = {}  # user_id -> [sources]
        
    def init_user(self, user_id: int, username: str, first_name: str):
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "username": username,
                "first_name": first_name,
                "joined": datetime.now(),
                "last_active": datetime.now()
            }
            self.user_tariffs[user_id] = "free"
            self.channels[user_id] = []
            self.sources[user_id] = []
    
    def add_channel(self, user_id: int, channel_id: str, channel_title: str):
        tariff = self.user_tariffs.get(user_id, "free")
        max_channels = TARIFFS[tariff]["max_channels"]
        
        if len(self.channels.get(user_id, [])) >= max_channels:
            return False, f"Достигнут лимит каналов для тарифа {TARIFFS[tariff]['name']} (макс: {max_channels})"
        
        if user_id not in self.channels:
            self.channels[user_id] = []
        
        # Проверяем, не добавлен ли уже
        for ch in self.channels[user_id]:
            if ch["id"] == channel_id:
                return False, "Этот канал уже добавлен"
        
        self.channels[user_id].append({
            "id": channel_id,
            "title": channel_title,
            "added": datetime.now()
        })
        return True, "Канал успешно добавлен!"
    
    def get_channels(self, user_id: int):
        return self.channels.get(user_id, [])
    
    def set_auto_posting(self, channel_id: str, user_id: int, topic: str, interval: int, is_active: bool = True):
        self.auto_posting[channel_id] = {
            "user_id": user_id,
            "topic": topic,
            "interval": interval,
            "is_active": is_active,
            "last_post": datetime.now(),
            "channel_title": self.get_channel_title(user_id, channel_id)
        }
        return True
    
    def get_channel_title(self, user_id: int, channel_id: str) -> str:
        for ch in self.channels.get(user_id, []):
            if ch["id"] == channel_id:
                return ch["title"]
        return channel_id
    
    def get_auto_settings(self, channel_id: str):
        return self.auto_posting.get(channel_id)
    
    def toggle_auto(self, channel_id: str, is_active: bool):
        if channel_id in self.auto_posting:
            self.auto_posting[channel_id]["is_active"] = is_active
            if is_active:
                self.auto_posting[channel_id]["last_post"] = datetime.now()
            return True
        return False
    
    def add_source(self, user_id: int, source_id: str, source_title: str, target_id: str):
        if user_id not in self.sources:
            self.sources[user_id] = []
        
        self.sources[user_id].append({
            "source_id": source_id,
            "source_title": source_title,
            "target_id": target_id,
            "added": datetime.now()
        })
        return True

bot_data = BotData()

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_worker(bot, channel_id: str):
    """Фоновый поток для автопостинга"""
    while True:
        try:
            settings = bot_data.get_auto_settings(channel_id)
            if not settings or not settings.get("is_active", False):
                # Если автопостинг выключен, завершаем задачу
                break
            
            current_time = datetime.now()
            last_post = settings.get("last_post", datetime.now() - timedelta(days=1))
            interval_seconds = settings.get("interval", 60)
            
            time_diff = (current_time - last_post).total_seconds()
            
            if time_diff >= interval_seconds:
                # Получаем тему
                topic = settings.get("topic", "technology")
                topic_data = TOPICS.get(topic, TOPICS["technology"])
                
                # Выбираем случайный пост из темы
                posts = topic_data.get("posts", [])
                if posts:
                    post_text = random.choice(posts)
                    
                    # Добавляем хэштеги
                    hashtags = f"\n\n#автопостинг #{topic_data['name'].replace(' ', '')} #telegram"
                    full_text = post_text + hashtags
                    
                    try:
                        # Отправляем пост
                        await bot.send_message(chat_id=channel_id, text=full_text)
                        
                        # Обновляем время последнего поста
                        settings["last_post"] = datetime.now()
                        logger.info(f"✅ Автопост отправлен в канал {channel_id}: {post_text[:50]}...")
                    except Exception as e:
                        logger.error(f"Ошибка отправки авто-поста: {e}")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(min(interval_seconds, 30))
            
        except Exception as e:
            logger.error(f"Ошибка в авто-постинге: {e}")
            await asyncio.sleep(60)

async def start_auto_posting(bot, channel_id: str):
    """Запуск автопостинга для канала"""
    if channel_id in bot_data.posting_tasks:
        # Если уже запущен, отменяем старую задачу
        old_task = bot_data.posting_tasks[channel_id]
        if not old_task.done():
            old_task.cancel()
    
    # Создаем новую задачу
    task = asyncio.create_task(auto_posting_worker(bot, channel_id))
    bot_data.posting_tasks[channel_id] = task
    return task

async def stop_auto_posting(channel_id: str):
    """Остановка автопостинга для канала"""
    if channel_id in bot_data.posting_tasks:
        task = bot_data.posting_tasks[channel_id]
        if not task.done():
            task.cancel()
        del bot_data.posting_tasks[channel_id]

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
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

async def get_channels_keyboard(user_id: int):
    channels = bot_data.get_channels(user_id)
    keyboard = []
    
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"channel_{ch['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_channels_keyboard(user_id: int):
    channels = bot_data.get_channels(user_id)
    keyboard = []
    
    for ch in channels:
        settings = bot_data.get_auto_settings(ch['id'])
        status = "✅" if settings and settings.get("is_active") else "❌"
        
        keyboard.append([
            InlineKeyboardButton(f"{status} {ch['title']}", callback_data=f"auto_channel_{ch['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_settings_keyboard(channel_id: str, current_interval: int, current_topic: str):
    keyboard = [
        [InlineKeyboardButton("🔄 Включить/Выключить", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("⏱ Изменить интервал", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str):
    keyboard = []
    for topic_key, topic_data in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(f"{topic_data['name']}", callback_data=f"set_topic_{channel_id}_{topic_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("1 минута", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("5 минут", callback_data=f"interval_{channel_id}_300")],
        [InlineKeyboardButton("10 минут", callback_data=f"interval_{channel_id}_600")],
        [InlineKeyboardButton("30 минут", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_3600")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_tariff_keyboard():
    keyboard = []
    for tariff_key, tariff_info in TARIFFS.items():
        keyboard.append([
            InlineKeyboardButton(f"{tariff_info['name']}", callback_data=f"select_tariff_{tariff_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• ⚙️ Автопостинг с интервалом от 1 минуты\n"
        f"• 🎯 6+ тем для контента\n"
        f"• 💎 Бесплатные тарифы\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал через кнопку 'Мои каналы'\n"
        f"3️⃣ Настройте автопостинг в меню\n\n"
        f"💡 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID канала или ссылку\n\n"
        "📝 Как получить ID:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "Отправьте ссылку на канал:",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    channel_id = channel_input
    if "t.me/" in channel_input:
        channel_id = "@" + channel_input.split("t.me/")[-1]
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал. Пожалуйста, отправьте ссылку на канал.")
            return
        
        success, message = bot_data.add_channel(user.id, str(chat.id), chat.title)
        
        if success:
            await update.message.reply_text(
                f"✅ *{message}*\n\n"
                f"📢 Название: {chat.title}\n"
                f"🆔 ID: {chat.id}\n\n"
                f"Теперь вы можете настроить автопостинг!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {message}", parse_mode='Markdown')
        
        context.user_data['adding_channel'] = False
        
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            f"Убедитесь что:\n"
            f"• Бот добавлен в канал\n"
            f"• Ссылка введена верно",
            parse_mode='Markdown'
        )

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Сначала добавьте канал в меню 'Мои каналы'")
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"post_to_{ch['id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['post_channel'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите пост*\n\n"
        "Отправьте текст сообщения:",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_post'] = True

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка. Начните заново /start")
        return
    
    message_text = update.message.text
    
    try:
        await context.bot.send_message(chat_id=channel_id, text=message_text)
        await update.message.reply_text(f"✅ Пост успешно опубликован в канал!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data['awaiting_post'] = False
    context.user_data['post_channel'] = None
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Сначала добавьте канал в меню 'Мои каналы'")
        return
    
    keyboard = await get_auto_channels_keyboard(query.from_user.id)
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - автопостинг активен\n"
        "❌ - автопостинг неактивен\n\n"
        "Выберите канал:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if settings:
        is_active = settings.get("is_active", False)
        interval = settings.get("interval", 60)
        topic = settings.get("topic", "technology")
        topic_name = TOPICS.get(topic, TOPICS["technology"])["name"]
    else:
        is_active = False
        interval = 60
        topic = "technology"
        topic_name = TOPICS["technology"]["name"]
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    interval_min = interval // 60
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval_min} мин\n\n"
        f"Выберите действие:"
    )
    
    keyboard = await get_auto_settings_keyboard(channel_id, interval, topic)
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if not settings:
        await query.edit_message_text("❌ Сначала настройте тему и интервал для канала")
        return
    
    is_active = not settings.get("is_active", False)
    
    if is_active:
        # Проверяем лимиты по тарифу
        user_id = settings.get("user_id")
        tariff = bot_data.user_tariffs.get(user_id, "free")
        min_interval = TARIFFS[tariff]["min_interval"]
        current_interval = settings.get("interval", 60)
        
        if current_interval < min_interval:
            await query.edit_message_text(
                f"❌ Для вашего тарифа {TARIFFS[tariff]['name']} минимальный интервал {min_interval // 60} минут\n"
                f"Установите интервал не менее {min_interval // 60} минут"
            )
            return
        
        bot_data.toggle_auto(channel_id, True)
        await start_auto_posting(context.bot, channel_id)
        await query.edit_message_text(f"✅ Автопостинг ВКЛЮЧЕН для канала {channel_id}")
    else:
        bot_data.toggle_auto(channel_id, False)
        await stop_auto_posting(channel_id)
        await query.edit_message_text(f"❌ Автопостинг ВЫКЛЮЧЕН для канала {channel_id}")
    
    await asyncio.sleep(2)
    await query.message.delete()
    await auto_posting_menu(update, context)

async def select_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    
    keyboard = await get_interval_keyboard(channel_id)
    await query.edit_message_text(
        "⏱ *Выберите интервал автопостинга:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    user_id = query.from_user.id
    tariff = bot_data.user_tariffs.get(user_id, "free")
    min_interval = TARIFFS[tariff]["min_interval"]
    
    if interval < min_interval:
        await query.edit_message_text(
            f"❌ Для вашего тарифа {TARIFFS[tariff]['name']} минимальный интервал {min_interval // 60} минут\n"
            f"Выберите другой интервал"
        )
        await asyncio.sleep(2)
        await select_interval(update, context)
        return
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["interval"] = interval
    else:
        bot_data.set_auto_posting(channel_id, user_id, "technology", interval, False)
    
    await query.edit_message_text(f"✅ Интервал установлен: {interval // 60} минут")
    await asyncio.sleep(2)
    await configure_auto(update, context)

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_", "")
    
    keyboard = await get_topics_keyboard(channel_id)
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic = parts[3]
    user_id = query.from_user.id
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["topic"] = topic
    else:
        bot_data.set_auto_posting(channel_id, user_id, topic, 60, False)
    
    topic_name = TOPICS.get(topic, TOPICS["technology"])["name"]
    await query.edit_message_text(f"✅ Тема установлена: {topic_name}")
    await asyncio.sleep(2)
    await configure_auto(update, context)

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_tariff = bot_data.user_tariffs.get(user_id, "free")
    
    text = "💎 *Доступные тарифы*\n\n"
    for tariff_key, tariff_info in TARIFFS.items():
        is_current = "✅ *Текущий* " if tariff_key == current_tariff else ""
        text += f"{is_current}{tariff_info['name']}\n"
        text += f"⏱ Минимальный интервал: {tariff_info['min_interval'] // 60} минут\n"
        text += f"📢 Максимум каналов: {tariff_info['max_channels']}\n"
        text += "📋 Возможности:\n"
        for feature in tariff_info['features']:
            text += f"{feature}\n"
        text += "\n"
    
    text += "🎁 *Все тарифы полностью бесплатны!*"
    
    keyboard = await get_tariff_keyboard()
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    bot_data.user_tariffs[user_id] = tariff_key
    
    await query.edit_message_text(
        f"✅ *Тариф обновлен!*\n\n"
        f"Ваш новый тариф: {TARIFFS[tariff_key]['name']}\n\n"
        f"Теперь доступны новые возможности!",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(user_id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot_data.users.get(user_id, {})
    tariff = bot_data.user_tariffs.get(user_id, "free")
    channels = bot_data.get_channels(user_id)
    
    # Считаем активные автопостинги
    active_auto = 0
    for ch in channels:
        settings = bot_data.get_auto_settings(ch['id'])
        if settings and settings.get("is_active"):
            active_auto += 1
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 Имя: {user.get('first_name', 'Unknown')}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n"
        f"📢 Каналов: {len(channels)}/{TARIFFS[tariff]['max_channels']}\n"
        f"⚙️ Активных автопостингов: {active_auto}\n"
        f"📅 В системе с: {user.get('joined', datetime.now()).strftime('%d.%m.%Y')}\n\n"
        f"Для смены тарифа используйте меню 'Тарифы'"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    channels = bot_data.get_channels(user_id)
    auto_settings = bot_data.auto_posting
    
    auto_for_user = [s for s in auto_settings.values() if s.get("user_id") == user_id]
    active_auto = [s for s in auto_for_user if s.get("is_active")]
    
    text = (
        f"📊 *Ваша статистика*\n\n"
        f"📢 Всего каналов: {len(channels)}\n"
        f"⚙️ Настроено автопостингов: {len(auto_for_user)}\n"
        f"✅ Активных автопостингов: {len(active_auto)}\n\n"
        f"💡 *Совет:*\n"
        f"• Используйте разные темы для контента\n"
        f"• Настройте оптимальный интервал\n"
        f"• Чем чаще посты, тем активнее аудитория!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено")
    
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "write_post":
        await write_post(update, context)
    elif data == "my_channels":
        keyboard = await get_channels_keyboard(query.from_user.id)
        await query.edit_message_text("📢 *Ваши каналы*", parse_mode='Markdown', reply_markup=keyboard)
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "reposts_menu":
        await query.edit_message_text("🔄 Репосты будут доступны в следующей версии", parse_mode='Markdown')
    elif data == "help":
        help_text = (
            "ℹ️ *Помощь*\n\n"
            "📋 *Как пользоваться:*\n\n"
            "1️⃣ *Добавьте бота в канал*\n"
            "2️⃣ *Добавьте канал в бота* - 'Мои каналы'\n"
            "3️⃣ *Настройте автопостинг* - выберите тему и интервал\n"
            "4️⃣ *Включите автопостинг*\n\n"
            "⏱ *Интервалы:*\n"
            "• 1 минута - для PRO тарифа\n"
            "• 5-30 минут - для всех тарифов\n\n"
            "💡 *Советы:*\n"
            "• Для каналов с аудиторией лучше интервал 30-60 минут\n"
            "• Используйте разные темы для разных каналов\n"
            "• Контент генерируется автоматически!"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    elif data.startswith("post_to_"):
        await send_post(update, context)
    elif data.startswith("auto_channel_"):
        await configure_auto(update, context)
    elif data.startswith("toggle_auto_"):
        await toggle_auto(update, context)
    elif data.startswith("change_interval_"):
        await select_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("select_topic_"):
        await select_topic(update, context)
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Добавление канала
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
        else (handle_post(u, c) if c.user_data.get('awaiting_post')
        else None)
    ))
    
    # Callback
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот для автопостинга запущен!")
    logger.info("✅ Автопостинг работает с интервалом от 1 минуты")
    logger.info("💎 Все тарифы бесплатны!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
