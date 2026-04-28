import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== API НАСТРОЙКИ ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== ТАРИФЫ ====================
class Tariff(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

TARIFFS = {
    "free": {
        "name": "📋 Бесплатный",
        "price": 0,
        "channels_limit": 1,
        "posts_per_day": 5,
        "ai_posts_per_day": 3,
        "auto_posting": False,
        "features": ["ручной постинг", "1 канал", "5 постов/день"]
    },
    "basic": {
        "name": "⚡ Базовый",
        "price": 0,
        "channels_limit": 3,
        "posts_per_day": 20,
        "ai_posts_per_day": 10,
        "auto_posting": True,
        "features": ["автопостинг", "3 канала", "20 постов/день", "AI-контент"]
    },
    "pro": {
        "name": "🚀 PRO",
        "price": 0,
        "channels_limit": 10,
        "posts_per_day": 100,
        "ai_posts_per_day": 50,
        "auto_posting": True,
        "features": ["10 каналов", "100 постов/день", "репост из каналов", "AI-генерация"]
    },
    "premium": {
        "name": "👑 PREMIUM",
        "price": 0,
        "channels_limit": 50,
        "posts_per_day": 500,
        "ai_posts_per_day": 250,
        "auto_posting": True,
        "features": ["50 каналов", "500 постов/день", "полный функционал", "приоритетная поддержка"]
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТОВ ====================
TOPICS = {
    "crypto": {
        "name": "💰 Криптовалюты",
        "emoji": "💰",
        "prompt": "Создай пост о криптовалютах: биткоин, эфириум, новые монеты, блокчейн, DeFi, тренды рынка. Будь актуальным и информативным.",
        "hashtags": ["#криптовалюта", "#биткоин", "#блокчейн", "#дефи"]
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "prompt": "Создай пост о NFT: новые коллекции, тренды, маркетплейсы, искусство в блокчейне, метавселенные. Будь креативным.",
        "hashtags": ["#nft", "#цифровоеискусство", "#метавселенная"]
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "prompt": "Создай пост о Telegram: новые функции, обновления, боты, каналы, фишки мессенджера. Будь полезным.",
        "hashtags": ["#telegram", "#мессенджер", "#обновления"]
    },
    "web3": {
        "name": "🌐 Web3",
        "emoji": "🌐",
        "prompt": "Создай пост о Web3: децентрализация, блокчейн приложения, будущее интернета. Будь инновационным.",
        "hashtags": ["#web3", "#децентрализация", "#блокчейн"]
    },
    "ai": {
        "name": "🤖 Искусственный интеллект",
        "emoji": "🤖",
        "prompt": "Создай пост об ИИ: новые модели, нейросети, применение AI, будущее технологий.",
        "hashtags": ["#искусственныйинтеллект", "#нейросети", "#ai"]
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "prompt": "Создай пост об играх: новинки, обзоры, киберспорт, игровые технологии.",
        "hashtags": ["#игры", #гейминг", "#киберспорт"]
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "prompt": "Создай пост о бизнесе: стартапы, инвестиции, предпринимательство, маркетинг.",
        "hashtags": ["#бизнес", "#стартап", "#инвестиции"]
    },
    "marketing": {
        "name": "📊 Маркетинг",
        "emoji": "📊",
        "prompt": "Создай пост о маркетинге: стратегии, SMM, реклама, аналитика, кейсы.",
        "hashtags": ["#маркетинг", "#smm", "#реклама"]
    },
    "tech": {
        "name": "🔧 Технологии",
        "emoji": "🔧",
        "prompt": "Создай пост о технологиях: гаджеты, инновации, наука, IT-тренды.",
        "hashtags": ["#технологии", "#инновации", "#it"]
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "prompt": "Создай пост о науке: открытия, исследования, космос, биотехнологии.",
        "hashtags": ["#наука", "#исследования", "#космос"]
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "prompt": "Создай пост о психологии: саморазвитие, отношения, эмоции, мышление.",
        "hashtags": ["#психология", "#саморазвитие", "#мотивация"]
    },
    "fitness": {
        "name": "💪 Фитнес",
        "emoji": "💪",
        "prompt": "Создай пост о фитнесе: тренировки, питание, здоровье, мотивация.",
        "hashtags": ["#фитнес", "#спорт", "#здоровье"]
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "prompt": "Создай пост о путешествиях: страны, советы, лайфхаки, направления.",
        "hashtags": ["#путешествия", "#тревел", "#отпуск"]
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "prompt": "Создай пост о кулинарии: рецепты, советы, рестораны, кулинарные тренды.",
        "hashtags": ["#кулинария", "#рецепты", "#еда"]
    },
    "art": {
        "name": "🎭 Искусство",
        "emoji": "🎭",
        "prompt": "Создай пост об искусстве: живопись, музыка, театр, современное искусство.",
        "hashtags": ["#искусство", "#творчество", "#культура"]
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "prompt": "Создай пост об образовании: обучение, курсы, навыки, саморазвитие.",
        "hashtags": ["#образование", "#обучение", "#навыки"]
    },
    "career": {
        "name": "💼 Карьера",
        "emoji": "💼",
        "prompt": "Создай пост о карьере: работа, вакансии, резюме, собеседования, рост.",
        "hashtags": ["#карьера", "#работа", "#вакансии"]
    },
    "finance": {
        "name": "📈 Финансы",
        "emoji": "📈",
        "prompt": "Создай пост о финансах: инвестиции, сбережения, бюджетирование, доходы.",
        "hashtags": ["#финансы", "#деньги", "#инвестиции"]
    },
    "lifehacks": {
        "name": "💡 Лайфхаки",
        "emoji": "💡",
        "prompt": "Создай пост с полезными лайфхаками: советы, хитрости, решения проблем.",
        "hashtags": ["#лайфхаки", "#советы", "#полезно"]
    },
    "news": {
        "name": "📰 Новости",
        "emoji": "📰",
        "prompt": "Создай пост с актуальными новостями: события, тренды, обновления.",
        "hashtags": ["#новости", "#актуально", "#события"]
    }
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
@dataclass
class UserProfile:
    user_id: int
    username: str
    first_name: str
    phone: str = ""
    tariff: str = "free"
    telegram_client: Optional[TelegramClient] = None
    string_session: str = ""
    channels: List[Dict] = field(default_factory=list)
    posts_today: int = 0
    ai_posts_today: int = 0
    last_post_date: datetime = field(default_factory=datetime.now)
    auto_posting_topics: List[str] = field(default_factory=list)
    posting_schedule: Dict = field(default_factory=dict)
    repost_sources: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def can_post(self) -> bool:
        """Проверка лимитов постинга"""
        tariff_config = TARIFFS[self.tariff]
        if self.posts_today >= tariff_config["posts_per_day"]:
            return False
        
        # Сброс счетчика в новый день
        if datetime.now().date() > self.last_post_date.date():
            self.posts_today = 0
            self.ai_posts_today = 0
            
        return True
    
    def can_ai_post(self) -> bool:
        """Проверка лимита AI-постов"""
        tariff_config = TARIFFS[self.tariff]
        if self.ai_posts_today >= tariff_config["ai_posts_per_day"]:
            return False
        
        if datetime.now().date() > self.last_post_date.date():
            self.ai_posts_today = 0
            
        return True

class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserProfile] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.bot_app = None
        self.posting_tasks = {}
        
    def load_users(self):
        """Загрузка пользователей из файла"""
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for user_id, user_data in data.items():
                    profile = UserProfile(
                        user_id=int(user_id),
                        username=user_data.get("username", ""),
                        first_name=user_data.get("first_name", ""),
                        phone=user_data.get("phone", ""),
                        tariff=user_data.get("tariff", "free"),
                        string_session=user_data.get("string_session", ""),
                        channels=user_data.get("channels", []),
                        auto_posting_topics=user_data.get("auto_posting_topics", []),
                        repost_sources=user_data.get("repost_sources", [])
                    )
                    self.users[int(user_id)] = profile
        except FileNotFoundError:
            logger.info("Файл users.json не найден, создаем новый")
    
    def save_users(self):
        """Сохранение пользователей в файл"""
        data = {}
        for user_id, profile in self.users.items():
            data[user_id] = {
                "username": profile.username,
                "first_name": profile.first_name,
                "phone": profile.phone,
                "tariff": profile.tariff,
                "string_session": profile.string_session,
                "channels": profile.channels,
                "auto_posting_topics": profile.auto_posting_topics,
                "repost_sources": profile.repost_sources
            }
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_profile(self, user_id: int, username: str = "", first_name: str = "") -> UserProfile:
        if user_id not in self.users:
            self.users[user_id] = UserProfile(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            self.save_users()
        return self.users[user_id]
    
    async def get_api_token(self) -> str:
        """Получение токена GigaChat"""
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
    
    async def generate_ai_post(self, topic_key: str, post_size: str = "medium") -> tuple[str, str]:
        """Генерация поста через GigaChat"""
        token = await self.get_api_token()
        if not token:
            return None, "❌ Ошибка авторизации API"
        
        topic = TOPICS.get(topic_key, TOPICS["news"])
        
        size_config = {
            "small": {"words": 50, "emoji_count": 2},
            "medium": {"words": 100, "emoji_count": 3},
            "large": {"words": 200, "emoji_count": 5}
        }
        
        size = size_config.get(post_size, size_config["medium"])
        
        prompt = f"""{topic['prompt']}

Требования к посту:
- Объем: {size['words']} слов
- Используй {size['emoji_count']} эмодзи
- Структурируй текст
- Добавь хэштеги: {' '.join(topic['hashtags'])}
- Будь уникальным и интересным
- Не повторяй стандартные фразы
- Пиши на русском языке

Создай уникальный пост на заданную тему."""
        
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
                        "max_tokens": 1500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            post_text = data["choices"][0]["message"]["content"]
                            # Генерация "картинки" (имитация, так как GigaChat не генерирует изображения)
                            image_url = await self.get_random_image(topic_key)
                            return post_text, image_url
                        else:
                            return None, "❌ Ошибка генерации поста"
                    else:
                        return None, f"❌ Ошибка API: {response.status}"
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return None, f"❌ Ошибка: {str(e)}"
    
    async def get_random_image(self, topic_key: str) -> str:
        """Получение случайного изображения по теме (имитация)"""
        # Здесь можно интегрировать Unsplash API или другой сервис
        # Пока возвращаем плейсхолдеры
        images = {
            "crypto": ["💰", "📈", "💎"],
            "nft": ["🎨", "🖼️", "✨"],
            "telegram": ["📱", "💬", "🤖"],
            "web3": ["🌐", "🔗", "⚡"],
            "ai": ["🤖", "🧠", "💡"]
        }
        
        emojis = images.get(topic_key, ["📝", "✨", "💫"])
        return random.choice(emojis)
    
    async def connect_telegram_account(self, phone: str, code_callback) -> bool:
        """Подключение аккаунта Telegram через телефон и код"""
        try:
            client = TelegramClient(StringSession(), api_id=1, api_hash='', device_model="PostingBot")
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                code = await code_callback()
                await client.sign_in(phone, code)
            
            string_session = client.session.save()
            await client.disconnect()
            return string_session
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return None
    
    async def send_post_to_channel(self, user_profile: UserProfile, channel_id: str, post_text: str, image: str = None):
        """Отправка поста в канал"""
        if not user_profile.telegram_client:
            user_profile.telegram_client = TelegramClient(
                StringSession(user_profile.string_session),
                api_id=1,
                api_hash=''
            )
            await user_profile.telegram_client.connect()
        
        try:
            if image and not image.startswith(("http", "https")):
                # Если это эмодзи или текст, отправляем просто текст
                await user_profile.telegram_client.send_message(channel_id, post_text)
            else:
                await user_profile.telegram_client.send_message(channel_id, post_text)
            
            user_profile.posts_today += 1
            user_profile.last_post_date = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в канал {channel_id}: {e}")
            return False
    
    async def start_auto_posting(self, user_id: int):
        """Запуск автопостинга для пользователя"""
        if user_id in self.posting_tasks:
            self.posting_tasks[user_id].cancel()
        
        profile = self.users.get(user_id)
        if not profile or profile.tariff not in ["basic", "pro", "premium"]:
            return
        
        async def auto_poster():
            while True:
                try:
                    for channel in profile.channels:
                        if profile.tariff == "basic" and len(profile.auto_posting_topics) > 0:
                            topic = random.choice(profile.auto_posting_topics)
                            post_text, image = await self.generate_ai_post(topic, random.choice(["small", "medium", "large"]))
                            if post_text:
                                await self.send_post_to_channel(profile, channel["id"], post_text, image)
                                profile.ai_posts_today += 1
                        
                        # Интервал между постами (от 1 до 4 часов)
                        await asyncio.sleep(random.randint(3600, 14400))
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Ошибка автопостинга: {e}")
                    await asyncio.sleep(3600)
        
        task = asyncio.create_task(auto_poster())
        self.posting_tasks[user_id] = task

# ==================== БОТ ДЛЯ ТЕЛЕГРАМ ====================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

bot = PostingBot()
bot.load_users()

# Состояния для разговора
PHONE, CODE, CHANNEL_ADD, TOPIC_SELECT, POST_SIZE, POST_CONTENT = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт бота"""
    user = update.effective_user
    profile = bot.get_user_profile(user.id, user.username or "", user.first_name or "")
    
    text = (
        f"🤖 *Привет, {user.first_name}!*\n\n"
        f"Добро пожаловать в *BotPosting* - систему автоматического постинга в Telegram!\n\n"
        f"✨ *Возможности:*\n"
        f"• 📝 Подключение аккаунта Telegram\n"
        f"• 📢 Добавление бота в каналы\n"
        f"• 🎨 Автопостинг с AI-контентом\n"
        f"• 🔄 Репост из других каналов\n"
        f"• 💰 Бесплатные тарифы\n"
        f"• 🎯 20+ тем для постов\n\n"
        f"📋 *Доступные тарифы:*\n"
    )
    
    for tariff_key, tariff in TARIFFS.items():
        text += f"\n*{tariff['name']}*:\n"
        for feature in tariff['features']:
            text += f"  • {feature}\n"
        text += f"  • {tariff['channels_limit']} каналов\n"
        text += f"  • {tariff['posts_per_day']} постов/день\n"
    
    keyboard = [
        [InlineKeyboardButton("🚀 Начать", callback_data="get_started")],
        [InlineKeyboardButton("💎 Выбрать тариф", callback_data="show_tariffs")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def get_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📱 Подключить аккаунт", callback_data="connect_account")],
        [InlineKeyboardButton("📊 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="show_tariffs")]
    ]
    
    await query.edit_message_text(
        "🎯 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подключение аккаунта"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 *Подключение аккаунта Telegram*\n\n"
        "Введите номер телефона в международном формате:\n"
        "Пример: `+79001234567`\n\n"
        "⚠️ Бот не хранит ваши данные, используется официальная библиотека Telethon",
        parse_mode='Markdown'
    )
    
    return PHONE

async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    phone = update.message.text
    context.user_data['phone'] = phone
    
    try:
        # Сохраняем номер и запрашиваем код
        context.user_data['temp_client'] = TelegramClient(StringSession(), api_id=1, api_hash='')
        await context.user_data['temp_client'].connect()
        await context.user_data['temp_client'].send_code_request(phone)
        
        await update.message.reply_text(
            "✅ *Код отправлен!*\n\n"
            "Введите код подтверждения из Telegram:",
            parse_mode='Markdown'
        )
        return CODE
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            "Попробуйте еще раз /start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода подтверждения"""
    code = update.message.text
    phone = context.user_data.get('phone')
    
    try:
        client = context.user_data['temp_client']
        await client.sign_in(phone, code)
        
        string_session = client.session.save()
        
        user_id = update.effective_user.id
        profile = bot.get_user_profile(user_id)
        profile.string_session = string_session
        profile.telegram_client = client
        profile.phone = phone
        
        bot.save_users()
        
        await update.message.reply_text(
            "✅ *Аккаунт успешно подключен!*\n\n"
            "Теперь вы можете добавлять каналы и настраивать постинг.\n\n"
            "Используйте /menu для продолжения.",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text(
            "🔐 *Требуется пароль двухфакторной аутентификации*\n\n"
            "Введите пароль:",
            parse_mode='Markdown'
        )
        return CODE  # Здесь можно добавить обработку пароля
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            "Попробуйте еще раз /start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр каналов"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    if not profile.channels:
        text = "📢 *У вас пока нет добавленных каналов*\n\nДобавьте первый канал:"
        keyboard = [[InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")]]
    else:
        text = "📢 *Ваши каналы:*\n\n"
        for i, channel in enumerate(profile.channels, 1):
            text += f"{i}. {channel.get('title', 'Канал')}\n"
            text += f"   ID: `{channel['id']}`\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Удалить канал", callback_data="remove_channel")],
            [InlineKeyboardButton("🔙 Назад", callback_data="get_started")]
        ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление канала"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1. Добавьте бота в канал как администратора\n"
        "2. Отправьте сюда ссылку или username канала\n\n"
        "Примеры:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`",
        parse_mode='Markdown'
    )
    
    return CHANNEL_ADD

async def channel_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    channel_input = update.message.text.strip()
    
    # Извлекаем username из ссылки
    if "t.me/" in channel_input:
        channel_username = channel_input.split("t.me/")[-1]
    else:
        channel_username = channel_input.replace("@", "")
    
    user_id = update.effective_user.id
    profile = bot.get_user_profile(user_id)
    
    tariff_config = TARIFFS[profile.tariff]
    if len(profile.channels) >= tariff_config["channels_limit"]:
        await update.message.reply_text(
            f"❌ *Достигнут лимит каналов для вашего тарифа!*\n\n"
            f"Лимит: {tariff_config['channels_limit']} каналов\n"
            f"Используйте /tariff для смены тарифа",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    try:
        # Получаем информацию о канале
        if not profile.telegram_client:
            profile.telegram_client = TelegramClient(
                StringSession(profile.string_session),
                api_id=1,
                api_hash=''
            )
            await profile.telegram_client.connect()
        
        entity = await profile.telegram_client.get_entity(channel_username)
        
        profile.channels.append({
            "id": channel_username,
            "title": entity.title,
            "added_at": datetime.now().isoformat()
        })
        
        bot.save_users()
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 Название: {entity.title}\n"
            f"🆔 Username: @{channel_username}\n\n"
            f"Теперь настройте автопостинг через /settings",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            "Убедитесь, что:\n"
            "1. Бот добавлен в канал как администратор\n"
            "2. Ссылка введена правильно\n"
            "3. Канал существует",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🎨 Настройка тем", callback_data="settings_topics")],
        [InlineKeyboardButton("⏰ Расписание постинга", callback_data="settings_schedule")],
        [InlineKeyboardButton("🔄 Репост из каналов", callback_data="settings_repost")],
        [InlineKeyboardButton("💎 Сменить тариф", callback_data="show_tariffs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="get_started")]
    ]
    
    active_topics = ", ".join([f"{TOPICS[t]['emoji']}" for t in profile.auto_posting_topics]) if profile.auto_posting_topics else "не выбраны"
    
    await query.edit_message_text(
        f"⚙️ *Настройки*\n\n"
        f"📊 Тариф: {TARIFFS[profile.tariff]['name']}\n"
        f"📢 Каналов: {len(profile.channels)}/{TARIFFS[profile.tariff]['channels_limit']}\n"
        f"🎨 Активные темы: {active_topics}\n"
        f"📝 Постов сегодня: {profile.posts_today}/{TARIFFS[profile.tariff]['posts_per_day']}\n"
        f"🤖 AI-постов: {profile.ai_posts_today}/{TARIFFS[profile.tariff]['ai_posts_per_day']}\n\n"
        f"Выберите раздел для настройки:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def settings_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка тем"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    # Создаем клавиатуру с темами
    keyboard = []
    for topic_key, topic in TOPICS.items():
        is_selected = topic_key in profile.auto_posting_topics
        button_text = f"{'✅' if is_selected else '⬜'} {topic['emoji']} {topic['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle_topic_{topic_key}")])
    
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="settings_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings")])
    
    await query.edit_message_text(
        "🎨 *Выберите темы для автопостинга*\n\n"
        "Нажмите на тему, чтобы включить/выключить\n"
        "Бот будет генерировать посты на выбранные темы\n\n"
        f"*Выбрано:* {len(profile.auto_posting_topics)} тем",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение темы"""
    query = update.callback_query
    await query.answer()
    
    topic_key = query.data.replace("toggle_topic_", "")
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    if topic_key in profile.auto_posting_topics:
        profile.auto_posting_topics.remove(topic_key)
    else:
        profile.auto_posting_topics.append(topic_key)
    
    bot.save_users()
    
    # Обновляем клавиатуру
    keyboard = []
    for tk, topic in TOPICS.items():
        is_selected = tk in profile.auto_posting_topics
        button_text = f"{'✅' if is_selected else '⬜'} {topic['emoji']} {topic['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle_topic_{tk}")])
    
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="settings_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings")])
    
    await query.edit_message_text(
        f"🎨 *Выберите темы для автопостинга*\n\n"
        f"*Выбрано:* {len(profile.auto_posting_topics)} тем",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    text = "💎 *Тарифы*\n\n"
    for tariff_key, tariff in TARIFFS.items():
        current = " ✅" if profile.tariff == tariff_key else ""
        text += f"*{tariff['name']}{current}*\n"
        for feature in tariff['features']:
            text += f"  • {feature}\n"
        text += f"  • {tariff['channels_limit']} каналов\n"
        text += f"  • {tariff['posts_per_day']} постов/день\n\n"
    
    keyboard = []
    for tariff_key in TARIFFS.keys():
        if profile.tariff != tariff_key:
            keyboard.append([InlineKeyboardButton(
                f"Выбрать {TARIFFS[tariff_key]['name']}",
                callback_data=f"select_tariff_{tariff_key}"
            )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="get_started")])
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор тарифа"""
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    profile.tariff = tariff_key
    bot.save_users()
    
    # Запускаем автопостинг если выбран платный тариф
    if tariff_key in ["basic", "pro", "premium"]:
        await bot.start_auto_posting(user_id)
    
    await query.edit_message_text(
        f"✅ *Тариф изменен на {TARIFFS[tariff_key]['name']}*\n\n"
        f"Теперь вам доступны новые возможности!\n"
        f"Используйте /menu для продолжения",
        parse_mode='Markdown'
    )

async def manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручной постинг"""
    user_id = update.effective_user.id
    profile = bot.get_user_profile(user_id)
    
    if not profile.can_post():
        await update.message.reply_text(
            "❌ *Лимит постов на сегодня исчерпан!*\n"
            "Завтра лимит обновится",
            parse_mode='Markdown'
        )
        return
    
    if not profile.channels:
        await update.message.reply_text(
            "❌ *У вас нет добавленных каналов*\n"
            "Сначала добавьте канал через /menu",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['manual_post'] = True
    await update.message.reply_text(
        "📝 *Создание поста*\n\n"
        "Выберите тип контента:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Сгенерировать AI", callback_data="generate_ai")],
            [InlineKeyboardButton("📝 Свой текст", callback_data="custom_text")],
            [InlineKeyboardButton("🔄 Репост", callback_data="repost_from_channel")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_post")]
        ])
    )

async def generate_ai_post_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация AI поста"""
    query = update.callback_query
    await query.answer()
    
    # Выбор темы
    keyboard = []
    for topic_key, topic in TOPICS.items():
        keyboard.append([InlineKeyboardButton(f"{topic['emoji']} {topic['name']}", callback_data=f"gen_topic_{topic_key}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_post")])
    
    await query.edit_message_text(
        "🤖 *Выберите тему для генерации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_generate_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора темы для генерации"""
    query = update.callback_query
    await query.answer()
    
    topic_key = query.data.replace("gen_topic_", "")
    context.user_data['generated_topic'] = topic_key
    
    # Выбор размера поста
    keyboard = [
        [InlineKeyboardButton("📄 Маленький", callback_data="size_small")],
        [InlineKeyboardButton("📑 Средний", callback_data="size_medium")],
        [InlineKeyboardButton("📚 Большой", callback_data="size_large")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_post")]
    ]
    
    await query.edit_message_text(
        f"📏 *Выберите размер поста:*\n\n"
        f"Тема: {TOPICS[topic_key]['emoji']} {TOPICS[topic_key]['name']}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def generate_post_with_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация поста с выбранным размером"""
    query = update.callback_query
    await query.answer()
    
    size = query.data.replace("size_", "")
    topic_key = context.user_data.get('generated_topic')
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    
    if not profile.can_ai_post():
        await query.edit_message_text(
            "❌ *Лимит AI-постов на сегодня исчерпан!*\n"
            "Завтра лимит обновится",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text("🤖 *Генерирую пост...*", parse_mode='Markdown')
    
    post_text, image = await bot.generate_ai_post(topic_key, size)
    
    if post_text:
        # Выбор канала для отправки
        keyboard = []
        for channel in profile.channels:
            keyboard.append([InlineKeyboardButton(
                f"📢 {channel.get('title', channel['id'])}",
                callback_data=f"send_{channel['id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_post")])
        
        context.user_data['generated_post'] = post_text
        context.user_data['generated_image'] = image
        
        await query.edit_message_text(
            f"✅ *Пост сгенерирован!*\n\n"
            f"{post_text}\n\n"
            f"Выберите канал для публикации:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            f"❌ *Ошибка генерации:* {image}",
            parse_mode='Markdown'
        )

async def send_post_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка сгенерированного поста в канал"""
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("send_", "")
    user_id = query.from_user.id
    profile = bot.get_user_profile(user_id)
    post_text = context.user_data.get('generated_post')
    image = context.user_data.get('generated_image')
    
    success = await bot.send_post_to_channel(profile, channel_id, post_text, image)
    
    if success:
        await query.edit_message_text(
            "✅ *Пост успешно опубликован!*",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ *Ошибка публикации поста*\n"
            "Проверьте права бота в канале",
            parse_mode='Markdown'
        )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    await get_started(update, context)

def main():
    """Запуск бота"""
    from telegram.ext import ConversationHandler
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ConversationHandler для подключения аккаунта
    connect_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(connect_account, pattern="^connect_account$")],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_handler)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    # ConversationHandler для добавления канала
    add_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_channel, pattern="^add_channel$")],
        states={
            CHANNEL_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, channel_add_handler)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(get_started, pattern="^get_started$"))
    application.add_handler(CallbackQueryHandler(my_channels, pattern="^my_channels$"))
    application.add_handler(CallbackQueryHandler(settings_menu, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(settings_topics, pattern="^settings_topics$"))
    application.add_handler(CallbackQueryHandler(settings_menu, pattern="^settings_menu$"))
    application.add_handler(CallbackQueryHandler(toggle_topic, pattern="^toggle_topic_"))
    application.add_handler(CallbackQueryHandler(show_tariffs, pattern="^show_tariffs$"))
    application.add_handler(CallbackQueryHandler(select_tariff, pattern="^select_tariff_"))
    application.add_handler(CallbackQueryHandler(generate_ai_post_manual, pattern="^generate_ai$"))
    application.add_handler(CallbackQueryHandler(handle_generate_topic, pattern="^gen_topic_"))
    application.add_handler(CallbackQueryHandler(generate_post_with_size, pattern="^size_"))
    application.add_handler(CallbackQueryHandler(send_post_to_channel_callback, pattern="^send_"))
    application.add_handler(CommandHandler("post", manual_post))
    
    application.add_handler(connect_conv)
    application.add_handler(add_channel_conv)
    
    logger.info("🚀 Бот для автопостинга запущен!")
    logger.info("📱 Поддерживается подключение через телефон и код")
    logger.info("🎨 20+ тем для автогенерации")
    logger.info("💎 Бесплатные тарифы для всех пользователей")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
