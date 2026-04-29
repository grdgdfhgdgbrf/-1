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

# ==================== ТАРИФЫ (ВСЕ БЕСПЛАТНЫЕ) ====================
TARIFFS = {
    "starter": {
        "name": "🌟 Стартовый",
        "emoji": "🌟",
        "channels": 1,
        "posts_per_day": 50,
        "min_interval": 10,  # секунд
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#00CED1"
    },
    "blogger": {
        "name": "📝 Блогер",
        "emoji": "📝",
        "channels": 3,
        "posts_per_day": 200,
        "min_interval": 5,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#FF6B6B"
    },
    "influencer": {
        "name": "⭐ Инфлюенсер",
        "emoji": "⭐",
        "channels": 10,
        "posts_per_day": 500,
        "min_interval": 3,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#FFD700"
    },
    "pro": {
        "name": "👑 PRO",
        "emoji": "👑",
        "channels": 100,
        "posts_per_day": 999999,
        "min_interval": 1,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "#9B59B6"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 ИИ и Нейросети",
        "emoji": "🤖",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#ИИ #Нейросети #AI #ChatGPT #ИскусственныйИнтеллект",
        "prompt": "Ты популярный блогер, пишущий об ИИ. Создай ВИРУСНЫЙ пост о нейросетях, ChatGPT или искусственном интеллекте. Используй эмодзи, будь современным и трендовым."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "description": "Крипто-новости и тренды",
        "hashtags": "#Криптовалюта #Биткоин #Blockchain #DeFi #Web3",
        "prompt": "Ты крипто-трейдер и аналитик. Создай пост о криптовалютах, биткоине, альткоинах или блокчейне. Добавь актуальную аналитику."
    },
    "nft": {
        "name": "🎨 NFT и Цифровое Искусство",
        "emoji": "🎨",
        "description": "Мир NFT и цифрового искусства",
        "hashtags": "#NFT #DigitalArt #Метавселенная #Web3 #NFTart",
        "prompt": "Ты NFT-коллекционер и арт-критик. Создай пост о NFT коллекциях, цифровом искусстве или метавселенных."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости и фишки Telegram",
        "hashtags": "#Telegram #ТГ #Мессенджер #TelegramUpdates",
        "prompt": "Ты эксперт по Telegram. Создай пост о новых функциях Telegram, полезных ботах или фишках мессенджера."
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес идеи и стратегии",
        "hashtags": "#Бизнес #Предпринимательство #Стартап #Маркетинг",
        "prompt": "Ты успешный предприниматель. Создай пост о бизнесе, стартапах, управлении или финансах."
    },
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "description": "Новости технологий",
        "hashtags": "#Технологии #Гаджеты #Инновции #TechNews",
        "prompt": "Ты техноблогер. Создай пост о новых технологиях, гаджетах или научных открытиях."
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "hashtags": "#Наука #Физика #Космос #Открытия #Science",
        "prompt": "Ты научный журналист. Создай пост о научных открытиях, космосе или интересных фактах."
    },
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "description": "Здоровье и ЗОЖ",
        "hashtags": "#Здоровье #ЗОЖ #Фитнес #Красота",
        "prompt": "Ты врач и блогер о здоровье. Создай полезный пост о здоровье, питании или фитнесе."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация",
        "prompt": "Ты психолог. Создай вдохновляющий пост о психологии, отношениях или саморазвитии."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Таргет #Реклама",
        "prompt": "Ты маркетолог-практик. Создай пост о маркетинге, SMM, рекламе или продвижении."
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #UIUX #ГрафическийДизайн #Креатив",
        "prompt": "Ты дизайнер. Создай вдохновляющий пост о дизайне, трендах или креативных решениях."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "description": "IT и разработка",
        "hashtags": "#Программирование #IT #Код #Разработка",
        "prompt": "Ты разработчик. Создай полезный пост о программировании, языках кода или IT-карьере."
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровая индустрия",
        "hashtags": "#Gaming #Игры #Киберспорт #ИгровыеНовости",
        "prompt": "Ты игровой журналист. Создай пост об играх, гейминге или игровой индустрии."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Кино новинки",
        "hashtags": "#Кино #Фильмы #Сериалы #НовинкиКино",
        "prompt": "Ты кинокритик. Создай пост о новинках кино, сериалов или кинопремьерах."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Плейлист #Хиты",
        "prompt": "Ты музыкальный обозреватель. Создай пост о музыке, новых релизах или исполнителях."
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости",
        "hashtags": "#Спорт #Футбол #Баскетбол #Теннис",
        "prompt": "Ты спортивный журналист. Создай пост о спорте, матчах или спортивных достижениях."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Трэвел #Туризм #Вояж",
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях, странах или туристических лайфхаках."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Рецепты и еда",
        "hashtags": "#Кулинария #Рецепты #Вкусно #Готовка",
        "prompt": "Ты фуд-блогер. Создай пост с рецептом или кулинарными советами."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "description": "Обучение и курсы",
        "hashtags": "#Образование #Учеба #Курсы #Обучение",
        "prompt": "Ты педагог и блогер. Создай полезный пост об образовании или обучении."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Цели #Развитие",
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост о мотивации, целях или успехе."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "micro": {"name": "🌀 Микро", "min_chars": 50, "max_chars": 150, "emoji": "🌀", "icon": "⚡"},
    "short": {"name": "📱 Короткий", "min_chars": 151, "max_chars": 350, "emoji": "📱", "icon": "📝"},
    "medium": {"name": "📄 Средний", "min_chars": 351, "max_chars": 700, "emoji": "📄", "icon": "📋"},
    "long": {"name": "📚 Длинный", "min_chars": 701, "max_chars": 1200, "emoji": "📚", "icon": "📖"},
    "epic": {"name": "🔥 Эпичный", "min_chars": 1201, "max_chars": 2000, "emoji": "🔥", "icon": "⭐"}
}

