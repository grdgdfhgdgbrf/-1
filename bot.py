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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, InputMediaPhoto
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

# ==================== ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ ====================
class TariffType(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

TARIFFS = {
    "free": {
        "name": "🌟 Стартовый",
        "price": 0,
        "channels": 2,
        "posts_per_day": 20,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "standard",
        "has_images": True,
        "image_limit": 5,
        "color": "🟢"
    },
    "basic": {
        "name": "⚡ Базовый", 
        "price": 0,
        "channels": 5,
        "posts_per_day": 50,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "enhanced",
        "has_images": True,
        "image_limit": 10,
        "color": "🔵"
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 0,
        "channels": 15,
        "posts_per_day": 150,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "premium",
        "has_images": True,
        "image_limit": 20,
        "color": "🟣"
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels": 999,
        "posts_per_day": 500,
        "can_repost": True,
        "can_schedule": True,
        "ai_quality": "ultra",
        "has_images": True,
        "image_limit": 50,
        "color": "🟡"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "Искусственный Интеллект",
        "emoji": "🤖",
        "color": "🔵",
        "description": "Новости AI, ChatGPT, нейросети",
        "prompt": "Ты эксперт по искусственному интеллекту. Создай интересный, познавательный пост о последних новостях в мире AI, нейросетях, ChatGPT. Добавь полезные советы или необычные факты. Пост должен быть написан увлекательно, с эмодзи, хэштегами и вопросом к аудитории."
    },
    "crypto": {
        "name": "Криптовалюты",
        "emoji": "🪙",
        "color": "🟡",
        "description": "Bitcoin, Ethereum, DeFi",
        "prompt": "Ты крипто-аналитик и блогер. Создай пост о криптовалютах: новости рынка, анализ трендов, полезные советы по инвестициям. Используй простой и понятный язык. Добавь эмодзи, хэштеги и вопрос к подписчикам."
    },
    "nft": {
        "name": "NFT и Цифровое Искусство",
        "emoji": "🎨",
        "color": "🎭",
        "description": "NFT коллекции, digital art",
        "prompt": "Ты эксперт по NFT и цифровому искусству. Расскажи о новых интересных NFT проектах, трендах в digital art, метавселенных. Пост должен быть вдохновляющим и информативным. Используй эмодзи, хэштеги."
    },
    "telegram": {
        "name": "Telegram",
        "emoji": "📱",
        "color": "💙",
        "description": "Новости и фишки Telegram",
        "prompt": "Ты Telegram-блогер. Создай пост о новых функциях Telegram, полезных ботах, крутых каналах или секретных фишках. Сделай пост максимально полезным для подписчиков. Добавь эмодзи и хэштеги."
    },
    "business": {
        "name": "Бизнес и Предпринимательство",
        "emoji": "💼",
        "color": "💼",
        "description": "Бизнес идеи, стартапы",
        "prompt": "Ты успешный предприниматель. Поделись бизнес-советами, идеями для стартапов, лайфхаками по управлению. Пост должен быть мотивирующим и практичным. Используй эмодзи, хэштеги и задай вопрос."
    },
    "tech": {
        "name": "Технологии и Гаджеты",
        "emoji": "📡",
        "color": "📱",
        "description": "Новости технологий",
        "prompt": "Ты техноблогер. Расскажи о новых технологиях, гаджетах, инновациях. Сделай обзор интересного устройства или технологии. Пост должен быть увлекательным и современным. Добавь эмодзи и хэштеги."
    },
    "science": {
        "name": "Наука и Открытия",
        "emoji": "🔬",
        "color": "🧪",
        "description": "Научные открытия",
        "prompt": "Ты научный журналист. Расскажи об интересном научном открытии или факте. Объясни сложное простыми словами. Пост должен быть познавательным и увлекательным. Используй эмодзи, хэштеги."
    },
    "health": {
        "name": "Здоровье и Благополучие",
        "emoji": "⚕️",
        "color": "💚",
        "description": "ЗОЖ, медицина",
        "prompt": "Ты медицинский блогер. Дай полезные советы по здоровью, правильному питанию, спорту. Пост должен быть научно обоснованным, но простым для понимания. Добавь эмодзи, хэштеги."
    },
    "psychology": {
        "name": "Психология и Саморазвитие",
        "emoji": "🧠",
        "color": "💜",
        "description": "Психология, личностный рост",
        "prompt": "Ты психолог. Поделись полезными советами по саморазвитию, управлению эмоциями, улучшению жизни. Пост должен быть поддерживающим и вдохновляющим. Используй эмодзи, хэштеги."
    },
    "marketing": {
        "name": "Маркетинг и SMM",
        "emoji": "📈",
        "color": "📊",
        "description": "Маркетинг, реклама",
        "prompt": "Ты маркетолог-эксперт. Дай практические советы по продвижению, SMM, контент-маркетингу. Пост должен быть максимально полезным. Добавь примеры, эмодзи, хэштеги."
    },
    "design": {
        "name": "Дизайн и Креатив",
        "emoji": "🎨",
        "color": "✨",
        "description": "Графический дизайн",
        "prompt": "Ты креативный дизайнер. Поделись советами по дизайну, вдохновением, трендами. Пост должен быть визуально-описательным и вдохновляющим. Используй эмодзи, хэштеги."
    },
    "programming": {
        "name": "Программирование",
        "emoji": "💻",
        "color": "💻",
        "description": "IT, coding, разработка",
        "prompt": "Ты разработчик-эксперт. Поделись полезными советами по программированию, новыми технологиями, лучшими практиками. Пост должен быть полезен как новичкам, так и профи. Добавь примеры кода (если уместно), эмодзи, хэштеги."
    },
    "gaming": {
        "name": "Игры и Гейминг",
        "emoji": "🎮",
        "color": "🎮",
        "description": "Видеоигры, новости gaming",
        "prompt": "Ты игровой журналист. Расскажи об интересных играх, новостях геймдева, киберспорте. Пост должен быть увлекательным для геймеров. Используй эмодзи, хэштеги."
    },
    "movies": {
        "name": "Кино и Сериалы",
        "emoji": "🎬",
        "color": "🍿",
        "description": "Новости кино, обзоры",
        "prompt": "Ты кинокритик. Поделись обзором интересного фильма или сериала, новостями кинематографа. Пост должен быть увлекательным и с интригой. Добавь эмодзи, хэштеги, вопрос к подписчикам."
    },
    "music": {
        "name": "Музыка",
        "emoji": "🎵",
        "color": "🎶",
        "description": "Музыкальные новости",
        "prompt": "Ты музыкальный обозреватель. Расскажи о новинках музыки, интересных исполнителях, музыкальных событиях. Пост должен вдохновлять на прослушивание. Используй эмодзи, хэштеги."
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "color": "🏆",
        "description": "Спортивные новости",
        "prompt": "Ты спортивный журналист. Расскажи о спортивных событиях, достижениях, тренировках. Пост должен быть энергичным и мотивирующим. Добавь эмодзи, хэштеги."
    },
    "travel": {
        "name": "Путешествия",
        "emoji": "✈️",
        "color": "🌍",
        "description": "Туризм, страны, приключения",
        "prompt": "Ты тревел-блогер. Поделись советами по путешествиям, расскажи об интересных местах. Пост должен пробуждать желание путешествовать. Используй яркие эмодзи, хэштеги."
    },
    "food": {
        "name": "Кулинария",
        "emoji": "🍳",
        "color": "🍜",
        "description": "Рецепты, кулинарные советы",
        "prompt": "Ты кулинарный блогер. Поделись вкусным рецептом или кулинарным лайфхаком. Пост должен быть аппетитным и полезным. Добавь эмодзи, хэштеги."
    },
    "education": {
        "name": "Образование",
        "emoji": "📚",
        "color": "📖",
        "description": "Обучение, курсы, знания",
        "prompt": "Ты педагог и коуч. Поделись советами по обучению, интересными фактами, полезными ресурсами. Пост должен вдохновлять на учебу. Используй эмодзи, хэштеги."
    },
    "motivation": {
        "name": "Мотивация и Успех",
        "emoji": "💪",
        "color": "🔥",
        "description": "Мотивация, успех, цели",
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост о достижении целей, успехе, преодолении препятствий. Пост должен заряжать энергией и верой в себя. Используй эмодзи, хэштеги."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "Мини", "min_chars": 150, "max_chars": 350, "emoji": "🔹", "desc": "Коротко и ясно"},
    "short": {"name": "Короткий", "min_chars": 351, "max_chars": 650, "emoji": "🔸", "desc": "Оптимально для ленты"},
    "medium": {"name": "Средний", "min_chars": 651, "max_chars": 1000, "emoji": "📝", "desc": "Развернутый пост"},
    "long": {"name": "Длинный", "min_chars": 1001, "max_chars": 1500, "emoji": "📄", "desc": "Максимум пользы"},
    "extra": {"name": "Экспертный", "min_chars": 1501, "max_chars": 2200, "emoji": "📚", "desc": "Глубокий разбор"}
}

# ==================== ИНТЕРВАЛЫ ДЛЯ АВТОПОСТИНГА ====================
AUTO_INTERVALS = {
    10: "🔟 10 минут (🔥 Часто)",
    15: "⏱ 15 минут",
    20: "⏰ 20 минут",
    30: "🕐 30 минут",
    45: "🕜 45 минут",
    60: "🕑 1 час (⭐ Популярно)",
    90: "🕒 1.5 часа",
    120: "🕓 2 часа",
    180: "🕔 3 часа",
    240: "🕕 4 часа",
    360: "🕖 6 часов",
    480: "🕗 8 часов",
    720: "🕘 12 часов",
    1440: "🕙 24 часа (Ежедневно)"
}

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
    likes: int = 0

@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    subscribed_at: float
    channels: List[str] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    themes: List[str] = field(default_factory=list)
    
    def can_post(self) -> bool:
        today = time.time()
        if today - self.last_reset > 86400:
            self.posts_today = 0
            self.last_reset = today
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return self.posts_today < tariff["posts_per_day"]
    
    def add_post(self):
        self.posts_today += 1
    
    def get_remaining_posts(self) -> int:
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return max(0, tariff["posts_per_day"] - self.posts_today)

@dataclass
class AutoPostConfig:
    channel_id: str
    theme: str
    size: str
    interval_minutes: int
    is_active: bool = True
    last_post: float = 0
    next_post_time: float = 0
    
    def update_next_post(self):
        self.next_post_time = time.time() + (self.interval_minutes * 60)

@dataclass
class PostStatistics:
    total_posts: int = 0
    posts_by_theme: Dict[str, int] = field(default_factory=dict)
    posts_by_size: Dict[str, int] = field(default_factory=dict)
    total_views: int = 0

# ==================== ОСНОВНОЕ ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.user_subscriptions: Dict[int, UserSubscription] = {}
        self.auto_configs: Dict[str, AutoPostConfig] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[Post] = []
        self.statistics: PostStatistics = PostStatistics()
        
    def load_data(self):
        """Загрузка данных из файлов"""
        try:
            with open("subscriptions.json", "r") as f:
                data = json.load(f)
                for user_id, sub_data in data.items():
                    self.user_subscriptions[int(user_id)] = UserSubscription(**sub_data)
        except FileNotFoundError:
            pass
        
        try:
            with open("auto_configs.json", "r") as f:
                data = json.load(f)
                for channel_id, config_data in data.items():
                    self.auto_configs[channel_id] = AutoPostConfig(**config_data)
        except FileNotFoundError:
            pass
        
        try:
            with open("statistics.json", "r") as f:
                stat_data = json.load(f)
                self.statistics = PostStatistics(**stat_data)
        except FileNotFoundError:
            pass
    
    def save_data(self):
        """Сохранение данных"""
        subs = {uid: {"user_id": sub.user_id, "tariff": sub.tariff, 
                      "subscribed_at": sub.subscribed_at, "channels": sub.channels,
                      "posts_today": sub.posts_today, "last_reset": sub.last_reset,
                      "themes": sub.themes} 
                for uid, sub in self.user_subscriptions.items()}
        with open("subscriptions.json", "w") as f:
            json.dump(subs, f, indent=2)
        
        configs = {cid: {"channel_id": cfg.channel_id, "theme": cfg.theme,
                         "size": cfg.size, "interval_minutes": cfg.interval_minutes,
                         "is_active": cfg.is_active, "last_post": cfg.last_post,
                         "next_post_time": cfg.next_post_time}
                   for cid, cfg in self.auto_configs.items()}
        with open("auto_configs.json", "w") as f:
            json.dump(configs, f, indent=2)
        
        with open("statistics.json", "w") as f:
            json.dump({
                "total_posts": self.statistics.total_posts,
                "posts_by_theme": self.statistics.posts_by_theme,
                "posts_by_size": self.statistics.posts_by_size,
                "total_views": self.statistics.total_views
            }, f, indent=2)
    
    def get_user_subscription(self, user_id: int) -> UserSubscription:
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = UserSubscription(
                user_id=user_id,
                tariff="premium",  # Даем премиум всем бесплатно
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
                    else:
                        logger.error(f"Ошибка токена: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            return None
    
    async def generate_post_content(self, theme: str, size: str) -> str:
        """Генерация поста через GigaChat с красивым форматированием"""
        token = await self.get_api_token()
        
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        prompt = f"""{theme_config['prompt']}

Дата: {current_date}

СРОЧНО! ТРЕБОВАНИЯ К ПОСТУ:
1. Длина: {size_config['min_chars']}-{size_config['max_chars']} символов (ОБЯЗАТЕЛЬНО!)
2. Начни с яркого заголовка в **жирном** тексте
3. Используй эмодзи в каждом абзаце
4. Разделяй текст на короткие абзацы (2-3 предложения)
5. Добавь 5-7 релевантных хэштегов в конце (начинающихся с #)
6. В конце обязательно задай вопрос подписчикам
7. Пиши на русском языке, живо и интересно
8. Используй смайлики и эмоции
9. Добавь призыв к действию (лайк, комментарий, репост)

Пост должен быть максимально качественным, интересным и вовлекающим!
ВАЖНО: Точно соблюди длину поста!"""
        
        if not token:
            return self._get_fallback_post(theme, size)
        
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
                        if "choices" in data and data["choices"]:
                            content = data["choices"][0]["message"]["content"]
                            # Проверка длины
                            if len(content) > size_config["max_chars"]:
                                content = content[:size_config["max_chars"]]
                            elif len(content) < size_config["min_chars"]:
                                # Добавляем контент если слишком коротко
                                extra = f"\n\n✨ А как вы относитесь к этой теме? Делитесь мнением в комментариях! 👇\n\n{self._get_hashtags(theme)}"
                                content += extra
                            return content
                    elif response.status == 401:
                        self.api_token = None
                        return await self.generate_post_content(theme, size)
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme, size)
    
    def _get_hashtags(self, theme: str) -> str:
        """Генерация хэштегов для темы"""
        hashtags_map = {
            "ai_news": "#искусственныйинтеллект #нейросети #chatgpt #ai #технологии",
            "crypto": "#криптовалюта #биткоин #блокчейн #инвестиции #crypto",
            "nft": "#nft #цифровоеискусство #метавселенная #art #nftart",
            "telegram": "#telegram #телеграм #мессенджеры #боты #tg",
            "business": "#бизнес #стартап #предпринимательство #успех #бизнесидеи",
            "tech": "#технологии #гаджеты #инновации #tech #наука",
            "science": "#наука #открытия #исследования #образование #science",
            "health": "#здоровье #зож #спорт #питание #здоровыйобразжизни",
            "psychology": "#психология #саморазвитие #мотивация #личность #mindset",
            "marketing": "#маркетинг #smm #реклама #продвижение #marketing",
            "design": "#дизайн #креатив #графическийдизайн #art #design",
            "programming": "#программирование #разработка #it #кодинг #dev",
            "gaming": "#игры #гейминг #киберспорт #game #gaming",
            "movies": "#кино #сериалы #фильмы #кинопоиск #movies",
            "music": "#музыка #новинкимузыки #плейлист #music #песни",
            "sport": "#спорт #тренировка #фитнес #чемпионы #sport",
            "travel": "#путешествия #туризм #отпуск #travel #приключения",
            "food": "#кулинария #рецепты #еда #готовим #food",
            "education": "#образование #обучение #развитие #курсы #study",
            "motivation": "#мотивация #успех #цели #вдохновение #success"
        }
        return hashtags_map.get(theme, "#полезныйпост #актуально #интересно")
    
    def _get_fallback_post(self, theme: str, size: str) -> str:
        """Красивый запасной пост при ошибке API"""
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        hashtags = self._get_hashtags(theme)
        
        fallbacks = {
            "ai_news": f"🤖 **Нейросети меняют мир!**\n\nИскусственный интеллект становится частью нашей жизни каждый день. От ChatGPT до генерации изображений — возможности безграничны!\n\n✨ А вы уже используете нейросети в работе или творчестве? Делитесь опытом!\n\n{hashtags}",
            "crypto": f"🪙 **Криптовалюты: новый тренд?**\n\nРынок цифровых активов продолжает развиваться. Биткоин, Ethereum и другие монеты привлекают все больше инвесторов.\n\n💡 А вы инвестируете в криптовалюты? С чего начинали?\n\n{hashtags}",
            "nft": f"🎨 **NFT: цифровое искусство будущего**\n\nУникальные токены открывают новые горизонты для творчества и коллекционирования.\n\n🖼 А вы приобретали NFT? Что думаете об этом тренде?\n\n{hashtags}",
            "telegram": f"📱 **Telegram: лучший мессенджер!**\n\nПостоянные обновления, боты, каналы — здесь есть все для удобного общения.\n\n🔥 Какая функция Telegram для вас самая полезная?\n\n{hashtags}",
        }
        
        return fallbacks.get(theme, f"{theme_config['emoji']} **{theme_config['name']}**\n\n{theme_config['description']}\n\n✨ А что вы думаете по этой теме? Делитесь мнением в комментариях!\n\n{hashtags}")
    
    async def send_beautiful_post(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, content: str):
        """Красивая отправка поста с кнопками"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Нравится", callback_data="like"),
                InlineKeyboardButton("💬 Комментировать", callback_data="comment"),
                InlineKeyboardButton("📢 Репост", callback_data="repost")
            ],
            [
                InlineKeyboardButton("🔔 Подписаться", url=f"https://t.me/{channel_id}")
            ]
        ])
        
        try:
            # Пробуем отправить с кнопками
            await context.bot.send_message(
                chat_id=channel_id,
                text=content,
                parse_mode='Markdown',
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
        except:
            # Если ошибка с Markdown, отправляем без форматирования
            await context.bot.send_message(
                chat_id=channel_id,
                text=content,
                reply_markup=keyboard
            )
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                              theme: str, size: str, is_auto: bool = False) -> bool:
        """Публикация поста в канал"""
        try:
            content = await self.generate_post_content(theme, size)
            
            await self.send_beautiful_post(context, channel_id, content)
            
            post = Post(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                theme=theme,
                content=content[:200],
                posted_at=time.time(),
                size=size
            )
            self.post_history.append(post)
            self.statistics.total_posts += 1
            self.statistics.posts_by_theme[theme] = self.statistics.posts_by_theme.get(theme, 0) + 1
            self.statistics.posts_by_size[size] = self.statistics.posts_by_size.get(size, 0) + 1
            self.save_data()
            
            logger.info(f"✅ Пост опубликован в {channel_id} (тема: {theme}, размер: {size})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка публикации в {channel_id}: {e}")
            return False

bot = PostingBot()

# ==================== КРАСИВЫЕ КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    remaining = sub.get_remaining_posts()
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("✨ Создать пост сейчас", callback_data="create_post")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Размер поста", callback_data="select_size")],
        [InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("📋 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(page: int = 0, mode: str = "select"):
    themes_list = list(POSTING_THEMES.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    
    keyboard = []
    for theme_key, theme in themes_list[start:end]:
        keyboard.append([
            InlineKeyboardButton(
                f"{theme['emoji']} {theme['name']}",
                callback_data=f"theme_{mode}_{theme_key}"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"themes_page_{mode}_{page-1}"))
    if end < len(themes_list):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"themes_page_{mode}_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(mode: str = "select", channel_id: str = None):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        btn_text = f"{size['emoji']} {size['name']} — {size['desc']} ({size['min_chars']}-{size['max_chars']} симв.)"
        callback = f"size_{mode}_{size_key}"
        if channel_id:
            callback = f"size_{mode}_{channel_id}_{size_key}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(channel_id: str):
    keyboard = []
    row = []
    for interval, desc in AUTO_INTERVALS.items():
        row.append(InlineKeyboardButton(desc, callback_data=f"interval_{channel_id}_{interval}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff['color']} {tariff['name']} — {tariff['channels']} каналов, {tariff['posts_per_day']} постов/день",
                callback_data=f"tariff_info_{tariff_key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    sub = bot.get_user_subscription(user.id)
    
    welcome = f"""
✨ *Добро пожаловать в AI Пост-Бот, {user.first_name}!* ✨

🤖 *Я создаю качественные посты с помощью ИИ*

━━━━━━━━━━━━━━━━━━━━
📢 *Мои возможности:*

✅ {len(POSTING_THEMES)}+ тем для постов
✅ Автопостинг 24/7
✅ Красивое оформление
✅ Кнопки вовлечения
✅ Все тарифы *БЕСПЛАТНЫЕ*
✅ Безлимитные возможности

━━━━━━━━━━━━━━━━━━━━
🎯 *Ваш текущий тариф:*
{TARIFFS[sub.tariff]['color']} *{TARIFFS[sub.tariff]['name']}*
📊 Каналов: {len(sub.channels)}/{TARIFFS[sub.tariff]['channels']}
📝 Постов сегодня: {sub.posts_today}/{TARIFFS[sub.tariff]['posts_per_day']}
⚡ Осталось: {sub.get_remaining_posts()}

━━━━━━━━━━━━━━━━━━━━
💡 *Как начать:*
1️⃣ Добавьте бота в канал (админом)
2️⃣ Нажмите "➕ Добавить канал"
3️⃣ Настройте автопостинг
4️⃣ Наслаждайтесь контентом!

👇 *Выберите действие:*
"""
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "🔹 *Шаг 1:* Добавьте бота в канал\n"
        "🔹 *Шаг 2:* Сделайте бота администратором\n"
        "🔹 *Шаг 3:* Перешлите любое сообщение из канала сюда\n"
        "🔹 *Шаг 4:* Или отправьте ID канала (@username или -100xxxxxx)\n\n"
        "✅ Бот автоматически определит канал!",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        user_id = update.effective_user.id
        text = update.message.text
        
        sub = bot.get_user_subscription(user_id)
        tariff = TARIFFS[sub.tariff]
        
        if len(sub.channels) >= tariff["channels"]:
            await update.message.reply_text(
                f"❌ *Лимит каналов достигнут!*\n\n"
                f"Ваш тариф: {tariff['channels']} каналов\n"
                f"Удалите канал или выберите другой тариф",
                parse_mode='Markdown'
            )
            return
        
        channel_id = None
        channel_name = None
        
        # Определяем канал
        if text.startswith('@') or text.startswith('https://t.me/'):
            username = text.replace('https://t.me/', '').replace('@', '')
            try:
                chat = await context.bot.get_chat(f"@{username}")
                channel_id = str(chat.id)
                channel_name = chat.title
            except:
                await update.message.reply_text("❌ Не удалось найти канал. Проверьте username")
                return
        elif text.startswith('-100') or text.lstrip('-').isdigit():
            channel_id = text
            try:
                chat = await context.bot.get_chat(int(text))
                channel_name = chat.title
            except:
                channel_name = "Канал"
        elif update.message.forward_from_chat:
            chat = update.message.forward_from_chat
            channel_id = str(chat.id)
            channel_name = chat.title
        else:
            await update.message.reply_text("❌ Отправьте ID канала, ссылку или перешлите сообщение из канала")
            return
        
        if channel_id not in sub.channels:
            sub.channels.append(channel_id)
            bot.save_data()
            
            # Создаем конфиг автопостинга по умолчанию
            if channel_id not in bot.auto_configs:
                bot.auto_configs[channel_id] = AutoPostConfig(
                    channel_id=channel_id,
                    theme="ai_news",
                    size="medium",
                    interval_minutes=60,
                    next_post_time=time.time() + 3600
                )
                bot.save_data()
            
            await update.message.reply_text(
                f"✅ *Канал успешно добавлен!*\n\n"
                f"📢 Название: *{channel_name}*\n"
                f"📊 Каналов: {len(sub.channels)}/{tariff['channels']}\n\n"
                f"🎯 *Что дальше?*\n"
                f"• Настройте автопостинг в меню\n"
                f"• Выберите тему и размер постов\n"
                f"• Установите интервал публикации",
                parse_mode='Markdown'
            )
        
        context.user_data['awaiting_channel'] = False

async def create_post_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания поста"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await update.message.reply_text("❌ *Сначала добавьте канал!*\n\nНажмите '➕ Добавить канал' в меню", parse_mode='Markdown')
        return
    
    if not sub.can_post():
        await update.message.reply_text(
            f"⚠️ *Лимит постов на сегодня исчерпан!*\n\n"
            f"Сегодня опубликовано: {sub.posts_today}/{TARIFFS[sub.tariff]['posts_per_day']}\n"
            f"Завтра лимит обновится",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_themes_keyboard(mode="create")
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🎨 *Выберите тему для поста:*\n\n"
            "Всего доступно 20 уникальных тем",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "🎨 *Выберите тему для поста:*\n\n"
            "Всего доступно 20 уникальных тем",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def finalize_post(update: Update, context: ContextTypes.DEFAULT_TYPE, theme: str):
    """Финальный этап создания поста - выбор размера"""
    context.user_data['post_theme'] = theme
    keyboard = await get_sizes_keyboard(mode="publish")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"✅ *Тема выбрана:* {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\n"
            f"📏 *Выберите размер поста:*\n\n"
            f"🔹 Мини: 150-350 символов (коротко)\n"
            f"🔸 Короткий: 351-650 символов\n"
            f"📝 Средний: 651-1000 символов (рекомендуемый)\n"
            f"📄 Длинный: 1001-1500 символов\n"
            f"📚 Экспертный: 1501-2200 символов",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE, size: str, channel_id: str = None):
    """Публикация поста"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    theme = context.user_data.get('post_theme')
    
    if not theme:
        await update.callback_query.edit_message_text("❌ Ошибка: тема не выбрана")
        return
    
    if not sub.can_post():
        await update.callback_query.edit_message_text("❌ Достигнут лимит постов на сегодня!")
        return
    
    target_channel = channel_id or (sub.channels[0] if sub.channels else None)
    if not target_channel:
        await update.callback_query.edit_message_text("❌ Нет добавленных каналов")
        return
    
    # Отправляем уведомление о начале генерации
    loading_msg = await update.callback_query.edit_message_text(
        f"✨ *Генерирую пост...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[size]['name']}\n"
        f"🤖 Использую нейросеть GigaChat\n\n"
        f"⏳ Пожалуйста, подождите 5-10 секунд...",
        parse_mode='Markdown'
    )
    
    # Публикуем пост
    success = await bot.post_to_channel(context, target_channel, theme, size)
    
    if success:
        sub.add_post()
        bot.save_data()
        await loading_msg.edit_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"📊 Статистика:\n"
            f"• Сегодня: {sub.posts_today}/{TARIFFS[sub.tariff]['posts_per_day']}\n"
            f"• Осталось: {sub.get_remaining_posts()}\n\n"
            f"🎯 Создать еще один пост? Нажмите /start",
            parse_mode='Markdown'
        )
    else:
        await loading_msg.edit_text(
            "❌ *Ошибка при публикации поста*\n\n"
            "Проверьте:\n"
            "• Бот добавлен в канал\n"
            "• У бота есть права администратора\n"
            "• Канал существует\n\n"
            "Попробуйте еще раз или обратитесь в поддержку",
            parse_mode='Markdown'
        )

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню настройки автопостинга"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        text = "❌ *У вас нет добавленных каналов*\n\nДобавьте канал через '➕ Добавить канал'"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = "🤖 *Настройка автопостинга*\n\n"
    text += "Выберите канал для настройки:\n\n"
    
    keyboard = []
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            config = bot.auto_configs.get(channel_id)
            status = "✅" if config and config.is_active else "⏸"
            theme_name = POSTING_THEMES.get(config.theme, {}).get('name', 'не настроена') if config else 'не настроен'
            
            text += f"{status} *{chat.title}*\n"
            text += f"   🎨 Тема: {theme_name}\n"
            if config:
                text += f"   ⏱ Интервал: {config.interval_minutes} мин\n"
            text += "\n"
            
            keyboard.append([InlineKeyboardButton(f"⚙️ {chat.title}", callback_data=f"config_auto_{channel_id}")])
        except:
            pass
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def configure_auto_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    """Настройка автопостинга для конкретного канала"""
    config = bot.auto_configs.get(channel_id)
    
    try:
        chat = await context.bot.get_chat(int(channel_id))
        channel_name = chat.title
    except:
        channel_name = "Канал"
    
    theme_name = POSTING_THEMES.get(config.theme, {}).get('name', 'не выбрана') if config else 'не выбрана'
    size_name = POST_SIZES.get(config.size, {}).get('name', 'не выбран') if config else 'не выбран'
    interval = config.interval_minutes if config else 60
    status = "✅ ВКЛЮЧЕН" if config and config.is_active else "⏸ ВЫКЛЮЧЕН"
    status_emoji = "🟢" if config and config.is_active else "🔴"
    
    text = f"""
⚙️ *Настройка канала:* {channel_name}

{status_emoji} *Статус:* {status}
🎨 *Тема:* {theme_name}
📏 *Размер:* {size_name}
⏱ *Интервал:* {interval} минут

━━━━━━━━━━━━━━━━━━━━
*Что можно настроить:*
▫️ Тему постов
▫️ Размер постов  
▫️ Частоту публикации
▫️ Включить/выключить
"""
    
    keyboard = [
        [InlineKeyboardButton("🎨 Сменить тему", callback_data=f"change_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Сменить размер", callback_data=f"change_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Сменить интервал", callback_data=f"change_interval_{channel_id}")],
    ]
    
    if config and config.is_active:
        keyboard.append([InlineKeyboardButton("⏸ Остановить автопостинг", callback_data=f"stop_auto_{channel_id}")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Запустить автопостинг", callback_data=f"start_auto_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к каналам", callback_data="auto_posting")])
    
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def change_auto_theme(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    """Смена темы автопостинга"""
    context.user_data['changing_theme_for'] = channel_id
    keyboard = await get_themes_keyboard(mode=f"autotheme_{channel_id}")
    await update.callback_query.edit_message_text(
        "🎨 *Выберите новую тему для автопостинга:*\n\n"
        "Посты будут генерироваться на выбранную тему",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def change_auto_size(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    """Смена размера автопостинга"""
    keyboard = await get_sizes_keyboard(mode=f"autosize_{channel_id}")
    await update.callback_query.edit_message_text(
        "📏 *Выберите размер постов для автопостинга:*\n\n"
        "Размер влияет на глубину контента",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def change_auto_interval(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    """Смена интервала автопостинга"""
    keyboard = await get_intervals_keyboard(channel_id)
    await update.callback_query.edit_message_text(
        "⏱ *Выберите интервал публикации:*\n\n"
        "🔟 10 минут — максимальная частота\n"
        "⭐ 1 час — оптимальный вариант\n"
        "🕙 24 часа — ежедневные посты\n\n"
        "Чем чаще посты, тем больше вовлеченность!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайный пост"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await update.message.reply_text("❌ Сначала добавьте канал!")
        return
    
    if not sub.can_post():
        await update.message.reply_text(f"❌ Лимит постов! Сегодня: {sub.posts_today}/{TARIFFS[sub.tariff]['posts_per_day']}")
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    msg = await update.message.reply_text(
        f"🎲 *Генерирую случайный пост...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[random_theme]['emoji']} {POSTING_THEMES[random_theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[random_size]['name']}\n\n"
        f"⏳ Подождите немного...",
        parse_mode='Markdown'
    )
    
    success = await bot.post_to_channel(context, sub.channels[0], random_theme, random_size)
    
    if success:
        sub.add_post()
        bot.save_data()
        await msg.edit_text(
            f"✅ *Случайный пост опубликован!*\n\n"
            f"📊 Осталось постов: {sub.get_remaining_posts()}\n"
            f"🎯 Хотите еще? Нажмите /start",
            parse_mode='Markdown'
        )
    else:
        await msg.edit_text("❌ Ошибка при публикации")

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список каналов пользователя"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    if not sub.channels:
        text = "📋 *У вас пока нет добавленных каналов*\n\n➕ Добавьте канал через главное меню"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = f"📋 *Ваши каналы* ({len(sub.channels)}/{tariff['channels']})\n\n"
    
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            config = bot.auto_configs.get(channel_id)
            
            text += f"📢 **{chat.title}**\n"
            text += f"🆔 `{channel_id}`\n"
            
            if config:
                theme = POSTING_THEMES.get(config.theme, {})
                size = POST_SIZES.get(config.size, {})
                text += f"🎨 {theme.get('emoji', '')} {theme.get('name', 'не настроена')}\n"
                text += f"📏 {size.get('name', 'не настроен')}\n"
                text += f"⏱ {config.interval_minutes} мин | "
                text += f"{'✅ Активен' if config.is_active else '⏸ Остановлен'}\n"
            text += "\n"
        except Exception as e:
            text += f"⚠️ Канал недоступен: {channel_id}\n\n"
    
    keyboard = []
    for channel_id in sub.channels:
        try:
            chat = await context.bot.get_chat(int(channel_id))
            keyboard.append([InlineKeyboardButton(f"🗑 Удалить {chat.title}", callback_data=f"delete_channel_{channel_id}")])
        except:
            pass
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    """Удаление канала"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.channels:
        sub.channels.remove(channel_id)
        if channel_id in bot.auto_configs:
            del bot.auto_configs[channel_id]
        bot.save_data()
        
        await update.callback_query.answer("Канал удален!")
        await my_channels(update, context)

async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика пользователя"""
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    # Статистика по постам пользователя
    user_posts = [p for p in bot.post_history if p.channel_id in sub.channels]
    
    text = f"""
📊 *Ваша статистика*

{tariff['color']} *Тариф:* {tariff['name']}
📊 *Каналов:* {len(sub.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {sub.posts_today}/{tariff['posts_per_day']}
⚡ *Осталось:* {sub.get_remaining_posts()}

━━━━━━━━━━━━━━━━━━━━
📈 *Всего постов:* {len(user_posts)}
🎨 *Уникальных тем:* {len(set(p.theme for p in user_posts))}
📅 *Время в боте:* {int((time.time() - sub.subscribed_at) / 86400)} дней

━━━━━━━━━━━━━━━━━━━━
📊 *Глобальная статистика:*
✨ Всего постов: {bot.statistics.total_posts}
🎯 Всего тем: {len(POSTING_THEMES)}
👥 Активных пользователей: {len(bot.user_subscriptions)}

💡 *Совет:* Чем чаще посты, тем быстрее рост канала!
"""
    
    keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="stats")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о тарифах"""
    text = """
💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ* 💎

🌟 *Стартовый* — 2 канала, 20 постов/день
⚡ *Базовый* — 5 каналов, 50 постов/день  
💎 *Профессиональный* — 15 каналов, 150 постов/день
👑 *Премиум* — Безлимит каналов, 500 постов/день

━━━━━━━━━━━━━━━━━━━━
*ВОЗМОЖНОСТИ ВСЕХ ТАРИФОВ:*
✅ Генерация постов ИИ
✅ Автопостинг 24/7
✅ 20+ уникальных тем
✅ Красивое оформление
✅ Кнопки вовлечения
✅ Перепост из каналов
✅ Настраиваемые интервалы
✅ Статистика и аналитика

━━━━━━━━━━━━━━━━━━━━
🎁 *ВСЕ ФУНКЦИИ ДОСТУПНЫ БЕСПЛАТНО!*

Просто добавьте бота в канал и начните получать качественный контент автоматически!
"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    text = """
🆘 *Помощь и инструкция*

━━━━━━━━━━━━━━━━━━━━
📌 *БЫСТРЫЙ СТАРТ:*
1. Добавьте @{bot_username} в канал
2. Сделайте бота администратором
3. Нажмите "➕ Добавить канал"
4. Перешлите сообщение из канала
5. Настройте автопостинг

━━━━━━━━━━━━━━━━━━━━
🎯 *ВОЗМОЖНОСТИ:*

✨ *Создание постов*
• Ручной пост — выберите тему и размер
• Случайный пост —一键 генерация
• Автопостинг — автоматически по расписанию

🎨 *20+ тем на выбор:*
AI, Крипта, NFT, Telegram, Бизнес, Технологии, Наука, Здоровье, Психология, Маркетинг, Дизайн, Программирование, Игры, Кино, Музыка, Спорт, Путешествия, Кулинария, Образование, Мотивация

📏 *Размеры постов:*
• Мини (150-350) — коротко
• Короткий (350-650) — оптимально
• Средний (650-1000) — рекомендуемый
• Длинный (1000-1500) — подробно
• Экспертный (1500-2200) — глубоко

⏱ *Интервалы автопостинга:*
От 10 минут до 24 часов

━━━━━━━━━━━━━━━━━━━━
💡 *СОВЕТЫ:*
• Для быстрого роста ставьте интервал 1-2 часа
• Меняйте темы для разнообразия
• Используйте кнопки вовлечения
• Анализируйте статистику

━━━━━━━━━━━━━━━━━━━━
❓ *Вопросы:* @support
"""
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")]]
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== АВТОМАТИЧЕСКАЯ ПУБЛИКАЦИЯ ====================
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """Job для автоматической публикации постов"""
    current_time = time.time()
    
    for channel_id, config in bot.auto_configs.items():
        if not config.is_active:
            continue
        
        if current_time >= config.next_post_time:
            # Ищем владельца канала
            for user_id, sub in bot.user_subscriptions.items():
                if channel_id in sub.channels and sub.can_post():
                    # Публикуем пост
                    success = await bot.post_to_channel(context, channel_id, config.theme, config.size, is_auto=True)
                    
                    if success:
                        config.last_post = current_time
                        config.update_next_post()
                        sub.add_post()
                        bot.save_data()
                        logger.info(f"🤖 Автопостинг в {channel_id}: тема {config.theme}, интервал {config.interval_minutes}мин")
                    break

# ==================== CALLBACK ОБРАБОТЧИК ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик callback запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Главное меню
    if data == "back_main":
        keyboard = await get_main_keyboard(query.from_user.id)
        await query.edit_message_text("🏠 *Главное меню*\n\nВыберите нужное действие:", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_channel":
        context.user_data['awaiting_channel'] = True
        await query.edit_message_text(
            "📢 *Добавление канала*\n\n"
            "1️⃣ Добавьте бота в канал\n"
            "2️⃣ Сделайте бота администратором\n"
            "3️⃣ Перешлите сообщение из канала\n\n"
            "✏️ Отправьте сюда сообщение из канала:",
            parse_mode='Markdown'
        )
    
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    
    elif data == "create_post":
        await create_post_flow(update, context)
    
    elif data == "select_theme":
        keyboard = await get_themes_keyboard(mode="select")
        await query.edit_message_text("🎨 *Все доступные темы:*\n\nВыберите интересующую тему", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "select_size":
        keyboard = await get_sizes_keyboard(mode="info")
        await query.edit_message_text("📏 *Размеры постов:*\n\nВыберите размер для просмотра описания", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "random_post":
        await random_post(update, context)
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "stats":
        await stats_menu(update, context)
    
    elif data == "tariffs":
        await tariffs_info(update, context)
    
    elif data == "help":
        await help_message(update, context)
    
    # Обработка выбора темы для создания поста
    elif data.startswith("theme_create_"):
        theme = data.replace("theme_create_", "")
        await finalize_post(update, context, theme)
    
    # Обработка выбора размера для публикации
    elif data.startswith("size_publish_"):
        size = data.replace("size_publish_", "")
        await publish_post(update, context, size)
    
    # Навигация по страницам тем
    elif data.startswith("themes_page_"):
        parts = data.split("_")
        page = int(parts[3])
        mode = parts[2]
        keyboard = await get_themes_keyboard(page=page, mode=mode)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    # Настройка автопостинга для канала
    elif data.startswith("config_auto_"):
        channel_id = data.replace("config_auto_", "")
        await configure_auto_channel(update, context, channel_id)
    
    # Смена темы автопостинга
    elif data.startswith("change_theme_"):
        channel_id = data.replace("change_theme_", "")
        await change_auto_theme(update, context, channel_id)
    
    # Смена размера автопостинга
    elif data.startswith("change_size_"):
        channel_id = data.replace("change_size_", "")
        await change_auto_size(update, context, channel_id)
    
    # Смена интервала
    elif data.startswith("change_interval_"):
        channel_id = data.replace("change_interval_", "")
        await change_auto_interval(update, context, channel_id)
    
    # Установка новой темы для автопостинга
    elif data.startswith("theme_autotheme_"):
        parts = data.split("_")
        channel_id = parts[2]
        theme = "_".join(parts[3:])
        
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].theme = theme
            bot.save_data()
            await query.edit_message_text(f"✅ Тема изменена на: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}")
            await configure_auto_channel(update, context, channel_id)
    
    # Установка нового размера для автопостинга
    elif data.startswith("size_autosize_"):
        parts = data.split("_")
        channel_id = parts[2]
        size = parts[3]
        
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].size = size
            bot.save_data()
            await query.edit_message_text(f"✅ Размер изменен на: {POST_SIZES[size]['name']}")
            await configure_auto_channel(update, context, channel_id)
    
    # Установка интервала
    elif data.startswith("interval_"):
        parts = data.split("_")
        channel_id = parts[1]
        interval = int(parts[2])
        
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].interval_minutes = interval
            bot.auto_configs[channel_id].update_next_post()
            bot.save_data()
            await query.edit_message_text(f"✅ Интервал установлен: {interval} минут")
            await configure_auto_channel(update, context, channel_id)
    
    # Запуск автопостинга
    elif data.startswith("start_auto_"):
        channel_id = data.replace("start_auto_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = True
            bot.auto_configs[channel_id].update_next_post()
            bot.save_data()
            await query.edit_message_text("✅ Автопостинг запущен!")
            await configure_auto_channel(update, context, channel_id)
    
    # Остановка автопостинга
    elif data.startswith("stop_auto_"):
        channel_id = data.replace("stop_auto_", "")
        if channel_id in bot.auto_configs:
            bot.auto_configs[channel_id].is_active = False
            bot.save_data()
            await query.edit_message_text("⏸ Автопостинг остановлен")
            await configure_auto_channel(update, context, channel_id)
    
    # Удаление канала
    elif data.startswith("delete_channel_"):
        channel_id = data.replace("delete_channel_", "")
        await delete_channel(update, context, channel_id)
    
    # Кнопки лайков/комментов (для бонуса)
    elif data in ["like", "comment", "repost"]:
        await query.answer("Спасибо за взаимодействие! 👍")

# ==================== ЗАПУСК БОТА ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_add))
    
    # Job для автопостинга (проверка каждые 30 секунд)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_job, interval=30, first=10)
    
    logger.info("=" * 50)
    logger.info("🚀 AI ПОСТ-БОТ ЗАПУЩЕН!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Все тарифы бесплатные!")
    logger.info(f"⏱ Интервалы: от 10 минут")
    logger.info(f"✨ Красивое оформление постов")
    logger.info("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
