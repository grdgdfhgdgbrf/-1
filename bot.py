import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
from pathlib import Path

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

# Файлы для хранения данных
DATA_DIR = Path("bot_data")
DATA_DIR.mkdir(exist_ok=True)
CHANNELS_FILE = DATA_DIR / "channels.json"
AUTOPOST_FILE = DATA_DIR / "autopost.json"
SOURCES_FILE = DATA_DIR / "sources.json"
POSTS_FILE = DATA_DIR / "posts.json"
USERS_FILE = DATA_DIR / "users.json"

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 2,
        "repost_limit": 20,
        "min_interval": 60,  # 1 минута в секундах
        "features": ["✅ 2 канала", "✅ Интервал от 1 мин", "✅ 20 репостов/день"]
    },
    "basic": {
        "name": "📘 Базовый", 
        "max_channels": 5,
        "repost_limit": 100,
        "min_interval": 30,  # 30 секунд
        "features": ["✅ 5 каналов", "✅ Интервал от 30 сек", "✅ 100 репостов/день"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 15,
        "repost_limit": 500,
        "min_interval": 10,  # 10 секунд
        "features": ["✅ 15 каналов", "✅ Интервал от 10 сек", "✅ 500 репостов/день"]
    }
}

# ==================== ТЕМЫ ДЛЯ КОНТЕНТА ====================
POST_TEMPLATES = {
    "technology": {
        "name": "💻 Технологии",
        "templates": [
            "🔥 Новинка! {topic} уже здесь. Рассказываем, как это изменит мир технологий!",
            "🤖 Искусственный интеллект в {topic} - прорыв года! Узнайте подробности.",
            "💡 {topic} - технология будущего. Почему это важно прямо сейчас?",
            "📱 Как {topic} влияет на повседневную жизнь? Разбираемся вместе!",
            "⚡ Срочно! {topic} представляет инновационное решение для всех!"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "templates": [
            "💼 {topic} - ключ к успешному бизнесу. 5 советов для роста!",
            "📈 Тренд года: {topic}. Как заработать на этом?",
            "💰 {topic} приносит прибыль уже сегодня. Инструкция внутри!",
            "🎯 Стратегия {topic} - путь к миллиону. Начни сейчас!",
            "🚀 {topic} взрывает рынок! Успейте войти в тренд."
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "templates": [
            "🏃‍♂️ {topic} - простой способ улучшить здоровье уже сегодня!",
            "🥗 Питание и {topic}: что нужно знать каждому?",
            "💪 {topic} для активной жизни. Начни с малого!",
            "🧘‍♀️ {topic} и ментальное здоровье - важная связь.",
            "🌿 Натуральные методы {topic} - работающие советы."
        ]
    },
    "motivation": {
        "name": "💪 Мотивация",
        "templates": [
            "✨ {topic} - твой путь к успеху. Сделай первый шаг сегодня!",
            "🌟 Вдохновение дня: {topic} изменит твою жизнь!",
            "🎯 {topic} - сила внутри тебя. Поверь в себя!",
            "🔥 Цитата дня о {topic} - то, что нужно услышать каждому.",
            "⭐ {topic} начинается с маленьких побед. Ты сможешь!"
        ]
    },
    "news": {
        "name": "📰 Новости",
        "templates": [
            "📢 Срочно! {topic} - главная новость этого часа!",
            "🌍 Мир меняется: {topic} обсуждают все!",
            "🔴 Прямо сейчас: {topic} - будьте в курсе!",
            "📡 Важные изменения в {topic} - что это значит для вас?",
            "🎬 {topic} - событие, которое нельзя пропустить!"
        ]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "templates": [
            "✨ {topic} - добавь стиля в свою жизнь!",
            "🌟 Твой идеальный {topic} - 5 простых шагов.",
            "💫 {topic} для успешных людей - попробуй сейчас!",
            "🎨 Креативный подход к {topic} - вдохновляйся!",
            "⭐ {topic} - создай свою лучшую жизнь!"
        ]
    }
}

# ==================== РАБОТА С ХРАНИЛИЩЕМ ====================
class Storage:
    @staticmethod
    def load_data(file_path):
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_data(file_path, data):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== БОТ ====================
class PostingBot:
    def __init__(self):
        self.bot = None
        self.posting_tasks = {}
        self.running = True
        
    def load_channels(self, user_id=None):
        data = Storage.load_data(CHANNELS_FILE)
        if user_id:
            return data.get(str(user_id), [])
        return data
    
    def save_channels(self, user_id, channels):
        data = Storage.load_data(CHANNELS_FILE)
        data[str(user_id)] = channels
        Storage.save_data(CHANNELS_FILE, data)
    
    def load_autopost(self, channel_id=None):
        data = Storage.load_data(AUTOPOST_FILE)
        if channel_id:
            return data.get(str(channel_id))
        return data
    
    def save_autopost(self, channel_id, settings):
        data = Storage.load_data(AUTOPOST_FILE)
        data[str(channel_id)] = settings
        Storage.save_data(AUTOPOST_FILE, data)
    
    def delete_autopost(self, channel_id):
        data = Storage.load_data(AUTOPOST_FILE)
        if str(channel_id) in data:
            del data[str(channel_id)]
            Storage.save_data(AUTOPOST_FILE, data)
    
    def load_sources(self, user_id=None):
        data = Storage.load_data(SOURCES_FILE)
        if user_id:
            return data.get(str(user_id), [])
        return data
    
    def save_source(self, user_id, source):
        data = Storage.load_data(SOURCES_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = []
        data[str(user_id)].append(source)
        Storage.save_data(SOURCES_FILE, data)
    
    def load_posts(self, user_id=None):
        data = Storage.load_data(POSTS_FILE)
        if user_id:
            return data.get(str(user_id), [])
        return data
    
    def save_post(self, user_id, post):
        data = Storage.load_data(POSTS_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = []
        data[str(user_id)].append(post)
        Storage.save_data(POSTS_FILE, data)
    
    def get_user_tariff(self, user_id):
        data = Storage.load_data(USERS_FILE)
        user_data = data.get(str(user_id), {})
        return user_data.get('tariff', 'free')
    
    def set_user_tariff(self, user_id, tariff):
        data = Storage.load_data(USERS_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = {}
        data[str(user_id)]['tariff'] = tariff
        Storage.save_data(USERS_FILE, data)
    
    def can_add_channel(self, user_id):
        tariff = self.get_user_tariff(user_id)
        max_channels = TARIFFS[tariff]['max_channels']
        current_channels = len(self.load_channels(user_id))
        return current_channels < max_channels

bot_manager = PostingBot()

# ==================== ГЕНЕРАЦИЯ КОНТЕНТА ====================
def generate_post(topic, user_id=None):
    """Генерация поста на основе темы"""
    topic_data = POST_TEMPLATES.get(topic, POST_TEMPLATES["news"])
    template = random.choice(topic_data["templates"])
    
    # Темы для подстановки
    subtopics = {
        "technology": ["нейросети", "робототехника", "IT-инновации", "цифровизация", "автоматизация"],
        "business": ["инвестиции", "стартапы", "маркетинг", "управление", "продажи"],
        "health": ["фитнес", "питание", "сон", "стрессоустойчивость", "иммунитет"],
        "motivation": ["успех", "развитие", "достижения", "цели", "мечты"],
        "news": ["события", "открытия", "достижения", "тренды", "обновления"],
        "lifestyle": ["хобби", "творчество", "путешествия", "общение", "развитие"]
    }
    
    subtopic_list = subtopics.get(topic, subtopics["news"])
    topic_name = random.choice(subtopic_list)
    
    post_text = template.format(topic=topic_name)
    
    # Добавляем хэштеги
    hashtags = f"\n\n#пост #контент #{topic}"
    post_text += hashtags
    
    return post_text

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_loop(user_id: int, channel_id: str, channel_title: str, topic: str, interval: int):
    """Цикл автопостинга"""
    logger.info(f"Запущен автопостинг для канала {channel_title} (интервал {interval} сек)")
    
    while bot_manager.running:
        try:
            # Проверяем, активен ли автопостинг
            settings = bot_manager.load_autopost(channel_id)
            if not settings or not settings.get('active', False):
                logger.info(f"Автопостинг для {channel_title} остановлен")
                break
            
            # Генерируем пост
            post_text = generate_post(topic, user_id)
            
            # Отправляем пост
            await bot_manager.bot.send_message(chat_id=channel_id, text=post_text)
            
            # Сохраняем информацию о посте
            post_info = {
                'channel_id': channel_id,
                'channel_title': channel_title,
                'topic': topic,
                'text': post_text,
                'time': datetime.now().isoformat()
            }
            bot_manager.save_post(user_id, post_info)
            
            logger.info(f"Опубликован пост в {channel_title} на тему {topic}")
            
            # Ждем следующий пост
            await asyncio.sleep(interval)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Ошибка автопостинга для {channel_title}: {e}")
            await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    logger.info(f"Автопостинг для {channel_title} завершен")

async def start_auto_posting(user_id: int, channel_id: str, channel_title: str, topic: str, interval: int):
    """Запуск автопостинга"""
    task_key = f"{user_id}_{channel_id}"
    
    # Останавливаем старый, если есть
    if task_key in bot_manager.posting_tasks:
        bot_manager.posting_tasks[task_key].cancel()
        await asyncio.sleep(1)
    
    # Запускаем новый
    task = asyncio.create_task(auto_posting_loop(user_id, channel_id, channel_title, topic, interval))
    bot_manager.posting_tasks[task_key] = task

async def stop_auto_posting(channel_id: str):
    """Остановка автопостинга"""
    for task_key, task in list(bot_manager.posting_tasks.items()):
        if task_key.endswith(channel_id):
            task.cancel()
            del bot_manager.posting_tasks[task_key]

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🔄 Репосты", callback_data="reposts_menu")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    """Клавиатура со списком каналов"""
    channels = bot_manager.load_channels(user_id)
    
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel['title']}", callback_data=f"select_{channel['id']}")
        ])
    
    if not channels:
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel_start")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel_start")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_autopost_keyboard(user_id: int):
    """Клавиатура для автопостинга"""
    channels = bot_manager.load_channels(user_id)
    
    keyboard = []
    for channel in channels:
        settings = bot_manager.load_autopost(channel['id'])
        status = "✅" if settings and settings.get('active') else "❌"
        interval = settings.get('interval', 60) if settings else 60
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {channel['title']} ({interval}с)", 
                callback_data=f"autopost_{channel['id']}"
            )
        ])
    
    if not channels:
        keyboard.append([InlineKeyboardButton("❌ Нет каналов", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_settings_keyboard(channel_id: str, settings: dict):
    """Клавиатура настроек автопостинга"""
    is_active = settings.get('active', False) if settings else False
    current_topic = settings.get('topic', 'news') if settings else 'news'
    interval = settings.get('interval', 60) if settings else 60
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'🟢 ВЫКЛЮЧИТЬ' if is_active else '🔴 ВКЛЮЧИТЬ'}", 
            callback_data=f"toggle_{channel_id}"
        )],
        [InlineKeyboardButton(f"📝 Тема: {POST_TEMPLATES[current_topic]['name']}", callback_data=f"topic_{channel_id}")],
        [InlineKeyboardButton(f"⏱ Интервал: {interval} сек", callback_data=f"interval_{channel_id}")],
        [InlineKeyboardButton("💾 Сохранить", callback_data=f"save_autopost_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str):
    """Клавиатура выбора темы"""
    keyboard = []
    for topic_key, topic_data in POST_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(topic_data['name'], callback_data=f"set_topic_{channel_id}_{topic_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"autopost_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    """Клавиатура выбора интервала"""
    keyboard = [
        [InlineKeyboardButton("⚡ 10 секунд (PRO)", callback_data=f"set_interval_{channel_id}_10")],
        [InlineKeyboardButton("🚀 30 секунд (Базовый)", callback_data=f"set_interval_{channel_id}_30")],
        [InlineKeyboardButton("⭐ 60 секунд (Бесплатный)", callback_data=f"set_interval_{channel_id}_60")],
        [InlineKeyboardButton("📘 120 секунд", callback_data=f"set_interval_{channel_id}_120")],
        [InlineKeyboardButton("📗 300 секунд (5 мин)", callback_data=f"set_interval_{channel_id}_300")],
        [InlineKeyboardButton("📙 600 секунд (10 мин)", callback_data=f"set_interval_{channel_id}_600")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"autopost_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Регистрируем пользователя
    if bot_manager.get_user_tariff(user.id) is None:
        bot_manager.set_user_tariff(user.id, 'free')
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Бот для автопостинга в Telegram*\n\n"
        f"🚀 *Возможности:*\n"
        f"• Автопостинг от 10 секунд!\n"
        f"• Генерация интересного контента\n"
        f"• Репосты из других каналов\n"
        f"• Ручная публикация\n\n"
        f"💡 *Как начать:*\n"
        f"1️⃣ Добавь меня в канал как админа\n"
        f"2️⃣ Нажми 'Мои каналы' ➕\n"
        f"3️⃣ Настрой автопостинг!\n\n"
        f"🎁 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления канала"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not bot_manager.can_add_channel(user_id):
        tariff = bot_manager.get_user_tariff(user_id)
        await query.edit_message_text(
            f"❌ *Достигнут лимит каналов!*\n\n"
            f"Ваш тариф: {TARIFFS[tariff]['name']}\n"
            f"Максимум: {TARIFFS[tariff]['max_channels']} каналов\n\n"
            f"Используйте /tariffs для смены тарифа",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Перешлите ЛЮБОЕ сообщение из канала сюда\n"
        "или отправьте ссылку на канал\n\n"
        "Примеры:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "⏸ Отмена - /cancel",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление канала"""
    user = update.effective_user
    text = update.message.text
    
    try:
        # Получаем информацию о канале
        if text.startswith('@'):
            chat = await context.bot.get_chat(chat_id=text)
        elif 't.me/' in text:
            username = text.split('t.me/')[-1]
            chat = await context.bot.get_chat(chat_id=f"@{username}")
        else:
            # Пробуем как forward
            await update.message.reply_text("Пожалуйста, отправьте ссылку на канал или перешлите сообщение")
            return
        
        # Проверяем, что это канал
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал!")
            return
        
        # Сохраняем канал
        channels = bot_manager.load_channels(user.id)
        
        # Проверяем дубликат
        if any(c['id'] == str(chat.id) for c in channels):
            await update.message.reply_text("❌ Этот канал уже добавлен!")
            return
        
        channels.append({
            'id': str(chat.id),
            'title': chat.title,
            'username': chat.username or '',
            'added': datetime.now().isoformat()
        })
        
        bot_manager.save_channels(user.id, channels)
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 {chat.title}\n"
            f"🆔 ID: {chat.id}\n\n"
            f"Теперь настройте автопостинг в меню!",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_channel'] = False
        
        # Показываем меню
        keyboard = await get_main_keyboard()
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}\n\nУбедитесь, что бот добавлен в канал как администратор!")

async def write_post_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная публикация поста"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    channels = bot_manager.load_channels(user_id)
    
    if not channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через 'Мои каналы'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel['title']}", callback_data=f"post_to_{channel['id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка поста в канал"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['manual_channel'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите пост*\n\n"
        "Отправьте текст, фото или видео для публикации\n\n"
        "⏸ Отмена - /cancel",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_post'] = True

async def handle_manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ручного поста"""
    user = update.effective_user
    channel_id = context.user_data.get('manual_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка! Начните заново /start")
        return
    
    try:
        text = update.message.text or update.message.caption
        if not text:
            text = "📷 Новый пост"
        
        # Отправляем
        if update.message.photo:
            await context.bot.send_photo(chat_id=channel_id, photo=update.message.photo[-1].file_id, caption=text)
        elif update.message.video:
            await context.bot.send_video(chat_id=channel_id, video=update.message.video.file_id, caption=text)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text)
        
        # Сохраняем
        bot_manager.save_post(user.id, {
            'channel_id': channel_id,
            'text': text,
            'time': datetime.now().isoformat(),
            'type': 'manual'
        })
        
        await update.message.reply_text("✅ *Пост опубликован!*", parse_mode='Markdown')
        
        context.user_data['manual_channel'] = None
        context.user_data['awaiting_post'] = False
        
        # Показываем меню
        keyboard = await get_main_keyboard()
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def show_autopost_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню автопостинга"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    keyboard = await get_autopost_keyboard(user_id)
    
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - автопостинг активен\n"
        "❌ - автопостинг выключен\n\n"
        "Выберите канал для настройки:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_autopost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка автопостинга для канала"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("autopost_", "")
    context.user_data['autopost_channel'] = channel_id
    
    settings = bot_manager.load_autopost(channel_id) or {}
    keyboard = await get_settings_keyboard(channel_id, settings)
    
    # Получаем название канала
    user_id = query.from_user.id
    channels = bot_manager.load_channels(user_id)
    channel = next((c for c in channels if c['id'] == channel_id), None)
    channel_title = channel['title'] if channel else channel_id
    
    await query.edit_message_text(
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_title}\n\n"
        f"Выберите параметры:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def toggle_autopost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение автопостинга"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_", "")
    user_id = query.from_user.id
    
    settings = bot_manager.load_autopost(channel_id) or {}
    current = settings.get('active', False)
    
    # Проверяем, есть ли настройки
    if not current and not settings.get('topic'):
        await query.answer("Сначала выберите тему и интервал!", show_alert=True)
        return
    
    # Меняем статус
    settings['active'] = not current
    bot_manager.save_autopost(channel_id, settings)
    
    # Запускаем или останавливаем
    channels = bot_manager.load_channels(user_id)
    channel = next((c for c in channels if c['id'] == channel_id), None)
    
    if settings['active']:
        await start_auto_posting(
            user_id, 
            channel_id, 
            channel['title'] if channel else channel_id,
            settings.get('topic', 'news'),
            settings.get('interval', 60)
        )
        await query.edit_message_text(f"✅ *Автопостинг ВКЛЮЧЕН!*\n\nПосты будут публиковаться каждые {settings.get('interval', 60)} секунд")
    else:
        await stop_auto_posting(channel_id)
        await query.edit_message_text(f"❌ *Автопостинг ВЫКЛЮЧЕН*")
    
    await asyncio.sleep(2)
    
    # Возвращаемся к настройкам
    keyboard = await get_settings_keyboard(channel_id, settings)
    await query.message.edit_text(
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel['title'] if channel else channel_id}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def change_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена темы"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("topic_", "")
    keyboard = await get_topics_keyboard(channel_id)
    
    await query.edit_message_text(
        "📝 *Выберите тему для контента:*\n\n"
        "Посты будут генерироваться автоматически",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка темы"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic = parts[3]
    
    settings = bot_manager.load_autopost(channel_id) or {}
    settings['topic'] = topic
    bot_manager.save_autopost(channel_id, settings)
    
    await query.edit_message_text(f"✅ *Тема установлена:* {POST_TEMPLATES[topic]['name']}")
    
    await asyncio.sleep(2)
    
    # Возвращаемся к настройкам
    keyboard = await get_settings_keyboard(channel_id, settings)
    await query.message.edit_text(
        f"⚙️ *Настройки автопостинга*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена интервала"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("interval_", "")
    keyboard = await get_interval_keyboard(channel_id)
    
    await query.edit_message_text(
        "⏱ *Выберите интервал публикации:*\n\n"
        "⚡ 10 сек - для PRO\n"
        "🚀 30 сек - для Базового\n"
        "⭐ 60 сек - для Бесплатного\n\n"
        "Больше скорость = больше охват!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка интервала"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    interval = int(parts[3])
    
    user_id = query.from_user.id
    tariff = bot_manager.get_user_tariff(user_id)
    min_interval = TARIFFS[tariff]['min_interval']
    
    if interval < min_interval:
        await query.answer(f"Для вашего тарифа минимальный интервал {min_interval} сек. Смените тариф!", show_alert=True)
        return
    
    settings = bot_manager.load_autopost(channel_id) or {}
    settings['interval'] = interval
    bot_manager.save_autopost(channel_id, settings)
    
    await query.edit_message_text(f"✅ *Интервал установлен:* {interval} секунд")
    
    # Если автопостинг активен, перезапускаем
    if settings.get('active'):
        channels = bot_manager.load_channels(user_id)
        channel = next((c for c in channels if c['id'] == channel_id), None)
        await stop_auto_posting(channel_id)
        await start_auto_posting(
            user_id, 
            channel_id, 
            channel['title'] if channel else channel_id,
            settings.get('topic', 'news'),
            interval
        )
    
    await asyncio.sleep(2)
    
    # Возвращаемся к настройкам
    keyboard = await get_settings_keyboard(channel_id, settings)
    await query.message.edit_text(
        f"⚙️ *Настройки автопостинга*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def save_autopost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить настройки автопостинга"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("save_autopost_", "")
    settings = bot_manager.load_autopost(channel_id) or {}
    
    if not settings.get('topic') or not settings.get('interval'):
        await query.answer("Сначала выберите тему и интервал!", show_alert=True)
        return
    
    await query.edit_message_text(
        "✅ *Настройки сохранены!*\n\n"
        f"📝 Тема: {POST_TEMPLATES[settings['topic']]['name']}\n"
        f"⏱ Интервал: {settings.get('interval', 60)} сек\n"
        f"🔄 Статус: {'Активен' if settings.get('active') else 'Неактивен'}\n\n"
        f"Включите автопостинг, если еще не сделали этого!"
    )
    
    await asyncio.sleep(3)
    
    # Возвращаемся к настройкам
    keyboard = await get_settings_keyboard(channel_id, settings)
    await query.message.edit_text(
        f"⚙️ *Настройки автопостинга*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    posts = bot_manager.load_posts(user_id)
    
    # Статистика по дням
    today = datetime.now().date()
    posts_today = sum(1 for p in posts if datetime.fromisoformat(p['time']).date() == today)
    
    channels = bot_manager.load_channels(user_id)
    autopost = bot_manager.load_autopost()
    active_autopost = sum(1 for s in autopost.values() if s.get('active'))
    
    stats_text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 Всего постов: {len(posts)}\n"
        f"📅 Сегодня: {posts_today}\n"
        f"📢 Каналов: {len(channels)}\n"
        f"⚙️ Активных автопостов: {active_autopost}\n"
        f"💎 Тариф: {TARIFFS[bot_manager.get_user_tariff(user_id)]['name']}\n\n"
        f"🚀 *Совет:* Чем чаще посты, тем выше охват!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=keyboard)

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_tariff = bot_manager.get_user_tariff(user_id)
    
    text = "💎 *Доступные тарифы*\n\n"
    
    for key, tariff in TARIFFS.items():
        marker = "✅ " if key == current_tariff else "• "
        text += f"{marker}*{tariff['name']}*\n"
        for feature in tariff['features']:
            text += f"  {feature}\n"
        text += "\n"
    
    keyboard = []
    for key in TARIFFS:
        if key != current_tariff:
            keyboard.append([InlineKeyboardButton(f"Выбрать {TARIFFS[key]['name']}", callback_data=f"set_tariff_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def set_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка тарифа"""
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("set_tariff_", "")
    user_id = query.from_user.id
    
    bot_manager.set_user_tariff(user_id, tariff_key)
    
    await query.edit_message_text(
        f"✅ *Тариф изменен на {TARIFFS[tariff_key]['name']}*\n\n"
        f"Доступные возможности:\n" +
        "\n".join(TARIFFS[tariff_key]['features'])
    )
    
    await asyncio.sleep(3)
    
    keyboard = await get_main_keyboard()
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "ℹ️ *Помощь*\n\n"
        "📋 *Как пользоваться:*\n\n"
        "1️⃣ *Добавить канал*\n"
        "• Добавьте бота в канал как админа\n"
        "• В меню 'Мои каналы' ➕\n"
        "• Отправьте ссылку на канал\n\n"
        "2️⃣ *Настроить автопостинг*\n"
        "• В меню 'Автопостинг'\n"
        "• Выберите канал\n"
        "• Установите тему и интервал\n"
        "• Включите автопостинг ✅\n\n"
        "3️⃣ *Ручной пост*\n"
        "• 'Написать пост'\n"
        "• Выберите канал\n"
        "• Отправьте текст/фото/видео\n\n"
        "🎁 *Все тарифы бесплатны!*\n"
        "Минимальный интервал: 10 секунд (PRO)\n\n"
        "❓ Вопросы: @support"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard()
    await query.edit_message_text(
        "🎯 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена действия"""
    context.user_data.clear()
    await update.message.reply_text("❌ *Действие отменено*", parse_mode='Markdown')
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ЗАПУСК ====================
def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Сохраняем бота в менеджере
    bot_manager.bot = application.bot
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
        else (handle_manual_post(u, c) if c.user_data.get('awaiting_post')
        else None)
    ))
    
    # Медиа для ручных постов
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        handle_manual_post
    ))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(lambda u, c: add_channel_start(u, c), pattern="^add_channel_start$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: write_post_manual(u, c), pattern="^write_post$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: send_post_to_channel(u, c), pattern="^post_to_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: show_autopost_menu(u, c), pattern="^auto_posting$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: configure_autopost(u, c), pattern="^autopost_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: toggle_autopost(u, c), pattern="^toggle_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: change_topic(u, c), pattern="^topic_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: set_topic(u, c), pattern="^set_topic_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: change_interval(u, c), pattern="^interval_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: set_interval(u, c), pattern="^set_interval_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: save_autopost(u, c), pattern="^save_autopost_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: show_stats(u, c), pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: show_tariffs(u, c), pattern="^tariffs$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: set_tariff(u, c), pattern="^set_tariff_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: show_help(u, c), pattern="^help$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: back_to_main(u, c), pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: back_to_main(u, c), pattern="^my_channels$"))
    
    logger.info("🚀 Бот запущен!")
    logger.info("⚡ Автопостинг от 10 секунд!")
    logger.info("💾 Данные хранятся в JSON файлах")
    logger.info("🎁 Все тарифы бесплатны!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