# ==================== ИНТЕРВАЛЫ ====================
INTERVALS = [
    {"seconds": 10, "name": "🔟 10 секунд", "emoji": "⚡"},
    {"seconds": 30, "name": "⏱ 30 секунд", "emoji": "🕐"},
    {"seconds": 60, "name": "⏰ 1 минута", "emoji": "1️⃣"},
    {"seconds": 300, "name": "🕔 5 минут", "emoji": "5️⃣"},
    {"seconds": 600, "name": "🔟 10 минут", "emoji": "🔟"},
    {"seconds": 1800, "name": "⏰ 30 минут", "emoji": "⏰"},
    {"seconds": 3600, "name": "🕐 1 час", "emoji": "🕐"},
    {"seconds": 7200, "name": "🕑 2 часа", "emoji": "🕑"},
    {"seconds": 21600, "name": "📅 6 часов", "emoji": "📅"},
    {"seconds": 43200, "name": "🌙 12 часов", "emoji": "🌙"},
    {"seconds": 86400, "name": "📆 24 часа", "emoji": "📆"}
]

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class Post:
    id: str
    channel_id: str
    theme: str
    content: str
    posted_at: float
    size: str
    views: int = 0

@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    channels: List[str] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    total_posts: int = 0

@dataclass
class AutoPostConfig:
    channel_id: str
    theme: str
    size: str
    interval_seconds: int
    is_active: bool = True
    last_post: float = 0
    job_id: str = ""

class PostingBot:
    def __init__(self):
        self.user_subscriptions: Dict[int, UserSubscription] = {}
        self.auto_configs: Dict[str, AutoPostConfig] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[Post] = []
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.application = None
    
    def load_data(self):
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
    
    def save_data(self):
        subs = {uid: {"user_id": sub.user_id, "tariff": sub.tariff,
                      "channels": sub.channels, "posts_today": sub.posts_today,
                      "last_reset": sub.last_reset, "total_posts": sub.total_posts}
                for uid, sub in self.user_subscriptions.items()}
        with open("subscriptions.json", "w") as f:
            json.dump(subs, f, indent=2)
        
        configs = {cid: {"channel_id": cfg.channel_id, "theme": cfg.theme,
                         "size": cfg.size, "interval_seconds": cfg.interval_seconds,
                         "is_active": cfg.is_active, "last_post": cfg.last_post,
                         "job_id": cfg.job_id}
                   for cid, cfg in self.auto_configs.items()}
        with open("auto_configs.json", "w") as f:
            json.dump(configs, f, indent=2)
    
    def get_user_subscription(self, user_id: int) -> UserSubscription:
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = UserSubscription(
                user_id=user_id,
                tariff="starter"
            )
            self.save_data()
        
        sub = self.user_subscriptions[user_id]
        # Сброс счетчика в новый день
        if time.time() - sub.last_reset > 86400:
            sub.posts_today = 0
            sub.last_reset = time.time()
            self.save_data()
        
        return sub
    
    def get_tariff_config(self, tariff_key: str):
        return TARIFFS.get(tariff_key, TARIFFS["starter"])
    
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
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        if not token:
            return self._get_fallback_post(theme, size)
        
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

ВАЖНЫЕ ТРЕБОВАНИЯ:
- Длина текста: {size_config['min_chars']}-{size_config['max_chars']} символов
- Используй КРАСИВОЕ оформление с эмодзи
- Добавь вопрос к подписчикам для вовлечения
- Поставь хэштеги: {theme_config['hashtags']}
- Тон: дружелюбный, современный, вирусный

