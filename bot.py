import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
import re
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
        "name": "🌟 Базовый",
        "price": 0,
        "channels": 5,
        "posts_per_day": 100,
        "interval_min": 10,
        "can_repost": True,
        "has_images": True,
        "color": "🟢"
    },
    "basic": {
        "name": "⭐ Стандарт",
        "price": 0,
        "channels": 15,
        "posts_per_day": 500,
        "interval_min": 5,
        "can_repost": True,
        "has_images": True,
        "color": "🔵"
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 0,
        "channels": 50,
        "posts_per_day": 1500,
        "interval_min": 3,
        "can_repost": True,
        "has_images": True,
        "color": "🟣"
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels": 200,
        "posts_per_day": 5000,
        "interval_min": 1,
        "can_repost": True,
        "has_images": True,
        "color": "🔴"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (30+ ТЕМ) ====================
POSTING_THEMES = {
    # === ТЕХНОЛОГИИ И IT ===
    "ai_news": {
        "name": "🤖 Новости AI",
        "emoji": "🤖",
        "category": "Технологии",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#AI #ИскусственныйИнтеллект #НовостиAI #ChatGPT",
        "prompt": "Ты журналист, пишущий об AI. Создай интересный и уникальный пост о последних новостях в мире искусственного интеллекта, нейросетях, ChatGPT."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "category": "Соцсети",
        "description": "Новости Telegram, боты, каналы",
        "hashtags": "#Telegram #Мессенджер #Обновления #TelegramBot",
        "prompt": "Ты блогер о Telegram. Создай уникальный пост о новых функциях Telegram, топовых ботах, полезных каналах, секретных фишках мессенджера."
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "category": "Криптовалюты",
        "description": "Новости NFT и цифрового искусства",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная #OpenSea",
        "prompt": "Ты эксперт по NFT. Создай уникальный пост о NFT коллекциях, digital art, метавселенных, трендах NFT рынка."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "category": "Криптовалюты",
        "description": "Новости криптовалют и блокчейна",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн #Ethereum #DeFi",
        "prompt": "Ты крипто-аналитик. Создай уникальный пост о криптовалютах, блокчейне, DeFi, трендах рынка, биткоине, альткоинах."
    },
    "web3": {
        "name": "🌐 Web3",
        "emoji": "🌐",
        "category": "Криптовалюты",
        "description": "Web3, децентрализация, блокчейн",
        "hashtags": "#Web3 #Децентрализация #Блокчейн #DAO",
        "prompt": "Ты эксперт по Web3. Создай уникальный пост о Web3 технологиях, децентрализации, DAO, будущем интернета."
    },
    "metaverse": {
        "name": "🕶️ Метавселенная",
        "emoji": "🕶️",
        "category": "Технологии",
        "description": "Метавселенные и виртуальная реальность",
        "hashtags": "#Метавселенная #VR #AR #VirtualReality",
        "prompt": "Ты эксперт по метавселенным. Создай уникальный пост о метавселенных, VR/AR технологиях, виртуальных мирах."
    },
    
    # === БИЗНЕС И МАРКЕТИНГ ===
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "category": "Бизнес",
        "description": "Бизнес новости и советы",
        "hashtags": "#Бизнес #Стартап #Предпринимательство #Успех",
        "prompt": "Ты бизнес-журналист. Создай уникальный пост о бизнесе, стартапах, инвестициях, успешных кейсах, предпринимательстве."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "category": "Маркетинг",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Реклама #Таргет",
        "prompt": "Ты маркетолог. Создай уникальный пост о маркетинге, SMM, рекламе, таргетинге, контент-маркетинге."
    },
    "startup": {
        "name": "🚀 Стартапы",
        "emoji": "🚀",
        "category": "Бизнес",
        "description": "Стартапы и инновации",
        "hashtags": "#Стартап #Инновации #Венчур #Инвестиции",
        "prompt": "Ты предприниматель. Создай уникальный пост о стартапах, инновациях, венчурных инвестициях, успешных запусках."
    },
    
    # === НАУКА И ОБРАЗОВАНИЕ ===
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "category": "Наука",
        "description": "Научные открытия",
        "hashtags": "#Наука #Открытия #Исследования #Физика",
        "prompt": "Ты научный журналист. Создай уникальный пост о научных открытиях и исследованиях."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "category": "Образование",
        "description": "Образование и обучение",
        "hashtags": "#Образование #Учеба #Знания #Курсы",
        "prompt": "Ты педагог. Создай уникальный полезный пост об образовании, обучении, полезных курсах."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "category": "Психология",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация #ЛичностныйРост",
        "prompt": "Ты психолог. Создай уникальный полезный пост по психологии и саморазвитию."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "category": "Мотивация",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Вдохновение #Цели",
        "prompt": "Ты мотивационный спикер. Создай уникальный вдохновляющий пост о достижении целей, успехе, мотивации."
    },
    
    # === ЗДОРОВЬЕ И ЖИЗНЬ ===
    "health": {
        "name": "💊 Здоровье",
        "emoji": "💊",
        "category": "Здоровье",
        "description": "Здоровье и медицина",
        "hashtags": "#Здоровье #Медицина #ЗОЖ #Спорт",
        "prompt": "Ты медицинский блогер. Создай уникальный полезный пост о здоровье, ЗОЖ, профилактике болезней."
    },
    "fitness": {
        "name": "🏋️ Фитнес",
        "emoji": "🏋️",
        "category": "Спорт",
        "description": "Фитнес и тренировки",
        "hashtags": "#Фитнес #Тренировки #ЗОЖ #Спорт",
        "prompt": "Ты фитнес-тренер. Создай уникальный пост о фитнесе, тренировках, правильном питании, здоровом образе жизни."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "category": "Кулинария",
        "description": "Кулинария и рецепты",
        "hashtags": "#Кулинария #Рецепты #Еда #Вкусно",
        "prompt": "Ты кулинарный блогер. Создай уникальный пост о еде, рецептах, кулинарных лайфхаках."
    },
    
    # === ТЕХНОЛОГИИ ===
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "category": "Технологии",
        "description": "Технологические новости",
        "hashtags": "#Технологии #Гаджеты #Инновации #Tech",
        "prompt": "Ты техноблогер. Создай уникальный пост о новых технологиях, гаджетах, изобретениях."
    },
    "gadgets": {
        "name": "📱 Гаджеты",
        "emoji": "📱",
        "category": "Технологии",
        "description": "Обзоры гаджетов",
        "hashtags": "#Гаджеты #Смартфоны #Apple #Xiaomi #Samsung",
        "prompt": "Ты обзорщик гаджетов. Создай уникальный пост о новых смартфонах, наушниках, умных устройствах."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "category": "IT",
        "description": "IT и разработка",
        "hashtags": "#Программирование #IT #Код #Python #JavaScript",
        "prompt": "Ты разработчик. Создай уникальный полезный пост о программировании, языках кода, IT-карьере."
    },
    "cybersecurity": {
        "name": "🔒 Кибербезопасность",
        "emoji": "🔒",
        "category": "IT",
        "description": "Кибербезопасность",
        "hashtags": "#Кибербезопасность #Безопасность #VPN #Хакеры",
        "prompt": "Ты эксперт по кибербезопасности. Создай уникальный пост о безопасности в интернете, защите данных, VPN."
    },
    
    # === РАЗВЛЕЧЕНИЯ ===
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "category": "Игры",
        "description": "Игровые новости",
        "hashtags": "#Игры #Гейминг #Видеоигры #PS5 #Xbox",
        "prompt": "Ты игровой журналист. Создай уникальный пост об играх, гейминге, новинках игр."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "category": "Развлечения",
        "description": "Новости кино",
        "hashtags": "#Кино #Фильмы #Сериалы #Кинопремьеры",
        "prompt": "Ты кинокритик. Создай уникальный пост о новинках кино и сериалов."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "category": "Развлечения",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Хиты #Плейлист",
        "prompt": "Ты музыкальный обозреватель. Создай уникальный пост о музыке, новых альбомах, плейлистах."
    },
    "anime": {
        "name": "🎌 Аниме",
        "emoji": "🎌",
        "category": "Развлечения",
        "description": "Новости аниме",
        "hashtags": "#Аниме #Anime #Манга #Косплей",
        "prompt": "Ты аниме-блогер. Создай уникальный пост о популярных аниме, новостях аниме-индустрии, манге."
    },
    
    # === СПОРТ ===
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "category": "Спорт",
        "description": "Спортивные новости",
        "hashtags": "#Спорт #Футбол #Баскетбол #Теннис #UFC",
        "prompt": "Ты спортивный журналист. Создай уникальный пост о спорте, футболе, баскетболе, теннисе."
    },
    "football": {
        "name": "⚽ Футбол",
        "emoji": "⚽",
        "category": "Спорт",
        "description": "Футбольные новости",
        "hashtags": "#Футбол #UCL #ЛигаЧемпионов #РеалМадрид #Месси",
        "prompt": "Ты футбольный журналист. Создай уникальный пост о футболе, чемпионатах, трансферах, матчах."
    },
    
    # === ПУТЕШЕСТВИЯ ===
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "category": "Путешествия",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Туризм #Отдых #Тревел",
        "prompt": "Ты тревел-блогер. Создай уникальный пост о путешествиях, туризме, лучших местах для отдыха."
    },
    "photography": {
        "name": "📷 Фотография",
        "emoji": "📷",
        "category": "Искусство",
        "description": "Фотография и искусство",
        "hashtags": "#Фотография #Фото #Искусство #Пленка",
        "prompt": "Ты фотограф. Создай уникальный пост о фотографии, советах по съемке, искусстве."
    },
    
    # === ДИЗАЙН И ТВОРЧЕСТВО ===
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "category": "Дизайн",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #Креатив #Вдохновение #UIUX",
        "prompt": "Ты дизайнер. Создай уникальный вдохновляющий пост о дизайне, графике, UI/UX."
    },
    
    # === АВТО ===
    "auto": {
        "name": "🚗 Авто",
        "emoji": "🚗",
        "category": "Авто",
        "description": "Автомобили и новинки",
        "hashtags": "#Авто #Машины #Электромобили #Тесла",
        "prompt": "Ты автомобильный блогер. Создай уникальный пост об автомобилях, новинках автопрома, электромобилях."
    },
    "tesla": {
        "name": "🔋 Tesla",
        "emoji": "🔋",
        "category": "Авто",
        "description": "Новости Tesla и электромобили",
        "hashtags": "#Tesla #Электромобили #ИлонМаск #Cybertruck",
        "prompt": "Ты эксперт по Tesla. Создай уникальный пост о Tesla, Илоне Маске, электромобилях, инновациях."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "🔹 Мини", "chars": 200, "emoji": "🔹"},
    "short": {"name": "🔸 Короткий", "chars": 400, "emoji": "🔸"},
    "medium": {"name": "📄 Средний", "chars": 700, "emoji": "📄"},
    "long": {"name": "📚 Длинный", "chars": 1000, "emoji": "📚"},
    "extra": {"name": "📖 Макси", "chars": 1500, "emoji": "📖"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class AutoPostConfig:
    channel_id: str
    channel_name: str
    channel_username: str
    theme: str
    size: str
    interval_seconds: int
    is_active: bool = True
    last_post: float = 0
    job_running: bool = False

@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    channels: List[dict] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    auto_posts: Dict[str, AutoPostConfig] = field(default_factory=dict)
    
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

# ==================== ОСНОВНОЕ ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.user_subscriptions: Dict[int, UserSubscription] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_counter = 0
        self.active_jobs: Dict[str, asyncio.Task] = {}
    
    def load_data(self):
        try:
            with open("subscriptions.json", "r", encoding='utf-8') as f:
                data = json.load(f)
                for user_id, sub_data in data.items():
                    user_id = int(user_id)
                    sub = UserSubscription(
                        user_id=user_id,
                        tariff=sub_data.get("tariff", "free"),
                        channels=sub_data.get("channels", []),
                        posts_today=sub_data.get("posts_today", 0),
                        last_reset=sub_data.get("last_reset", time.time())
                    )
                    for ch_id, cfg_data in sub_data.get("auto_posts", {}).items():
                        sub.auto_posts[ch_id] = AutoPostConfig(**cfg_data)
                    self.user_subscriptions[user_id] = sub
        except FileNotFoundError:
            logger.info("Файл subscriptions.json не найден, создаем новый")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
    
    def save_data(self):
        try:
            data = {}
            for user_id, sub in self.user_subscriptions.items():
                auto_posts = {}
                for ch_id, cfg in sub.auto_posts.items():
                    auto_posts[ch_id] = {
                        "channel_id": cfg.channel_id,
                        "channel_name": cfg.channel_name,
                        "channel_username": cfg.channel_username,
                        "theme": cfg.theme,
                        "size": cfg.size,
                        "interval_seconds": cfg.interval_seconds,
                        "is_active": cfg.is_active,
                        "last_post": cfg.last_post
                    }
                data[user_id] = {
                    "tariff": sub.tariff,
                    "channels": sub.channels,
                    "posts_today": sub.posts_today,
                    "last_reset": sub.last_reset,
                    "auto_posts": auto_posts
                }
            with open("subscriptions.json", "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def get_user_subscription(self, user_id: int) -> UserSubscription:
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = UserSubscription(
                user_id=user_id,
                tariff="free",
                channels=[]
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
            logger.error(f"Ошибка токена: {e}")
        return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

ВАЖНО: Создай УНИКАЛЬНЫЙ, ИНТЕРЕСНЫЙ пост, который привлечет внимание читателей.

Требования к посту:
- Длина: примерно {size_config['chars']} символов
- Используй красивые эмодзи для оформления (минимум 5-7 разных эмодзи)
- Добавь в конце хэштеги: {theme_config['hashtags']}
- Пиши на русском языке, интересно и вовлекающе
- Добавь вопрос к подписчикам в конце поста для комментариев
- Пост должен быть полезным, информативным или вдохновляющим
- Используй маркированные списки где уместно

Структура поста:
1. Яркий привлекающий заголовок с эмодзи
2. Основной полезный контент (разбитый на абзацы)
3. Вопрос к аудитории или призыв к действию
4. Хэштеги"""

        if not token:
            return self._get_fallback_post(theme)
        
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
                        "temperature": 0.9,
                        "max_tokens": 2500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                            return content
                    elif response.status == 401:
                        self.api_token = None
                        return await self.generate_post(theme, size)
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme)
    
    def _get_fallback_post(self, theme: str) -> str:
        fallbacks = {
            "ai_news": "🤖 *Искусственный интеллект меняет мир!*\n\nКаждый день появляются новые нейросети и AI-инструменты. Как вы относитесь к развитию ИИ? Делитесь мнением!\n\n👇\n\n#AI #Нейросети #Технологии",
            "telegram": "📱 *Telegram - лучший мессенджер!*\n\nА вы знали все скрытые функции Telegram? Расскажите в комментариях, какие боты и каналы вы используете!\n\n👇\n\n#Telegram #СекретыTelegram #Боты",
            "nft": "🎨 *NFT - цифровое искусство будущего!*\n\nКоллекционируете ли вы NFT? Какая ваша любимая коллекция? Пишите в комментариях!\n\n👇\n\n#NFT #ЦифровоеИскусство #Крипта",
            "crypto": "🪙 *Криптовалюта - новый тренд!*\n\nБиткоин снова растет! А вы инвестируете в крипту? Делитесь своим опытом!\n\n👇\n\n#Биткоин #Криптовалюта #Инвестиции",
            "programming": "💻 *Программирование - навык будущего!*\n\nКакой язык программирования вы учите или используете? Что посоветуете новичкам?\n\n👇\n\n#Программирование #Код #IT"
        }
        return fallbacks.get(theme, f"✨ *{POSTING_THEMES[theme]['name']}*\n\nИнтересная тема для обсуждения! А что вы думаете по этому поводу?\n\n👇 Делитесь мнением в комментариях!\n\n{POSTING_THEMES[theme]['hashtags']}")
    
    async def format_and_send_post(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                                    theme: str, size: str, is_auto: bool = False) -> bool:
        try:
            content = await self.generate_post(theme, size)
            self.post_counter += 1
            
            theme_config = POSTING_THEMES[theme]
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            formatted_post = f"""━━━━━━━━━━━━━━━━━━━━━
{theme_config['emoji']} *{theme_config['name']}* {theme_config['emoji']}
━━━━━━━━━━━━━━━━━━━━━

{content}

━━━━━━━━━━━━━━━━━━━━━
📅 {timestamp} | 📊 Пост #{self.post_counter}
💬 Ждем ваши комментарии!
🚀 Создано с любовью ❤️
━━━━━━━━━━━━━━━━━━━━━"""
            
            await context.bot.send_message(
                chat_id=channel_id,
                text=formatted_post,
                parse_mode='Markdown'
            )
            
            for user_id, sub in self.user_subscriptions.items():
                for ch in sub.channels:
                    if ch.get("id") == channel_id:
                        if not is_auto:
                            sub.add_post()
                        break
            
            self.save_data()
            logger.info(f"✅ Пост отправлен в канал {channel_id} на тему {theme}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Настройка автопостинга", callback_data="auto_posting")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="select_size")],
        [InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("📋 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_themes_by_category():
    """Группировка тем по категориям"""
    categories = {}
    for key, theme in POSTING_THEMES.items():
        cat = theme.get("category", "Другое")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, theme))
    return categories

async def get_themes_keyboard(page: int = 0):
    themes_list = list(POSTING_THEMES.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    
    keyboard = []
    for theme_key, theme in themes_list[start:end]:
        keyboard.append([InlineKeyboardButton(
            f"{theme['emoji']} {theme['name']}",
            callback_data=f"theme_{theme_key}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"themes_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("📂 По категориям", callback_data="themes_categories")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_categories_keyboard():
    categories = await get_themes_by_category()
    keyboard = []
    for category in categories.keys():
        emoji_map = {
            "Технологии": "📡",
            "Криптовалюты": "🪙",
            "Бизнес": "💼",
            "Маркетинг": "📈",
            "Наука": "🔬",
            "Образование": "📚",
            "Психология": "🧠",
            "Мотивация": "💪",
            "Здоровье": "💊",
            "Спорт": "⚽",
            "Кулинария": "🍳",
            "IT": "💻",
            "Игры": "🎮",
            "Развлечения": "🎬",
            "Путешествия": "✈️",
            "Искусство": "🎨",
            "Дизайн": "🎨",
            "Авто": "🚗",
            "Соцсети": "📱",
            "Другое": "📌"
        }
        emoji = emoji_map.get(category, "📌")
        keyboard.append([InlineKeyboardButton(f"{emoji} {category}", callback_data=f"category_{category}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад к темам", callback_data="back_to_themes")])
    return InlineKeyboardMarkup(keyboard)

async def get_themes_by_category_keyboard(category: str):
    categories = await get_themes_by_category()
    themes = categories.get(category, [])
    
    keyboard = []
    for theme_key, theme in themes:
        keyboard.append([InlineKeyboardButton(
            f"{theme['emoji']} {theme['name']}",
            callback_data=f"theme_{theme_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="themes_categories")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard():
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} (~{size['chars']} симв.)",
            callback_data=f"size_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard():
    intervals = [10, 30, 60, 300, 600, 1800, 3600, 7200, 21600, 43200, 86400]
    keyboard = []
    row = []
    for sec in intervals:
        if sec < 60:
            text = f"{sec} сек"
        elif sec < 3600:
            text = f"{sec//60} мин"
        elif sec < 86400:
            text = f"{sec//3600} ч"
        else:
            text = f"{sec//86400} дн"
        row.append(InlineKeyboardButton(text, callback_data=f"interval_{sec}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⚡ Свой интервал", callback_data="custom_interval")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    
    welcome = f"""━━━━━━━━━━━━━━━━━━━━━
✨ *ПРИВЕТ, {user.first_name}!* ✨
━━━━━━━━━━━━━━━━━━━━━

🤖 *AI Бот для автопостинга*

🎯 *Мои возможности:*
• 📝 Генерация уникальных постов через ИИ (GigaChat)
• 🎨 *30+ разных тематик* на выбор!
• ⏱ Автопостинг от 10 секунд!
• 📏 5 размеров постов
• 💰 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*

━━━━━━━━━━━━━━━━━━━━━
📌 *Доступные темы (30+):*

🤖 Новости AI | 📱 Telegram | 🎨 NFT
🪙 Криптовалюты | 🌐 Web3 | 🕶️ Метавселенная
💼 Бизнес | 📈 Маркетинг | 🚀 Стартапы
🔬 Наука | 📚 Образование | 🧠 Психология
💪 Мотивация | 💊 Здоровье | 🏋️ Фитнес
🍳 Кулинария | 📡 Технологии | 📱 Гаджеты
💻 Программирование | 🔒 Кибербезопасность
🎮 Игры | 🎬 Кино | 🎵 Музыка | 🎌 Аниме
⚽ Спорт | ✈️ Путешествия | 📷 Фотография
🎨 Дизайн | 🚗 Авто | 🔋 Tesla

━━━━━━━━━━━━━━━━━━━━━
👇 *Выберите действие ниже:*"""

    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📢 *ДОБАВЛЕНИЕ КАНАЛА*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *Отправьте ССЫЛКУ на канал:*\n\n"
        "• https://t.me/username\n"
        "• t.me/username\n"
        "• @username\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *ВАЖНО:*\n"
        "1. Бот должен быть АДМИНИСТРАТОРОМ канала\n"
        "2. Ссылка должна быть публичной\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel_link'] = True

async def extract_username_from_link(text: str) -> str:
    """Извлекает username из ссылки"""
    patterns = [
        r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)',
        r'(?:https?://)?(?:www\.)?telegram\.me/([a-zA-Z0-9_]+)',
        r'@([a-zA-Z0-9_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

async def handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ссылки на канал"""
    if not context.user_data.get('awaiting_channel_link'):
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    username = await extract_username_from_link(text)
    
    if not username:
        await update.message.reply_text(
            "❌ *Неверный формат ссылки!*\n\n"
            "Отправьте ссылку в одном из форматов:\n"
            "• https://t.me/username\n"
            "• t.me/username\n"
            "• @username",
            parse_mode='Markdown'
        )
        return
    
    try:
        chat = await context.bot.get_chat(f"@{username}")
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text(
                "❌ *Это не канал!*\n\n"
                "Пожалуйста, отправьте ссылку на КАНАЛ.",
                parse_mode='Markdown'
            )
            return
        
        channel_id = str(chat.id)
        channel_name = chat.title
        
        try:
            bot_member = await context.bot.get_chat_member(
                chat_id=channel_id, 
                user_id=context.bot.id
            )
            
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    f"⚠️ *Бот не является администратором канала!*\n\n"
                    f"📢 Канал: {channel_name}\n\n"
                    f"🔧 *Инструкция:*\n"
                    f"1. Зайдите в настройки канала\n"
                    f"2. Добавьте @{context.bot.username} как администратора\n"
                    f"3. После этого отправьте ссылку снова",
                    parse_mode='Markdown'
                )
                return
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {e}")
            await update.message.reply_text(
                f"⚠️ *Не удалось проверить права бота!*\n\n"
                f"Убедитесь, что бот добавлен в канал {channel_name}\n"
                f"как АДМИНИСТРАТОР и попробуйте снова.",
                parse_mode='Markdown'
            )
            return
        
        sub = bot.get_user_subscription(user_id)
        tariff = TARIFFS[sub.tariff]
        
        if len(sub.channels) >= tariff["channels"]:
            await update.message.reply_text(
                f"❌ *Лимит каналов достигнут!*\n\n"
                f"📊 Ваш тариф: {tariff['name']}\n"
                f"📢 Максимум каналов: {tariff['channels']}\n\n"
                f"💡 Используйте /tariffs для просмотра тарифов",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_channel_link'] = False
            return
        
        for ch in sub.channels:
            if ch.get('id') == channel_id:
                await update.message.reply_text(
                    "❌ *Этот канал уже добавлен!*\n\n"
                    f"📢 {channel_name}\n\n"
                    "Используйте /my_channels для просмотра",
                    parse_mode='Markdown'
                )
                context.user_data['awaiting_channel_link'] = False
                return
        
        sub.channels.append({
            "id": channel_id,
            "name": channel_name,
            "username": username
        })
        bot.save_data()
        
        await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *КАНАЛ УСПЕШНО ДОБАВЛЕН!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📢 *Название:* {channel_name}\n"
            f"🔗 *Ссылка:* t.me/{username}\n"
            f"🆔 *ID:* `{channel_id}`\n\n"
            f"📊 *Ваши каналы:* {len(sub.channels)}/{tariff['channels']}\n\n"
            f"🎯 *Что дальше?*\n"
            f"• Нажмите *«Настройка автопостинга»*\n"
            f"• Выберите тему из 30+ вариантов!\n"
            f"• Установите интервал публикации\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения канала: {e}")
        await update.message.reply_text(
            f"❌ *Не удалось найти канал!*\n\n"
            f"Проверьте:\n"
            f"• Существует ли канал t.me/{username}\n"
            f"• Публичная ли ссылка на канал\n"
            f"• Правильно ли вы ввели ссылку",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['awaiting_channel_link'] = False

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    text = "━━━━━━━━━━━━━━━━━━━━━\n"
    text += "🤖 *НАСТРОЙКА АВТОПОСТИНГА*\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not sub.channels:
        text += "❌ *У вас нет добавленных каналов!*\n\n"
        text += "Сначала добавьте канал через\n"
        text += "«📢 Добавить канал» в главном меню\n"
        await query.edit_message_text(text, parse_mode='Markdown')
        return
    
    keyboard = []
    for ch in sub.channels:
        ch_id = ch.get('id')
        ch_name = ch.get('name', 'Канал')
        is_configured = ch_id in sub.auto_posts
        status = "✅" if is_configured and sub.auto_posts[ch_id].is_active else "⚙️"
        button_text = f"{status} {ch_name[:30]}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"config_channel_{ch_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await query.edit_message_text(
        text + "\n👇 *Выберите канал для настройки:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def configure_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("config_channel_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    channel_name = "Канал"
    channel_username = ""
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            channel_name = ch.get('name', 'Канал')
            channel_username = ch.get('username', '')
            break
    
    config = sub.auto_posts.get(channel_id)
    
    text = f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"⚙️ *НАСТРОЙКА КАНАЛА*\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📢 *Канал:* {channel_name}\n"
    if channel_username:
        text += f"🔗 *Ссылка:* t.me/{channel_username}\n"
    text += f"\n"
    
    if config:
        theme = POSTING_THEMES.get(config.theme, {})
        size = POST_SIZES.get(config.size, {})
        interval = config.interval_seconds
        
        if interval < 60:
            interval_text = f"{interval} сек"
        elif interval < 3600:
            interval_text = f"{interval//60} мин"
        else:
            interval_text = f"{interval//3600} ч"
        
        text += f"🎨 *Тема:* {theme.get('emoji', '')} {theme.get('name', '-')}\n"
        text += f"📏 *Размер:* {size.get('name', '-')}\n"
        text += f"⏱ *Интервал:* {interval_text}\n"
        text += f"🔘 *Статус:* {'✅ АКТИВЕН' if config.is_active else '⏸ ОСТАНОВЛЕН'}\n\n"
    else:
        text += "⚠️ *Автопостинг не настроен*\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🎨 Выбрать тему (30+ тем)", callback_data=f"set_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"set_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Выбрать интервал", callback_data=f"set_interval_{channel_id}")],
    ]
    
    if config:
        if config.is_active:
            keyboard.append([InlineKeyboardButton("⏸ Остановить", callback_data=f"stop_auto_{channel_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Запустить", callback_data=f"start_auto_{channel_id}")])
        keyboard.append([InlineKeyboardButton("🗑 Удалить настройки", callback_data=f"delete_config_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к каналам", callback_data="auto_posting")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def set_channel_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("set_theme_", "")
    context.user_data['temp_channel_id'] = channel_id
    await query.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎨 *ВЫБОР ТЕМЫ*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *Доступно 30+ тем:*\n"
        "• 🤖 Новости AI\n"
        "• 📱 Telegram\n"
        "• 🎨 NFT\n"
        "• 🪙 Криптовалюты\n"
        "• 🌐 Web3\n"
        "• 💼 Бизнес\n"
        "• 🚀 Стартапы\n"
        "• И многие другие!\n\n"
        "👇 *Выберите тему ниже:*",
        parse_mode='Markdown',
        reply_markup=await get_themes_keyboard()
    )

async def set_channel_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("set_size_", "")
    context.user_data['temp_channel_id'] = channel_id
    keyboard = await get_sizes_keyboard()
    await query.edit_message_text(
        "📏 *Выберите размер постов:*\n\n"
        "Размер влияет на длину текста",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_channel_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("set_interval_", "")
    context.user_data['temp_channel_id'] = channel_id
    keyboard = await get_intervals_keyboard()
    await query.edit_message_text(
        "⏱ *Выберите интервал публикации:*\n\n"
        "Посты будут публиковаться автоматически\n"
        "с выбранным промежутком времени\n\n"
        "✨ *Минимальный интервал:* 10 секунд",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def handle_theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    theme = query.data.replace("theme_", "")
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка: канал не найден", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id,
            channel_name="",
            channel_username="",
            theme=theme,
            size="medium",
            interval_seconds=300
        )
    else:
        sub.auto_posts[channel_id].theme = theme
    
    bot.save_data()
    
    theme_config = POSTING_THEMES[theme]
    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *ТЕМА ВЫБРАНА!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{theme_config['emoji']} *{theme_config['name']}*\n"
        f"📂 Категория: {theme_config.get('category', 'Другое')}\n\n"
        f"📝 *Описание:* {theme_config['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Теперь выберите размер поста:",
        parse_mode='Markdown',
        reply_markup=await get_sizes_keyboard()
    )

async def handle_size_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    size = query.data.replace("size_", "")
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка: канал не найден", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id,
            channel_name="",
            channel_username="",
            theme="ai_news",
            size=size,
            interval_seconds=300
        )
    else:
        sub.auto_posts[channel_id].size = size
    
    bot.save_data()
    
    await query.edit_message_text(
        f"✅ *Размер выбран!*\n\n"
        f"{POST_SIZES[size]['emoji']} {POST_SIZES[size]['name']}\n"
        f"📏 Длина: ~{POST_SIZES[size]['chars']} символов\n\n"
        f"📊 Осталось выбрать интервал публикации!",
        parse_mode='Markdown',
        reply_markup=await get_intervals_keyboard()
    )

async def handle_interval_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "custom_interval":
        context.user_data['awaiting_custom_interval'] = True
        await query.edit_message_text(
            "⏱ *Введите свой интервал*\n\n"
            "Примеры:\n"
            "• `10` - 10 секунд\n"
            "• `60` - 1 минута\n"
            "• `300` - 5 минут\n"
            "• `3600` - 1 час\n\n"
            "Отправьте ЧИСЛО (в секундах):",
            parse_mode='Markdown'
        )
        return
    
    interval = int(data.replace("interval_", ""))
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка: канал не найден", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    if interval < tariff["interval_min"]:
        await query.edit_message_text(
            f"❌ *Минимальный интервал для вашего тарифа: {tariff['interval_min']} сек*\n\n"
            f"Выберите больший интервал",
            parse_mode='Markdown',
            reply_markup=await get_intervals_keyboard()
        )
        return
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id,
            channel_name="",
            channel_username="",
            theme="ai_news",
            size="medium",
            interval_seconds=interval
        )
    else:
        sub.auto_posts[channel_id].interval_seconds = interval
    
    sub.auto_posts[channel_id].is_active = True
    sub.auto_posts[channel_id].last_post = time.time()
    
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            sub.auto_posts[channel_id].channel_name = ch.get('name', '')
            sub.auto_posts[channel_id].channel_username = ch.get('username', '')
            break
    
    bot.save_data()
    await start_auto_posting(context, user_id, channel_id)
    
    if interval < 60:
        interval_text = f"{interval} сек"
    elif interval < 3600:
        interval_text = f"{interval//60} мин"
    else:
        interval_text = f"{interval//3600} ч"
    
    theme_config = POSTING_THEMES[sub.auto_posts[channel_id].theme]
    
    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 *АВТОПОСТИНГ НАСТРОЕН!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ *Параметры:*\n"
        f"🎨 Тема: {theme_config['emoji']} {theme_config['name']}\n"
        f"📏 Размер: {POST_SIZES[sub.auto_posts[channel_id].size]['name']}\n"
        f"⏱ Интервал: {interval_text}\n\n"
        f"🤖 Бот будет автоматически публиковать посты!\n"
        f"🔄 Статус: АКТИВЕН\n\n"
        f"📊 *30+ тем доступны!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )

async def start_auto_posting(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: str):
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        return
    
    config = sub.auto_posts[channel_id]
    if not config.is_active or config.job_running:
        return
    
    config.job_running = True
    
    async def post_loop():
        while config.is_active and channel_id in sub.auto_posts:
            try:
                current_time = time.time()
                time_since_last = current_time - config.last_post
                
                if time_since_last >= config.interval_seconds:
                    if sub.can_post():
                        success = await bot.format_and_send_post(
                            context, channel_id, config.theme, config.size, is_auto=True
                        )
                        if success:
                            config.last_post = current_time
                            sub.add_post()
                            bot.save_data()
                            logger.info(f"🔄 Автопостинг: канал {channel_id}")
                    else:
                        logger.warning(f"⚠️ Лимит постов для {user_id}")
                
                await asyncio.sleep(min(config.interval_seconds, 30))
                
            except Exception as e:
                logger.error(f"Ошибка автопостинга: {e}")
                await asyncio.sleep(60)
    
    task = asyncio.create_task(post_loop())
    bot.active_jobs[f"{user_id}_{channel_id}"] = task

async def start_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("start_auto_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        sub.auto_posts[channel_id].is_active = True
        bot.save_data()
        await start_auto_posting(context, user_id, channel_id)
        await query.edit_message_text("✅ *Автопостинг запущен!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Настройки не найдены*", parse_mode='Markdown')

async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("stop_auto_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        sub.auto_posts[channel_id].is_active = False
        bot.save_data()
        await query.edit_message_text("⏸ *Автопостинг остановлен*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Настройки не найдены*", parse_mode='Markdown')

async def delete_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("delete_config_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        job_key = f"{user_id}_{channel_id}"
        if job_key in bot.active_jobs:
            bot.active_jobs[job_key].cancel()
            del bot.active_jobs[job_key]
        
        del sub.auto_posts[channel_id]
        bot.save_data()
        await query.edit_message_text("🗑 *Настройки удалены!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Настройки не найдены*", parse_mode='Markdown')

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через «📢 Добавить канал»",
            parse_mode='Markdown'
        )
        return
    
    if not sub.can_post():
        await query.edit_message_text(
            f"⚠️ *Лимит постов на сегодня исчерпан!*\n\n"
            f"📊 Осталось: 0/{TARIFFS[sub.tariff]['posts_per_day']}",
            parse_mode='Markdown'
        )
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    await query.edit_message_text(
        f"🎲 *Генерация случайного поста...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[random_theme]['emoji']} {POSTING_THEMES[random_theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[random_size]['name']}\n\n"
        f"⏳ Генерирую уникальный контент через ИИ...",
        parse_mode='Markdown'
    )
    
    success = await bot.format_and_send_post(context, sub.channels[0]['id'], random_theme, random_size)
    
    if success:
        await query.edit_message_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"📊 Осталось постов сегодня: {sub.get_remaining_posts() - 1}\n"
            f"🎨 Всего доступно тем: {len(POSTING_THEMES)}",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ *Ошибка при публикации поста*", parse_mode='Markdown')

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    text = f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📡 *МОИ КАНАЛЫ*\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not sub.channels:
        text += "❌ *У вас нет добавленных каналов*\n\n"
        text += "Нажмите *«Добавить канал»* в главном меню\n"
    else:
        for i, ch in enumerate(sub.channels, 1):
            text += f"{i}. 📢 *{ch.get('name', 'Канал')}*\n"
            if ch.get('username'):
                text += f"   🔗 t.me/{ch.get('username')}\n"
            text += f"   🆔 `{ch.get('id', 'ID')}`\n"
            
            if ch.get('id') in sub.auto_posts:
                cfg = sub.auto_posts[ch['id']]
                theme = POSTING_THEMES.get(cfg.theme, {})
                size = POST_SIZES.get(cfg.size, {})
                interval = cfg.interval_seconds
                
                if interval < 60:
                    interval_text = f"{interval} сек"
                elif interval < 3600:
                    interval_text = f"{interval//60} мин"
                else:
                    interval_text = f"{interval//3600} ч"
                
                text += f"   🎨 Тема: {theme.get('emoji', '')} {theme.get('name', '-')}\n"
                text += f"   📏 Размер: {size.get('name', '-')}\n"
                text += f"   ⏱ Интервал: {interval_text}\n"
                text += f"   🔄 Статус: {'✅ АКТИВЕН' if cfg.is_active else '⏸ ОСТАНОВЛЕН'}\n"
            else:
                text += f"   ⚙️ *Автопостинг не настроен*\n"
            text += "\n"
    
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 Лимит каналов: {len(sub.channels)}/{tariff['channels']}\n"
    text += f"📝 Постов сегодня: {sub.posts_today}/{tariff['posts_per_day']}\n"
    text += f"🎨 Доступно тем: {len(POSTING_THEMES)}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━"
    
    keyboard = []
    for ch in sub.channels:
        keyboard.append([InlineKeyboardButton(
            f"⚙️ {ch.get('name', 'Канал')[:25]}",
            callback_data=f"config_channel_{ch['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await query.edit_message_text(
        text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    remaining = sub.get_remaining_posts()
    reset_time = 86400 - (time.time() - sub.last_reset)
    reset_hours = int(reset_time // 3600)
    reset_minutes = int((reset_time % 3600) // 60)
    
    text = f"""━━━━━━━━━━━━━━━━━━━━━
📊 *МОЯ СТАТИСТИКА*
━━━━━━━━━━━━━━━━━━━━━

👤 *Пользователь:* {query.from_user.first_name}
💎 *Тариф:* {tariff['color']} {tariff['name']}

━━━━━━━━━━━━━━━━━━━━━
📡 *КАНАЛЫ*
📢 Добавлено: {len(sub.channels)}/{tariff['channels']}

━━━━━━━━━━━━━━━━━━━━━
📝 *ПОСТЫ*
📊 Сегодня: {sub.posts_today}/{tariff['posts_per_day']}
⏳ Осталось: {remaining}
🔄 Сброс через: {reset_hours}ч {reset_minutes}мин

━━━━━━━━━━━━━━━━━━━━━
🤖 *АВТОПОСТИНГ*
⚙️ Активных: {len([c for c in sub.auto_posts.values() if c.is_active])}
⏱ Мин. интервал: {tariff['interval_min']} сек

━━━━━━━━━━━━━━━━━━━━━
🎨 *ТЕМЫ*
📚 Всего тем: {len(POSTING_THEMES)}
📂 Категорий: 15+

━━━━━━━━━━━━━━━━━━━━━
✨ *Все тарифы БЕСПЛАТНЫЕ!*
━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """━━━━━━━━━━━━━━━━━━━━━
💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*
━━━━━━━━━━━━━━━━━━━━━

🌟 *БАЗОВЫЙ* - 0₽
├ 📢 Каналов: 5
├ 📝 Постов/день: 100
├ ⏱ Мин. интервал: 10 сек
└ 🎨 Доступно тем: 30+

⭐ *СТАНДАРТ* - 0₽  
├ 📢 Каналов: 15
├ 📝 Постов/день: 500
├ ⏱ Мин. интервал: 5 сек
└ 🎨 Доступно тем: 30+

💎 *ПРОФЕССИОНАЛЬНЫЙ* - 0₽
├ 📢 Каналов: 50
├ 📝 Постов/день: 1500
├ ⏱ Мин. интервал: 3 сек
└ 🎨 Доступно тем: 30+

👑 *ПРЕМИУМ* - 0₽
├ 📢 Каналов: 200
├ 📝 Постов/день: 5000
├ ⏱ Мин. интервал: 1 сек
└ 🎨 Доступно тем: 30+

━━━━━━━━━━━━━━━━━━━━━
✨ *ВСЕ ФУНКЦИИ ДОСТУПНЫ!*
🎯 30+ уникальных тем для постов
━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """━━━━━━━━━━━━━━━━━━━━━
🆘 *ПОМОЩЬ И ИНСТРУКЦИЯ*
━━━━━━━━━━━━━━━━━━━━━

📌 *КАК ДОБАВИТЬ КАНАЛ:*

1️⃣ *Добавьте бота в канал*
   → Как АДМИНИСТРАТОРА!

2️⃣ *Нажмите «📢 Добавить канал»*

3️⃣ *Отправьте ССЫЛКУ на канал*
   → https://t.me/username
   → t.me/username  
   → @username

━━━━━━━━━━━━━━━━━━━━━
🎯 *НАСТРОЙКА АВТОПОСТИНГА:*

1. Нажмите «🤖 Настройка автопостинга»
2. Выберите канал
3. Выберите ТЕМУ из 30+
4. Выберите РАЗМЕР поста
5. Установите ИНТЕРВАЛ
6. Автопостинг запустится автоматически!

━━━━━━━━━━━━━━━━━━━━━
🎨 *ДОСТУПНЫЕ ТЕМЫ (30+):*

🤖 Новости AI
📱 Telegram  
🎨 NFT
🪙 Криптовалюты
🌐 Web3
💼 Бизнес
📈 Маркетинг
🚀 Стартапы
🔬 Наука
📚 Образование
🧠 Психология
💪 Мотивация
💊 Здоровье
🏋️ Фитнес
🍳 Кулинария
📡 Технологии
💻 Программирование
🎮 Игры
🎬 Кино
🎵 Музыка
⚽ Спорт
✈️ Путешествия
📷 Фотография
🎨 Дизайн
🚗 Авто
...и еще 10+ тем!

━━━━━━━━━━━━━━━━━━━━━
✨ *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*
━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_custom_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_custom_interval'):
        return
    
    try:
        interval = int(update.message.text.strip())
        if interval < 1:
            await update.message.reply_text("❌ Интервал должен быть больше 0 секунд")
            return
        
        channel_id = context.user_data.get('temp_channel_id')
        if not channel_id:
            await update.message.reply_text("❌ Ошибка: канал не найден")
            return
        
        user_id = update.effective_user.id
        sub = bot.get_user_subscription(user_id)
        
        tariff = TARIFFS[sub.tariff]
        if interval < tariff["interval_min"]:
            await update.message.reply_text(
                f"❌ Минимальный интервал для вашего тарифа: {tariff['interval_min']} сек\n\n"
                f"Установите больший интервал",
                parse_mode='Markdown'
            )
            return
        
        if channel_id not in sub.auto_posts:
            sub.auto_posts[channel_id] = AutoPostConfig(
                channel_id=channel_id,
                channel_name="",
                channel_username="",
                theme="ai_news",
                size="medium",
                interval_seconds=interval
            )
        else:
            sub.auto_posts[channel_id].interval_seconds = interval
        
        sub.auto_posts[channel_id].is_active = True
        sub.auto_posts[channel_id].last_post = time.time()
        
        bot.save_data()
        await start_auto_posting(context, user_id, channel_id)
        
        if interval < 60:
            interval_text = f"{interval} сек"
        elif interval < 3600:
            interval_text = f"{interval//60} мин"
        else:
            interval_text = f"{interval//3600} ч"
        
        await update.message.reply_text(
            f"✅ *Интервал установлен!*\n\n"
            f"⏱ Интервал: {interval_text}\n"
            f"🤖 Автопостинг АКТИВЕН\n"
            f"🎨 Доступно 30+ тем для постов!",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Введите ЧИСЛО (количество секунд)")
    
    context.user_data['awaiting_custom_interval'] = False
    context.user_data['temp_channel_id'] = None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        keyboard = await get_main_keyboard()
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "select_theme":
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🎨 *ВЫБОР ТЕМЫ*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📚 *Доступно {len(POSTING_THEMES)} тем!*\n\n"
            "👇 *Выберите тему ниже:*",
            parse_mode='Markdown',
            reply_markup=await get_themes_keyboard()
        )
    elif data == "themes_categories":
        await query.edit_message_text(
            "📂 *ВЫБОР ПО КАТЕГОРИЯМ*\n\n"
            "Выберите категорию:",
            parse_mode='Markdown',
            reply_markup=await get_categories_keyboard()
        )
    elif data == "back_to_themes":
        await query.edit_message_text(
            "🎨 *ВЫБОР ТЕМЫ*\n\n"
            f"📚 *Доступно {len(POSTING_THEMES)} тем!*\n\n"
            "👇 *Выберите тему:*",
            parse_mode='Markdown',
            reply_markup=await get_themes_keyboard()
        )
    elif data.startswith("category_"):
        category = data.replace("category_", "")
        await query.edit_message_text(
            f"📂 *Категория: {category}*\n\n"
            f"👇 *Выберите тему:*",
            parse_mode='Markdown',
            reply_markup=await get_themes_by_category_keyboard(category)
        )
    elif data == "select_size":
        await query.edit_message_text(
            "📏 *Выберите размер поста:*\n\n"
            "Размер влияет на длину текста",
            parse_mode='Markdown',
            reply_markup=await get_sizes_keyboard()
        )
    elif data == "random_post":
        await random_post(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "my_channels":
        await my_channels(update, context)
    elif data == "tariffs":
        await tariffs(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    elif data.startswith("theme_") and not data.startswith("themes_page_"):
        await handle_theme_selection(update, context)
    elif data.startswith("size_"):
        await handle_size_selection(update, context)
    elif data.startswith("interval_"):
        await handle_interval_selection(update, context)
    elif data == "custom_interval":
        await handle_interval_selection(update, context)
    elif data.startswith("config_channel_"):
        await configure_channel(update, context)
    elif data.startswith("set_theme_"):
        await set_channel_theme(update, context)
    elif data.startswith("set_size_"):
        await set_channel_size(update, context)
    elif data.startswith("set_interval_"):
        await set_channel_interval(update, context)
    elif data.startswith("start_auto_"):
        await start_auto(update, context)
    elif data.startswith("stop_auto_"):
        await stop_auto(update, context)
    elif data.startswith("delete_config_"):
        await delete_config(update, context)

# ==================== ЗАПУСК ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Callback обработчик
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_link))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info("💰 ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!")
    logger.info("⏱ Интервалы от 10 секунд!")
    logger.info("🔗 Добавление каналов только по ссылке!")
    logger.info("🎨 30+ уникальных тем для контента!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
