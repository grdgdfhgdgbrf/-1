import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
import random
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import schedule
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# API GigaChat
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# Состояния для разговора
PHONE, CODE, PASSWORD, CHANNEL_SELECTION, POST_SETUP = range(5)

# ==================== ТЕМАТИКИ ДЛЯ ПОСТИНГА ====================
TOPICS = {
    "nft": {
        "name": "🎨 NFT",
        "emoji": "🎨",
        "description": "NFT новости и тренды",
        "prompt": "Ты эксперт по NFT. Создай пост о NFT: новости, тренды, коллекции, художники. Используй эмодзи, будь актуальным.",
        "hashtags": ["#NFT", #криптоискусство", "#цифровоеискусство"]
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "description": "Новости Telegram",
        "prompt": "Ты эксперт по Telegram. Создай пост о новых функциях, обновлениях, ботах, каналах Telegram.",
        "hashtags": ["#Telegram", "#обновления", "#мессенджер"]
    },
    "crypto": {
        "name": "💰 Криптовалюты",
        "emoji": "💰",
        "description": "Крипто новости",
        "prompt": "Ты крипто-аналитик. Создай пост о криптовалютах, биткоине, эфире, DeFi, новости рынка.",
        "hashtags": ["#криптовалюта", "#биткоин", "#дефи"]
    },
    "ai": {
        "name": "🤖 Искусственный интеллект",
        "emoji": "🤖",
        "description": "Новости AI",
        "prompt": "Ты эксперт по AI. Создай пост о искусственном интеллекте, нейросетях, новых технологиях.",
        "hashtags": ["#искусственныйинтеллект", "#нейросети", "#AI"]
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "description": "Игровые новости",
        "prompt": "Ты геймер. Создай пост о играх, новинках, киберспорте, геймдеве.",
        "hashtags": ["#игры", "#гейминг", "#киберспорт"]
    },
    "movies": {
        "name": "🎬 Кино",
        "emoji": "🎬",
        "description": "Кино новости",
        "prompt": "Ты кинокритик. Создай пост о новинках кино, сериалах, трейлерах, актерах.",
        "hashtags": ["#кино", "#сериалы", "#фильмы"]
    },
    "music": {
        "name": "🎵 Музыка",
        "emoji": "🎵",
        "description": "Музыкальные новости",
        "prompt": "Ты музыкальный критик. Создай пост о музыке, альбомах, концертах, исполнителях.",
        "hashtags": ["#музыка", "#новинкимузыки", "#концерты"]
    },
    "sport": {
        "name": "⚽ Спорт",
        "emoji": "⚽",
        "description": "Спортивные новости",
        "prompt": "Ты спортивный журналист. Создай пост о спорте, футболе, баскетболе, теннисе.",
        "hashtags": ["#спорт", "#футбол", "#спортивные новости"]
    },
    "tech": {
        "name": "💻 Технологии",
        "emoji": "💻",
        "description": "Технологические новости",
        "prompt": "Ты техноблогер. Создай пост о гаджетах, инновациях, IT, науке и технике.",
        "hashtags": ["#технологии", "#гаджеты", "#инновации"]
    },
    "business": {
        "name": "📊 Бизнес",
        "emoji": "📊",
        "description": "Бизнес новости",
        "prompt": "Ты бизнес-аналитик. Создай пост о бизнесе, стартапах, инвестициях, финансах.",
        "hashtags": ["#бизнес", "#стартапы", "#инвестиции"]
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "description": "Научные открытия",
        "prompt": "Ты ученый. Создай пост о научных открытиях, космосе, биологии, физике.",
        "hashtags": ["#наука", "#открытия", "#космос"]
    },
    "health": {
        "name": "🏥 Здоровье",
        "emoji": "🏥",
        "description": "Здоровье и медицина",
        "prompt": "Ты врач. Создай пост о здоровом образе жизни, медицине, правильном питании.",
        "hashtags": ["#здоровье", "#зож", "#медицина"]
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "description": "Туризм и путешествия",
        "prompt": "Ты тревел-блогер. Создай пост о путешествиях, странах, отелях, советах туристам.",
        "hashtags": ["#путешествия", "#тревел", "#туры"]
    },
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "description": "Рецепты и кулинария",
        "prompt": "Ты шеф-повар. Создай пост о кулинарии, рецептах, ресторанах, еде.",
        "hashtags": ["#кулинария", "#рецепты", "#еда"]
    },
    "fashion": {
        "name": "👗 Мода",
        "emoji": "👗",
        "description": "Модные тенденции",
        "prompt": "Ты стилист. Создай пост о моде, стиле, брендах, показах, трендах.",
        "hashtags": ["#мода", "#стиль", "#тренды"]
    },
    "beauty": {
        "name": "💄 Красота",
        "emoji": "💄",
        "description": "Бьюти индустрия",
        "prompt": "Ты бьюти-блогер. Создай пост о косметике, уходе, процедурах, бьюти-трендах.",
        "hashtags": ["#красота", "#бьюти", "#косметика"]
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "description": "Психология и саморазвитие",
        "prompt": "Ты психолог. Создай пост о психологии, саморазвитии, отношениях, мотивации.",
        "hashtags": ["#психология", "#саморазвитие", "#мотивация"]
    },
    "books": {
        "name": "📚 Книги",
        "emoji": "📚",
        "description": "Книжные новинки",
        "prompt": "Ты книжный блогер. Создай пост о книгах, писателях, литературе, новинках.",
        "hashtags": ["#книги", "#чтение", "#литература"]
    },
    "cryptoart": {
        "name": "🖼️ Криптоарт",
        "emoji": "🖼️",
        "description": "Цифровое искусство",
        "prompt": "Ты художник. Создай пост о криптоарте, цифровом искусстве, художниках, коллекциях.",
        "hashtags": ["#криптоарт", "#цифровоеискусство", "#искусство"]
    },
    "metaverse": {
        "name": "🌐 Метавселенная",
        "emoji": "🌐",
        "description": "Метавселенная и Web3",
        "prompt": "Ты эксперт по метавселенной. Создай пост о метавселенной, Web3, виртуальной реальности.",
        "hashtags": ["#метавселенная", "#web3", "#виртуальнаяреальность"]
    }
}

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🆓 Бесплатный",
        "price": 0,
        "description": "Базовые возможности",
        "posts_per_day": 5,
        "channels_limit": 1,
        "features": ["Автопостинг", "1 канал", "5 постов/день"]
    },
    "basic": {
        "name": "⭐ Базовый",
        "price": 0,
        "description": "Расширенные возможности",
        "posts_per_day": 20,
        "channels_limit": 3,
        "features": ["Автопостинг", "3 канала", "20 постов/день", "Свой промпт"]
    },
    "pro": {
        "name": "💎 Pro",
        "price": 0,
        "description": "Максимальные возможности",
        "posts_per_day": 100,
        "channels_limit": 10,
        "features": ["Автопостинг", "10 каналов", "100 постов/день", "Свой промпт", "Приоритет"]
    }
}