Тема: {theme_config['name']}
Напиши пост прямо сейчас:"""
        
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
                        content = data["choices"][0]["message"]["content"]
                        if len(content) > size_config["max_chars"]:
                            content = content[:size_config["max_chars"]]
                        # Добавляем хэштеги если их нет
                        if "#" not in content:
                            content += f"\n\n{theme_config['hashtags']}"
                        return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme, size)
    
    def _get_fallback_post(self, theme: str, size: str) -> str:
        posts = {
            "ai_news": "🤖✨ Искусственный интеллект меняет мир!\n\nКакие нейросети вы используете? Делитесь в комментариях! 👇\n\n🤖 #ИИ #Нейросети #AI",
            "crypto": "🪙📈 Биткоин снова в тренде!\n\nА вы верите в криптовалюты? 💭\n\n#Криптовалюта #Биткоин #Blockchain",
            "nft": "🎨🖼 NFT - будущее цифрового искусства!\n\nКакая ваша любимая NFT коллекция? 🎭\n\n#NFT #DigitalArt #Web3",
            "telegram": "📱💫 Telegram становится лучше каждый день!\n\nКакую функцию вы ждете больше всего? 🚀\n\n#Telegram #ТГ #Мессенджер",
            "business": "💼💰 5 секретов успешного бизнеса:\n\n1. 🔥 Любите свое дело\n2. 📈 Учитесь каждый день\n3. 🤝 Окружайтесь правильными людьми\n4. 🎯 Ставьте амбициозные цели\n5. 🚀 Действуйте!\n\n#Бизнес #Успех #Предпринимательство"
        }
        return posts.get(theme, f"✨ {POSTING_THEMES.get(theme, {}).get('name', 'Новый пост')}!\n\nДелитесь мыслями в комментариях! 💬\n\n{POSTING_THEMES.get(theme, {}).get('hashtags', '#пост')}")

bot = PostingBot()

# ==================== КРАСИВЫЕ КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    sub = bot.get_user_subscription(user_id)
    tariff = bot.get_tariff_config(sub.tariff)
    
    keyboard = [
        [InlineKeyboardButton("➕ ДОБАВИТЬ КАНАЛ", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 АВТОПОСТИНГ", callback_data="auto_posting")],
        [InlineKeyboardButton("🎯 РАЗОВЫЙ ПОСТ", callback_data="single_post")],
        [InlineKeyboardButton("🎨 ТЕМЫ", callback_data="themes_menu")],
        [InlineKeyboardButton("📏 РАЗМЕРЫ ПОСТОВ", callback_data="sizes_menu")],
        [InlineKeyboardButton("⏱ ИНТЕРВАЛЫ", callback_data="intervals_menu")],
        [InlineKeyboardButton("📊 МОЯ СТАТИСТИКА", callback_data="my_stats")],
        [InlineKeyboardButton("📋 МОИ КАНАЛЫ", callback_data="my_channels")],
        [InlineKeyboardButton("💎 ТАРИФЫ", callback_data="tariffs_menu")],
        [InlineKeyboardButton("🆘 ПОМОЩЬ", callback_data="help_menu")]
    ]
    
    status_text = f"📊 {tariff['emoji']} {tariff['name']} | 📝 {sub.posts_today}/{tariff['posts_per_day']} | 📢 {len(sub.channels)}/{tariff['channels']}"
    
    return InlineKeyboardMarkup(keyboard), status_text

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
                callback_data=f"select_theme_{theme_key}"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ НАЗАД", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav_buttons.append(InlineKeyboardButton("ВПЕРЕД ▶️", callback_data=f"themes_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(prefix: str = "size"):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{size['emoji']} {size['name']} ({size['min_chars']}-{size['max_chars']} симв.)",
                callback_data=f"{prefix}_{size_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(prefix: str = "interval"):
    keyboard = []
    for interval in INTERVALS:
        keyboard.append([
            InlineKeyboardButton(
                f"{interval['emoji']} {interval['name']}",
                callback_data=f"{prefix}_{interval['seconds']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff['emoji']} {tariff['name']} | {tariff['channels']} каналов | {tariff['posts_per_day']} пост/день",
                callback_data=f"select_tariff_{tariff_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    sub = bot.get_user_subscription(user_id)
    keyboard = []
    
    for channel_id in sub.channels:
        try:
            if bot.application:
                chat = await bot.application.bot.get_chat(int(channel_id))
                name = chat.title[:30]
                keyboard.append([
                    InlineKeyboardButton(f"📢 {name}", callback_data=f"channel_{channel_id}")
                ])
        except:
            keyboard.append([
                InlineKeyboardButton(f"⚠️ Канал {channel_id[:10]}...", callback_data=f"channel_{channel_id}")
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.application = context.application
    bot.load_data()
    
    sub = bot.get_user_subscription(user.id)
    tariff = bot.get_tariff_config(sub.tariff)
    
    welcome_text = f"""
✨ *ДОБРО ПОЖАЛОВАТЬ, {user.first_name}!* ✨

🤖 *AI Постинг Бот* - твой персональный SMM-помощник

{'='*30}
📊 *ТВОЙ ТАРИФ:* {tariff['emoji']} {tariff['name']}
📢 *Доступно каналов:* {tariff['channels']}
📝 *Постов в день:* {tariff['posts_per_day']}
⚡ *Мин. интервал:* {tariff['min_interval']} сек
{'='*30}

🚀 *ВОЗМОЖНОСТИ:*
✅ Автопостинг с ИИ (GigaChat)
✅ 20+ актуальных тем
✅ 5 размеров постов
✅ Интервалы от 10 секунд
✅ Красивое оформление
✅ Перепост из каналов

💡 *БЫСТРЫЙ СТАРТ:*
1️⃣ Нажми «➕ ДОБАВИТЬ КАНАЛ»
2️⃣ Настрой АВТОПОСТИНГ
3️⃣ Выбери тему и интервал

