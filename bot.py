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
        "channels": 5,
        "posts_per_day": 100,
        "interval_min": 10,
        "color": "🟢"
    },
    "basic": {
        "name": "⭐ Стандарт",
        "price": 0,
        "channels": 15,
        "posts_per_day": 300,
        "interval_min": 5,
        "color": "🔵"
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 0,
        "channels": 50,
        "posts_per_day": 1000,
        "interval_min": 3,
        "color": "🟣"
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels": 999,
        "posts_per_day": 5000,
        "interval_min": 1,
        "color": "🔴"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {"name": "🤖 Новости AI", "emoji": "🤖", "description": "Новости искусственного интеллекта", "hashtags": "#AI #ИскусственныйИнтеллект", "prompt": "Ты журналист, пишущий об AI. Создай интересный пост о новостях AI."},
    "crypto": {"name": "🪙 Криптовалюты", "emoji": "🪙", "description": "Новости криптовалют", "hashtags": "#Криптовалюта #Биткоин", "prompt": "Ты крипто-аналитик. Создай пост о криптовалютах."},
    "nft": {"name": "🎨 NFT", "emoji": "🎨", "description": "Новости NFT", "hashtags": "#NFT #ЦифровоеИскусство", "prompt": "Ты эксперт по NFT. Создай пост об NFT."},
    "telegram": {"name": "📱 Telegram", "emoji": "📱", "description": "Новости Telegram", "hashtags": "#Telegram", "prompt": "Ты блогер о Telegram. Создай пост о Telegram."},
    "business": {"name": "💼 Бизнес", "emoji": "💼", "description": "Бизнес новости", "hashtags": "#Бизнес", "prompt": "Ты бизнес-журналист. Создай пост о бизнесе."},
    "tech": {"name": "📡 Технологии", "emoji": "📡", "description": "Технологии", "hashtags": "#Технологии", "prompt": "Ты техноблогер. Создай пост о технологиях."},
    "science": {"name": "🔬 Наука", "emoji": "🔬", "description": "Научные открытия", "hashtags": "#Наука", "prompt": "Ты научный журналист. Создай пост о науке."},
    "health": {"name": "💊 Здоровье", "emoji": "💊", "description": "Здоровье", "hashtags": "#Здоровье", "prompt": "Ты медицинский блогер. Создай пост о здоровье."},
    "psychology": {"name": "🧠 Психология", "emoji": "🧠", "description": "Психология", "hashtags": "#Психология", "prompt": "Ты психолог. Создай пост о психологии."},
    "marketing": {"name": "📈 Маркетинг", "emoji": "📈", "description": "Маркетинг", "hashtags": "#Маркетинг", "prompt": "Ты маркетолог. Создай пост о маркетинге."},
    "design": {"name": "🎨 Дизайн", "emoji": "🎨", "description": "Дизайн", "hashtags": "#Дизайн", "prompt": "Ты дизайнер. Создай пост о дизайне."},
    "programming": {"name": "💻 Программирование", "emoji": "💻", "description": "IT и разработка", "hashtags": "#Программирование", "prompt": "Ты разработчик. Создай пост о программировании."},
    "gaming": {"name": "🎮 Игры", "emoji": "🎮", "description": "Игры", "hashtags": "#Игры", "prompt": "Ты игровой журналист. Создай пост об играх."},
    "movies": {"name": "🎬 Кино", "emoji": "🎬", "description": "Кино", "hashtags": "#Кино", "prompt": "Ты кинокритик. Создай пост о кино."},
    "music": {"name": "🎵 Музыка", "emoji": "🎵", "description": "Музыка", "hashtags": "#Музыка", "prompt": "Ты музыкальный обозреватель. Создай пост о музыке."},
    "sport": {"name": "⚽ Спорт", "emoji": "⚽", "description": "Спорт", "hashtags": "#Спорт", "prompt": "Ты спортивный журналист. Создай пост о спорте."},
    "travel": {"name": "✈️ Путешествия", "emoji": "✈️", "description": "Путешествия", "hashtags": "#Путешествия", "prompt": "Ты тревел-блогер. Создай пост о путешествиях."},
    "food": {"name": "🍳 Кулинария", "emoji": "🍳", "description": "Кулинария", "hashtags": "#Кулинария", "prompt": "Ты кулинарный блогер. Создай пост о еде."},
    "education": {"name": "📚 Образование", "emoji": "📚", "description": "Образование", "hashtags": "#Образование", "prompt": "Ты педагог. Создай пост об образовании."},
    "motivation": {"name": "💪 Мотивация", "emoji": "💪", "description": "Мотивация", "hashtags": "#Мотивация", "prompt": "Ты мотивационный спикер. Создай пост о мотивации."}
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

# ==================== ОСНОВНОЕ ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.user_subscriptions: Dict[int, UserSubscription] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_counter = 0
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
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
                logger.info(f"Загружено {len(self.user_subscriptions)} пользователей")
        except FileNotFoundError:
            logger.info("Файл subscriptions.json не найден, создаем новый")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
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
            with open("subscriptions.json", "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Данные сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
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
                        logger.info("Токен API получен")
                        return self.api_token
        except Exception as e:
            logger.error(f"Ошибка токена: {e}")
        return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

Требования:
- Длина: примерно {size_config['chars']} символов
- Используй эмодзи
- Добавь хэштеги: {theme_config['hashtags']}
- Пиши на русском языке
- Добавь вопрос к подписчикам"""
        
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
                        "max_tokens": 2000
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self._get_fallback_post(theme)
    
    def _get_fallback_post(self, theme: str) -> str:
        return f"""{POSTING_THEMES[theme]['emoji']} *{POSTING_THEMES[theme]['name']}*

Интересный пост на тему {POSTING_THEMES[theme]['name'].lower()}!

А что вы думаете по этому поводу? Делитесь мнением в комментариях! 👇

{POSTING_THEMES[theme]['hashtags']}"""
    
    async def send_post(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, theme: str, size: str) -> bool:
        try:
            content = await self.generate_post(theme, size)
            self.post_counter += 1
            
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            formatted_post = f"""━━━━━━━━━━━━━━━━━━━━━
{POSTING_THEMES[theme]['emoji']} *{POSTING_THEMES[theme]['name']}*
━━━━━━━━━━━━━━━━━━━━━

{content}

━━━━━━━━━━━━━━━━━━━━━
📅 {timestamp} | Пост #{self.post_counter}
💬 Ждем ваши комментарии!
━━━━━━━━━━━━━━━━━━━━━"""
            
            await context.bot.send_message(
                chat_id=channel_id,
                text=formatted_post,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Пост отправлен в {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="select_size")],
        [InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
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
    intervals = [10, 30, 60, 300, 600, 1800, 3600, 7200, 21600]
    keyboard = []
    row = []
    for sec in intervals:
        if sec < 60:
            text = f"{sec} сек"
        elif sec < 3600:
            text = f"{sec//60} мин"
        else:
            text = f"{sec//3600} ч"
        row.append(InlineKeyboardButton(text, callback_data=f"interval_{sec}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    
    welcome = f"""✨ *Привет, {user.first_name}!* ✨

🤖 *AI Бот для автопостинга*

🎯 *Возможности:*
• 📝 Генерация постов через ИИ
• 🎨 20 разных тематик
• ⏱ Автопостинг от 10 секунд
• 💰 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*

👇 *Выберите действие:*"""
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['adding_channel'] = True
    
    await query.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📢 *ДОБАВЛЕНИЕ КАНАЛА*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Как добавить канал:*\n\n"
        "1️⃣ *Добавьте бота в канал*\n"
        "   Как АДМИНИСТРАТОРА!\n\n"
        "2️⃣ *Перешлите ЛЮБОЕ сообщение*\n"
        "   Из канала СЮДА\n\n"
        "3️⃣ *Или отправьте username:*\n"
        "   Например: @durov\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📤 *Отправьте сообщение из канала*",
        parse_mode='Markdown'
    )

async def handle_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления канала"""
    if not context.user_data.get('adding_channel'):
        return
    
    user_id = update.effective_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    # Проверка лимита
    if len(sub.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ *Лимит каналов достигнут!*\n\n"
            f"Ваш тариф: {tariff['name']}\n"
            f"Максимум: {tariff['channels']} каналов",
            parse_mode='Markdown'
        )
        context.user_data['adding_channel'] = False
        return
    
    channel_id = None
    channel_name = None
    
    # Способ 1: Пересланное сообщение
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
        logger.info(f"Канал из пересылки: {channel_id} - {channel_name}")
    
    # Способ 2: Текст с username
    elif update.message.text:
        text = update.message.text.strip()
        if text.startswith('@'):
            try:
                chat = await context.bot.get_chat(text)
                channel_id = str(chat.id)
                channel_name = chat.title
                logger.info(f"Канал по username: {channel_id} - {channel_name}")
            except Exception as e:
                logger.error(f"Ошибка получения чата: {e}")
        
        # Способ 3: ID канала
        elif text.startswith('-100') or (text.isdigit() and len(text) > 5):
            try:
                chat_id = int(text)
                chat = await context.bot.get_chat(chat_id)
                channel_id = str(chat.id)
                channel_name = chat.title
                logger.info(f"Канал по ID: {channel_id} - {channel_name}")
            except Exception as e:
                logger.error(f"Ошибка получения чата по ID: {e}")
    
    if not channel_id:
        await update.message.reply_text(
            "❌ *Не удалось определить канал*\n\n"
            "Попробуйте:\n"
            "• Переслать сообщение ИЗ КАНАЛА\n"
            "• Отправить username канала (с @)\n"
            "• Отправить ID канала",
            parse_mode='Markdown'
        )
        return
    
    # Проверяем, не добавлен ли уже канал
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            await update.message.reply_text(
                f"❌ *Канал уже добавлен!*\n\n"
                f"📢 {channel_name}",
                parse_mode='Markdown'
            )
            context.user_data['adding_channel'] = False
            return
    
    # Проверяем, есть ли бот в канале
    try:
        bot_member = await context.bot.get_chat_member(
            chat_id=int(channel_id), 
            user_id=context.bot.id
        )
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "⚠️ *Бот не администратор канала!*\n\n"
                "Добавьте бота в канал как АДМИНИСТРАТОРА\n"
                "и попробуйте снова.",
                parse_mode='Markdown'
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки прав: {e}")
        await update.message.reply_text(
            "⚠️ *Не удалось проверить права бота*\n\n"
            "Убедитесь, что бот добавлен в канал\n"
            "и имеет права администратора.",
            parse_mode='Markdown'
        )
        return
    
    # Добавляем канал
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
        f"📊 *Каналов:* {len(sub.channels)}/{tariff['channels']}\n\n"
        f"🎯 *Что дальше?*\n"
        f"• Настройте автопостинг\n"
        f"• Выберите тему и интервал\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )
    
    context.user_data['adding_channel'] = False

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    text = "🤖 *НАСТРОЙКА АВТОПОСТИНГА*\n\n"
    text += "Выберите канал для настройки:\n\n"
    
    keyboard = []
    for ch in sub.channels:
        ch_id = ch.get('id')
        config = sub.auto_posts.get(ch_id)
        status = "✅" if config and config.is_active else "⚙️"
        button_text = f"{status} {ch.get('name', 'Канал')[:30]}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"config_{ch_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def configure_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("config_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    # Находим имя канала
    channel_name = "Канал"
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            channel_name = ch.get('name', 'Канал')
            break
    
    config = sub.auto_posts.get(channel_id)
    
    text = f"⚙️ *Настройка канала*\n\n"
    text += f"📢 *Канал:* {channel_name}\n\n"
    
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
        text += f"🔄 *Статус:* {'✅ Активен' if config.is_active else '⏸ Остановлен'}\n\n"
    else:
        text += "⚠️ *Автопостинг не настроен*\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"theme_{channel_id}")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"size_{channel_id}")],
        [InlineKeyboardButton("⏱ Выбрать интервал", callback_data=f"interval_{channel_id}")],
    ]
    
    if config:
        if config.is_active:
            keyboard.append([InlineKeyboardButton("⏸ Остановить", callback_data=f"stop_{channel_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Запустить", callback_data=f"start_{channel_id}")])
        keyboard.append([InlineKeyboardButton("🗑 Удалить настройки", callback_data=f"delete_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_theme_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("theme_", "")
    context.user_data['config_channel'] = channel_id
    
    keyboard = await get_themes_keyboard()
    await query.edit_message_text(
        "🎨 *Выберите тему для автопостинга:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def select_size_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("size_", "")
    context.user_data['config_channel'] = channel_id
    
    keyboard = await get_sizes_keyboard()
    await query.edit_message_text(
        "📏 *Выберите размер постов:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def select_interval_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("interval_", "")
    context.user_data['config_channel'] = channel_id
    
    keyboard = await get_intervals_keyboard()
    await query.edit_message_text(
        "⏱ *Выберите интервал публикации:*\n\n"
        "Посты будут публиковаться автоматически",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def save_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    theme = query.data.replace("theme_", "")
    channel_id = context.user_data.get('config_channel')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
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
        f"Теперь выберите размер:",
        parse_mode='Markdown',
        reply_markup=await get_sizes_keyboard()
    )

async def save_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    size = query.data.replace("size_", "")
    channel_id = context.user_data.get('config_channel')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
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
        f"Теперь выберите интервал:",
        parse_mode='Markdown',
        reply_markup=await get_intervals_keyboard()
    )

async def save_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    interval = int(query.data.replace("interval_", ""))
    channel_id = context.user_data.get('config_channel')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    if interval < tariff["interval_min"]:
        await query.edit_message_text(
            f"❌ *Минимальный интервал: {tariff['interval_min']} сек*\n\n"
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
        f"🤖 Автопостинг АКТИВЕН!\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode='Markdown'
    )

async def start_auto_posting(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: str):
    """Запуск автопостинга"""
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        return
    
    config = sub.auto_posts[channel_id]
    if not config.is_active:
        return
    
    task_key = f"{user_id}_{channel_id}"
    if task_key in bot.active_tasks:
        return
    
    async def auto_post_loop():
        while True:
            try:
                current_sub = bot.get_user_subscription(user_id)
                if channel_id not in current_sub.auto_posts:
                    break
                
                current_config = current_sub.auto_posts[channel_id]
                if not current_config.is_active:
                    break
                
                now = time.time()
                if now - current_config.last_post >= current_config.interval_seconds:
                    if current_sub.can_post():
                        success = await bot.send_post(
                            context, channel_id, 
                            current_config.theme, 
                            current_config.size
                        )
                        if success:
                            current_config.last_post = now
                            current_sub.add_post()
                            bot.save_data()
                            logger.info(f"Автопостинг: {channel_id}")
                    else:
                        logger.warning(f"Лимит постов для {user_id}")
                
                await asyncio.sleep(min(current_config.interval_seconds, 30))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка автопостинга: {e}")
                await asyncio.sleep(60)
    
    task = asyncio.create_task(auto_post_loop())
    bot.active_tasks[task_key] = task

async def start_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("start_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        sub.auto_posts[channel_id].is_active = True
        bot.save_data()
        await start_auto_posting(context, user_id, channel_id)
        await query.edit_message_text("✅ *Автопостинг запущен!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Сначала настройте автопостинг*", parse_mode='Markdown')

async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("stop_", "")
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
    
    channel_id = query.data.replace("delete_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        task_key = f"{user_id}_{channel_id}"
        if task_key in bot.active_tasks:
            bot.active_tasks[task_key].cancel()
            del bot.active_tasks[task_key]
        
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
            "Сначала добавьте канал",
            parse_mode='Markdown'
        )
        return
    
    if not sub.can_post():
        await query.edit_message_text(
            "⚠️ *Лимит постов на сегодня исчерпан!*",
            parse_mode='Markdown'
        )
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    await query.edit_message_text(
        f"🎲 *Генерация поста...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[random_theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[random_size]['name']}",
        parse_mode='Markdown'
    )
    
    success = await bot.send_post(context, sub.channels[0]['id'], random_theme, random_size)
    
    if success:
        await query.edit_message_text("✅ *Пост опубликован!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Ошибка публикации*", parse_mode='Markdown')

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    if not sub.channels:
        text = "📡 *Мои каналы*\n\n❌ *Нет добавленных каналов*"
    else:
        text = "📡 *Мои каналы*\n\n"
        for i, ch in enumerate(sub.channels, 1):
            text += f"{i}. 📢 *{ch.get('name', 'Канал')}*\n"
            text += f"   🆔 `{ch.get('id')}`\n"
            
            if ch.get('id') in sub.auto_posts:
                cfg = sub.auto_posts[ch['id']]
                text += f"   🎨 Тема: {POSTING_THEMES[cfg.theme]['name']}\n"
                text += f"   🔄 Статус: {'✅ Активен' if cfg.is_active else '⏸ Остановлен'}\n"
            text += "\n"
        
        text += f"📊 *Каналов:* {len(sub.channels)}/{tariff['channels']}\n"
        text += f"📝 *Постов сегодня:* {sub.posts_today}/{tariff['posts_per_day']}"
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    tariff = TARIFFS[sub.tariff]
    
    remaining = tariff["posts_per_day"] - sub.posts_today
    
    text = f"""📊 *Моя статистика*

👤 *Пользователь:* {query.from_user.first_name}
💎 *Тариф:* {tariff['name']}

━━━━━━━━━━━━━━━━━━━━━
📡 *КАНАЛЫ*
📢 Добавлено: {len(sub.channels)}/{tariff['channels']}

━━━━━━━━━━━━━━━━━━━━━
📝 *ПОСТЫ*
📊 Сегодня: {sub.posts_today}/{tariff['posts_per_day']}
⏳ Осталось: {remaining if remaining > 0 else 0}

━━━━━━━━━━━━━━━━━━━━━
🤖 *АВТОПОСТИНГ*
⚙️ Активных: {len([c for c in sub.auto_posts.values() if c.is_active])}
⏱ Мин. интервал: {tariff['interval_min']} сек

━━━━━━━━━━━━━━━━━━━━━
✨ *Все тарифы БЕСПЛАТНЫЕ!*"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*

🌟 *БАЗОВЫЙ* - 0₽
├ 📢 Каналов: 5
├ 📝 Постов/день: 100
└ ⏱ Мин. интервал: 10 сек

⭐ *СТАНДАРТ* - 0₽  
├ 📢 Каналов: 15
├ 📝 Постов/день: 300
└ ⏱ Мин. интервал: 5 сек

💎 *ПРОФЕССИОНАЛЬНЫЙ* - 0₽
├ 📢 Каналов: 50
├ 📝 Постов/день: 1000
└ ⏱ Мин. интервал: 3 сек

👑 *ПРЕМИУМ* - 0₽
├ 📢 Каналов: 999
├ 📝 Постов/день: 5000
└ ⏱ Мин. интервал: 1 сек

✨ *ВСЕ ФУНКЦИИ ДОСТУПНЫ!*"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """🆘 *Помощь и инструкция*

📌 *БЫСТРЫЙ СТАРТ:*

1️⃣ *Добавьте канал*
   → Нажмите «📢 Добавить канал»
   → Добавьте бота в канал (админ)
   → Перешлите сообщение из канала

2️⃣ *Настройте автопостинг*
   → Нажмите «🤖 Автопостинг»
   → Выберите канал
   → Выберите ТЕМУ, РАЗМЕР, ИНТЕРВАЛ

🎯 *ВОЗМОЖНОСТИ:*
• 20+ тем на выбор
• 5 размеров постов
• Интервалы от 10 секунд
• Генерация через AI

💡 *СОВЕТЫ:*
• Используйте «Случайный пост»
• Все тарифы БЕСПЛАТНЫЕ!"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard()
    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback запросов"""
    query = update.callback_query
    data = query.data
    
    logger.info(f"Callback: {data}")
    
    if data == "main_menu":
        await main_menu(update, context)
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "select_theme":
        keyboard = await get_themes_keyboard()
        await query.edit_message_text(
            "🎨 *Выберите тему для случайного поста:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    elif data == "select_size":
        keyboard = await get_sizes_keyboard()
        await query.edit_message_text(
            "📏 *Выберите размер для случайного поста:*",
            parse_mode='Markdown',
            reply_markup=keyboard
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
    elif data.startswith("config_"):
        await configure_channel(update, context)
    elif data.startswith("theme_") and not data.startswith("themes_page_"):
        # Проверяем, это выбор темы для настройки или для случайного поста
        if context.user_data.get('config_channel'):
            await save_theme(update, context)
        else:
            # Сохраняем тему для случайного поста
            theme = data.replace("theme_", "")
            context.user_data['temp_theme'] = theme
            keyboard = await get_sizes_keyboard()
            await query.edit_message_text(
                f"✅ Тема: {POSTING_THEMES[theme]['name']}\n\nТеперь выберите размер:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    elif data.startswith("size_") and not data.startswith("size_for_"):
        if context.user_data.get('config_channel'):
            await save_size(update, context)
        else:
            # Случайный пост с выбранными темой и размером
            theme = context.user_data.get('temp_theme', random.choice(list(POSTING_THEMES.keys())))
            size = data.replace("size_", "")
            
            user_id = query.from_user.id
            sub = bot.get_user_subscription(user_id)
            
            if not sub.channels:
                await query.edit_message_text("❌ *Нет добавленных каналов!*", parse_mode='Markdown')
                return
            
            if not sub.can_post():
                await query.edit_message_text("⚠️ *Лимит постов на сегодня!*", parse_mode='Markdown')
                return
            
            await query.edit_message_text("🎲 *Генерация поста...*", parse_mode='Markdown')
            success = await bot.send_post(context, sub.channels[0]['id'], theme, size)
            
            if success:
                await query.edit_message_text("✅ *Пост опубликован!*", parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ *Ошибка публикации*", parse_mode='Markdown')
            
            context.user_data.pop('temp_theme', None)
    elif data.startswith("interval_"):
        await save_interval(update, context)
    elif data.startswith("start_"):
        await start_auto(update, context)
    elif data.startswith("stop_"):
        await stop_auto(update, context)
    elif data.startswith("delete_"):
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
    
    # Обработчик добавления канала
    application.add_handler(MessageHandler(
        filters.TEXT | filters.FORWARDED,
        handle_add_channel
    ))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info("💰 ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
