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
    "starter": {
        "name": "🌟 Стартовый",
        "channels": 1,
        "posts_per_day": 999999,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 10,
        "emoji": "🌟"
    },
    "pro": {
        "name": "⚡ PRO",
        "channels": 5,
        "posts_per_day": 999999,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 10,
        "emoji": "⚡"
    },
    "ultimate": {
        "name": "👑 ULTIMATE",
        "channels": 999,
        "posts_per_day": 999999,
        "can_repost": True,
        "can_schedule": True,
        "interval_min": 5,
        "emoji": "👑"
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТИНГА (20 ТЕМ) ====================
POSTING_THEMES = {
    "ai_news": {"name": "🤖 ИИ Новости", "emoji": "🤖", "prompt": "напиши пост о новостях искусственного интеллекта, нейросетях, ChatGPT"},
    "crypto": {"name": "🪙 Криптовалюты", "emoji": "🪙", "prompt": "напиши пост о криптовалютах, биткоине, блокчейн технологиях"},
    "nft": {"name": "🎨 NFT", "emoji": "🎨", "prompt": "напиши пост о NFT, цифровом искусстве, метавселенных"},
    "telegram": {"name": "📱 Telegram", "emoji": "📱", "prompt": "напиши пост о Telegram, новых функциях, ботах, каналах"},
    "business": {"name": "💼 Бизнес", "emoji": "💼", "prompt": "напиши пост о бизнесе, стартапах, предпринимательстве"},
    "tech": {"name": "📡 Технологии", "emoji": "📡", "prompt": "напиши пост о новых технологиях, гаджетах, инновациях"},
    "science": {"name": "🔬 Наука", "emoji": "🔬", "prompt": "напиши пост о научных открытиях и исследованиях"},
    "health": {"name": "💪 Здоровье", "emoji": "💪", "prompt": "напиши полезный пост о здоровье, фитнесе, правильном питании"},
    "psychology": {"name": "🧠 Психология", "emoji": "🧠", "prompt": "напиши пост по психологии, саморазвитию, отношениям"},
    "marketing": {"name": "📈 Маркетинг", "emoji": "📈", "prompt": "напиши пост о маркетинге, SMM, рекламе, продвижении"},
    "design": {"name": "🎨 Дизайн", "emoji": "🎨", "prompt": "напиши вдохновляющий пост о дизайне, UI/UX, творчестве"},
    "programming": {"name": "💻 Программирование", "emoji": "💻", "prompt": "напиши полезный пост о программировании, IT, разработке"},
    "gaming": {"name": "🎮 Игры", "emoji": "🎮", "prompt": "напиши пост о видеоиграх, гейминге, новинках игр"},
    "movies": {"name": "🎬 Кино", "emoji": "🎬", "prompt": "напиши пост о кино, сериалах, новинках кинопроката"},
    "music": {"name": "🎵 Музыка", "emoji": "🎵", "prompt": "напиши пост о музыке, новых альбомах, исполнителях"},
    "sport": {"name": "⚽ Спорт", "emoji": "⚽", "prompt": "напиши пост о спорте, футболе, баскетболе, тренировках"},
    "travel": {"name": "✈️ Путешествия", "emoji": "✈️", "prompt": "напиши пост о путешествиях, туризме, интересных местах"},
    "food": {"name": "🍳 Кулинария", "emoji": "🍳", "prompt": "напиши пост о кулинарии, рецептах, вкусной еде"},
    "education": {"name": "📚 Образование", "emoji": "📚", "prompt": "напиши полезный пост об образовании, обучении, курсах"},
    "motivation": {"name": "💪 Мотивация", "emoji": "💪", "prompt": "напиши вдохновляющий пост о мотивации, успехе, целях"}
}

# ==================== РАЗМЕРЫ ПОСТОВ ====================
POST_SIZES = {
    "mini": {"name": "🔹 Мини", "chars": "50-150", "tokens": 200, "emoji": "🔹"},
    "short": {"name": "🔸 Короткий", "chars": "150-300", "tokens": 400, "emoji": "🔸"},
    "medium": {"name": "📄 Средний", "chars": "300-600", "tokens": 800, "emoji": "📄"},
    "long": {"name": "📚 Длинный", "chars": "600-1000", "tokens": 1200, "emoji": "📚"},
    "epic": {"name": "⭐ Эпичный", "chars": "1000-1500", "tokens": 1800, "emoji": "⭐"}
}

# ==================== ИНТЕРВАЛЫ ====================
INTERVALS = {
    10: "🔟 10 секунд",
    30: "⏱ 30 секунд",
    60: "⏰ 1 минута",
    300: "📅 5 минут",
    600: "📅 10 минут",
    1800: "📅 30 минут",
    3600: "📅 1 час",
    7200: "📅 2 часа",
    21600: "📅 6 часов",
    43200: "📅 12 часов",
    86400: "📅 24 часа"
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class ChannelConfig:
    channel_id: str
    channel_name: str
    theme: str
    size: str
    interval_seconds: int
    is_active: bool = True
    last_post_time: float = 0
    posts_today: int = 0
    last_reset_date: str = ""

@dataclass
class UserData:
    user_id: int
    username: str
    first_name: str
    tariff: str = "starter"
    channels: List[Dict] = field(default_factory=list)
    
    def get_channel_config(self, channel_id: str) -> Optional[ChannelConfig]:
        for ch in self.channels:
            if ch.get("channel_id") == channel_id:
                return ChannelConfig(**ch)
        return None
    
    def add_channel(self, config: ChannelConfig):
        self.channels.append({
            "channel_id": config.channel_id,
            "channel_name": config.channel_name,
            "theme": config.theme,
            "size": config.size,
            "interval_seconds": config.interval_seconds,
            "is_active": config.is_active,
            "last_post_time": config.last_post_time,
            "posts_today": config.posts_today,
            "last_reset_date": config.last_reset_date
        })

class PostingBot:
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            self.save_data()
        return self.users[user_id]
    
    def save_data(self):
        try:
            data = {}
            for uid, user in self.users.items():
                data[uid] = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "tariff": user.tariff,
                    "channels": user.channels
                }
            with open("users_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    def load_data(self):
        try:
            with open("users_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, user_data in data.items():
                    self.users[int(uid)] = UserData(**user_data)
        except:
            pass
    
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
        if not token:
            return await self.get_fallback_post(theme, size)
        
        theme_config = POSTING_THEMES.get(theme, POSTING_THEMES["ai_news"])
        size_config = POST_SIZES.get(size, POST_SIZES["medium"])
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        prompt = f"""Ты креативный копирайтер. {theme_config['prompt']}.

ТРЕБОВАНИЯ:
- Длина: {size_config['chars']} символов
- Используй красивые эмодзи в каждом предложении
- Сделай 3-4 абзаца
- Добавь хэштеги (4-6 штук) в конце
- В конце задай вопрос подписчикам
- Напиши дату: {current_date}
- Пиши увлекательно и информативно
- Используй смайлики 😊

ФОРМАТ:
✨ Заголовок (короткий и цепляющий)

📝 Основной текст (полезная информация)

💡 Интересный факт или совет

❓ Вопрос к подписчикам

#хэштеги #для #поста"""

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
                        "max_tokens": size_config["tokens"]
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
        
        return await self.get_fallback_post(theme, size)
    
    async def get_fallback_post(self, theme: str, size: str) -> str:
        fallbacks = {
            "ai_news": "🤖 Искусственный интеллект меняет мир! Какие возможности AI вас впечатляют больше всего?",
            "crypto": "🪙 Биткоин снова в тренде! А вы инвестируете в криптовалюты?",
            "nft": "🎨 NFT открывают новые горизонты! У вас есть цифровые коллекции?",
            "telegram": "📱 Telegram - лучшее приложение для общения! Какие функции вы используете чаще всего?",
            "business": "💼 Успешный бизнес начинается с идеи! А какая у вас бизнес-идея?",
        }
        text = fallbacks.get(theme, f"{POSTING_THEMES[theme]['emoji']} Новый интересный пост! Делитесь мнением в комментариях! 👇")
        
        if size == "mini":
            return text[:150]
        elif size == "short":
            return text[:300]
        elif size == "long":
            return text + "\n\n" + text
        else:
            return text
    
    async def post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, channel_id: str, 
                              theme: str, size: str, user_id: int) -> bool:
        try:
            content = await self.generate_post(theme, size)
            
            # Красивое оформление поста
            theme_config = POSTING_THEMES[theme]
            size_config = POST_SIZES[size]
            
            current_time = datetime.now().strftime("%H:%M")
            current_date = datetime.now().strftime("%d.%m.%Y")
            
            formatted_post = f"""<b>{theme_config['emoji']} {theme_config['name']}</b>
<code>{'─' * 30}</code>

{content}

<code>{'─' * 30}</code>
📅 {current_date} | ⏰ {current_time}
📏 {size_config['name']} | #{theme}"""
            
            await context.bot.send_message(
                chat_id=channel_id,
                text=formatted_post,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ Пост опубликован в {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка публикации: {e}")
            return False

bot = PostingBot()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("⚙️ Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🎨 Выбрать тему", callback_data="select_theme")],
        [InlineKeyboardButton("📏 Выбрать размер", callback_data="select_size")],
        [InlineKeyboardButton("⏱ Настройка интервала", callback_data="select_interval")],
        [InlineKeyboardButton("▶️ Запустить автопостинг", callback_data="start_auto")],
        [InlineKeyboardButton("⏸ Остановить автопостинг", callback_data="stop_auto")],
        [InlineKeyboardButton("🎲 Пост сейчас", callback_data="post_now")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
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
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"themes_page_{page-1}"))
    if end < len(themes_list):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"themes_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_sizes_keyboard():
    keyboard = []
    for size_key, size in POST_SIZES.items():
        keyboard.append([InlineKeyboardButton(
            f"{size['emoji']} {size['name']} ({size['chars']} симв.)",
            callback_data=f"size_{size_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard():
    keyboard = []
    row = []
    for sec, name in INTERVALS.items():
        row.append(InlineKeyboardButton(name, callback_data=f"interval_{sec}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff in TARIFFS.items():
        keyboard.append([InlineKeyboardButton(
            f"{tariff['emoji']} {tariff['name']} | {tariff['channels']} каналов",
            callback_data=f"tariff_{tariff_key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    user = bot.get_user(user_id)
    keyboard = []
    
    for ch in user.channels:
        keyboard.append([InlineKeyboardButton(
            f"📢 {ch['channel_name'][:30]}",
            callback_data=f"channel_{ch['channel_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_channel_settings_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("🎨 Сменить тему", callback_data=f"ch_theme_{channel_id}")],
        [InlineKeyboardButton("📏 Сменить размер", callback_data=f"ch_size_{channel_id}")],
        [InlineKeyboardButton("⏱ Сменить интервал", callback_data=f"ch_interval_{channel_id}")],
        [InlineKeyboardButton("🗑 Удалить канал", callback_data=f"delete_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="my_channels")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== АВТОПОСТИНГ ====================
async def auto_poster(context: ContextTypes.DEFAULT_TYPE, channel_config: dict, user_id: int):
    """Фоновая задача для автопостинга"""
    channel_id = channel_config["channel_id"]
    
    while True:
        try:
            user = bot.get_user(user_id)
            current_config = user.get_channel_config(channel_id)
            
            if not current_config or not current_config.is_active:
                break
            
            current_time = time.time()
            time_since_last = current_time - current_config.last_post_time
            
            if time_since_last >= current_config.interval_seconds:
                loggep.info(f"📤 Автопостинг в {channel_config['channel_name']}")
                
                success = await bot.post_to_channel(
                    context, channel_id, 
                    current_config.theme, 
                    current_config.size,
                    user_id
                )
                
                if success:
                    for ch in user.channels:
                        if ch["channel_id"] == channel_id:
                            ch["last_post_time"] = current_time
                            ch["posts_today"] += 1
                            break
                    bot.save_data()
            
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Ошибка автопостинга: {e}")
            await asyncio.sleep(30)

async def start_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Запуск автопостинга для всех каналов"""
    user = bot.get_user(user_id)
    
    if not user.channels:
        await update.callback_query.edit_message_text(
            "❌ У вас нет добавленных каналов!\n\n"
            "Сначала добавьте канал через '📢 Добавить канал'",
            parse_mode='HTML'
        )
        return
    
    started = 0
    for channel in user.channels:
        channel_id = channel["channel_id"]
        
        if channel_id not in bot.running_tasks or bot.running_tasks[channel_id].done():
            task = asyncio.create_task(auto_poster(context, channel, user_id))
            bot.running_tasks[channel_id] = task
            started += 1
            channel["is_active"] = True
    
    bot.save_data()
    
    await update.callback_query.edit_message_text(
        f"✅ <b>Автопостинг запущен!</b>\n\n"
        f"📊 Запущено каналов: {started}\n"
        f"🎯 Каждый канал постит с заданным интервалом\n\n"
        f"🛑 Для остановки нажмите '⏸ Остановить автопостинг'",
        parse_mode='HTML'
    )

async def stop_auto_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка автопостинга"""
    user_id = update.effective_user.id
    
    stopped = 0
    for channel_id, task in list(bot.running_tasks.items()):
        if not task.done():
            task.cancel()
            stopped += 1
        
        user = bot.get_user(user_id)
        for ch in user.channels:
            if ch["channel_id"] == channel_id:
                ch["is_active"] = False
                break
    
    bot.running_tasks.clear()
    bot.save_data()
    
    await update.callback_query.edit_message_text(
        f"⏸ <b>Автопостинг остановлен!</b>\n\n"
        f"🛑 Остановлено каналов: {stopped}\n\n"
        f"▶️ Для запуска нажмите '▶️ Запустить автопостинг'",
        parse_mode='HTML'
    )

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.get_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = f"""
✨ <b>Привет, {user.first_name}!</b> ✨

🤖 <b>Я бот для автопостинга с ИИ</b>

📝 <b>Что я умею:</b>
• 📢 Публиковать посты в Telegram каналы
• 🎨 20 разных тематик на выбор
• ⚡ Интервалы от 10 секунд
• 🎲 Генерация уникальных постов через GigaChat AI
• 💎 Все тарифы БЕСПЛАТНЫЕ

🎯 <b>Как начать:</b>
1️⃣ Добавь меня в канал как администратора
2️⃣ Нажми "📢 Добавить канал"
3️⃣ Настрой тему, размер и интервал
4️⃣ Запусти автопостинг!

👇 <b>Выбери действие:</b>
"""
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 <b>Добавление канала</b>\n\n"
        "1️⃣ Добавьте бота в канал как <b>администратора</b>\n"
        "2️⃣ Перешлите <b>любое сообщение</b> из канала сюда\n"
        "3️⃣ Или отправьте <b>ID канала</b> (@username или -100xxx)\n\n"
        "✅ После добавления можно настроить параметры постинга",
        parse_mode='HTML'
    )
    context.user_data['awaiting_channel'] = True

async def handle_channel_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_channel'):
        return
    
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    
    channel_id = None
    channel_name = None
    
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        channel_id = str(chat.id)
        channel_name = chat.title
    elif update.message.text:
        text = update.message.text.strip()
        if text.startswith('@') or text.startswith('-100'):
            channel_id = text
            try:
                chat = await context.bot.get_chat(int(text) if text.startswith('-100') else text)
                channel_name = chat.title
            except:
                channel_name = "Неизвестный канал"
    
    if not channel_id:
        await update.message.reply_text("❌ Не удалось определить канал. Перешлите сообщение из канала.")
        return
    
    tariff = TARIFFS[user.tariff]
    if len(user.channels) >= tariff["channels"]:
        await update.message.reply_text(
            f"❌ Лимит каналов для тарифа {tariff['name']}: {tariff['channels']}\n"
            f"💎 Выберите другой тариф в меню '💎 Тарифы'"
        )
        return
    
    for ch in user.channels:
        if ch["channel_id"] == channel_id:
            await update.message.reply_text("❌ Этот канал уже добавлен!")
            return
    
    user.add_channel(ChannelConfig(
        channel_id=channel_id,
        channel_name=channel_name,
        theme="ai_news",
        size="medium",
        interval_seconds=3600,
        last_post_time=0,
        posts_today=0,
        last_reset_date=datetime.now().strftime("%Y-%m-%d")
    ))
    
    bot.save_data()
    
    await update.message.reply_text(
        f"✅ <b>Канал добавлен!</b>\n\n"
        f"📢 <b>{channel_name}</b>\n"
        f"🆔 <code>{channel_id}</code>\n\n"
        f"📊 Всего каналов: {len(user.channels)}/{tariff['channels']}\n\n"
        f"⚙️ Теперь настройте:\n"
        f"• 🎨 Тему через '🎨 Выбрать тему'\n"
        f"• 📏 Размер через '📏 Выбрать размер'\n"
        f"• ⏱ Интервал через '⏱ Настройка интервала'",
        parse_mode='HTML'
    )
    
    context.user_data['awaiting_channel'] = False

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await update.callback_query.edit_message_text(
            "❌ Нет добавленных каналов!\nДобавьте канал через '📢 Добавить канал'",
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for ch in user.channels:
        keyboard.append([InlineKeyboardButton(
            f"📢 {ch['channel_name'][:30]}",
            callback_data=f"post_now_{ch['channel_id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.callback_query.edit_message_text(
        "🎯 <b>Выберите канал для публикации:</b>\n\n"
        "Пост будет создан с текущими настройками канала",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.replace("post_now_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    config = user.get_channel_config(channel_id)
    if not config:
        await query.edit_message_text("❌ Канал не найден")
        return
    
    await query.edit_message_text("🎲 <b>Генерирую пост...</b>", parse_mode='HTML')
    
    success = await bot.post_to_channel(context, channel_id, config.theme, config.size, user_id)
    
    if success:
        await query.edit_message_text(
            f"✅ <b>Пост успешно опубликован!</b>\n\n"
            f"📢 Канал: {config.channel_name}\n"
            f"🎨 Тема: {POSTING_THEMES[config.theme]['name']}\n"
            f"📏 Размер: {POST_SIZES[config.size]['name']}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В меню", callback_data="back_main")
            ]])
        )
    else:
        await query.edit_message_text("❌ Ошибка при публикации поста")

async def my_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    
    if not user.channels:
        await update.callback_query.edit_message_text(
            "❌ <b>У вас нет добавленных каналов</b>\n\n"
            "Нажмите '📢 Добавить канал' чтобы начать",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="back_main")
            ]])
        )
        return
    
    text = "📋 <b>Ваши каналы</b>\n\n"
    
    for ch in user.channels:
        theme = POSTING_THEMES.get(ch["theme"], POSTING_THEMES["ai_news"])
        size = POST_SIZES.get(ch["size"], POST_SIZES["medium"])
        interval_sec = ch["interval_seconds"]
        interval_text = INTERVALS.get(interval_sec, f"{interval_sec} сек")
        status = "✅ Активен" if ch.get("is_active", True) else "⏸ Остановлен"
        
        text += f"<b>📢 {ch['channel_name']}</b>\n"
        text += f"└ 🎨 {theme['emoji']} {theme['name']}\n"
        text += f"└ 📏 {size['emoji']} {size['name']}\n"
        text += f"└ ⏱ {interval_text}\n"
        text += f"└ 📊 {status}\n\n"
    
    keyboard = await get_channels_keyboard(user_id)
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)

async def channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    channel_id = query.data.replace("channel_", "")
    user_id = query.from_user.id
    user = bot.get_user(user_id)
    
    config = user.get_channel_config(channel_id)
    if not config:
        await query.edit_message_text("❌ Канал не найден")
        return
    
    theme = POSTING_THEMES[config.theme]
    size = POST_SIZES[config.size]
    interval_text = INTERVALS.get(config.interval_seconds, f"{config.interval_seconds} сек")
    
    text = f"""
<b>⚙️ Настройки канала</b>

📢 <b>{config.channel_name}</b>

🎨 <b>Тема:</b> {theme['emoji']} {theme['name']}
📏 <b>Размер:</b> {size['emoji']} {size['name']}
⏱ <b>Интервал:</b> {interval_text}
📊 <b>Статус:</b> {'✅ Активен' if config.is_active else '⏸ Остановлен'}

Выберите параметр для изменения:
"""
    
    keyboard = await get_channel_settings_keyboard(channel_id)
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)

async def update_channel_theme(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str, theme: str):
    user_id = update.callback_query.from_user.id
    user = bot.get_user(user_id)
    
    for ch in user.channels:
        if ch["channel_id"] == channel_id:
            ch["theme"] = theme
            break
    
    bot.save_data()
    
    await update.callback_query.edit_message_text(
        f"✅ <b>Тема обновлена!</b>\n\n"
        f"Новая тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К настройкам", callback_data=f"channel_{channel_id}")
        ]])
    )

async def update_channel_size(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str, size: str):
    user_id = update.callback_query.from_user.id
    user = bot.get_user(user_id)
    
    for ch in user.channels:
        if ch["channel_id"] == channel_id:
            ch["size"] = size
            break
    
    bot.save_data()
    
    await update.callback_query.edit_message_text(
        f"✅ <b>Размер обновлен!</b>\n\n"
        f"Новый размер: {POST_SIZES[size]['emoji']} {POST_SIZES[size]['name']}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К настройкам", callback_data=f"channel_{channel_id}")
        ]])
    )

async def update_channel_interval(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str, interval_sec: int):
    user_id = update.callback_query.from_user.id
    user = bot.get_user(user_id)
    
    for ch in user.channels:
        if ch["channel_id"] == channel_id:
            ch["interval_seconds"] = interval_sec
            break
    
    bot.save_data()
    
    interval_text = INTERVALS.get(interval_sec, f"{interval_sec} сек")
    
    await update.callback_query.edit_message_text(
        f"✅ <b>Интервал обновлен!</b>\n\n"
        f"Новый интервал: {interval_text}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К настройкам", callback_data=f"channel_{channel_id}")
        ]])
    )

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    user_id = update.callback_query.from_user.id
    user = bot.get_user(user_id)
    
    user.channels = [ch for ch in user.channels if ch["channel_id"] != channel_id]
    
    if channel_id in bot.running_tasks:
        bot.running_tasks[channel_id].cancel()
        del bot.running_tasks[channel_id]
    
    bot.save_data()
    
    await update.callback_query.edit_message_text(
        "✅ <b>Канал удален!</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В меню", callback_data="back_main")
        ]])
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = bot.get_user(user_id)
    tariff = TARIFFS[user.tariff]
    
    total_posts = sum(ch.get("posts_today", 0) for ch in user.channels)
    
    text = f"""
📊 <b>Ваша статистика</b>

👤 <b>Пользователь:</b> {user.first_name}
💎 <b>Тариф:</b> {tariff['emoji']} {tariff['name']}

📢 <b>Каналов:</b> {len(user.channels)}/{tariff['channels']}

📝 <b>Постов сегодня:</b> {total_posts}
⏱ <b>Мин. интервал:</b> {tariff['interval_min']} сек

🎯 <b>Активные каналы:</b>
"""
    
    for ch in user.channels:
        theme = POSTING_THEMES[ch["theme"]]
        status = "✅" if ch.get("is_active", True) else "⏸"
        text += f"\n{status} {theme['emoji']} {ch['channel_name'][:25]}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def tariffs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💎 <b>Тарифы (ВСЕ БЕСПЛАТНЫЕ!)</b>\n\n"
    
    for tariff_key, tariff in TARIFFS.items():
        text += f"<b>{tariff['emoji']} {tariff['name']}</b>\n"
        text += f"└ 📊 Каналов: {tariff['channels']}\n"
        text += f"└ 📝 Постов: безлимит\n"
        text += f"└ 🔄 Перепост: {'✅' if tariff['can_repost'] else '❌'}\n"
        text += f"└ ⏰ Расписание: {'✅' if tariff['can_schedule'] else '❌'}\n"
        text += f"└ ⚡ Интервал: от {tariff['interval_min']} сек\n"
        text += f"└ 💰 Цена: <b>БЕСПЛАТНО!</b>\n\n"
    
    keyboard = await get_tariffs_keyboard()
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🆘 <b>Помощь по боту</b>