👇 *ВЫБЕРИ ДЕЙСТВИЕ:*
"""
    keyboard, status = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = bot.get_tariff_config(sub.tariff)
    
    if len(sub.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ *Лимит каналов достигнут!*\n\n"
            f"📊 Ваш тариф: {tariff['emoji']} {tariff['name']}\n"
            f"📢 Максимум каналов: {tariff['channels']}\n\n"
            f"💎 Для добавления большего количества каналов выберите другой тариф в разделе «💎 ТАРИФЫ»",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📢 *ДОБАВЛЕНИЕ КАНАЛА*\n\n"
        "✨ *ПРОСТАЯ ИНСТРУКЦИЯ:*\n\n"
        "1️⃣ *Добавьте бота в канал как АДМИНИСТРАТОРА*\n"
        "   🔹 Права: отправка сообщений\n\n"
        "2️⃣ *Перешлите ЛЮБОЕ сообщение из канала СЮДА*\n"
        "   🔹 Или отправьте username канала (@channel)\n"
        "   🔹 Или ID канала (-100xxxxxxxxx)\n\n"
        "3️⃣ *Бот автоматически подключит канал!*\n\n"
        "💡 *Совет:* После добавления настройте автопостинг в главном меню",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        user_id = update.effective_user.id
        text = update.message.text
        sub = bot.get_user_subscription(user_id)
        tariff = bot.get_tariff_config(sub.tariff)
        
        if len(sub.channels) >= tariff["channels"]:
            await update.message.reply_text("❌ Лимит каналов достигнут!")
            context.user_data['awaiting_channel'] = False
            return
        
        channel_id = None
        channel_name = None
        
        # Определяем канал
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
        elif text.startswith('-100') or text.startswith('-'):
            channel_id = text
            try:
                chat = await context.bot.get_chat(int(text))
                channel_name = chat.title
            except:
                channel_name = "Канал"
        
        if channel_id and channel_id not in sub.channels:
            sub.channels.append(channel_id)
            bot.save_data()
            
            success_text = f"""
✅ *КАНАЛ УСПЕШНО ДОБАВЛЕН!*

📢 *Название:* {channel_name}
🆔 *ID:* `{channel_id}`

📊 *Ваши каналы:* {len(sub.channels)}/{tariff['channels']}

🚀 *ЧТО ДАЛЬШЕ?*
1️⃣ Настройте АВТОПОСТИНГ в главном меню
2️⃣ Выберите тему и интервал
3️⃣ Бот начнет публикации автоматически!

💡 *Совет:* Нажмите «АВТОПОСТИНГ» для настройки
"""
            await update.message.reply_text(success_text, parse_mode='Markdown')
        
        context.user_data['awaiting_channel'] = False

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        keyboard = [[InlineKeyboardButton("➕ ДОБАВИТЬ КАНАЛ", callback_data="add_channel")]]
        await update.message.reply_text(
            "❌ *У вас нет добавленных каналов!*\n\nСначала добавьте канал через меню.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    text = "🤖 *НАСТРОЙКА АВТОПОСТИНГА*\n\n"
    text += "Выберите канал для настройки:\n\n"
    
    keyboard = []
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            config = bot.auto_configs.get(channel_id)
            status = "✅ АКТИВЕН" if config and config.is_active else "⏸ ОСТАНОВЛЕН"
            theme_name = POSTING_THEMES.get(config.theme, {}).get('name', 'не настроен') if config else 'не настроен'
            
            text += f"📢 *{chat.title[:40]}*\n"
            text += f"   🎯 Тема: {theme_name}\n"
            text += f"   📊 Статус: {status}\n\n"
            
            keyboard.append([InlineKeyboardButton(f"⚙️ {chat.title[:30]}", callback_data=f"config_{channel_id}")])
        except:
            keyboard.append([InlineKeyboardButton(f"⚠️ Неизвестный канал", callback_data=f"config_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_auto_config(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    config = bot.auto_configs.get(channel_id)
    
    if config:
        theme = POSTING_THEMES.get(config.theme, {})
        size = POST_SIZES.get(config.size, {})
        interval = next((i for i in INTERVALS if i['seconds'] == config.interval_seconds), INTERVALS[0])
        
        text = f"""
⚙️ *НАСТРОЙКИ АВТОПОСТИНГА*

{'='*25}
🎨 *Тема:* {theme.get('emoji', '📝')} {theme.get('name', 'Не выбрана')}
📏 *Размер:* {size.get('emoji', '📄')} {size.get('name', 'Не выбран')}
⏱ *Интервал:* {interval['emoji']} {interval['name']}
📊 *Статус:* {'✅ АКТИВЕН' if config.is_active else '⏸ ОСТАНОВЛЕН'}
⏰ *Последний пост:* {datetime.fromtimestamp(config.last_post).strftime('%H:%M:%S') if config.last_post else 'Нет'}
{'='*25}

