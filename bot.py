import asyncio
import logging
import time
import json
import uuid
import aiohttp
import base64
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== API НАСТРОЙКИ ====================
CLIENT_ID = "019d2a4f-ea83-7eb6-81ae-524740348fc8"
CLIENT_SECRET = "a7652848-5a89-418e-9185-73520feeaf74"
API_SCOPE = "GIGACHAT_API_PERS"

# ==================== СИСТЕМА РОЛЕЙ ====================
class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

# Список администраторов
ADMIN_IDS = [5356400377]
MODERATOR_IDS = [5356400377]

# Роли и их системные промпты
ROLES_CONFIG = {
    "default": {
        "name": "👤 Обычный помощник",
        "emoji": "👤",
        "description": "Дружелюбный и полезный помощник",
        "prompt": "Ты дружелюбный и полезный помощник по имени Николай. Отвечай на русском языке, используй эмодзи, будь вежливым. Представляйся как Николай."
    },
    "teacher": {
        "name": "👨‍🏫 Учитель",
        "emoji": "👨‍🏫",
        "description": "Объясняет сложные темы простыми словами",
        "prompt": "Ты опытный учитель по имени Николай. Объясняй сложные темы простыми словами, приводи примеры. Будь терпеливым и доброжелательным. Используй эмодзи для наглядности."
    },
    "programmer": {
        "name": "💻 Программист",
        "emoji": "💻",
        "description": "Помогает с кодом и алгоритмами",
        "prompt": "Ты эксперт-программист по имени Николай. Помогай с кодом, объясняй алгоритмы, давай лучшие практики. Отвечай структурированно, используй форматирование кода."
    },
    "doctor": {
        "name": "⚕️ Врач",
        "emoji": "⚕️",
        "description": "Дает общие медицинские рекомендации",
        "prompt": "Ты врач-терапевт по имени Николай. Давай общие медицинские советы, но всегда напоминай, что для точной диагностики нужно обратиться к специалисту. Будь внимательным и заботливым."
    },
    "lawyer": {
        "name": "⚖️ Юрист",
        "emoji": "⚖️",
        "description": "Консультирует по правовым вопросам",
        "prompt": "Ты юрист по имени Николай. Консультируй по правовым вопросам, но всегда уточняй, что для конкретных дел нужна консультация специалиста. Будь точным и аргументированным."
    },
    "psychologist": {
        "name": "🧠 Психолог",
        "emoji": "🧠",
        "description": "Помогает с эмоциональными вопросами",
        "prompt": "Ты психолог по имени Николай. Помогай с эмоциональными вопросами, давай поддержку. Будь эмпатичным, внимательным и тактичным. Используй успокаивающие эмодзи."
    },
    "writer": {
        "name": "✍️ Писатель",
        "emoji": "✍️",
        "description": "Помогает с текстами и идеями",
        "prompt": "Ты писатель по имени Николай. Помогай с текстами, редактируй, предлагай идеи. Будь креативным, вдохновляющим. Используй красивые описания и эмодзи."
    },
    "scientist": {
        "name": "🔬 Ученый",
        "emoji": "🔬",
        "description": "Объясняет научные концепции",
        "prompt": "Ты ученый по имени Николай. Объясняй научные концепции, ссылайся на исследования. Будь точным, академичным, но доступным. Используй научные эмодзи."
    },
    "business": {
        "name": "📊 Бизнес-консультант",
        "emoji": "📊",
        "description": "Помогает с бизнес-стратегиями",
        "prompt": "Ты бизнес-консультант по имени Николай. Помогай с бизнес-стратегиями, маркетингом, управлением. Давай практические советы, будь структурированным."
    },
    "creative": {
        "name": "🎨 Креативный специалист",
        "emoji": "🎨",
        "description": "Генерирует идеи и вдохновляет",
        "prompt": "Ты креативный специалист по имени Николай. Генерируй идеи, вдохновляй, помогай с творческими задачами. Будь нестандартным, используй яркие эмодзи."
    }
}

# ==================== Хранилище сессий ====================
@dataclass
class UserSession:
    user_id: int
    username: str
    first_name: str
    conversation_history: list = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    role: str = "default"
    custom_prompt: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        self.last_active = time.time()
        if len(self.conversation_history) > 30:
            self.conversation_history = self.conversation_history[-30:]
    
    def clear_history(self):
        self.conversation_history = []
        self.last_active = time.time()
    
    def get_system_prompt(self) -> str:
        if self.custom_prompt:
            return self.custom_prompt
        return ROLES_CONFIG.get(self.role, ROLES_CONFIG["default"])["prompt"]
    
    def get_role_name(self) -> str:
        return ROLES_CONFIG.get(self.role, ROLES_CONFIG["default"])["name"]
    
    def get_role_emoji(self) -> str:
        return ROLES_CONFIG.get(self.role, ROLES_CONFIG["default"])["emoji"]