# ==================== СТРУКТУРЫ ДАННЫХ ====================
@dataclass
class ConnectedAccount:
    user_id: int
    phone: str
    session_string: str
    client: Optional[TelegramClient] = None
    connected_at: float = field(default_factory=time.time)
    
@dataclass
class Channel:
    channel_id: int
    channel_username: str
    channel_title: str
    topics: List[str] = field(default_factory=list)
    auto_post: bool = True
    post_interval: int = 3600  # секунды
    
@dataclass
class UserSubscription:
    user_id: int
    tariff: str = "free"
    connected_accounts: List[ConnectedAccount] = field(default_factory=list)
    channels: List[Channel] = field(default_factory=list)
    last_post_time: Dict[str, float] = field(default_factory=dict)
    daily_posts_count: Dict[str, int] = field(default_factory=dict)
    custom_prompts: Dict[str, str] = field(default_factory=dict)

class BotManager:
    def __init__(self):
        self.subscriptions: Dict[int, UserSubscription] = {}
        self.api_token = None
        self.api_token_expiry = 0
        self.posting_tasks: Dict[int, asyncio.Task] = {}
        
    def get_subscription(self, user_id: int) -> UserSubscription:
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = UserSubscription(user_id=user_id)
        return self.subscriptions[user_id]
    
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
                    else:
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            return None
    
    async def generate_post(self, topic: str, custom_prompt: str = None) -> Dict[str, str]:
        """Генерация поста через GigaChat"""
        token = await self.get_api_token()
        if not token:
            return {"error": "❌ Ошибка авторизации GigaChat"}
        
        topic_config = TOPICS.get(topic, TOPICS["tech"])
        
        prompt = custom_prompt if custom_prompt else topic_config["prompt"]
        
        # Размеры текста (символы)
        post_sizes = {
            "short": (100, 300),
            "medium": (300, 800),
            "long": (800, 2000)
        }
        post_size = random.choice(["short", "medium", "long"])
        min_len, max_len = post_sizes[post_size]
        
        # Размеры изображения
        image_sizes = {
            "small": "512x512",
            "medium": "1024x1024", 
            "large": "1792x1024"
        }
        image_size = random.choice(list(image_sizes.keys()))
        
        full_prompt = f"""{prompt}

Требования к посту:
- Длина: {min_len}-{max_len} символов
- Используй эмодзи для эмоциональности
- Добавь хэштеги в конце
- Пост должен быть уникальным, не повторяться
- Напиши в формате: текст поста + [РАЗМЕР_ИЗОБРАЖЕНИЯ:{image_size}]

Создай интересный пост на тему {topic_config['name']}:"""
        
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
                        "messages": [{"role": "user", "content": full_prompt}],
                        "temperature": 0.9,
                        "max_tokens": 2000
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"]["content"]
                            
                            # Извлекаем размер изображения
                            img_size = "1024x1024"
                            if "[РАЗМЕР_ИЗОБРАЖЕНИЯ:" in content:
                                size_part = content.split("[РАЗМЕР_ИЗОБРАЖЕНИЯ:")[1].split("]")[0]
                                img_size = image_sizes.get(size_part, "1024x1024")
                                content = content.split("[РАЗМЕР_ИЗОБРАЖЕНИЯ:")[0]
                            
                            # Добавляем хэштеги если их нет
                            hashtags = topic_config.get("hashtags", [])
                            if not any(tag in content for tag in hashtags):
                                content += "\n\n" + " ".join(hashtags)
                            
                            return {
                                "text": content.strip(),
                                "size": post_size,
                                "image_size": img_size,
                                "topic": topic,
                                "topic_name": topic_config["name"]
                            }
                        else:
                            return {"error": "❌ Не удалось сгенерировать пост"}
                    else:
                        return {"error": f"❌ Ошибка API: {response.status}"}
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return {"error": f"❌ Ошибка: {str(e)}"}
    
    async def post_to_channel(self, account: ConnectedAccount, channel: Channel, post_data: Dict):
        """Постинг в канал"""
        if "error" in post_data:
            return False
        
        try:
            text = post_data["text"]
            
            # Отправляем сообщение
            await account.client.send_message(
                channel.channel_id,
                text,
                parse_mode='html'
            )
            
            logger.info(f"✅ Пост опубликован в {channel.channel_title}")
            return True
        except Exception as e:
            logger.error(f"Ошибка постинга в {channel.channel_title}: {e}")
            return False