Выберите параметр для изменения:
"""
    else:
        text = "⚙️ *НАСТРОЙКА АВТОПОСТИНГА*\n\nВыберите параметры:"
    
    keyboard = [
        [InlineKeyboardButton("🎨 ВЫБРАТЬ ТЕМУ", callback_data=f"set_theme_{channel_id}")],
        [InlineKeyboardButton("📏 ВЫБРАТЬ РАЗМЕР", callback_data=f"set_size_{channel_id}")],
        [InlineKeyboardButton("⏱ ВЫБРАТЬ ИНТЕРВАЛ", callback_data=f"set_interval_{channel_id}")],
        [InlineKeyboardButton("▶️ ВКЛЮЧИТЬ", callback_data=f"enable_auto_{channel_id}")],
        [InlineKeyboardButton("⏸ ВЫКЛЮЧИТЬ", callback_data=f"disable_auto_{channel_id}")],
        [InlineKeyboardButton("🗑 УДАЛИТЬ КАНАЛ", callback_data=f"delete_channel_{channel_id}")],
        [InlineKeyboardButton("🔙 НАЗАД", callback_data="auto_posting")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def start_auto_posting(user_id: int, channel_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Запуск автопостинга для канала"""
    config = bot.auto_configs.get(channel_id)
    if not config or not config.is_active:
        return
    
    sub = bot.get_user_subscription(user_id)
    tariff = bot.get_tariff_config(sub.tariff)
    
    # Проверяем интервал
    if config.interval_seconds < tariff["min_interval"]:
        config.interval_seconds = tariff["min_interval"]
    
    # Запускаем задачу
    async def auto_post_job():
        while True:
            if not config.is_active:
                break
            
            current_time = time.time()
            if current_time - config.last_post >= config.interval_seconds:
                # Проверяем лимит постов
                if sub.posts_today < tariff["posts_per_day"]:
                    # Генерируем и отправляем пост
                    content = await bot.generate_post(config.theme, config.size)
                    
                    try:
                        await context.bot.send_message(
                            chat_id=channel_id,
                            text=content,
                            parse_mode='HTML'
                        )
                        config.last_post = current_time
                        sub.posts_today += 1
                        sub.total_posts += 1
                        bot.save_data()
                        logger.info(f"✅ Автопост в {channel_id} | Тема: {config.theme}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
            
            await asyncio.sleep(config.interval_seconds)
    
    # Сохраняем задачу
    task = asyncio.create_task(auto_post_job())
    bot.active_jobs[channel_id] = task

async def stop_auto_posting(channel_id: str):
    """Остановка автопостинга"""
    if channel_id in bot.active_jobs:
        bot.active_jobs[channel_id].cancel()
        del bot.active_jobs[channel_id]

async def single_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        keyboard = [[InlineKeyboardButton("➕ ДОБАВИТЬ КАНАЛ", callback_data="add_channel")]]
        await update.message.reply_text(
            "❌ *У вас нет каналов!*\n\nДобавьте канал через главное меню.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    context.user_data['single_post_mode'] = True
    keyboard = await get_themes_keyboard()
    await update.message.reply_text(
        "🎯 *РАЗОВАЯ ПУБЛИКАЦИЯ*\n\n"
        "Выберите тему для поста:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = bot.get_tariff_config(sub.tariff)
    
    # Подсчет постов по каналам за сегодня
    remaining = tariff["posts_per_day"] - sub.posts_today
    
    stats_text = f"""
📊 *ВАША СТАТИСТИКА*

{'='*30}
💎 *Тариф:* {tariff['emoji']} {tariff['name']}
📢 *Каналов:* {len(sub.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {sub.posts_today}/{tariff['posts_per_day']}
⏳ *Осталось постов:* {remaining}
📈 *Всего постов:* {sub.total_posts}
⚡ *Мин. интервал:* {tariff['min_interval']} сек
{'='*30}

🎯 *Активные автопостинги:*
"""
    
    for channel_id in sub.channels:
        config = bot.auto_configs.get(channel_id)
        if config and config.is_active:
            theme = POSTING_THEMES.get(config.theme, {})
            stats_text += f"\n✅ {theme.get('emoji', '📢')} {theme.get('name', 'Постинг')} | интервал: {config.interval_seconds}с"
    
    if not any(config and config.is_active for config in bot.auto_configs.values() if config.channel_id in sub.channels):
        stats_text += "\n❌ Нет активных автопостингов"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await update.message.reply_text("❌ У вас нет добавленных каналов")
        return
    
    text = "📋 *ВАШИ КАНАЛЫ*\n\n"
    
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            config = bot.auto_configs.get(channel_id)
            status = "✅ АКТИВЕН" if config and config.is_active else "⏸ НЕАКТИВЕН"
            
            text += f"""
📢 *{chat.title}*
🆔 `{channel_id}`
📊 Статус: {status}
{'─'*25}
"""
        except:
            text += f"⚠️ Канал {channel_id[:15]}... - недоступен\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]]
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_sub = bot.get_user_subscription(user_id)
    
    text = "💎 *ДОСТУПНЫЕ ТАРИФЫ*\n\n"
    text += "Все тарифы *БЕСПЛАТНЫЕ*! 🎉\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        current = " ✅ ТЕКУЩИЙ" if current_sub.tariff == tariff_key else ""
        text += f"""
{tariff['emoji']} *{tariff['name']}{current}*
{'─'*20}
📢 Каналов: {tariff['channels']}
📝 Постов/день: {tariff['posts_per_day']}
⚡ Мин. интервал: {tariff['min_interval']} сек
🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}
🖼 Картинки: {'✅' if tariff['has_images'] else '❌'}
"""
    
    text += "\n💡 *Как сменить тариф:*\nПросто нажмите на нужный тариф ниже!"
    
    keyboard = await get_tariffs_keyboard()
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_key: str):
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    sub.tariff = tariff_key
    bot.save_data()
    
    tariff = TARIFFS[tariff_key]
    
    await update.callback_query.edit_message_text(
        f"✅ *Тариф изменен на {tariff['emoji']} {tariff['name']}!*\n\n"
        f"📢 Теперь доступно: {tariff['channels']} каналов\n"
        f"📝 Лимит постов: {tariff['posts_per_day']}/день\n"
        f"⚡ Минимальный интервал: {tariff['min_interval']} сек\n\n"
        f"🔙 Нажмите «ГЛАВНОЕ МЕНЮ» для продолжения",
        parse_mode='Markdown'
    )

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *ПОМОЩЬ ПО РАБОТЕ БОТА*

{'='*30}

📌 *ОСНОВНЫЕ ФУНКЦИИ:*

🤖 *АВТОПОСТИНГ*
• Автоматическая публикация постов
• Генерация контента через GigaChat AI
• 20+ тем на выбор
• Настраиваемые интервалы (от 10 секунд до 24 часов)

🎯 *РАЗОВЫЙ ПОСТ*
• Быстрая публикация одного поста
• Выбор темы и размера
• Мгновенная отправка

📋 *УПРАВЛЕНИЕ КАНАЛАМИ*
• Добавляйте бота в каналы
• Настраивайте параметры для каждого канала
• Удаляйте ненужные каналы

{'='*30}

🎨 *ДОСТУПНЫЕ ТЕМЫ (20):*
🤖 ИИ и Нейросети
🪙 Криптовалюты
🎨 NFT и Искусство
📱 Telegram
💼 Бизнес
📡 Технологии
🔬 Наука
⚕️ Здоровье
🧠 Психология
📈 Маркетинг
🎨 Дизайн
💻 Программирование
🎮 Игры
🎬 Кино
🎵 Музыка
⚽ Спорт
✈️ Путешествия
🍳 Кулинария
📚 Образование
💪 Мотивация

{'='*30}

📏 *РАЗМЕРЫ ПОСТОВ:*
🌀 Микро (50-150 симв.)
📱 Короткий (150-350)
📄 Средний (350-700)
📚 Длинный (700-1200)
🔥 Эпичный (1200-2000)

{'='*30}

❓ *ЧАСТЫЕ ВОПРОСЫ:*

❔ *Как добавить бота в канал?*
→ Сделайте бота администратором канала
→ Перешлите сообщение из канала боту

❔ *Почему бот не постит?*
→ Проверьте, что бот админ в канале
→ Убедитесь, что автопостинг включен
→ Проверьте лимиты постов

❔ *Как изменить настройки?*
→ Нажмите «АВТОПОСТИНГ» в главном меню
→ Выберите нужный канал
→ Измените параметры

💬 *Поддержка:* @

🔙 *Вернуться в меню:* Нажмите кнопку ниже
"""
    keyboard = [[InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]]
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ОБРАБОТЧИК CALLBACK'ОВ ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    # Главное меню
    if data == "main_menu":
        keyboard, status = await get_main_keyboard(user_id)
        await query.edit_message_text(
            "🏠 *ГЛАВНОЕ МЕНЮ*\n\n" + status,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data == "add_channel":
        tariff = bot.get_tariff_config(sub.tariff)
        if len(sub.channels) >= tariff["channels"]:
            await query.edit_message_text(
                f"❌ *Лимит каналов: {tariff['channels']}*\n\n"
                f"Выберите другой тариф в разделе «💎 ТАРИФЫ»",
                parse_mode='Markdown'
            )
        else:
            context.user_data['awaiting_channel'] = True
            await query.edit_message_text(
                "📢 *ДОБАВЛЕНИЕ КАНАЛА*\n\n"
                "1️⃣ Добавьте бота в канал как АДМИНИСТРАТОРА\n"
                "2️⃣ Перешлите ЛЮБОЕ сообщение из канала СЮДА\n"
                "3️⃣ Бот автоматически подключит канал!",
                parse_mode='Markdown'
            )
    
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    
    elif data == "single_post":
        context.user_data['single_post_mode'] = True
        keyboard = await get_themes_keyboard()
        await query.edit_message_text(
            "🎯 *РАЗОВАЯ ПУБЛИКАЦИЯ*\n\nВыберите тему:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data == "themes_menu":
        keyboard = await get_themes_keyboard()
        await query.edit_message_text(
            "🎨 *ВСЕ ТЕМЫ ДЛЯ ПОСТОВ*\n\n"
            "Выберите тему:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data == "sizes_menu":
        keyboard = await get_sizes_keyboard("single_size" if context.user_data.get('single_post_mode') else "size")
        await query.edit_message_text(
            "📏 *РАЗМЕРЫ ПОСТОВ*\n\n"
            "Выберите желаемый размер:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data == "intervals_menu":
        keyboard = await get_intervals_keyboard("interval")
        await query.edit_message_text(
            "⏱ *ИНТЕРВАЛЫ АВТОПОСТИНГА*\n\n"
            "Выберите интервал публикации:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data == "my_stats":
        tariff = bot.get_tariff_config(sub.tariff)
        remaining = tariff["posts_per_day"] - sub.posts_today
        
        text = f"""
📊 *ВАША СТАТИСТИКА*

{'='*25}
💎 *Тариф:* {tariff['emoji']} {tariff['name']}
📢 *Каналов:* {len(sub.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {sub.posts_today}/{tariff['posts_per_day']}
⏳ *Осталось:* {remaining}
📈 *Всего постов:* {sub.total_posts}
⚡ *Мин. интервал:* {tariff['min_interval']} сек
{'='*25}

🎯 *Активные автопостинги:*
"""
        for channel_id in sub.channels:
            config = bot.auto_configs.get(channel_id)
            if config and config.is_active:
                theme = POSTING_THEMES.get(config.theme, {})
                interval = next((i for i in INTERVALS if i['seconds'] == config.interval_seconds), INTERVALS[0])
                text += f"\n✅ {theme.get('emoji', '📢')} | {interval['emoji']} {interval['name']}"
        
        keyboard = [[InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "tariffs_menu":
        await tariffs_menu(update, context)
    
    elif data == "help_menu":
        await help_menu(update, context)
    
    # Выбор темы
    elif data.startswith("select_theme_"):
        theme = data.replace("select_theme_", "")
        context.user_data['selected_theme'] = theme
        
        if context.user_data.get('single_post_mode'):
            # Для разового поста - выбираем размер
            keyboard = await get_sizes_keyboard("single_post_with_theme")
            await query.edit_message_text(
                f"✅ Тема: *{POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}*\n\n"
                f"📏 Теперь выберите размер поста:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            # Для автонастройки - сохраняем тему
            await query.edit_message_text(
                f"✅ Тема сохранена: *{POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}*\n\n"
                f"Теперь настройте остальные параметры в меню АВТОПОСТИНГА",
                parse_mode='Markdown'
            )
    
    # Разовые посты
    elif data.startswith("single_post_with_theme_"):
        size = data.replace("single_post_with_theme_", "")
        theme = context.user_data.get('selected_theme')
        
        if theme and sub.channels:
            if sub.posts_today < TARIFFS[sub.tariff]["posts_per_day"]:
                await query.edit_message_text(f"🎲 *Генерация поста...*\n\nТема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\nРазмер: {POST_SIZES[size]['name']}")
                
                content = await bot.generate_post(theme, size)
                
                try:
                    await context.bot.send_message(
                        chat_id=sub.channels[0],
                        text=content,
                        parse_mode='HTML'
                    )
                    sub.posts_today += 1
                    sub.total_posts += 1
                    bot.save_data()
                    
                    await query.edit_message_text(
                        f"✅ *Пост успешно опубликован!*\n\n"
                        f"📊 Осталось постов сегодня: {TARIFFS[sub.tariff]['posts_per_day'] - sub.posts_today}\n\n"
                        f"🔙 Нажмите «ГЛАВНОЕ МЕНЮ» для продолжения",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    await query.edit_message_text(f"❌ Ошибка публикации: {str(e)[:100]}")
            else:
                await query.edit_message_text("❌ Достигнут лимит постов на сегодня!")
        
        context.user_data['single_post_mode'] = False
        context.user_data['selected_theme'] = None
    
    # Настройка автопостинга для канала
    elif data.startswith("config_"):
        channel_id = data.replace("config_", "")
        await show_auto_config(update, context, channel_id)
    
    # Установка темы для автопостинга
    elif data.startswith("set_theme_"):
        channel_id = data.replace("set_theme_", "")
        context.user_data['config_channel'] = channel_id
        keyboard = await get_themes_keyboard()
        await query.edit_message_text(
            "🎨 *Выберите тему для автопостинга:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    # Сохранение темы для автопостинга
    elif data.startswith("save_theme_for_auto_"):
        theme = data.replace("save_theme_for_auto_", "")
        channel_id = context.user_data.get('config_channel')
        
        if channel_id:
            if channel_id not in bot.auto_configs:
                bot.auto_configs[channel_id] = AutoPostConfig(
                    channel_id=channel_id,
                    theme=theme,
                    size="medium",
                    interval_seconds=3600
                )
            else:
                bot.auto_configs[channel_id].theme = theme
            bot.save_data()
            
            await query.edit_message_text(
                f"✅ Тема сохранена: *{POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}*\n\n"
                f"Теперь настройте другие параметры",
                parse_mode='Markdown'
            )
            await show_auto_config(update, context, channel_id)
    
    # Установка размера для автопостинга
    elif data.startswith("set_size_"):
        channel_id = data.replace("set_size_", "")
        context.user_data['config_channel'] = channel_id
        keyboard = await get_sizes_keyboard("save_size_for_auto")
        await query.edit_message_text(
            "📏 *Выберите размер постов:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data.startswith("save_size_for_auto_"):
        size = data.replace("save_size_for_auto_", "")
        channel_id = context.user_data.get('config_channel')
        
        if channel_id:
            if channel_id not in bot.auto_configs:
                bot.auto_configs[channel_id] = AutoPostConfig(
                    channel_id=channel_id,
                    theme="ai_news",
                    size=size,
                    interval_seconds=3600
                )
            else:
                bot.auto_configs[channel_id].size = size
            bot.save_data()
            
            await query.edit_message_text(
                f"✅ Размер сохранен: *{POST_SIZES[size]['name']}* ({POST_SIZES[size]['min_chars']}-{POST_SIZES[size]['max_chars']} симв.)",
                parse_mode='Markdown'
            )
            await show_auto_config(update, context, channel_id)
    
    # Установка интервала
    elif data.startswith("set_interval_"):
        channel_id = data.replace("set_interval_", "")
        context.user_data['config_channel'] = channel_id
        keyboard = await get_intervals_keyboard("save_interval_for_auto")
        await query.edit_message_text(
            "⏱ *Выберите интервал автопостинга:*\n\n"
            f"⚡ Минимальный интервал для вашего тарифа: {TARIFFS[sub.tariff]['min_interval']} сек",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif data.startswith("save_interval_for_auto_"):
        interval_seconds = int(data.replace("save_interval_for_auto_", ""))
        channel_id = context.user_data.get('config_channel')
        tariff = TARIFFS[sub.tariff]
        
        if interval_seconds < tariff["min_interval"]:
            await query.edit_message_text(
                f"❌ Интервал {interval_seconds} сек меньше минимального для вашего тарифа!\n\n"
                f"⚡ Минимальный интервал: {tariff['min_interval']} сек\n"
                f"💎 Выберите другой тариф для более частых постов",
                parse_mode='Markdown'
            )
            return
        
        if channel_id:
            if channel_id not in bot.auto_configs:
                bot.auto_configs[channel_id] = AutoPostConfig(
                    channel_id=channel_id,
                    theme="ai_news",
                    size="medium",
                    interval_seconds=interval_seconds
                )
            else:
                bot.auto_configs[channel_id].interval_seconds = interval_seconds
            bot.save_data()
            
            interval_name = next((i['name'] for i in INTERVALS if i['seconds'] == interval_seconds), f"{interval_seconds} сек")
            await query.edit_message_text(
                f"✅ Интервал сохранен: *{interval_name}*",
                parse_mode='Markdown'
            )
            await show_auto_config(update, context, channel_id)
    
    # Включение/выключение автопостинга
    elif data.startswith("enable_auto_"):
        channel_id = data.replace("enable_auto_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = True
            bot.save_data()
            
            # Запускаем автопостинг
            await start_auto_posting(user_id, channel_id, context)
            
            await query.edit_message_text(
                "✅ *Автопостинг ВКЛЮЧЕН!*\n\n"
                f"⏱ Интервал: {bot.auto_configs[channel_id].interval_seconds} сек\n"
                f"🎨 Тема: {POSTING_THEMES[bot.auto_configs[channel_id].theme]['name']}\n\n"
                f"Бот начнет публикации автоматически!",
                parse_mode='Markdown'
            )
            await show_auto_config(update, context, channel_id)
    
    elif data.startswith("disable_auto_"):
        channel_id = data.replace("disable_auto_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = False
            bot.save_data()
            
            # Останавливаем автопостинг
            await stop_auto_posting(channel_id)
            
            await query.edit_message_text(
                "⏸ *Автопостинг ВЫКЛЮЧЕН*\n\nВы можете включить его снова в любой момент.",
                parse_mode='Markdown'
            )
            await show_auto_config(update, context, channel_id)
    
    # Удаление канала
    elif data.startswith("delete_channel_"):
        channel_id = data.replace("delete_channel_", "")
        
        if channel_id in sub.channels:
            sub.channels.remove(channel_id)
            if channel_id in bot.auto_configs:
                # Останавливаем автопостинг
                await stop_auto_posting(channel_id)
                del bot.auto_configs[channel_id]
            bot.save_data()
            
            await query.edit_message_text(
                "✅ *Канал удален!*\n\n"
                f"Осталось каналов: {len(sub.channels)}/{TARIFFS[sub.tariff]['channels']}",
                parse_mode='Markdown'
            )
    
    # Страницы тем
    elif data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    # Выбор тарифа
    elif data.startswith("select_tariff_"):
        tariff_key = data.replace("select_tariff_", "")
        await select_tariff(update, context, tariff_key)

# ==================== ЗАПУСК БОТА ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot.application = application
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Тарифов: {len(TARIFFS)} (все бесплатные)")
    logger.info(f"⚡ Интервалы: от 10 секунд до 24 часов")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
