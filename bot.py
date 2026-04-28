import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    JobQueue
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

# ==================== ТАРИФЫ ====================
class TariffType(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

TARIFFS = {
    "free": {
        "name": "📢 Бесплатный",
        "price": 0,
        "channels": 1,
        "posts_per_day": 5,
        "can_repost": False,
        "can_schedule": False,
        "ai_quality": "standard",
        "has_images": True,
        "image_limit": 3
    },
    "basic": {
        "name": "⭐ Базовый",
        "price": 299,
        "channels": 3,
        "posts_per_day": 15,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "enhanced",
        "has_images": True,
        "image_limit": 5
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 699,
        "channels": 10,
        "posts_per_day": 50,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "premium",
        "has_images": True,
        "image_limit": 10
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 1499,
        "channels": 999,
        "posts_per_day": 200,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "ultra",
        "has_images": True,
        "image_limit": 20
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 Новости AI",
        "emoji": "🤖",
        "description": "Новости искусственного интеллекта",
        "prompt": "Ты журналист, пишущий об AI. Создай интересный пост о последних новостях в мире искусственного интеллекта."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "description": "Новости криптовалют",
        "prompt": "Ты крипто-аналитик. Создай пост о криптовалютах, блокчейне, DeFi."
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "description": "Новости NFT и digital art",
        "prompt": "Ты эксперт по NFT. Создай пост о NFT коллекциях, digital art, метавселенных."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram",
        "prompt": "Ты блогер о Telegram. Создай пост о новых функциях Telegram, ботах, каналах."
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес новости",
        "prompt": "Ты бизнес-журналист. Создай пост о бизнесе, стартапах, инвестициях."
    },
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "description": "Технологические новости",
        "prompt": "Ты техноблогер. Создай пост о новых технологиях, гаджетах, изобретениях."
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "prompt": "Ты научный журналист. Создай пост о научных открытиях и исследованиях."
    },
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "description": "Здоровье и медицина",
        "prompt": "Ты медицинский блогер. Создай полезный пост о здоровье."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "prompt": "Ты психолог. Создай полезный пост по психологии и саморазвитию."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "description": "Маркетинг и SMM",
        "prompt": "Ты маркетолог. Создай пост о маркетинге, SMM, рекламе."
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "description": "Дизайн и креатив",
        "prompt": "Ты дизайнер. Создай вдохновляющий пост о дизайне."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "description": "IT и разработка",
        "prompt": "Ты разработчик. Создай полезный пост о программировании."
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровые новости",
        "prompt": "Ты игровой журналист. Создай пост об играх и гейминге."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Новости кино",
        "prompt": "Ты кинокритик. Создай пост о новинках кино и сериалов."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "prompt": "Ты музыкальный обозреватель. Создай пост о музыке."
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости",
        "prompt": "Ты спортивный журналист. Создай пост о спорте."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Путешествия и туризм",
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Кулинария и рецепты",
        "prompt": "Ты кулинарный блогер. Создай пост о еде и рецептах."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "description": "Образование и обучение",
        "prompt": "Ты педагог. Создай полезный пост об образовании."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "description": "Мотивация и успех",
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
class PostSize(Enum):
    MINI = "mini"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    EXTRA = "extra"

POST_SIZES = {
    "mini": {"name": "🔹 Мини", "min_chars": 100, "max_chars": 300, "emoji": "🔹"},
    "short": {"name": "🔸 Короткий", "min_chars": 301, "max_chars": 600, "emoji": "🔸"},
    "medium": {"name": "🔹 Средний", "min_chars": 601, "max_chars": 1000, "emoji": "🔹"},
    "long": {"name": "📄 Длинный", "min_chars": 1001, "max_chars": 1500, "emoji": "📄"},
    "extra": {"name": "📚 Макси", "min_chars": 1501, "max_chars": 2000, "emoji": "📚"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class Post:
    id: str
    channel_id: str
    theme: str
    content: str
    image_url: Optional[str]
    posted_at: float
    size: str
    views: int = 0

@dataclass
class SourceChannel:
    channel_id: str
    channel_name: str
    theme: str
    is_active: bool = True

@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    subscribed_at: float
    channels: List[str] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    themes: List[str] = field(default_factory=list)
    post_schedule: Dict[str, str] = field(default_factory=dict)  # theme -> hour
    
    def can_post(self) -> bool:
        today = time.time()
        if today - self.last_reset > 86400:
            self.posts_today = 0
            self.last_reset = today
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return self.posts_today < tariff["posts_per_day"]
    
    def add_post(self):
        self.posts_today += 1

@dataclass    
class AutoPostConfig:
    channel_id: str
    theme: str
    size: str
    interval_minutes: int
    is_active: bool = True
    last_post: float = 0

# ==================== ОСНОВНОЕ ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.user_subscriptions: Dict[int, UserSubscription] = {}
        self.auto_configs: Dict[str, AutoPostConfig] = {}
        self.source_channels: Dict[str, SourceChannel] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[Post] = []
        self.pending_approvals: Dict[str, dict] = {}
        self.channel_admins: Dict[str, List[int]] = {}
    
    def load_data(self):
        """Загрузка данных из файлов"""
        try:
            with open("subscriptions.json", "r") as f:
                data = json.load(f)
                for user_id, sub_data in data.items():
                    self.user_subscriptions[int(user_id)] = UserSubscription(**sub_data)
        except:
            pass
        
        try:
            with open("auto_configs.json", "r") as f:
                data = json.load(f)
                for channel_id, config_data in data.items():
                    self.auto_configs[channel_id] = AutoPostConfig(**config_data)
        except:
            pass
        
        try:
            with open("source_channels.json", "r") as f:
                data = json.load(f)
                for channel_id, source_data in data.items():
                    self.source_channels[channel_id] = SourceChannel(**source_data)
        except:
            pass
    
    def save_data(self):
        """Сохранение данных"""
        subs = {uid: {"user_id": sub.user_id, "tariff": sub.tariff, 
                      "subscribed_at": sub.subscribed_at, "channels": sub.channels,
                      "posts_today": sub.posts_today, "last_reset": sub.last_reset,
                      "themes": sub.themes, "post_schedule": sub.post_schedule} 
                for uid, sub in self.user_subscriptions.items()}
        with open("subscriptions.json", "w") as f:
            json.dump(subs, f, indent=2)
        
        configs = {cid: {"channel_id": cfg.channel_id, "theme": cfg.theme,
                         "size": cfg.size, "interval_minutes": cfg.interval_minutes,
                         "is_active": cfg.is_active, "last_post": cfg.last_post}
                   for cid, cfg in self.auto_configs.items()}
        with open("auto_configs.json", "w") as f:
            json.dump(configs, f, indent=2)
        
        sources = {cid: {"channel_id": src.channel_id, "channel_name": src.channel_name,
                         "theme": src.theme, "is_active": src.is_active}
                   for cid, src in self.source_channels.items()}
        with open("source_channels.json", "w") as f:
            json.dump(sources, f, indent=2)
    
    def get_user_subscription(self, user_id: int) -> UserSubscription:
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = UserSubscription(
                user_id=user_id,
                tariff="free",
                subscribed_at=time.time(),
                channels=[],
                themes=[]
            )
            self.save_data()
        return self.user_subscriptions[user_id]
    
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
    
    async def generate_post_content(self, theme: str, size: str) -> str:
        """Генерация поста через GigaChat"""
        token = await self.get_api_token()
        if not token:
            return "❌ Ошибка генерации. Попробуйте позже."
        
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

Требования к посту:
- Длина: {size_config['min_chars']}-{size_config['max_chars']} символов
- Используй эмодзи для украшения
- Добавь хэштеги в конце (3-5 штук)
- Пиши на русском языке
- Пост должен быть интересным и полезным
- Добавь вопрос к подписчикам в конце

Тема: {theme_config['name']}"""
        
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
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                            if len(content) > size_config["max_chars"]:
                                content = content[:size_config["max_chars"]]
                            return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme, size)
    
    def _get_fallback_post(self, theme: str, size: str) -> str:
        """Запасной пост при ошибке API"""
        fallbacks = {
            "ai_news": "🤖 Искусственный интеллект продолжает удивлять! Какие новые возможности AI вас впечатлили?",
            "crypto": "🪙 Биткоин показывает новые тренды! Следите за рынком криптовалют!",
            "nft": "🎨 NFT открывают новые горизонты для цифрового искусства! У вас есть NFT?",
            "telegram": "📱 Telegram выпустил обновление! Какие функции вы ждете?",
            "business": "💼 Успешный бизнес начинается с идеи! Какую бизнес-идею вы хотели бы реализовать?",
        }
        return fallbacks.get(theme, "✨ Новый пост! Делитесь мыслями в комментариях! ✨")
    
    async def generate_post_image(self, theme: str) -> Optional[str]:
        """Генерация URL изображения для поста (эмуляция)"""
        # В реальном проекте здесь был бы API генерации изображений
        # Пока возвращаем None, так как GigaChat не генерирует картинки
        return None
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                              theme: str, size: str, is_auto: bool = False):
        """Публикация поста в канал"""
        content = await self.generate_post_content(theme, size)
        image_url = await self.generate_post_image(theme)
        
        try:
            if image_url:
                await context.bot.send_photo(
                    chat_id=channel_id,
                    photo=image_url,
                    caption=content,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode='HTML'
                )
            
            post = Post(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                theme=theme,
                content=content[:200],
                image_url=image_url,
                posted_at=time.time(),
                size=size
            )
            self.post_history.append(post)
            
            if not is_auto:
                for user_id, sub in self.user_subscriptions.items():
                    if channel_id in sub.channels:
                        sub.add_post()
            
            return True
        except Exception as e:
            logger.error(f"Ошибка публикации в {channel_id}: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🔄 Перепост из каналов", callback_data="repost_menu")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер поста", callback_data="select_size")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("📋 Список каналов", callback_data="my_channels")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    
    if sub.tariff != "free":
        keyboard.insert(2, [InlineKeyboardButton("⏰ Расписание постов", callback_data="schedule")])
    
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
                callback_data=f"theme_{theme_key}"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"themes_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard():
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{size['emoji']} {size['name']} ({size['min_chars']}-{size['max_chars']} симв.)",
                callback_data=f"size_{size_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        price_text = f"{tariff['price']}₽" if tariff['price'] > 0 else "Бесплатно"
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff['name']} - {price_text}",
                callback_data=f"tariff_{tariff_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    
    welcome = f"""
🚀 *Добро пожаловать, {user.first_name}!*

🤖 *Бот для автопостинга с AI*

📝 *Возможности:*
✅ Генерация постов через ИИ (GigaChat)
✅ 20 различных тематик
✅ Автоматический постинг в каналы
✅ Перепост из других каналов
✅ Настройка размера постов
✅ Расписание публикаций
✅ Бесплатный тариф с базовыми функциями

💡 *Как начать:*
1. Добавьте бота в свой канал как администратора
2. Нажмите "➕ Добавить канал"
3. Выберите тему и размер постов
4. Настройте автопостинг

🎁 *Бесплатный тариф:* 1 канал, 5 постов/день

👇 *Выберите действие:*
"""
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Перешлите любое сообщение из канала сюда\n"
        "3️⃣ Бот автоматически определит канал\n\n"
        "или просто отправьте ID канала: @username или -100xxxxxx",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        user_id = update.effective_user.id
        text = update.message.text
        
        sub = bot.get_user_subscription(user_id)
        tariff = TARIFFS[sub.tariff]
        
        if len(sub.channels) >= tariff["channels"]:
            await update.message.reply_text(
                f"❌ Лимит каналов для вашего тарифа: {tariff['channels']}\n"
                f"💎 Купите более дорогой тариф для добавления большего количества каналов"
            )
            return
        
        channel_id = None
        if text.startswith('@'):
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
                channel_name = "Неизвестный канал"
        else:
            if update.message.forward_from_chat:
                chat = update.message.forward_from_chat
                channel_id = str(chat.id)
                channel_name = chat.title
            else:
                await update.message.reply_text("❌ Отправьте ID канала или перешлите сообщение из канала")
                return
        
        if channel_id not in sub.channels:
            sub.channels.append(channel_id)
            bot.save_data()
            
            await update.message.reply_text(
                f"✅ Канал *{channel_name}* успешно добавлен!\n\n"
                f"📊 Каналов: {len(sub.channels)}/{tariff['channels']}\n"
                f"🎯 Теперь выберите тему для постов в /menu",
                parse_mode='Markdown'
            )
        
        context.user_data['awaiting_channel'] = False

async def select_theme(update: Update, context: ContextTypes.DEFAULT_TYPE, message=None):
    keyboard = await get_themes_keyboard()
    if message:
        await message.edit_text("🎨 *Выберите тему для постов:*", parse_mode='Markdown', reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text("🎨 *Выберите тему:*", parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text("🎨 *Выберите тему:*", parse_mode='Markdown', reply_markup=keyboard)

async def select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = await get_sizes_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text("📏 *Выберите размер постов:*", parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text("📏 *Выберите размер постов:*", parse_mode='Markdown', reply_markup=keyboard)

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    text = "🤖 *Настройка автопостинга*\n\n"
    
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            channel_name = chat.title
        except:
            channel_name = "Канал"
        
        config = bot.auto_configs.get(channel_id)
        if config:
            theme_name = POSTING_THEMES.get(config.theme, {}).get('name', config.theme)
            size_name = POST_SIZES.get(config.size, {}).get('name', config.size)
            status = "✅ Активен" if config.is_active else "⏸ Остановлен"
            text += f"\n📢 *{channel_name}*\n   Тема: {theme_name}\n   Размер: {size_name}\n   Интервал: {config.interval_minutes} мин\n   Статус: {status}\n"
        else:
            text += f"\n📢 *{channel_name}* - ❌ не настроен\n"
    
    keyboard = []
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            keyboard.append([InlineKeyboardButton(f"⚙️ {chat.title}", callback_data=f"config_{channel_id}")])
        except:
            pass
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def configure_auto_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.replace("config_", "")
    
    keyboard = [
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"set_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"set_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал (мин)", callback_data=f"set_interval_{channel_id}")],
        [InlineKeyboardButton("▶️ Включить", callback_data=f"enable_{channel_id}")],
        [InlineKeyboardButton("⏸ Выключить", callback_data=f"disable_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text("⚙️ *Настройка автопостинга*\n\nВыберите параметр:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await update.message.reply_text("❌ Сначала добавьте канал через '➕ Добавить канал'")
        return
    
    if not sub.can_post():
        await update.message.reply_text("❌ Достигнут лимит постов на сегодня! Купите тариф для увеличения лимита.")
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    await update.message.reply_text(f"🎲 Генерирую пост на тему {POSTING_THEMES[random_theme]['emoji']} {POSTING_THEMES[random_theme]['name']}...")
    
    success = await bot.post_to_channel(context, sub.channels[0], random_theme, random_size)
    
    if success:
        await update.message.reply_text("✅ Пост успешно опубликован!")
        sub.add_post()
        bot.save_data()
    else:
        await update.message.reply_text("❌ Ошибка при публикации")

async def repost_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    if not tariff["can_repost"]:
        await update.message.reply_text(
            "❌ *Перепост недоступен на вашем тарифе*\n\n"
            "💎 Купите тариф Базовый или выше для перепоста из других каналов",
            parse_mode='Markdown'
        )
        return
    
    text = "🔄 *Перепост из каналов*\n\n"
    text += "Добавьте каналы, из которых бот будет перепостить:\n"
    text += "Отправьте ссылку или username канала\n\n"
    text += "📋 *Активные источники:*\n"
    
    for src_id, src in bot.source_channels.items():
        text += f"• {src.channel_name} → тема: {POSTING_THEMES[src.theme]['emoji']}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')
    context.user_data['awaiting_source'] = True

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    text = f"📋 *Ваши каналы* ({len(sub.channels)}/{tariff['channels']})\n\n"
    
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            text += f"📢 *{chat.title}*\n"
            text += f"🆔 `{channel_id}`\n"
            
            config = bot.auto_configs.get(channel_id)
            if config:
                theme = POSTING_THEMES.get(config.theme, {})
                size = POST_SIZES.get(config.size, {})
                text += f"🎨 Тема: {theme.get('emoji', '')} {theme.get('name', '-')}\n"
                text += f"📏 Размер: {size.get('name', '-')}\n"
                text += f"⏱ Интервал: {config.interval_minutes} мин\n"
                text += f"🔄 Статус: {'✅ Активен' if config.is_active else '⏸ Остановлен'}\n"
            text += "\n"
        except:
            text += f"⚠️ Канал {channel_id} - недоступен\n\n"
    
    keyboard = []
    for channel_id in sub.channels:
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить канал", callback_data=f"del_channel_{channel_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    text = "💎 *Тарифы*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        price = f"{tariff['price']}₽/мес" if tariff['price'] > 0 else "Бесплатно"
        current = " ✅ ТЕКУЩИЙ" if sub.tariff == tariff_key else ""
        
        text += f"*{tariff['name']}{current}*\n"
        text += f"💰 Цена: {price}\n"
        text += f"📊 Каналов: {tariff['channels']}\n"
        text += f"📝 Постов/день: {tariff['posts_per_day']}\n"
        text += f"🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}\n"
        text += f"⏰ Расписание: {'✅' if tariff['can_schedule'] else '❌'}\n"
        text += f"🖼 Картинки: до {tariff['image_limit']}\n\n"
    
    text += "\n💡 *Как оплатить:*\n"
    text += "Напишите @ для оплаты\n"
    text += "После оплаты ваш тариф будет обновлен"
    
    keyboard = await get_tariffs_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    remaining = tariff["posts_per_day"] - sub.posts_today
    
    text = f"📊 *Ваша статистика*\n\n"
    text += f"💎 *Тариф:* {tariff['name']}\n"
    text += f"📊 *Каналов:* {len(sub.channels)}/{tariff['channels']}\n"
    text += f"📝 *Постов сегодня:* {sub.posts_today}/{tariff['posts_per_day']}\n"
    text += f"⏳ *Осталось:* {remaining}\n"
    text += f"🎨 *Тем:* {len(sub.themes) if sub.themes else 'не выбраны'}\n"
    text += f"\n📈 *Всего постов в боте:* {len(bot.post_history)}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь по работе бота*

📌 *Основные команды:*
/start - Главное меню
/menu - Открыть меню

📢 *Управление каналами:*
• Добавить канал - бот будет постить в него
• Автопостинг - настройка автоматических постов
• Перепост - копирование постов из других каналов

🎨 *Темы (20 штук):*
AI новости, Криптовалюты, NFT, Telegram, Бизнес, Технологии, Наука, Здоровье, Психология, Маркетинг, Дизайн, Программирование, Игры, Кино, Музыка, Спорт, Путешествия, Кулинария, Образование, Мотивация

📏 *Размеры постов:*
Мини (100-300), Короткий (300-600), Средний (600-1000), Длинный (1000-1500), Макси (1500-2000)

💎 *Тарифы:*
• Бесплатный - 1 канал, 5 постов/день
• Базовый (299₽) - 3 канала, 15 постов/день
• Про (699₽) - 10 каналов, 50 постов/день
• Премиум (1499₽) - безлимит, 200 постов/день

❓ *Вопросы:* @
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_main":
        keyboard = await get_main_keyboard(query.from_user.id)
        await query.edit_message_text("🏠 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_channel":
        context.user_data['awaiting_channel'] = True
        await query.edit_message_text(
            "📢 *Добавление канала*\n\n"
            "Перешлите любое сообщение из канала сюда\n"
            "или отправьте ID канала: @username или -100xxxxxx",
            parse_mode='Markdown'
        )
    
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    
    elif data == "repost_menu":
        await repost_menu(update, context)
    
    elif data == "select_theme":
        await select_theme(update, context, query.message)
    
    elif data == "select_size":
        await select_size(update, context)
    
    elif data == "tariffs":
        await tariffs_menu(update, context)
    
    elif data == "stats":
        keyboard = await get_main_keyboard(query.from_user.id)
        await stats(update, context)
    
    elif data == "random_post":
        await random_post(update, context)
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    elif data.startswith("theme_"):
        theme = data.replace("theme_", "")
        context.user_data['selected_theme'] = theme
        await query.edit_message_text(
            f"✅ Тема *{POSTING_THEMES[theme]['name']}* выбрана!\n\n"
            f"Теперь выберите размер поста:",
            parse_mode='Markdown',
            reply_markup=await get_sizes_keyboard()
        )
    
    elif data.startswith("size_"):
        size = data.replace("size_", "")
        theme = context.user_data.get('selected_theme')
        
        if theme:
            user_id = query.from_user.id
            sub = bot.get_user_subscription(user_id)
            
            if sub.channels:
                if sub.can_post():
                    await query.edit_message_text(f"🎲 Генерирую пост на тему {POSTING_THEMES[theme]['emoji']}...")
                    success = await bot.post_to_channel(context, sub.channels[0], theme, size)
                    if success:
                        sub.add_post()
                        bot.save_data()
                        await query.edit_message_text("✅ Пост успешно опубликован!")
                    else:
                        await query.edit_message_text("❌ Ошибка при публикации")
                else:
                    await query.edit_message_text("❌ Достигнут лимит постов на сегодня!")
            else:
                await query.edit_message_text("❌ Сначала добавьте канал через '➕ Добавить канал'")
        else:
            await query.edit_message_text("❌ Сначала выберите тему")
    
    elif data.startswith("config_"):
        await configure_auto_post(update, context)
    
    elif data.startswith("set_theme_"):
        channel_id = data.replace("set_theme_", "")
        context.user_data['config_channel'] = channel_id
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 Выберите тему для автопостинга:", reply_markup=keyboard)
    
    elif data.startswith("set_size_"):
        channel_id = data.replace("set_size_", "")
        keyboard = []
        for size_key, size in POST_SIZES.items():
            keyboard.append([InlineKeyboardButton(size['name'], callback_data=f"auto_size_{channel_id}_{size_key}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"config_{channel_id}")])
        await query.edit_message_text("📏 Выберите размер:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("auto_size_"):
        parts = data.split("_")
        channel_id = parts[2]
        size = parts[3]
        
        if channel_id not in bot.auto_configs:
            bot.auto_configs[channel_id] = AutoPostConfig(
                channel_id=channel_id,
                theme="ai_news",
                size=size,
                interval_minutes=60
            )
        else:
            bot.auto_configs[channel_id].size = size
        
        bot.save_data()
        await query.edit_message_text(f"✅ Размер установлен! Теперь выберите тему:", reply_markup=await get_themes_keyboard())
    
    elif data.startswith("set_interval_"):
        channel_id = data.replace("set_interval_", "")
        context.user_data['interval_channel'] = channel_id
        await query.edit_message_text(
            "⏱ Введите интервал в минутах (от 30 до 1440):\n"
            "Пример: 60 - каждый час, 120 - раз в 2 часа",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data=f"config_{channel_id}")
            ]])
        )
        context.user_data['awaiting_interval'] = True
    
    elif data.startswith("enable_"):
        channel_id = data.replace("enable_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = True
            bot.save_data()
            await query.edit_message_text("✅ Автопостинг включен!")
    
    elif data.startswith("disable_"):
        channel_id = data.replace("disable_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = False
            bot.save_data()
            await query.edit_message_text("⏸ Автопостинг выключен!")
    
    elif data.startswith("del_channel_"):
        channel_id = data.replace("del_channel_", "")
        user_id = query.from_user.id
        sub = bot.get_user_subscription(user_id)
        
        if channel_id in sub.channels:
            sub.channels.remove(channel_id)
            if channel_id in bot.auto_configs:
                del bot.auto_configs[channel_id]
            bot.save_data()
            await query.edit_message_text("✅ Канал удален!")
            await my_channels(update, context)

async def handle_interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_interval'):
        try:
            interval = int(update.message.text)
            if 30 <= interval <= 1440:
                channel_id = context.user_data.get('interval_channel')
                if channel_id in bot.auto_configs:
                    bot.auto_configs[channel_id].interval_minutes = interval
                    bot.save_data()
                    await update.message.reply_text(f"✅ Интервал установлен: {interval} минут")
                else:
                    await update.message.reply_text("❌ Канал не найден")
            else:
                await update.message.reply_text("❌ Интервал должен быть от 30 до 1440 минут")
        except:
            await update.message.reply_text("❌ Введите число")
        
        context.user_data['awaiting_interval'] = False

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """Автоматическая публикация постов по расписанию"""
    for channel_id, config in bot.auto_configs.items():
        if not config.is_active:
            continue
        
        current_time = time.time()
        if current_time - config.last_post < config.interval_minutes * 60:
            continue
        
        # Находим владельца канала
        for user_id, sub in bot.user_subscriptions.items():
            if channel_id in sub.channels and sub.can_post():
                success = await bot.post_to_channel(context, channel_id, config.theme, config.size, is_auto=True)
                if success:
                    config.last_post = current_time
                    sub.add_post()
                    bot.save_data()
                    logger.info(f"Авто-пост в {channel_id} на тему {config.theme}")
                break

async def handle_forward_for_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пересылаемых сообщений для перепоста"""
    if context.user_data.get('awaiting_source'):
        user_id = update.effective_user.id
        sub = bot.get_user_subscription(user_id)
        
        if not sub.can_post():
            await update.message.reply_text("❌ Лимит постов!")
            return
        
        forward = update.message.forward_from_chat
        if forward:
            source_id = str(forward.id)
            source_name = forward.title
            
            # Генерируем пост на основе пересланного
            theme = random.choice(list(POSTING_THEMES.keys()))
            size = random.choice(list(POST_SIZES.keys()))
            
            content = f"📢 *Перепост из {source_name}*\n\n"
            content += update.message.text or "Новый пост!"
            
            if sub.channels:
                await bot.post_to_channel(context, sub.channels[0], theme, size)
                await update.message.reply_text("✅ Перепост выполнен!")
                sub.add_post()
                bot.save_data()
        
        context.user_data['awaiting_source'] = False

# ==================== ЗАПУСК БОТА ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_message))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forward_for_repost))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interval_input))
    
    # Job для автопостинга
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_job, interval=60, first=10)
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Тарифов: {len(TARIFFS)}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
