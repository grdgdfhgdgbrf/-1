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
        "name": "🌟 Базовый",
        "price": 0,
        "channels": 1,
        "posts_per_day": 50,
        "interval_min": 10,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "🟢"
    },
    "basic": {
        "name": "⭐ Стандарт",
        "price": 0,
        "channels": 5,
        "posts_per_day": 200,
        "interval_min": 5,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "🔵"
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 0,
        "channels": 20,
        "posts_per_day": 500,
        "interval_min": 3,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "🟣"
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels": 100,
        "posts_per_day": 2000,
        "interval_min": 1,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "color": "🔴"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 Новости AI",
        "emoji": "🤖",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#AI #ИскусственныйИнтеллект #НовостиAI",
        "prompt": "Ты журналист, пишущий об AI. Создай интересный и уникальный пост о последних новостях в мире искусственного интеллекта."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "description": "Новости криптовалют и блокчейна",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн",
        "prompt": "Ты крипто-аналитик. Создай уникальный пост о криптовалютах, блокчейне, DeFi, трендах рынка."
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "description": "Новости NFT и цифрового искусства",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная",
        "prompt": "Ты эксперт по NFT. Создай уникальный пост о NFT коллекциях, digital art, метавселенных."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram",
        "hashtags": "#Telegram #Мессенджер #Обновления",
        "prompt": "Ты блогер о Telegram. Создай уникальный пост о новых функциях Telegram, ботах, каналах."
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес новости и советы",
        "hashtags": "#Бизнес #Стартап #Предпринимательство",
        "prompt": "Ты бизнес-журналист. Создай уникальный пост о бизнесе, стартапах, инвестициях, успешных кейсах."
    },
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "description": "Технологические новости",
        "hashtags": "#Технологии #Гаджеты #Инновации",
        "prompt": "Ты техноблогер. Создай уникальный пост о новых технологиях, гаджетах, изобретениях."
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "hashtags": "#Наука #Открытия #Исследования",
        "prompt": "Ты научный журналист. Создай уникальный пост о научных открытиях и исследованиях."
    },
    "health": {
        "name": "💊 Здоровье",
        "emoji": "💊",
        "description": "Здоровье и медицина",
        "hashtags": "#Здоровье #Медицина #ЗОЖ",
        "prompt": "Ты медицинский блогер. Создай уникальный полезный пост о здоровье."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация",
        "prompt": "Ты психолог. Создай уникальный полезный пост по психологии и саморазвитию."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Реклама",
        "prompt": "Ты маркетолог. Создай уникальный пост о маркетинге, SMM, рекламе."
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #Креатив #Вдохновение",
        "prompt": "Ты дизайнер. Создай уникальный вдохновляющий пост о дизайне."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "description": "IT и разработка",
        "hashtags": "#Программирование #IT #Код",
        "prompt": "Ты разработчик. Создай уникальный полезный пост о программировании."
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровые новости",
        "hashtags": "#Игры #Гейминг #Видеоигры",
        "prompt": "Ты игровой журналист. Создай уникальный пост об играх и гейминге."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Новости кино",
        "hashtags": "#Кино #Фильмы #Сериалы",
        "prompt": "Ты кинокритик. Создай уникальный пост о новинках кино и сериалов."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Хиты",
        "prompt": "Ты музыкальный обозреватель. Создай уникальный пост о музыке."
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости",
        "hashtags": "#Спорт #Футбол #Баскетбол",
        "prompt": "Ты спортивный журналист. Создай уникальный пост о спорте."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Туризм #Отдых",
        "prompt": "Ты тревел-блогер. Создай уникальный пост о путешествиях."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Кулинария и рецепты",
        "hashtags": "#Кулинария #Рецепты #Еда",
        "prompt": "Ты кулинарный блогер. Создай уникальный пост о еде и рецептах."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "description": "Образование и обучение",
        "hashtags": "#Образование #Учеба #Знания",
        "prompt": "Ты педагог. Создай уникальный полезный пост об образовании."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Вдохновение",
        "prompt": "Ты мотивационный спикер. Создай уникальный вдохновляющий пост."
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
            with open("subscriptions.json", "r") as f:
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
            with open("subscriptions.json", "w") as f:
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

ВАЖНО: Создай УНИКАЛЬНЫЙ пост, который не похож на предыдущие.

Требования:
- Длина: примерно {size_config['chars']} символов
- Используй красивые эмодзи для оформления
- Добавь в конце: {theme_config['hashtags']}
- Пиши на русском языке, интересно и вовлекающе
- Добавь вопрос к подписчикам для комментариев
- Пост должен быть полезным или вдохновляющим

Структура:
1. Яркий заголовок с эмодзи
2. Основной контент
3. Вопрос к аудитории
4. Хэштеги"""
        
        if not token:
            return self._get_fallback_post(theme, size_config['chars'])
        
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
                        "max_tokens": 2000
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                            return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme, size_config['chars'])
    
    def _get_fallback_post(self, theme: str, chars: int) -> str:
        fallbacks = {
            "ai_news": f"🤖 *ИИ меняет мир!*\n\nИскусственный интеллект продолжает удивлять нас новыми возможностями. Какие технологии будущего вас впечатляют больше всего?\n\n👇 Делитесь мнением в комментариях!\n\n{POSTING_THEMES['ai_news']['hashtags']}",
            "crypto": f"🪙 *Крипто-новости*\n\nРынок криптовалют не стоит на месте! Следите за трендами и не упустите возможности.\n\nА вы инвестируете в крипту? 💎\n\n{POSTING_THEMES['crypto']['hashtags']}",
            "nft": f"🎨 *NFT - цифровое искусство*\n\nNFT открывают новые горизонты для творчества! У вас есть своя NFT коллекция?\n\nРасскажите в комментариях! 🖼️\n\n{POSTING_THEMES['nft']['hashtags']}",
        }
        return fallbacks.get(theme, f"✨ *{POSTING_THEMES[theme]['name']}*\n\nНовый интересный пост! А что вы думаете по этой теме?\n\n👇 Ваше мнение в комментариях!\n\n{POSTING_THEMES[theme]['hashtags']}")
    
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
📅 {timestamp} | #{self.post_counter}
💬 Ждем ваши комментарии! 
🚀 Пост создан с помощью AI
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
            logger.info(f"✅ Пост отправлен в канал {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False

bot = PostingBot()

# ==================== КРАСИВЫЕ КЛАВИАТУРЫ ====================
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
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
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
• 📝 Генерация уникальных постов через ИИ
• 🎨 20 разных тематик на выбор
• ⏱ Автопостинг от 10 секунд!
• 📏 5 размеров постов
• 🔄 Перепост из других каналов
• 💰 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*

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
        "📌 *Инструкция:*\n\n"
        "1️⃣ *Добавьте бота в канал*\n"
        "   Как АДМИНИСТРАТОРА!\n\n"
        "2️⃣ *Перешлите ЛЮБОЕ сообщение*\n"
        "   Из канала СЮДА\n\n"
        "3️⃣ *Или отправьте ID канала:*\n"
        "   @username или -100xxxxxx\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ *После добавления* вы сможете\n"
        "настроить автопостинг!\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений для добавления канала"""
    if not context.user_data.get('awaiting_channel'):
        return
    
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    # Проверка лимита каналов
    if len(sub.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ *Лимит каналов достигнут!*\n\n"
            f"📊 Ваш тариф: {tariff['name']}\n"
            f"📢 Максимум каналов: {tariff['channels']}\n\n"
            f"💡 Используйте /tariffs для просмотра тарифов",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_channel'] = False
        return
    
    channel_id = None
    channel_name = None
    
    # Проверяем пересланное сообщение
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
        logger.info(f"Получен пересланный канал: {channel_id} - {channel_name}")
    
    # Проверяем текстовый ввод (username)
    elif update.message.text:
        text = update.message.text.strip()
        if text.startswith('@'):
            try:
                chat = await context.bot.get_chat(text)
                channel_id = str(chat.id)
                channel_name = chat.title
                logger.info(f"Получен username канала: {channel_id} - {channel_name}")
            except Exception as e:
                logger.error(f"Ошибка получения чата по username: {e}")
        
        elif text.startswith('-100') or text.isdigit():
            try:
                chat_id = int(text)
                chat = await context.bot.get_chat(chat_id)
                channel_id = str(chat.id)
                channel_name = chat.title
                logger.info(f"Получен ID канала: {channel_id} - {channel_name}")
            except Exception as e:
                logger.error(f"Ошибка получения чата по ID: {e}")
    
    if channel_id:
        # Проверяем, есть ли уже такой канал
        exists = False
        for ch in sub.channels:
            if ch.get('id') == channel_id:
                exists = True
                break
        
        if not exists:
            # Проверяем, добавлен ли бот в канал
            try:
                bot_member = await context.bot.get_chat_member(chat_id=int(channel_id), user_id=context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "⚠️ *Бот не является администратором канала!*\n\n"
                        "Пожалуйста, добавьте бота в канал как АДМИНИСТРАТОРА\n"
                        "и попробуйте снова.",
                        parse_mode='Markdown'
                    )
                    return
            except Exception as e:
                logger.error(f"Ошибка проверки прав бота: {e}")
                await update.message.reply_text(
                    "⚠️ *Не удалось проверить права бота*\n\n"
                    "Убедитесь, что бот добавлен в канал как администратор.",
                    parse_mode='Markdown'
                )
                return
            
            sub.channels.append({
                "id": channel_id,
                "name": channel_name
            })
            bot.save_data()
            
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ *КАНАЛ ДОБАВЛЕН!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📢 *Название:* {channel_name}\n"
                f"🆔 *ID:* `{channel_id}`\n\n"
                f"📊 *Ваши каналы:* {len(sub.channels)}/{tariff['channels']}\n\n"
                f"🎯 *Что дальше?*\n"
                f"• Нажмите *«Настройка автопостинга»*\n"
                f"• Выберите тему и размер постов\n"
                f"• Установите интервал публикации\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Этот канал уже добавлен!*\n\n"
                "Используйте /my_channels для просмотра",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "❌ *Не удалось определить канал*\n\n"
            "Попробуйте один из способов:\n\n"
            "1️⃣ *Перешлите сообщение* из канала\n"
            "2️⃣ *Отправьте username* канала (с @)\n"
            "3️⃣ *Отправьте ID* канала (число)",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['awaiting_channel'] = False

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
        is_configured = ch_id in sub.auto_posts
        status = "✅" if is_configured and sub.auto_posts[ch_id].is_active else "⚙️"
        button_text = f"{status} {ch.get('name', 'Канал')[:30]}"
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
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            channel_name = ch.get('name', 'Канал')
            break
    
    config = sub.auto_posts.get(channel_id)
    
    text = f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"⚙️ *НАСТРОЙКА КАНАЛА*\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📢 *Канал:* {channel_name}\n"
    text += f"🆔 *ID:* `{channel_id}`\n\n"
    
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
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"set_theme_{channel_id}")],
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
    keyboard = await get_themes_keyboard()
    await query.edit_message_text(
        "🎨 *Выберите тему для автопостинга:*\n\n"
        "Тема влияет на содержание и стиль постов",
        parse_mode='Markdown',
        reply_markup=keyboard
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
        "✨ *Доступные интервалы:*",
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
            theme=theme,
            size="medium",
            interval_seconds=300
        )
    else:
        sub.auto_posts[channel_id].theme = theme
    
    bot.save_data()
    
    await query.edit_message_text(
        f"✅ *Тема выбрана!*\n\n"
        f"{POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\n"
        f"📝 *Описание:* {POSTING_THEMES[theme]['description']}\n\n"
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
        f"Теперь выберите интервал публикации:",
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
            theme="ai_news",
            size="medium",
            interval_seconds=interval
        )
    else:
        sub.auto_posts[channel_id].interval_seconds = interval
    
    sub.auto_posts[channel_id].is_active = True
    sub.auto_posts[channel_id].last_post = time.time()
    
    bot.save_data()
    
    if interval < 60:
        interval_text = f"{interval} сек"
    elif interval < 3600:
        interval_text = f"{interval//60} мин"
    else:
        interval_text = f"{interval//3600} ч"
    
    # Запускаем автопостинг
    await start_auto_posting(context, user_id, channel_id)
    
    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 *АВТОПОСТИНГ НАСТРОЕН!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ *Параметры:*\n"
        f"🎨 Тема: {POSTING_THEMES[sub.auto_posts[channel_id].theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[sub.auto_posts[channel_id].size]['name']}\n"
        f"⏱ Интервал: {interval_text}\n\n"
        f"🤖 Бот будет автоматически публиковать посты!\n"
        f"🔄 Статус: АКТИВЕН\n\n"
        f"💡 *Чтобы остановить*, зайдите в настройки канала\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )

