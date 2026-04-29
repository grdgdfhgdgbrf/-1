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

# ==================== ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "price": 0,
        "channels": 3,
        "posts_per_day": 50,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "features": ["3 канала", "50 постов/день", "Автопостинг", "Перепост", "Расписание", "20 тем", "5 размеров"]
    },
    "plus": {
        "name": "💎 Бесплатный Плюс",
        "price": 0,
        "channels": 10,
        "posts_per_day": 200,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "features": ["10 каналов", "200 постов/день", "Автопостинг", "Перепост", "Расписание", "20 тем", "5 размеров"]
    },
    "pro": {
        "name": "👑 Бесплатный Про",
        "price": 0,
        "channels": 999,
        "posts_per_day": 999,
        "can_repost": True,
        "can_schedule": True,
        "has_images": True,
        "features": ["Безлимит каналов", "Безлимит постов", "Автопостинг", "Перепост", "Расписание", "20 тем", "5 размеров", "Приоритет"]
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {
        "name": "🤖 ИИ и Технологии",
        "emoji": "🤖",
        "description": "Новости искусственного интеллекта",
        "hashtags": "#ИИ #AI #Технологии",
        "prompt": "Ты журналист, пишущий об AI. Создай интересный пост о последних новостях в мире искусственного интеллекта, нейросетях и технологиях."
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "description": "Новости криптовалют и блокчейн",
        "hashtags": "#Криптовалюта #Биткоин #Блокчейн",
        "prompt": "Ты крипто-аналитик. Создай пост о криптовалютах, блокчейне, DeFi, трендах рынка."
    },
    "nft": {
        "name": "🎨 NFT и Цифровое Искусство",
        "emoji": "🎨",
        "description": "Новости NFT и digital art",
        "hashtags": "#NFT #ЦифровоеИскусство #Метавселенная",
        "prompt": "Ты эксперт по NFT. Создай пост о NFT коллекциях, digital art, метавселенных, трендах."
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram",
        "hashtags": "#Telegram #Боты #Каналы",
        "prompt": "Ты блогер о Telegram. Создай пост о новых функциях Telegram, полезных ботах, каналах."
    },
    "business": {
        "name": "💼 Бизнес",
        "emoji": "💼",
        "description": "Бизнес новости",
        "hashtags": "#Бизнес #Предпринимательство #Стартап",
        "prompt": "Ты бизнес-журналист. Создай пост о бизнесе, стартапах, инвестициях, управлении."
    },
    "tech": {
        "name": "📡 Технологии",
        "emoji": "📡",
        "description": "Технологические новости",
        "hashtags": "#Технологии #Гаджеты #Инновации",
        "prompt": "Ты техноблогер. Создай пост о новых технологиях, гаджетах, изобретениях."
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "hashtags": "#Наука #Открытия #Исследования",
        "prompt": "Ты научный журналист. Создай пост о научных открытиях и исследованиях."
    },
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "description": "Здоровье и медицина",
        "hashtags": "#Здоровье #Медицина #ЗОЖ",
        "prompt": "Ты медицинский блогер. Создай полезный пост о здоровье, профилактике, ЗОЖ."
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "hashtags": "#Психология #Саморазвитие #Мотивация",
        "prompt": "Ты психолог. Создай полезный пост по психологии и саморазвитию, дай советы."
    },
    "marketing": {
        "name": "📈 Маркетинг",
        "emoji": "📈",
        "description": "Маркетинг и SMM",
        "hashtags": "#Маркетинг #SMM #Реклама",
        "prompt": "Ты маркетолог. Создай пост о маркетинге, SMM, рекламе, трендах."
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "description": "Дизайн и креатив",
        "hashtags": "#Дизайн #UI #UX #Креатив",
        "prompt": "Ты дизайнер. Создай вдохновляющий пост о дизайне, творчестве."
    },
    "programming": {
        "name": "💻 Программирование",
        "emoji": "💻",
        "description": "IT и разработка",
        "hashtags": "#Программирование #IT #Кодер",
        "prompt": "Ты разработчик. Создай полезный пост о программировании, языках, инструментах."
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровые новости",
        "hashtags": "#Gaming #Игры #Гейминг",
        "prompt": "Ты игровой журналист. Создай пост об играх, новинках, гейминге."
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Новости кино",
        "hashtags": "#Кино #Сериалы #Кинопремьеры",
        "prompt": "Ты кинокритик. Создай пост о новинках кино и сериалов, обзоры."
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "hashtags": "#Музыка #НовинкиМузыки #Хиты",
        "prompt": "Ты музыкальный обозреватель. Создай пост о музыке, артистах, новинках."
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости",
        "hashtags": "#Спорт #Футбол #Турниры",
        "prompt": "Ты спортивный журналист. Создай пост о спорте, турнирах, достижениях."
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Путешествия и туризм",
        "hashtags": "#Путешествия #Туризм #Отдых",
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях, странах, местах."
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Кулинария и рецепты",
        "hashtags": "#Кулинария #Рецепты #Еда",
        "prompt": "Ты кулинарный блогер. Создай пост о еде, рецептах, кулинарных хитростях."
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "description": "Образование и обучение",
        "hashtags": "#Образование #Учеба #Навыки",
        "prompt": "Ты педагог. Создай полезный пост об образовании, учебе, навыках."
    },
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "description": "Мотивация и успех",
        "hashtags": "#Мотивация #Успех #Цели",
        "prompt": "Ты мотивационный спикер. Создай вдохновляющий пост о достижении целей."
    }
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "🔹 Мини", "min_chars": 150, "max_chars": 350, "emoji": "🔹", "description": "Коротко и ясно"},
    "short": {"name": "🔸 Короткий", "min_chars": 351, "max_chars": 650, "emoji": "🔸", "description": "Основная мысль"},
    "medium": {"name": "📝 Средний", "min_chars": 651, "max_chars": 1000, "emoji": "📝", "description": "Детальный разбор"},
    "long": {"name": "📄 Длинный", "min_chars": 1001, "max_chars": 1500, "emoji": "📄", "description": "Полная статья"},
    "extra": {"name": "📚 Макси", "min_chars": 1501, "max_chars": 2000, "emoji": "📚", "description": "Максимум пользы"}
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class UserData:
    user_id: int
    username: str
    first_name: str
    tariff: str = "free"
    channels: List[Dict] = field(default_factory=list)  # [{channel_id, channel_name, theme, size, auto_active, interval}]
    repost_sources: List[Dict] = field(default_factory=list)  # [{channel_id, channel_name, target_channel, theme}]
    posts_today: int = 0
    last_reset: float = field(default_factory=time.time)
    schedule: Dict[str, str] = field(default_factory=dict)  # {channel_id: time}
    
    def reset_daily(self):
        today = time.time()
        if today - self.last_reset > 86400:
            self.posts_today = 0
            self.last_reset = today
            return True
        return False
    
    def can_post(self) -> bool:
        self.reset_daily()
        tariff = TARIFFS.get(self.tariff, TARIFFS["free"])
        return self.posts_today < tariff["posts_per_day"]

