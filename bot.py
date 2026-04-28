import asyncio
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    JobQueue
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  joined_date TIMESTAMP,
                  last_active TIMESTAMP)''')
    
    # Таблица каналов
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  channel_title TEXT,
                  channel_username TEXT,
                  added_date TIMESTAMP,
                  status TEXT DEFAULT 'active')''')
    
    # Таблица подписок
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY,
                  tariff TEXT DEFAULT 'free',
                  start_date TIMESTAMP,
                  end_date TIMESTAMP,
                  max_channels INTEGER DEFAULT 2)''')
    
    # Таблица источников для репостов
    c.execute('''CREATE TABLE IF NOT EXISTS sources
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  source_channel_id TEXT,
                  source_channel_title TEXT,
                  target_channel_id TEXT,
                  last_post_id INTEGER DEFAULT 0,
                  is_active INTEGER DEFAULT 1,
                  added_date TIMESTAMP)''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  content TEXT,
                  post_type TEXT,
                  posted_time TIMESTAMP)''')
    
    # Таблица настроек автопостинга
    c.execute('''CREATE TABLE IF NOT EXISTS auto_posting
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  channel_title TEXT,
                  topic TEXT,
                  is_active INTEGER DEFAULT 0,
                  interval_minutes INTEGER DEFAULT 60,
                  last_post_time TIMESTAMP,
                  keywords TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ТЕМЫ ДЛЯ КОНТЕНТА ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии",
        "posts": [
            "🔬 *Новый прорыв в ИИ!* Сегодня нейросети могут генерировать видео по текстовому описанию. Технологии развиваются с невероятной скоростью! А вы следите за новинками? #технологии #ai",
            "📱 *Топ-5 полезных приложений 2024*\n\n1. Приложение для заметок с ИИ\n2. Менеджер паролей нового поколения\n3. Фитнес-трекер с анализом сна\n4. Редактор фото на нейросетях\n5. Органайзер задач\n\nКакие приложения используете вы?",
            "💡 *Лайфхак для программистов*\n\nИспользуйте GitHub Copilot - ИИ-помощник пишет код за вас! Экономит до 50% времени разработки. Кто уже пробовал?",
            "🚀 *Будущее уже здесь* \n\nДроны-доставщики, роботы-помощники, умные дома - это не фантастика, а реальность 2024 года. Что из этого уже есть у вас?",
            "🎮 *Игровые новости*\n\nВышло обновление с трассировкой лучей для популярных игр. Графика стала еще реалистичнее! Какие игры проходите сейчас?"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "posts": [
            "💼 *5 советов для начинающих предпринимателей*\n\n1. Изучите рынок\n2. Составьте бизнес-план\n3. Найдите первых клиентов\n4. Автоматизируйте процессы\n5. Не бойтесь ошибок\n\nВаш первый бизнес - какой он?",
            "📈 *Тренды 2024 в бизнесе*\n\n• Искусственный интеллект\n• Удаленная работа\n• Экологичность\n• Персонализация\n• Маркетплейсы\n\nЧто из этого актуально для вас?",
            "💰 *Как привлечь инвестиции*\n\n• Подготовьте качественную презентацию\n• Покажите финансовую модель\n• Расскажите о команде\n• Продемонстрируйте первые продажи\n\nГотовы к инвестициям?",
            "📊 *Ключевые метрики бизнеса*\n\n✔️ CAC - стоимость привлечения клиента\n✔️ LTV - пожизненная ценность клиента\n✔️ ROI - возврат инвестиций\n✔️ Churn rate - отток клиентов\n\nКакие метрики отслеживаете?",
            "🎯 *Маркетинг 2024*\n\nКонтент-маркетинг, TikTok, нейросети, чат-боты - вот главные тренды продвижения. Что работает лучше всего для вас?"
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "posts": [
            "🥗 *Правильное питание: 5 простых правил*\n\n1. Пейте воду (30 мл на 1 кг веса)\n2. Ешьте больше овощей\n3. Не пропускайте завтрак\n4. Уменьшите сахар\n5. Считайте калории\n\nСоблюдаете эти правила?",
            "🏃‍♂️ *Утренняя зарядка - 5 минут здоровья*\n\n• Наклоны головы - 10 раз\n• Вращения плечами - 10 раз\n• Наклоны корпуса - 10 раз\n• Приседания - 15 раз\n• Прыжки - 20 раз\n\nДелаете зарядку по утрам?",
            "😴 *Как улучшить качество сна*\n\n• Ложитесь до 23:00\n• Не ешьте за 2 часа до сна\n• Проветрите комнату\n• Уберите гаджеты\n• Медитируйте перед сном\n\nСколько часов спите вы?",
            "🧘 *Польза медитации*\n\n10 минут медитации в день:\n• Снижают стресс\n• Улучшают концентрацию\n• Повышают иммунитет\n• Нормализуют давление\n\nПрактикуете медитацию?",
            "💪 *Спорт для всех*\n\nДаже 30 минут ходьбы в день снижают риск болезней сердца на 30%! Какой спорт предпочитаете?"
        ]
    },
    "motivation": {
        "name": "💪 Мотивация",
        "posts": [
            "🌟 *Успех не приходит мгновенно*\n\nКаждый большой успех начинается с маленького шага. Не бойтесь начинать, не бойтесь ошибаться. Главное - не останавливаться!\n\nКакой ваш первый шаг к успеху?",
            "🎯 *Правило 5 секунд*\n\nЕсли у вас есть идея, которую нужно реализовать - сделайте это в течение 5 секунд. Не дайте страху и сомнениям остановить вас!\n\nКакую идею вы откладываете?",
            "📚 *Читайте каждый день*\n\nУспешные люди много читают. Книги - это знания, опыт, вдохновение. Начните с 10 страниц в день - это 3650 страниц в год!\n\nКакую книгу читаете сейчас?",
            "🚀 *Ваше время ограничено*\n\nНе тратьте его на сожаления и страхи. Действуйте здесь и сейчас. Мечты не работают, пока не работаете вы!\n\nЧто вы сделали сегодня?",
            "💫 *Каждый эксперт был новичком*\n\nНикто не рождается профессионалом. Ошибки - это опыт. Падения - это рост. Продолжайте идти вперед!\n\nВ чем вы хотите стать экспертом?"
        ]
    },
    "lifehacks": {
        "name": "🎯 Лайфхаки",
        "posts": [
            "✨ *Организация пространства*\n\n• Храните вещи вертикально\n• Используйте прозрачные контейнеры\n• Избавляйтесь от ненужного\n• Маркируйте все коробки\n\nКак вы организуете дом?",
            "⏰ *Тайм-менеджмент*\n\n• Планируйте день с вечера\n• Делайте самое сложное первым\n• Используйте таймер Pomodoro\n• Делегируйте задачи\n\nКак вы управляете временем?",
            "💰 *Экономия бюджета*\n\n• Ведите учет расходов\n• Используйте кэшбэк\n• Покупайте оптом\n• Откажитесь от ненужных подписок\n\nНа чем вы экономите?",
            "📱 *Полезные приложения*\n\n• Todoist - планирование\n• Notion - заметки\n• Forest - концентрация\n• Headspace - медитация\n\nКакие приложения в фаворитах?",
            "🍳 *Быстрые рецепты*\n\nЗавтрак за 5 минут: овсянка с бананом и медом. Просто, вкусно, полезно! Какой ваш любимый быстрый завтрак?"
        ]
    }
}

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 2,
        "features": ["✅ 2 канала", "✅ Ручной постинг", "✅ 2 темы для автопостинга"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 10,
        "features": ["✅ 10 каналов", "✅ Автопостинг", "✅ Все темы", "✅ Репосты", "✅ Приоритет"]
    }
}