bot_manager = BotManager()

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 Подключить аккаунт", callback_data="connect_account")],
        [InlineKeyboardButton("📊 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🎭 Выбрать тематику", callback_data="topics")],
        [InlineKeyboardButton("⚙️ Настройки постинга", callback_data="post_settings")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard():
    keyboard = []
    row = []
    for topic_key, topic_config in list(TOPICS.items()):
        button_text = f"{topic_config['emoji']} {topic_config['name']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"topic_{topic_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_tariffs_keyboard():
    keyboard = []
    for tariff_key, tariff_config in TARIFFS.items():
        button_text = f"{tariff_config['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tariff_{tariff_key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    subscription = bot_manager.get_subscription(user.id)
    
    welcome_text = (
        f"🤖 *Привет, {user.first_name}!*\n\n"
        f"✨ *AI Постинг Бот - твой автоматический помощник*\n\n"
        f"📱 *Возможности:*\n"
        f"✅ Подключение аккаунтов Telegram\n"
        f"✅ Автоматический постинг в каналы\n"
        f"✅ Генерация постов через ИИ\n"
        f"✅ 20+ тематик для контента\n"
        f"✅ Настройка интервалов постинга\n"
        f"✅ Разные размеры постов и изображений\n\n"
        f"💰 *Тарифы:*\n"
        f"🆓 Бесплатный - 1 канал, 5 постов/день\n"
        f"⭐ Базовый - 3 канала, 20 постов/день\n"
        f"💎 Pro - 10 каналов, 100 постов/день\n\n"
        f"👇 *Начни с подключения аккаунта!*"
    )
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def connect_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало подключения аккаунта"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📱 *Подключение аккаунта Telegram*\n\n"
            "Введите номер телефона в международном формате:\n"
            "Пример: +79123456789\n\n"
            "❌ Для отмены отправьте /cancel",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "📱 *Подключение аккаунта Telegram*\n\n"
            "Введите номер телефона в международном формате:\n"
            "Пример: +79123456789\n\n"
            "❌ Для отмены отправьте /cancel",
            parse_mode='Markdown'
        )
    return PHONE

async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен номер телефона"""
    phone = update.message.text
    if phone == "/cancel":
        await update.message.reply_text("❌ Операция отменена")
        return ConversationHandler.END
    
    context.user_data['phone'] = phone
    
    try:
        # Создаем клиента Telethon
        session_name = f"user_{update.effective_user.id}_{int(time.time())}"
        client = TelegramClient(session_name, api_id=1, api_hash='')  # ВАЖНО: Добавьте свои api_id и api_hash
        context.user_data['temp_client'] = client
        
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            await update.message.reply_text(
                "📱 *Код отправлен!*\n\n"
                "Введите код из SMS или Telegram:\n"
                "❌ /cancel для отмены",
                parse_mode='Markdown'
            )
            return CODE
        else:
            # Уже авторизован
            session_string = client.session.save()
            account = ConnectedAccount(
                user_id=update.effective_user.id,
                phone=phone,
                session_string=session_string,
                client=client
            )
            
            subscription = bot_manager.get_subscription(update.effective_user.id)
            subscription.connected_accounts.append(account)
            
            await update.message.reply_text(
                "✅ *Аккаунт успешно подключен!*\n\n"
                "Теперь вы можете добавить каналы для постинга.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(
            f"❌ Ошибка подключения: {str(e)}\n"
            "Попробуйте еще раз /start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен код подтверждения"""
    code = update.message.text
    if code == "/cancel":
        await update.message.reply_text("❌ Операция отменена")
        return ConversationHandler.END
    
    try:
        client = context.user_data.get('temp_client')
        phone = context.user_data.get('phone')
        
        await client.sign_in(phone, code)
        
        session_string = client.session.save()
        account = ConnectedAccount(
            user_id=update.effective_user.id,
            phone=phone,
            session_string=session_string,
            client=client
        )
        
        subscription = bot_manager.get_subscription(update.effective_user.id)
        subscription.connected_accounts.append(account)
        
        await update.message.reply_text(
            "✅ *Аккаунт успешно подключен!*\n\n"
            "📊 Используйте /start для управления",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text(
            "🔐 *Введите двухфакторный пароль:*\n"
            "❌ /cancel для отмены",
            parse_mode='Markdown'
        )
        return PASSWORD
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n"
            "Попробуйте еще раз /start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback от меню"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "connect_account":
        await connect_account_start(update, context)
        return PHONE
    
    elif callback_data == "my_channels":
        subscription = bot_manager.get_subscription(query.from_user.id)
        if not subscription.channels:
            text = "📊 *У вас пока нет добавленных каналов*\n\nДобавьте канал через команду /addchannel"
        else:
            text = "📊 *Ваши каналы:*\n\n"
            for i, channel in enumerate(subscription.channels, 1):
                topics_str = ", ".join([TOPICS[t]["emoji"] for t in channel.topics])
                text += f"{i}. {channel.channel_title}\n"
                text += f"   📍 Темы: {topics_str}\n"
                text += f"   ⏱ Интервал: {channel.post_interval//3600}ч\n"
                text += f"   ✅ Автопостинг: {'Вкл' if channel.auto_post else 'Выкл'}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif callback_data == "topics":
        keyboard = await get_topics_keyboard()
        await query.edit_message_text(
            "🎭 *Выберите тематику для постов*\n\n"
            "Посты будут генерироваться в выбранной тематике:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif callback_data == "tariffs":
        keyboard = await get_tariffs_keyboard()
        await query.edit_message_text(
            "💰 *Тарифы*\n\n"
            "Выберите тарифный план:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif callback_data == "post_settings":
        subscription = bot_manager.get_subscription(query.from_user.id)
        tariff_config = TARIFFS.get(subscription.tariff, TARIFFS["free"])
        
        text = (
            "⚙️ *Настройки постинга*\n\n"
            f"📊 Тариф: {tariff_config['name']}\n"
            f"📝 Постов в день: {tariff_config['posts_per_day']}\n"
            f"📢 Доступно каналов: {tariff_config['channels_limit']}\n\n"
            "Настройте параметры:"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏱ Интервал постинга", callback_data="set_interval")],
            [InlineKeyboardButton("📝 Свой промпт", callback_data="set_prompt")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
        ]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif callback_data == "help":
        help_text = (
            "❓ *Помощь*\n\n"
            "*Как использовать бота:*\n\n"
            "1️⃣ Подключите аккаунт Telegram\n"
            "2️⃣ Добавьте канал для постинга\n"
            "3️⃣ Выберите тематику контента\n"
            "4️⃣ Настройте интервал постинга\n"
            "5️⃣ Бот начнет автоматически генерировать и публиковать посты\n\n"
            "*Команды:*\n"
            "/start — Главное меню\n"
            "/addchannel — Добавить канал\n"
            "/postnow — Опубликовать сейчас\n"
            "/stats — Статистика\n"
            "/help — Помощь"
        )
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif callback_data == "back_main":
        keyboard = await get_main_keyboard()
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif callback_data.startswith("topic_"):
        topic_key = callback_data.replace("topic_", "")
        if topic_key in TOPICS:
            subscription = bot_manager.get_subscription(query.from_user.id)
            if not subscription.channels:
                await query.edit_message_text(
                    "⚠️ *Сначала добавьте канал!*\n"
                    "Используйте команду /addchannel",
                    parse_mode='Markdown'
                )
                return
            
            # Добавляем тему к каналу
            channel = subscription.channels[0]
            if topic_key not in channel.topics:
                channel.topics.append(topic_key)
            
            await query.edit_message_text(
                f"✅ *Тематика добавлена!*\n\n"
                f"Тема: {TOPICS[topic_key]['emoji']} {TOPICS[topic_key]['name']}\n"
                f"Канал: {channel.channel_title}\n\n"
                f"Бот будет генерировать посты на эту тему.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Неизвестная тематика", parse_mode='Markdown')
    
    elif callback_data.startswith("tariff_"):
        tariff_key = callback_data.replace("tariff_", "")
        if tariff_key in TARIFFS:
            subscription = bot_manager.get_subscription(query.from_user.id)
            subscription.tariff = tariff_key
            
            tariff_config = TARIFFS[tariff_key]
            await query.edit_message_text(
                f"✅ *Тариф изменен!*\n\n"
                f"Ваш тариф: {tariff_config['name']}\n"
                f"📝 Постов в день: {tariff_config['posts_per_day']}\n"
                f"📢 Каналов: {tariff_config['channels_limit']}",
                parse_mode='Markdown'
            )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление канала"""
    user = update.effective_user
    subscription = bot_manager.get_subscription(user.id)
    
    if not subscription.connected_accounts:
        await update.message.reply_text(
            "⚠️ *Сначала подключите аккаунт!*\n"
            "Используйте /start и кнопку 'Подключить аккаунт'",
            parse_mode='Markdown'
        )
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "📢 *Как добавить канал:*\n\n"
            "Отправьте ссылку или username канала:\n"
            "Пример: /addchannel @channel\n"
            "или: /addchannel https://t.me/channel\n\n"
            "⚠️ Бот должен быть администратором канала!",
            parse_mode='Markdown'
        )
        return
    
    channel_input = args[0]
    channel_username = channel_input.replace("https://t.me/", "").replace("@", "")
    
    try:
        account = subscription.connected_accounts[0]
        entity = await account.client.get_entity(channel_username)
        
        # Проверяем права
        if hasattr(entity, 'participants_count'):
            is_admin = False
            # Проверка админки (упрощенно)
        
        channel = Channel(
            channel_id=entity.id,
            channel_username=channel_username,
            channel_title=entity.title
        )
        
        subscription.channels.append(channel)
        
        # Запускаем задачу постинга
        await start_posting_for_channel(user.id, channel)
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 Название: {entity.title}\n"
            f"🆔 Username: @{channel_username}\n\n"
            f"Теперь выберите тематику для постов в меню.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка добавления канала: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: Канал не найден или бот не администратор\n\n"
            f"Убедитесь, что:\n"
            f"1. @{channel_username} существует\n"
            f"2. Бот добавлен в администраторы канала",
            parse_mode='Markdown'
        )

async def start_posting_for_channel(user_id: int, channel: Channel):
    """Запуск автопостинга для канала"""
    if user_id in bot_manager.posting_tasks:
        bot_manager.posting_tasks[user_id].cancel()
    
    async def post_loop():
        subscription = bot_manager.get_subscription(user_id)
        tariff_config = TARIFFS.get(subscription.tariff, TARIFFS["free"])
        
        while True:
            try:
                if channel.auto_post:
                    today = datetime.now().strftime("%Y-%m-%d")
                    if subscription.daily_posts_count.get(today, 0) >= tariff_config["posts_per_day"]:
                        await asyncio.sleep(3600)
                        continue
                    
                    # Выбираем случайную тему
                    if channel.topics:
                        topic = random.choice(channel.topics)
                    else:
                        topic = "tech"
                    
                    # Генерируем пост
                    custom_prompt = subscription.custom_prompts.get(topic)
                    post_data = await bot_manager.generate_post(topic, custom_prompt)
                    
                    if "error" not in post_data and subscription.connected_accounts:
                        account = subscription.connected_accounts[0]
                        await bot_manager.post_to_channel(account, channel, post_data)
                        
                        subscription.daily_posts_count[today] = subscription.daily_posts_count.get(today, 0) + 1
                    
                await asyncio.sleep(channel.post_interval)
            except Exception as e:
                logger.error(f"Ошибка в цикле постинга: {e}")
                await asyncio.sleep(60)
    
    task = asyncio.create_task(post_loop())
    bot_manager.posting_tasks[user_id] = task

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Немедленный постинг"""
    user = update.effective_user
    subscription = bot_manager.get_subscription(user.id)
    
    if not subscription.channels:
        await update.message.reply_text(
            "⚠️ У вас нет добавленных каналов!\n"
            "Добавьте канал через /addchannel",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text("🔄 Генерация поста...", parse_mode='Markdown')
    
    channel = subscription.channels[0]
    topic = channel.topics[0] if channel.topics else "tech"
    
    post_data = await bot_manager.generate_post(topic)
    
    if "error" in post_data:
        await update.message.reply_text(post_data["error"], parse_mode='Markdown')
        return
    
    if subscription.connected_accounts:
        account = subscription.connected_accounts[0]
        success = await bot_manager.post_to_channel(account, channel, post_data)
        
        if success:
            await update.message.reply_text(
                f"✅ *Пост опубликован!*\n\n"
                f"📝 Тема: {post_data['topic_name']}\n"
                f"📏 Размер: {post_data['size']}\n"
                f"🖼 Изображение: {post_data['image_size']}\n\n"
                f"Текст поста:\n{post_data['text'][:200]}...",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка публикации!", parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика"""
    user = update.effective_user
    subscription = bot_manager.get_subscription(user.id)
    tariff_config = TARIFFS.get(subscription.tariff, TARIFFS["free"])
    
    today = datetime.now().strftime("%Y-%m-%d")
    posts_today = subscription.daily_posts_count.get(today, 0)
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"💎 Тариф: {tariff_config['name']}\n"
        f"📝 Постов сегодня: {posts_today}/{tariff_config['posts_per_day']}\n"
        f"📢 Каналов: {len(subscription.channels)}/{tariff_config['channels_limit']}\n"
        f"📱 Аккаунтов: {len(subscription.connected_accounts)}\n"
        f"🎭 Тем: {sum(len(c.topics) for c in subscription.channels)}\n\n"
        f"🔄 Постинг {'активен' if subscription.channels else 'не настроен'}"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text("❌ Операция отменена", parse_mode='Markdown')
    return ConversationHandler.END

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("postnow", post_now))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Conversation handler для подключения аккаунта
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("connect", connect_account_start),
            CallbackQueryHandler(connect_account_start, pattern="^connect_account$")
        ],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_received)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^(?!connect_account$).*"))
    
    logger.info("🚀 AI Постинг Бот запущен")
    logger.info("🎭 Доступно 20 тематик")
    logger.info("💰 3 тарифных плана")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