class BotMemory:
    def __init__(self):
        self.sessions: Dict[int, UserSession] = {}
        self.api_token = None
        self.api_token_expiry = 0
    
    def get_session(self, user_id: int, username: str = "", first_name: str = "") -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(
                user_id=user_id, username=username, first_name=first_name
            )
        return self.sessions[user_id]
    
    def cleanup_old_sessions(self):
        current_time = time.time()
        inactive_ids = []
        for user_id, session in self.sessions.items():
            if current_time - session.last_active > 3600:
                inactive_ids.append(user_id)
        for user_id in inactive_ids:
            del self.sessions[user_id]
    
    def get_user_role(self, user_id: int) -> UserRole:
        if user_id in ADMIN_IDS:
            return UserRole.ADMIN
        elif user_id in MODERATOR_IDS:
            return UserRole.MODERATOR
        return UserRole.USER
    
    async def get_api_token(self) -> str:
        """Получение токена API"""
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
    
    async def ask_ai(self, messages: list) -> str:
        """Запрос к AI"""
        token = await self.get_api_token()
        if not token:
            return "❌ Ошибка авторизации. Пожалуйста, попробуйте позже."
        
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
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1500
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                        else:
                            return "❌ Неожиданный формат ответа"
                    elif response.status == 401:
                        self.api_token = None
                        return await self.ask_ai(messages)
                    else:
                        return f"❌ Ошибка API: {response.status}"
        except asyncio.TimeoutError:
            return "⏰ Превышено время ожидания. Попробуйте еще раз."
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return f"❌ Ошибка: {str(e)}"

bot_memory = BotMemory()

# ==================== КЛАВИАТУРЫ ====================
async def get_role_keyboard():
    """Клавиатура выбора роли"""
    keyboard = []
    row = []
    
    for role_key, role_config in ROLES_CONFIG.items():
        button_text = f"{role_config['emoji']} {role_config['name']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"role_{role_key}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="role_cancel")])
    return InlineKeyboardMarkup(keyboard)