# ==================== КЛАВИАТУРЫ ====================
async def main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting_menu")],
        [InlineKeyboardButton("🔄 Репосты", callback_data="repost_menu")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def channels_keyboard(user_id: int):
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status = 'active'", (user_id,))
    channels = c.fetchall()
    conn.close()
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"channel_{channel_id}")])
    
    if not channels:
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def auto_posting_keyboard(user_id: int):
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status = 'active'", (user_id,))
    channels = c.fetchall()
    
    keyboard = []
    for channel_id, title in channels:
        c.execute("SELECT is_active, topic FROM auto_posting WHERE channel_id = ?", (channel_id,))
        setting = c.fetchone()
        status = "✅" if setting and setting[0] else "❌"
        topic_name = ""
        if setting and setting[1] and setting[1] in TOPICS:
            topic_name = f" - {TOPICS[setting[1]]['name']}"
        keyboard.append([InlineKeyboardButton(f"{status} {title}{topic_name}", callback_data=f"auto_{channel_id}")])
    
    conn.close()
    
    if not channels:
        keyboard = [[InlineKeyboardButton("❌ Нет каналов", callback_data="noop")]]
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def topic_keyboard(channel_id: str):
    keyboard = []
    for topic_key, topic_info in TOPICS.items():
        keyboard.append([InlineKeyboardButton(topic_info["name"], callback_data=f"topic_{channel_id}_{topic_key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting_menu")])
    return InlineKeyboardMarkup(keyboard)

