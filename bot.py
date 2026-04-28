import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from threading import Thread

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

# ==================== ХРАНИЛИЩЕ ДАННЫХ В ПАМЯТИ ====================
class Storage:
    def __init__(self):
        self.users = {}  # user_id: user_data
        self.channels = {}  # user_id: [channels]
        self.sources = {}  # user_id: [sources]
        self.posts = {}  # user_id: [posts]
        self.auto_posting = {}  # channel_id: auto_settings
        self.subscriptions = {}  # user_id: tariff_data
        
    def get_user(self, user_id):
        if user_id not in self.users:
            self.users[user_id] = {
                'username': '',
                'first_name': '',
                'joined_date': datetime.now(),
                'last_active': datetime.now()
            }
        return self.users[user_id]
    
    def get_channels(self, user_id):
        if user_id not in self.channels:
            self.channels[user_id] = []
        return self.channels[user_id]
    
    def add_channel(self, user_id, channel_id, channel_title, channel_username):
        channels = self.get_channels(user_id)
        # Проверяем, нет ли уже такого канала
        for ch in channels:
            if ch['channel_id'] == channel_id:
                return False
        channels.append({
            'channel_id': channel_id,
            'channel_title': channel_title,
            'channel_username': channel_username,
            'added_date': datetime.now(),
            'status': 'active'
        })
        return True
    
    def get_sources(self, user_id):
        if user_id not in self.sources:
            self.sources[user_id] = []
        return self.sources[user_id]
    
    def add_source(self, user_id, source_id, source_title, target_channel):
        sources = self.get_sources(user_id)
        sources.append({
            'source_id': source_id,
            'source_title': source_title,
            'target_channel': target_channel,
            'is_active': True,
            'added_date': datetime.now()
        })
    
    def add_post(self, user_id, channel_id, content, media_id=None, media_type=None):
        if user_id not in self.posts:
            self.posts[user_id] = []
        self.posts[user_id].append({
            'channel_id': channel_id,
            'content': content,
            'media_id': media_id,
            'media_type': media_type,
            'posted_time': datetime.now(),
            'status': 'posted'
        })
    
    def get_auto_settings(self, channel_id):
        return self.auto_posting.get(channel_id)
    
    def set_auto_settings(self, channel_id, user_id, settings):
        self.auto_posting[channel_id] = {
            'user_id': user_id,
            **settings
        }
    
    def delete_auto_settings(self, channel_id):
        if channel_id in self.auto_posting:
            del self.auto_posting[channel_id]
    
    def get_subscription(self, user_id):
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {
                'tariff': 'free',
                'start_date': datetime.now(),
                'end_date': datetime.now() + timedelta(days=30),
                'max_channels': 2,
                'repost_limit': 20,
                'post_interval': 60  # минимальный интервал 1 минута
            }
        return self.subscriptions[user_id]
    
    def update_subscription(self, user_id, tariff):
        tariff_config = TARIFFS[tariff]
        self.subscriptions[user_id] = {
            'tariff': tariff,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=30),
            'max_channels': tariff_config['max_channels'],
            'repost_limit': tariff_config['repost_limit'],
            'post_interval': tariff_config['post_interval']
        }

