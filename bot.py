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

# ==================== ТАРИФЫ БЕЗ ЛИМИТОВ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Базовый",
        "price": 0,
        "channels": 999999,
        "posts_per_day": 999999,
        "interval_min": 5,
        "color": "🟢"
    },
    "basic": {
        "name": "⭐ Стандарт",
        "price": 0,
        "channels": 999999,
        "posts_per_day": 999999,
        "interval_min": 5,
        "color": "🔵"
    },
    "pro": {
        "name": "💎 Профессиональный",
        "price": 0,
        "channels": 999999,
        "posts_per_day": 999999,
        "interval_min": 5,
        "color": "🟣"
    },
    "premium": {
        "name": "👑 Премиум",
        "price": 0,
        "channels": 999999,
        "posts_per_day": 999999,
        "interval_min": 5,
        "color": "🔴"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 Новости AI",
        "emoji": "🤖",
        "category": "Технологии",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#AI #ИскусственныйИнтеллект #НовостиAI",
        "prompt": "Ты журналист, пишущий об AI. Создай интересный и уникальный пост о последних новостях в мире искусственного интеллекта."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "category": "Соцсети",
        "description": "Новости Telegram, боты, каналы",
        "hashtags": "#Telegram #Мессенджер #Обновления",
        "prompt": "Ты блогер о Telegram. Создай уникальный пост о новых функциях Telegram, топовых ботах, полезных каналах."
    },
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "category": "Криптовалюты",
        "description": "Новости NFT и цифрового искусства",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная",
        "prompt": "Ты эксперт по NFT. Создай уникальный пост о NFT коллекциях, digital art, метавселенных."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "category": "Криптовалюты",
        "description": "Новости криптовалют и блокчейна",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн",
        "prompt": "Ты крипто-аналитик. Создай уникальный пост о криптовалютах, блокчейне, DeFi."
    },
    "web3": {
        "name": "🌐 Web3",
        "emoji": "🌐",
        "category": "Криптовалюты",
        "description": "Web3 и децентрализация",
        "hashtags": "#Web3 #Децентрализация #Блокчейн",
        "prompt": "Ты эксперт по Web3. Создай уникальный пост о Web3 технологиях, децентрализации, DAO."
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "category": "Бизнес",
        "description": "Бизнес новости и советы",
        "hashtags": "#Бизнес #Стартап #Предпринимательство",
        "prompt": "Ты бизнес-журналист. Создай уникальный пост о бизнесе, стартапах, инвестициях."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "category": "Маркетинг",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Реклама",
        "prompt": "Ты маркетолог. Создай уникальный пост о маркетинге, SMM, рекламе."
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "category": "Наука",
        "description": "Научные открытия",
        "hashtags": "#Наука #Открытия #Исследования",
        "prompt": "Ты научный журналист. Создай уникальный пост о научных открытиях."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "category": "Психология",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация",
        "prompt": "Ты психолог. Создай полезный пост по психологии и саморазвитию."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "category": "Мотивация",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Вдохновение",
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост о достижении целей."
    },
    "health": {
        "name": "💊 Здоровье",
        "emoji": "💊",
        "category": "Здоровье",
        "description": "Здоровье и медицина",
        "hashtags": "#Здоровье #Медицина #ЗОЖ",
        "prompt": "Ты медицинский блогер. Создай полезный пост о здоровье."
    },
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "category": "Технологии",
        "description": "Технологические новости",
        "hashtags": "#Технологии #Гаджеты #Инновации",
        "prompt": "Ты техноблогер. Создай пост о новых технологиях и гаджетах."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "category": "IT",
        "description": "IT и разработка",
        "hashtags": "#Программирование #IT #Код",
        "prompt": "Ты разработчик. Создай полезный пост о программировании."
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "category": "Игры",
        "description": "Игровые новости",
        "hashtags": "#Игры #Гейминг #Видеоигры",
        "prompt": "Ты игровой журналист. Создай пост об играх."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "category": "Развлечения",
        "description": "Новости кино",
        "hashtags": "#Кино #Фильмы #Сериалы",
        "prompt": "Ты кинокритик. Создай пост о новинках кино."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "category": "Развлечения",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Хиты",
        "prompt": "Ты музыкальный обозреватель. Создай пост о музыке."
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "category": "Спорт",
        "description": "Спортивные новости",
        "hashtags": "#Спорт #Футбол #Баскетбол",
        "prompt": "Ты спортивный журналист. Создай пост о спорте."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "category": "Путешествия",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Туризм #Отдых",
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "category": "Кулинария",
        "description": "Кулинария и рецепты",
        "hashtags": "#Кулинария #Рецепты #Еда",
        "prompt": "Ты кулинарный блогер. Создай пост о рецептах."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "category": "Образование",
        "description": "Образование и обучение",
        "hashtags": "#Образование #Учеба #Знания",
        "prompt": "Ты педагог. Создай полезный пост об образовании."
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "category": "Дизайн",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #Креатив #Вдохновение",
        "prompt": "Ты дизайнер. Создай вдохновляющий пост о дизайне."
    },
    "auto": {
        "name": "🚗 Авто",
        "emoji": "🚗",
        "category": "Авто",
        "description": "Автомобили и новинки",
        "hashtags": "#Авто #Машины #Электромобили",
        "prompt": "Ты автомобильный блогер. Создай пост об автомобилях."
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
    task: asyncio.Task = None

@dataclass
class UserSubscription:
    user_id: int
    tariff: str
    channels: List[dict] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    auto_posts: Dict[str, AutoPostConfig] = field(default_factory=dict)
    
    def can_post(self) -> bool:
        return True
    
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
        except FileNotFoundError:
            logger.info("Файл subscriptions.json не найден")
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
- Используй эмодзи для оформления
- Добавь в конце: {theme_config['hashtags']}
- Пиши на русском языке
- Добавь вопрос к подписчикам в конце"""

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
        return f"✨ *{POSTING_THEMES[theme]['name']}*\n\nНовый интересный пост! А что вы думаете по этой теме?\n\n👇 Ваше мнение в комментариях!\n\n{POSTING_THEMES[theme]['hashtags']}"
    
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
            
            logger.info(f"✅ Пост отправлен в канал {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False
    
    async def stop_auto_posting(self, user_id: int, channel_id: str):
        """Остановка автопостинга для канала"""
        task_key = f"{user_id}_{channel_id}"
        if task_key in self.active_tasks:
            task = self.active_tasks[task_key]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_tasks[task_key]
            logger.info(f"⏹ Автопостинг остановлен для канала {channel_id}")
    
    async def start_auto_posting(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: str):
        """Запуск автопостинга для канала"""
        sub = self.get_user_subscription(user_id)
        
        if channel_id not in sub.auto_posts:
            return
        
        config = sub.auto_posts[channel_id]
        
        # Останавливаем старую задачу если есть
        await self.stop_auto_posting(user_id, channel_id)
        
        async def post_loop():
            logger.info(f"🚀 Запущен автопостинг для канала {channel_id}, интервал: {config.interval_seconds}с")
            while True:
                try:
                    # Проверяем актуальную конфигурацию
                    current_sub = self.get_user_subscription(user_id)
                    if channel_id not in current_sub.auto_posts:
                        logger.info(f"Канал {channel_id} удален из настроек")
                        break
                    
                    current_config = current_sub.auto_posts[channel_id]
                    
                    if not current_config.is_active:
                        await asyncio.sleep(1)
                        continue
                    
                    current_time = time.time()
                    if current_time - current_config.last_post >= current_config.interval_seconds:
                        logger.info(f"📝 Публикация поста в канал {channel_id}")
                        success = await self.format_and_send_post(
                            context, channel_id, current_config.theme, current_config.size, is_auto=True
                        )
                        if success:
                            current_config.last_post = current_time
                            self.save_data()
                    
                    await asyncio.sleep(1)
                    
                except asyncio.CancelledError:
                    logger.info(f"⏹ Задача автопостинга для канала {channel_id} отменена")
                    break
                except Exception as e:
                    logger.error(f"Ошибка в цикле автопостинга {channel_id}: {e}")
                    await asyncio.sleep(5)
        
        task = asyncio.create_task(post_loop())
        self.active_tasks[f"{user_id}_{channel_id}"] = task
        config.task = task
        logger.info(f"✅ Автопостинг запущен для канала {channel_id}")

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
    intervals = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 14400, 21600, 43200, 86400]
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
• 📝 Генерация постов через ИИ
• 🎨 *{len(POSTING_THEMES)} тем* на выбор
• ⏱ Автопостинг от 5 секунд
• 📏 5 размеров постов
• 🚫 *БЕЗ ЛИМИТОВ!*

━━━━━━━━━━━━━━━━━━━━━
👇 *Выберите действие:*"""

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
        "⚠️ *Важно:* бот должен быть АДМИНИСТРАТОРОМ канала!",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel_link'] = True

async def extract_username(text: str) -> str:
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
    if not context.user_data.get('awaiting_channel_link'):
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    username = await extract_username(text)
    if not username:
        await update.message.reply_text("❌ *Неверный формат ссылки!*", parse_mode='Markdown')
        return
    
    try:
        chat = await context.bot.get_chat(f"@{username}")
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ *Это не канал!*", parse_mode='Markdown')
            return
        
        channel_id = str(chat.id)
        channel_name = chat.title
        
        # Проверяем права бота
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"⚠️ *Бот не администратор канала!*\n\n"
                f"Добавьте @{context.bot.username} как администратора",
                parse_mode='Markdown'
            )
            return
        
        sub = bot.get_user_subscription(user_id)
        
        # Проверяем дубликаты
        for ch in sub.channels:
            if ch.get('id') == channel_id:
                await update.message.reply_text("❌ *Канал уже добавлен!*", parse_mode='Markdown')
                return
        
        sub.channels.append({
            "id": channel_id,
            "name": channel_name,
            "username": username
        })
        bot.save_data()
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 {channel_name}\n"
            f"🔗 t.me/{username}\n\n"
            f"Теперь настройте автопостинг в меню",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ *Не удалось найти канал*", parse_mode='Markdown')
    
    context.user_data['awaiting_channel_link'] = False

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await query.edit_message_text("❌ *Нет добавленных каналов!*", parse_mode='Markdown')
        return
    
    keyboard = []
    for ch in sub.channels:
        ch_id = ch.get('id')
        config = sub.auto_posts.get(ch_id)
        status = "✅" if config and config.is_active else "⏸" if config else "⚙️"
        keyboard.append([InlineKeyboardButton(
            f"{status} {ch.get('name', 'Канал')[:30]}",
            callback_data=f"config_{ch_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    await query.edit_message_text(
        "🤖 *Настройка автопостинга*\n\nВыберите канал:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def configure_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("config_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    channel_name = "Канал"
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            channel_name = ch.get('name', 'Канал')
            break
    
    config = sub.auto_posts.get(channel_id)
    
    text = f"⚙️ *{channel_name}*\n\n"
    
    if config:
        theme = POSTING_THEMES.get(config.theme, {})
        size = POST_SIZES.get(config.size, {})
        interval = config.interval_seconds
        interval_text = f"{interval} сек" if interval < 60 else f"{interval//60} мин" if interval < 3600 else f"{interval//3600} ч"
        
        text += f"🎨 Тема: {theme.get('emoji', '')} {theme.get('name', '-')}\n"
        text += f"📏 Размер: {size.get('name', '-')}\n"
        text += f"⏱ Интервал: {interval_text}\n"
        text += f"🔘 Статус: {'✅ АКТИВЕН' if config.is_active else '⏸ ОСТАНОВЛЕН'}\n\n"
    else:
        text += "⚠️ Автопостинг не настроен\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"theme_{channel_id}")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"size_{channel_id}")],
        [InlineKeyboardButton("⏱ Выбрать интервал", callback_data=f"interval_{channel_id}")],
    ]
    
    if config:
        if config.is_active:
            keyboard.append([InlineKeyboardButton("⏸ ОСТАНОВИТЬ", callback_data=f"stop_{channel_id}")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ ЗАПУСТИТЬ", callback_data=f"start_{channel_id}")])
        keyboard.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_theme_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("theme_", "")
    context.user_data['temp_channel_id'] = channel_id
    await query.edit_message_text(
        "🎨 *Выберите тему:*",
        parse_mode='Markdown',
        reply_markup=await get_themes_keyboard()
    )

async def select_size_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("size_", "")
    context.user_data['temp_channel_id'] = channel_id
    await query.edit_message_text(
        "📏 *Выберите размер:*",
        parse_mode='Markdown',
        reply_markup=await get_sizes_keyboard()
    )

async def select_interval_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("interval_", "")
    context.user_data['temp_channel_id'] = channel_id
    await query.edit_message_text(
        "⏱ *Выберите интервал:*",
        parse_mode='Markdown',
        reply_markup=await get_intervals_keyboard()
    )

async def handle_theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    theme = query.data.replace("theme_", "")
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id, channel_name="", channel_username="",
            theme=theme, size="medium", interval_seconds=300
        )
    else:
        sub.auto_posts[channel_id].theme = theme
    
    bot.save_data()
    await query.edit_message_text("✅ *Тема сохранена!*", parse_mode='Markdown')

async def handle_size_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    size = query.data.replace("size_", "")
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id, channel_name="", channel_username="",
            theme="ai_news", size=size, interval_seconds=300
        )
    else:
        sub.auto_posts[channel_id].size = size
    
    bot.save_data()
    await query.edit_message_text("✅ *Размер сохранен!*", parse_mode='Markdown')

async def handle_interval_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "custom_interval":
        context.user_data['awaiting_custom_interval'] = True
        await query.edit_message_text(
            "⏱ *Введите интервал в секундах:*\n\n"
            "Пример: 10, 30, 60, 300",
            parse_mode='Markdown'
        )
        return
    
    interval = int(data.replace("interval_", ""))
    channel_id = context.user_data.get('temp_channel_id')
    
    if not channel_id:
        await query.edit_message_text("❌ Ошибка", parse_mode='Markdown')
        return
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id not in sub.auto_posts:
        sub.auto_posts[channel_id] = AutoPostConfig(
            channel_id=channel_id, channel_name="", channel_username="",
            theme="ai_news", size="medium", interval_seconds=interval
        )
    else:
        sub.auto_posts[channel_id].interval_seconds = interval
    
    sub.auto_posts[channel_id].is_active = True
    sub.auto_posts[channel_id].last_post = time.time()
    
    # Обновляем имя канала
    for ch in sub.channels:
        if ch.get('id') == channel_id:
            sub.auto_posts[channel_id].channel_name = ch.get('name', '')
            sub.auto_posts[channel_id].channel_username = ch.get('username', '')
            break
    
    bot.save_data()
    
    # Запускаем автопостинг
    await bot.start_auto_posting(context, user_id, channel_id)
    
    interval_text = f"{interval} сек" if interval < 60 else f"{interval//60} мин" if interval < 3600 else f"{interval//3600} ч"
    
    await query.edit_message_text(
        f"✅ *Автопостинг настроен!*\n\n"
        f"⏱ Интервал: {interval_text}\n"
        f"🔄 Статус: АКТИВЕН\n\n"
        f"Бот будет публиковать посты автоматически!",
        parse_mode='Markdown'
    )

async def start_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("start_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        sub.auto_posts[channel_id].is_active = True
        bot.save_data()
        await bot.start_auto_posting(context, user_id, channel_id)
        await query.edit_message_text("✅ *Автопостинг запущен!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Настройки не найдены*", parse_mode='Markdown')

async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("stop_", "")
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if channel_id in sub.auto_posts:
        sub.auto_posts[channel_id].is_active = False
        bot.save_data()
        await bot.stop_auto_posting(user_id, channel_id)
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
        await bot.stop_auto_posting(user_id, channel_id)
        del sub.auto_posts[channel_id]
        bot.save_data()
        await query.edit_message_text("🗑 *Настройки удалены*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Настройки не найдены*", parse_mode='Markdown')

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    if not sub.channels:
        await query.edit_message_text("❌ *Нет добавленных каналов*", parse_mode='Markdown')
        return
    
    random_theme = random.choice(list(POSTING_THEMES.keys()))
    random_size = random.choice(list(POST_SIZES.keys()))
    
    await query.edit_message_text(
        f"🎲 *Генерация поста...*\n\n"
        f"Тема: {POSTING_THEMES[random_theme]['name']}",
        parse_mode='Markdown'
    )
    
    success = await bot.format_and_send_post(context, sub.channels[0]['id'], random_theme, random_size)
    
    if success:
        await query.edit_message_text("✅ *Пост опубликован!*", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ *Ошибка публикации*", parse_mode='Markdown')

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    
    text = "📡 *Мои каналы*\n\n"
    
    if not sub.channels:
        text += "Нет добавленных каналов"
    else:
        for i, ch in enumerate(sub.channels, 1):
            text += f"{i}. {ch.get('name', 'Канал')}\n"
            config = sub.auto_posts.get(ch.get('id'))
            if config:
                status = "✅ Активен" if config.is_active else "⏸ Остановлен"
                text += f"   Статус: {status}\n"
            text += "\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    sub = bot.get_user_subscription(user_id)
    active_count = len([c for c in sub.auto_posts.values() if c.is_active])
    
    text = f"""━━━━━━━━━━━━━━━━━━━━━
📊 *Моя статистика*
━━━━━━━━━━━━━━━━━━━━━

👤 Пользователь: {query.from_user.first_name}
💎 Тариф: БЕСПЛАТНЫЙ

━━━━━━━━━━━━━━━━━━━━━
📡 Каналов: {len(sub.channels)}
🤖 Активных автопостингов: {active_count}
🎨 Доступно тем: {len(POSTING_THEMES)}

━━━━━━━━━━━━━━━━━━━━━
✨ *БЕЗ ЛИМИТОВ!*
🚀 Автопостинг 24/7
━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """━━━━━━━━━━━━━━━━━━━━━
💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ*
━━━━━━━━━━━━━━━━━━━━━

🌟 *БАЗОВЫЙ* - 0₽
├ 📢 Каналов: ∞
├ 📝 Постов: ∞
└ ⏱ От 5 секунд

⭐ *СТАНДАРТ* - 0₽  
├ 📢 Каналов: ∞
├ 📝 Постов: ∞
└ ⏱ От 5 секунд

💎 *ПРО* - 0₽
├ 📢 Каналов: ∞
├ 📝 Постов: ∞
└ ⏱ От 5 секунд

👑 *ПРЕМИУМ* - 0₽
├ 📢 Каналов: ∞
├ 📝 Постов: ∞
└ ⏱ От 5 секунд

━━━━━━━━━━━━━━━━━━━━━
✨ *БЕЗ ЛИМИТОВ!*
━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """━━━━━━━━━━━━━━━━━━━━━
🆘 *Помощь*
━━━━━━━━━━━━━━━━━━━━━

📌 *Как добавить канал:*
1. Добавьте бота в канал (администратор)
2. Нажмите «Добавить канал»
3. Отправьте ссылку: https://t.me/username

🎯 *Настройка автопостинга:*
1. Нажмите «Настройка автопостинга»
2. Выберите канал
3. Выберите тему, размер, интервал
4. Автопостинг запустится автоматически!

✨ *Преимущества:*
• БЕЗ ЛИМИТОВ на каналы и посты
• Автопостинг 24/7
• 30+ тем на выбор
• Все тарифы бесплатные

━━━━━━━━━━━━━━━━━━━━━"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_custom_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_custom_interval'):
        return
    
    try:
        interval = int(update.message.text.strip())
        if interval < 1:
            await update.message.reply_text("❌ Интервал должен быть больше 0")
            return
        
        channel_id = context.user_data.get('temp_channel_id')
        if not channel_id:
            await update.message.reply_text("❌ Ошибка")
            return
        
        user_id = update.effective_user.id
        sub = bot.get_user_subscription(user_id)
        
        if channel_id not in sub.auto_posts:
            sub.auto_posts[channel_id] = AutoPostConfig(
                channel_id=channel_id, channel_name="", channel_username="",
                theme="ai_news", size="medium", interval_seconds=interval
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
        await bot.start_auto_posting(context, user_id, channel_id)
        
        interval_text = f"{interval} сек" if interval < 60 else f"{interval//60} мин"
        await update.message.reply_text(f"✅ *Интервал установлен: {interval_text}*", parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Введите число")
    
    context.user_data['awaiting_custom_interval'] = False
    context.user_data['temp_channel_id'] = None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        keyboard = await get_main_keyboard()
        await query.edit_message_text("🏠 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "add_channel":
        await add_channel_start(update, context)
    
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    
    elif data == "select_theme":
        await query.edit_message_text(
            "🎨 *Выберите тему:*",
            parse_mode='Markdown',
            reply_markup=await get_themes_keyboard()
        )
    
    elif data == "select_size":
        await query.edit_message_text(
            "📏 *Выберите размер:*",
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
        await query.edit_message_reply_markup(reply_markup=await get_themes_keyboard(page))
    
    elif data.startswith("theme_") and not data.startswith("themes_page_"):
        if data.startswith("theme_") and len(data) > 6 and not data.startswith("themes_page_"):
            channel_id = context.user_data.get('temp_channel_id')
            if channel_id:
                await handle_theme_selection(update, context)
            else:
                await handle_theme_selection(update, context)
        else:
            await handle_theme_selection(update, context)
    
    elif data.startswith("size_"):
        await handle_size_selection(update, context)
    
    elif data.startswith("interval_"):
        await handle_interval_selection(update, context)
    
    elif data == "custom_interval":
        await handle_interval_selection(update, context)
    
    elif data.startswith("config_"):
        await configure_channel(update, context)
    
    elif data.startswith("theme_") and context.user_data.get('temp_channel_id'):
        await handle_theme_selection(update, context)
    
    elif data.startswith("size_") and context.user_data.get('temp_channel_id'):
        await handle_size_selection(update, context)
    
    elif data.startswith("interval_") and context.user_data.get('temp_channel_id'):
        await handle_interval_selection(update, context)
    
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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_link))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval))
    
    logger.info("🚀 Бот запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info("💰 Все тарифы БЕСПЛАТНЫЕ!")
    logger.info("🚫 БЕЗ ЛИМИТОВ!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