📌 <b>Основные возможности:</b>
• Генерация постов через ИИ (GigaChat)
• 20 различных тематик
• Автоматический постинг с интервалом от 10 сек
• Все тарифы БЕСПЛАТНЫЕ

🎨 <b>Темы (20 шт):</b>
🤖 ИИ Новости | 🪙 Криптовалюты | 🎨 NFT
📱 Telegram | 💼 Бизнес | 📡 Технологии
🔬 Наука | 💪 Здоровье | 🧠 Психология
📈 Маркетинг | 🎨 Дизайн | 💻 Программирование
🎮 Игры | 🎬 Кино | 🎵 Музыка
⚽ Спорт | ✈️ Путешествия | 🍳 Кулинария
📚 Образование | 💪 Мотивация

📏 <b>Размеры постов:</b>
🔹 Мини (50-150 симв.)
🔸 Короткий (150-300)
📄 Средний (300-600)
📚 Длинный (600-1000)
⭐ Эпичный (1000-1500)

⚡ <b>Интервалы:</b>
10 сек - 24 часа, любой на выбор!

💡 <b>Советы:</b>
• Добавьте бота в канал как администратора
• Настройте тему и размер под свой канал
• Запустите автопостинг и расслабляйтесь!

❓ <b>Вопросы?</b> Пишите @support
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="back_main")
        ]]))
    else:
        await update.message.reply_text(text, parse_mode='HTML')

