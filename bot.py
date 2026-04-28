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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    "free": {
        "name": "📢 Базовый",
        "channels": 1,
        "posts_per_day": 10,
        "can_repost": True,
        "can_schedule": True,
        "auto_posting": True
    },
    "standard": {
        "name": "⭐ Стандартный",
        "channels": 5,
        "posts_per_day": 30,
        "can_repost": True,
        "can_schedule": True,
        "auto_posting": True
    },
    "pro": {
        "name": "💎 Профессиональный",
        "channels": 15,
        "posts_per_day": 100,
        "can_repost": True,
        "can_schedule": True,
        "auto_posting": True
    },
    "unlimited": {
        "name": "👑 Unlimited",
        "channels": 999,
        "posts_per_day": 500,
        "can_repost": True,
        "can_schedule": True,
        "auto_posting": True
    }
}

# ==================== 20 ТЕМ ДЛЯ ПОСТИНГА ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "ИИ и Нейросети",
        "emoji": "🤖",
        "color": "🔵",
        "hashtags": ["#ИИ", "#Нейросети", "#AI", "#ИскусственныйИнтеллект"],
        "prompt": "Ты журналист, пишущий об ИИ. Создай увлекательный пост о нейросетях и искусственном интеллекте."
    },
    "crypto": {
        "name": "Криптовалюты",
        "emoji": "🪙",
        "color": "🟡",
        "hashtags": ["#Криптовалюта", "#Биткоин", "#Blockchain", "#DeFi"],
        "prompt": "Ты криптоаналитик. Создай пост о мире криптовалют и блокчейна."
    },
    "nft": {
        "name": "NFT и Цифровое Искусство",
        "emoji": "🎨",
        "color": "🟣",
        "hashtags": ["#NFT", "#ЦифровоеИскусство", "#Метавселенная", "#Web3"],
        "prompt": "Ты эксперт по NFT. Создай пост о цифровом искусстве и NFT коллекциях."
    },
    "telegram": {
        "name": "Telegram",
        "emoji": "📱",
        "color": "🔵",
        "hashtags": ["#Telegram", "#Мессенджеры", "#Криптобезопасность"],
        "prompt": "Ты блогер о Telegram. Создай пост о новых функциях и возможностях Telegram."
    },
    "business": {
        "name": "Бизнес",
        "emoji": "💼",
        "color": "🟢",
        "hashtags": ["#Бизнес", "#Предпринимательство", "#Успех", "#БизнесИдеи"],
        "prompt": "Ты бизнес-журналист. Создай полезный пост о бизнесе и предпринимательстве."
    },
    "tech": {
        "name": "Технологии",
        "emoji": "📡",
        "color": "🔵",
        "hashtags": ["#Технологии", "#Гаджеты", "#Инновации", "#IT"],
        "prompt": "Ты техноблогер. Создай пост о новейших технологиях и гаджетах."
    },
    "science": {
        "name": "Наука",
        "emoji": "🔬",
        "color": "🧪",
        "hashtags": ["#Наука", "#Открытия", "#Исследования", "#Физика"],
        "prompt": "Ты научный журналист. Создай пост о научных открытиях и исследованиях."
    },
    "health": {
        "name": "Здоровье",
        "emoji": "⚕️",
        "color": "❤️",
        "hashtags": ["#Здоровье", "#Медицина", "#ЗОЖ", "#Спорт"],
        "prompt": "Ты медицинский блогер. Создай полезный пост о здоровье и ЗОЖ."
    },
    "psychology": {
        "name": "Психология",
        "emoji": "🧠",
        "color": "💜",
        "hashtags": ["#Психология", "#Саморазвитие", "#Мотивация", "#Осознанность"],
        "prompt": "Ты психолог. Создай интересный пост о психологии и личностном росте."
    },
    "marketing": {
        "name": "Маркетинг",
        "emoji": "📈",
        "color": "🟠",
        "hashtags": ["#Маркетинг", "#SMM", "#Реклама", "#Брендинг"],
        "prompt": "Ты маркетолог. Создай пост о маркетинге и digital-продвижении."
    },
    "design": {
        "name": "Дизайн",
        "emoji": "🎨",
        "color": "💗",
        "hashtags": ["#Дизайн", "#ГрафическийДизайн", "#UIUX", "#Креатив"],
        "prompt": "Ты дизайнер. Создай вдохновляющий пост о дизайне и творчестве."
    },
    "programming": {
        "name": "Программирование",
        "emoji": "💻",
        "color": "💙",
        "hashtags": ["#Программирование", "#Код", "#Разработка", "#ИТ"],
        "prompt": "Ты разработчик. Создай полезный пост о программировании и IT."
    },
    "gaming": {
        "name": "Игры",
        "emoji": "🎮",
        "color": "🟢",
        "hashtags": ["#Игры", "#Гейминг", "#Видеоигры", "#Киберспорт"],
        "prompt": "Ты игровой журналист. Создай пост о новинках игровой индустрии."
    },
    "movies": {
        "name": "Кино",
        "emoji": "🎬",
        "color": "🔴",
        "hashtags": ["#Кино", "#Фильмы", "#Сериалы", "#Кинопремьеры"],
        "prompt": "Ты кинокритик. Создай пост о новых фильмах и сериалах."
    },
    "music": {
        "name": "Музыка",
        "emoji": "🎵",
        "color": "🎶",
        "hashtags": ["#Музыка", "#НовинкиМузыки", "#Хиты", "#Концерты"],
        "prompt": "Ты музыкальный обозреватель. Создай пост о музыкальных новинках."
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "color": "🏆",
        "hashtags": ["#Спорт", "#Футбол", "#Тренировки", "#ЗОЖ"],
        "prompt": "Ты спортивный журналист. Создай пост о спорте и активном образе жизни."
    },
    "travel": {
        "name": "Путешествия",
        "emoji": "✈️",
        "color": "🌍",
        "hashtags": ["#Путешествия", "#Туризм", "#Мир", "#Приключения"],
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях и лучших местах для отдыха."
    },
    "food": {
        "name": "Кулинария",
        "emoji": "🍳",
        "color": "🍜",
        "hashtags": ["#Кулинария", "#Рецепты", "#Еда", "#ГотовимДома"],
        "prompt": "Ты кулинарный блогер. Создай пост с интересным рецептом."
    },
    "education": {
        "name": "Образование",
        "emoji": "📚",
        "color": "🎓",
        "hashtags": ["#Образование", "#Учеба", "#Знания", "#Саморазвитие"],
        "prompt": "Ты педагог. Создай полезный пост об образовании и обучении."
    },
    "motivation": {
        "name": "Мотивация",
        "emoji": "💪",
        "color": "✨",
        "hashtags": ["#Мотивация", "#Успех", "#Цитаты", "#Вдохновение"],
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост для достижения целей."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "Мини", "emoji": "🔹", "min": 100, "max": 300},
    "short": {"name": "Короткий", "emoji": "🔸", "min": 301, "max": 600},
    "medium": {"name": "Средний", "emoji": "📝", "min": 601, "max": 1000},
    "long": {"name": "Длинный", "emoji": "📄", "min": 1001, "max": 1500},
    "extra": {"name": "Максимальный", "emoji": "📚", "min": 1501, "max": 2000}
}