storage = Storage()

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "price": "0 ₽",
        "max_channels": 2,
        "repost_limit": 20,
        "post_interval": 300,  # 5 минут
        "features": [
            "✅ 2 канала для постинга",
            "✅ 20 репостов в день",
            "✅ Интервал от 5 минут",
            "✅ Ручной постинг",
            "✅ Базовые темы"
        ]
    },
    "basic": {
        "name": "📘 Базовый",
        "price": "0 ₽",
        "max_channels": 5,
        "repost_limit": 100,
        "post_interval": 60,  # 1 минута
        "features": [
            "✅ До 5 каналов",
            "✅ 100 репостов в день",
            "✅ Интервал от 1 минуты",
            "✅ Автопостинг",
            "✅ 10 тем для контента",
            "✅ Репосты из источников"
        ]
    },
    "pro": {
        "name": "💎 PRO",
        "price": "0 ₽",
        "max_channels": 15,
        "repost_limit": 500,
        "post_interval": 30,  # 30 секунд
        "features": [
            "✅ До 15 каналов",
            "✅ 500 репостов в день",
            "✅ Интервал от 30 секунд",
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
        "templates": [
            "🔬 {emoji} Интересный факт о технологиях: {fact}\n\n#технологии #it",
            "🚀 {emoji} Новинка в мире IT: {fact}\n\n#технологии #инновации",
            "💡 {emoji} Лайфхак для программистов: {fact}\n\n#программирование #лайфхак"
        ],
        "facts": [
            "Первый компьютер весил более 27 тонн!",
            "Современный смартфон мощнее компьютеров 90-х в тысячи раз",
            "Python - один из самых популярных языков программирования",
            "Искусственный интеллект уже пишет код лучше некоторых программистов"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "templates": [
            "💼 {emoji} Бизнес-совет дня: {fact}\n\n#бизнес #успех",
            "📈 {emoji} Как увеличить продажи: {fact}\n\n#маркетинг #бизнес",
            "🎯 {emoji} Секрет успешных предпринимателей: {fact}\n\n#мотивация #бизнес"
        ],
        "facts": [
            "80% бизнеса закрываются в первый год",
            "Лучший способ удержать клиента - качественный сервис",
            "Социальные сети - главный канал продвижения сегодня",
            "Автоматизация увеличивает прибыль на 40%"
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "templates": [
            "🏃 {emoji} Совет для здоровья: {fact}\n\n#здоровье #советы",
            "🥗 {emoji} Правильное питание: {fact}\n\n#зож #питание",
            "🧘 {emoji} Забота о себе: {fact}\n\n#здоровье #wellness"
        ],
        "facts": [
            "Утренняя зарядка продлевает жизнь на 5 лет",
            "Вода - основа здоровья, пейте 2 литра в день",
            "Сон 7-8 часов необходим для восстановления",
            "Стресс - главный враг иммунитета"
        ]
    },
    "education": {
        "name": "📚 Образование",
        "templates": [
            "🎓 {emoji} Полезный факт: {fact}\n\n#образование #обучение",
            "📖 {emoji} Знания - сила: {fact}\n\n#саморазвитие #навыки",
            "💡 {emoji} Интересно знать: {fact}\n\n#образование #факты"
        ],
        "facts": [
            "Чтение развивает мозг и повышает IQ",
            "Изучение языков снижает риск деменции",
            "Лучшее время для учебы - утро",
            "Практика важнее теории в 10 раз"
        ]
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "templates": [
            "😄 {emoji} Прикол дня: {fact}\n\n#юмор #развлечения",
            "🎮 {emoji} Факт из мира игр: {fact}\n\n#игры #гики",
            "🎥 {emoji} Кино-лайфхак: {fact}\n\n#кино #развлечения"
        ],
        "facts": [
            "Смех продлевает жизнь и снимает стресс",
            "Minecraft - самая продаваемая игра в истории",
            "Самый длинный фильм длится 10 часов",
            "Мемы стали частью современной культуры"
        ]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "templates": [
            "✨ {emoji} Лайфхак для жизни: {fact}\n\n#лайфхак #советы",
            "💪 {emoji} Полезный совет: {fact}\n\n#жизнь #мотивация",
            "🎯 {emoji} Секрет успеха: {fact}\n\n#успех #жизнь"
        ],
        "facts": [
            "Ведите список дел - это повышает продуктивность",
            "Медитация улучшает концентрацию на 30%",
            "Путешествия расширяют кругозор",
            "Хобби делает жизнь интереснее"
        ]
    },
    "motivation": {
        "name": "💪 Мотивация",
        "templates": [
            "🔥 {emoji} Мотивация на сегодня: {fact}\n\n#мотивация #успех",
            "⭐ {emoji} Вдохновение: {fact}\n\n#вдохновение #цели",
            "🚀 {emoji} Действуй сегодня: {fact}\n\n#мотивация #развитие"
        ],
        "facts": [
            "Успех приходит к тем, кто не сдается",
            "Каждый день - новая возможность",
            "Верьте в себя и у вас все получится",
            "Маленькие шаги ведут к большим целям"
        ]
    }
}

# ==================== АВТОПОСТИНГ ====================
import random

async def auto_posting_worker():
    """Фоновый процесс автопостинга"""
    while True:
        try:
            current_time = datetime.now()
            
            # Перебираем все настройки автопостинга
            for channel_id, settings in list(storage.auto_posting.items()):
                if not settings.get('is_active', False):
                    continue
                
                # Проверяем интервал
                last_post = settings.get('last_post_time')
                interval_minutes = settings.get('interval', 60)  # интервал в минутах
                
                if last_post:
                    time_diff = (current_time - last_post).total_seconds() / 60
                    if time_diff < interval_minutes:
                        continue
                
                # Получаем тему
                topic = settings.get('topic')
                if not topic or topic not in TOPICS:
                    continue
                
                # Получаем информацию о пользователе
                user_id = settings.get('user_id')
                if not user_id:
                    continue
                
                # Генерируем пост
                post_content = generate_post_content(topic)
                
                # Отправляем пост
                try:
                    # Получаем application из глобальной переменной
                    from telegram.ext import Application
                    # Нужно хранить application в глобальной переменной
                    if 'app' in globals():
                        await app.bot.send_message(chat_id=channel_id, text=post_content)
                        
                        # Обновляем время последнего поста
                        settings['last_post_time'] = datetime.now()
                        storage.set_auto_settings(channel_id, user_id, settings)
                        
                        # Сохраняем пост в историю
                        storage.add_post(user_id, channel_id, post_content)
                        
                        logger.info(f"Автопост отправлен в канал {channel_id}")
                except Exception as e:
                    logger.error(f"Ошибка автопостинга в {channel_id}: {e}")
            
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
        except Exception as e:
            logger.error(f"Ошибка в автопостинге: {e}")
            await asyncio.sleep(60)

def generate_post_content(topic_key):
    """Генерация контента для поста"""
    topic = TOPICS[topic_key]
    
    # Выбираем случайный шаблон и факт
    template = random.choice(topic['templates'])
    fact = random.choice(topic['facts'])
    
    # Случайные эмодзи для разнообразия
    emojis = ['✨', '⭐', '🌟', '💫', '⚡', '🔥', '💪', '🎯', '📌', '💡']
    emoji = random.choice(emojis)
    
    # Формируем пост
    post = template.format(emoji=emoji, fact=fact)
    
    return post

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    """Главная клавиатура"""
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
    """Клавиатура со списком каналов"""
    channels = storage.get_channels(user_id)
    
    keyboard = []
    for channel in channels:
        if channel['status'] == 'active':
            keyboard.append([
                InlineKeyboardButton(f"📢 {channel['channel_title']}", callback_data=f"channel_{channel['channel_id']}")
            ])
    
    if not channels:
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_channels_keyboard(user_id: int):
    """Клавиатура для выбора канала автопостинга"""
    channels = storage.get_channels(user_id)
    
    keyboard = []
    for channel in channels:
        if channel['status'] == 'active':
            settings = storage.get_auto_settings(channel['channel_id'])
            status = "✅" if settings and settings.get('is_active') else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {channel['channel_title']}", 
                    callback_data=f"auto_channel_{channel['channel_id']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str):
    """Клавиатура выбора темы"""
    keyboard = []
    for topic_key, topic_info in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(f"{topic_info['name']}", callback_data=f"set_topic_{channel_id}_{topic_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str, current_interval: int):
    """Клавиатура выбора интервала"""
    intervals = [1, 5, 10, 15, 30, 60, 120, 240]  # минуты
    keyboard = []
    row = []
    
    for interval in intervals:
        text = f"{interval} мин"
        if interval == current_interval:
            text = f"✅ {text}"
        row.append(InlineKeyboardButton(text, callback_data=f"interval_{channel_id}_{interval}"))
        
        if len(row) == 4:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Регистрируем пользователя
    storage.get_user(user.id)
    storage.get_subscription(user.id)
    
    welcome_text = (
        f"✨ *Добро пожаловать, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автоматического постинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Писать посты в каналы\n"
        f"• 🔄 Делать репосты\n"
        f"• ⚙️ Автопостинг с интервалом от 1 минуты\n"
        f"• 🎯 8 тем для генерации контента\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал через меню 'Мои каналы'\n"
        f"3️⃣ Настройте автопостинг!\n\n"
        f"💎 *Все тарифы бесплатны!*\n"
        f"⚡ *Минимальный интервал: от 30 секунд на PRO тарифе*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления канала"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    subscription = storage.get_subscription(user.id)
    channels = storage.get_channels(user.id)
    active_channels = [ch for ch in channels if ch['status'] == 'active']
    
    if len(active_channels) >= subscription['max_channels']:
        tariff_name = TARIFFS[subscription['tariff']]['name']
        await query.edit_message_text(
            f"❌ *Достигнут лимит каналов!*\n\n"
            f"Ваш тариф: {tariff_name}\n"
            f"Максимум: {subscription['max_channels']} каналов\n\n"
            f"Чтобы добавить больше каналов, перейдите на другой тариф в меню 'Тарифы'",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID канала или ссылку\n\n"
        "📝 *Как получить ID канала:*\n"
        "• Форвардните любое сообщение из канала боту\n"
        "• Или отправьте ссылку: `@channel_username`\n"
        "• Или: `https://t.me/channel_username`\n\n"
        "Отправьте ссылку на канал:",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    # Извлекаем ID канала
    channel_username = None
    if "t.me/" in channel_input:
        channel_username = channel_input.split("t.me/")[-1]
        if "/" in channel_username:
            channel_username = channel_username.split("/")[0]
        channel_id = f"@{channel_username}"
    elif channel_input.startswith("@"):
        channel_username = channel_input[1:]
        channel_id = channel_input
    else:
        channel_id = channel_input
    
    try:
        # Получаем информацию о канале
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал. Отправьте ссылку на канал.")
            return
        
        # Сохраняем канал
        if storage.add_channel(user.id, str(chat.id), chat.title, channel_username or ""):
            await update.message.reply_text(
                f"✅ *Канал добавлен!*\n\n"
                f"📢 Название: {chat.title}\n"
                f"🆔 ID: {chat.id}\n\n"
                f"Теперь вы можете настраивать автопостинг!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Этот канал уже добавлен!")
        
        context.user_data['adding_channel'] = False
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            f"Убедитесь что:\n"
            f"• Бот добавлен в канал как администратор\n"
            f"• Ссылка на канал правильная",
            parse_mode='Markdown'
        )

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Написать пост"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    channels = storage.get_channels(user.id)
    active_channels = [ch for ch in channels if ch['status'] == 'active']
    
    if not active_channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через меню 'Мои каналы'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel in active_channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel['channel_title']}", callback_data=f"select_channel_{channel['channel_id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация поста"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_channel_", "")
    context.user_data['post_channel_id'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите пост*\n\n"
        "Отправьте текст, фото или видео с подписью\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_post'] = True

async def handle_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка контента для поста"""
    user = update.effective_user
    channel_id = context.user_data.get('post_channel_id')
    
    if not channel_id:
        await update.message.reply_text("❌ Сессия истекла")
        return
    
    # Получаем текст
    caption = None
    media_id = None
    media_type = None
    
    if update.message.text:
        caption = update.message.text
    elif update.message.caption:
        caption = update.message.caption
        if update.message.photo:
            media_id = update.message.photo[-1].file_id
            media_type = 'photo'
        elif update.message.video:
            media_id = update.message.video.file_id
            media_type = 'video'
    elif update.message.photo:
        media_id = update.message.photo[-1].file_id
        media_type = 'photo'
    elif update.message.video:
        media_id = update.message.video.file_id
        media_type = 'video'
    
    try:
        # Отправляем пост
        if media_id and media_type == 'photo':
            await context.bot.send_photo(chat_id=channel_id, photo=media_id, caption=caption or "")
        elif media_id and media_type == 'video':
            await context.bot.send_video(chat_id=channel_id, video=media_id, caption=caption or "")
        else:
            await context.bot.send_message(chat_id=channel_id, text=caption or "")
        
        # Сохраняем в историю
        storage.add_post(user.id, channel_id, caption or "", media_id, media_type)
        
        await update.message.reply_text("✅ *Пост опубликован!*", parse_mode='Markdown')
        
        context.user_data['awaiting_post'] = False
        context.user_data['post_channel_id'] = None
        
        # Показываем меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='Markdown')

async def setup_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка автопостинга"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    channels = storage.get_channels(user.id)
    active_channels = [ch for ch in channels if ch['status'] == 'active']
    
    if not active_channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_auto_channels_keyboard(user.id)
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - автопостинг активен\n"
        "❌ - автопостинг неактивен\n\n"
        "Выберите канал:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_auto_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Конфигурация автопостинга для канала"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    context.user_data['auto_channel_id'] = channel_id
    
    settings = storage.get_auto_settings(channel_id)
    
    is_active = settings.get('is_active', False) if settings else False
    topic = settings.get('topic', 'technology') if settings else 'technology'
    interval = settings.get('interval', 60) if settings else 60
    
    topic_name = TOPICS.get(topic, TOPICS['technology'])['name']
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    
    # Получаем информацию о канале
    channels = storage.get_channels(query.from_user.id)
    channel_title = channel_id
    for ch in channels:
        if ch['channel_id'] == channel_id:
            channel_title = ch['channel_title']
            break
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_title}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval} минут\n\n"
        f"Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 {'Выключить' if is_active else 'Включить'}", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал постинга", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_topic_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор темы"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_", "")
    keyboard = await get_topics_keyboard(channel_id)
    
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*\n\n"
        "Посты будут генерироваться на выбранную тему",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка темы"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic_key = parts[3]
    
    # Получаем текущие настройки
    settings = storage.get_auto_settings(channel_id) or {}
    settings['topic'] = topic_key
    settings['user_id'] = query.from_user.id
    
    storage.set_auto_settings(channel_id, query.from_user.id, settings)
    
    topic_name = TOPICS[topic_key]['name']
    
    await query.edit_message_text(
        f"✅ *Тема установлена!*\n\n"
        f"📝 Тема: {topic_name}\n\n"
        f"Теперь включите автопостинг",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение интервала"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    settings = storage.get_auto_settings(channel_id) or {}
    current_interval = settings.get('interval', 60)
    
    keyboard = await get_interval_keyboard(channel_id, current_interval)
    
    await query.edit_message_text(
        "⏱ *Выберите интервал между постами:*\n\n"
        "Чем меньше интервал, тем чаще будут публиковаться посты",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка интервала"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    # Получаем подписку пользователя
    subscription = storage.get_subscription(query.from_user.id)
    min_interval = subscription['post_interval']
    
    if interval < min_interval:
        await query.edit_message_text(
            f"❌ *Интервал {interval} минут недоступен для вашего тарифа!*\n\n"
            f"Минимальный интервал: {min_interval} минут\n\n"
            f"Чтобы уменьшить интервал, перейдите на другой тариф",
            parse_mode='Markdown'
        )
        await asyncio.sleep(3)
        await change_interval(update, context)
        return
    
    # Обновляем интервал
    settings = storage.get_auto_settings(channel_id) or {}
    settings['interval'] = interval
    settings['user_id'] = query.from_user.id
    
    storage.set_auto_settings(channel_id, query.from_user.id, settings)
    
    await query.edit_message_text(
        f"✅ *Интервал установлен!*\n\n"
        f"⏱ Интервал: {interval} минут\n\n"
        f"Посты будут публиковаться каждые {interval} минут",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def toggle_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение автопостинга"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    
    settings = storage.get_auto_settings(channel_id)
    
    if not settings or not settings.get('topic'):
        await query.edit_message_text(
            "❌ *Сначала выберите тему для автопостинга!*",
            parse_mode='Markdown'
        )
        await asyncio.sleep(2)
        await select_topic_for_channel(update, context)
        return
    
    current_status = settings.get('is_active', False)
    new_status = not current_status
    
    settings['is_active'] = new_status
    if new_status:
        settings['last_post_time'] = datetime.now() - timedelta(minutes=settings.get('interval', 60))
    
    storage.set_auto_settings(channel_id, query.from_user.id, settings)
    
    status_text = "включен" if new_status else "выключен"
    await query.edit_message_text(f"✅ *Автопостинг {status_text}!*", parse_mode='Markdown')
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    subscription = storage.get_subscription(user.id)
    current_tariff = subscription['tariff']
    
    text = "💎 *Доступные тарифы*\n\n"
    
    for tariff_key, tariff_info in TARIFFS.items():
        is_current = "✅ *ТЕКУЩИЙ* " if tariff_key == current_tariff else ""
        text += f"{is_current}{tariff_info['name']}\n"
        text += f"💰 {tariff_info['price']}\n"
        text += "📋 Возможности:\n"
        for feature in tariff_info['features']:
            text += f"{feature}\n"
        text += "\n"
    
    keyboard = []
    for tariff_key in TARIFFS:
        if tariff_key != current_tariff:
            keyboard.append([InlineKeyboardButton(f"Выбрать {TARIFFS[tariff_key]['name']}", callback_data=f"select_tariff_{tariff_key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор тарифа"""
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    storage.update_subscription(user_id, tariff_key)
    
    await query.edit_message_text(
        f"✅ *Тариф обновлен!*\n\n"
        f"Ваш новый тариф: {TARIFFS[tariff_key]['name']}\n"
        f"Минимальный интервал: {TARIFFS[tariff_key]['post_interval']} минут\n\n"
        f"Теперь вам доступны новые возможности!",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    
    keyboard = await get_main_keyboard(user_id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = storage.get_user(user.id)
    subscription = storage.get_subscription(user.id)
    channels = storage.get_channels(user.id)
    active_channels = [ch for ch in channels if ch['status'] == 'active']
    posts = storage.posts.get(user.id, [])
    
    tariff_info = TARIFFS[subscription['tariff']]
    
    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 Имя: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'нет'}\n\n"
        f"💎 Тариф: {tariff_info['name']}\n"
        f"📊 Статистика:\n"
        f"• Каналов: {len(active_channels)}/{subscription['max_channels']}\n"
        f"• Постов: {len(posts)}\n"
        f"• Автопостинг: {len(storage.auto_posting)} каналов\n\n"
        f"⚡ Минимальный интервал: {subscription['post_interval']} минут\n"
        f"📅 В системе с: {user_data['joined_date'].strftime('%d.%m.%Y')}\n"
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
    posts = storage.posts.get(user.id, [])
    channels = storage.get_channels(user.id)
    
    # Статистика по дням
    today = datetime.now().date()
    posts_today = sum(1 for p in posts if p['posted_time'].date() == today)
    posts_week = sum(1 for p in posts if p['posted_time'] >= datetime.now() - timedelta(days=7))
    posts_month = sum(1 for p in posts if p['posted_time'] >= datetime.now() - timedelta(days=30))
    
    # Посты по каналам
    channels_stats = {}
    for post in posts:
        ch_id = post['channel_id']
        if ch_id not in channels_stats:
            channels_stats[ch_id] = 0
        channels_stats[ch_id] += 1
    
    stats_text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 *Посты:*\n"
        f"• Сегодня: {posts_today}\n"
        f"• За неделю: {posts_week}\n"
        f"• За месяц: {posts_month}\n"
        f"• Всего: {len(posts)}\n\n"
    )
    
    if channels_stats:
        stats_text += "📢 *По каналам:*\n"
        for ch_id, count in channels_stats.items():
            # Находим название канала
            channel_title = ch_id
            for ch in channels:
                if ch['channel_id'] == ch_id:
                    channel_title = ch['channel_title']
                    break
            stats_text += f"• {channel_title}: {count} постов\n"
    
    # Информация об автопостинге
    auto_channels = []
    for ch_id, settings in storage.auto_posting.items():
        if settings.get('user_id') == user.id and settings.get('is_active'):
            for ch in channels:
                if ch['channel_id'] == ch_id:
                    auto_channels.append(f"• {ch['channel_title']} (каждые {settings.get('interval', 60)} мин)")
                    break
    
    if auto_channels:
        stats_text += f"\n⚙️ *Активный автопостинг:*\n"
        stats_text += "\n".join(auto_channels)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    context.user_data.clear()
    await update.message.reply_text("❌ *Действие отменено*", parse_mode='Markdown')
    
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ОБРАБОТЧИК CALLBACK ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик callback"""
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
            "📋 *Как пользоваться:*\n\n"
            "1️⃣ *Добавьте канал*\n"
            "• Добавьте бота в канал как администратора\n"
            "• В меню 'Мои каналы' ➕ 'Добавить канал'\n\n"
            "2️⃣ *Настройте автопостинг*\n"
            "• В меню 'Автопостинг' выберите канал\n"
            "• Выберите тему для контента\n"
            "• Установите интервал (от 1 минуты)\n"
            "• Включите автопостинг\n\n"
            "3️⃣ *Публикуйте вручную*\n"
            "• 'Написать пост' ➡️ выберите канал\n"
            "• Отправьте текст, фото или видео\n\n"
            "💡 *Советы:*\n"
            "• Автопостинг работает автоматически\n"
            "• Контент генерируется сам\n"
            "• Можно настроить несколько каналов\n\n"
            "⚡ *Интервалы:*\n"
            "• Бесплатный: от 5 минут\n"
            "• Базовый: от 1 минуты\n"
            "• PRO: от 30 секунд\n\n"
            "❓ Вопросы: @support_bot"
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
    elif data.startswith("change_interval_"):
        await change_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК ====================
async def main():
    """Запуск бота"""
    global app
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel') 
        else (handle_post_content(u, c) if c.user_data.get('awaiting_post')
        else None)
    ))
    
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        handle_post_content
    ))
    
    # Callback обработчики
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаем фоновый процесс автопостинга
    asyncio.create_task(auto_posting_worker())
    
    logger.info("🚀 Бот запущен!")
    logger.info("⚡ Автопостинг активен")
    logger.info("⏱ Минимальный интервал: 30 секунд")
    logger.info("💎 Все тарифы бесплатны!")
    
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())