# ==================== ОБРАБОТКА CALLBACK'ОВ ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "back_main":
        keyboard = await get_main_keyboard()
        await query.edit_message_text("🏠 <b>Главное меню</b>", parse_mode='HTML', reply_markup=keyboard)
    
    elif data == "add_channel":
        await add_channel_start(update, context)
    
    elif data == "my_channels":
        await my_channels_menu(update, context)
    
    elif data == "select_theme":
        keyboard = await get_themes_keyboard()
        await query.edit_message_text("🎨 <b>Выберите тему</b>\n\nТема определяет стиль и содержание постов", parse_mode='HTML', reply_markup=keyboard)
    
    elif data == "select_size":
        keyboard = await get_sizes_keyboard()
        await query.edit_message_text("📏 <b>Выберите размер поста</b>\n\nОт размера зависит длина текста", parse_mode='HTML', reply_markup=keyboard)
    
    elif data == "select_interval":
        keyboard = await get_intervals_keyboard()
        await query.edit_message_text("⏱ <b>Выберите интервал</b>\n\nКак часто публиковать посты", parse_mode='HTML', reply_markup=keyboard)
    
    elif data == "start_auto":
        await start_auto_posting(update, context, query.from_user.id)
    
    elif data == "stop_auto":
        await stop_auto_posting(update, context)
    
    elif data == "post_now":
        await post_now(update, context)
    
    elif data == "tariffs":
        await tariffs_menu(update, context)
    
    elif data == "stats":
        await stats(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data.startswith("themes_page_"):
        page = int(data.split("_")[2])
        keyboard = await get_themes_keyboard(page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    elif data.startswith("theme_"):
        theme = data.replace("theme_", "")
        context.user_data['temp_theme'] = theme
        keyboard = await get_sizes_keyboard()
        await query.edit_message_text(
            f"✅ Выбрана тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n\n"
            f"📏 Теперь выберите размер поста:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif data.startswith("size_"):
        size = data.replace("size_", "")
        
        if 'temp_theme' in context.user_data:
            theme = context.user_data['temp_theme']
            user_id = query.from_user.id
            user = bot.get_user(user_id)
            
            if user.channels:
                for ch in user.channels:
                    ch["theme"] = theme
                    ch["size"] = size
                bot.save_data()
                
                await query.edit_message_text(
                    f"✅ <b>Настройки обновлены для всех каналов!</b>\n\n"
                    f"🎨 Тема: {POSTING_THEMES[theme]['emoji']} {POSTING_THEMES[theme]['name']}\n"
                    f"📏 Размер: {POST_SIZES[size]['emoji']} {POST_SIZES[size]['name']}\n\n"
                    f"⚙️ Для настройки конкретного канала - '⚙️ Мои каналы'",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 В меню", callback_data="back_main")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ <b>Нет добавленных каналов!</b>\n\n"
                    "Сначала добавьте канал через '📢 Добавить канал'",
                    parse_mode='HTML'
                )
            del context.user_data['temp_theme']
    
    elif data.startswith("interval_"):
        interval = int(data.replace("interval_", ""))
        user_id = query.from_user.id
        user = bot.get_user(user_id)
        
        if user.channels:
            for ch in user.channels:
                ch["interval_seconds"] = interval
            bot.save_data()
            
            await query.edit_message_text(
                f"✅ <b>Интервал обновлен для всех каналов!</b>\n\n"
                f"⏱ Новый интервал: {INTERVALS[interval]}\n\n"
                f"⚙️ Для настройки конкретного канала - '⚙️ Мои каналы'",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 В меню", callback_data="back_main")
                ]])
            )
        else:
            await query.edit_message_text("❌ Нет добавленных каналов!")
    
    elif data.startswith("channel_"):
        await channel_settings(update, context)
    
    elif data.startswith("ch_theme_"):
        channel_id = data.replace("ch_theme_", "")
        keyboard = await get_themes_keyboard()
        context.user_data['temp_channel_for_theme'] = channel_id
        await query.edit_message_text("🎨 Выберите новую тему:", parse_mode='HTML', reply_markup=keyboard)
    
    elif data.startswith("ch_size_"):
        channel_id = data.replace("ch_size_", "")
        keyboard = await get_sizes_keyboard()
        context.user_data['temp_channel_for_size'] = channel_id
        await query.edit_message_text("📏 Выберите новый размер:", parse_mode='HTML', reply_markup=keyboard)
    
    elif data.startswith("ch_interval_"):
        channel_id = data.replace("ch_interval_", "")
        keyboard = await get_intervals_keyboard()
        context.user_data['temp_channel_for_interval'] = channel_id
        await query.edit_message_text("⏱ Выберите новый интервал:", parse_mode='HTML', reply_markup=keyboard)
    
    elif data.startswith("delete_"):
        channel_id = data.replace("delete_", "")
        await delete_channel(update, context, channel_id)
    
    elif data.startswith("post_now_"):
        await handle_post_now(update, context)
    
    elif data.startswith("tariff_"):
        tariff = data.replace("tariff_", "")
        user_id = query.from_user.id
        user = bot.get_user(user_id)
        user.tariff = tariff
        bot.save_data()
        
        await query.edit_message_text(
            f"✅ <b>Тариф изменен на {TARIFFS[tariff]['name']}</b>\n\n"
            f"📊 Каналов: {TARIFFS[tariff]['channels']}\n"
            f"⚡ Интервал: от {TARIFFS[tariff]['interval_min']} сек\n\n"
            f"🎉 Все тарифы бесплатные!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В меню", callback_data="back_main")
            ]])
        )
    
    elif data.startswith("theme_for_channel_"):
        theme = data.replace("theme_for_channel_", "")
        channel_id = context.user_data.get('temp_channel_for_theme')
        if channel_id:
            await update_channel_theme(update, context, channel_id, theme)
            del context.user_data['temp_channel_for_theme']
    
    elif data.startswith("size_for_channel_"):
        size = data.replace("size_for_channel_", "")
        channel_id = context.user_data.get('temp_channel_for_size')
        if channel_id:
            await update_channel_size(update, context, channel_id, size)
            del context.user_data['temp_channel_for_size']
    
    elif data.startswith("interval_for_channel_"):
        interval = int(data.replace("interval_for_channel_", ""))
        channel_id = context.user_data.get('temp_channel_for_interval')
        if channel_id:
            await update_channel_interval(update, context, channel_id, interval)
            del context.user_data['temp_channel_for_interval']

# ==================== ЗАПУСК ====================
def main():
    bot.load_data()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_forward))
    
    logger.info("🚀 Бот автопостинга запущен!")
    logger.info(f"📊 Доступно тем: {len(POSTING_THEMES)}")
    logger.info(f"💰 Все тарифы бесплатные!")
    logger.info(f"⚡ Интервалы: от 10 секунд до 24 часов")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
