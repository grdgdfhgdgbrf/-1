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

# ==================== ТОКЕН БОТА ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== GIGACHAT API НАСТРОЙКИ ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== ТАРИФЫ (ВСЕ БЕСПЛАТНЫЕ) ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "price": 0,
        "channels": 3,
        "posts_per_day": 50,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "description": "Полный доступ ко всем функциям"
    },
    "plus": {
        "name": "💎 Плюс",
        "price": 0,
        "channels": 10,
        "posts_per_day": 200,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "description": "Расширенный пакет"
    },
    "pro": {
        "name": "👑 Про",
        "price": 0,
        "channels": 999,
        "posts_per_day": 500,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "description": "Максимальные возможности"
    }
}

# ==================== 20 ТЕМ ДЛЯ ПОСТИНГА ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 AI Новости",
        "emoji": "🤖",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#AI #ИскусственныйИнтеллект #Нейросети"
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "description": "Криптовалюты и блокчейн",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн"
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "description": "NFT и цифровое искусство",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная"
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram",
        "hashtags": "#Telegram #Мессенджер #НовостиTelegram"
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес и предпринимательство",
        "hashtags": "#Бизнес #Предпринимательство #Стартап"
    },
    "technology": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "description": "Технологические новости",
        "hashtags": "#Технологии #Гаджеты #Инновации"
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "hashtags": "#Наука #Открытия #Исследования"
    },
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "description": "Здоровье и благополучие",
        "hashtags": "#Здоровье #ЗОЖ #Медицина"
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация"
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Реклама"
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #UXUI #Креатив"
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "description": "IT и разработка",
        "hashtags": "#Программирование #Код #IT"
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровая индустрия",
        "hashtags": "#Игры #Гейминг #Видеоигры"
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Кино и сериалы",
        "hashtags": "#Кино #Сериалы #Фильмы"
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Плейлист"
    },
    "sports": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные события",
        "hashtags": "#Спорт #Футбол #Тренировки"
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Туризм #Страны"
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Кулинария и рецепты",
        "hashtags": "#Кулинария #Рецепты #Еда"
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "description": "Образование и обучение",
        "hashtags": "#Образование #Учеба #Знания"
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Вдохновение"
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "🔹 Мини", "chars": 200, "emoji": "🔹", "desc": "Коротко и ясно"},
    "short": {"name": "🔸 Короткий", "chars": 400, "emoji": "🔸", "desc": "Оптимально для ленты"},
    "medium": {"name": "📄 Средний", "chars": 700, "emoji": "📄", "desc": "Развернутый пост"},
    "long": {"name": "📚 Длинный", "chars": 1000, "emoji": "📚", "desc": "Максимум информации"},
    "extra": {"name": "✨ Макси", "chars": 1500, "emoji": "✨", "desc": "Полноценная статья"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class Channel:
    channel_id: str
    channel_name: str
    added_by: int
    added_at: float
    is_active: bool = True

@dataclass
class AutoPostConfig:
    channel_id: str
    theme: str
    size: str
    interval_minutes: int
    is_active: bool = True
    last_post: float = 0
    next_post: float = 0

@dataclass
class UserData:
    user_id: int
    username: str
    tariff: str = "free"
    channels: List[str] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    auto_configs: Dict[str, AutoPostConfig] = field(default_factory=dict)
    
    def reset_daily(self):
        today = time.time()
        if today - self.last_reset >= 86400:
            self.posts_today = 0
            self.last_reset = today
            return True
        return False
    
    def can_post(self) -> bool:
        self.reset_daily()
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return self.posts_today < tariff["posts_per_day"]
    
    def add_post(self):
        self.posts_today += 1

# ==================== ОСНОВНОЙ КЛАСС БОТА ====================
class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[dict] = []
        
    def load_data(self):
        try:
            with open("bot_data.json", "r") as f:
                data = json.load(f)
                for user_id, user_data in data.get("users", {}).items():
                    user = UserData(**{k: v for k, v in user_data.items() if k != "auto_configs"})
                    for ch_id, cfg in user_data.get("auto_configs", {}).items():
                        user.auto_configs[ch_id] = AutoPostConfig(**cfg)
                    self.users[int(user_id)] = user
                self.post_history = data.get("post_history", [])
                logger.info(f"Загружено {len(self.users)} пользователей")
        except FileNotFoundError:
            logger.info("Нет сохраненных данных, создаем новые")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    def save_data(self):
        try:
            data = {
                "users": {},
                "post_history": self.post_history
            }
            for user_id, user in self.users.items():
                data["users"][str(user_id)] = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "tariff": user.tariff,
                    "channels": user.channels,
                    "posts_today": user.posts_today,
                    "last_reset": user.last_reset,
                    "auto_configs": {
                        ch_id: {
                            "channel_id": cfg.channel_id,
                            "theme": cfg.theme,
                            "size": cfg.size,
                            "interval_minutes": cfg.interval_minutes,
                            "is_active": cfg.is_active,
                            "last_post": cfg.last_post,
                            "next_post": cfg.next_post
                        } for ch_id, cfg in user.auto_configs.items()
                    }
                }
            with open("bot_data.json", "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    def get_user(self, user_id: int, username: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(user_id=user_id, username=username)
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
                        logger.info("Токен GigaChat получен")
                        return self.api_token
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
        return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        if not token:
            return self.get_fallback_post(theme, size)
        
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""Ты профессиональный контент-мейкер. Напиши интересный пост на тему "{theme_config['name']}".

Требования:
- Длина: примерно {size_config['chars']} символов
- Используй красивые эмодзи в начале и в тексте
- Добавь вопрос к аудитории в конце для вовлечения
- Закончи пост хэштегами: {theme_config['hashtags']}
- Пиши на русском, грамотно, с душой
- Пост должен быть полезным и интересным

Примерный план:
1. Яркий заголовок или начало
2. Основной контент (факты, советы, новости)
3. Вопрос к подписчикам
4. Хэштеги

Напиши сразу готовый пост, без лишних комментариев:"""
        
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
                        if "choices" in data and data["choices"]:
                            content = data["choices"][0]["message"]["content"]
                            # Обрезаем если слишком длинный
                            if len(content) > size_config['chars'] + 200:
                                content = content[:size_config['chars']]
                            return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self.get_fallback_post(theme, size)
    
    def get_fallback_post(self, theme: str, size: str) -> str:
        fallbacks = {
            "ai_news": f"🤖 Искусственный интеллект меняет мир!\n\nКаждый день появляются новые модели нейросетей. AI уже умеет писать тексты, создавать изображения и даже программировать.\n\nА как вы используете AI в своей жизни?\n\n{POSTING_THEMES[theme]['hashtags']}",
            "crypto": f"🪙 Криптовалюты продолжают завоевывать мир!\n\nБиткоин, Эфириум и тысячи других монет создают новую экономику.\n\nУже инвестируете в крипту или только присматриваетесь?\n\n{POSTING_THEMES[theme]['hashtags']}",
            "nft": f"🎨 NFT - цифровое искусство будущего\n\nУникальные токены меняют представление о владении цифровыми активами. Художники со всего мира продают свои работы за миллионы!\n\nКакое NFT вы бы хотели создать?\n\n{POSTING_THEMES[theme]['hashtags']}",
            "telegram": f"📱 Telegram - больше чем мессенджер\n\nБоты, каналы, группы, Stories - здесь есть всё! А вы знали все возможности?\n\nКакая функция Telegram для вас самая полезная?\n\n{POSTING_THEMES[theme]['hashtags']}",
        }
        return fallbacks.get(theme, f"{POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\nНовый интересный пост!\n\nА что вы думаете на эту тему?\n\n{POSTING_THEMES[theme]['hashtags']}")
    
    async def post_to_channel(self, bot, channel_id: str, theme: str, size: str, is_auto: bool = False) -> bool:
        content = await self.generate_post(theme, size)
        
        # Форматируем пост красиво
        theme_emoji = POSTING_THEMES[theme]['emoji']
        formatted_post = f"{theme_emoji} *{POSTING_THEMES[theme]['name']}*\n\n{content}"
        
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=formatted_post,
                parse_mode='Markdown'
            )
            
            self.post_history.append({
                "channel_id": channel_id,
                "theme": theme,
                "size": size,
                "content": content[:100],
                "timestamp": time.time(),
                "auto": is_auto
            })
            self.save_data()
            logger.info(f"Пост отправлен в {channel_id} на тему {theme}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в {channel_id}: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="select_size")],
        [InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(page=0):
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
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav_row.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"themes_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(prefix="size"):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} - {size['desc']} ({size['chars']} симв.)",
            callback_data=f"{prefix}_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id):
    user = bot.get_user(user_id)
    keyboard = []
    
    for ch_id in user.channels:
        keyboard.append([InlineKeyboardButton(f"📢 Канал {ch_id[:10]}...", callback_data=f"channel_{ch_id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_config_keyboard(channel_id: str, config):
    status = "✅ Вкл" if config.is_active else "⏸ Выкл"
    theme = POSTING_THEMES.get(config.theme, {}).get('name', config.theme)
    size = POST_SIZES.get(config.size, {}).get('name', config.size)
    
    keyboard = [
        [InlineKeyboardButton(f"🎨 Тема: {theme}", callback_data=f"auto_theme_{channel_id}")],
        [InlineKeyboardButton(f"📏 Размер: {size}", callback_data=f"auto_size_{channel_id}")],
        [InlineKeyboardButton(f"⏱ Интервал: {config.interval_minutes} мин", callback_data=f"auto_interval_{channel_id}")],
        [InlineKeyboardButton(f"🔄 Статус: {status}", callback_data=f"auto_toggle_{channel_id}")],
        [InlineKeyboardButton("📤 Отправить тестовый пост", callback_data=f"test_post_{channel_id}")],
        [InlineKeyboardButton("🗑 Удалить настройку", callback_data=f"auto_delete_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    user_data = bot.get_user(user.id, user.username or "")
    
    welcome_text = f"""🚀 *Добро пожаловать, {user.first_name}!*

✨ *Бот для автопостинга с ИИ*

📝 *Возможности:*
• 🎨 20 разных тем для постов
• 📏 5 размеров постов
• 🤖 Генерация через GigaChat AI
• ⏰ Автоматический постинг
• 💰 Все тарифы БЕСПЛАТНЫЕ!
• 🔄 Перепост из других каналов

💡 *Как начать:*
1️⃣ Добавьте бота в канал как администратора
2️⃣ Нажмите "➕ Добавить канал" в меню
3️⃣ Настройте автопостинг

👇 *Выберите действие:*"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=await get_main_keyboard())

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Перешлите ЛЮБОЕ сообщение из канала сюда\n\n"
        "Или отправьте username канала (например @channel)\n"
        "Или ID канала (например -1001234567890)\n\n"
        "Бот автоматически определит ваш канал!",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_channel'):
        return
    
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    text = update.message.text.strip()
    
    tariff = TARIFFS[user.tariff]
    if len(user.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ Лимит каналов для вашего тарифа: {tariff['channels']}\n"
            f"Удалите один из каналов или выберите другой тариф"
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
    elif text.startswith('@'):
        try:
            chat = await context.bot.get_chat(text)
            channel_id = str(chat.id)
            channel_name = chat.title
        except:
            await update.message.reply_text("❌ Не найден канал с таким username")
            return
    elif text.startswith('-100'):
        channel_id = text
        try:
            chat = await context.bot.get_chat(int(text))
            channel_name = chat.title
        except:
            channel_name = "Канал"
    else:
        await update.message.reply_text("❌ Перешлите сообщение из канала или укажите правильный ID/username")
        return
    
    # Проверяем, не добавлен ли уже
    if channel_id in user.channels:
        await update.message.reply_text("❌ Этот канал уже добавлен!")
        context.user_data['awaiting_channel'] = False
        return
    
    # Проверяем, что бот админ в канале
    try:
        chat_member = await context.bot.get_chat_member(int(channel_id), context.bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Бот не является администратором канала! Добавьте бота как администратора.")
            return
    except:
        await update.message.reply_text("❌ Не удалось проверить права бота. Убедитесь, что бот добавлен в канал.")
        return
    
    user.channels.append(channel_id)
    bot.save_data()
    
    await update.message.reply_text(
        f"✅ *Канал успешно добавлен!*\n\n"
        f"📢 Название: {channel_name}\n"
        f"📊 Каналов: {len(user.channels)}/{tariff['channels']}\n\n"
        f"🎯 Теперь настройте автопостинг в меню",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = False

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    if not user.channels:
        await query.edit_message_text(
            "📢 *У вас пока нет добавленных каналов*\n\n"
            "Нажмите '➕ Добавить канал' в меню",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_main")
            ]])
        )
        return
    
    text = f"📋 *Ваши каналы* ({len(user.channels)}/{tariff['channels']})\n\n"
    
    for ch_id in user.channels:
        try:
            chat = await context.bot.get_chat(int(ch_id))
            text += f"📢 *{chat.title}*\n"
            text += f"🆔 `{ch_id}`\n"
            
            if ch_id in user.auto_configs:
                cfg = user.auto_configs[ch_id]
                theme = POSTING_THEMES.get(cfg.theme, {}).get('name', '-')
                size = POST_SIZES.get(cfg.size, {}).get('name', '-')
                status = "✅" if cfg.is_active else "⏸"
                text += f"🎨 Автопостинг: {status} | {theme} | {size} | каждые {cfg.interval_minutes} мин\n"
            else:
                text += f"⚙️ Автопостинг: ❌ не настроен\n"
            text += "\n"
        except:
            text += f"⚠️ Канал {ch_id} - недоступен\n\n"
    
    keyboard = []
    for ch_id in user.channels:
        keyboard.append([InlineKeyboardButton(f"⚙️ Настроить канал", callback_data=f"config_channel_{ch_id}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def config_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("config_channel_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    config = user.auto_configs.get(channel_id)
    if not config:
        config = AutoPostConfig(
            channel_id=channel_id,
            theme="ai_news",
            size="medium",
            interval_minutes=60
        )
        user.auto_configs[channel_id] = config
        bot.save_data()
    
    keyboard = await get_auto_config_keyboard(channel_id, config)
    await query.edit_message_text(
        f"⚙️ *Настройка автопостинга*\n\n"
        f"Канал настроен и готов к работе!\n"
        f"Выберите параметры для настройки:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов*\n\n"
            "Сначала добавьте канал: нажмите '➕ Добавить канал'",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_main")
            ]])
        )
        return
    
    text = "🤖 *Настройка автопостинга*\n\nВыберите канал для настройки:\n\n"
    
    for ch_id in user.channels:
        try:
            chat = await context.bot.get_chat(int(ch_id))
            config = user.auto_configs.get(ch_id)
            status = "✅" if config and config.is_active else "⏸" if config else "⚪"
            text += f"{status} *{chat.title}*\n"
        except:
            text += f"⚠️ Канал {ch_id[:10]}...\n"
    
    keyboard = []
    for ch_id in user.channels:
        try:
            chat = await context.bot.get_chat(int(ch_id))
            keyboard.append([InlineKeyboardButton(f"⚙️ {chat.title}", callback_data=f"config_channel_{ch_id}")])
        except:
            keyboard.append([InlineKeyboardButton(f"⚠️ Канал", callback_data=f"config_channel_{ch_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def auto_theme_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_theme_", "")
    context.user_data['config_channel'] = channel_id
    
    keyboard = await get_themes_keyboard()
    await query.edit_message_text(
        f"🎨 *Выберите тему для автопостинга*\n\n"
        f"Тема определяет стиль и содержание постов:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def auto_size_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_size_", "")
    context.user_data['config_channel'] = channel_id
    
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} - {size['desc']}",
            callback_data=f"auto_set_size_{channel_id}_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"config_channel_{channel_id}")])
    
    await query.edit_message_text(
        f"📏 *Выберите размер постов*\n\n"
        f"Размер влияет на длину генерируемого поста:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def auto_interval_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_interval_", "")
    context.user_data['interval_channel'] = channel_id
    
    keyboard = [
        [InlineKeyboardButton("30 минут", callback_data=f"set_interval_{channel_id}_30")],
        [InlineKeyboardButton("1 час", callback_data=f"set_interval_{channel_id}_60")],
        [InlineKeyboardButton("2 часа", callback_data=f"set_interval_{channel_id}_120")],
        [InlineKeyboardButton("4 часа", callback_data=f"set_interval_{channel_id}_240")],
        [InlineKeyboardButton("6 часов", callback_data=f"set_interval_{channel_id}_360")],
        [InlineKeyboardButton("12 часов", callback_data=f"set_interval_{channel_id}_720")],
        [InlineKeyboardButton("24 часа", callback_data=f"set_interval_{channel_id}_1440")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"config_channel_{channel_id}")]
    ]
    
    await query.edit_message_text(
        f"⏱ *Выберите интервал между постами*\n\n"
        f"Чем меньше интервал, тем чаще будут выходить посты:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[3]
    interval = int(parts[4])
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id in user.auto_configs:
        user.auto_configs[channel_id].interval_minutes = interval
        bot.save_data()
        await query.edit_message_text(f"✅ Интервал установлен: {interval} минут")
        
        # Возвращаемся к настройкам
        config = user.auto_configs[channel_id]
        keyboard = await get_auto_config_keyboard(channel_id, config)
        await query.edit_message_text(
            f"⚙️ *Настройка автопостинга*\n\nИнтервал обновлен!",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await query.edit_message_text("❌ Ошибка: канал не найден")

async def auto_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_toggle_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id in user.auto_configs:
        user.auto_configs[channel_id].is_active = not user.auto_configs[channel_id].is_active
        bot.save_data()
        
        status = "включен" if user.auto_configs[channel_id].is_active else "выключен"
        await query.answer(f"Автопостинг {status}!")
        
        config = user.auto_configs[channel_id]
        keyboard = await get_auto_config_keyboard(channel_id, config)
        await query.edit_message_reply_markup(reply_markup=keyboard)

async def auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_delete_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id in user.auto_configs:
        del user.auto_configs[channel_id]
        bot.save_data()
        await query.edit_message_text("✅ Настройки автопостинга удалены!")
        
        # Показываем меню каналов
        await my_channels(update, context)

async def test_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("test_post_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if channel_id not in user.channels:
        await query.edit_message_text("❌ Канал не найден в вашем списке")
        return
    
    config = user.auto_configs.get(channel_id)
    if not config:
        await query.edit_message_text("❌ Сначала настройте автопостинг")
        return
    
    await query.edit_message_text("🎲 Генерирую тестовый пост...")
    
    success = await bot.post_to_channel(context.bot, channel_id, config.theme, config.size)
    
    if success:
        user.add_post()
        bot.save_data()
        await query.edit_message_text("✅ Тестовый пост успешно отправлен!")
        
        # Возвращаемся к настройкам
        config = user.auto_configs[channel_id]
        keyboard = await get_auto_config_keyboard(channel_id, config)
        await query.edit_message_text(
            f"⚙️ *Настройка автопостинга*\n\nТестовый пост отправлен!",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await query.edit_message_text("❌ Ошибка при отправке тестового поста")

async def select_theme_for_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_themes_keyboard()
    await query.edit_message_text(
        "🎨 *Выберите тему для поста*\n\n"
        "Пост будет создан сразу после выбора:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def select_size_for_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    theme = context.user_data.get('selected_theme')
    if not theme:
        await query.edit_message_text("❌ Сначала выберите тему")
        return
    
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} - {size['desc']}",
            callback_data=f"post_size_{theme}_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="select_theme")])
    
    await query.edit_message_text(
        f"📏 *Выберите размер поста*\n\n"
        f"Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def create_and_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    theme = parts[2]
    size = parts[3]
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await query.edit_message_text("❌ Сначала добавьте канал через 'Мои каналы'")
        return
    
    if not user.can_post():
        await query.edit_message_text(f"❌ Достигнут лимит постов на сегодня! Завтра лимит обновится.")
        return
    
    await query.edit_message_text(f"🎲 Генерирую пост на тему {POSTING_THEMES[theme]['emoji']}...")
    
    # Отправляем в первый канал из списка
    channel_id = user.channels[0]
    success = await bot.post_to_channel(context.bot, channel_id, theme, size)
    
    if success:
        user.add_post()
        bot.save_data()
        await query.edit_message_text("✅ Пост успешно опубликован!")
    else:
        await query.edit_message_text("❌ Ошибка при публикации")

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await query.edit_message_text("❌ Сначала добавьте канал через 'Мои каналы'")
        return
    
    if not user.can_post():
        await query.edit_message_text(f"❌ Достигнут лимит постов на сегодня!")
        return
    
    theme = random.choice(list(POSTING_THEMES.keys()))
    size = random.choice(list(POST_SIZES.keys()))
    
    await query.edit_message_text(f"🎲 Случайный пост!\n\nТема: {POSTING_THEMES[theme]['emoji']}\nРазмер: {POST_SIZES[size]['name']}\n\nГенерирую...")
    
    channel_id = user.channels[0]
    success = await bot.post_to_channel(context.bot, channel_id, theme, size)
    
    if success:
        user.add_post()
        bot.save_data()
        await query.edit_message_text("✅ Случайный пост опубликован!")
    else:
        await query.edit_message_text("❌ Ошибка при публикации")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    user.reset_daily()
    remaining = tariff["posts_per_day"] - user.posts_today
    
    text = f"""📊 *Ваша статистика*

👤 *Пользователь:* {user.username or user.user_id}
💎 *Тариф:* {tariff['name']}
📢 *Каналов:* {len(user.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {user.posts_today}/{tariff['posts_per_day']}
⏳ *Осталось постов:* {remaining}

🤖 *Автопостинг:*
"""
    
    auto_count = 0
    for ch_id, cfg in user.auto_configs.items():
        if cfg.is_active:
            auto_count += 1
            theme = POSTING_THEMES.get(cfg.theme, {}).get('name', '-')
            text += f"• Канал: {cfg.interval_minutes} мин, тема: {theme}\n"
    
    if auto_count == 0:
        text += "• Не настроен\n"
    
    text += f"\n📈 *Всего постов в боте:* {len(bot.post_history)}"
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    text = "💎 *Все тарифы БЕСПЛАТНЫЕ!*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        current = " ✅ (Активен)" if user.tariff == tariff_key else ""
        text += f"""
*{tariff['name']}{current}*
💰 Цена: {tariff['price']} руб/мес
📊 Каналов: {tariff['channels']}
📝 Постов/день: {tariff['posts_per_day']}
🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}
⏰ Расписание: {'✅' if tariff['can_schedule'] else '❌'}
🖼 Картинки: {'✅' if tariff['has_images'] else '❌'}
{tariff['description']}

"""
    
    keyboard = []
    for tariff_key in TARIFFS.keys():
        keyboard.append([InlineKeyboardButton(
            f"🎁 Активировать {TARIFFS[tariff_key]['name']}",
            callback_data=f"activate_tariff_{tariff_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def activate_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("activate_tariff_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    user.tariff = tariff_key
    bot.save_data()
    
    tariff = TARIFFS[tariff_key]
    await query.edit_message_text(
        f"✅ *Тариф успешно активирован!*\n\n"
        f"Ваш новый тариф: {tariff['name']}\n"
        f"📊 Каналов: {tariff['channels']}\n"
        f"📝 Постов в день: {tariff['posts_per_day']}\n\n"
        f"Наслаждайтесь использованием! 🚀",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")
        ]])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """🆘 *Помощь и инструкция*

📌 *Как пользоваться ботом:*

1️⃣ *Добавьте канал*
• Добавьте бота в канал как администратора
• Нажмите "Мои каналы" ➔ "Добавить канал"
• Перешлите сообщение из канала или введите ID

2️⃣ *Настройте автопостинг*
• Выберите канал в меню "Автопостинг"
• Установите тему, размер и интервал
• Включите автопостинг

3️⃣ *Создайте пост вручную*
• Выберите "Тема" ➔ выберите тему
• Выберите размер поста
• Пост отправится в ваш первый канал

🎲 *Случайный пост* - быстрый пост на случайную тему

💎 *Тарифы* - все тарифы БЕСПЛАТНЫЕ!

📊 *Статистика* - ваша активность и лимиты

❓ *Вопросы*
Если возникли проблемы, проверьте:
• Бот добавлен в канал как администратор
• У бота есть права на отправку сообщений
• Вы не превысили лимит постов

✨ *Все функции доступны бесплатно!*"""

    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return
    
    if data.startswith("theme_"):
        theme = data.replace("theme_", "")
        
        # Если выбрана тема для автопостинга
        if 'config_channel' in context.user_data:
            channel_id = context.user_data['config_channel']
            user_id = query.from_user.id
            user = bot.get_user(user_id)
            
            if channel_id in user.auto_configs:
                user.auto_configs[channel_id].theme = theme
                bot.save_data()
                
                config = user.auto_configs[channel_id]
                keyboard = await get_auto_config_keyboard(channel_id, config)
                await query.edit_message_text(
                    f"✅ Тема установлена: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text("❌ Ошибка: канал не найден")
            return
        
        # Для обычного поста
        context.user_data['selected_theme'] = theme
        await select_size_for_post(update, context)
        return
    
    if data.startswith("auto_set_size_"):
        parts = data.split("_")
        channel_id = parts[3]
        size = parts[4]
        
        user_id = query.from_user.id
        user = bot.get_user(user_id)
        
        if channel_id in user.auto_configs:
            user.auto_configs[channel_id].size = size
            bot.save_data()
            
            config = user.auto_configs[channel_id]
            keyboard = await get_auto_config_keyboard(channel_id, config)
            await query.edit_message_text(
                f"✅ Размер установлен: {POST_SIZES[size]['name']}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        return
    
    if data.startswith("post_size_"):
        await create_and_post(update, context)
        return

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard()
    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def auto_post_check(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для автопостинга"""
    bot.load_data()
    current_time = time.time()
    
    for user_id, user in bot.users.items():
        for channel_id, config in user.auto_configs.items():
            if not config.is_active:
                continue
            
            # Проверяем время следующего поста
            if config.next_post == 0:
                config.next_post = current_time + (config.interval_minutes * 60)
                continue
            
            if current_time >= config.next_post:
                if user.can_post():
                    logger.info(f"Автопостинг в канал {channel_id}")
                    success = await bot.post_to_channel(
                        context.bot, 
                        channel_id, 
                        config.theme, 
                        config.size,
                        is_auto=True
                    )
                    if success:
                        user.add_post()
                        config.last_post = current_time
                        config.next_post = current_time + (config.interval_minutes * 60)
                        bot.save_data()
                else:
                    logger.warning(f"У пользователя {user_id} лимит постов")

# ==================== ЗАПУСК ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(add_channel, pattern="^add_channel$"))
    application.add_handler(CallbackQueryHandler(my_channels, pattern="^my_channels$"))
    application.add_handler(CallbackQueryHandler(auto_posting_menu, pattern="^auto_posting$"))
    application.add_handler(CallbackQueryHandler(config_channel, pattern="^config_channel_"))
    application.add_handler(CallbackQueryHandler(auto_theme_select, pattern="^auto_theme_"))
    application.add_handler(CallbackQueryHandler(auto_size_select, pattern="^auto_size_"))
    application.add_handler(CallbackQueryHandler(auto_interval_set, pattern="^auto_interval_"))
    application.add_handler(CallbackQueryHandler(set_interval, pattern="^set_interval_"))
    application.add_handler(CallbackQueryHandler(auto_toggle, pattern="^auto_toggle_"))
    application.add_handler(CallbackQueryHandler(auto_delete, pattern="^auto_delete_"))
    application.add_handler(CallbackQueryHandler(test_post, pattern="^test_post_"))
    application.add_handler(CallbackQueryHandler(select_theme_for_post, pattern="^select_theme$"))
    application.add_handler(CallbackQueryHandler(select_size_for_post, pattern="^select_size$"))
    application.add_handler(CallbackQueryHandler(random_post, pattern="^random_post$"))
    application.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(tariffs_menu, pattern="^tariffs$"))
    application.add_handler(CallbackQueryHandler(activate_tariff, pattern="^activate_tariff_"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(handle_theme_selection, pattern="^(themes_page_|theme_|auto_set_size_|post_size_)"))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    
    # Фоновая задача для автопостинга
    application.job_queue.run_repeating(auto_post_check, interval=60, first=10)
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💎 Все тарифы бесплатные!")
    logger.info(f"⚙️ Автопостинг проверяется каждую минуту")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
