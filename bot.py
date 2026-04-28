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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# API GigaChat
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== ТЕМАТИКИ ПОСТОВ ====================
TOPICS = {
    "nft": {
        "name": "🎨 NFT & Цифровое искусство",
        "emoji": "🎨",
        "description": "NFT коллекции, новости рынка, тренды",
        "prompt": "Ты эксперт в NFT. Пиши интересные посты о NFT коллекциях, новостях рынка, новых проектах. Используй эмодзи, будь энергичным.",
        "hashtags": ["#NFT", #ЦифровоеИскусство", #КриптоИскусство"],
        "image_style": "digital art, nft, colorful, abstract"
    },
    "telegram": {
        "name": "📱 Telegram & Web3",
        "emoji": "📱",
        "description": "Telegram боты, каналы, технологии",
        "prompt": "Ты эксперт по Telegram. Пиши посты о Telegram ботах, каналах, функциях, новостях мессенджера.",
        "hashtags": ["#Telegram", #Web3", #TGbot"],
        "image_style": "telegram app interface, modern"
    },
    "crypto": {
        "name": "💰 Криптовалюты",
        "emoji": "💰",
        "description": "Криптовалюты, биткоин, трейдинг",
        "prompt": "Ты криптотрейдер. Пиши посты о криптовалютах, аналитике, трендах. Давай полезные советы.",
        "hashtags": ["#Криптовалюта", #Биткоин", #Трейдинг"],
        "image_style": "cryptocurrency, bitcoin, ethereum, futuristic"
    },
    "defi": {
        "name": "🏦 DeFi",
        "emoji": "🏦",
        "description": "Децентрализованные финансы",
        "prompt": "Ты эксперт DeFi. Рассказывай о децентрализованных финансах, стейкинге, фарминге.",
        "hashtags": ["#DeFi", #Стейкинг", #Фарминг"],
        "image_style": "defi finance, blockchain, decentralized"
    },
    "memes": {
        "name": "😂 Мемы & Криптоюмор",
        "emoji": "😂",
        "description": "Криптомемы и юмор",
        "prompt": "Ты криптоюморист. Пиши смешные посты о криптовалютах с юмором и мемами.",
        "hashtags": ["#Мемы", #Криптоюмор", #Шутки"],
        "image_style": "meme style, funny crypto art"
    },
    "analysis": {
        "name": "📊 Аналитика рынка",
        "emoji": "📊",
        "description": "Технический и фундаментальный анализ",
        "prompt": "Ты аналитик крипторынка. Делай технический анализ, давай прогнозы, анализируй графики.",
        "hashtags": ["#Аналитика", #Сигналы", #Прогноз"],
        "image_style": "candlestick chart, trading analysis"
    },
    "gaming": {
        "name": "🎮 GameFi & Metaverse",
        "emoji": "🎮",
        "description": "Игры, метаверсы, GameFi",
        "prompt": "Ты геймер и эксперт GameFi. Пиши о Play-to-Earn играх, метаверсах, игровой экономике.",
        "hashtags": ["#GameFi", #Метаверс", #P2E"],
        "image_style": "gamefi metaverse gaming art"
    },
    "security": {
        "name": "🔒 Безопасность",
        "emoji": "🔒",
        "description": "Безопасность в крипте",
        "prompt": "Ты специалист по безопасности. Рассказывай как защитить криптовалюту, безопасные практики.",
        "hashtags": ["#Безопасность", #ХолодныйКошелек", #2FA"],
        "image_style": "cybersecurity, encryption, secure"
    },
    "mining": {
        "name": "⛏️ Майнинг",
        "emoji": "⛏️",
        "description": "Майнинг и оборудование",
        "prompt": "Ты майнер. Пиши о майнинге, оборудовании, пулах, доходности.",
        "hashtags": ["#Майнинг", #ASIC", #GPU"],
        "image_style": "mining rig, cryptocurrency mining"
    },
    "airdrops": {
        "name": "🎁 Airdrops & Фарминг",
        "emoji": "🎁",
        "description": "Аирдропы и фарминг",
        "prompt": "Ты охотник за аирдропами. Рассказывай о новых аирдропах, фарминге, как заработать бесплатные токены.",
        "hashtags": ["#Airdrop", #Фарминг", #Giveaway"],
        "image_style": "gift boxes, crypto airdrop"
    },
    "nft_art": {
        "name": "🖼️ NFT Художники",
        "emoji": "🖼️",
        "description": "Профили NFT художников",
        "prompt": "Ты искусствовед NFT. Рассказывай о известных NFT художниках, их работах, стилях.",
        "hashtags": ["#NFTArt", #ЦифровойХудожник", #Искусство"],
        "image_style": "digital artwork, painting style"
    },
    "web3": {
        "name": "🌐 Web3 технологии",
        "emoji": "🌐",
        "description": "Web3, DApps, блокчейн",
        "prompt": "Ты разработчик Web3. Пиши посты о технологии блокчейн, DApps, смарт-контрактах.",
        "hashtags": ["#Web3", #DApps", #Блокчейн"],
        "image_style": "web3 decentralized internet"
    },
    "altcoins": {
        "name": "🪙 Альткоины",
        "emoji": "🪙",
        "description": "Альткоины и их анализ",
        "prompt": "Ты аналитик альткоинов. Рассказывай о перспективных альткоинах, их проектах и токеномике.",
        "hashtags": ["#Альткоины", #ТопПроекты", #Инвестиции"],
        "image_style": "altcoins, ethereum solana cardano"
    },
    "influencers": {
        "name": "⭐ Криптоинфлюенсеры",
        "emoji": "⭐",
        "description": "Новости от криптоблогеров",
        "prompt": "Ты криптоблогер. Делай дайджест новостей от известных криптоинфлюенсеров.",
        "hashtags": ["#Инфлюенсеры", #Криптоблогеры", #Новости"],
        "image_style": "social media influencer, crypto"
    },
    "regulation": {
        "name": "⚖️ Регулирование",
        "emoji": "⚖️",
        "description": "Законодательство и регулирование",
        "prompt": "Ты юрист по крипте. Пиши о законах, регулировании криптовалют в разных странах.",
        "hashtags": ["#Регулирование", #Закон", #Юристы"],
        "image_style": "law, regulation, legal documents"
    },
    "defi_protocols": {
        "name": "🏛️ DeFi протоколы",
        "emoji": "🏛️",
        "description": "Обзор DeFi протоколов",
        "prompt": "Ты исследователь DeFi. Делай обзоры DeFi протоколов, их механик и доходности.",
        "hashtags": ["#DeFi", #Протоколы", #Доходность"],
        "image_style": "defi protocols dashboard"
    },
    "trading_bots": {
        "name": "🤖 Торговые боты",
        "emoji": "🤖",
        "description": "Обзор торговых ботов",
        "prompt": "Ты трейдер с ботами. Рассказывай о торговых ботах, стратегиях, настройке.",
        "hashtags": ["#ТорговыеБоты", #Криптоботы", #Автотрейдинг"],
        "image_style": "trading bot, algorithmic trading"
    },
    "crypto_news": {
        "name": "📰 Новости крипты",
        "emoji": "📰",
        "description": "Свежие новости криптовалют",
        "prompt": "Ты журналист. Делай обзор главных новостей за день из мира криптовалют.",
        "hashtags": ["#Новости", #Криптоновости", #Дайджест"],
        "image_style": "crypto news headlines"
    },
    "education": {
        "name": "📚 Обучение крипте",
        "emoji": "📚",
        "description": "Обучение криптовалютам",
        "prompt": "Ты учитель по крипте. Объясняй термины, концепции, обучай новичков простым языком.",
        "hashtags": ["#Обучение", #КриптаДляНачинающих", #Термины"],
        "image_style": "education, learning crypto"
    },
    "predictions": {
        "name": "🔮 Прогнозы",
        "emoji": "🔮",
        "description": "Прогнозы цен и трендов",
        "prompt": "Ты аналитик. Делай прогнозы цен на криптовалюты, анализируй тренды и настроения рынка.",
        "hashtags": ["#Прогноз", #Аналитика", #Цены"],
        "image_style": "crystal ball, prediction chart"
    }
}

# ==================== РАЗМЕРЫ ТЕКСТА ====================
TEXT_SIZES = {
    "short": {"name": "📝 Короткий", "min": 150, "max": 300, "emoji": "📝"},
    "medium": {"name": "📄 Средний", "min": 300, "max": 600, "emoji": "📄"},
    "long": {"name": "📖 Длинный", "min": 600, "max": 1000, "emoji": "📖"},
    "detailed": {"name": "📚 Детальный", "min": 1000, "max": 1500, "emoji": "📚"}
}

# ==================== ТАРИФЫ ====================
class TariffType(Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

TARIFFS = {
    "free": {
        "name": "🎁 Бесплатный",
        "price": 0,
        "channels_limit": 1,
        "posts_per_day_limit": 5,
        "topics_limit": 3,
        "can_repost": False,
        "auto_posting": True,
        "interval_hours": 6,
        "features": ["1 канал", "5 постов в день", "3 темы", "Автопостинг каждые 6ч"]
    },
    "pro": {
        "name": "⭐ Pro",
        "price": 0,
        "channels_limit": 5,
        "posts_per_day_limit": 20,
        "topics_limit": 10,
        "can_repost": True,
        "auto_posting": True,
        "interval_hours": 3,
        "features": ["5 каналов", "20 постов в день", "10 тем", "Автопостинг 3ч", "Перепосты"]
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels_limit": 20,
        "posts_per_day_limit": 100,
        "topics_limit": 20,
        "can_repost": True,
        "auto_posting": True,
        "interval_hours": 1,
        "features": ["20 каналов", "100 постов в день", "20 тем", "Автопостинг 1ч", "Перепосты"]
    }
}

# ==================== БАЗА ДАННЫХ (в памяти) ====================
@dataclass
class Channel:
    channel_id: str
    channel_username: str
    channel_title: str
    topics: List[str] = field(default_factory=list)
    text_sizes: List[str] = field(default_factory=lambda: ["short", "medium", "long", "detailed"])
    auto_posting_enabled: bool = True
    repost_enabled: bool = False
    repost_sources: List[str] = field(default_factory=list)
    posts_today: int = 0
    last_posts: List[Dict] = field(default_factory=list)
    last_post_time: float = field(default_factory=time.time)
    schedule_intervals: List[int] = field(default_factory=lambda: [6])

@dataclass
class User:
    user_id: int
    username: str
    first_name: str
    tariff: str = "free"
    channels: Dict[str, Channel] = field(default_factory=dict)
    subscribed_at: float = field(default_factory=time.time)
    total_posts: int = 0
    total_channels: int = 0

class Database:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_scheduler_tasks = {}
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> User:
        if user_id not in self.users:
            self.users[user_id] = User(
                user_id=user_id, username=username, first_name=first_name
            )
        return self.users[user_id]
    
    def can_add_channel(self, user_id: int) -> Tuple[bool, str]:
        user = self.get_user(user_id)
        tariff = TARIFFS[user.tariff]
        current_channels = len(user.channels)
        if current_channels >= tariff["channels_limit"]:
            return False, f"Лимит каналов для тарифа {tariff['name']}: {tariff['channels_limit']}"
        return True, ""
    
    def can_post_today(self, user_id: int, channel_id: str) -> Tuple[bool, str]:
        user = self.get_user(user_id)
        tariff = TARIFFS[user.tariff]
        if channel_id not in user.channels:
            return False, "Канал не найден"
        
        channel = user.channels[channel_id]
        current_day = datetime.now().day
        if not hasattr(channel, 'posts_day_count'):
            channel.posts_day_count = 0
            channel.posts_day_date = current_day
        
        if channel.posts_day_date != current_day:
            channel.posts_day_count = 0
            channel.posts_day_date = current_day
        
        if channel.posts_day_count >= tariff["posts_per_day_limit"]:
            return False, f"Достигнут лимит постов в день ({tariff['posts_per_day_limit']})"
        
        return True, ""
    
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
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            return None
    
    async def generate_post(self, topic_key: str, text_size: str, context: str = "") -> Dict:
        """Генерация уникального поста с помощью GigaChat"""
        token = await self.get_api_token()
        if not token:
            return {"success": False, "error": "Не удалось получить токен API"}
        
        topic = TOPICS.get(topic_key, TOPICS["crypto"])
        size = TEXT_SIZES.get(text_size, TEXT_SIZES["medium"])
        
        # Генерация текста
        prompt = f"""{topic['prompt']}

Напиши пост по теме {topic['name']}.

{"Дополнительный контекст: " + context if context else ""}

Требования к посту:
- Длина: от {size['min']} до {size['max']} символов
- Используй эмодзи (3-5 штук)
- Будь информативным и интересным
- Добавь хэштеги: {" ".join(topic['hashtags'])} и 2-3 своих
- Будь оригинальным, не повторяйся
- Пиши в разговорном стиле

Напиши только текст поста без лишних комментариев."""
        
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
                        "max_tokens": 2000
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            text = data["choices"][0]["message"]["content"]
                            
                            # Генерация уникального ID поста
                            post_id = f"{topic_key}_{int(time.time())}_{random.randint(1000, 9999)}"
                            
                            return {
                                "success": True,
                                "text": text,
                                "topic": topic_key,
                                "topic_name": topic['name'],
                                "size": text_size,
                                "hashtags": topic['hashtags'],
                                "post_id": post_id,
                                "timestamp": time.time()
                            }
                        else:
                            return {"success": False, "error": "Пустой ответ от AI"}
                    else:
                        return {"success": False, "error": f"Ошибка API: {response.status}"}
        except Exception as e:
            logger.error(f"Ошибка генерации поста: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_image_prompt(self, topic_key: str, post_text: str) -> str:
        """Генерация промпта для картинки на основе поста"""
        topic = TOPICS.get(topic_key, TOPICS["crypto"])
        
        prompt = f"""На основе этого поста создай промпт для генерации изображения.

Пост: {post_text[:500]}

Стиль изображения: {topic['image_style']}

Требования к промпту:
- На английском языке
- Детальное описание
- Добавь про стиль: vibrant colors, high quality, detailed
- Добавь про размер: 16:9 aspect ratio

Только промпт, без лишних слов:"""
        
        token = await self.get_api_token()
        if not token:
            return f"{topic['image_style']}, random style, vibrant colors"
        
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
                        "temperature": 0.8,
                        "max_tokens": 500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                    return f"{topic['image_style']}, random generation, vibrant colors"
        except:
            return f"{topic['image_style']}, random style"

db = Database()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("📋 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🎭 Выбрать темы", callback_data="topics")],
        [InlineKeyboardButton("📏 Размер текста", callback_data="text_size")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("⭐ Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🔴 Пост сейчас", callback_data="post_now")],
        [InlineKeyboardButton("🔄 Перепост", callback_data="repost")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(selected_topics: List[str] = None):
    keyboard = []
    row = []
    for key, topic in TOPICS.items():
        is_selected = selected_topics and key in selected_topics
        button_text = f"{'✅ ' if is_selected else ''}{topic['emoji']} {topic['name']}"
        row.append(InlineKeyboardButton(button_text[:40], callback_data=f"topic_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="topics_done")])
    return InlineKeyboardMarkup(keyboard)

async def get_text_size_keyboard(current_sizes: List[str] = None):
    keyboard = []
    for size_key, size in TEXT_SIZES.items():
        is_selected = current_sizes and size_key in current_sizes
        button_text = f"{'✅ ' if is_selected else ''}{size['emoji']} {size['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"size_{size_key}")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="size_done")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user: User):
    keyboard = []
    for channel_id, channel in user.channels.items():
        keyboard.append([InlineKeyboardButton(
            f"{channel.channel_title[:30]}", 
            callback_data=f"channel_{channel_id}"
        )])
    return InlineKeyboardMarkup(keyboard)

async def get_channel_settings_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("🎭 Изменить темы", callback_data=f"ch_topics_{channel_id}")],
        [InlineKeyboardButton("📏 Изменить размер", callback_data=f"ch_size_{channel_id}")],
        [InlineKeyboardButton("🕐 Интервал постинга", callback_data=f"ch_interval_{channel_id}")],
        [InlineKeyboardButton("🛑 Отключить канал", callback_data=f"ch_disable_{channel_id}")],
        [InlineKeyboardButton("🗑 Удалить канал", callback_data=f"ch_delete_{channel_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="my_channels")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        button_text = f"{tariff['name']} - {tariff['price']}₽"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tariff_{tariff_key}")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard():
    keyboard = [
        [InlineKeyboardButton("1 час", callback_data="interval_1")],
        [InlineKeyboardButton("3 часа", callback_data="interval_3")],
        [InlineKeyboardButton("6 часов", callback_data="interval_6")],
        [InlineKeyboardButton("12 часов", callback_data="interval_12")],
        [InlineKeyboardButton("24 часа", callback_data="interval_24")],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== РАСПИСАНИЕ ПОСТОВ ====================
async def scheduled_post_worker():
    """Фоновая задача для автопостинга"""
    while True:
        try:
            current_time = time.time()
            
            for user_id, user in db.users.items():
                tariff = TARIFFS[user.tariff]
                
                for channel_id, channel in user.channels.items():
                    if not channel.auto_posting_enabled:
                        continue
                    
                    # Проверяем интервал
                    interval_seconds = channel.schedule_intervals[0] * 3600 if channel.schedule_intervals else 6 * 3600
                    time_since_last = current_time - channel.last_post_time
                    
                    if time_since_last >= interval_seconds and channel.posts_today < tariff["posts_per_day_limit"]:
                        await post_to_channel(user_id, channel_id, is_auto=True)
                        
            await asyncio.sleep(60)  # Проверяем каждую минуту
            
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(60)

async def post_to_channel(user_id: int, channel_id: str, is_auto: bool = True):
    """Отправка поста в канал"""
    user = db.get_user(user_id)
    if channel_id not in user.channels:
        return False
    
    channel = user.channels[channel_id]
    tariff = TARIFFS[user.tariff]
    
    # Проверка лимитов
    current_day = datetime.now().day
    if not hasattr(channel, 'posts_day_count'):
        channel.posts_day_count = 0
        channel.posts_day_date = current_day
    
    if channel.posts_day_date != current_day:
        channel.posts_day_count = 0
        channel.posts_day_date = current_day
    
    if channel.posts_day_count >= tariff["posts_per_day_limit"]:
        return False
    
    # Выбираем тему
    if not channel.topics:
        channel.topics = list(TOPICS.keys())[:tariff["topics_limit"]]
    
    topic_key = random.choice(channel.topics)
    text_size = random.choice(channel.text_sizes) if channel.text_sizes else "medium"
    
    # Генерируем пост
    post = await db.generate_post(topic_key, text_size)
    
    if not post["success"]:
        logger.error(f"Ошибка генерации поста: {post.get('error')}")
        return False
    
    # Генерируем промпт для картинки
    image_prompt = await db.generate_image_prompt(topic_key, post["text"])
    
    # Отправляем в канал
    try:
        bot = application.bot
        
        # Отправляем текст
        final_text = f"{post['text']}\n\n{post['topic_name']} | #{channel_id}"
        
        await bot.send_message(
            chat_id=channel_id,
            text=final_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        
        # Обновляем статистику
        channel.posts_today += 1
        channel.posts_day_count += 1
        channel.last_post_time = time.time()
        channel.last_posts.append({
            "topic": topic_key,
            "size": text_size,
            "time": time.time(),
            "post_id": post["post_id"]
        })
        
        if len(channel.last_posts) > 50:
            channel.last_posts = channel.last_posts[-50:]
        
        user.total_posts += 1
        
        logger.info(f"Пост отправлен в канал {channel_id}, тема: {topic_key}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки в канал: {e}")
        return False

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"🤖 *Привет, {user.first_name}!*\n\n"
        f"Это *AI Постинг Бот* для автоматического постинга в Telegram каналы\n\n"
        f"✨ *Возможности:*\n"
        f"• 📝 Автоматический постинг в каналы\n"
        f"• 🎨 20 разных тем с эмодзи\n"
        f"• 📏 4 размера текста\n"
        f"• 🖼️ Уникальные посты через GigaChat AI\n"
        f"• 🔄 Перепосты из других каналов\n"
        f"• ⭐ Бесплатные тарифы\n\n"
        f"💡 *Как начать:*\n"
        f"1. Добавь бота в свой канал как администратора\n"
        f"2. Нажми /menu и выбери 'Добавить канал'\n"
        f"3. Настрой темы и размер текста\n"
        f"4. Жди автоматических постов!\n\n"
        f"📋 *Команды:*\n"
        f"/start - Главное меню\n"
        f"/menu - Открыть меню\n"
        f"/help - Помощь"
    )
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = await get_main_keyboard()
    await update.message.reply_text(
        "🎯 *Главное меню*\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 *Помощь*\n\n"
        "*Как добавить канал:*\n"
        "1. Добавьте бота в канал\n"
        "2. Выдайте права администратора\n"
        "3. Используйте /menu → Добавить канал\n"
        "4. Укажите ID канала (например @channel)\n\n"
        
        "*Настройки канала:*\n"
        "• Выберите темы для постов\n"
        "• Выберите размер текста\n"
        "• Настройте интервал постинга\n\n"
        
        "*Тарифы:*\n"
        "🎁 Бесплатный - 1 канал, 5 постов/день\n"
        "⭐ Pro - 5 каналов, 20 постов/день\n"
        "👑 Премиум - 20 каналов, 100 постов/день\n\n"
        
        "*Темы:*\n"
        "NFT, Криптовалюты, DeFi, Мемы, Аналитика, GameFi,\n"
        "Безопасность, Майнинг, Airdrops, Web3 и другие\n\n"
        
        f"📞 Поддержка: @support"
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db_user = db.get_user(user.id, user.username or "", user.first_name or "")
    data = query.data
    
    # Добавление канала
    if data == "add_channel":
        context.user_data['adding_channel'] = True
        await query.edit_message_text(
            "📢 *Добавление канала*\n\n"
            "Отправьте ID вашего канала одним из форматов:\n"
            "• `@username` (например @my_channel)\n"
            "• `-100123456789` (числовой ID)\n\n"
            "⚠️ Бот должен быть администратором канала!\n\n"
            "❌ Отмена: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Мои каналы
    elif data == "my_channels":
        if not db_user.channels:
            await query.edit_message_text(
                "❌ *У вас нет добавленных каналов*\n\n"
                "Используйте '➕ Добавить канал' в главном меню",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = "📋 *Ваши каналы:*\n\n"
        for channel_id, channel in db_user.channels.items():
            text += f"📢 {channel.channel_title}\n"
            text += f"   ID: `{channel_id}`\n"
            text += f"   Тем: {len(channel.topics)} | Постов: {channel.posts_today}\n\n"
        
        keyboard = await get_channels_keyboard(db_user)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    
    # Темы
    elif data == "topics":
        selected = None
        if db_user.channels:
            first_channel = list(db_user.channels.values())[0]
            selected = first_channel.topics
        
        keyboard = await get_topics_keyboard(selected)
        await query.edit_message_text(
            "🎭 *Выберите темы для постов*\n\n"
            "✅ - тема выбрана\n"
            "Нажмите 'Готово' когда закончите",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Размер текста
    elif data == "text_size":
        selected = None
        if db_user.channels:
            first_channel = list(db_user.channels.values())[0]
            selected = first_channel.text_sizes
        
        keyboard = await get_text_size_keyboard(selected)
        await query.edit_message_text(
            "📏 *Выберите размер текста постов*\n\n"
            "✅ - размер выбран\n"
            "Можно выбрать несколько",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Настройки
    elif data == "settings":
        if not db_user.channels:
            await query.edit_message_text(
                "❌ *Нет каналов для настройки*\n\n"
                "Сначала добавьте канал",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = await get_channels_keyboard(db_user)
        await query.edit_message_text(
            "⚙️ *Выберите канал для настройки:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Тарифы
    elif data == "tariffs":
        text = "⭐ *Тарифы*\n\n"
        for key, tariff in TARIFFS.items():
            text += f"**{tariff['name']}** - {tariff['price']}₽\n"
            text += f"📢 Каналов: {tariff['channels_limit']}\n"
            text += f"📝 Постов в день: {tariff['posts_per_day_limit']}\n"
            text += f"🎨 Тем: {tariff['topics_limit']}\n"
            text += f"⏰ Интервал: {tariff['interval_hours']}ч\n"
            if tariff['can_repost']:
                text += "🔄 Есть перепосты\n"
            text += "\n"
        
        text += f"\n💡 Ваш тариф: {TARIFFS[db_user.tariff]['name']}\n"
        text += f"💳 Баланс: 0 ₽ (все тарифы бесплатные)"
        
        keyboard = await get_tariffs_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    
    # Отправка поста сейчас
    elif data == "post_now":
        if not db_user.channels:
            await query.edit_message_text(
                "❌ *Нет каналов для постинга*\n\n"
                "Сначала добавьте канал",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        tariff = TARIFFS[db_user.tariff]
        text = "🔴 *Отправка поста сейчас*\n\nВыберите канал:\n\n"
        
        keyboard = []
        for channel_id, channel in db_user.channels.items():
            can_post, msg = db.can_post_today(user.id, channel_id)
            status = "✅" if can_post else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status} {channel.channel_title}",
                callback_data=f"post_now_{channel_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Перепост
    elif data == "repost":
        tariff = TARIFFS[db_user.tariff]
        if not tariff['can_repost']:
            await query.edit_message_text(
                "❌ *Перепосты недоступны на вашем тарифе*\n\n"
                "Обновитесь до тарифа Pro или Премиум",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not db_user.channels:
            await query.edit_message_text(
                "❌ *Нет каналов для перепоста*\n\n"
                "Сначала добавьте канал",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = []
        for channel_id in db_user.channels:
            keyboard.append([InlineKeyboardButton(
                f"📢 Канал", callback_data=f"repost_setup_{channel_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(
            "🔄 *Настройка перепостов*\n\n"
            "Выберите канал, в который будут приходить перепосты\n"
            "Затем отправьте ссылку на источник",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Помощь
    elif data == "help":
        help_text = (
            "🤖 *Помощь*\n\n"
            "*Быстрый старт:*\n"
            "1. Добавьте бота в канал как админа\n"
            "2. Используйте /menu → Добавить канал\n"
            "3. Настройте темы и размер текста\n\n"
            
            "*Команды:*\n"
            "/start - Главное меню\n"
            "/menu - Открыть меню\n"
            "/help - Помощь\n"
            "/cancel - Отменить действие\n\n"
            
            "*Поддержка:* @support"
        )
        await query.edit_message_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    # Обработка выбора канала
    elif data.startswith("channel_"):
        channel_id = data.replace("channel_", "")
        if channel_id in db_user.channels:
            keyboard = await get_channel_settings_keyboard(channel_id)
            channel = db_user.channels[channel_id]
            await query.edit_message_text(
                f"⚙️ *Настройки канала*\n\n"
                f"📢 {channel.channel_title}\n"
                f"🎭 Тем: {len(channel.topics)}\n"
                f"📏 Размеры: {', '.join(channel.text_sizes)}\n"
                f"📊 Постов сегодня: {channel.posts_today}\n"
                f"🔄 Перепосты: {'✅' if channel.repost_enabled else '❌'}\n\n"
                f"Выберите действие:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    
    # Интервал постинга
    elif data.startswith("ch_interval_"):
        channel_id = data.replace("ch_interval_", "")
        context.user_data['interval_channel'] = channel_id
        keyboard = await get_intervals_keyboard()
        await query.edit_message_text(
            "🕐 *Выберите интервал постинга*\n\n"
            "Как часто публиковать посты?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    elif data.startswith("interval_"):
        hours = int(data.replace("interval_", ""))
        channel_id = context.user_data.get('interval_channel')
        if channel_id and channel_id in db_user.channels:
            db_user.channels[channel_id].schedule_intervals = [hours]
            await query.edit_message_text(
                f"✅ *Интервал постинга установлен*\n\n"
                f"Посты будут публиковаться каждые {hours} час(а/ов)",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Удаление канала
    elif data.startswith("ch_delete_"):
        channel_id = data.replace("ch_delete_", "")
        if channel_id in db_user.channels:
            channel_title = db_user.channels[channel_id].channel_title
            del db_user.channels[channel_id]
            await query.edit_message_text(
                f"🗑 *Канал '{channel_title}' удален*",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Отключение канала
    elif data.startswith("ch_disable_"):
        channel_id = data.replace("ch_disable_", "")
        if channel_id in db_user.channels:
            db_user.channels[channel_id].auto_posting_enabled = False
            await query.edit_message_text(
                f"⚠️ *Канал отключен*\n\n"
                f"Автопостинг остановлен. Включите в настройках.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Обработка тем для канала
    elif data.startswith("ch_topics_"):
        channel_id = data.replace("ch_topics_", "")
        context.user_data['topics_channel'] = channel_id
        channel = db_user.channels[channel_id]
        keyboard = await get_topics_keyboard(channel.topics)
        await query.edit_message_text(
            f"🎭 *Выберите темы для канала*\n\n"
            f"Канал: {channel.channel_title}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Обработка размера для канала
    elif data.startswith("ch_size_"):
        channel_id = data.replace("ch_size_", "")
        context.user_data['size_channel'] = channel_id
        channel = db_user.channels[channel_id]
        keyboard = await get_text_size_keyboard(channel.text_sizes)
        await query.edit_message_text(
            f"📏 *Выберите размер текста*\n\n"
            f"Канал: {channel.channel_title}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Выбор темы
    elif data.startswith("topic_"):
        topic_key = data.replace("topic_", "")
        channel_id = context.user_data.get('topics_channel')
        
        if channel_id and channel_id in db_user.channels:
            channel = db_user.channels[channel_id]
            if topic_key in channel.topics:
                channel.topics.remove(topic_key)
            else:
                if len(channel.topics) < TARIFFS[db_user.tariff]['topics_limit']:
                    channel.topics.append(topic_key)
            
            keyboard = await get_topics_keyboard(channel.topics)
            await query.edit_message_text(
                f"🎭 *Выберите темы*\n\n"
                f"Канал: {channel.channel_title}\n"
                f"Выбрано: {len(channel.topics)}/{TARIFFS[db_user.tariff]['topics_limit']}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    
    # Выбор размера
    elif data.startswith("size_"):
        size_key = data.replace("size_", "")
        channel_id = context.user_data.get('size_channel')
        
        if channel_id and channel_id in db_user.channels:
            channel = db_user.channels[channel_id]
            if size_key in channel.text_sizes:
                channel.text_sizes.remove(size_key)
            else:
                channel.text_sizes.append(size_key)
            
            keyboard = await get_text_size_keyboard(channel.text_sizes)
            await query.edit_message_text(
                f"📏 *Выберите размер текста*\n\n"
                f"Канал: {channel.channel_title}\n"
                f"Выбрано: {len(channel.text_sizes)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    
    # Топики готово
    elif data == "topics_done":
        await query.edit_message_text(
            "✅ *Темы сохранены*\n\n"
            "Посты будут генерироваться по выбранным темам",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Размер готово
    elif data == "size_done":
        await query.edit_message_text(
            "✅ *Размеры сохранены*\n\n"
            "Размер текста будет случайным из выбранных",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Пост сейчас в канал
    elif data.startswith("post_now_"):
        channel_id = data.replace("post_now_", "")
        can_post, msg = db.can_post_today(user.id, channel_id)
        
        if not can_post:
            await query.edit_message_text(f"❌ {msg}", parse_mode=ParseMode.MARKDOWN)
            return
        
        await query.edit_message_text(
            "⏳ *Генерация поста...*\n\n"
            "Пожалуйста, подождите, это может занять до 30 секунд",
            parse_mode=ParseMode.MARKDOWN
        )
        
        success = await post_to_channel(user.id, channel_id, is_auto=False)
        
        if success:
            await query.edit_message_text(
                "✅ *Пост успешно опубликован!*",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                "❌ *Ошибка публикации*\n\n"
                "Проверьте права бота в канале и попробуйте снова",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Перепост настройка
    elif data.startswith("repost_setup_"):
        channel_id = data.replace("repost_setup_", "")
        context.user_data['repost_channel'] = channel_id
        await query.edit_message_text(
            "🔄 *Настройка перепостов*\n\n"
            "Отправьте ссылку на канал или сообщение, откуда хотите делать репосты\n\n"
            "Форматы:\n"
            "• @channel\n"
            "• https://t.me/channel/123\n\n"
            "❌ Отмена: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Главное меню
    elif data == "main":
        keyboard = await get_main_keyboard()
        await query.edit_message_text(
            "🎯 *Главное меню*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # Выбор тарифа
    elif data.startswith("tariff_"):
        tariff_key = data.replace("tariff_", "")
        if tariff_key in TARIFFS:
            db_user.tariff = tariff_key
            await query.edit_message_text(
                f"✅ *Тариф изменен на {TARIFFS[tariff_key]['name']}*\n\n"
                f"Новые лимиты:\n"
                f"📢 Каналов: {TARIFFS[tariff_key]['channels_limit']}\n"
                f"📝 Постов: {TARIFFS[tariff_key]['posts_per_day_limit']} в день\n"
                f"🎨 Тем: {TARIFFS[tariff_key]['topics_limit']}\n\n"
                f"💳 Стоимость: {TARIFFS[tariff_key]['price']} ₽\n"
                f"(все тарифы бесплатные)",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    text = update.message.text
    
    # Добавление канала
    if context.user_data.get('adding_channel'):
        channel_id = text.strip()
        
        # Поддержка числовых ID и username
        if channel_id.isdigit():
            channel_id = f"-100{channel_id}" if not channel_id.startswith('-') else channel_id
        
        # Валидация
        if channel_id.startswith('@') or channel_id.startswith('-') or channel_id.startswith('-100'):
            try:
                # Проверяем права бота в канале
                chat = await context.bot.get_chat(chat_id=channel_id)
                channel_title = chat.title or channel_id
                
                db_user = db.get_user(user.id)
                
                # Проверка лимитов
                can_add, msg = db.can_add_channel(user.id)
                if not can_add:
                    await update.message.reply_text(f"❌ {msg}")
                    context.user_data['adding_channel'] = False
                    return
                
                # Добавляем канал
                channel = Channel(
                    channel_id=channel_id,
                    channel_username=channel_id.replace('@', ''),
                    channel_title=channel_title
                )
                
                tariff = TARIFFS[db_user.tariff]
                channel.topics = list(TOPICS.keys())[:tariff["topics_limit"]]
                
                db_user.channels[channel_id] = channel
                db_user.total_channels += 1
                
                await update.message.reply_text(
                    f"✅ *Канал добавлен!*\n\n"
                    f"📢 {channel_title}\n"
                    f"🆔 ID: `{channel_id}`\n\n"
                    f"🎭 Автоматически выбрано {len(channel.topics)} тем\n"
                    f"📏 Размер текста: короткий, средний, длинный\n"
                    f"🕐 Интервал: каждые 6 часов\n\n"
                    f"⚙️ Настройте канал через /menu",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                context.user_data['adding_channel'] = False
                
            except Exception as e:
                logger.error(f"Ошибка добавления канала: {e}")
                await update.message.reply_text(
                    "❌ *Ошибка добавления канала*\n\n"
                    "Проверьте:\n"
                    "• Бот добавлен в канал как администратор\n"
                    "• ID канала правильный\n"
                    "• Канал существует",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(
                "❌ *Неверный формат*\n\n"
                "Используйте:\n"
                "• `@username`\n"
                "• `-100123456789`\n\n"
                "Отмена: /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Перепост
    if context.user_data.get('repost_channel'):
        channel_id = context.user_data['repost_channel']
        source = text.strip()
        
        db_user = db.get_user(user.id)
        
        if channel_id in db_user.channels:
            channel = db_user.channels[channel_id]
            channel.repost_enabled = True
            
            if source not in channel.repost_sources:
                channel.repost_sources.append(source)
            
            await update.message.reply_text(
                f"✅ *Источник для перепостов добавлен*\n\n"
                f"📢 Канал: {channel.channel_title}\n"
                f"🔄 Источник: {source}\n\n"
                f"Бот будет автоматически пересылать новые посты",
                parse_mode=ParseMode.MARKDOWN
            )
        
        context.user_data['repost_channel'] = None
        return
    
    # Обычный ответ
    await update.message.reply_text(
        "🤖 *Используйте меню для управления ботом*\n\n"
        "Команды:\n"
        "/start - Главное меню\n"
        "/menu - Открыть меню\n"
        "/help - Помощь",
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ *Действие отменено*",
        parse_mode=ParseMode.MARKDOWN
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ *Произошла ошибка. Попробуйте позже.*",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== ЗАПУСК ====================
application = None

def main():
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    # Запуск фоновых задач
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(scheduled_post_worker())
    
    logger.info("🚀 Бот для постинга запущен")
    logger.info(f"🎭 Доступно тем: {len(TOPICS)}")
    logger.info("⭐ Все тарифы бесплатные")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
