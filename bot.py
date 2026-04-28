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

# ==================== GIGACHAT API ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== БЕСПЛАТНЫЕ ТАРИФЫ ====================
TARIFFS = {
    "starter": {
        "name": "🌟 Стартовый",
        "emoji": "🌟",
        "channels": 1,
        "posts_per_day": 10,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 60,
        "color": "#00CED1"
    },
    "pro": {
        "name": "⚡ Профессиональный",
        "emoji": "⚡",
        "channels": 5,
        "posts_per_day": 50,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 30,
        "color": "#FF6B6B"
    },
    "unlimited": {
        "name": "👑 Безлимитный",
        "emoji": "👑",
        "channels": 999,
        "posts_per_day": 999,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 15,
        "color": "#FFD700"
    }
}

# ==================== 20 ТЕМ ДЛЯ ПОСТИНГА ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "ИИ и технологии",
        "emoji": "🤖",
        "hashtags": "#ИИ #Нейросети #Технологии",
        "prompt": "Создай интересный пост о последних новостях в мире искусственного интеллекта, нейросетях и технологиях будущего. Напиши увлекательно и познавательно."
    },
    "crypto": {
        "name": "Криптовалюты",
        "emoji": "🪙",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн",
        "prompt": "Создай пост о криптовалютах, биткоине, блокчейн технологиях и децентрализации."
    },
    "nft": {
        "name": "NFT и искусство",
        "emoji": "🎨",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная",
        "prompt": "Создай пост о мире NFT, цифровом искусстве, метавселенных и коллекционировании."
    },
    "telegram": {
        "name": "Telegram",
        "emoji": "📱",
        "hashtags": "#Telegram #Мессенджеры #Общение",
        "prompt": "Создай пост о Telegram: новые функции, боты, каналы, секретные возможности."
    },
    "business": {
        "name": "Бизнес",
        "emoji": "💼",
        "hashtags": "#Бизнес #Предпринимательство #Успех",
        "prompt": "Создай пост о бизнесе, предпринимательстве, стартапах и инвестициях."
    },
    "marketing": {
        "name": "Маркетинг",
        "emoji": "📊",
        "hashtags": "#Маркетинг #SMM #Реклама",
        "prompt": "Создай пост о маркетинге, SMM, рекламе и продвижении бизнеса."
    },
    "programming": {
        "name": "Программирование",
        "emoji": "💻",
        "hashtags": "#Программирование #IT #Код",
        "prompt": "Создай полезный пост о программировании, языках кода и IT-сфере."
    },
    "design": {
        "name": "Дизайн",
        "emoji": "🎨",
        "hashtags": "#Дизайн #Графика #Творчество",
        "prompt": "Создай вдохновляющий пост о дизайне, графике и креативности."
    },
    "psychology": {
        "name": "Психология",
        "emoji": "🧠",
        "hashtags": "#Психология #Саморазвитие #Мотивация",
        "prompt": "Создай полезный пост о психологии, саморазвитии и личностном росте."
    },
    "health": {
        "name": "Здоровье",
        "emoji": "⚕️",
        "hashtags": "#Здоровье #Спорт #ЗОЖ",
        "prompt": "Создай пост о здоровье, правильном питании и здоровом образе жизни."
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "hashtags": "#Спорт #Фитнес #Тренировки",
        "prompt": "Создай пост о спорте, тренировках и спортивных достижениях."
    },
    "travel": {
        "name": "Путешествия",
        "emoji": "✈️",
        "hashtags": "#Путешествия #Туризм #Мир",
        "prompt": "Создай пост о путешествиях, туризме и красивых местах мира."
    },
    "food": {
        "name": "Кулинария",
        "emoji": "🍳",
        "hashtags": "#Кулинария #Рецепты #Еда",
        "prompt": "Создай аппетитный пост о кулинарии, рецептах и вкусной еде."
    },
    "movies": {
        "name": "Кино",
        "emoji": "🎬",
        "hashtags": "#Кино #Фильмы #Сериалы",
        "prompt": "Создай пост о новинках кино, сериалах и интересных фильмах."
    },
    "music": {
        "name": "Музыка",
        "emoji": "🎵",
        "hashtags": "#Музыка #Новинки #Хиты",
        "prompt": "Создай пост о музыке, новинках и музыкальных трендах."
    },
    "gaming": {
        "name": "Игры",
        "emoji": "🎮",
        "hashtags": "#Игры #Гейминг #Новинки",
        "prompt": "Создай пост о видеоиграх, новинках и игровой индустрии."
    },
    "science": {
        "name": "Наука",
        "emoji": "🔬",
        "hashtags": "#Наука #Открытия #Исследования",
        "prompt": "Создай пост о научных открытиях и интересных фактах."
    },
    "education": {
        "name": "Образование",
        "emoji": "📚",
        "hashtags": "#Образование #Учеба #Знания",
        "prompt": "Создай пост об образовании, обучении и саморазвитии."
    },
    "motivation": {
        "name": "Мотивация",
        "emoji": "💪",
        "hashtags": "#Мотивация #Успех #Цели",
        "prompt": "Создай вдохновляющий пост о мотивации и достижении целей."
    },
    "news": {
        "name": "Новости мира",
        "emoji": "🌍",
        "hashtags": "#Новости #Мир #События",
        "prompt": "Создай пост о главных мировых новостях и событиях."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "short": {
        "name": "Короткий",
        "emoji": "📝",
        "chars": "200-400",
        "max_tokens": 600,
        "icon": "🔹"
    },
    "medium": {
        "name": "Средний",
        "emoji": "📄",
        "chars": "400-800",
        "max_tokens": 1000,
        "icon": "🔸"
    },
    "long": {
        "name": "Длинный",
        "emoji": "📖",
        "chars": "800-1200",
        "max_tokens": 1500,
        "icon": "📚"
    }
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class ChannelConfig:
    channel_id: str
    channel_name: str
    theme: str
    post_size: str
    is_active: bool = True
    interval_minutes: int = 60
    last_post: float = 0
    custom_prompt: Optional[str] = None

@dataclass
class UserData:
    user_id: int
    username: str
    first_name: str
    tariff: str = "starter"
    channels: List[ChannelConfig] = field(default_factory=list)
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    repost_sources: List[Dict] = field(default_factory=list)

# ==================== ХРАНИЛИЩЕ ====================
class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.post_history: List[Dict] = []
    
    def load_data(self):
        try:
            with open("users_data.json", "r", encoding='utf-8') as f:
                data = json.load(f)
                for user_id, user_data in data.items():
                    user = UserData(**{k: v for k, v in user_data.items() if k != 'channels'})
                    user.channels = [ChannelConfig(**ch) for ch in user_data.get('channels', [])]
                    self.users[int(user_id)] = user
        except:
            pass
    
    def save_data(self):
        data = {}
        for user_id, user in self.users.items():
            data[str(user_id)] = {
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "tariff": user.tariff,
                "posts_today": user.posts_today,
                "last_reset": user.last_reset,
                "repost_sources": user.repost_sources,
                "channels": [{
                    "channel_id": ch.channel_id,
                    "channel_name": ch.channel_name,
                    "theme": ch.theme,
                    "post_size": ch.post_size,
                    "is_active": ch.is_active,
                    "interval_minutes": ch.interval_minutes,
                    "last_post": ch.last_post
                } for ch in user.channels]
            }
        with open("users_data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            self.save_data()
        return self.users[user_id]
    
    def reset_daily_posts(self):
        current_time = time.time()
        for user in self.users.values():
            if current_time - user.last_reset > 86400:
                user.posts_today = 0
                user.last_reset = current_time
        self.save_data()
    
    def can_post(self, user: UserData) -> bool:
        tariff = TARIFFS[user.tariff]
        return user.posts_today < tariff["posts_per_day"]
    
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
    
    async def generate_post(self, theme: str, size: str, custom_topic: str = None) -> str:
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        topic = custom_topic if custom_topic else theme_config['name']
        
        prompt = f"""Ты профессиональный контент-мейкер и копирайтер. 
Создай КРАСИВЫЙ и ИНТЕРЕСНЫЙ пост на тему: {topic}

Требования к посту:
- Длина: {size_config['chars']} символов
- Используй красивые эмодзи для украшения
- Разбей текст на смысловые абзацы
- Добавь вопрос к подписчикам в конце
- Добавь призыв к действию
- Пост должен быть уникальным и полезным

Структура:
1. Яркий заголовок с эмодзи
2. Основной контент (интересные факты/советы)
3. Вопрос для обсуждения
4. Хэштеги: {theme_config['hashtags']}

Напиши ПОСТ СРАЗУ, без лишних слов и объяснений:"""
        
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
                        "max_tokens": size_config["max_tokens"]
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                            # Добавляем разделители для красоты
                            post = f"""
{content}

━━━━━━━━━━━━━━━━━━━━
💬 *Обсуждение в комментариях!*
✨ *Ставь ❤️ если понравилось!*
━━━━━━━━━━━━━━━━━━━━
"""
                            return post
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self.get_fallback_post(theme, size_config)
    
    def get_fallback_post(self, theme: str, size_config: dict) -> str:
        fallbacks = {
            "ai_news": "🤖 *ИИ меняет мир!*\n\nНейросети становятся умнее с каждым днем. Какие технологии будущего вас впечатляют?\n\n❓ *А вы используете ИИ в работе?*\n\n#ИИ #ТехнологииБудущего",
            "telegram": "📱 *Telegram: больше чем мессенджер!*\n\nПостоянные обновления, боты и каналы делают Telegram уникальным.\n\n❓ *Какая фишка Telegram вам нравится больше всего?*\n\n#Telegram #Мессенджеры",
            "crypto": "🪙 *Криптовалюта: будущее финансов?*\n\nДецентрализация меняет мир. Следите за трендами!\n\n❓ *Инвестируете в крипту?*\n\n#Криптовалюта #Биткоин"
        }
        return fallbacks.get(theme, f"""
{size_config['emoji']} *Новый интересный пост!*

✨ Узнавайте первыми самые актуальные новости и тренды!

❓ *Что вы думаете по этой теме? Делитесь в комментариях!*

{POSTING_THEMES.get(theme, {}).get('hashtags', '#Новости')}
""")
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_config: ChannelConfig, user: UserData) -> bool:
        content = await self.generate_post(channel_config.theme, channel_config.post_size)
        
        try:
            await context.bot.send_message(
                chat_id=int(channel_config.channel_id),
                text=content,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            
            channel_config.last_post = time.time()
            user.posts_today += 1
            
            self.post_history.append({
                "channel": channel_config.channel_name,
                "theme": channel_config.theme,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            self.save_data()
            return True
        except Exception as e:
            logger.error(f"Ошибка постинга: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🤖 Настройка автопостинга", callback_data="auto_setup")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="theme_select")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="size_select")],
        [InlineKeyboardButton("⚡ Случайный пост", callback_data="random_post")],
        [InlineKeyboardButton("🔄 Перепост из канала", callback_data="repost_setup")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    user = bot.get_user(user_id)
    keyboard = []
    for ch in user.channels:
        status = "✅" if ch.is_active else "⏸"
        keyboard.append([InlineKeyboardButton(
            f"{status} {ch.channel_name[:20]}", 
            callback_data=f"channel_{ch.channel_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(page: int = 0):
    themes = list(POSTING_THEMES.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    
    keyboard = []
    for theme_key, theme in themes[start:end]:
        keyboard.append([InlineKeyboardButton(
            f"{theme['emoji']} {theme['name']}",
            callback_data=f"theme_{theme_key}"
        )])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"theme_page_{page-1}"))
    if end < len(themes):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"theme_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard():
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['icon']} {size['name']} ({size['chars']} симв.)",
            callback_data=f"size_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_setup_keyboard(user_id: int):
    user = bot.get_user(user_id)
    keyboard = []
    
    for ch in user.channels:
        keyboard.append([InlineKeyboardButton(
            f"⚙️ {ch.channel_name[:25]}",
            callback_data=f"auto_channel_{ch.channel_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channel_settings_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("🎨 Сменить тему", callback_data=f"ch_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Сменить размер", callback_data=f"ch_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал (минуты)", callback_data=f"ch_interval_{channel_id}")],
        [InlineKeyboardButton("▶️ Включить", callback_data=f"ch_on_{channel_id}")],
        [InlineKeyboardButton("⏸ Выключить", callback_data=f"ch_off_{channel_id}")],
        [InlineKeyboardButton("🗑 Удалить канал", callback_data=f"ch_del_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.load_data()
    bot.reset_daily_posts()
    
    bot.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome = f"""
✨ *Добро пожаловать, {user.first_name}!* ✨

🤖 *Бот для автопостинга с ИИ (GigaChat)*

🎯 *Что я умею:*
✅ Генерировать уникальные посты через ИИ
✅ Автоматически постить в ваши каналы
✅ 20 разных тематик на выбор
✅ Настройка размера постов
✅ Перепост из других каналов
✅ Все функции БЕСПЛАТНО!

📊 *Доступные тарифы:* Все БЕСПЛАТНЫЕ!
• 🌟 Стартовый: 1 канал, 10 постов/день
• ⚡ Профессиональный: 5 каналов, 50 постов/день  
• 👑 Безлимитный: безлимит каналов и постов

🚀 *Как начать:*
1️⃣ Нажмите "➕ Добавить канал"
2️⃣ Добавьте бота в канал как администратора
3️⃣ Настройте автопостинг

👇 *Выберите действие:*
"""
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=await get_main_keyboard())

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ *Добавьте бота в канал как администратора*\n"
        "   ID бота: @YourBotUsername\n\n"
        "2️⃣ *Перешлите любое сообщение из канала сюда*\n\n"
        "3️⃣ Или отправьте ID канала:\n"
        "   • username канала: @channel\n"
        "   • числовой ID: -100123456789\n\n"
        "💡 *Как получить ID?*\n"
        "Перешлите сообщение из канала боту @userinfobot",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        user = update.effective_user
        user_data = bot.get_user(user.id)
        text = update.message.text
        
        channel_id = None
        channel_name = None
        
        # Получаем ID канала
        if update.message.forward_from_chat:
            chat = update.message.forward_from_chat
            if chat.type in ['channel', 'supergroup']:
                channel_id = str(chat.id)
                channel_name = chat.title
        elif text.startswith('@'):
            try:
                chat = await context.bot.get_chat(text)
                channel_id = str(chat.id)
                channel_name = chat.title
            except:
                pass
        elif text.startswith('-100') or text.startswith('-'):
            channel_id = text
            try:
                chat = await context.bot.get_chat(int(text))
                channel_name = chat.title
            except:
                channel_name = "Канал"
        
        if channel_id:
            tariff = TARIFFS[user_data.tariff]
            if len(user_data.channels) >= tariff["channels"]:
                await update.message.reply_text(
                    f"❌ Лимит каналов для вашего тарифа: {tariff['channels']}\n"
                    f"💡 Используйте тариф ⚡ Профессиональный или 👑 Безлимитный"
                )
                return
            
            # Проверяем, не добавлен ли уже
            if any(ch.channel_id == channel_id for ch in user_data.channels):
                await update.message.reply_text("❌ Этот канал уже добавлен!")
                return
            
            # Добавляем канал
            new_channel = ChannelConfig(
                channel_id=channel_id,
                channel_name=channel_name,
                theme="ai_news",
                post_size="medium",
                interval_minutes=60
            )
            user_data.channels.append(new_channel)
            bot.save_data()
            
            await update.message.reply_text(
                f"✅ *Канал добавлен!*\n\n"
                f"📢 *Название:* {channel_name}\n"
                f"🎨 *Тема:* ИИ и технологии\n"
                f"📏 *Размер:* Средний\n"
                f"⏱ *Интервал:* 60 минут\n\n"
                f"🔧 *Настройте автопостинг:* /menu → Настройка автопостинга",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось определить канал.\n\n"
                "Попробуйте:\n"
                "1. Переслать сообщение ИЗ КАНАЛА (не из чата)\n"
                "2. Или отправить username канала с @\n"
                "3. Или числовой ID канала"
            )
        
        context.user_data['awaiting_channel'] = False

async def auto_setup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = bot.get_user(user_id)
    
    if not user_data.channels:
        await update.message.reply_text(
            "❌ *Нет добавленных каналов*\n\n"
            "Сначала добавьте канал через '➕ Добавить канал'",
            parse_mode='Markdown'
        )
        return
    
    text = "🤖 *Настройка автопостинга*\n\n"
    for ch in user_data.channels:
        theme = POSTING_THEMES.get(ch.theme, POSTING_THEMES["ai_news"])
        size = POST_SIZES.get(ch.post_size, POST_SIZES["medium"])
        status = "✅ АКТИВЕН" if ch.is_active else "⏸ ОСТАНОВЛЕН"
        text += f"\n📢 *{ch.channel_name}*\n"
        text += f"   🎨 Тема: {theme['emoji']} {theme['name']}\n"
        text += f"   📏 Размер: {size['icon']} {size['name']}\n"
        text += f"   ⏱ Интервал: {ch.interval_minutes} мин\n"
        text += f"   📊 Статус: {status}\n"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode='Markdown', 
            reply_markup=await get_auto_setup_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            text, parse_mode='Markdown',
            reply_markup=await get_auto_setup_keyboard(user_id)
        )

async def theme_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = await get_themes_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🎨 *Выберите тему для постов*\n\n"
            "Посты будут генерироваться ИИ на выбранную тему:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "🎨 *Выберите тему для постов*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def size_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = await get_sizes_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📏 *Выберите размер постов*\n\n"
            "Влияет на длину и детализацию:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "📏 *Выберите размер постов*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = bot.get_user(user_id)
    
    if not user_data.channels:
        await update.message.reply_text("❌ Сначала добавьте канал")
        return
    
    if not bot.can_post(user_data):
        await update.message.reply_text(
            "❌ *Лимит постов на сегодня исчерпан!*\n\n"
            f"📊 Сегодня: {user_data.posts_today}/{TARIFFS[user_data.tariff]['posts_per_day']}\n"
            "⏳ Лимит обнулится завтра",
            parse_mode='Markdown'
        )
        return
    
    theme = random.choice(list(POSTING_THEMES.keys()))
    size = random.choice(list(POST_SIZES.keys()))
    
    msg = await update.message.reply_text(
        f"🎲 *Генерирую случайный пост...*\n\n"
        f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
        f"📏 Размер: {POST_SIZES[size]['icon']} {POST_SIZES[size]['name']}\n\n"
        f"⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    success = await bot.post_to_channel(context, user_data.channels[0], user_data)
    
    if success:
        await msg.edit_text(
            f"✅ *Пост успешно опубликован!*\n\n"
            f"📢 В канале: {user_data.channels[0].channel_name}\n"
            f"📊 Осталось постов: {TARIFFS[user_data.tariff]['posts_per_day'] - user_data.posts_today}",
            parse_mode='Markdown'
        )
    else:
        await msg.edit_text("❌ *Ошибка при публикации.* Проверьте права бота в канале", parse_mode='Markdown')

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = bot.get_user(user_id)
    
    if not user_data.channels:
        await update.message.reply_text("❌ *Нет добавленных каналов*\n\nНажмите '➕ Добавить канал'", parse_mode='Markdown')
        return
    
    text = f"📋 *Ваши каналы* ({len(user_data.channels)}/{TARIFFS[user_data.tariff]['channels']})\n\n"
    for ch in user_data.channels:
        theme = POSTING_THEMES.get(ch.theme, POSTING_THEMES["ai_news"])
        status = "✅" if ch.is_active else "⏸"
        text += f"{status} *{ch.channel_name}*\n"
        text += f"   🎨 {theme['emoji']} {theme['name']}\n"
        text += f"   ⏱ Каждые {ch.interval_minutes} мин\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=await get_channels_keyboard(user_id))

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = bot.get_user(user_id)
    
    text = "💎 *Доступные тарифы* (ВСЕ БЕСПЛАТНЫЕ!)\n\n"
    
    for key, tariff in TARIFFS.items():
        current = " ✅ (Ваш)" if user_data.tariff == key else ""
        text += f"{tariff['emoji]} *{tariff['name']}{current}*\n"
        text += f"   📊 Каналов: {tariff['channels']}\n"
        text += f"   📝 Постов/день: {tariff['posts_per_day']}\n"
        text += f"   ⏱ Мин. интервал: {tariff['interval_min']} мин\n"
        text += f"   🔄 Перепост: ✅\n"
        text += f"   📅 Расписание: ✅\n\n"
    
    text += "🎁 *Все функции доступны бесплатно!*\n"
    text += "💡 Выберите тариф в зависимости от нужного количества каналов"
    
    keyboard = []
    for key in TARIFFS.keys():
        keyboard.append([InlineKeyboardButton(
            f"{TARIFFS[key]['emoji']} {TARIFFS[key]['name']}",
            callback_data=f"tariff_{key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = bot.get_user(user_id)
    tariff = TARIFFS[user_data.tariff]
    
    today = datetime.now().strftime("%d.%m.%Y")
    
    text = f"""
📊 *Статистика пользователя*

👤 *Имя:* {user_data.first_name}
💎 *Тариф:* {tariff['emoji']} {tariff['name']}

📈 *Сегодня ({today}):*
├ 📝 Постов: {user_data.posts_today}/{tariff['posts_per_day']}
├ 📢 Каналов: {len(user_data.channels)}/{tariff['channels']}
└ ⏳ Осталось: {tariff['posts_per_day'] - user_data.posts_today}

🎯 *Активность:*
├ 🤖 Активных каналов: {sum(1 for ch in user_data.channels if ch.is_active)}
└ 🔄 Настроено автопостинга: {len(user_data.channels)}

📊 *Всего постов в боте:* {len(bot.post_history)}

💡 *Совет:* Чем больше постов, тем активнее канал!
"""
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Назад", callback_data="back_main")
    ]]))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь по боту*

📌 *Основные команды:*
/start - Главное меню
/menu - Показать меню

✨ *Возможности бота:*

1️⃣ *Добавление канала*
• Добавьте бота в канал как администратора
• Перешлите сообщение из канала боту
• Бот автоматически определит канал

2️⃣ *Настройка автопостинга*
• Выберите тему (20 тем на выбор)
• Выберите размер поста
• Настройте интервал публикации
• Включите автопостинг

3️⃣ *Темы для постов (20):*
🤖 ИИ технологии | 🪙 Криптовалюты | 🎨 NFT
📱 Telegram | 💼 Бизнес | 📊 Маркетинг
💻 Программирование | 🎨 Дизайн | 🧠 Психология
⚕️ Здоровье | ⚽ Спорт | ✈️ Путешествия
🍳 Кулинария | 🎬 Кино | 🎵 Музыка
🎮 Игры | 🔬 Наука | 📚 Образование
💪 Мотивация | 🌍 Новости

4️⃣ *Размеры постов:*
• 📝 Короткий (200-400 символов)
• 📄 Средний (400-800 символов)
• 📖 Длинный (800-1200 символов)

💎 *Все тарифы БЕСПЛАТНЫЕ!*
• 🌟 Стартовый: 1 канал, 10 постов/день
• ⚡ Профессиональный: 5 каналов, 50 постов
• 👑 Безлимитный: безлимит каналов и постов

❓ *Вопросы:* @BotSupport

✨ *Начните прямо сейчас - добавьте канал!*
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== CALLBACK ОБРАБОТЧИКИ ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    user_id = query.from_user.id
    user_data = bot.get_user(user_id)
    
    # Главное меню
    if data == "back_main":
        await query.edit_message_text("🏠 *Главное меню*", parse_mode='Markdown', reply_markup=await get_main_keyboard())
    
    elif data == "add_channel":
        await add_channel(update, context)
    
    elif data == "auto_setup":
        await auto_setup_menu(update, context)
    
    elif data == "theme_select":
        await theme_select(update, context)
    
    elif data == "size_select":
        await size_select(update, context)
    
    elif data == "random_post":
        await random_post(update, context)
    
    elif data == "my_channels":
        await my_channels(update, context)
    
    elif data == "tariffs":
        await tariffs_menu(update, context)
    
    elif data == "stats":
        await stats(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    # Смена тарифа
    elif data.startswith("tariff_"):
        new_tariff = data.replace("tariff_", "")
        if new_tariff in TARIFFS:
            user_data.tariff = new_tariff
            bot.save_data()
            await query.edit_message_text(
                f"✅ *Тариф изменен на {TARIFFS[new_tariff]['emoji']} {TARIFFS[new_tariff]['name']}!*\n\n"
                f"📊 Каналов: {TARIFFS[new_tariff]['channels']}\n"
                f"📝 Постов/день: {TARIFFS[new_tariff]['posts_per_day']}",
                parse_mode='Markdown'
            )
    
    # Выбор темы
    elif data.startswith("theme_"):
        theme = data.replace("theme_", "")
        context.user_data['temp_theme'] = theme
        await query.edit_message_text(
            f"✅ *Тема выбрана:* {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\n"
            f"Теперь выберите размер поста:",
            parse_mode='Markdown',
            reply_markup=await get_sizes_keyboard()
        )
    
    elif data.startswith("theme_page_"):
        page = int(data.split("_")[2])
        await query.edit_message_reply_markup(reply_markup=await get_themes_keyboard(page))
    
    # Выбор размера
    elif data.startswith("size_"):
        size = data.replace("size_", "")
        context.user_data['temp_size'] = size
        
        theme = context.user_data.get('temp_theme')
        if theme and user_data.channels:
            await query.edit_message_text(f"🎲 *Применяю настройки ко всем каналам...*", parse_mode='Markdown')
            
            for ch in user_data.channels:
                ch.theme = theme
                ch.post_size = size
            bot.save_data()
            
            await query.edit_message_text(
                f"✅ *Настройки применены к {len(user_data.channels)} каналу(ам)!*\n\n"
                f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
                f"📏 Размер: {POST_SIZES[size]['icon']} {POST_SIZES[size]['name']}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("✅ *Размер сохранен*", parse_mode='Markdown')
    
    # Настройка каналов
    elif data.startswith("auto_channel_"):
        channel_id = data.replace("auto_channel_", "")
        context.user_data['config_channel_id'] = channel_id
        await query.edit_message_text(
            f"⚙️ *Настройка канала*\n\nВыберите параметр для настройки:",
            parse_mode='Markdown',
            reply_markup=await get_channel_settings_keyboard(channel_id)
        )
    
    elif data.startswith("ch_theme_"):
        channel_id = data.replace("ch_theme_", "")
        context.user_data['config_channel_id'] = channel_id
        await query.edit_message_text(
            "🎨 *Выберите тему для канала:*",
            parse_mode='Markdown',
            reply_markup=await get_themes_keyboard()
        )
    
    elif data.startswith("ch_size_"):
        channel_id = data.replace("ch_size_", "")
        keyboard = []
        for size_key, size in POST_SIZES.items():
            keyboard.append([InlineKeyboardButton(
                f"{size['icon']} {size['name']}",
                callback_data=f"ch_apply_size_{channel_id}_{size_key}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
        await query.edit_message_text("📏 *Выберите размер постов:*", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("ch_apply_size_"):
        parts = data.split("_")
        channel_id = parts[3]
        size = parts[4]
        
        for ch in user_data.channels:
            if ch.channel_id == channel_id:
                ch.post_size = size
                bot.save_data()
                break
        
        await query.edit_message_text(f"✅ Размер изменен на {POST_SIZES[size]['name']}!")
    
    elif data.startswith("ch_interval_"):
        channel_id = data.replace("ch_interval_", "")
        context.user_data['interval_channel_id'] = channel_id
        await query.edit_message_text(
            "⏱ *Настройка интервала*\n\n"
            "Введите интервал в минутах (от 15 до 1440):\n"
            "• 15-30 - для активных каналов\n"
            "• 60-120 - стандартный режим\n"
            "• 240+ - редкие посты\n\n"
            "Отправьте число сообщением:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_interval'] = True
    
    elif data.startswith("ch_on_"):
        channel_id = data.replace("ch_on_", "")
        for ch in user_data.channels:
            if ch.channel_id == channel_id:
                ch.is_active = True
                bot.save_data()
                break
        await query.edit_message_text("✅ *Автопостинг включен!*", parse_mode='Markdown')
    
    elif data.startswith("ch_off_"):
        channel_id = data.replace("ch_off_", "")
        for ch in user_data.channels:
            if ch.channel_id == channel_id:
                ch.is_active = False
                bot.save_data()
                break
        await query.edit_message_text("⏸ *Автопостинг выключен*", parse_mode='Markdown')
    
    elif data.startswith("ch_del_"):
        channel_id = data.replace("ch_del_", "")
        user_data.channels = [ch for ch in user_data.channels if ch.channel_id != channel_id]
        bot.save_data()
        await query.edit_message_text("🗑 *Канал удален!*", parse_mode='Markdown')

async def handle_interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_interval'):
        try:
            interval = int(update.message.text)
            if 15 <= interval <= 1440:
                channel_id = context.user_data.get('interval_channel_id')
                user_id = update.effective_user.id
                user_data = bot.get_user(user_id)
                
                for ch in user_data.channels:
                    if ch.channel_id == channel_id:
                        ch.interval_minutes = interval
                        bot.save_data()
                        await update.message.reply_text(f"✅ Интервал установлен: {interval} минут")
                        break
            else:
                await update.message.reply_text("❌ Интервал должен быть от 15 до 1440 минут")
        except:
            await update.message.reply_text("❌ Введите число (минуты)")
        
        context.user_data['awaiting_interval'] = False

# ==================== АВТОМАТИЧЕСКИЙ ПОСТИНГ ====================
async def auto_post_check(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и отправка автоматических постов"""
    bot.reset_daily_posts()
    
    for user_id, user_data in bot.users.items():
        tariff = TARIFFS[user_data.tariff]
        
        for channel in user_data.channels:
            if not channel.is_active:
                continue
            
            current_time = time.time()
            interval_seconds = channel.interval_minutes * 60
            
            if current_time - channel.last_post >= interval_seconds:
                if bot.can_post(user_data):
                    success = await bot.post_to_channel(context, channel, user_data)
                    if success:
                        logger.info(f"Автопост в {channel.channel_name} - тема: {channel.theme}")
                        await asyncio.sleep(2)  # Задержка между постами
                else:
                    logger.info(f"Лимит постов для {user_data.first_name}")

# ==================== ЗАПУСК ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interval_input))
    
    # Job для автопостинга (каждые 30 секунд)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_check, interval=30, first=10)
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💎 Тарифов: {len(TARIFFS)} (все бесплатные)")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
        