# ==================== ВРЕМЕННЫЕ ИНТЕРВАЛЫ ====================
AUTO_INTERVALS = {
    30: "⏰ Каждые 30 минут",
    60: "🕐 Каждый час", 
    120: "🕑 Каждые 2 часа",
    240: "🕓 Каждые 4 часа",
    360: "🕕 Каждые 6 часов",
    720: "🕛 Каждые 12 часов",
    1440: "📅 Раз в день"
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
@dataclass
class UserData:
    user_id: int
    username: str
    first_name: str
    tariff: str = "free"
    channels: List[dict] = field(default_factory=list)  # [{"id": "123", "name": "Канал"}]
    daily_posts: int = 0
    last_reset: float = field(default_factory=time.time)
    auto_configs: Dict[str, dict] = field(default_factory=dict)  # channel_id -> {"theme": "", "size": "", "interval": 60, "active": True}
    selected_theme: str = "ai_news"
    selected_size: str = "medium"
    
    def reset_daily(self):
        now = time.time()
        if now - self.last_reset >= 86400:
            self.daily_posts = 0
            self.last_reset = now
    
    def can_post(self) -> bool:
        self.reset_daily()
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return self.daily_posts < tariff["posts_per_day"]
    
    def add_post(self):
        self.daily_posts += 1

class BotDatabase:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[dict] = []
    
    def load(self):
        try:
            with open("users_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, udata in data.items():
                    user = UserData(
                        user_id=udata["user_id"],
                        username=udata.get("username", ""),
                        first_name=udata.get("first_name", ""),
                        tariff=udata.get("tariff", "free"),
                        channels=udata.get("channels", []),
                        daily_posts=udata.get("daily_posts", 0),
                        last_reset=udata.get("last_reset", time.time()),
                        auto_configs=udata.get("auto_configs", {}),
                        selected_theme=udata.get("selected_theme", "ai_news"),
                        selected_size=udata.get("selected_size", "medium")
                    )
                    self.users[int(uid)] = user
        except:
            pass
    
    def save(self):
        data = {}
        for uid, user in self.users.items():
            data[uid] = {
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "tariff": user.tariff,
                "channels": user.channels,
                "daily_posts": user.daily_posts,
                "last_reset": user.last_reset,
                "auto_configs": user.auto_configs,
                "selected_theme": user.selected_theme,
                "selected_size": user.selected_size
            }
        with open("users_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            self.save()
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
            logger.error(f"Ошибка получения токена: {e}")
        return None
    
    async def generate_post(self, theme_key: str, size_key: str) -> str:
        """Генерация поста через GigaChat"""
        token = await self.get_api_token()
        theme = POSTING_THEMES.get(theme_key, POSTING_THEMES["ai_news"])
        size = POST_SIZES.get(size_key, POST_SIZES["medium"])
        
        if not token:
            return self.get_fallback_post(theme_key, size_key)
        
        prompt = f"""Напиши интересный пост для Telegram канала на тему "{theme['name']}".

Требования:
- Длина: {size['min']}-{size['max']} символов
- Используй эмодзи для украшения
- Пост должен быть полезным и увлекательным
- В конце добавь вопрос к подписчикам
- Затем добавь хэштеги: {' '.join(theme['hashtags'])}

{theme['prompt']}

Пост должен выглядеть красиво и профессионально."""
        
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
                        "max_tokens": 2500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and data["choices"]:
                            content = data["choices"][0]["message"]["content"]
                            if len(content) > size["max"]:
                                content = content[:size["max"]]
                            return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self.get_fallback_post(theme_key, size_key)
    
    def get_fallback_post(self, theme_key: str, size_key: str) -> str:
        """Запасной пост при ошибке API"""
        theme = POSTING_THEMES.get(theme_key, POSTING_THEMES["ai_news"])
        size = POST_SIZES.get(size_key, POST_SIZES["medium"])
        
        texts = {
            "ai_news": f"{theme['emoji']} *Искусственный интеллект меняет мир!*\n\nНейросети становятся умнее с каждым днём. Какое применение ИИ вас больше всего впечатляет?\n\n{' '.join(theme['hashtags'])}",
            "crypto": f"{theme['emoji']} *Крипторынок оживает!*\n\nБиткоин снова в центре внимания. Следите за трендами и не упустите возможность!\n\n{' '.join(theme['hashtags'])}",
            "nft": f"{theme['emoji']} *NFT - будущее цифрового искусства?*\n\nУникальные токены открывают новые горизонты для художников и коллекционеров.\n\n{' '.join(theme['hashtags'])}",
            "telegram": f"{theme['emoji']} *Telegram — лучший мессенджер!*\n\nНовые функции, боты и каналы делают его незаменимым.\n\n{' '.join(theme['hashtags'])}"
        }
        
        return texts.get(theme_key, f"{theme['emoji']} *{theme['name']}*\n\nИнтересные новости и факты ждут вас!\n\n{' '.join(theme['hashtags'])}")
    
    def format_post(self, content: str, theme_key: str) -> str:
        """Красивое форматирование поста"""
        theme = POSTING_THEMES.get(theme_key, POSTING_THEMES["ai_news"])
        
        separator = "─" * 30
        header = f"{theme['color']} *{theme['name']}* {theme['emoji']}\n{separator}\n"
        
        if not content.startswith(header):
            content = header + content
        
        if not content.endswith("\n\n✨ *Подписывайтесь на наш канал!* ✨"):
            content += f"\n\n{separator}\n✨ *Подписывайтесь на наш канал!* ✨"
        
        return content
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                              theme_key: str, size_key: str) -> bool:
        """Публикация поста в канал"""
        user_id = None
        for uid, user in self.users.items():
            for ch in user.channels:
                if ch.get("id") == channel_id:
                    user_id = uid
                    break
        
        if not user_id:
            return False
        
        user = self.get_user(user_id)
        
        if not user.can_post():
            return False
        
        content = await self.generate_post(theme_key, size_key)
        formatted_content = self.format_post(content, theme_key)
        
        try:
            await context.bot.send_message(
                chat_id=channel_id,
                text=formatted_content,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            
            user.add_post()
            self.post_history.append({
                "channel": channel_id,
                "theme": theme_key,
                "time": time.time(),
                "size": size_key
            })
            self.save()
            
            logger.info(f"✅ Пост опубликован в {channel_id} на тему {theme_key}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка публикации: {e}")
            return False

db = BotDatabase()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="select_size")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("📤 Опубликовать пост", callback_data="post_now")],
        [InlineKeyboardButton("📋 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(page: int = 0):
    themes_list = list(POSTING_THEMES.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    
    keyboard = []
    for theme_key, theme in themes_list[start:end]:
        keyboard.append([
            InlineKeyboardButton(
                f"{theme['emoji']} {theme['name']}",
                callback_data=f"theme_sel_{theme_key}"
            )
        ])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"themes_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard():
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{size['emoji']} {size['name']} ({size['min']}-{size['max']} симв.)",
                callback_data=f"size_sel_{size_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user: UserData):
    keyboard = []
    for ch in user.channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {ch['name'][:30]}", callback_data=f"channel_{ch['id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_settings_keyboard(channel_id: str, config: dict):
    theme = POSTING_THEMES.get(config.get('theme', 'ai_news'), POSTING_THEMES['ai_news'])
    size = POST_SIZES.get(config.get('size', 'medium'), POST_SIZES['medium'])
    interval_text = AUTO_INTERVALS.get(config.get('interval', 60), f"⏰ Каждые {config.get('interval', 60)} мин")
    status = "✅ Вкл" if config.get('active', True) else "⏸ Выкл"
    
    keyboard = [
        [InlineKeyboardButton(f"🎨 Тема: {theme['emoji']} {theme['name']}", callback_data=f"auto_theme_{channel_id}")],
        [InlineKeyboardButton(f"📏 Размер: {size['emoji']} {size['name']}", callback_data=f"auto_size_{channel_id}")],
        [InlineKeyboardButton(f"⏱ Интервал: {interval_text}", callback_data=f"auto_interval_{channel_id}")],
        [InlineKeyboardButton(f"🔄 Статус: {status}", callback_data=f"auto_toggle_{channel_id}")],
        [InlineKeyboardButton("💾 Сохранить и запустить", callback_data=f"auto_save_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = []
    for minutes, name in AUTO_INTERVALS.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"interval_set_{channel_id}_{minutes}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_auto_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff['name']} — {tariff['channels']} каналов, {tariff['posts_per_day']} постов/день",
                callback_data=f"tariff_select_{tariff_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = f"""
✨ *Добро пожаловать, {user.first_name}!* ✨

🤖 *Я бот для автоматического постинга с ИИ*

📝 *Мои возможности:*
• 🎨 20 разных тематик для постов
• 🤖 Генерация уникальных постов через GigaChat
• 📏 5 размеров постов
• 🎯 Автоматический постинг по расписанию
• 📢 Поддержка нескольких каналов
• 🔄 Перепост из других каналов

💎 *Все тарифы БЕСПЛАТНЫЕ!*
• Базовый: 1 канал, 10 постов/день
• Стандартный: 5 каналов, 30 постов/день
• Профессиональный: 15 каналов, 100 постов/день
• Unlimited: Безлимит каналов, 500 постов/день

👇 *Нажмите кнопку ниже, чтобы начать!*
"""
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    tariff = TARIFFS.get(user_data.tariff, TARIFFS["free"])
    
    if len(user_data.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ *Лимит каналов достигнут!*\n\n"
            f"Ваш тариф: {tariff['name']}\n"
            f"Максимум каналов: {tariff['channels']}\n\n"
            f"Используйте /tariffs чтобы выбрать тариф с большим количеством каналов",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📢 *Как добавить канал:*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте сюда ID канала в формате:\n"
        "   • `@username_канала`\n"
        "   • `-1001234567890`\n"
        "3️⃣ Или перешлите любое сообщение из канала\n\n"
        "📝 *Инструкция получения ID:*\n"
        "• Отправьте в канал любое сообщение\n"
        "• Перешлите его сюда\n\n"
        "⏸ *Отмена:* /cancel",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_channel'):
        return
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    text = update.message.text
    
    if text == "/cancel":
        context.user_data['awaiting_channel'] = False
        await update.message.reply_text("❌ Добавление канала отменено")
        return
    
    channel_id = None
    channel_name = "Новый канал"
    
    # Определяем ID канала
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
    elif text.startswith('@'):
        try:
            chat = await context.bot.get_chat(text)
            channel_id = str(chat.id)
            channel_name = chat.title
        except:
            await update.message.reply_text("❌ Не удалось найти канал. Проверьте username")
            return
    elif text.startswith('-100'):
        channel_id = text
        try:
            chat = await context.bot.get_chat(int(text))
            channel_name = chat.title
        except:
            channel_name = "Канал"
    
    if not channel_id:
        await update.message.reply_text("❌ Не удалось определить канал. Перешлите сообщение из канала или отправьте его ID")
        return
    
    # Проверяем, не добавлен ли уже
    for ch in user_data.channels:
        if ch.get("id") == channel_id:
            await update.message.reply_text(f"❌ Канал *{channel_name}* уже добавлен!", parse_mode='Markdown')
            return
    
    # Проверяем лимиты
    tariff = TARIFFS.get(user_data.tariff, TARIFFS["free"])
    if len(user_data.channels) >= tariff["channels"]:
        await update.message.reply_text("❌ Достигнут лимит каналов для вашего тарифа!")
        return
    
    # Добавляем канал
    user_data.channels.append({
        "id": channel_id,
        "name": channel_name,
        "added_at": time.time()
    })
    
    # Создаем конфиг автопостинга
    if channel_id not in user_data.auto_configs:
        user_data.auto_configs[channel_id] = {
            "theme": user_data.selected_theme,
            "size": user_data.selected_size,
            "interval": 60,
            "active": False,
            "last_post": 0
        }
    
    db.save()
    context.user_data['awaiting_channel'] = False
    
    await update.message.reply_text(
        f"✅ *Канал добавлен!*\n\n"
        f"📢 Название: {channel_name}\n"
        f"🆔 ID: `{channel_id}`\n"
        f"📊 Всего каналов: {len(user_data.channels)}/{tariff['channels']}\n\n"
        f"Теперь настройте автопостинг в меню 🤖 Автопостинг",
        parse_mode='Markdown'
    )

async def select_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        keyboard = await get_themes_keyboard()
        await query.edit_message_text(
            "🎨 *Выберите тему для постов*\n\n"
            "Доступно 20 уникальных тематик:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        keyboard = await get_themes_keyboard()
        await update.message.reply_text(
            "🎨 *Выберите тему для постов*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = await get_sizes_keyboard()
    text = "📏 *Выберите размер постов*\n\n" + "\n".join([f"{s['emoji']} {s['name']}: {s['min']}-{s['max']} символов" for s in POST_SIZES.values()])
    
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data.channels:
        await update.message.reply_text(
            "❌ *Нет добавленных каналов*\n\n"
            "Сначала добавьте канал через '📢 Добавить канал'",
            parse_mode='Markdown'
        )
        return
    
    text = "🤖 *Настройка автопостинга*\n\nВыберите канал для настройки:\n\n"
    
    keyboard = []
    for ch in user_data.channels:
        config = user_data.auto_configs.get(ch['id'], {})
        status = "✅" if config.get('active', False) else "⏸"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {ch['name'][:25]}",
                callback_data=f"edit_auto_{ch['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_auto_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("edit_auto_", "")
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if channel_id not in user_data.auto_configs:
        user_data.auto_configs[channel_id] = {
            "theme": user_data.selected_theme,
            "size": user_data.selected_size,
            "interval": 60,
            "active": False,
            "last_post": 0
        }
        db.save()
    
    config = user_data.auto_configs[channel_id]
    keyboard = await get_auto_settings_keyboard(channel_id, config)
    
    # Находим имя канала
    channel_name = "Канал"
    for ch in user_data.channels:
        if ch['id'] == channel_id:
            channel_name = ch['name']
            break
    
    await query.edit_message_text(
        f"⚙️ *Настройка автопостинга*\n\n"
        f"📢 Канал: {channel_name}\n\n"
        f"Настройте параметры:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data.channels:
        await update.message.reply_text("❌ Сначала добавьте канал!")
        return
    
    if not user_data.can_post():
        tariff = TARIFFS[user_data.tariff]
        await update.message.reply_text(
            f"❌ *Лимит постов на сегодня исчерпан!*\n\n"
            f"📊 Ваш тариф: {tariff['name']}\n"
            f"📝 Постов в день: {tariff['posts_per_day']}\n"
            f"⏳ Сброс завтра в 00:00\n\n"
            f"Используйте /tariffs для выбора другого тарифа",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_channels_keyboard(user_data)
    await update.message.reply_text(
        "📤 *В какой канал опубликовать пост?*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("channel_", "")
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data.can_post():
        await query.edit_message_text("❌ Лимит постов на сегодня!")
        return
    
    theme = user_data.selected_theme
    size = user_data.selected_size
    
    await query.edit_message_text(
        f"🤖 *Генерация поста...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[size]['name']}\n"
        f"⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    success = await db.post_to_channel(context, channel_id, theme, size)
    
    if success:
        tariff = TARIFFS[user_data.tariff]
        remaining = tariff["posts_per_day"] - user_data.daily_posts
        await query.edit_message_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"📊 Осталось постов сегодня: {remaining}/{tariff['posts_per_day']}\n\n"
            f"Чтобы опубликовать ещё, нажмите /menu",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard()
        )
    else:
        await query.edit_message_text("❌ Ошибка при публикации поста. Попробуйте позже.")

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    tariff = TARIFFS[user_data.tariff]
    
    if not user_data.channels:
        await update.message.reply_text("❌ У вас нет добавленных каналов. Используйте '📢 Добавить канал'")
        return
    
    text = f"📋 *Ваши каналы* ({len(user_data.channels)}/{tariff['channels']})\n\n"
    
    for ch in user_data.channels:
        config = user_data.auto_configs.get(ch['id'], {})
        status = "✅ Активен" if config.get('active', False) else "⏸ Неактивен"
        theme = POSTING_THEMES.get(config.get('theme', 'ai_news'), POSTING_THEMES['ai_news'])
        
        text += f"📢 *{ch['name']}*\n"
        text += f"🆔 `{ch['id']}`\n"
        text += f"🎨 Тема: {theme['emoji']} {theme['name']}\n"
        text += f"🔄 Автопостинг: {status}\n"
        text += f"⏱ Интервал: {config.get('interval', 60)} мин\n"
        text += f"📏 Размер: {POST_SIZES.get(config.get('size', 'medium'), POST_SIZES['medium'])['name']}\n"
        text += "─" * 20 + "\n"
    
    keyboard = []
    for ch in user_data.channels:
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить {ch['name'][:20]}", callback_data=f"delete_channel_{ch['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("delete_channel_", "")
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    user_data.channels = [ch for ch in user_data.channels if ch['id'] != channel_id]
    if channel_id in user_data.auto_configs:
        del user_data.auto_configs[channel_id]
    
    db.save()
    await query.edit_message_text("✅ Канал удален!")
    await my_channels(update, context)

async def tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    text = "💎 *Все тарифы БЕСПЛАТНЫЕ!*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        current = " ✅ *(Ваш тариф)*" if user_data.tariff == tariff_key else ""
        text += f"*{tariff['name']}*{current}\n"
        text += f"📊 Каналов: {tariff['channels']}\n"
        text += f"📝 Постов в день: {tariff['posts_per_day']}\n"
        text += f"🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}\n"
        text += f"⏰ Автопостинг: {'✅' if tariff['auto_posting'] else '❌'}\n"
        text += "─" * 25 + "\n\n"
    
    text += "\n💡 *Как повысить тариф?*\nПросто выберите нужный тариф в меню ниже!"
    
    keyboard = await get_tariffs_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("tariff_select_", "")
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if tariff_key in TARIFFS:
        user_data.tariff = tariff_key
        db.save()
        
        tariff = TARIFFS[tariff_key]
        await query.edit_message_text(
            f"✅ *Тариф изменен!*\n\n"
            f"Ваш новый тариф: {tariff['name']}\n"
            f"📊 Каналов: {tariff['channels']}\n"
            f"📝 Постов в день: {tariff['posts_per_day']}\n\n"
            f"Теперь вы можете добавить до {tariff['channels']} каналов!",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard()
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    tariff = TARIFFS[user_data.tariff]
    remaining = tariff["posts_per_day"] - user_data.daily_posts
    
    text = f"""
📊 *Ваша статистика*

👤 Пользователь: {user_data.first_name}
💎 Тариф: {tariff['name']}
📊 Каналов: {len(user_data.channels)}/{tariff['channels']}
📝 Постов сегодня: {user_data.daily_posts}/{tariff['posts_per_day']}
⏳ Осталось постов: {remaining}
🎨 Текущая тема: {POSTING_THEMES[user_data.selected_theme]['emoji']} {POSTING_THEMES[user_data.selected_theme]['name']}
📏 Текущий размер: {POST_SIZES[user_data.selected_size]['name']}

🔄 *Автопостинг:*
"""
    active_count = 0
    for ch in user_data.channels:
        config = user_data.auto_configs.get(ch['id'], {})
        if config.get('active', False):
            active_count += 1
            text += f"• {ch['name'][:20]}: ✅ {config.get('interval', 60)} мин\n"
    
    if active_count == 0:
        text += "• Нет активных автопостов\n"
    
    text += f"\n📈 Всего постов в боте: {len(db.post_history)}"
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        keyboard = await get_main_keyboard()
        await query.edit_message_text("🏠 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_channel":
        await add_channel(update, context)
    
    elif data == "select_theme":
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 *Выберите тему*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "select_size":
        keyboard = await get_sizes_keyboard()
        await query.edit_message_text("📏 *Выберите размер*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "auto_posting":
        await auto_posting(update, context)
    
    elif data == "post_now":
        await post_now(update, context)
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "tariffs":
        await tariffs(update, context)
    
    elif data == "stats":
        keyboard = await get_main_keyboard()
        await query.edit_message_text("📊 *Статистика*\nИспользуйте /stats", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    elif data.startswith("theme_sel_"):
        theme_key = data.replace("theme_sel_", "")
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        user_data.selected_theme = theme_key
        db.save()
        
        await query.edit_message_text(
            f"✅ *Тема выбрана!*\n\n"
            f"🎨 {POSTING_THEMES[theme_key]['emoji']} {POSTING_THEMES[theme_key]['name']}\n\n"
            f"Теперь выберите размер поста:",
            parse_mode='Markdown',
            reply_markup=await get_sizes_keyboard()
        )
    
    elif data.startswith("size_sel_"):
        size_key = data.replace("size_sel_", "")
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        user_data.selected_size = size_key
        db.save()
        
        await query.edit_message_text(
            f"✅ *Размер выбран!*\n\n"
            f"📏 {POST_SIZES[size_key]['name']} ({POST_SIZES[size_key]['min']}-{POST_SIZES[size_key]['max']} символов)\n\n"
            f"🎨 Тема: {POSTING_THEMES[user_data.selected_theme]['emoji']} {POSTING_THEMES[user_data.selected_theme]['name']}\n\n"
            f"Теперь вы можете опубликовать пост через главное меню или настроить автопостинг.",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard()
        )
    
    elif data.startswith("edit_auto_"):
        await edit_auto_config(update, context)
    
    elif data.startswith("auto_theme_"):
        channel_id = data.replace("auto_theme_", "")
        context.user_data['auto_channel'] = channel_id
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 Выберите тему для автопостинга:", reply_markup=keyboard)
    
    elif data.startswith("auto_size_"):
        channel_id = data.replace("auto_size_", "")
        context.user_data['auto_size_channel'] = channel_id
        keyboard = []
        for size_key, size in POST_SIZES.items():
            keyboard.append([InlineKeyboardButton(f"{size['emoji']} {size['name']}", callback_data=f"auto_set_size_{channel_id}_{size_key}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_auto_{channel_id}")])
        await query.edit_message_text("📏 Выберите размер:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("auto_interval_"):
        channel_id = data.replace("auto_interval_", "")
        keyboard = await get_interval_keyboard(channel_id)
        await query.edit_message_text("⏱ Выберите интервал публикации:", reply_markup=keyboard)
    
    elif data.startswith("interval_set_"):
        parts = data.split("_")
        channel_id = parts[2]
        interval = int(parts[3])
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        
        if channel_id in user_data.auto_configs:
            user_data.auto_configs[channel_id]['interval'] = interval
            db.save()
        
        config = user_data.auto_configs[channel_id]
        keyboard = await get_auto_settings_keyboard(channel_id, config)
        await query.edit_message_text(
            f"✅ Интервал установлен: {AUTO_INTERVALS.get(interval, f'{interval} минут')}",
            reply_markup=keyboard
        )
    
    elif data.startswith("auto_toggle_"):
        channel_id = data.replace("auto_toggle_", "")
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        
        if channel_id in user_data.auto_configs:
            user_data.auto_configs[channel_id]['active'] = not user_data.auto_configs[channel_id].get('active', False)
            db.save()
        
        config = user_data.auto_configs[channel_id]
        keyboard = await get_auto_settings_keyboard(channel_id, config)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    elif data.startswith("auto_save_"):
        channel_id = data.replace("auto_save_", "")
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        
        if channel_id in user_data.auto_configs:
            user_data.auto_configs[channel_id]['active'] = True
            db.save()
        
        await query.edit_message_text(
            f"✅ *Настройки автопостинга сохранены!*\n\n"
            f"Бот будет автоматически публиковать посты в выбранный канал.",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard()
        )
    
    elif data.startswith("auto_set_size_"):
        parts = data.split("_")
        channel_id = parts[3]
        size_key = parts[4]
        user_id = query.from_user.id
        user_data = db.get_user(user_id)
        
        if channel_id in user_data.auto_configs:
            user_data.auto_configs[channel_id]['size'] = size_key
            db.save()
        
        config = user_data.auto_configs[channel_id]
        keyboard = await get_auto_settings_keyboard(channel_id, config)
        await query.edit_message_text(
            f"✅ Размер установлен: {POST_SIZES[size_key]['name']}",
            reply_markup=keyboard
        )
    
    elif data.startswith("channel_"):
        await publish_post(update, context)
    
    elif data.startswith("delete_channel_"):
        await delete_channel(update, context)
    
    elif data.startswith("tariff_select_"):
        await select_tariff(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь и инструкция*

📌 *Как пользоваться ботом:*

1️⃣ *Добавьте канал*
• Нажмите "📢 Добавить канал"
• Добавьте бота в канал как администратора
• Перешлите сообщение из канала или отправьте его ID

2️⃣ *Выберите тему и размер*
• 🎨 Выберите тему из 20 вариантов
• 📏 Выберите размер поста
• Темы и размеры можно менять в любой момент

3️⃣ *Опубликуйте пост*
• Нажмите "📤 Опубликовать пост"
• Выберите канал
• Бот сгенерирует уникальный пост через ИИ

4️⃣ *Настройте автопостинг*
• 🤖 Автопостинг → выберите канал
• Настройте тему, размер, интервал
• Включите автопостинг

🎨 *20 тем:*
""" + "\n".join([f"{t['emoji']} {t['name']}" for t in POSTING_THEMES.values()]) + """

📏 *5 размеров:*
• Мини: 100-300 символов
• Короткий: 301-600 символов  
• Средний: 601-1000 символов
• Длинный: 1001-1500 символов
• Максимальный: 1501-2000 символов

💎 *Все тарифы БЕСПЛАТНЫЕ!*

❓ *Вопросы:* Напишите @ для поддержки
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def auto_post_check(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и выполнение автопостинга"""
    now = time.time()
    
    for user_id, user_data in db.users.items():
        for channel in user_data.channels:
            channel_id = channel['id']
            config = user_data.auto_configs.get(channel_id, {})
            
            if not config.get('active', False):
                continue
            
            last_post = config.get('last_post', 0)
            interval = config.get('interval', 60) * 60
            
            if now - last_post >= interval:
                if user_data.can_post():
                    theme = config.get('theme', user_data.selected_theme)
                    size = config.get('size', user_data.selected_size)
                    
                    success = await db.post_to_channel(context, channel_id, theme, size)
                    
                    if success:
                        config['last_post'] = now
                        db.save()
                        logger.info(f"Автопостинг: канал {channel_id}, тема {theme}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ *Произошла ошибка. Попробуйте позже.*",
            parse_mode='Markdown'
        )

# ==================== ЗАПУСК ====================
def main():
    db.load()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tariffs", tariffs))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("cancel", lambda u,c: None))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_channel_input))
    
    application.add_error_handler(error_handler)
    
    # Автопостинг каждые 30 секунд
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_check, interval=30, first=10)
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"🎨 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"📏 Доступно размеров: {len(POST_SIZES)}")
    logger.info(f"💎 Все тарифы бесплатные!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