@dataclass
class Post:
    id: str
    channel_id: str
    theme: str
    content: str
    posted_at: float
    size: str
    views: int = 0

class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.post_history: List[Post] = []
        self.api_token = None
        self.api_token_expiry = 0
        self.load_data()
    
    def load_data(self):
        """Загрузка данных"""
        try:
            with open("bot_users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, user_data in data.items():
                    self.users[int(uid)] = UserData(**user_data)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    def save_data(self):
        """Сохранение данных"""
        try:
            data = {uid: {
                "user_id": u.user_id,
                "username": u.username,
                "first_name": u.first_name,
                "tariff": u.tariff,
                "channels": u.channels,
                "repost_sources": u.repost_sources,
                "posts_today": u.posts_today,
                "last_reset": u.last_reset,
                "schedule": u.schedule
            } for uid, u in self.users.items()}
            with open("bot_users.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            self.save_data()
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
                        logger.error(f"Ошибка токена: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            return None
    
    async def generate_post(self, theme: str, size: str) -> str:
        """Генерация поста через GigaChat"""
        token = await self.get_api_token()
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        prompt = f"""{theme_config['prompt']}

ТРЕБОВАНИЯ:
- Длина: {size_config['min_chars']}-{size_config['max_chars']} символов
- Используй эмодзи (5-10 штук) для украшения
- Добавь хэштеги: {theme_config['hashtags']}
- Пиши на русском языке, грамотно
- Пост должен быть интересным и полезным
- В конце добавь вопрос к подписчикам или призыв к действию
- Используй красивое форматирование

Напиши пост прямо сейчас:"""
        
        if not token:
            return self.get_fallback_post(theme, size)
        
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
                        "max_tokens": 2500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        if len(content) > size_config["max_chars"]:
                            content = content[:size_config["max_chars"]]
                        return content
                    elif response.status == 401:
                        self.api_token = None
                        return await self.generate_post(theme, size)
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
        
        return self.get_fallback_post(theme, size)
    
    def get_fallback_post(self, theme: str, size: str) -> str:
        """Запасной пост"""
        post_templates = {
            "ai_news": "🤖 *Искусственный интеллект меняет мир!*\n\nКаждый день появляются новые нейросети и AI-инструменты. Какое применение AI вас больше всего удивляет?\n\n#ИИ #AI #Технологии\n\n👇 Поделитесь мнением в комментариях!",
            "crypto": "🪙 *Криптовалюты: новый тренд*\n\nБиткоин снова в центре внимания! А что вы думаете о будущем криптовалют?\n\n#Криптовалюта #Биткоин\n\n💬 Жду ваши мысли!",
            "nft": "🎨 *NFT - будущее искусства?*\n\nЦифровое искусство набирает обороты. Какая NFT коллекция вам нравится больше всего?\n\n#NFT #ЦифровоеИскусство\n\n🖼️ Делитесь в комментариях!",
            "telegram": "📱 *Telegram обновляется!*\n\nНовые функции делают мессенджер еще удобнее. Какое обновление вы ждете?\n\n#Telegram\n\n✨ Расскажите в комментах!",
        }
        
        template = post_templates.get(theme, f"{POSTING_THEMES[theme]['emoji']} *{POSTING_THEMES[theme]['name']}*\n\nИнтересный пост на тему! А что вы думаете по этому поводу?\n\n{POSTING_THEMES[theme]['hashtags']}\n\n💬 Жду ваши комментарии!")
        
        if len(template) > POST_SIZES[size]["max_chars"]:
            template = template[:POST_SIZES[size]["max_chars"]]
        return template
    
    async def send_beautiful_post(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, content: str):
        """Красивая отправка поста"""
        try:
            # Разбиваем длинный пост на части
            if len(content) > 4000:
                parts = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for part in parts:
                    await context.bot.send_message(
                        chat_id=channel_id,
                        text=part,
                        parse_mode='Markdown',
                        disable_web_page_preview=False
                    )
                return True
            else:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )
                return True
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False
    
    async def create_post(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_info: dict, theme: str = None, size: str = None):
        """Создание поста"""
        user = self.get_user(user_id, "", "")
        
        if not user.can_post():
            return False, "❌ Достигнут лимит постов на сегодня!"
        
        if not channel_info:
            return False, "❌ Сначала добавьте канал!"
        
        theme = theme or channel_info.get('theme') or random.choice(list(POSTING_THEMES.keys()))
        size = size or channel_info.get('size') or random.choice(list(POST_SIZES.keys()))
        
        await context.bot.send_message(user_id, f"🎨 *Генерация поста...*\n\nТема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\nРазмер: {POST_SIZES[size]['name']}", parse_mode='Markdown')
        
        content = await self.generate_post(theme, size)
        
        success = await self.send_beautiful_post(context, channel_info['channel_id'], content)
        
        if success:
            user.posts_today += 1
            self.post_history.append(Post(
                id=str(uuid.uuid4()),
                channel_id=channel_info['channel_id'],
                theme=theme,
                content=content[:200],
                posted_at=time.time(),
                size=size
            ))
            self.save_data()
            await context.bot.send_message(user_id, f"✅ *Пост успешно опубликован!*\n\n📊 Осталось постов: {TARIFFS[user.tariff]['posts_per_day'] - user.posts_today}", parse_mode='Markdown')
            return True, "Успешно!"
        else:
            return False, "❌ Ошибка публикации"

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("⚙️ Настройки канала", callback_data="channel_settings")],
        [InlineKeyboardButton("🎨 Создать пост", callback_data="create_post")],
        [InlineKeyboardButton("🤖 Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🔄 Перепост", callback_data="repost_settings")],
        [InlineKeyboardButton("🎭 20 тем", callback_data="themes_list")],
        [InlineKeyboardButton("📏 Размеры постов", callback_data="sizes_list")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user: UserData):
    keyboard = []
    for ch in user.channels:
        keyboard.append([InlineKeyboardButton(f"📢 {ch['channel_name']}", callback_data=f"channel_{ch['channel_id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_themes_keyboard(action: str, channel_id: str = None):
    keyboard = []
    row = []
    for theme_key, theme in POSTING_THEMES.items():
        btn_text = f"{theme['emoji']} {theme['name']}"
        callback = f"theme_{action}_{theme_key}"
        if channel_id:
            callback += f"_{channel_id}"
        row.append(InlineKeyboardButton(btn_text, callback_data=callback))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_settings" if channel_id else "back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard(action: str, channel_id: str = None):
    keyboard = []
    for size_key, size in POST_SIZES.items():
        callback = f"size_{action}_{size_key}"
        if channel_id:
            callback += f"_{channel_id}"
        keyboard.append([InlineKeyboardButton(f"{size['emoji']} {size['name']} - {size['description']}", callback_data=callback)])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_settings" if channel_id else "back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(channel_id: str):
    intervals = [30, 60, 120, 180, 240, 360, 480, 720, 1440]
    keyboard = []
    row = []
    for interval in intervals:
        hours = interval // 60
        label = f"{interval} мин" if interval < 60 else f"{hours} час" + ("а" if hours == 1 else "ов")
        row.append(InlineKeyboardButton(label, callback_data=f"interval_{channel_id}_{interval}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"channel_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = f"""
✨ *Дорогой {user.first_name}!*

🤖 *Добро пожаловать в бота для автопостинга с ИИ!*

📝 *Что я умею:*
• ✅ Генерировать посты через нейросеть GigaChat
• 🎭 20 различных тематик на выбор
• 📏 5 размеров постов (от мини до макси)
• 🤖 Автоматический постинг в ваши каналы
• 🔄 Перепост из других каналов
• ⏰ Настройка расписания

💰 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*
- 🌟 Бесплатный: 3 канала, 50 постов/день
- 💎 Бесплатный Плюс: 10 каналов, 200 постов/день  
- 👑 Бесплатный Про: безлимит каналов и постов

🎯 *Как начать:*
1️⃣ Нажмите "➕ Добавить канал"
2️⃣ Выберите тему и размер постов
3️⃣ Настройте автопостинг
4️⃣ Наслаждайтесь уникальным контентом!

👇 *Выберите действие в меню ниже*
"""
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    
    text = """
📢 *Добавление канала*

🔹 *Способ 1:* Перешлите любое сообщение из канала сюда
🔹 *Способ 2:* Отправьте username канала (например: @channel)
🔹 *Способ 3:* Отправьте ID канала (например: -1001234567890)

📌 *Важно:* Бот должен быть администратором канала!

✏️ *Отправьте информацию о канале прямо сейчас*
"""
    await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    context.user_data['awaiting_channel'] = True

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        user_id = update.effective_user.id
        user = bot.get_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
        
        text = update.message.text.strip()
        channel_id = None
        channel_name = None
        
        # Определяем канал
        try:
            if text.startswith('@'):
                chat = await context.bot.get_chat(text)
                channel_id = str(chat.id)
                channel_name = chat.title
            elif text.startswith('-100'):
                channel_id = text
                chat = await context.bot.get_chat(int(text))
                channel_name = chat.title
            elif update.message.forward_from_chat:
                chat = update.message.forward_from_chat
                channel_id = str(chat.id)
                channel_name = chat.title
            else:
                await update.message.reply_text("❌ Не удалось определить канал. Попробуйте еще раз или перешлите сообщение из канала.")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}\nУбедитесь, что бот добавлен в канал как администратор.")
            return
        
        # Проверяем лимит
        tariff = TARIFFS[user.tariff]
        if len(user.channels) >= tariff["channels"]:
            await update.message.reply_text(f"❌ Достигнут лимит каналов для вашего тарифа ({tariff['channels']})\nВыберите другой тариф в разделе 💎 Тарифы")
            return
        
        # Добавляем канал
        channel_data = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'theme': 'ai_news',
            'size': 'medium',
            'auto_active': False,
            'interval': 60,
            'last_post': 0
        }
        user.channels.append(channel_data)
        bot.save_data()
        
        # Отправляем сообщение в канал для проверки
        try:
            await context.bot.send_message(channel_id, f"✅ *Бот успешно подключен!*\n\nДобро пожаловать! Я буду публиковать интересные посты в этот канал.\n\nЧтобы начать, настройте тему и размер постов в меню.", parse_mode='Markdown')
        except:
            pass
        
        # Предлагаем настроить канал
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Выбрать тему", callback_data=f"channel_theme_{channel_id}")],
            [InlineKeyboardButton("📏 Выбрать размер", callback_data=f"channel_size_{channel_id}")],
            [InlineKeyboardButton("🤖 Настроить автопостинг", callback_data=f"channel_{channel_id}")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="back_main")]
        ])
        
        await update.message.reply_text(
            f"✅ *Канал успешно добавлен!*\n\n"
            f"📢 Название: {channel_name}\n"
            f"🆔 ID: {channel_id}\n"
            f"📊 Всего каналов: {len(user.channels)}/{tariff['channels']}\n\n"
            f"👇 *Настройте канал:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        context.user_data['awaiting_channel'] = False

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = bot.get_user(query.from_user.id)
    tariff = TARIFFS[user.tariff]
    
    if not user.channels:
        text = "📢 *У вас пока нет добавленных каналов*\n\nНажмите '➕ Добавить канал' чтобы начать"
    else:
        text = f"📋 *Ваши каналы* ({len(user.channels)}/{tariff['channels']})\n\n"
        for i, ch in enumerate(user.channels, 1):
            theme = POSTING_THEMES.get(ch['theme'], POSTING_THEMES['ai_news'])
            size = POST_SIZES.get(ch['size'], POST_SIZES['medium'])
            status = "✅" if ch.get('auto_active') else "⏸"
            text += f"{i}. {status} *{ch['channel_name']}*\n"
            text += f"   🎨 Тема: {theme['emoji']} {theme['name']}\n"
            text += f"   📏 Размер: {size['name']}\n"
            text += f"   ⏱ Интервал: {ch['interval']} мин\n\n"
    
    keyboard = await get_channels_keyboard(user)
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("channel_"):
        channel_id = query.data.replace("channel_", "")
        user = bot.get_user(query.from_user.id)
        
        channel = None
        for ch in user.channels:
            if ch['channel_id'] == channel_id:
                channel = ch
                break
        
        if channel:
            theme = POSTING_THEMES.get(channel['theme'], POSTING_THEMES['ai_news'])
            size = POST_SIZES.get(channel['size'], POST_SIZES['medium'])
            
            text = f"""
⚙️ *Настройки канала*

📢 *{channel['channel_name']}*

🎨 *Тема:* {theme['emoji']} {theme['name']}
📏 *Размер:* {size['name']} ({size['description']})
⏱ *Интервал:* {channel['interval']} мин
🤖 *Автопостинг:* {'✅ Включен' if channel.get('auto_active') else '⏸ Выключен'}

👇 *Выберите действие:*
"""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎨 Сменить тему", callback_data=f"channel_theme_{channel_id}")],
                [InlineKeyboardButton("📏 Сменить размер", callback_data=f"channel_size_{channel_id}")],
                [InlineKeyboardButton("⏱ Интервал", callback_data=f"channel_interval_{channel_id}")],
                [InlineKeyboardButton("🤖 Автопостинг", callback_data=f"auto_toggle_{channel_id}")],
                [InlineKeyboardButton("🗑 Удалить канал", callback_data=f"delete_channel_{channel_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="my_channels")]
            ])
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await query.edit_message_text("❌ Канал не найден")

async def set_channel_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[3]
    
    context.user_data['setting_theme_for'] = channel_id
    keyboard = await get_themes_keyboard("set", channel_id)
    await query.edit_message_text("🎨 *Выберите тему для канала:*", parse_mode='Markdown', reply_markup=keyboard)

async def set_channel_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[3]
    
    keyboard = await get_sizes_keyboard("set", channel_id)
    await query.edit_message_text("📏 *Выберите размер постов:*", parse_mode='Markdown', reply_markup=keyboard)

async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    action = parts[1]
    theme_key = parts[2]
    
    if len(parts) > 3:
        channel_id = parts[3]
        user = bot.get_user(query.from_user.id)
        
        for ch in user.channels:
            if ch['channel_id'] == channel_id:
                ch['theme'] = theme_key
                bot.save_data()
                
                theme = POSTING_THEMES[theme_key]
                await query.edit_message_text(
                    f"✅ *Тема изменена!*\n\nТеперь канал будет получать посты на тему:\n{theme['emoji']} {theme['name']}\n\n{theme['description']}",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(2)
                await channel_settings(update, context)
                return
    else:
        context.user_data['post_theme'] = theme_key
        keyboard = await get_sizes_keyboard("create", None)
        await query.edit_message_text(
            f"✅ Выбрана тема: {POSTING_THEMES[theme_key]['emoji']} {POSTING_THEMES[theme_key]['name']}\n\n📏 *Теперь выберите размер поста:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def size_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    action = parts[1]
    size_key = parts[2]
    
    if action == "create":
        theme = context.user_data.get('post_theme', 'ai_news')
        user = bot.get_user(query.from_user.id)
        
        if not user.channels:
            await query.edit_message_text("❌ Сначала добавьте канал через '➕ Добавить канал'")
            return
        
        target_channel = None
        if len(user.channels) == 1:
            target_channel = user.channels[0]
        else:
            keyboard = []
            for ch in user.channels:
                keyboard.append([InlineKeyboardButton(ch['channel_name'], callback_data=f"post_to_{ch['channel_id']}_{theme}_{size_key}")])
            await query.edit_message_text("📢 *Выберите канал для публикации:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        success, msg = await bot.create_post(context, query.from_user.id, target_channel, theme, size_key)
        if success:
            await query.edit_message_text("✅ Пост успешно опубликован!", parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {msg}", parse_mode='Markdown')
    
    elif action == "set" and len(parts) > 3:
        channel_id = parts[3]
        user = bot.get_user(query.from_user.id)
        
        for ch in user.channels:
            if ch['channel_id'] == channel_id:
                ch['size'] = size_key
                bot.save_data()
                
                size = POST_SIZES[size_key]
                await query.edit_message_text(
                    f"✅ *Размер изменен!*\n\nТеперь посты будут размером:\n{size['name']} ({size['description']})\n\n{size['min_chars']}-{size['max_chars']} символов",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(2)
                await channel_settings(update, context)
                return

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = bot.get_user(query.from_user.id)
    
    if not user.channels:
        await query.edit_message_text("❌ Сначала добавьте канал через '➕ Добавить канал'")
        return
    
    text = "🤖 *Настройка автопостинга*\n\nВыберите канал для настройки автоматической публикации:\n\n"
    
    keyboard = []
    for ch in user.channels:
        status = "✅" if ch.get('auto_active') else "⏸"
        keyboard.append([InlineKeyboardButton(f"{status} {ch['channel_name']}", callback_data=f"auto_config_{ch['channel_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def auto_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_config_", "")
    user = bot.get_user(query.from_user.id)
    
    channel = None
    for ch in user.channels:
        if ch['channel_id'] == channel_id:
            channel = ch
            break
    
    if channel:
        theme = POSTING_THEMES[channel['theme']]
        size = POST_SIZES[channel['size']]
        
        text = f"""
⚙️ *Автопостинг для канала*

📢 *{channel['channel_name']}*

🎨 Тема: {theme['emoji']} {theme['name']}
📏 Размер: {size['name']}
⏱ Интервал: {channel['interval']} мин
🤖 Статус: {'✅ Активен' if channel.get('auto_active') else '⏸ Остановлен'}

📝 *Что будет делать бот:*
Бот будет автоматически создавать и публиковать посты каждые {channel['interval']} минут на выбранную тему.

👇 *Настройки:*
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Сменить тему", callback_data=f"channel_theme_{channel_id}")],
            [InlineKeyboardButton("📏 Сменить размер", callback_data=f"channel_size_{channel_id}")],
            [InlineKeyboardButton("⏱ Интервал ({channel['interval']} мин)", callback_data=f"auto_interval_{channel_id}")],
            [InlineKeyboardButton("🔄 Включить/Выключить", callback_data=f"auto_toggle_{channel_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
        ])
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def set_auto_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_interval_", "")
    keyboard = await get_intervals_keyboard(channel_id)
    await query.edit_message_text("⏱ *Выберите интервал автопостинга:*\n\n(от 30 минут до 24 часов)", parse_mode='Markdown', reply_markup=keyboard)

async def interval_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    user = bot.get_user(query.from_user.id)
    
    for ch in user.channels:
        if ch['channel_id'] == channel_id:
            ch['interval'] = interval
            bot.save_data()
            break
    
    hours = interval // 60
    mins = interval % 60
    text = f"⏱ *Интервал установлен!*\n\nБот будет публиковать посты каждые "
    if hours > 0:
        text += f"{hours} час" + ("а" if hours == 1 else "ов")
    if mins > 0:
        text += f" {mins} минут" if hours > 0 else f"{mins} минут"
    text += "\n\n✅ Настройки сохранены!"
    
    await query.edit_message_text(text, parse_mode='Markdown')
    await asyncio.sleep(2)
    await auto_config(update, context)

async def toggle_auto_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_toggle_", "")
    user = bot.get_user(query.from_user.id)
    
    for ch in user.channels:
        if ch['channel_id'] == channel_id:
            ch['auto_active'] = not ch.get('auto_active', False)
            bot.save_data()
            status = "✅ ВКЛЮЧЕН" if ch['auto_active'] else "⏸ ВЫКЛЮЧЕН"
            await query.edit_message_text(f"🤖 *Автопостинг {status}*", parse_mode='Markdown')
            await asyncio.sleep(2)
            break
    
    await auto_config(update, context)

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("delete_channel_", "")
    user = bot.get_user(query.from_user.id)
    
    user.channels = [ch for ch in user.channels if ch['channel_id'] != channel_id]
    bot.save_data()
    
    await query.edit_message_text("✅ *Канал успешно удален*", parse_mode='Markdown')
    await asyncio.sleep(1)
    await my_channels(update, context)

async def create_post_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = bot.get_user(query.from_user.id)
    
    if not user.channels:
        await query.edit_message_text("❌ Сначала добавьте канал через '➕ Добавить канал'")
        return
    
    keyboard = await get_themes_keyboard("create", None)
    await query.edit_message_text(
        "🎨 *Создание поста*\n\n"
        "Сначала выберите тему для поста:\n\n"
        f"📊 Доступно постов сегодня: {TARIFFS[user.tariff]['posts_per_day'] - user.posts_today}/{TARIFFS[user.tariff]['posts_per_day']}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def repost_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🔄 *Перепост из других каналов*

📌 *Как это работает:*
1. Вы указываете канал-источник (откуда перепостить)
2. Выбираете канал-назначение (куда перепостить)
3. Бот будет автоматически пересылать новые посты

🎯 *Настройка:*
Напишите @username канала-источника, и я добавлю его в список для перепоста

📝 *Активные источники:*
"""
    user = bot.get_user(query.from_user.id)
    if user.repost_sources:
        text += "\n"
        for src in user.repost_sources:
            text += f"• {src['channel_name']} → {src['target_channel_name']}\n"
    else:
        text += "\nНет активных источников"
    
    await query.edit_message_text(text, parse_mode='Markdown')
    context.user_data['awaiting_repost_source'] = True

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "💎 *ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!*\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        text += f"{tariff['name']}\n"
        text += "├ 💰 Цена: 0₽ (Бесплатно)\n"
        for feature in tariff['features']:
            text += f"├ ✅ {feature}\n"
        text += "\n"
    
    text += "\n✨ *Как получить улучшенный тариф?*\n"
    text += "Просто напишите @, и мы активируем любой тариф бесплатно!\n\n"
    text += "🎁 *Все пользователи могут пользоваться всеми функциями!*"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = bot.get_user(query.from_user.id)
    tariff = TARIFFS[user.tariff]
    
    # Подсчет постов за сегодня от бота
    today_posts = user.posts_today
    
    text = f"""
📊 *Ваша статистика*

👤 *Пользователь:* {user.first_name}
💎 *Тариф:* {tariff['name']}

📢 *Каналы:* {len(user.channels)}/{tariff['channels']}
📝 *Постов сегодня:* {today_posts}/{tariff['posts_per_day']}
💬 *Осталось постов:* {tariff['posts_per_day'] - today_posts}

🎨 *Активные темы:*
"""
    themes_used = {}
    for ch in user.channels:
        theme = POSTING_THEMES.get(ch['theme'], POSTING_THEMES['ai_news'])
        themes_used[theme['name']] = themes_used.get(theme['name'], 0) + 1
    
    for theme_name, count in themes_used.items():
        text += f"• {theme_name}: {count} канал(ов)\n"
    
    if user.repost_sources:
        text += f"\n🔄 *Источников перепоста:* {len(user.repost_sources)}"
    
    text += f"\n\n📈 *Всего постов в системе:* {len(bot.post_history)}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Обновить", callback_data="stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def themes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎨 *20 доступных тем для постов:*\n\n"
    for theme_key, theme in POSTING_THEMES.items():
        text += f"{theme['emoji']} **{theme['name']}**\n"
        text += f"   └ {theme['description']}\n\n"
    
    text += "\n💡 *Все темы бесплатны!*"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def sizes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "📏 *Размеры постов:*\n\n"
    for size_key, size in POST_SIZES.items():
        text += f"{size['emoji']} **{size['name']}** - {size['description']}\n"
        text += f"   └ Длина: {size['min_chars']}-{size['max_chars']} символов\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
❓ *Помощь и инструкция*

📌 *Быстрый старт:*
1️⃣ Добавьте бота в канал как администратора
2️⃣ Нажмите "➕ Добавить канал" и отправьте информацию
3️⃣ Настройте тему, размер и интервал
4️⃣ Включите автопостинг

🎯 *Основные функции:*
• **Создать пост** - ручная публикация
• **Автопостинг** - автоматические посты по расписанию
• **Перепост** - копирование из других каналов
• **20 тем** - любой контент на выбор
• **5 размеров** - от мини до макси

💰 *Тарифы:*
ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!
- Бесплатный: 3 канала, 50 постов/день
- Бесплатный Плюс: 10 каналов, 200 постов/день
- Бесплатный Про: безлимит

🆘 *Поддержка:*
По всем вопросам пишите @

🔙 *Назад в меню* - просто нажмите кнопку
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard()
    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:", 
        parse_mode='Markdown', 
        reply_markup=keyboard
    )

async def post_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    theme = parts[3]
    size = parts[4]
    
    user = bot.get_user(query.from_user.id)
    
    channel = None
    for ch in user.channels:
        if ch['channel_id'] == channel_id:
            channel = ch
            break
    
    if channel:
        await query.edit_message_text("🎨 *Генерация поста...*", parse_mode='Markdown')
        success, msg = await bot.create_post(context, query.from_user.id, channel, theme, size)
        if success:
            await query.edit_message_text("✅ *Пост успешно опубликован!*", parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {msg}", parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ Канал не найден", parse_mode='Markdown')

# ==================== АВТОМАТИЧЕСКИЙ ПОСТИНГ ====================
async def auto_posting_job(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для автопостинга"""
    current_time = time.time()
    
    for user_id, user in bot.users.items():
        for channel in user.channels:
            if channel.get('auto_active', False):
                last_post = channel.get('last_post', 0)
                interval = channel.get('interval', 60) * 60
                
                if current_time - last_post >= interval:
                    if user.can_post():
                        theme = channel.get('theme', 'ai_news')
                        size = channel.get('size', 'medium')
                        
                        content = await bot.generate_post(theme, size)
                        
                        # Создаем контекст для отправки
                        class DummyContext:
                            bot = context.bot
                        
                        success = await bot.send_beautiful_post(DummyContext(), channel['channel_id'], content)
                        
                        if success:
                            channel['last_post'] = current_time
                            user.posts_today += 1
                            bot.post_history.append(Post(
                                id=str(uuid.uuid4()),
                                channel_id=channel['channel_id'],
                                theme=theme,
                                content=content[:200],
                                posted_at=current_time,
                                size=size
                            ))
                            bot.save_data()
                            logger.info(f"Автопост в {channel['channel_name']} на тему {theme}")

# ==================== ЗАПУСК ====================
def main():
    global bot
    bot = PostingBot()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(my_channels, pattern="^my_channels$"))
    application.add_handler(CallbackQueryHandler(add_channel, pattern="^add_channel$"))
    application.add_handler(CallbackQueryHandler(channel_settings, pattern="^channel_settings$"))
    application.add_handler(CallbackQueryHandler(create_post_menu, pattern="^create_post$"))
    application.add_handler(CallbackQueryHandler(auto_posting_menu, pattern="^auto_posting$"))
    application.add_handler(CallbackQueryHandler(repost_settings, pattern="^repost_settings$"))
    application.add_handler(CallbackQueryHandler(tariffs_menu, pattern="^tariffs$"))
    application.add_handler(CallbackQueryHandler(stats_menu, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(themes_list, pattern="^themes_list$"))
    application.add_handler(CallbackQueryHandler(sizes_list, pattern="^sizes_list$"))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(back_main, pattern="^back_settings$"))
    
    # Настройки каналов
    application.add_handler(CallbackQueryHandler(set_channel_theme, pattern="^channel_theme_"))
    application.add_handler(CallbackQueryHandler(set_channel_size, pattern="^channel_size_"))
    application.add_handler(CallbackQueryHandler(set_auto_interval, pattern="^auto_interval_"))
    application.add_handler(CallbackQueryHandler(toggle_auto_post, pattern="^auto_toggle_"))
    application.add_handler(CallbackQueryHandler(delete_channel, pattern="^delete_channel_"))
    application.add_handler(CallbackQueryHandler(auto_config, pattern="^auto_config_"))
    application.add_handler(CallbackQueryHandler(interval_selected, pattern="^interval_"))
    application.add_handler(CallbackQueryHandler(theme_selected, pattern="^theme_"))
    application.add_handler(CallbackQueryHandler(size_selected, pattern="^size_"))
    application.add_handler(CallbackQueryHandler(post_to_channel_callback, pattern="^post_to_"))
    application.add_handler(CallbackQueryHandler(channel_settings, pattern="^channel_\\d"))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))
    
    # Job для автопостинга
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_posting_job, interval=30, first=10)
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info("💰 ВСЕ ТАРИФЫ БЕСПЛАТНЫЕ!")
    logger.info("🎯 Автопостинг активен")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
