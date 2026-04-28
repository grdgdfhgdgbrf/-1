import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
from datetime import datetime
from typing import Dict, Optional, List, Tuple
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

# ==================== БЕСПЛАТНЫЕ ТАРИФЫ ====================
TARIFFS = {
    "starter": {
        "name": "🌟 СТАРТ",
        "emoji": "🌟",
        "channels": 1,
        "posts_per_day": 10,
        "can_repost": True,
        "can_schedule": True,
        "intervals": [30, 60, 120, 180, 240, 360, 720, 1440],
        "color": "#00CED1"
    },
    "blogger": {
        "name": "📝 БЛОГЕР",
        "emoji": "📝",
        "channels": 3,
        "posts_per_day": 30,
        "can_repost": True,
        "can_schedule": True,
        "intervals": [15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440],
        "color": "#FF6B6B"
    },
    "pro": {
        "name": "💎 PRO",
        "emoji": "💎",
        "channels": 10,
        "posts_per_day": 100,
        "can_repost": True,
        "can_schedule": True,
        "intervals": [5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440],
        "color": "#9B59B6"
    },
    "unlimited": {
        "name": "👑 UNLIMITED",
        "emoji": "👑",
        "channels": 999,
        "posts_per_day": 999,
        "can_repost": True,
        "can_schedule": True,
        "intervals": [1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440],
        "color": "#F1C40F"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {"name": "ИИ и Нейросети", "emoji": "🧠", "hashtags": "#ИИ #Нейросети #AI", "prompt": "расскажи последние новости из мира искусственного интеллекта, нейросетей и машинного обучения"},
    "crypto": {"name": "Криптовалюты", "emoji": "🪙", "hashtags": "#Крипта #Bitcoin #Blockchain", "prompt": "расскажи о криптовалютах, биткоине, блокчейне и DeFi"},
    "nft": {"name": "NFT и Цифровое Искусство", "emoji": "🎨", "hashtags": "#NFT #DigitalArt #Метавселенная", "prompt": "расскажи о NFT коллекциях, цифровом искусстве и метавселенных"},
    "telegram": {"name": "Telegram", "emoji": "📱", "hashtags": "#Telegram #Мессенджеры #TG", "prompt": "расскажи о новых функциях Telegram, ботах, каналах и секретных возможностях"},
    "web3": {"name": "Web3 и Децентрализация", "emoji": "🌐", "hashtags": "#Web3 #Децентрализация #DAO", "prompt": "расскажи о Web3, децентрализации, DAO и будущем интернета"},
    "business": {"name": "Бизнес и Стартапы", "emoji": "💼", "hashtags": "#Бизнес #Стартапы #Предпринимательство", "prompt": "расскажи о бизнесе, стартапах, инвестициях и предпринимательстве"},
    "marketing": {"name": "Маркетинг и SMM", "emoji": "📈", "hashtags": "#Маркетинг #SMM #Реклама", "prompt": "расскажи о маркетинге, SMM, контент-стратегиях и продвижении"},
    "programming": {"name": "Программирование", "emoji": "💻", "hashtags": "#Код #Python #Dev", "prompt": "расскажи о программировании, языках кода, тулзах и IT-трендах"},
    "design": {"name": "Дизайн и Креатив", "emoji": "🎨", "hashtags": "#Дизайн #UIUX #Креатив", "prompt": "расскажи о дизайне, UI/UX, типографике и креативных решениях"},
    "psychology": {"name": "Психология", "emoji": "🧠", "hashtags": "#Психология #Саморазвитие #Мотивация", "prompt": "расскажи о психологии, саморазвитии, мотивации и личностном росте"},
    "health": {"name": "Здоровье", "emoji": "⚕️", "hashtags": "#Здоровье #Спорт #ЗОЖ", "prompt": "расскажи о здоровье, фитнесе, правильном питании и ЗОЖ"},
    "science": {"name": "Наука и Технологии", "emoji": "🔬", "hashtags": "#Наука #Технологии #Открытия", "prompt": "расскажи о научных открытиях, технологиях и инновациях"},
    "gaming": {"name": "Игры и Гейминг", "emoji": "🎮", "hashtags": "#Игры #Гейминг #Геймдев", "prompt": "расскажи об играх, игровой индустрии и новинках гейминга"},
    "movies": {"name": "Кино и Сериалы", "emoji": "🎬", "hashtags": "#Кино #Сериалы #Новинки", "prompt": "расскажи о новинках кино, сериалах и кинематографе"},
    "music": {"name": "Музыка", "emoji": "🎵", "hashtags": "#Музыка #НовинкиМузыки #Плейлист", "prompt": "расскажи о музыке, новинках и музыкальных трендах"},
    "travel": {"name": "Путешествия", "emoji": "✈️", "hashtags": "#Путешествия #Туризм #Впечатления", "prompt": "расскажи о путешествиях, туризме и интересных местах мира"},
    "food": {"name": "Кулинария", "emoji": "🍳", "hashtags": "#Кулинария #Рецепты #Еда", "prompt": "расскажи о кулинарии, рецептах и вкусной еде"},
    "sport": {"name": "Спорт", "emoji": "⚽", "hashtags": "#Спорт #Футбол #Тренировки", "prompt": "расскажи о спорте, тренировках и спортивных событиях"},
    "education": {"name": "Образование", "emoji": "📚", "hashtags": "#Образование #Учеба #Знания", "prompt": "расскажи об образовании, учебе и полезных знаниях"},
    "motivation": {"name": "Мотивация и Успех", "emoji": "💪", "hashtags": "#Мотивация #Успех #Цели", "prompt": "расскажи о мотивации, достижении целей и успехе"}
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "Мини", "emoji": "🔹", "chars": 200, "desc": "Коротко и по делу (до 200 символов)"},
    "short": {"name": "Короткий", "emoji": "🔸", "chars": 400, "desc": "Лаконичный пост (до 400 символов)"},
    "medium": {"name": "Средний", "emoji": "📄", "chars": 700, "desc": "Информативный пост (до 700 символов)"},
    "long": {"name": "Длинный", "emoji": "📖", "chars": 1000, "desc": "Подробный пост (до 1000 символов)"},
    "extra": {"name": "Максимальный", "emoji": "🌟", "chars": 1500, "desc": "Максимально подробно (до 1500 символов)"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class UserData:
    user_id: int
    username: str
    first_name: str
    tariff: str = "starter"
    channels: List[dict] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    auto_posts: List[dict] = field(default_factory=list)
    
    def reset_daily(self):
        today = time.time()
        if today - self.last_reset >= 86400:
            self.posts_today = 0
            self.last_reset = today
            return True
        return False
    
    def can_post(self) -> bool:
        self.reset_daily()
        tariff = TARIFFS[self.tariff]
        return self.posts_today < tariff["posts_per_day"]
    
    def add_post(self):
        self.posts_today += 1

@dataclass
class AutoPostConfig:
    channel_id: str
    channel_name: str
    theme: str
    size: str
    interval_minutes: int
    last_post: float = 0
    is_active: bool = True
    job_id: str = ""

# ==================== ОСНОВНОЙ КЛАСС ====================
class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.auto_configs: Dict[str, AutoPostConfig] = {}
        self.api_token = None
        self.api_token_expiry = 0
        
    def load_data(self):
        try:
            with open("users_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for user_id, user_data in data.items():
                    self.users[int(user_id)] = UserData(**user_data)
        except:
            pass
        
        try:
            with open("auto_configs.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, cfg_data in data.items():
                    self.auto_configs[key] = AutoPostConfig(**cfg_data)
        except:
            pass
    
    def save_data(self):
        users_data = {uid: {"user_id": u.user_id, "username": u.username, "first_name": u.first_name,
                           "tariff": u.tariff, "channels": u.channels, "posts_today": u.posts_today,
                           "last_reset": u.last_reset, "auto_posts": u.auto_posts} 
                     for uid, u in self.users.items()}
        with open("users_data.json", "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
        
        auto_data = {key: {"channel_id": cfg.channel_id, "channel_name": cfg.channel_name,
                          "theme": cfg.theme, "size": cfg.size, "interval_minutes": cfg.interval_minutes,
                          "last_post": cfg.last_post, "is_active": cfg.is_active, "job_id": cfg.job_id}
                    for key, cfg in self.auto_configs.items()}
        with open("auto_configs.json", "w", encoding="utf-8") as f:
            json.dump(auto_data, f, indent=2, ensure_ascii=False)
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id, username=username, first_name=first_name
            )
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
                        return self.api_token
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
        return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""Ты - профессиональный контент-мейкер и копирайтер. 
Создай интересный, увлекательный пост для Telegram-канала на тему: {theme_config['name']}

Требования к посту:
1. Длина: ОКОЛО {size_config['chars']} символов (плюс-минус 100 символов)
2. Напиши от первого лица или как эксперт
3. Используй эмодзи для украшения (но не переусердствуй)
4. Добавь в конце: {theme_config['hashtags']}
5. Пост должен быть полезным, интересным и вызывать эмоции
6. Добавь вопрос к читателям в конце
7. Пиши на русском языке грамотно и красиво

Контент: {theme_config['prompt']}

Напиши готовый пост в формате как для публикации, без лишних комментариев."""
        
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
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                            return content
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self.get_fallback_post(theme, size_config)
    
    def get_fallback_post(self, theme: str, size_config: dict) -> str:
        fallbacks = {
            "ai_news": "🤖 Искусственный интеллект меняет мир! А вы используете нейросети в работе? Расскажите в комментариях!",
            "crypto": "🪙 Криптовалюты - это будущее финансов! Как вы относитесь к биткоину?",
            "nft": "🎨 NFT открывают новые горизонты для творчества! У вас есть NFT?",
            "telegram": "📱 Telegram становится лучше с каждым днем! Какую функцию вы ждете больше всего?",
        }
        content = fallbacks.get(theme, f"✨ Новый пост на тему {POSTING_THEMES[theme]['name']}! Делитесь мыслями в комментариях! ✨")
        return content[:size_config["chars"]]
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                              theme: str, size: str, user_id: int = None) -> bool:
        content = await self.generate_post(theme, size)
        
        # Красивое оформление поста
        theme_config = POSTING_THEMES[theme]
        size_config = POST_SIZES[size]
        
        post_text = f"""
{theme_config['emoji']} *{theme_config['name']}*

{content}

━━━━━━━━━━━━━━━━━━━━
✨ *Пост создан с помощью ИИ*
📏 Размер: {size_config['emoji']} {size_config['name']}
{theme_config['hashtags']}
━━━━━━━━━━━━━━━━━━━━
"""
        
        try:
            await context.bot.send_message(
                chat_id=channel_id,
                text=post_text,
                parse_mode='Markdown'
            )
            
            if user_id:
                user = self.get_user(user_id)
                user.add_post()
                self.save_data()
            
            return True
        except Exception as e:
            logger.error(f"Ошибка публикации: {e}")
            return False

bot = PostingBot()

# ==================== КРАСИВЫЕ КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 МОИ КАНАЛЫ", callback_data="my_channels")],
        [InlineKeyboardButton("➕ ДОБАВИТЬ КАНАЛ", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 АВТОПОСТИНГ", callback_data="auto_menu")],
        [InlineKeyboardButton("⚡ РАЗОВЫЙ ПОСТ", callback_data="quick_post")],
        [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats")],
        [InlineKeyboardButton("💎 ТАРИФЫ", callback_data="tariffs")],
        [InlineKeyboardButton("🆘 ПОМОЩЬ", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(selected_theme=None):
    keyboard = []
    row = []
    for i, (theme_key, theme) in enumerate(POSTING_THEMES.items()):
        marker = "✅ " if selected_theme == theme_key else ""
        row.append(InlineKeyboardButton(f"{theme['emoji']} {marker}{theme['name']}", callback_data=f"theme_{theme_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(selected_size=None):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        marker = "✅ " if selected_size == size_key else ""
        keyboard.append([InlineKeyboardButton(f"{size['emoji']} {marker}{size['name']} - {size['desc']}", callback_data=f"size_{size_key}")])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard(user_tariff):
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        marker = "✅" if user_tariff == tariff_key else "🔘"
        keyboard.append([InlineKeyboardButton(f"{tariff['emoji']} {marker} {tariff['name']}", callback_data=f"tariff_{tariff_key}")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_channels_keyboard(user: UserData):
    keyboard = []
    for channel in user.channels:
        config = bot.auto_configs.get(f"{user.user_id}_{channel['id']}")
        status = "✅" if config and config.is_active else "⏸"
        keyboard.append([InlineKeyboardButton(f"{status} 📢 {channel['name'][:30]}", callback_data=f"auto_config_{channel['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(channel_id):
    keyboard = []
    row = []
    intervals = [5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440]
    for interval in intervals:
        if interval < 60:
            text = f"{interval} мин"
        elif interval == 60:
            text = "1 час"
        elif interval == 1440:
            text = "24 часа"
        else:
            text = f"{interval//60} часа"
        
        row.append(InlineKeyboardButton(text, callback_data=f"interval_{channel_id}_{interval}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="auto_menu")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = f"""
✨ *ДОБРО ПОЖАЛОВАТЬ, {user.first_name.upper()}!* ✨

🤖 *AI Пост-Бот* - твой персональный контент-менеджер

━━━━━━━━━━━━━━━━━━━━
🎯 *ВОЗМОЖНОСТИ:*
━━━━━━━━━━━━━━━━━━━━

🧠 *Умный ИИ* - посты на основе GigaChat
🎨 *20+ ТЕМ* - от крипты до психологии
📏 *5 РАЗМЕРОВ* - от мини до максимального
🤖 *АВТОПОСТИНГ* - с настраиваемым интервалом
🔄 *ПЕРЕПОСТ* - из любых каналов
📊 *СТАТИСТИКА* - контроль публикаций

━━━━━━━━━━━━━━━━━━━━
💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫ!*
━━━━━━━━━━━━━━━━━━━━

🌟 СТАРТ - 1 канал, 10 постов/день
📝 БЛОГЕР - 3 канала, 30 постов/день
💎 PRO - 10 каналов, 100 постов/день
👑 UNLIMITED - безлимит!

━━━━━━━━━━━━━━━━━━━━
👇 *НАЧНИ ПРЯМО СЕЙЧАС:*
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    tariff = TARIFFS[user_data.tariff]
    
    if len(user_data.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ *Лимит каналов достигнут!*\n\n"
            f"📊 Ваш тариф: {tariff['emoji']} {tariff['name']}\n"
            f"📢 Максимум: {tariff['channels']} каналов\n\n"
            f"💡 Хотите больше? Просто выберите другой бесплатный тариф!",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        f"📢 *ДОБАВЛЕНИЕ КАНАЛА*\n\n"
        f"1️⃣ Добавьте бота в канал как *администратора*\n"
        f"2️⃣ Отправьте сюда *ссылку* или *username* канала\n"
        f"3️⃣ Или *перешлите* любое сообщение из канала\n\n"
        f"✨ *Примеры:* @channel или https://t.me/channel\n\n"
        f"⚡ Осталось мест: {tariff['channels'] - len(user_data.channels)}/{tariff['channels']}",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_channel'):
        return
    
    user = update.effective_user
    user_data = bot.get_user(user.id)
    text = update.message.text.strip()
    
    channel_id = None
    channel_name = None
    
    # Парсим ссылку или username
    if text.startswith('@'):
        username = text[1:]
        try:
            chat = await context.bot.get_chat(username)
            channel_id = str(chat.id)
            channel_name = chat.title
        except:
            pass
    
    elif 't.me/' in text:
        username = text.split('t.me/')[-1].split('/')[0].split('?')[0]
        try:
            chat = await context.bot.get_chat(username)
            channel_id = str(chat.id)
            channel_name = chat.title
        except:
            pass
    
    elif update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
    
    if not channel_id:
        await update.message.reply_text("❌ *Не удалось определить канал!*\n\nПопробуйте:\n• Отправить username: @channel\n• Отправить ссылку: https://t.me/channel\n• Переслать сообщение из канала", parse_mode='Markdown')
        return
    
    # Проверяем, не добавлен ли уже
    for ch in user_data.channels:
        if ch['id'] == channel_id:
            await update.message.reply_text(f"❌ *Канал уже добавлен!*\n\n📢 {channel_name}", parse_mode='Markdown')
            context.user_data['awaiting_channel'] = False
            return
    
    # Добавляем канал
    user_data.channels.append({
        'id': channel_id,
        'name': channel_name,
        'added_at': time.time()
    })
    bot.save_data()
    
    await update.message.reply_text(
        f"✅ *КАНАЛ УСПЕШНО ДОБАВЛЕН!*\n\n"
        f"📢 *Название:* {channel_name}\n"
        f"🆔 *ID:* `{channel_id}`\n\n"
        f"🎯 *Что дальше?*\n"
        f"• Настройте /auto_posting для автоматических постов\n"
        f"• Или создайте /quick_post разовый пост\n\n"
        f"✨ Используйте главное меню для управления!",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = False

async def auto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    
    if not user_data.channels:
        await update.message.reply_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через кнопку '➕ ДОБАВИТЬ КАНАЛ'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_auto_channels_keyboard(user_data)
    await update.message.reply_text(
        "🤖 *АВТОПОСТИНГ*\n\n"
        "Выберите канал для настройки автоматической публикации постов:\n\n"
        "✅ - активен | ⏸ - остановлен",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_auto_post(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    
    # Находим канал
    channel = None
    for ch in user_data.channels:
        if ch['id'] == channel_id:
            channel = ch
            break
    
    if not channel:
        await update.callback_query.edit_message_text("❌ Канал не найден")
        return
    
    config = bot.auto_configs.get(f"{user.id}_{channel_id}")
    
    if config:
        theme = POSTING_THEMES[config.theme]
        size = POST_SIZES[config.size]
        interval = config.interval_minutes
        status = "✅ АКТИВЕН" if config.is_active else "⏸ ОСТАНОВЛЕН"
        
        if interval < 60:
            interval_text = f"{interval} минут"
        elif interval == 60:
            interval_text = "1 час"
        else:
            interval_text = f"{interval//60} часов"
        
        text = f"""
⚙️ *НАСТРОЙКИ АВТОПОСТИНГА*

📢 *Канал:* {channel['name']}

🎨 *Тема:* {theme['emoji']} {theme['name']}
📏 *Размер:* {size['emoji']} {size['name']}
⏱ *Интервал:* {interval_text}
🔄 *Статус:* {status}

━━━━━━━━━━━━━━━━━━━━
"""
    else:
        text = f"""
⚙️ *НАСТРОЙКИ АВТОПОСТИНГА*

📢 *Канал:* {channel['name']}

⚠️ *Автопостинг не настроен!*

Выберите параметры ниже:
━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = [
        [InlineKeyboardButton("🎨 ВЫБРАТЬ ТЕМУ", callback_data=f"set_theme_{channel_id}")],
        [InlineKeyboardButton("📏 ВЫБРАТЬ РАЗМЕР", callback_data=f"set_size_{channel_id}")],
        [InlineKeyboardButton("⏱ ВЫБРАТЬ ИНТЕРВАЛ", callback_data=f"set_interval_{channel_id}")],
    ]
    
    if config and config.is_active:
        keyboard.append([InlineKeyboardButton("⏸ ОСТАНОВИТЬ", callback_data=f"stop_auto_{channel_id}")])
    elif config and not config.is_active:
        keyboard.append([InlineKeyboardButton("▶️ ЗАПУСТИТЬ", callback_data=f"start_auto_{channel_id}")])
    
    if config:
        keyboard.append([InlineKeyboardButton("🗑 ОТКЛЮЧИТЬ АВТОПОСТИНГ", callback_data=f"delete_auto_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="auto_menu")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def quick_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    
    if not user_data.channels:
        await update.message.reply_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через кнопку '➕ ДОБАВИТЬ КАНАЛ'",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['post_mode'] = 'select_channel'
    
    keyboard = []
    for channel in user_data.channels:
        keyboard.append([InlineKeyboardButton(f"📢 {channel['name'][:40]}", callback_data=f"post_channel_{channel['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")])
    
    await update.message.reply_text(
        "⚡ *СОЗДАНИЕ РАЗОВОГО ПОСТА*\n\n"
        "Выберите канал для публикации:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    
    text = "💎 *БЕСПЛАТНЫЕ ТАРИФЫ*\n\n"
    text += "✨ Все тарифы полностью бесплатны!\n"
    text += "Просто выбери подходящий и пользуйся:\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        marker = "✅" if user_data.tariff == tariff_key else "🔘"
        text += f"{tariff['emoji']} *{tariff['name']}* {marker}\n"
        text += f"   📢 Каналов: {tariff['channels']}\n"
        text += f"   📝 Постов в день: {tariff['posts_per_day']}\n"
        text += f"   🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}\n"
        text += f"   ⏰ Расписание: {'✅' if tariff['can_schedule'] else '❌'}\n\n"
    
    keyboard = await get_tariffs_keyboard(user_data.tariff)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    tariff = TARIFFS[user_data.tariff]
    
    if not user_data.channels:
        await update.message.reply_text(
            "📢 *У вас пока нет каналов*\n\n"
            "Нажмите '➕ ДОБАВИТЬ КАНАЛ' чтобы начать!",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard()
        )
        return
    
    text = f"📢 *ВАШИ КАНАЛЫ* ({len(user_data.channels)}/{tariff['channels']})\n\n"
    
    for i, channel in enumerate(user_data.channels, 1):
        config = bot.auto_configs.get(f"{user.id}_{channel['id']}")
        auto_status = "✅ Авто" if config and config.is_active else "⏸ Нет авто"
        
        text += f"{i}. *{channel['name']}*\n"
        text += f"   🆔 `{channel['id']}`\n"
        text += f"   🤖 {auto_status}\n\n"
    
    keyboard = []
    for channel in user_data.channels:
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить {channel['name'][:30]}", callback_data=f"delete_channel_{channel['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = bot.get_user(user.id)
    tariff = TARIFFS[user_data.tariff]
    
    user_data.reset_daily()
    
    text = f"""
📊 *СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ*

👤 *Пользователь:* {user_data.first_name}
💎 *Тариф:* {tariff['emoji']} {tariff['name']}

━━━━━━━━━━━━━━━━━━━━
📢 *Каналы:* {len(user_data.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {user_data.posts_today}/{tariff['posts_per_day']}
⏳ *Осталось сегодня:* {tariff['posts_per_day'] - user_data.posts_today}

━━━━━━━━━━━━━━━━━━━━
🤖 *Автопостинг:*

"""
    auto_count = 0
    for key, config in bot.auto_configs.items():
        if key.startswith(str(user.id)):
            auto_count += 1
            theme = POSTING_THEMES[config.theme]
            text += f"• {theme['emoji']} {config.channel_name[:20]}: {'✅' if config.is_active else '⏸'}\n"
    
    text += f"\nВсего авто-настроек: {auto_count}"
    
    keyboard = [[InlineKeyboardButton("🔄 ОБНОВИТЬ", callback_data="stats"), InlineKeyboardButton("🔙 НАЗАД", callback_data="back_main")]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *ПОМОЩЬ ПО БОТУ*

━━━━━━━━━━━━━━━━━━━━
📌 *ОСНОВНЫЕ КОМАНДЫ*
━━━━━━━━━━━━━━━━━━━━

/start - Главное меню
/menu - Открыть меню

━━━━━━━━━━━━━━━━━━━━
🎯 *ЧТО МЫ УМЕЕМ?*
━━━━━━━━━━━━━━━━━━━━

🧠 *Умный ИИ (GigaChat)*
Генерирует уникальные посты на любые темы

🎨 *20+ ТЕМАТИК*
От криптовалют и NFT до психологии и мотивации

📏 *5 РАЗМЕРОВ ПОСТОВ*
Выбирай длину под свой канал

🤖 *АВТОПОСТИНГ*
Настрой расписание и бот будет постить сам

🔄 *ПЕРЕПОСТ*
Копируй посты из других каналов

━━━━━━━━━━━━━━━━━━━━
💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫ!*
━━━━━━━━━━━━━━━━━━━━

🌟 СТАРТ - 1 канал, 10 постов/день
📝 БЛОГЕР - 3 канала, 30 постов/день  
💎 PRO - 10 каналов, 100 постов/день
👑 UNLIMITED - безлимит!

━━━━━━━━━━━━━━━━━━━━
❓ *ВОПРОСЫ?*
━━━━━━━━━━━━━━━━━━━━

Напишите @ для связи
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== ОБРАБОТЧИКИ CALLBACK ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    user_data = bot.get_user(user.id)
    
    # Главное меню
    if data == "back_main":
        keyboard = await get_main_keyboard()
        await query.edit_message_text("🏠 *ГЛАВНОЕ МЕНЮ*\n\nВыберите действие:", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "add_channel":
        await add_channel(update, context)
    
    elif data == "auto_menu":
        await auto_menu(update, context)
    
    elif data == "quick_post":
        await quick_post(update, context)
    
    elif data == "stats":
        await stats(update, context)
    
    elif data == "tariffs":
        await tariffs(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    # Настройка автопостинга
    elif data.startswith("auto_config_"):
        channel_id = data.replace("auto_config_", "")
        await configure_auto_post(update, context, channel_id)
    
    # Выбор темы
    elif data.startswith("set_theme_"):
        channel_id = data.replace("set_theme_", "")
        context.user_data['config_channel'] = channel_id
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 *ВЫБЕРИТЕ ТЕМУ ДЛЯ АВТОПОСТИНГА*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data.startswith("theme_") and 'config_channel' in context.user_data:
        theme = data.replace("theme_", "")
        channel_id = context.user_data['config_channel']
        key = f"{user.id}_{channel_id}"
        
        if key in bot.auto_configs:
            bot.auto_configs[key].theme = theme
        else:
            # Находим название канала
            channel_name = "Канал"
            for ch in user_data.channels:
                if ch['id'] == channel_id:
                    channel_name = ch['name']
                    break
            
            bot.auto_configs[key] = AutoPostConfig(
                channel_id=channel_id,
                channel_name=channel_name,
                theme=theme,
                size="medium",
                interval_minutes=60
            )
        
        bot.save_data()
        await query.edit_message_text(f"✅ *Тема выбрана:* {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\nТеперь выберите размер поста...")
        await configure_auto_post(update, context, channel_id)
        del context.user_data['config_channel']
    
    # Выбор размера
    elif data.startswith("set_size_"):
        channel_id = data.replace("set_size_", "")
        context.user_data['size_channel'] = channel_id
        config_key = f"{user.id}_{channel_id}"
        current_size = bot.auto_configs[config_key].size if config_key in bot.auto_configs else None
        keyboard = await get_sizes_keyboard(current_size)
        await query.edit_message_text("📏 *ВЫБЕРИТЕ РАЗМЕР ПОСТОВ*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data.startswith("size_") and 'size_channel' in context.user_data:
        size = data.replace("size_", "")
        channel_id = context.user_data['size_channel']
        key = f"{user.id}_{channel_id}"
        
        if key in bot.auto_configs:
            bot.auto_configs[key].size = size
            bot.save_data()
        
        await query.edit_message_text(f"✅ *Размер установлен:* {POST_SIZES[size]['emoji']} {POST_SIZES[size]['name']}")
        await configure_auto_post(update, context, channel_id)
        del context.user_data['size_channel']
    
    # Выбор интервала
    elif data.startswith("set_interval_"):
        channel_id = data.replace("set_interval_", "")
        context.user_data['interval_channel'] = channel_id
        keyboard = await get_intervals_keyboard(channel_id)
        await query.edit_message_text("⏱ *ВЫБЕРИТЕ ИНТЕРВАЛ АВТОПОСТИНГА*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data.startswith("interval_"):
        parts = data.split("_")
        channel_id = parts[1]
        interval = int(parts[2])
        key = f"{user.id}_{channel_id}"
        
        if key in bot.auto_configs:
            bot.auto_configs[key].interval_minutes = interval
            bot.save_data()
        
        interval_text = f"{interval} минут" if interval < 60 else f"{interval//60} часов"
        await query.edit_message_text(f"✅ *Интервал установлен:* {interval_text}")
        await configure_auto_post(update, context, channel_id)
        del context.user_data['interval_channel']
    
    # Управление автопостингом
    elif data.startswith("start_auto_"):
        channel_id = data.replace("start_auto_", "")
        key = f"{user.id}_{channel_id}"
        if key in bot.auto_configs:
            bot.auto_configs[key].is_active = True
            bot.save_data()
            await query.edit_message_text("✅ *Автопостинг запущен!*")
            await configure_auto_post(update, context, channel_id)
    
    elif data.startswith("stop_auto_"):
        channel_id = data.replace("stop_auto_", "")
        key = f"{user.id}_{channel_id}"
        if key in bot.auto_configs:
            bot.auto_configs[key].is_active = False
            bot.save_data()
            await query.edit_message_text("⏸ *Автопостинг остановлен*")
            await configure_auto_post(update, context, channel_id)
    
    elif data.startswith("delete_auto_"):
        channel_id = data.replace("delete_auto_", "")
        key = f"{user.id}_{channel_id}"
        if key in bot.auto_configs:
            del bot.auto_configs[key]
            bot.save_data()
            await query.edit_message_text("🗑 *Автопостинг отключен для этого канала*")
            await auto_menu(update, context)
    
    # Удаление канала
    elif data.startswith("delete_channel_"):
        channel_id = data.replace("delete_channel_", "")
        user_data.channels = [ch for ch in user_data.channels if ch['id'] != channel_id]
        
        # Удаляем настройки автопостинга
        key = f"{user.id}_{channel_id}"
        if key in bot.auto_configs:
            del bot.auto_configs[key]
        
        bot.save_data()
        await query.edit_message_text("✅ *Канал удален!*")
        await my_channels(update, context)
    
    # Смена тарифа
    elif data.startswith("tariff_"):
        tariff_key = data.replace("tariff_", "")
        if tariff_key in TARIFFS:
            user_data.tariff = tariff_key
            bot.save_data()
            await query.edit_message_text(f"✅ *Тариф изменен на {TARIFFS[tariff_key]['emoji']} {TARIFFS[tariff_key]['name']}!*\n\nВсе возможности уже доступны!")
            await tariffs(update, context)
    
    # Разовый пост - выбор канала
    elif data.startswith("post_channel_"):
        channel_id = data.replace("post_channel_", "")
        context.user_data['post_channel'] = channel_id
        context.user_data['post_mode'] = 'select_theme'
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 *ВЫБЕРИТЕ ТЕМУ ДЛЯ ПОСТА*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data.startswith("theme_") and context.user_data.get('post_mode') == 'select_theme':
        theme = data.replace("theme_", "")
        context.user_data['post_theme'] = theme
        context.user_data['post_mode'] = 'select_size'
        keyboard = await get_sizes_keyboard()
        await query.edit_message_text("📏 *ВЫБЕРИТЕ РАЗМЕР ПОСТА*", parse_mode='Markdown', reply_markup=keyboard)
    
    elif data.startswith("size_") and context.user_data.get('post_mode') == 'select_size':
        size = data.replace("size_", "")
        channel_id = context.user_data.get('post_channel')
        theme = context.user_data.get('post_theme')
        
        if not user_data.can_post():
            await query.edit_message_text(
                f"❌ *Лимит постов на сегодня исчерпан!*\n\n"
                f"📝 Сегодня: {user_data.posts_today}/{TARIFFS[user_data.tariff]['posts_per_day']}\n"
                f"🔄 Завтра лимит обновится!",
                parse_mode='Markdown'
            )
            context.user_data['post_mode'] = None
            return
        
        await query.edit_message_text(f"🎲 *Генерирую пост*\n\nТема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\nРазмер: {POST_SIZES[size]['emoji']} {POST_SIZES[size]['name']}\n\n⏳ Пожалуйста, подождите...", parse_mode='Markdown')
        
        success = await bot.post_to_channel(context, channel_id, theme, size, user.id)
        
        if success:
            await query.edit_message_text(
                f"✅ *ПОСТ УСПЕШНО ОПУБЛИКОВАН!*\n\n"
                f"📢 В канал: {channel_id}\n"
                f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
                f"📏 Размер: {POST_SIZES[size]['name']}\n\n"
                f"📊 Осталось постов сегодня: {TARIFFS[user_data.tariff]['posts_per_day'] - user_data.posts_today}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ *Ошибка при публикации поста!*\n\nПопробуйте позже или выберите другую тему.", parse_mode='Markdown')
        
        context.user_data['post_mode'] = None

# ==================== АВТОПОСТИНГ ====================
async def check_auto_posts(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и выполнение автопостинга"""
    current_time = time.time()
    
    for key, config in list(bot.auto_configs.items()):
        if not config.is_active:
            continue
        
        if current_time - config.last_post >= config.interval_minutes * 60:
            # Находим пользователя
            user_id = int(key.split('_')[0])
            if user_id in bot.users:
                user = bot.users[user_id]
                
                if user.can_post():
                    await bot.post_to_channel(context, config.channel_id, config.theme, config.size, user_id)
                    config.last_post = current_time
                    bot.save_data()
                    logger.info(f"✅ Автопост в {config.channel_name} на тему {config.theme}")

# ==================== ЗАПУСК БОТА ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    
    # Задача автопостинга (каждые 30 секунд)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_auto_posts, interval=30, first=10)
    
    logger.info("="*50)
    logger.info("🚀 БОТ АВТОПОСТИНГА ЗАПУЩЕН!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Тарифов: {len(TARIFFS)} (ВСЕ БЕСПЛАТНЫЕ)")
    logger.info(f"📏 Размеров постов: {len(POST_SIZES)}")
    logger.info("="*50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