async def start_auto_posting(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: str):
    """Запуск автопостинга для канала"""
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
        remaining = TARIFFS[sub.tariff]["posts_per_day"] - sub.posts_today
        await query.edit_message_text(
            f"⚠️ *Лимит постов на сегодня исчерпан!*\n\n"
            f"📊 Осталось: 0/{TARIFFS[sub.tariff]['posts_per_day']}",
            parse_mode='Markdown'
        )
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    await query.edit_message_text(
        f"🎲 *Генерация поста...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[random_theme]['emoji']} {POSTING_THEMES[random_theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[random_size]['name']}\n\n"
        f"⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    success = await bot.format_and_send_post(context, sub.channels[0]['id'], random_theme, random_size)
    
    if success:
        await query.edit_message_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"📊 Осталось постов сегодня: {sub.get_remaining_posts() - 1}",
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
{'⚠️ Достигнут лимит!' if len(sub.channels) >= tariff['channels'] else '✅ Можно добавить еще'}

━━━━━━━━━━━━━━━━━━━━━
📝 *ПОСТЫ*
📊 Сегодня: {sub.posts_today}/{tariff['posts_per_day']}
⏳ Осталось: {remaining if remaining > 0 else 0}
🔄 Сброс через: {reset_hours}ч {reset_minutes}мин

━━━━━━━━━━━━━━━━━━━━━
🤖 *АВТОПОСТИНГ*
⚙️ Активных настроек: {len([c for c in sub.auto_posts.values() if c.is_active])}
⏱ Минимальный интервал: {tariff['interval_min']} сек

━━━━━━━━━━━━━━━━━━━━━
✨ *Все тарифы БЕСПЛАТНЫЕ!*
🎯 Используйте все возможности

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
├ 📢 Каналов: 1
├ 📝 Постов/день: 50
├ ⏱ Мин. интервал: 10 сек
└ 🎨 Картинки: Да

⭐ *СТАНДАРТ* - 0₽  
├ 📢 Каналов: 5
├ 📝 Постов/день: 200
├ ⏱ Мин. интервал: 5 сек
└ 🎨 Картинки: Да

💎 *ПРОФЕССИОНАЛЬНЫЙ* - 0₽
├ 📢 Каналов: 20
├ 📝 Постов/день: 500
├ ⏱ Мин. интервал: 3 сек
└ 🎨 Картинки: Да

👑 *ПРЕМИУМ* - 0₽
├ 📢 Каналов: 100
├ 📝 Постов/день: 2000
├ ⏱ Мин. интервал: 1 сек
└ 🎨 Картинки: Да

━━━━━━━━━━━━━━━━━━━━━
✨ *ВСЕ ФУНКЦИИ ДОСТУПНЫ!*
🎯 Просто добавьте канал и настройте

━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """━━━━━━━━━━━━━━━━━━━━━
🆘 *ПОМОЩЬ И ИНСТРУКЦИЯ*
━━━━━━━━━━━━━━━━━━━━━

📌 *БЫСТРЫЙ СТАРТ:*

1️⃣ *Добавьте канал*
   → Нажмите «📢 Добавить канал»
   → Добавьте бота в канал (админ)
   → Перешлите сообщение из канала

2️⃣ *Настройте автопостинг*
   → Нажмите «🤖 Настройка автопостинга»
   → Выберите канал
   → Выберите ТЕМУ, РАЗМЕР, ИНТЕРВАЛ
   → Запустите автопостинг!

━━━━━━━━━━━━━━━━━━━━━
🎯 *ВОЗМОЖНОСТИ:*

• 20+ тем на выбор
• 5 размеров постов
• Интервалы от 10 секунд!
• Генерация через AI (GigaChat)
• Уникальные посты без повторов
• Красивое оформление

━━━━━━━━━━━━━━━━━━━━━
💡 *СОВЕТЫ:*

• Используйте «Случайный пост»
• Проверяйте статистику
• Все тарифы БЕСПЛАТНЫЕ!

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
                f"❌ Минимальный интервал для вашего тарифа: {tariff['interval_min']} сек\n"
                f"Установите больший интервал",
                parse_mode='Markdown'
            )
            return
        
        if channel_id not in sub.auto_posts:
            sub.auto_posts[channel_id] = AutoPostConfig(
                channel_id=channel_id,
                channel_name="",
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
            f"🤖 Автопостинг АКТИВЕН\n\n"
            f"Используйте /menu для управления",
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
            "🎨 *Выберите тему:*\n\nТема влияет на содержание постов",
            parse_mode='Markdown',
            reply_markup=await get_themes_keyboard()
        )
    elif data == "select_size":
        await query.edit_message_text(
            "📏 *Выберите размер поста:*\n\nРазмер влияет на длину текста",
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
    
    # Обработчики сообщений (ВАЖНО: порядок имеет значение!)
    application.add_handler(MessageHandler(filters.FORWARDED, handle_channel_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info("💰 ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!")
    logger.info("⏱ Интервалы от 10 секунд!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
