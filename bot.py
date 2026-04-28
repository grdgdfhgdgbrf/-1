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
from collections import defaultdict

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

# ==================== API НАСТРОЙКИ ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== ТАРИФЫ ====================
class Tariff(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    VIP = "vip"

TARIFFS_CONFIG = {
    Tariff.FREE: {
        "name": "🌟 Бесплатный",
        "price": 0,
        "max_channels": 1,
        "posts_per_day": 5,
        "can_repost": False,
        "ai_generation": True,
        "max_image_generation": 0,
        "priority": 0
    },
    Tariff.BASIC: {
        "name": "💎 Базовый",
        "price": 0,  # Бесплатно для демо
        "max_channels": 3,
        "posts_per_day": 20,
        "can_repost": True,
        "ai_generation": True,
        "max_image_generation": 5,
        "priority": 1
    },
    Tariff.PRO: {
        "name": "🚀 PRO",
        "price": 0,  # Бесплатно для демо
        "max_channels": 10,
        "posts_per_day": 100,
        "can_repost": True,
        "ai_generation": True,
        "max_image_generation": 50,
        "priority": 2
    },
    Tariff.VIP: {
        "name": "👑 VIP",
        "price": 0,  # Бесплатно для демо
        "max_channels": 50,
        "posts_per_day": 500,
        "can_repost": True,
        "ai_generation": True,
        "max_image_generation": 200,
        "priority": 3
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТОВ (20 ТЕМ) ====================
TOPICS_CONFIG = {
    "crypto": {
        "name": "₿ Криптовалюты",
        "emoji": "₿",
        "description": "Новости крипторынка, биткоин, альткоины",
        "hashtags": ["криптовалюта", "биткоин", "блокчейн"],
        "system_prompt": "Ты криптоэксперт. Пиши информативные посты о криптовалютах, анализируй рынок. Используй эмодзи.",
        "image_probability": 0.6,
        "text_length": "normal"  # short, normal, long
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "description": "Новости NFT коллекций, маркетплейсы",
        "hashtags": ["nft", "цифровоеискусство", "web3"],
        "system_prompt": "Ты эксперт по NFT. Рассказывай о новых коллекциях, трендах, маркетплейсах. Будь креативным.",
        "image_probability": 0.8,
        "text_length": "short"
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram, функции, боты",
        "hashtags": ["telegram", "мессенджер", "новости"],
        "system_prompt": "Ты блогер о Telegram. Рассказывай о новых функциях, ботах, каналах, обновлениях. Будь полезным.",
        "image_probability": 0.5,
        "text_length": "normal"
    },
    "ai": {
        "name": "🤖 Искусственный интеллект",
        "emoji": "🤖",
        "description": "Новости AI, нейросети, технологии",
        "hashtags": ["ии", "нейросети", "технологии"],
        "system_prompt": "Ты эксперт по ИИ. Рассказывай о новых нейросетях, технологиях, инструментах. Будь технически точным.",
        "image_probability": 0.4,
        "text_length": "long"
    },
    "web3": {
        "name": "🌐 Web3",
        "emoji": "🌐",
        "description": "Децентрализация, блокчейн, метавселенные",
        "hashtags": ["web3", "децентрализация", "метавселенная"],
        "system_prompt": "Ты специалист по Web3. Рассказывай о децентрализации, блокчейн-приложениях, DAO, метавселенных.",
        "image_probability": 0.7,
        "text_length": "normal"
    },
    "defi": {
        "name": "💰 DeFi",
        "emoji": "💰",
        "description": "Децентрализованные финансы",
        "hashtags": ["defi", "децентрализация", "финансы"],
        "system_prompt": "Ты эксперт DeFi. Рассказывай о децентрализованных финансах, стейкинге, фермерстве, протоколах.",
        "image_probability": 0.6,
        "text_length": "long"
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровая индустрия, новинки, обзоры",
        "hashtags": ["игры", "гейминг", "новинки"],
        "system_prompt": "Ты игровой блогер. Рассказывай о новых играх, обновлениях, прохождениях. Используй геймерский сленг.",
        "image_probability": 0.9,
        "text_length": "short"
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Киноновинки, сериалы, трейлеры",
        "hashtags": ["кино", "сериалы", "трейлеры"],
        "system_prompt": "Ты кинокритик. Рассказывай о новых фильмах и сериалах, давай обзоры, рекомендации.",
        "image_probability": 0.7,
        "text_length": "normal"
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новинки, артисты, альбомы",
        "hashtags": ["музыка", "альбомы", "артисты"],
        "system_prompt": "Ты музыкальный блогер. Рассказывай о новых треках, альбомах, концертах. Делитесь настроением.",
        "image_probability": 0.6,
        "text_length": "short"
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости, события, результаты",
        "hashtags": ["спорт", "футбол", "новости"],
        "system_prompt": "Ты спортивный комментатор. Рассказывай о спортивных событиях, результатах, трансферах.",
        "image_probability": 0.5,
        "text_length": "normal"
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес новости, стартапы, инвестиции",
        "hashtags": ["бизнес", "стартапы", "инвестиции"],
        "system_prompt": "Ты бизнес-аналитик. Рассказывай о новых бизнес-моделях, стартапах, инвестиционных трендах.",
        "image_probability": 0.4,
        "text_length": "long"
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия, исследования, технологии",
        "hashtags": ["наука", "открытия", "исследования"],
        "system_prompt": "Ты ученый-популяризатор. Рассказывай о новых научных открытиях, исследованиях, технологиях.",
        "image_probability": 0.5,
        "text_length": "long"
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Туризм, страны, места, советы",
        "hashtags": ["путешествия", "туризм", "страны"],
        "system_prompt": "Ты тревел-блогер. Рассказывай о красивых местах, странах, давай советы путешественникам.",
        "image_probability": 0.9,
        "text_length": "short"
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Рецепты, кулинарные советы, рестораны",
        "hashtags": ["кулинария", "рецепты", "еда"],
        "system_prompt": "Ты шеф-повар. Делитесь рецептами, кулинарными советами, рассказывай о ресторанах.",
        "image_probability": 0.9,
        "text_length": "short"
    },
    "health": {
        "name": "💊 Здоровье",
        "emoji": "💊",
        "description": "Здоровье, фитнес, советы",
        "hashtags": ["здоровье", "фитнес", "советы"],
        "system_prompt": "Ты фитнес-тренер и нутрициолог. Давай советы по здоровью, фитнесу, правильному питанию.",
        "image_probability": 0.6,
        "text_length": "normal"
    },
    "tech": {
        "name": "📱 Технологии",
        "emoji": "📱",
        "description": "Гаджеты, устройства, технологии",
        "hashtags": ["технологии", "гаджеты", "инновации"],
        "system_prompt": "Ты технологический обозреватель. Рассказывай о новых гаджетах, устройствах, технологических инновациях.",
        "image_probability": 0.7,
        "text_length": "normal"
    },
    "fashion": {
        "name": "👗 Мода",
        "emoji": "👗",
        "description": "Мода, стиль, бренды",
        "hashtags": ["мода", "стиль", "бренды"],
        "system_prompt": "Ты модный эксперт. Рассказывай о модных тенденциях, брендах, стиле.",
        "image_probability": 0.9,
        "text_length": "short"
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология, саморазвитие, советы",
        "hashtags": ["психология", "саморазвитие", "советы"],
        "system_prompt": "Ты психолог. Дай полезные советы по психологии, саморазвитию, отношениям.",
        "image_probability": 0.5,
        "text_length": "long"
    },
    "marketing": {
        "name": "📊 Маркетинг",
        "emoji": "📊",
        "description": "Маркетинг, SMM, реклама",
        "hashtags": ["маркетинг", "smm", "реклама"],
        "system_prompt": "Ты маркетолог. Рассказывай о маркетинговых стратегиях, SMM, рекламе, продвижении.",
        "image_probability": 0.5,
        "text_length": "long"
    },
    "automotive": {
        "name": "🚗 Авто",
        "emoji": "🚗",
        "description": "Автомобили, новинки, обзоры",
        "hashtags": ["авто", "cars", "новинки"],
        "system_prompt": "Ты автоблогер. Рассказывай о новых автомобилях, технологиях, давай обзоры.",
        "image_probability": 0.8,
        "text_length": "normal"
    }
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class Channel:
    """Модель канала"""
    channel_id: str
    channel_name: str
    topics: List[str]  # Список тем для постинга
    schedule_time: str  # Время постинга (HH:MM)
    schedule_interval: int  # Интервал в часах или минутах
    last_post_time: float = 0
    is_active: bool = True
    repost_from: List[str] = field(default_factory=list)  # Каналы для репоста
    
@dataclass
class User:
    """Модель пользователя"""
    user_id: int
    username: str
    tariff: Tariff = Tariff.FREE
    channels: List[Channel] = field(default_factory=list)
    tariff_start_date: float = field(default_factory=time.time)
    
    def can_add_channel(self) -> bool:
        return len(self.channels) < TARIFFS_CONFIG[self.tariff]["max_channels"]
    
    def get_daily_post_count(self) -> int:
        # Подсчет постов за сегодня
        return 0  # Упрощенная версия
    
    def can_post_today(self) -> bool:
        return self.get_daily_post_count() < TARIFFS_CONFIG[self.tariff]["posts_per_day"]

@dataclass
class Post:
    """Модель поста"""
    post_id: str
    channel_id: str
    topic: str
    content: str
    image_url: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    is_repost: bool = False
    original_post_id: Optional[str] = None
    views_count: int = 0

# ==================== API КЛИЕНТ GIGACHAT ====================
class GigaChatClient:
    def __init__(self):
        self.api_token = None
        self.api_token_expiry = 0
    
    async def get_token(self) -> str:
        """Получение токена API"""
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
    
    async def generate_post(self, topic: str, text_length: str = "normal", include_image: bool = False) -> Tuple[str, Optional[str]]:
        """Генерация поста через GigaChat"""
        token = await self.get_token()
        if not token:
            return "❌ Ошибка авторизации", None
        
        topic_config = TOPICS_CONFIG[topic]
        
        # Настройка длины текста
        length_settings = {
            "short": "Короткий пост на 100-200 символов",
            "normal": "Пост среднего размера на 300-500 символов",
            "long": "Развернутый пост на 600-1000 символов"
        }
        
        # Формирование промпта
        prompt = f"""Ты автопостер в Telegram-канале. Создай уникальный, интересный пост на тему "{topic_config['name']}".

Требования:
- Язык: русский
- {length_settings.get(text_length, length_settings['normal'])}
- Используй эмодзи (3-5 штук)
- Добавь 2-3 хэштега: {' '.join(['#' + h for h in topic_config['hashtags']])}
- Будь информативным и вовлекающим
- Не повторяй предыдущие посты
- Стиль: {topic_config['system_prompt']}

Пост должен быть готов к публикации в Telegram, не используй markdown разметку.
Напиши только текст поста без дополнительных комментариев."""
        
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
                        "max_tokens": 1500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"]["content"]
                            # Генерация изображения через GigaChat (упрощенно, API может не поддерживать)
                            image_url = None
                            if include_image and topic_config["image_probability"] > random.random():
                                # Здесь можно добавить генерацию изображения через внешний API
                                image_url = None  # Пока без изображений
                            return content, image_url
                        return "❌ Не удалось сгенерировать пост", None
                    elif response.status == 401:
                        self.api_token = None
                        return await self.generate_post(topic, text_length, include_image)
                    else:
                        return f"❌ Ошибка API: {response.status}", None
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return f"❌ Ошибка: {str(e)}", None
    
    async def generate_repost_comment(self, original_content: str, topic: str) -> str:
        """Генерация комментария для репоста"""
        token = await self.get_token()
        if not token:
            return "♻️ Репост"
        
        prompt = f"""Сделай репост этого сообщения в свой канал. Добавь краткий комментарий от себя на русском языке (30-50 символов).
Тематика: {TOPICS_CONFIG[topic]['name']}

Оригинальный пост:
{original_content[:500]}

Ответь только текстом комментария, без кавычек и дополнительных пояснений."""
        
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
                        "max_tokens": 100
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                        return "♻️ Репост"
                    return "♻️ Репост"
        except Exception as e:
            logger.error(f"Ошибка репоста: {e}")
            return "♻️ Репост"

# ==================== БОТ ====================
class AutoPostBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.gigachat = GigaChatClient()
        self.users: Dict[int, User] = {}
        self.posts_history: List[Post] = []
        self.posting_tasks: Dict[str, asyncio.Task] = {}
        
    def get_user(self, user_id: int, username: str = "") -> User:
        """Получить пользователя"""
        if user_id not in self.users:
            self.users[user_id] = User(user_id=user_id, username=username)
        return self.users[user_id]
    
    async def post_to_channel(self, channel_id: str, content: str, image_url: Optional[str] = None):
        """Отправить пост в канал"""
        try:
            if image_url:
                await self.application.bot.send_photo(
                    chat_id=channel_id,
                    photo=image_url,
                    caption=content,
                    parse_mode='HTML'
                )
            else:
                await self.application.bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode='HTML'
                )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в канал {channel_id}: {e}")
            return False
    
    async def generate_and_post(self, user_id: int, channel: Channel):
        """Генерация и публикация поста"""
        user = self.get_user(user_id)
        
        # Проверка лимитов
        if not user.can_post_today():
            logger.warning(f"Пользователь {user_id} превысил лимит постов")
            return
        
        # Выбор случайной темы из списка канала
        if not channel.topics:
            return
        
        topic = random.choice(channel.topics)
        topic_config = TOPICS_CONFIG[topic]
        
        # Определение размера текста и наличия картинки
        text_length = topic_config["text_length"]
        include_image = random.random() < topic_config["image_probability"]
        
        # Генерация поста
        content, image_url = await self.gigachat.generate_post(
            topic, text_length, include_image
        )
        
        # Добавление хэштегов если их нет
        if not any(hash in content for hash in topic_config["hashtags"]):
            content += f"\n\n{' '.join(['#' + h for h in topic_config['hashtags'][:3]])}"
        
        # Публикация
        success = await self.post_to_channel(channel.channel_id, content, image_url)
        
        if success:
            # Сохранение в историю
            post = Post(
                post_id=str(uuid.uuid4()),
                channel_id=channel.channel_id,
                topic=topic,
                content=content,
                image_url=image_url
            )
            self.posts_history.append(post)
            channel.last_post_time = time.time()
            logger.info(f"Пост опубликован в {channel.channel_name} на тему {topic}")
    
    async def repost_from_channels(self, user_id: int, channel: Channel):
        """Репост из других каналов"""
        user = self.get_user(user_id)
        tariff_config = TARIFFS_CONFIG[user.tariff]
        
        if not tariff_config["can_repost"] or not channel.repost_from:
            return
        
        for source_channel in channel.repost_from:
            try:
                # Получаем последний пост из канала-источника
                # Упрощенная версия - пропускаем, т.к. требует прав бота в том канале
                pass
            except Exception as e:
                logger.error(f"Ошибка репоста: {e}")
    
    async def schedule_posts(self):
        """Планировщик постов"""
        while True:
            current_time = time.time()
            current_hour_min = datetime.now().strftime("%H:%M")
            
            for user_id, user in self.users.items():
                for channel in user.channels:
                    if not channel.is_active:
                        continue
                    
                    # Проверяем время по расписанию
                    if channel.schedule_time == current_hour_min:
                        # Генерация поста
                        await self.generate_and_post(user_id, channel)
                        
                        # Репосты
                        await self.repost_from_channels(user_id, channel)
                        
                        # Небольшая задержка между постами
                        await asyncio.sleep(2)
            
            await asyncio.sleep(30)  # Проверка каждые 30 секунд
    
    async def start_posting_scheduler(self):
        """Запуск планировщика"""
        asyncio.create_task(self.schedule_posts())
    
    # ==================== ОБРАБОТЧИКИ КОМАНД ====================
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        db_user = self.get_user(user.id, user.username or user.first_name)
        
        text = f"""🤖 *Привет, {user.first_name}!*

Добро пожаловать в *AutoPost Bot* - мощную систему автоматического постинга в Telegram!

*Что я умею:*
✅ Автоматический постинг в ваши каналы
✅ 20+ тематик: крипта, NFT, Telegram, AI и другие
✅ Уникальные посты через ИИ (GigaChat)
✅ Разные размеры текста и картинки
✅ Репосты из других каналов
✅ Гибкие тарифы

*Тарифы:*
🌟 Бесплатный - 1 канал, 5 постов/день
💎 Базовый - 3 канала, 20 постов/день
🚀 PRO - 10 каналов, 100 постов/день
👑 VIP - 50 каналов, 500 постов/день

*Команды:*
/addchannel - добавить канал
/mychannels - мои каналы
/remotechannel - удалить канал
/tariff - тарифы
/settariff - выбрать тариф
/topics - список тем
/postnow - пост сейчас
/help - помощь

*Начните с добавления канала:* /addchannel"""
        
        keyboard = [[
            InlineKeyboardButton("📊 Мои каналы", callback_data="my_channels"),
            InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")
        ], [
            InlineKeyboardButton("📝 Добавить канал", callback_data="add_channel"),
            InlineKeyboardButton("🎨 Темы", callback_data="topics_list")
        ]]
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def cmd_addchannel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление канала"""
        user_id = update.effective_user.id
        user = self.get_user(user_id)
        
        if not user.can_add_channel():
            tariff = TARIFFS_CONFIG[user.tariff]
            text = f"❌ *Лимит каналов*\n\nУ вас уже {len(user.channels)} из {tariff['max_channels']} каналов.\nДля добавления больше каналов обновите тариф: /settariff"
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        context.user_data['adding_channel'] = True
        await update.message.reply_text(
            "📝 *Добавление канала*\n\n"
            "Отправьте username канала (например, @mychannel) или перешлите любое сообщение из канала сюда.\n\n"
            "Бот должен быть администратором канала!\n\n"
            "Для отмены используйте /cancel",
            parse_mode='Markdown'
        )
    
    async def cmd_mychannels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список каналов"""
        user_id = update.effective_user.id
        user = self.get_user(user_id)
        
        if not user.channels:
            await update.message.reply_text(
                "❌ *У вас нет каналов*\n\nДобавьте первый канал: /addchannel",
                parse_mode='Markdown'
            )
            return
        
        text = f"📊 *Ваши каналы* ({len(user.channels)}/{TARIFFS_CONFIG[user.tariff]['max_channels']})\n\n"
        
        for i, channel in enumerate(user.channels, 1):
            topics_str = ", ".join([TOPICS_CONFIG[t]['emoji'] for t in channel.topics[:3]])
            status = "✅ активен" if channel.is_active else "⏸ приостановлен"
            text += f"{i}. {channel.channel_name}\n"
            text += f"   ID: `{channel.channel_id}`\n"
            text += f"   📍 Темы: {topics_str}\n"
            text += f"   ⏰ Время: {channel.schedule_time}\n"
            text += f"   🟢 Статус: {status}\n\n"
        
        keyboard = []
        for i, channel in enumerate(user.channels):
            keyboard.append([InlineKeyboardButton(
                f"⚙️ {channel.channel_name[:20]}",
                callback_data=f"channel_{i}"
            )])
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def cmd_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список тем"""
        text = "🎨 *Доступные темы для постинга*\n\n"
        
        for i, (key, config) in enumerate(TOPICS_CONFIG.items(), 1):
            text += f"{config['emoji']} *{config['name']}*\n"
            text += f"   📝 {config['description']}\n"
            text += f"   📍 Хэштеги: {', '.join(config['hashtags'][:2])}\n\n"
        
        text += "💡 Для настройки темы канала используйте команду /mychannels и выберите канал"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_tariff(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о тарифах"""
        user_id = update.effective_user.id
        user = self.get_user(user_id)
        
        text = f"💎 *Тарифные планы*\n\nВаш тариф: {TARIFFS_CONFIG[user.tariff]['name']}\n\n"
        
        for tariff, config in TARIFFS_CONFIG.items():
            price_text = f"{config['price']}₽" if config['price'] > 0 else "Бесплатно"
            text += f"*{config['name']}* - {price_text}\n"
            text += f"├ 📊 Каналов: {config['max_channels']}\n"
            text += f"├ 📝 Постов/день: {config['posts_per_day']}\n"
            text += f"├ 📢 Репосты: {'✅' if config['can_repost'] else '❌'}\n"
            text += f"├ 🤖 ИИ-посты: {'✅' if config['ai_generation'] else '❌'}\n"
            text += f"└ 🖼 Изображения: до {config['max_image_generation']} в день\n\n"
        
        text += "Для смены тарифа используйте /settariff"
        
        keyboard = []
        for tariff in Tariff:
            if tariff != user.tariff:
                keyboard.append([InlineKeyboardButton(
                    f"Перейти на {TARIFFS_CONFIG[tariff]['name']}",
                    callback_data=f"set_tariff_{tariff.value}"
                )])
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def cmd_settariff(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор тарифа"""
        keyboard = []
        for tariff in Tariff:
            config = TARIFFS_CONFIG[tariff]
            keyboard.append([InlineKeyboardButton(
                f"{config['name']} - {config['max_channels']} каналов",
                callback_data=f"tariff_{tariff.value}"
            )])
        
        await update.message.reply_text(
            "💎 *Выберите тарифный план*\n\n2500рублей в месяц все тарифы",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_postnow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Немедленный постинг"""
        user_id = update.effective_user.id
        user = self.get_user(user_id)
        
        if not user.channels:
            await update.message.reply_text("❌ У вас нет каналов. Добавьте сначала: /addchannel")
            return
        
        text = "🎯 *Выберите канал* для немедленного постинга:\n\n"
        
        keyboard = []
        for i, channel in enumerate(user.channels):
            keyboard.append([InlineKeyboardButton(
                f"{channel.channel_name}",
                callback_data=f"postnow_{i}"
            )])
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь"""
        text = """🤖 *AutoPost Bot - Помощь*

*Основные команды:*
/start - Главное меню
/addchannel - Добавить канал
/mychannels - Мои каналы
/remotechannel - Удалить канал
/channelinfo - Информация о канале

*Постинг:*
/topics - Список тем
/postnow - Пост прямо сейчас
/schedule - Управление расписанием

*Тарифы:*
/tariff - Информация о тарифах
/settariff - Сменить тариф

*Другое:*
/help - Эта справка
/cancel - Отменить действие

*Как настроить канал:*
1. Добавьте бота в канал как администратора
2. Используйте /addchannel
3. Выберите темы для постинга
4. Настройте расписание
5. Всё! Бот начнет постить автоматически

*Вопросы:* @support"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ==================== CALLBACK ОБРАБОТЧИКИ ====================
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        user = self.get_user(user_id)
        
        # Добавление канала
        if data == "add_channel":
            context.user_data['adding_channel'] = True
            await query.edit_message_text(
                "📝 *Добавление канала*\n\n"
                "Отправьте username канала (например, @mychannel) или перешлите сообщение из канала.\n\n"
                "Для отмены: /cancel",
                parse_mode='Markdown'
            )
        
        # Мои каналы
        elif data == "my_channels":
            await self.cmd_mychannels(update, context)
        
        # Тарифы
        elif data == "tariffs":
            await self.cmd_tariff(update, context)
        
        # Список тем
        elif data == "topics_list":
            await self.cmd_topics(update, context)
        
        # Настройка тарифа
        elif data.startswith("tariff_"):
            tariff_key = data.replace("tariff_", "")
            user.tariff = Tariff(tariff_key)
            user.tariff_start_date = time.time()
            await query.edit_message_text(
                f"✅ *Тариф изменен на {TARIFFS_CONFIG[user.tariff]['name']}*\n\n"
                f"📊 Доступно каналов: {TARIFFS_CONFIG[user.tariff]['max_channels']}\n"
                f"📝 Постов в день: {TARIFFS_CONFIG[user.tariff]['posts_per_day']}\n"
                f"📢 Репосты: {'✅' if TARIFFS_CONFIG[user.tariff]['can_repost'] else '❌'}",
                parse_mode='Markdown'
            )
        
        # Настройка канала
        elif data.startswith("channel_"):
            channel_index = int(data.replace("channel_", ""))
            if channel_index < len(user.channels):
                channel = user.channels[channel_index]
                text = f"⚙️ *Настройка канала:* {channel.channel_name}\n\n"
                
                topics_str = "\n".join([f"• {TOPICS_CONFIG[t]['name']}" for t in channel.topics])
                text += f"📍 *Темы:*\n{topics_str}\n\n"
                text += f"⏰ *Расписание:* {channel.schedule_time}\n"
                text += f"🟢 *Статус:* {'Активен' if channel.is_active else 'Приостановлен'}\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("🎨 Изменить темы", callback_data=f"ch_topics_{channel_index}")],
                    [InlineKeyboardButton("⏰ Изменить время", callback_data=f"ch_time_{channel_index}")],
                    [InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"ch_status_{channel_index}")],
                    [InlineKeyboardButton("📢 Настроить репосты", callback_data=f"ch_repost_{channel_index}")],
                    [InlineKeyboardButton("🗑 Удалить канал", callback_data=f"ch_delete_{channel_index}")]
                ]
                
                await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Изменение тем канала
        elif data.startswith("ch_topics_"):
            channel_index = int(data.replace("ch_topics_", ""))
            context.user_data['config_channel_index'] = channel_index
            context.user_data['config_step'] = 'topics'
            
            text = "🎨 *Выберите темы для канала*\n\nВы можете выбрать несколько тем:\n\n"
            
            keyboard = []
            for topic_key, topic_config in TOPICS_CONFIG.items():
                keyboard.append([InlineKeyboardButton(
                    f"{topic_config['emoji']} {topic_config['name']}",
                    callback_data=f"add_topic_{topic_key}_{channel_index}"
                )])
            keyboard.append([InlineKeyboardButton("✅ Готово", callback_data=f"topics_done_{channel_index}")])
            
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Добавление темы
        elif data.startswith("add_topic_"):
            parts = data.split("_")
            topic_key = parts[2]
            channel_index = int(parts[3])
            
            if channel_index < len(user.channels):
                if topic_key not in user.channels[channel_index].topics:
                    user.channels[channel_index].topics.append(topic_key)
                    await query.answer(f"✅ Тема {TOPICS_CONFIG[topic_key]['name']} добавлена")
                else:
                    await query.answer("⏰ Тема уже добавлена")
        
        # Завершение выбора тем
        elif data.startswith("topics_done_"):
            channel_index = int(data.replace("topics_done_", ""))
            context.user_data.pop('config_step', None)
            
            await query.edit_message_text(
                f"✅ *Темы канала обновлены!*\n\n"
                f"Теперь канал будет постить на {len(user.channels[channel_index].topics)} темах.",
                parse_mode='Markdown'
            )
        
        # Изменение времени
        elif data.startswith("ch_time_"):
            channel_index = int(data.replace("ch_time_", ""))
            context.user_data['config_channel_index'] = channel_index
            context.user_data['config_step'] = 'time'
            
            await query.edit_message_text(
                "⏰ *Настройка расписания*\n\n"
                "Введите время постинга в формате ЧЧ:ММ (например, 09:00 или 18:30)\n\n"
                "Посты будут публиковаться каждый день в это время.\n\n"
                "Для отмены: /cancel",
                parse_mode='Markdown'
            )
        
        # Вкл/Выкл канал
        elif data.startswith("ch_status_"):
            channel_index = int(data.replace("ch_status_", ""))
            if channel_index < len(user.channels):
                user.channels[channel_index].is_active = not user.channels[channel_index].is_active
                status_text = "включен" if user.channels[channel_index].is_active else "выключен"
                await query.answer(f"Канал {status_text}")
                # Возврат к настройкам
                await self.handle_callback(update, context)
        
        # Удаление канала
        elif data.startswith("ch_delete_"):
            channel_index = int(data.replace("ch_delete_", ""))
            if channel_index < len(user.channels):
                channel = user.channels.pop(channel_index)
                await query.answer(f"Канал {channel.channel_name} удален")
                await self.cmd_mychannels(update, context)
        
        # Немедленный пост
        elif data.startswith("postnow_"):
            channel_index = int(data.replace("postnow_", ""))
            if channel_index < len(user.channels):
                await query.edit_message_text("🔄 *Генерация поста...*", parse_mode='Markdown')
                await self.generate_and_post(user_id, user.channels[channel_index])
                await query.edit_message_text("✅ *Пост опубликован!*", parse_mode='Markdown')
    
    # ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Добавление канала
        if context.user_data.get('adding_channel'):
            channel_input = text.strip()
            channel_id = channel_input
            
            # Если переслано сообщение из канала
            if update.message.forward_from_chat:
                channel_id = str(update.message.forward_from_chat.id)
                channel_name = update.message.forward_from_chat.title or channel_id
            else:
                # Убираем @ если есть
                if channel_input.startswith('@'):
                    channel_input = channel_input[1:]
                channel_name = channel_input
                channel_id = f"@{channel_input}"
            
            # Создание канала
            user = self.get_user(user_id)
            if user.can_add_channel():
                new_channel = Channel(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    topics=["tech", "ai"],  # Темы по умолчанию
                    schedule_time="12:00",
                    schedule_interval=24
                )
                user.channels.append(new_channel)
                
                # Выбор тем
                context.user_data['config_channel_index'] = len(user.channels) - 1
                context.user_data['config_step'] = 'topics'
                
                await update.message.reply_text(
                    f"✅ *Канал добавлен!*\n\n"
                    f"📊 Название: {channel_name}\n"
                    f"🆔 ID: {channel_id}\n\n"
                    f"Теперь выберите темы для постинга:",
                    parse_mode='Markdown'
                )
                
                # Показываем выбор тем
                await self.cmd_topics(update, context)
            else:
                await update.message.reply_text("❌ Лимит каналов исчерпан")
            
            context.user_data.pop('adding_channel', None)
        
        # Настройка времени
        elif context.user_data.get('config_step') == 'time':
            try:
                time_str = text.strip()
                # Проверка формата
                datetime.strptime(time_str, "%H:%M")
                
                channel_index = context.user_data.get('config_channel_index')
                user = self.get_user(user_id)
                
                if channel_index is not None and channel_index < len(user.channels):
                    user.channels[channel_index].schedule_time = time_str
                    await update.message.reply_text(
                        f"✅ *Время изменено на {time_str}*\n\n"
                        f"Теперь посты будут публиковаться каждый день в {time_str}",
                        parse_mode='Markdown'
                    )
                
                context.user_data.pop('config_step', None)
                context.user_data.pop('config_channel_index', None)
            except ValueError:
                await update.message.reply_text(
                    "❌ *Неверный формат времени*\n\n"
                    "Используйте формат ЧЧ:ММ, например: 09:00 или 18:30",
                    parse_mode='Markdown'
                )
        
        else:
            await update.message.reply_text(
                "🤖 *AutoPost Bot*\n\n"
                "Используйте команды из меню или /help для справки",
                parse_mode='Markdown'
            )
    
    # ==================== ЗАПУСК ====================
    def setup_handlers(self):
        """Настройка обработчиков"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("addchannel", self.cmd_addchannel))
        self.application.add_handler(CommandHandler("mychannels", self.cmd_mychannels))
        self.application.add_handler(CommandHandler("topics", self.cmd_topics))
        self.application.add_handler(CommandHandler("tariff", self.cmd_tariff))
        self.application.add_handler(CommandHandler("settariff", self.cmd_settariff))
        self.application.add_handler(CommandHandler("postnow", self.cmd_postnow))
        
        # Callback
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Сообщения
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def run(self):
        """Запуск бота"""
        self.setup_handlers()
        
        # Запуск планировщика
        asyncio.create_task(self.schedule_posts())
        
        logger.info("🚀 AutoPost Bot запущен!")
        logger.info(f"📊 Доступно {len(TOPICS_CONFIG)} тем")
        logger.info("💎 Тарифы: Бесплатный, Базовый, PRO, VIP")
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Держим бота запущенным
        while True:
            await asyncio.sleep(1)

# ==================== ТОЧКА ВХОДА ====================
async def main():
    bot = AutoPostBot(TELEGRAM_TOKEN)
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