async def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = [
        [
            InlineKeyboardButton("🎭 Сменить роль", callback_data="menu_role"),
            InlineKeyboardButton("🗑 Очистить историю", callback_data="menu_clear")
        ],
        [
            InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help"),
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton("👤 Моя роль", callback_data="menu_myrole")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = bot_memory.get_session(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я Николай* - твой персональный AI-помощник\n"
        f"🇷🇺 Работаю в России без VPN\n\n"
        f"🎭 *Мои возможности:*\n"
        f"• 📝 Отвечаю на любые вопросы\n"
        f"• 🎭 Могу менять роли\n"
        f"• 💬 Поддерживаю диалог\n"
        f"• 🧠 Помню контекст\n\n"
        f"📋 *Команды:*\n"
        f"• /start — показать это сообщение\n"
        f"• /menu — открыть меню\n"
        f"• /role — выбрать роль\n"
        f"• /myrole — текущая роль\n"
        f"• /clear — очистить историю\n"
        f"• /help — помощь\n"
        f"• /stats — статистика\n\n"
        f"💬 *Просто напиши мне сообщение!*\n"
        f"👇 Нажми /menu для быстрого доступа"
    )
    
    keyboard = await get_main_keyboard()
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    keyboard = await get_main_keyboard()
    await update.message.reply_text(
        "🎯 *Главное меню*\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 *Помощь*\n\n"
        "*Я Николай* - твой персональный AI-помощник\n\n"
        "✨ *Что я умею:*\n"
        "✅ Отвечаю на любые вопросы\n"
        "✅ Меняю роли (учитель, программист, врач и др.)\n"
        "✅ Поддерживаю диалог\n"
        "✅ Помню последние 30 сообщений\n\n"
        "📋 *Команды:*\n"
        "/start — главное меню\n"
        "/menu — открыть меню\n"
        "/role — выбрать роль\n"
        "/myrole — текущая роль\n"
        "/clear — очистить историю\n"
        "/help — помощь\n"
        "/stats — статистика\n\n"
        "🎭 *Доступные роли:*\n"
    )
    
    for role_key, role_config in ROLES_CONFIG.items():
        help_text += f"{role_config['emoji']} *{role_config['name']}* — {role_config['description']}\n"
    
    help_text += "\n💡 *Советы:*\n"
    help_text += "• Используйте /role для смены роли\n"
    help_text += "• Роль влияет на стиль ответов\n"
    help_text += "• Используйте /clear для новой темы\n"
    help_text += "• Нажмите /menu для быстрого доступа"
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = bot_memory.get_session(update.effective_user.id)
    session.clear_history()
    await update.message.reply_text("🧹 *История диалога очищена!* Начинаем чистый разговор.", parse_mode='Markdown')

async def role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор роли"""
    keyboard = await get_role_keyboard()
    await update.message.reply_text(
        "🎭 *Выберите роль*\n\n"
        "Роль определяет стиль и характер ответов.\n"
        "Вы можете сменить роль в любой момент.\n\n"
        "👇 *Нажмите на кнопку с нужной ролью:*",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def myrole_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущую роль"""
    session = bot_memory.get_session(update.effective_user.id)
    role_config = ROLES_CONFIG.get(session.role, ROLES_CONFIG["default"])
    
    role_text = (
        f"🎭 *Ваша текущая роль*\n\n"
        f"{role_config['emoji']} **{role_config['name']}**\n\n"
        f"📝 *Описание:* {role_config['description']}\n\n"
        f"🔄 Чтобы сменить роль, используйте команду /role"
    )
    await update.message.reply_text(role_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = bot_memory.get_session(user.id)
    user_role = bot_memory.get_user_role(user.id)
    role_config = ROLES_CONFIG.get(session.role, ROLES_CONFIG["default"])
    
    stats_text = (
        "📊 *Ваша статистика*\n\n"
        f"👤 *Имя:* {session.first_name}\n"
        f"🆔 *ID:* `{session.user_id}`\n"
        f"👑 *Статус:* {user_role.value.upper()}\n"
        f"🎭 *Роль:* {role_config['emoji']} {role_config['name']}\n"
        f"💬 *История:* {len(session.conversation_history)} сообщений\n"
        f"🕐 *Активность:* {time.strftime('%H:%M:%S', time.localtime(session.last_active))}\n"
        f"✨ *Активных пользователей:* {len(bot_memory.sessions)}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback от главного меню"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "menu_role":
        keyboard = await get_role_keyboard()
        await query.edit_message_text(
            "🎭 *Выберите роль*\n\nРоль определяет стиль ответов:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    elif callback_data == "menu_clear":
        session = bot_memory.get_session(query.from_user.id)
        session.clear_history()
        await query.edit_message_text("🧹 *История диалога очищена!*", parse_mode='Markdown')
    
    elif callback_data == "menu_help":
        help_text = (
            "🤖 *Помощь*\n\n"
            "*Я Николай* - твой AI-помощник\n\n"
            "📝 *Команды:*\n"
            "/start — главное меню\n"
            "/menu — открыть меню\n"
            "/role — выбрать роль\n"
            "/myrole — текущая роль\n"
            "/clear — очистить историю\n"
            "/help — помощь\n\n"
            "💬 Просто напиши сообщение, и я отвечу!"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif callback_data == "menu_stats":
        user = query.from_user
        session = bot_memory.get_session(user.id)
        role_config = ROLES_CONFIG.get(session.role, ROLES_CONFIG["default"])
        
        stats_text = (
            f"📊 *Статистика*\n\n"
            f"👤 *Имя:* {session.first_name}\n"
            f"🎭 *Роль:* {role_config['emoji']} {role_config['name']}\n"
            f"💬 *Сообщений:* {len(session.conversation_history)}\n"
            f"🕐 *Активность:* {time.strftime('%H:%M:%S')}\n"
            f"✨ *Пользователей:* {len(bot_memory.sessions)}"
        )
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    elif callback_data == "menu_myrole":
        session = bot_memory.get_session(query.from_user.id)
        role_config = ROLES_CONFIG.get(session.role, ROLES_CONFIG["default"])
        
        role_text = (
            f"🎭 *Ваша роль*\n\n"
            f"{role_config['emoji']} **{role_config['name']}**\n"
            f"📝 {role_config['description']}"
        )
        await query.edit_message_text(role_text, parse_mode='Markdown')

async def handle_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора роли"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "role_cancel":
        await query.edit_message_text("❌ *Выбор роли отменен*", parse_mode='Markdown')
        return
    
    if callback_data.startswith("role_"):
        role_key = callback_data.replace("role_", "")
        if role_key in ROLES_CONFIG:
            session = bot_memory.get_session(query.from_user.id)
            session.role = role_key
            session.custom_prompt = None
            
            role_config = ROLES_CONFIG[role_key]
            
            success_text = (
                f"✅ *Роль успешно изменена!*\n\n"
                f"{role_config['emoji']} **{role_config['name']}**\n\n"
                f"📝 *Описание:* {role_config['description']}\n\n"
                f"💬 Теперь я буду отвечать в этом стиле.\n"
                f"🔄 Используйте /role для смены роли"
            )
            await query.edit_message_text(success_text, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ *Неизвестная роль*", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    user_message = update.message.text
    
    await update.message.chat.send_action(action="typing")
    
    try:
        session = bot_memory.get_session(user.id, user.username or "", user.first_name or "")
        session.add_message("user", user_message)
        
        messages = [{"role": "system", "content": session.get_system_prompt()}]
        messages.extend(session.conversation_history)
        
        response = await bot_memory.ask_ai(messages)
        
        session.add_message("assistant", response)
        
        if len(response) > 4096:
            parts = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ *Произошла ошибка. Попробуйте позже.*", parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ *Произошла ошибка. Попробуйте позже.*",
            parse_mode='Markdown'
        )

async def cleanup_task():
    while True:
        await asyncio.sleep(1800)
        bot_memory.cleanup_old_sessions()

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("role", role_command))
    application.add_handler(CommandHandler("myrole", myrole_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(handle_role_callback, pattern="^role_"))
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(cleanup_task())
    
    logger.info("🚀 Бот Николай запущен")
    logger.info("🎭 Доступно 10 ролей с эмодзи")
    logger.info("💬 Все сообщения от имени Николая")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