async def interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("⏱ 30 минут", callback_data=f"interval_{channel_id}_30")],
        [InlineKeyboardButton("⏱ 1 час", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("⏱ 2 часа", callback_data=f"interval_{channel_id}_120")],
        [InlineKeyboardButton("⏱ 4 часа", callback_data=f"interval_{channel_id}_240")],
        [InlineKeyboardButton("⏱ 6 часов", callback_data=f"interval_{channel_id}_360")],
        [InlineKeyboardButton("⏱ 12 часов", callback_data=f"interval_{channel_id}_720")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ФУНКЦИИ АВТОПОСТИНГА ====================
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для автопостинга"""
    job_data = context.job.data
    channel_id = job_data['channel_id']
    user_id = job_data['user_id']
    topic = job_data['topic']
    
    try:
        # Получаем посты по теме
        posts = TOPICS.get(topic, {}).get('posts', [])
        if not posts:
            return
        
        # Выбираем случайный пост
        post = random.choice(posts)
        
        # Отправляем пост
        await context.bot.send_message(chat_id=channel_id, text=post, parse_mode='Markdown')
        
        # Обновляем время последнего поста
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("UPDATE auto_posting SET last_post_time = ? WHERE channel_id = ?", 
                  (datetime.now(), channel_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Автопостинг отправлен в канал {channel_id} на тему {topic}")
        
    except Exception as e:
        logger.error(f"Ошибка автопостинга: {e}")

def schedule_auto_posting(application: Application, user_id: int, channel_id: str, interval_minutes: int, topic: str):
    """Запланировать автопостинг"""
    job_name = f"auto_post_{user_id}_{channel_id}"
    
    # Удаляем старую задачу если есть
    current_jobs = application.job_queue.jobs()
    for job in current_jobs:
        if job.name == job_name:
            job.schedule_removal()
    
    # Создаем новую задачу
    application.job_queue.run_repeating(
        auto_post_job,
        interval=interval_minutes * 60,
        first=10,  # Первый пост через 10 секунд
        data={'channel_id': channel_id, 'user_id': user_id, 'topic': topic},
        name=job_name
    )

def stop_auto_posting(application: Application, user_id: int, channel_id: str):
    """Остановить автопостинг"""
    job_name = f"auto_post_{user_id}_{channel_id}"
    current_jobs = application.job_queue.jobs()
    for job in current_jobs:
        if job.name == job_name:
            job.schedule_removal()
            return True
    return False

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
              (user.id, user.username or "", user.first_name or "", datetime.now(), datetime.now()))
    c.execute("INSERT OR IGNORE INTO subscriptions (user_id, tariff, start_date, max_channels) VALUES (?, 'free', ?, 2)",
              (user.id, datetime.now()))
    conn.commit()
    conn.close()
    
    text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Бот для автоматического постинга*\n\n"
        f"📋 *Что я умею:*\n"
        f"• 📝 Писать посты вручную\n"
        f"• ⚙️ Автоматический постинг по темам\n"
        f"• 🔄 Репосты из других каналов\n"
        f"• 📊 Статистика\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Введите /add_channel или нажмите 'Мои каналы'\n"
        f"3️⃣ Настройте автопостинг\n\n"
        f"💡 *Все функции бесплатны!*"
    )
    
    keyboard = await main_keyboard(user.id)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Добавление канала*\n\n"
        "1. Добавьте бота в канал как администратора\n"
        "2. Отправьте ссылку на канал:\n"
        "• `@username`\n"
        "• `https://t.me/username`\n\n"
        "Отправьте ссылку:",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    # Извлекаем ID
    if "t.me/" in channel_input:
        username = channel_input.split("t.me/")[-1]
        if "/" in username:
            username = username.split("/")[0]
        channel_id = f"@{username}"
    else:
        channel_id = channel_input if channel_input.startswith("@") else f"@{channel_input}"
    
    # Проверяем лимит
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    tariff = sub[0] if sub else "free"
    max_channels = TARIFFS[tariff]["max_channels"]
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    count = c.fetchone()[0]
    
    if count >= max_channels:
        await update.message.reply_text(f"❌ Лимит каналов: {max_channels}. Перейдите на PRO тариф для увеличения.")
        conn.close()
        return
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        c.execute("INSERT INTO channels (user_id, channel_id, channel_title, channel_username, added_date) VALUES (?, ?, ?, ?, ?)",
                  (user.id, str(chat.id), chat.title, channel_input, datetime.now()))
        conn.commit()
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n📢 {chat.title}\n🆔 {chat.id}\n\nТеперь настройте автопостинг в меню!",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\n\nУбедитесь что бот добавлен в канал как администратор!")
    finally:
        conn.close()
        context.user_data['adding_channel'] = False

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (query.from_user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text("❌ Нет каналов. Сначала добавьте канал!", parse_mode='Markdown')
        return
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"post_to_{channel_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text("📝 Выберите канал:", reply_markup=InlineKeyboardMarkup(keyboard))

async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['post_channel'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите пост*\n\n"
        "Отправьте текст, фото или видео\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        return
    
    text = update.message.text or update.message.caption or ""
    
    try:
        if update.message.photo:
            photo = update.message.photo[-1].file_id
            await context.bot.send_photo(chat_id=channel_id, photo=photo, caption=text)
        elif update.message.video:
            video = update.message.video.file_id
            await context.bot.send_video(chat_id=channel_id, video=video, caption=text)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text)
        
        # Сохраняем в БД
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, channel_id, content, post_type, posted_time) VALUES (?, ?, ?, ?, ?)",
                  (user.id, channel_id, text, "manual", datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Пост опубликован!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data['post_channel'] = None
    
    # Показываем меню
    keyboard = await main_keyboard(user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await auto_posting_keyboard(query.from_user.id)
    await query.edit_message_text("⚙️ *Автопостинг*\n\nВыберите канал:", parse_mode='Markdown', reply_markup=keyboard)

async def auto_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_", "")
    context.user_data['auto_channel'] = channel_id
    
    # Получаем настройки
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT is_active, topic, interval_minutes FROM auto_posting WHERE channel_id = ?", (channel_id,))
    setting = c.fetchone()
    conn.close()
    
    is_active = setting[0] if setting else 0
    topic = setting[1] if setting and setting[1] else "Не выбрана"
    interval = setting[2] if setting else 60
    
    topic_name = TOPICS.get(topic, {}).get("name", "Не выбрана")
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {'✅ Включен' if is_active else '❌ Выключен'}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval} мин\n\n"
        f"Что хотите изменить?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"toggle_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"topic_menu_{channel_id}")],
        [InlineKeyboardButton("⏱ Изменить интервал", callback_data=f"interval_menu_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting_menu")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_", "")
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Проверяем есть ли настройки
    c.execute("SELECT * FROM auto_posting WHERE channel_id = ?", (channel_id,))
    exists = c.fetchone()
    
    if exists:
        c.execute("SELECT is_active FROM auto_posting WHERE channel_id = ?", (channel_id,))
        current = c.fetchone()[0]
        new_status = 0 if current else 1
        
        if new_status == 1:
            # Проверяем выбрана ли тема
            c.execute("SELECT topic FROM auto_posting WHERE channel_id = ?", (channel_id,))
            topic = c.fetchone()[0]
            if not topic:
                await query.edit_message_text(
                    "❌ *Сначала выберите тему!*\n\n"
                    "Нажмите 'Выбрать тему' и выберите тему для постов",
                    parse_mode='Markdown'
                )
                conn.close()
                return
            
            c.execute("UPDATE auto_posting SET is_active = ?, last_post_time = ? WHERE channel_id = ?",
                      (new_status, datetime.now(), channel_id))
            
            # Запускаем автопостинг
            c.execute("SELECT topic, interval_minutes FROM auto_posting WHERE channel_id = ?", (channel_id,))
            topic, interval = c.fetchone()
            schedule_auto_posting(context.application, user_id, channel_id, interval, topic)
            
        else:
            c.execute("UPDATE auto_posting SET is_active = ? WHERE channel_id = ?", (new_status, channel_id))
            stop_auto_posting(context.application, user_id, channel_id)
    else:
        # Создаем настройки
        c.execute("INSERT INTO auto_posting (user_id, channel_id, is_active) VALUES (?, ?, 1)", (user_id, channel_id))
        await query.edit_message_text(
            "❌ *Сначала выберите тему!*\n\n"
            "Нажмите 'Выбрать тему' и выберите тему для постов",
            parse_mode='Markdown'
        )
        conn.commit()
        conn.close()
        return
    
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ Автопостинг {'включен' if new_status else 'выключен'}!")
    await asyncio.sleep(1)
    await auto_settings(update, context)

async def topic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("topic_menu_", "")
    keyboard = await topic_keyboard(channel_id)
    await query.edit_message_text("📝 *Выберите тему для автопостинга:*", parse_mode='Markdown', reply_markup=keyboard)

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    topic_key = parts[2]
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    # Обновляем тему
    c.execute("SELECT * FROM auto_posting WHERE channel_id = ?", (channel_id,))
    exists = c.fetchone()
    
    if exists:
        c.execute("UPDATE auto_posting SET topic = ? WHERE channel_id = ?", (topic_key, channel_id))
        # Если автопостинг был активен, перезапускаем
        c.execute("SELECT is_active, interval_minutes FROM auto_posting WHERE channel_id = ?", (channel_id,))
        is_active, interval = c.fetchone()
        if is_active:
            schedule_auto_posting(context.application, user_id, channel_id, interval, topic_key)
    else:
        c.execute("INSERT INTO auto_posting (user_id, channel_id, topic, is_active) VALUES (?, ?, ?, 0)",
                  (user_id, channel_id, topic_key))
    
    conn.commit()
    conn.close()
    
    topic_name = TOPICS[topic_key]["name"]
    await query.edit_message_text(f"✅ Тема установлена: {topic_name}!")
    await asyncio.sleep(1)
    await auto_settings(update, context)

async def interval_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("interval_menu_", "")
    keyboard = await interval_keyboard(channel_id)
    await query.edit_message_text("⏱ *Выберите интервал постинга:*", parse_mode='Markdown', reply_markup=keyboard)

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM auto_posting WHERE channel_id = ?", (channel_id,))
    exists = c.fetchone()
    
    if exists:
        c.execute("UPDATE auto_posting SET interval_minutes = ? WHERE channel_id = ?", (interval, channel_id))
        # Перезапускаем если активен
        c.execute("SELECT is_active, topic FROM auto_posting WHERE channel_id = ?", (channel_id,))
        is_active, topic = c.fetchone()
        if is_active and topic:
            schedule_auto_posting(context.application, user_id, channel_id, interval, topic)
    else:
        c.execute("INSERT INTO auto_posting (user_id, channel_id, interval_minutes) VALUES (?, ?, ?)",
                  (user_id, channel_id, interval))
    
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ Интервал установлен: {interval} минут!")
    await asyncio.sleep(1)
    await auto_settings(update, context)

async def my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await channels_keyboard(query.from_user.id)
    await query.edit_message_text("📢 *Ваши каналы*", parse_mode='Markdown', reply_markup=keyboard)

async def repost_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔄 Настроить репосты", callback_data="setup_repost")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    await query.edit_message_text("🔄 *Репосты*\n\nФункция в разработке", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user_id,))
    current = c.fetchone()
    current_tariff = current[0] if current else "free"
    conn.close()
    
    text = "💎 *Тарифы*\n\n"
    for key, tariff in TARIFFS.items():
        marker = "✅ " if key == current_tariff else "📌 "
        text += f"{marker}*{tariff['name']}*\n"
        for feature in tariff['features']:
            text += f"  {feature}\n"
        text += "\n"
    
    text += "🎁 *Все тарифы бесплатны!*\n"
    text += "PRO тариф доступен по запросу @admin"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    tariff = c.fetchone()
    tariff_name = TARIFFS.get(tariff[0] if tariff else "free", {}).get("name", "Бесплатный")
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user.id,))
    posts_count = c.fetchone()[0]
    
    conn.close()
    
    text = (
        f"👤 *Профиль*\n\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Имя: {user.first_name}\n"
        f"💎 Тариф: {tariff_name}\n"
        f"📢 Каналов: {channels_count}\n"
        f"📝 Постов: {posts_count}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND DATE(posted_time) = ?", (user_id, today))
    today_posts = c.fetchone()[0]
    
    week_ago = datetime.now() - timedelta(days=7)
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND posted_time >= ?", (user_id, week_ago))
    week_posts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM auto_posting WHERE user_id = ? AND is_active = 1", (user_id,))
    active_auto = c.fetchone()[0]
    
    conn.close()
    
    text = (
        f"📊 *Статистика*\n\n"
        f"📝 Постов сегодня: {today_posts}\n"
        f"📊 Постов за неделю: {week_posts}\n"
        f"⚙️ Активных автопостингов: {active_auto}\n\n"
        f"💡 Продолжайте в том же духе!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "ℹ️ *Помощь*\n\n"
        "📌 *Команды:*\n"
        "/start - Главное меню\n"
        "/add_channel - Добавить канал\n"
        "/cancel - Отменить действие\n\n"
        "📌 *Как настроить автопостинг:*\n"
        "1. Добавьте бота в канал\n"
        "2. Нажмите 'Автопостинг'\n"
        "3. Выберите канал\n"
        "4. Выберите тему\n"
        "5. Включите автопостинг\n\n"
        "📌 *Как публиковать вручную:*\n"
        "1. Нажмите 'Написать пост'\n"
        "2. Выберите канал\n"
        "3. Отправьте сообщение\n\n"
        "❓ Вопросы: @SupportBot"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено")
    
    keyboard = await main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def restart_auto_jobs(application: Application):
    """Перезапуск всех автопостингов после перезагрузки"""
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, channel_id, topic, interval_minutes FROM auto_posting WHERE is_active = 1 AND topic IS NOT NULL")
    active_posts = c.fetchall()
    conn.close()
    
    for user_id, channel_id, topic, interval in active_posts:
        if topic and topic in TOPICS:
            schedule_auto_posting(application, user_id, channel_id, interval, topic)
            logger.info(f"Восстановлен автопостинг для канала {channel_id} - тема {topic}")

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_channel", add_channel_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel') 
        else (handle_post(u, c) if c.user_data.get('post_channel') else None)
    ))
    
    # Обработчики медиа
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        handle_post
    ))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(write_post, pattern="^write_post$"))
    application.add_handler(CallbackQueryHandler(my_channels, pattern="^my_channels$"))
    application.add_handler(CallbackQueryHandler(auto_posting_menu, pattern="^auto_posting_menu$"))
    application.add_handler(CallbackQueryHandler(repost_menu, pattern="^repost_menu$"))
    application.add_handler(CallbackQueryHandler(show_tariffs, pattern="^tariffs$"))
    application.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(post_to_channel, pattern="^post_to_"))
    application.add_handler(CallbackQueryHandler(auto_settings, pattern="^auto_"))
    application.add_handler(CallbackQueryHandler(toggle_auto, pattern="^toggle_"))
    application.add_handler(CallbackQueryHandler(topic_menu, pattern="^topic_menu_"))
    application.add_handler(CallbackQueryHandler(set_topic, pattern="^topic_"))
    application.add_handler(CallbackQueryHandler(interval_menu, pattern="^interval_menu_"))
    application.add_handler(CallbackQueryHandler(set_interval, pattern="^interval_"))
    
    # Запускаем восстановление автопостингов
    application.post_init = restart_auto_jobs
    
    logger.info("🚀 Бот запущен!")
    logger.info("✅ Автопостинг работает через JobQueue")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
