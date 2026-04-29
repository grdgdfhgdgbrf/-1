import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== GIGACHAT API НАСТРОЙКИ ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ ====================
TARIFFS = {
    "starter": {
        "name": "🌟 Стартовый",
        "emoji": "🌟",
        "channels": 1,
        "posts_per_day": 50,
        "interval_min": 10,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#4CAF50"
    },
    "standard": {
        "name": "⭐ Стандартный",
        "emoji": "⭐",
        "channels": 5,
        "posts_per_day": 200,
        "interval_min": 10,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#2196F3"
    },
    "professional": {
        "name": "💎 Профессиональный",
        "emoji": "💎",
        "channels": 20,
        "posts_per_day": 500,
        "interval_min": 10,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#9C27B0"
    },
    "unlimited": {
        "name": "👑 Безлимитный",
        "emoji": "👑",
        "channels": 999,
        "posts_per_day": 9999,
        "interval_min": 5,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#FF9800"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "Искусственный интеллект",
        "emoji": "🤖",
        "color": "#00BCD4",
        "hashtags": ["#AI", #ИскусственныйИнтеллект", "#Нейросети"],
        "prompt": "Ты эксперт по искусственному интеллекту. Напиши интересный пост о последних новостях и достижениях в мире AI."
    },
    "crypto": {
        "name": "Криптовалюты",
        "emoji": "🪙",
        "color": "#FFC107",
        "hashtags": ["#Криптовалюта", "#Биткоин", "#Блокчейн"],
        "prompt": "Ты криптоаналитик. Напиши пост о криптовалютах, блокчейне и децентрализации."
    },
    "nft": {
        "name": "NFT и Цифровое искусство",
        "emoji": "🎨",
        "color": "#E91E63",
        "hashtags": ["#NFT", "#ЦифровоеИскусство", "#Метавселенная"],
        "prompt": "Ты эксперт по NFT. Напиши пост о цифровом искусстве, коллекциях NFT и метавселенных."
    },
    "telegram": {
        "name": "Telegram",
        "emoji": "📱",
        "color": "#0088CC",
        "hashtags": ["#Telegram", "#Мессенджеры", "#Боты"],
        "prompt": "Ты блогер о Telegram. Напиши пост о новых функциях, ботах и возможностях Telegram."
    },
    "business": {
        "name": "Бизнес и Стартапы",
        "emoji": "💼",
        "color": "#795548",
        "hashtags": ["#Бизнес", "#Стартап", "#Предпринимательство"],
        "prompt": "Ты бизнес-консультант. Напиши пост о бизнесе, стартапах и успешных кейсах."
    },
    "tech": {
        "name": "Технологии",
        "emoji": "📡",
        "color": "#607D8B",
        "hashtags": ["#Технологии", "#Гаджеты", "#Инновации"],
        "prompt": "Ты технологический блогер. Напиши пост о новых технологиях и гаджетах."
    },
    "science": {
        "name": "Наука",
        "emoji": "🔬",
        "color": "#8BC34A",
        "hashtags": ["#Наука", "#Открытия", "#Исследования"],
        "prompt": "Ты научный журналист. Напиши пост о научных открытиях и исследованиях."
    },
    "health": {
        "name": "Здоровье",
        "emoji": "⚕️",
        "color": "#4CAF50",
        "hashtags": ["#Здоровье", "#Медицина", "#ЗОЖ"],
        "prompt": "Ты медицинский блогер. Напиши полезный пост о здоровье и здоровом образе жизни."
    },
    "psychology": {
        "name": "Психология",
        "emoji": "🧠",
        "color": "#9C27B0",
        "hashtags": ["#Психология", "#Саморазвитие", "#Мотивация"],
        "prompt": "Ты психолог. Напиши полезный пост о психологии и саморазвитии."
    },
    "marketing": {
        "name": "Маркетинг",
        "emoji": "📈",
        "color": "#FF5722",
        "hashtags": ["#Маркетинг", "#SMM", "#Реклама"],
        "prompt": "Ты маркетолог. Напиши пост о маркетинге, SMM и продвижении."
    },
    "design": {
        "name": "Дизайн",
        "emoji": "🎨",
        "color": "#FF4081",
        "hashtags": ["#Дизайн", "#UIUX", "#ГрафическийДизайн"],
        "prompt": "Ты дизайнер. Напиши вдохновляющий пост о дизайне и креативе."
    },
    "programming": {
        "name": "Программирование",
        "emoji": "💻",
        "color": "#37474F",
        "hashtags": ["#Программирование", "#Код", "#IT"],
        "prompt": "Ты разработчик. Напиши полезный пост о программировании и IT."
    },
    "gaming": {
        "name": "Игры",
        "emoji": "🎮",
        "color": "#F44336",
        "hashtags": ["#Игры", "#Гейминг", "#Видеоигры"],
        "prompt": "Ты игровой журналист. Напиши пост об играх и игровой индустрии."
    },
    "movies": {
        "name": "Кино и Сериалы",
        "emoji": "🎬",
        "color": "#3F51B5",
        "hashtags": ["#Кино", "#Сериалы", "#НовинкиКино"],
        "prompt": "Ты кинокритик. Напиши пост о новинках кино и сериалов."
    },
    "music": {
        "name": "Музыка",
        "emoji": "🎵",
        "color": "#673AB7",
        "hashtags": ["#Музыка", "#НовинкиМузыки", "#Плейлист"],
        "prompt": "Ты музыкальный обозреватель. Напиши пост о музыке и новинках."
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "color": "#4CAF50",
        "hashtags": ["#Спорт", "#Футбол", "#Тренировки"],
        "prompt": "Ты спортивный журналист. Напиши пост о спорте и здоровом образе жизни."
    },
    "travel": {
        "name": "Путешествия",
        "emoji": "✈️",
        "color": "#00BCD4",
        "hashtags": ["#Путешествия", "#Туризм", "#Мир"],
        "prompt": "Ты тревел-блогер. Напиши пост о путешествиях и интересных местах."
    },
    "food": {
        "name": "Кулинария",
        "emoji": "🍳",
        "color": "#FF9800",
        "hashtags": ["#Кулинария", "#Рецепты", "#Еда"],
        "prompt": "Ты кулинарный блогер. Напиши пост с интересным рецептом или фактами о еде."
    },
    "education": {
        "name": "Образование",
        "emoji": "📚",
        "color": "#2196F3",
        "hashtags": ["#Образование", "#Учеба", "#Знания"],
        "prompt": "Ты педагог. Напиши полезный пост об образовании и обучении."
    },
    "motivation": {
        "name": "Мотивация",
        "emoji": "💪",
        "color": "#FF4081",
        "hashtags": ["#Мотивация", "#Успех", "#Развитие"],
        "prompt": "Ты мотивационный спикер. Напиши вдохновляющий пост о достижении целей."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "Мини", "emoji": "🔹", "min_chars": 150, "max_chars": 300, "format": "Коротко и ёмко"},
    "short": {"name": "Короткий", "emoji": "🔸", "min_chars": 301, "max_chars": 600, "format": "Оптимальный формат"},
    "medium": {"name": "Средний", "emoji": "📄", "min_chars": 601, "max_chars": 1000, "format": "Подробный рассказ"},
    "long": {"name": "Длинный", "emoji": "📖", "min_chars": 1001, "max_chars": 1500, "format": "Глубокий анализ"},
    "extra": {"name": "Максимальный", "emoji": "📚", "min_chars": 1501, "max_chars": 2500, "format": "Максимум пользы"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    channels: List[str] = field(default_factory=list)
    channel_names: Dict[str, str] = field(default_factory=dict)
    auto_configs: Dict[str, dict] = field(default_factory=dict)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    repost_sources: List[str] = field(default_factory=list)
    
    def reset_daily(self):
        now = time.time()
        if now - self.last_reset > 86400:
            self.posts_today = 0
            self.last_reset = now
            return True
        return False
    
    def can_post(self, tariff_config: dict) -> bool:
        self.reset_daily()
        return self.posts_today < tariff_config["posts_per_day"]
    
    def add_post(self):
        self.posts_today += 1

@dataclass
class Post:
    id: str
    channel_id: str
    theme: str
    content: str
    posted_at: float
    size: str
    views: int = 0
    likes: int = 0

# ==================== ОСНОВНОЙ КЛАСС БОТА ====================
class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserSubscription] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[Post] = []
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.running = True
        
    def load_data(self):
        try:
            with open("users_data.json", "r") as f:
                data = json.load(f)
                for uid, udata in data.items():
                    user = UserSubscription(
                        user_id=udata["user_id"],
                        tariff=udata["tariff"],
                        channels=udata.get("channels", []),
                        channel_names=udata.get("channel_names", {}),
                        auto_configs=udata.get("auto_configs", {}),
                        repost_sources=udata.get("repost_sources", [])
                    )
                    self.users[int(uid)] = user
        except:
            pass
        
    def save_data(self):
        data = {}
        for uid, user in self.users.items():
            data[uid] = {
                "user_id": user.user_id,
                "tariff": user.tariff,
                "channels": user.channels,
                "channel_names": user.channel_names,
                "auto_configs": user.auto_configs,
                "repost_sources": user.repost_sources
            }
        with open("users_data.json", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_user(self, user_id: int) -> UserSubscription:
        if user_id not in self.users:
            self.users[user_id] = UserSubscription(
                user_id=user_id,
                tariff="starter"
            )
            self.save_data()
        return self.users[user_id]
    
    async def get_api_token(self) -> str:
        if self.api_token and time.time() < self.api_token_expiry:
            return self.api_token
        
        try:
            auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
            auth_base64 = base64.b64encode(auth_string.encode()).decode()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                    headers={
                        "Authorization": f"Basic {auth_base64}",
                        "RqUID": str(uuid.uuid4()),
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={"scope": API_SCOPE},
                    ssl=False
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.api_token = data.get("access_token")
                        expires_in = data.get("expires_in", 1800)
                        self.api_token_expiry = time.time() + expires_in - 60
                        return self.api_token
        except Exception as e:
            logger.error(f"Ошибка токена: {e}")
        return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

Требования:
- Длина: {size_config['min_chars']}-{size_config['max_chars']} символов
- Используй эмодзи для украшения (5-10 штук)
- Структурируй текст: выделяй важное **жирным**, делай списки
- Добавь интересный факт или вопрос в конце
- Используй красивое форматирование
- В конце добавь 3-5 хэштегов

Тема: {theme_config['name']} {theme_config['emoji']}
Стиль: {size_config['format']}"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "GigaChat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.85,
                        "max_tokens": 3000
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        # Добавляем хэштеги если их нет
                        if not any(hash in content for hash in theme_config["hashtags"]):
                            content += "\n\n" + " ".join(theme_config["hashtags"]) + " #пост #актуальное"
                        
                        return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme, size_config)
    
    def _get_fallback_post(self, theme: str, size_config: dict) -> str:
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        
        fallback = f"""
{theme_config['emoji']} *{theme_config['name']}*

✨ Интересный факт и полезная информация в этом посте!

📝 {size_config['format']}

💡 А как вы относитесь к этой теме? Делитесь мнением в комментариях!

{random.choice(theme_config['hashtags'])} #познавательно #актуально
"""
        return fallback
    
    async def send_beautiful_post(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                                   content: str, theme: str):
        """Красивая отправка поста"""
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        
        # Добавляем разделители и форматирование
        formatted_content = f"""
{theme_config['emoji']} *{theme_config['name']}* {theme_config['emoji']}
{'─' * 30}

{content}

{'─' * 30}
💭 *Обсуждение:* @{channel_id.replace("-100", "")}

#пост #{theme_config['name'].lower().replace(' ', '')}
"""
        
        try:
            # Пробуем отправить с HTML разметкой
            await context.bot.send_message(
                chat_id=channel_id,
                text=formatted_content,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            return True
        except:
            # Fallback без разметки
            try:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode=None
                )
                return True
            except Exception as e:
                logger.error(f"Ошибка отправки в {channel_id}: {e}")
                return False
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, user_id: int,
                              channel_id: str, theme: str, size: str) -> bool:
        user = self.get_user(user_id)
        tariff = TARIFFS[user.tariff]
        
        if not user.can_post(tariff):
            return False
        
        content = await self.generate_post(theme, size)
        success = await self.send_beautiful_post(context, channel_id, content, theme)
        
        if success:
            user.add_post()
            self.post_history.append(Post(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                theme=theme,
                content=content[:200],
                posted_at=time.time(),
                size=size
            ))
            self.save_data()
            return True
        return False
    
    async def auto_post_loop(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                             channel_id: str, config: dict):
        """Цикл автопостинга"""
        user = self.get_user(user_id)
        
        while self.running and channel_id in user.auto_configs:
            try:
                current_config = user.auto_configs.get(channel_id)
                if not current_config or not current_config.get("active", True):
                    break
                
                tariff = TARIFFS[user.tariff]
                if user.can_post(tariff):
                    theme = current_config["theme"]
                    size = current_config["size"]
                    
                    success = await self.post_to_channel(
                        context, user_id, channel_id, theme, size
                    )
                    
                    if success:
                        logger.info(f"✅ Автопост в {channel_id} на тему {theme}")
                
                # Ожидание интервала
                interval = current_config.get("interval", 60)
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Ошибка автопостинга: {e}")
                await asyncio.sleep(30)
    
    def start_auto_posting(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                          channel_id: str, config: dict):
        """Запуск автопостинга"""
        job_key = f"{user_id}_{channel_id}"
        
        if job_key in self.active_jobs:
            self.active_jobs[job_key].cancel()
        
        task = asyncio.create_task(self.auto_post_loop(context, user_id, channel_id, config))
        self.active_jobs[job_key] = task
    
    def stop_auto_posting(self, user_id: int, channel_id: str):
        """Остановка автопостинга"""
        job_key = f"{user_id}_{channel_id}"
        if job_key in self.active_jobs:
            self.active_jobs[job_key].cancel()
            del self.active_jobs[job_key]

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_menu")],
        [InlineKeyboardButton("⚡ Разовый пост", callback_data="single_post")],
        [InlineKeyboardButton("🔄 Перепост", callback_data="repost_menu")],
        [InlineKeyboardButton("💎 Выбрать тариф", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(action: str, channel_id: str = None):
    keyboard = []
    row = []
    
    for theme_key, theme in POSTING_THEMES.items():
        callback = f"{action}_{theme_key}"
        if channel_id:
            callback = f"{action}_{channel_id}_{theme_key}"
        row.append(InlineKeyboardButton(
            f"{theme['emoji']} {theme['name']}", 
            callback_data=callback
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(action: str, theme: str = None, channel_id: str = None):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        callback = f"{action}_{size_key}"
        if theme:
            callback = f"{action}_{theme}_{size_key}"
        if channel_id:
            callback = f"{action}_{channel_id}_{size_key}"
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} ({size['min_chars']}-{size['max_chars']} симв.)",
            callback_data=callback
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int, action: str):
    user = bot.get_user(user_id)
    keyboard = []
    
    for channel_id in user.channels:
        name = user.channel_names.get(channel_id, "Канал")
        keyboard.append([InlineKeyboardButton(
            f"📢 {name}", 
            callback_data=f"{action}_{channel_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(channel_id: str):
    intervals = [10, 30, 60, 120, 180, 300, 600, 900, 1800, 3600]
    keyboard = []
    row = []
    
    for interval in intervals:
        text = f"{interval//60} мин" if interval >= 60 else f"{interval} сек"
        row.append(InlineKeyboardButton(text, callback_data=f"interval_{channel_id}_{interval}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"config_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    
    welcome_text = f"""
🚀 *Добро пожаловать, {user.first_name}!*

🤖 *AI Бот для автопостинга*

✨ *Возможности:*
• 📝 Генерация уникальных постов через ИИ
• 🎨 20+ тематик на выбор
• ⏱ Автопостинг от 10 секунд
• 🔄 Перепост из других каналов
• 💎 Все тарифы БЕСПЛАТНЫЕ

🎯 *Как начать:*
1️⃣ Добавьте бота в канал как администратора
2️⃣ Нажмите "➕ Добавить канал"
3️⃣ Настройте автопостинг

💡 *Все функции доступны бесплатно!*

👇 *Выберите действие:*
"""
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "📌 *Инструкция:*\n"
        "1️⃣ Сделайте бота администратором канала\n"
        "2️⃣ Перешлите ЛЮБОЕ сообщение из канала сюда\n"
        "3️⃣ Или отправьте ссылку/username канала\n\n"
        "✅ После добавления можно настроить автопостинг",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_channel'):
        return
    
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    if len(user.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ Лимит каналов для тарифа *{tariff['name']}*: {tariff['channels']}\n"
            f"💎 Выберите другой тариф в меню",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_channel'] = False
        return
    
    channel_id = None
    channel_name = None
    
    # Определяем канал
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
    elif update.message.text:
        text = update.message.text.strip()
        if text.startswith('@'):
            try:
                chat = await context.bot.get_chat(text)
                channel_id = str(chat.id)
                channel_name = chat.title
            except:
                pass
        elif text.startswith('-100') or text.lstrip('-').isdigit():
            channel_id = text
            try:
                chat = await context.bot.get_chat(int(channel_id))
                channel_name = chat.title
            except:
                channel_name = f"Канал {channel_id}"
    
    if channel_id and channel_id not in user.channels:
        user.channels.append(channel_id)
        user.channel_names[channel_id] = channel_name
        bot.save_data()
        
        await update.message.reply_text(
            f"✅ *Канал успешно добавлен!*\n\n"
            f"📢 *Название:* {channel_name}\n"
            f"📊 *Всего каналов:* {len(user.channels)}/{tariff['channels']}\n\n"
            f"🤖 Теперь настройте автопостинг в меню",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Не удалось определить канал. Попробуйте переслать сообщение.")
    
    context.user_data['awaiting_channel'] = False

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    if not user.channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов*\n\n➕ Нажмите 'Добавить канал' в главном меню",
            parse_mode='Markdown'
        )
        return
    
    text = f"📋 *Ваши каналы* ({len(user.channels)}/{tariff['channels']})\n\n"
    
    for channel_id in user.channels:
        channel_name = user.channel_names.get(channel_id, "Канал")
        config = user.auto_configs.get(channel_id, {})
        
        status = "✅ Активен" if config.get("active") else "⏸ Остановлен"
        theme = config.get("theme", "Не выбран")
        interval = config.get("interval", 60)
        interval_text = f"{interval//60} мин" if interval >= 60 else f"{interval} сек"
        
        text += f"""
📢 *{channel_name}*
🆔 `{channel_id}`
🎨 Тема: {POSTING_THEMES.get(theme, {}).get('emoji', '')} {POSTING_THEMES.get(theme, {}).get('name', 'Не выбрана')}
⏱ Интервал: {interval_text}
🔄 Статус: {status}
{'─' * 30}
"""
    
    keyboard = []
    for channel_id in user.channels:
        channel_name = user.channel_names.get(channel_id, "Канал")
        keyboard.append([InlineKeyboardButton(f"⚙️ {channel_name}", callback_data=f"config_{channel_id}")])
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить {channel_name}", callback_data=f"delete_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def auto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов*\n\n"
            "➕ Сначала добавьте канал через главное меню",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_channels_keyboard(user_id, "auto_select")
    await query.edit_message_text(
        "🤖 *Настройка автопостинга*\n\n"
        "Выберите канал для настройки:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def config_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[1]
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    config = user.auto_configs.get(channel_id, {})
    channel_name = user.channel_names.get(channel_id, "Канал")
    
    theme = config.get("theme", "Не выбрана")
    size = config.get("size", "medium")
    interval = config.get("interval", 60)
    active = config.get("active", False)
    
    interval_text = f"{interval//60} мин" if interval >= 60 else f"{interval} сек"
    theme_display = f"{POSTING_THEMES.get(theme, {}).get('emoji', '')} {POSTING_THEMES.get(theme, {}).get('name', 'Не выбрана')}"
    
    text = f"""
⚙️ *Настройка канала*

📢 *{channel_name}*

🎨 *Тема:* {theme_display}
📏 *Размер:* {POST_SIZES.get(size, {}).get('emoji', '')} {POST_SIZES.get(size, {}).get('name', 'Средний')}
⏱ *Интервал:* {interval_text}
🔄 *Статус:* {'✅ Включен' if active else '⏸ Выключен'}

Выберите действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"set_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"set_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Выбрать интервал", callback_data=f"set_interval_{channel_id}")],
        [InlineKeyboardButton("✅ Включить автопостинг", callback_data=f"enable_{channel_id}")] if not active else
        [InlineKeyboardButton("⏸ Выключить автопостинг", callback_data=f"disable_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_menu")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def set_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[2]
    
    keyboard = await get_themes_keyboard("theme_select", channel_id)
    await query.edit_message_text(
        "🎨 *Выберите тему для автопостинга:*\n\n"
        "Доступно 20+ уникальных тем",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[2]
    
    keyboard = await get_sizes_keyboard("size_select", channel_id=channel_id)
    await query.edit_message_text(
        "📏 *Выберите размер постов:*\n\n"
        "Размер влияет на детализацию контента",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[2]
    
    keyboard = await get_intervals_keyboard(channel_id)
    await query.edit_message_text(
        "⏱ *Выберите интервал публикации:*\n\n"
        "• 10 сек - для тестирования\n"
        "• 30 сек - очень часто\n"
        "• 1-5 мин - оптимально\n"
        "• 10-60 мин - редко\n\n"
        "Минимальный интервал: 10 секунд",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def save_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id not in user.auto_configs:
        user.auto_configs[channel_id] = {}
    
    user.auto_configs[channel_id]["interval"] = interval
    bot.save_data()
    
    await query.answer(f"✅ Интервал установлен: {interval//60} мин" if interval >= 60 else f"{interval} сек")
    await config_channel(update, context)

async def select_theme_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    channel_id = parts[2]
    theme = parts[3]
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id not in user.auto_configs:
        user.auto_configs[channel_id] = {}
    
    user.auto_configs[channel_id]["theme"] = theme
    bot.save_data()
    
    await query.answer(f"✅ Тема выбрана: {POSTING_THEMES[theme]['name']}")
    await config_channel(update, context)

async def select_size_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    channel_id = parts[2]
    size = parts[3]
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id not in user.auto_configs:
        user.auto_configs[channel_id] = {}
    
    user.auto_configs[channel_id]["size"] = size
    bot.save_data()
    
    await query.answer(f"✅ Размер выбран: {POST_SIZES[size]['name']}")
    await config_channel(update, context)

async def enable_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[1]
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id not in user.auto_configs:
        user.auto_configs[channel_id] = {}
    
    config = user.auto_configs[channel_id]
    
    if "theme" not in config:
        await query.answer("❌ Сначала выберите тему!", show_alert=True)
        return
    if "size" not in config:
        await query.answer("❌ Сначала выберите размер!", show_alert=True)
        return
    if "interval" not in config:
        await query.answer("❌ Сначала выберите интервал!", show_alert=True)
        return
    
    config["active"] = True
    bot.save_data()
    
    # Запускаем автопостинг
    bot.start_auto_posting(context, user_id, channel_id, config)
    
    await query.answer("✅ Автопостинг включен!")
    await config_channel(update, context)

async def disable_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[1]
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id in user.auto_configs:
        user.auto_configs[channel_id]["active"] = False
        bot.save_data()
        bot.stop_auto_posting(user_id, channel_id)
    
    await query.answer("⏸ Автопостинг выключен!")
    await config_channel(update, context)

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[1]
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id in user.channels:
        user.channels.remove(channel_id)
        if channel_id in user.channel_names:
            del user.channel_names[channel_id]
        if channel_id in user.auto_configs:
            del user.auto_configs[channel_id]
        bot.stop_auto_posting(user_id, channel_id)
        bot.save_data()
        
        await query.answer("✅ Канал удален!")
        await my_channels(update, context)

async def single_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов*\n\n"
            "➕ Сначала добавьте канал",
            parse_mode='Markdown'
        )
        return
    
    # Сохраняем в контекст что это разовый пост
    context.user_data['single_post'] = True
    keyboard = await get_channels_keyboard(user_id, "single_channel")
    await query.edit_message_text(
        "📝 *Разовый пост*\n\n"
        "Выберите канал для публикации:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def single_post_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.split("_")[2]
    
    # Сохраняем канал
    context.user_data['single_channel'] = channel_id
    keyboard = await get_themes_keyboard("single_theme")
    await query.edit_message_text(
        "🎨 *Выберите тему для поста:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def single_post_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    theme = query.data.split("_")[2]
    
    context.user_data['single_theme'] = theme
    keyboard = await get_sizes_keyboard("single_size", theme)
    await query.edit_message_text(
        "📏 *Выберите размер поста:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def single_post_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    theme = parts[2]
    size = parts[3]
    
    user_id = query.from_user.id
    channel_id = context.user_data.get('single_channel')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка, попробуйте снова")
        return
    
    await query.edit_message_text(f"✨ Генерирую пост на тему {POSTING_THEMES[theme]['emoji']}...")
    
    success = await bot.post_to_channel(context, user_id, channel_id, theme, size)
    
    if success:
        await query.edit_message_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
            f"📏 Размер: {POST_SIZES[size]['name']}\n\n"
            f"📊 Статистика обновлена",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Ошибка при публикации поста")

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    text = "💎 *Доступные тарифы (ВСЕ БЕСПЛАТНЫ!)*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        current = " ✅ ТЕКУЩИЙ" if user.tariff == tariff_key else ""
        text += f"""
{tariff['emoji']} *{tariff['name']}{current}*
├ 📊 Каналов: {tariff['channels']}
├ 📝 Постов/день: {tariff['posts_per_day']}
├ ⏱ Мин. интервал: {tariff['interval_min']} сек
├ 🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}
└ 🖼 Картинки: {'✅' if tariff['has_images'] else '❌'}

"""
    
    text += "\n✨ *Все тарифы полностью бесплатны!*\n"
    text += "Просто выберите подходящий и наслаждайтесь 🎉"
    
    keyboard = []
    for tariff_key in TARIFFS:
        keyboard.append([InlineKeyboardButton(
            f"{TARIFFS[tariff_key]['emoji']} {TARIFFS[tariff_key]['name']}",
            callback_data=f"select_tariff_{tariff_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tariff_key = query.data.split("_")[2]
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    user.tariff = tariff_key
    bot.save_data()
    
    await query.answer(f"✅ Тариф {TARIFFS[tariff_key]['name']} активирован!")
    await tariffs_menu(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    user.reset_daily()
    remaining = tariff["posts_per_day"] - user.posts_today
    
    text = f"""
📊 *Ваша статистика*

👤 *Пользователь:* ID {user_id}
💎 *Тариф:* {tariff['emoji']} {tariff['name']}

📈 *Каналы:*
├ Всего: {len(user.channels)}/{tariff['channels']}
└ Активных: {len([c for c in user.auto_configs if user.auto_configs[c].get('active')])}

📝 *Посты:*
├ Сегодня: {user.posts_today}/{tariff['posts_per_day']}
└ Осталось: {remaining} постов

⚙️ *Автопостинг:*
├ Активных задач: {len([c for c in user.auto_configs if user.auto_configs[c].get('active')])}
└ Всего постов в боте: {len(bot.post_history)}

✨ *Статус:* {'🟢 Активен' if remaining > 0 else '🔴 Лимит исчерпан'}
"""
    
    keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="stats")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def repost_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    if not tariff["can_repost"]:
        await query.edit_message_text(
            "❌ *Функция перепоста*\n\n"
            "На вашем тарифе эта функция недоступна\n"
            "Выберите другой тариф в меню",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        "🔄 *Настройка перепоста*\n\n"
        "📌 *Инструкция:*\n"
        "1. Добавьте бота в канал-источник\n"
        "2. Перешлите пост из источника сюда\n"
        "3. Бот будет автоматически копировать новые посты\n\n"
        "ИЛИ отправьте ссылку на канал для перепоста\n\n"
        "💡 *Важно:* Для автоперепоста нужны права администратора в канале-источнике\n\n"
        "Отправьте сюда ссылку или перешлите пост:",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_repost'] = True

async def handle_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_repost'):
        return
    
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    
    source_id = None
    source_name = None
    
    if update.message.forward_from_chat:
        source_id = str(update.message.forward_from_chat.id)
        source_name = update.message.forward_from_chat.title
    elif update.message.text:
        text = update.message.text.strip()
        if 't.me/' in text:
            username = text.split('t.me/')[-1].split('/')[0].split('?')[0]
            try:
                chat = await context.bot.get_chat(f"@{username}")
                source_id = str(chat.id)
                source_name = chat.title
            except:
                pass
    
    if source_id and source_id not in user.repost_sources:
        user.repost_sources.append(source_id)
        bot.save_data()
        
        await update.message.reply_text(
            f"✅ *Источник для перепоста добавлен!*\n\n"
            f"📢 Канал: {source_name}\n"
            f"🆔 ID: {source_id}\n\n"
            f"📌 Новые посты из этого канала будут автоматически копироваться",
            parse_mode='Markdown'
        )
    elif source_id:
        await update.message.reply_text("❌ Этот источник уже добавлен")
    else:
        await update.message.reply_text("❌ Не удалось определить канал-источник")
    
    context.user_data['awaiting_repost'] = False

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    help_text = """
🆘 *Помощь по работе бота*

📌 *Основные команды:*
• /start - Главное меню
• /menu - Открыть меню

📢 *Управление каналами:*
• Добавить канал - бот будет постить
• Автопостинг - настройка автоматических постов
• Разовый пост - публикация одного поста

⚙️ *Настройки автопостинга:*
• Тема - выбор тематики (20+ тем)
• Размер - длина поста (5 вариантов)
• Интервал - от 10 секунд до часа
• Включить/выключить - управление

🎨 *Доступные темы:*
"""
    
    for theme_key, theme in list(POSTING_THEMES.items())[:10]:
        help_text += f"{theme['emoji']} {theme['name']}\n"
    help_text += "...и еще 10 тем\n\n"
    
    help_text += """
💰 *Тарифы (ВСЕ БЕСПЛАТНЫ):*
• Стартовый - 1 канал, 50 постов/день
• Стандартный - 5 каналов, 200 постов/день
• Профессиональный - 20 каналов, 500 постов/день
• Безлимитный - безлимит

❓ *Вопросы и поддержка:* @

👇 *Выберите действие в меню*
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = await get_main_keyboard()
    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "my_channels":
        await my_channels(update, context)
    elif data == "add_channel":
        await add_channel(update, context)
    elif data == "auto_menu":
        await auto_menu(update, context)
    elif data == "single_post":
        await single_post(update, context)
    elif data == "repost_menu":
        await repost_menu(update, context)
    elif data == "tariffs":
        await tariffs_menu(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("config_"):
        await config_channel(update, context)
    elif data.startswith("delete_"):
        await delete_channel(update, context)
    elif data.startswith("auto_select_"):
        channel_id = data.split("_")[2]
        context.user_data['config_channel'] = channel_id
        await config_channel(update, context)
    elif data.startswith("set_theme_"):
        await set_theme(update, context)
    elif data.startswith("set_size_"):
        await set_size(update, context)
    elif data.startswith("set_interval_"):
        await set_interval(update, context)
    elif data.startswith("interval_"):
        await save_interval(update, context)
    elif data.startswith("theme_select_"):
        await select_theme_for_channel(update, context)
    elif data.startswith("size_select_"):
        await select_size_for_channel(update, context)
    elif data.startswith("enable_"):
        await enable_auto(update, context)
    elif data.startswith("disable_"):
        await disable_auto(update, context)
    elif data.startswith("single_channel_"):
        await single_post_channel(update, context)
    elif data.startswith("single_theme_"):
        await single_post_theme(update, context)
    elif data.startswith("single_size_"):
        await single_post_size(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_add))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_repost))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Тарифов: {len(TARIFFS)} (все бесплатные)")
    logger.info(f"⏱ Минимальный интервал: {min(TARIFFS[t]['interval_min'] for t in TARIFFS)} сек")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
