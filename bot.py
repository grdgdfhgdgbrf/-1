import asyncio
import logging
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
    filters
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
    
    # Таблица тарифов
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY,
                  tariff TEXT DEFAULT 'free',
                  start_date TIMESTAMP,
                  max_channels INTEGER DEFAULT 2)''')
    
    # Таблица настроек автопостинга
    c.execute('''CREATE TABLE IF NOT EXISTS auto_posting
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  is_active INTEGER DEFAULT 0,
                  topic TEXT,
                  interval_minutes INTEGER DEFAULT 60,
                  last_post_time TIMESTAMP,
                  next_post_time TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  channel_id TEXT,
                  content TEXT,
                  post_type TEXT,
                  posted_time TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 2,
        "min_interval": 5,
        "features": ["✅ 2 канала", "✅ Интервал от 5 минут", "✅ 5 тем"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 5,
        "min_interval": 2,
        "features": ["✅ 5 каналов", "✅ Интервал от 2 минут", "✅ 10 тем"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 15,
        "min_interval": 1,
        "features": ["✅ 15 каналов", "✅ Интервал от 1 минуты", "✅ Все темы"]
    }
}

# ==================== ТЕМЫ ДЛЯ ПОСТОВ ====================
POSTS_TEMPLATES = {
    "technology": {
        "name": "💻 Технологии",
        "posts": [
            "🔬 *Новая эра технологий*\n\nИскусственный интеллект меняет наш мир каждый день. Что ждет нас через 5 лет?\n\n#технологии #ai #будущее",
            "📱 *Топ гаджетов этого месяца*\n\nСобрали для вас лучшие новинки рынка. Какой gadget хотите себе?\n\n#гаджеты #обзор #техника",
            "💡 *IT-лайфхак*\n\nКак ускорить работу компьютера за 5 минут? Делимся простыми советами!\n\n#лайфхак #it #советы",
            "🚀 *Инновации в космосе*\n\nЧастные компании осваивают космос быстрее государств. Подробности в посте\n\n#космос #spacex #инновации",
            "⚡ *Будущее уже здесь*\n\n5 технологий, которые изменят нашу жизнь в ближайшие годы\n\n#технологии #будущее #тренды"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "posts": [
            "💼 *Как начать свой бизнес с нуля*\n\nПошаговый план для начинающих предпринимателей\n\n#бизнес #стартап #советы",
            "📈 *Тренды 2024 в бизнесе*\n\nКакие ниши будут самыми прибыльными в этом году?\n\n#бизнес #тренды #прибыль",
            "💰 *Финансовая грамотность*\n\nКак управлять деньгами и приумножить капитал\n\n#финансы #деньги #инвестиции",
            "🎯 *Маркетинг без бюджета*\n\nКак продвигать бизнес бесплатно и эффективно\n\n#маркетинг #продвижение #бизнес",
            "🤝 *Как найти первых клиентов*\n\nПрактические советы для старта\n\n#клиенты #продажи #бизнес"
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "posts": [
            "🏃‍♂️ *Утренняя зарядка: 5 минут для здоровья*\n\nПростые упражнения для бодрости на весь день\n\n#здоровье #спорт #утро",
            "🥗 *Правильное питание: с чего начать?\n\nОсновы здорового рациона для каждого\n\n#питание #зож #здоровье",
            "😴 *Как наладить сон за 3 дня*\n\nСоветы сомнологов для крепкого сна\n\n#сон #здоровье #советы",
            "🧘‍♀️ *Медитация для начинающих*\n\nКак справиться со стрессом за 10 минут\n\n#медитация #стресс #релакс",
            "💪 *Домашние тренировки*\n\nЭффективные упражнения без тренажеров\n\n#фитнес #тренировка #спорт"
        ]
    },
    "education": {
        "name": "📚 Образование",
        "posts": [
            "🎓 *Как учиться эффективнее*\n\nМетодики быстрого запоминания информации\n\n#обучение #память #советы",
            "📖 *Топ книг для саморазвития*\n\nЧто прочитать, чтобы стать лучше\n\n#книги #саморазвитие #чтение",
            "🌍 *Изучение языков: лайфхаки*\n\nКак выучить иностранный язык за 3 месяца\n\n#языки #обучение #советы",
            "💡 *Развитие памяти*\n\nУпражнения для улучшения работы мозга\n\n#память #мозг #развитие",
            "🎯 *Постановка целей и их достижение*\n\nSMART-система для успеха\n\n#цели #успех #мотивация"
        ]
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "posts": [
            "🎬 *Топ фильмов этого года*\n\nЧто посмотреть вечером: наша подборка\n\n#кино #фильмы #топ",
            "🎮 *Новинки видеоигр*\n\nВо что поиграть на выходных\n\n#игры #гейминг #новинки",
            "😂 *Смешные истории из жизни*\n\nПоднимите себе настроение\n\n#юмор #жизнь #смех",
            "🎵 *Музыкальный чарт недели*\n\nСамые популярные треки прямо сейчас\n\n#музыка #хиты #плейлист",
            "📺 *Что посмотреть на Netflix*\n\nЛучшие сериалы для вечернего просмотра\n\n#netflix #сериалы #тв"
        ]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "posts": [
            "🏠 *Как сделать дом уютным*\n\nИдеи для интерьера своими руками\n\n#дом #уют #интерьер",
            "🎨 *Хобби, которые меняют жизнь*\n\nНайдите дело по душе\n\n#хобби #творчество #жизнь",
            "✈️ *Путешествия: куда поехать*\n\nНаправления для отдыха в этом сезоне\n\n#путешествия #отдых #туры",
            "📸 *Фотография для начинающих*\n\nКак делать красивые фото на телефон\n\n#фото #советы #искусство",
            "💭 *Мотивация на каждый день*\n\nЦитаты для вдохновения\n\n#мотивация #вдохновение #цитаты"
        ]
    },
    "news": {
        "name": "📰 Новости",
        "posts": [
            "🌐 *Главные события дня*\n\nСамые важные новости, которые нужно знать\n\n#новости #события #день",
            "📊 *Экономический дайджест*\n\nЧто происходит на финансовых рынках\n\n#экономика #финансы #рынок",
            "🚀 *Научные открытия*\n\nПрорывы, о которых говорят ученые\n\n#наука #открытия #технологии",
            "🎉 *Праздники и события*\n\nЧто отмечают в этом месяце\n\n#праздники #события #календарь",
            "💡 *Полезные новости*\n\nИзменения в законах и правилах\n\n#законы #права #новости"
        ]
    }
}

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting_menu")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_intervals_keyboard(channel_id: str):
    """Клавиатура выбора интервала"""
    keyboard = [
        [InlineKeyboardButton("1 минута 🔥", callback_data=f"interval_{channel_id}_1")],
        [InlineKeyboardButton("5 минут", callback_data=f"interval_{channel_id}_5")],
        [InlineKeyboardButton("10 минут", callback_data=f"interval_{channel_id}_10")],
        [InlineKeyboardButton("30 минут", callback_data=f"interval_{channel_id}_30")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("2 часа", callback_data=f"interval_{channel_id}_120")],
        [InlineKeyboardButton("4 часа", callback_data=f"interval_{channel_id}_240")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_auto_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_auto_keyboard(channel_id: str, is_active: int, interval: int, topic: str):
    """Клавиатура управления автопостингом"""
    status = "✅ ВКЛЮЧЕН" if is_active else "❌ ВЫКЛЮЧЕН"
    topic_name = POSTS_TEMPLATES.get(topic, {}).get("name", "Не выбрана") if topic else "Не выбрана"
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 Статус: {status}", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton(f"📝 Тема: {topic_name}", callback_data=f"change_topic_{channel_id}")],
        [InlineKeyboardButton(f"⏱ Интервал: {interval} мин", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str):
    """Клавиатура выбора темы"""
    keyboard = []
    for topic_key, topic_data in POSTS_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(topic_data["name"], callback_data=f"set_topic_{channel_id}_{topic_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_auto_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_loop(application: Application):
    """Фоновый процесс автопостинга"""
    while True:
        try:
            conn = sqlite3.connect('posting_bot.db')
            c = conn.cursor()
            
            # Получаем активные автопостинги
            c.execute("""SELECT user_id, channel_id, topic, interval_minutes, last_post_time 
                        FROM auto_posting 
                        WHERE is_active = 1""")
            auto_posts = c.fetchall()
            conn.close()
            
            for user_id, channel_id, topic, interval_min, last_post_time_str in auto_posts:
                try:
                    # Проверяем время следующего поста
                    last_post = datetime.fromisoformat(last_post_time_str) if last_post_time_str else datetime.now() - timedelta(days=1)
                    next_post_time = last_post + timedelta(minutes=interval_min)
                    
                    if datetime.now() >= next_post_time:
                        # Выбираем случайный пост из темы
                        posts_list = POSTS_TEMPLATES.get(topic, {}).get("posts", [])
                        if posts_list:
                            post_content = random.choice(posts_list)
                            
                            # Отправляем пост
                            await application.bot.send_message(chat_id=channel_id, text=post_content, parse_mode='Markdown')
                            
                            # Сохраняем пост в историю
                            conn2 = sqlite3.connect('posting_bot.db')
                            c2 = conn2.cursor()
                            c2.execute("""INSERT INTO posts (user_id, channel_id, content, post_type, posted_time) 
                                         VALUES (?, ?, ?, ?, ?)""",
                                      (user_id, channel_id, post_content, "auto", datetime.now()))
                            c2.execute("""UPDATE auto_posting 
                                         SET last_post_time = ?, next_post_time = ? 
                                         WHERE channel_id = ? AND user_id = ?""",
                                      (datetime.now().isoformat(), 
                                       (datetime.now() + timedelta(minutes=interval_min)).isoformat(),
                                       channel_id, user_id))
                            conn2.commit()
                            conn2.close()
                            
                            logger.info(f"Автопост отправлен в канал {channel_id}")
                except Exception as e:
                    logger.error(f"Ошибка автопостинга для {channel_id}: {e}")
            
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
        except Exception as e:
            logger.error(f"Ошибка в цикле автопостинга: {e}")
            await asyncio.sleep(60)

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
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• 🤖 Автоматический постинг по темам\n"
        f"• ⏱ Интервал от 1 минуты\n"
        f"• 📊 Сбор статистики\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал в бота\n"
        f"3️⃣ Настройте автопостинг или пишите вручную!\n\n"
        f"💡 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    tariff = sub[0] if sub else "free"
    max_channels = TARIFFS[tariff]["max_channels"]
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    current_count = c.fetchone()[0]
    conn.close()
    
    if current_count >= max_channels:
        await query.edit_message_text(
            f"❌ *Лимит каналов: {max_channels}*\n\n"
            f"Ваш тариф '{TARIFFS[tariff]['name']}' позволяет добавить только {max_channels} канала(ов).\n"
            f"Используйте /tariffs для смены тарифа.",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "Чтобы добавить канал:\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Перешлите любое сообщение из канала сюда\n"
        "или отправьте ссылку вида: @channel_username\n\n"
        "📝 *Отправьте ID или ссылку на канал:*",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    # Определяем ID канала
    if text.startswith('@'):
        channel_id = text
    elif 't.me/' in text:
        channel_id = '@' + text.split('t.me/')[-1]
    else:
        channel_id = text
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал! Отправьте ссылку на канал.")
            return
        
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM channels WHERE user_id = ? AND channel_id = ?", (user.id, str(chat.id)))
        if c.fetchone():
            await update.message.reply_text("❌ Этот канал уже добавлен!")
            conn.close()
            return
        
        c.execute("INSERT INTO channels (user_id, channel_id, channel_title, added_date) VALUES (?, ?, ?, ?)",
                  (user.id, str(chat.id), chat.title, datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 Название: {chat.title}\n"
            f"🆔 ID: {chat.id}\n\n"
            f"Теперь вы можете:\n"
            f"• Писать посты вручную\n"
            f"• Настроить автопостинг",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_channel'] = False
        
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Ошибка:* {str(e)}\n\n"
            f"Убедитесь что:\n"
            f"• Бот добавлен в канал\n"
            f"• Бот является администратором\n"
            f"• Ссылка правильная",
            parse_mode='Markdown'
        )

async def write_post_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через меню 'Мои каналы'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"manual_post_{channel_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("manual_post_", "")
    context.user_data['manual_channel'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите пост для публикации*\n\n"
        "Вы можете отправить:\n"
        "• Текст\n"
        "• Фото с подписью\n"
        "• Видео с подписью\n\n"
        "Отправьте /cancel для отмены",
        parse_mode='Markdown'
    )

async def publish_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = context.user_data.get('manual_channel')
    if not channel_id:
        await update.message.reply_text("❌ Ошибка, попробуйте снова /start")
        return
    
    text = update.message.caption or update.message.text
    
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=channel_id, photo=update.message.photo[-1].file_id, caption=text)
        elif update.message.video:
            await context.bot.send_video(chat_id=channel_id, video=update.message.video.file_id, caption=text)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text, parse_mode='Markdown')
        
        # Сохраняем в БД
        conn = sqlite3.connect('posting_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, channel_id, content, post_type, posted_time) VALUES (?, ?, ?, ?, ?)",
                  (update.effective_user.id, channel_id, text, "manual", datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ *Пост успешно опубликован!*", parse_mode='Markdown')
        
        context.user_data['manual_channel'] = None
        keyboard = await get_main_keyboard(update.effective_user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='Markdown')

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *Нет добавленных каналов!*\n\n"
            "Сначала добавьте канал",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel_id, title in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"auto_setup_{channel_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "⚙️ *Выберите канал для настройки автопостинга:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def auto_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_setup_", "")
    context.user_data['auto_channel'] = channel_id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT is_active, interval_minutes, topic FROM auto_posting WHERE channel_id = ? AND user_id = ?", 
              (channel_id, query.from_user.id))
    settings = c.fetchone()
    conn.close()
    
    is_active = settings[0] if settings else 0
    interval = settings[1] if settings else 60
    topic = settings[2] if settings else "technology"
    
    keyboard = await get_auto_keyboard(channel_id, is_active, interval, topic)
    await query.edit_message_text(
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n\n"
        f"Выберите параметры:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT is_active, topic FROM auto_posting WHERE channel_id = ? AND user_id = ?", 
              (channel_id, user_id))
    current = c.fetchone()
    
    if not current:
        # Создаем новую запись
        c.execute("""INSERT INTO auto_posting (user_id, channel_id, is_active, topic, interval_minutes, last_post_time) 
                     VALUES (?, ?, 1, 'technology', 60, ?)""",
                  (user_id, channel_id, datetime.now().isoformat()))
        is_active = 1
    else:
        is_active = 0 if current[0] else 1
        c.execute("UPDATE auto_posting SET is_active = ?, last_post_time = ? WHERE channel_id = ? AND user_id = ?",
                  (is_active, datetime.now().isoformat() if is_active else None, channel_id, user_id))
    
    conn.commit()
    conn.close()
    
    status = "включен" if is_active else "выключен"
    await query.edit_message_text(f"✅ *Автопостинг {status}!*", parse_mode='Markdown')
    await asyncio.sleep(1)
    await auto_setup(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    
    keyboard = await get_intervals_keyboard(channel_id)
    await query.edit_message_text(
        "⏱ *Выберите интервал между постами:*\n\n"
        "Минимальный интервал зависит от вашего тарифа",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    interval = int(parts[3])
    
    user_id = query.from_user.id
    
    # Проверяем лимит по тарифу
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user_id,))
    tariff = c.fetchone()[0]
    min_interval = TARIFFS[tariff]["min_interval"]
    
    if interval < min_interval:
        await query.edit_message_text(
            f"❌ *Интервал {interval} мин недоступен для вашего тарифа*\n\n"
            f"Ваш тариф '{TARIFFS[tariff]['name']}' позволяет интервал от {min_interval} минут\n\n"
            f"Используйте /tariffs для смены тарифа",
            parse_mode='Markdown'
        )
        conn.close()
        return
    
    c.execute("INSERT OR REPLACE INTO auto_posting (user_id, channel_id, interval_minutes, last_post_time) VALUES (?, ?, ?, ?)",
              (user_id, channel_id, interval, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ *Интервал установлен: {interval} минут*", parse_mode='Markdown')
    await asyncio.sleep(1)
    await auto_setup(update, context)

async def change_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_topic_", "")
    
    keyboard = await get_topics_keyboard(channel_id)
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*\n\n"
        "Посты будут генерироваться на выбранную тему",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[3]
    topic = parts[4]
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO auto_posting (user_id, channel_id, topic, last_post_time) VALUES (?, ?, ?, ?)",
              (user_id, channel_id, topic, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    topic_name = POSTS_TEMPLATES[topic]["name"]
    await query.edit_message_text(f"✅ *Тема выбрана: {topic_name}*", parse_mode='Markdown')
    await asyncio.sleep(1)
    await auto_setup(update, context)

async def back_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await auto_setup(update, context)

async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title, added_date FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов*\n\n"
            "Нажмите '➕ Добавить канал'",
            parse_mode='Markdown'
        )
        return
    
    text = "📢 *Ваши каналы:*\n\n"
    for channel_id, title, date in channels:
        text += f"📌 {title}\n🆔 `{channel_id}`\n📅 Добавлен: {date[:10]}\n\n"
    
    keyboard = [[InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("SELECT tariff FROM subscriptions WHERE user_id = ?", (user.id,))
    current = c.fetchone()
    current_tariff = current[0] if current else "free"
    conn.close()
    
    text = "💎 *Доступные тарифы (все бесплатны!)*\n\n"
    
    for key, tariff in TARIFFS.items():
        mark = "✅ *ТЕКУЩИЙ* " if key == current_tariff else "📌 "
        text += f"{mark}{tariff['name']}\n"
        for feature in tariff['features']:
            text += f"   {feature}\n"
        text += "\n"
    
    keyboard = []
    for key in TARIFFS.keys():
        if key != current_tariff:
            keyboard.append([InlineKeyboardButton(f"Выбрать {TARIFFS[key]['name']}", callback_data=f"select_tariff_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    c.execute("UPDATE subscriptions SET tariff = ?, max_channels = ? WHERE user_id = ?",
              (tariff_key, TARIFFS[tariff_key]["max_channels"], user_id))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        f"✅ *Тариф изменен на {TARIFFS[tariff_key]['name']}!*\n\n"
        f"Теперь вам доступно {TARIFFS[tariff_key]['max_channels']} каналов\n"
        f"Минимальный интервал: {TARIFFS[tariff_key]['min_interval']} минут",
        parse_mode='Markdown'
    )
    await asyncio.sleep(2)
    await show_tariffs(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT tariff, start_date FROM subscriptions WHERE user_id = ?", (user.id,))
    sub = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM channels WHERE user_id = ? AND status='active'", (user.id,))
    channels_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user.id,))
    posts_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM auto_posting WHERE user_id = ? AND is_active = 1", (user.id,))
    active_auto = c.fetchone()[0]
    
    conn.close()
    
    tariff = sub[0] if sub else "free"
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🆔 ID: {user.id}\n"
        f"📝 Имя: {user.first_name}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n\n"
        f"📊 *Статистика:*\n"
        f"• Каналов: {channels_count}/{TARIFFS[tariff]['max_channels']}\n"
        f"• Постов: {posts_count}\n"
        f"• Активных автопостингов: {active_auto}\n\n"
        f"🎁 Все тарифы бесплатны!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    conn = sqlite3.connect('posting_bot.db')
    c = conn.cursor()
    
    today = datetime.now().date()
    week_ago = datetime.now() - timedelta(days=7)
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND DATE(posted_time) = ?", (user.id, today))
    today_posts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND posted_time >= ?", (user.id, week_ago))
    week_posts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND post_type = 'auto'", (user.id,))
    auto_posts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ? AND post_type = 'manual'", (user.id,))
    manual_posts = c.fetchone()[0]
    
    conn.close()
    
    text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 *Посты:*\n"
        f"• Сегодня: {today_posts}\n"
        f"• За неделю: {week_posts}\n"
        f"• Всего: {today_posts + week_posts}\n\n"
        f"🤖 *По типам:*\n"
        f"• Автопосты: {auto_posts}\n"
        f"• Ручные: {manual_posts}\n\n"
        f"💡 *Совет:* Включите автопостинг для автоматической публикации!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "ℹ️ *Помощь*\n\n"
        "📋 *Как пользоваться ботом:*\n\n"
        "1️⃣ *Добавьте канал*\n"
        "• Добавьте @bot в канал как администратора\n"
        "• В меню 'Мои каналы' ➕ 'Добавить канал'\n"
        "• Отправьте ссылку на канал\n\n"
        "2️⃣ *Ручные посты*\n"
        "• 'Написать пост' ➡️ выберите канал\n"
        "• Отправьте текст, фото или видео\n\n"
        "3️⃣ *Автопостинг*\n"
        "• 'Автопостинг' ➡️ выберите канал\n"
        "• Включите автопостинг\n"
        "• Выберите тему и интервал\n"
        "• Бот будет постить автоматически!\n\n"
        "⏱ *Интервалы:*\n"
        "• Бесплатный: от 5 минут\n"
        "• Базовый: от 2 минут\n"
        "• PRO: от 1 минуты\n\n"
        "🎁 *Все тарифы БЕСПЛАТНЫ!*\n\n"
        "❓ Вопросы: @support"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*\n\nВыберите действие:", 
                                  parse_mode='Markdown', 
                                  reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ *Действие отменено*", parse_mode='Markdown')
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    
    if data == "back_main":
        await back_main(update, context)
    elif data == "write_post":
        await write_post_manual(update, context)
    elif data == "my_channels":
        await show_channels(update, context)
    elif data == "add_channel":
        await add_channel(update, context)
    elif data == "auto_posting_menu":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("manual_post_"):
        await send_manual_post(update, context)
    elif data.startswith("auto_setup_"):
        await auto_setup(update, context)
    elif data.startswith("toggle_auto_"):
        await toggle_auto(update, context)
    elif data.startswith("change_interval_"):
        await change_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("change_topic_"):
        await change_topic(update, context)
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    elif data.startswith("back_auto_"):
        await back_auto(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                          lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
                                          else publish_manual(u, c) if c.user_data.get('manual_channel')
                                          else None))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, 
                                          lambda u, c: publish_manual(u, c) if c.user_data.get('manual_channel') else None))
    
    # Запускаем фоновый процесс автопостинга
    async def start_auto_posting():
        asyncio.create_task(auto_posting_loop(application))
    
    application.post_init = start_auto_posting
    
    logger.info("🚀 Бот запущен!")
    logger.info("✅ Автопостинг работает!")
    logger.info("⏱ Доступны интервалы от 1 минуты!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
    
