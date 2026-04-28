import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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

# ==================== ХРАНИЛИЩЕ ДАННЫХ В ПАМЯТИ ====================
class Storage:
    def __init__(self):
        self.users = {}  # user_id -> user_data
        self.channels = {}  # user_id -> [channels]
        self.auto_posting = {}  # channel_id -> auto_settings
        self.sources = {}  # user_id -> [sources]
        self.posts = []  # список постов
        self.posting_tasks = {}  # channel_id -> task

storage = Storage()

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 2,
        "post_interval": 60,  # 1 минута в секундах
        "features": ["✅ 2 канала", "✅ Интервал 1 минута", "✅ 5 тем"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 5,
        "post_interval": 30,  # 30 секунд
        "features": ["✅ 5 каналов", "✅ Интервал 30 секунд", "✅ 10 тем"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 10,
        "post_interval": 10,  # 10 секунд
        "features": ["✅ 10 каналов", "✅ Интервал 10 секунд", "✅ 15 тем"]
    }
}

# ==================== ТЕМЫ ДЛЯ КОНТЕНТА ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии",
        "posts": [
            "🚀 *Новый прорыв в AI!* Искусственный интеллект теперь может генерировать видео по текстовому описанию. Будущее уже наступило!\n\n#технологии #ai #инновации",
            "📱 *Топ-5 фишек нового iPhone*: 1) Титановый корпус 2) Бесконечный экран 3) ИИ-камера 4) Зарядка за 5 минут 5) Спутниковая связь\n\n#apple #iphone #гаджеты",
            "💻 *Python vs JavaScript: что учить в 2024?* Оба языка востребованы, но Python лидирует в AI и Data Science, а JS - в веб-разработке.\n\n#программирование #python #javascript",
            "🔬 *Квантовые компьютеры стали реальностью!* Google объявил о создании 100-кубитного процессора, способного решать задачи за секунды.\n\n#квантовыевычисления #наука",
            "🎮 *Новый уровень графики в играх*: Unreal Engine 6 показывает фотореалистичную графику в реальном времени.\n\n#игры #unrealengine #гейминг"
        ]
    },
    "business": {
        "name": "📊 Бизнес",
        "posts": [
            "💼 *Как выйти на пассивный доход за 3 месяца?* Топ-5 стратегий для начинающих предпринимателей.\n\n#бизнес #пассивныйдоход #стартап",
            "📈 *Крипторынок обновил максимумы!* Биткоин достиг $100,000. Что дальше? Аналитика и прогнозы.\n\n#криптовалюта #биткоин #инвестиции",
            "🏢 *Как масштабировать бизнес в 10 раз?* Реальные кейсы и стратегии роста.\n\n#масштабирование #бизнесстратегия",
            "💰 *Фриланс 2024: какие навыки самые дорогие?* Топ-10 востребованных профессий с доходом от $5000.\n\n#фриланс #заработок #удаленка",
            "📊 *Секреты успешных инвесторов*: 5 правил, которые работают всегда.\n\n#инвестиции #финансы #успех"
        ]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "posts": [
            "🏃‍♂️ *Утренняя зарядка 5 минут*: комплекс упражнений для бодрости на весь день!\n\n#здоровье #фитнес #зарядка",
            "🥗 *Правильное питание*: 10 продуктов, которые стоит есть каждый день.\n\n#здоровоепитание #пп #советы",
            "🧘 *Медитация для начинающих*: 3 простых техники для снижения стресса.\n\n#медитация #релакс #психология",
            "💪 *Тренировка дома*: комплекс на 15 минут для всех групп мышц.\n\n#фитнес #тренировкадома #спорт",
            "😴 *Как высыпаться за 5 часов?* Техники глубокого сна и восстановления.\n\n#сон #здоровье #продуктивность"
        ]
    },
    "education": {
        "name": "📚 Образование",
        "posts": [
            "📖 *Как выучить английский за 3 месяца?* Методика полиглотов, которая работает.\n\n#английский #обучение #саморазвитие",
            "🎓 *Топ-10 бесплатных курсов 2024*: от программирования до маркетинга.\n\n#образование #курсы #бесплатно",
            "🧠 *Скорочтение за неделю*: упражнения для развития быстрого чтения.\n\n#скорочтение #развитие #память",
            "📚 *Книги, которые изменят вашу жизнь*: подборка из 10 must-read.\n\n#книги #саморазвитие #мотивация",
            "🎯 *Как достигать любых целей?* Система SMART и пошаговый план.\n\n#цели #успех #мотивация"
        ]
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "posts": [
            "🎬 *Топ-10 фильмов 2024*: что обязательно посмотреть!\n\n#кино #фильмы #кинотеатр",
            "🎵 *Музыкальные новинки*: лучшие треки этой недели 🎧\n\n#музыка #новинки #плейлист",
            "😂 *Мемы дня*: подборка самых смешных мемов из интернета 🤣\n\n#мемы #юмор #ржака",
            "🎮 *Новые игры месяца*: во что поиграть на выходных?\n\n#игры #новинки #гейминг",
            "🍿 *Что посмотреть вечером?* Подборка лучших сериалов 2024 года.\n\n#сериалы #кино #вечернийпросмотр"
        ]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "posts": [
            "🏠 *Как организовать идеальный дом?* 10 лайфхаков для уюта.\n\n#дом #уют #лайфхаки",
            "✈️ *Путешествия мечты*: топ-5 мест, которые нужно посетить.\n\n#путешествия #отдых #впечатления",
            "📸 *Фото на iPhone как у профессионала*: секреты идеальных снимков.\n\n#фото #iphone #лайфхаки",
            "🎨 *Хобби, которые приносят доход*: от вышивки до блогинга.\n\n#хобби #заработок #творчество",
            "💑 *Отношения без ссор*: 5 правил счастливой пары.\n\n#отношения #психология #любовь"
        ]
    },
    "news": {
        "name": "📰 Новости",
        "posts": [
            "🌍 *Главные новости дня*: что произошло в мире за последние часы.\n\n#новости #мир #события",
            "🚀 *Elon Musk представил новый проект*: Neuralink позволяет управлять компьютером силой мысли.\n\n#технологии #илонмаск #новости",
            "💰 *Курс валют на сегодня*: актуальная информация от Центробанка.\n\n#курсвалют #финансы #экономика",
            "⚡️ *Срочная новость*: важное событие, о котором все говорят.\n\n #срочно #новости #важно",
            "📈 *Биржи растут*: аналитика и прогнозы на сегодня.\n\n #биржи #инвестиции #новости"
        ]
    },
    "cooking": {
        "name": "🍳 Кулинария",
        "posts": [
            "🍕 *Идеальная пицца за 30 минут*: простой рецепт, как в Италии!\n\n#пицца #рецепт #кулинария",
            "🍰 *Торт без выпечки за 15 минут*: вкуснее, чем в магазине.\n\n#десерт #рецепт #торт",
            "🥗 *Полезный завтрак за 5 минут*: овсяноблин с начинкой.\n\n#завтрак #пп #здоровоепитание",
            "🍲 *Борщ как у бабушки*: секретный рецепт наваристого супа.\n\n#борщ #первоеблюдо #рецепт",
            "🍪 *Печенье из 3 ингредиентов*: быстро, вкусно, бюджетно!\n\n#печенье #десерт #рецепт"
        ]
    }
}

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🔄 Репосты", callback_data="reposts_menu")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_channels_keyboard(user_id: int):
    user_channels = storage.channels.get(user_id, [])
    
    keyboard = []
    for channel in user_channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel['title']}", callback_data=f"channel_{channel['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_auto_keyboard(user_id: int):
    user_channels = storage.channels.get(user_id, [])
    
    keyboard = []
    for channel in user_channels:
        # Проверяем статус автопостинга
        auto_settings = storage.auto_posting.get(channel['id'])
        status = "✅" if auto_settings and auto_settings.get('active') else "❌"
        keyboard.append([
            InlineKeyboardButton(f"{status} {channel['title']}", callback_data=f"auto_channel_{channel['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("⏱ 1 минута", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("⏱ 5 минут", callback_data=f"interval_{channel_id}_300")],
        [InlineKeyboardButton("⏱ 10 минут", callback_data=f"interval_{channel_id}_600")],
        [InlineKeyboardButton("⏱ 30 минут", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("⏱ 1 час", callback_data=f"interval_{channel_id}_3600")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_task(channel_id: str, user_id: int, bot):
    """Задача автопостинга для канала"""
    while True:
        try:
            # Получаем настройки
            settings = storage.auto_posting.get(channel_id)
            if not settings or not settings.get('active'):
                logger.info(f"Автопостинг для канала {channel_id} остановлен")
                break
            
            topic = settings.get('topic')
            interval = settings.get('interval', 60)
            
            if topic and topic in TOPICS:
                # Выбираем случайный пост из темы
                posts_list = TOPICS[topic]['posts']
                post_text = random.choice(posts_list)
                
                # Отправляем пост
                try:
                    await bot.send_message(chat_id=channel_id, text=post_text, parse_mode='Markdown')
                    logger.info(f"Автопост отправлен в канал {channel_id} на тему {topic}")
                    
                    # Обновляем статистику
                    storage.posts.append({
                        'channel_id': channel_id,
                        'user_id': user_id,
                        'content': post_text,
                        'time': datetime.now()
                    })
                except Exception as e:
                    logger.error(f"Ошибка отправки авто поста: {e}")
            
            # Ждем указанный интервал
            await asyncio.sleep(interval)
            
        except asyncio.CancelledError:
            logger.info(f"Задача автопостинга для канала {channel_id} отменена")
            break
        except Exception as e:
            logger.error(f"Ошибка в автопостинге для {channel_id}: {e}")
            await asyncio.sleep(60)

def start_auto_posting(channel_id: str, user_id: int, bot):
    """Запуск автопостинга для канала"""
    if channel_id in storage.posting_tasks:
        storage.posting_tasks[channel_id].cancel()
    
    task = asyncio.create_task(auto_posting_task(channel_id, user_id, bot))
    storage.posting_tasks[channel_id] = task

def stop_auto_posting(channel_id: str):
    """Остановка автопостинга для канала"""
    if channel_id in storage.posting_tasks:
        storage.posting_tasks[channel_id].cancel()
        del storage.posting_tasks[channel_id]

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Регистрируем пользователя
    if user.id not in storage.users:
        storage.users[user.id] = {
            'id': user.id,
            'name': user.first_name,
            'username': user.username,
            'tariff': 'free',
            'joined': datetime.now()
        }
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автоматического постинга*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• 🤖 Автопостинг с интервалом от 1 минуты\n"
        f"• 🔄 Репосты из других каналов\n"
        f"• 🎭 9 тем для контента\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал через кнопку 'Мои каналы'\n"
        f"3️⃣ Включите автопостинг и выберите тему!\n\n"
        f"💡 *Автопостинг работает сразу после включения!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Перешлите ЛЮБОЕ сообщение из канала сюда\n\n"
        "Или отправьте:\n"
        "• Ссылку на канал: https://t.me/username\n"
        "• ID канала: -1001234567890\n\n"
        "⚠️ *Бот должен быть администратором!*",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    
    channel_id = None
    channel_title = None
    
    try:
        # Если переслано сообщение из канала
        if message.forward_from_chat:
            channel_id = str(message.forward_from_chat.id)
            channel_title = message.forward_from_chat.title
        else:
            # Пробуем получить канал по тексту
            text = message.text.strip()
            if text.startswith('@') or 't.me/' in text:
                # Извлекаем username
                if 't.me/' in text:
                    username = text.split('t.me/')[-1]
                else:
                    username = text[1:]
                
                # Получаем информацию о канале
                chat = await context.bot.get_chat(chat_id=f"@{username}")
                channel_id = str(chat.id)
                channel_title = chat.title
            elif text.startswith('-100'):
                chat = await context.bot.get_chat(chat_id=text)
                channel_id = str(chat.id)
                channel_title = chat.title
            else:
                await message.reply_text("❌ Неверный формат. Перешлите сообщение из канала или отправьте ссылку.")
                return
        
        # Проверяем тариф и лимиты
        user_tariff = storage.users[user.id]['tariff']
        max_channels = TARIFFS[user_tariff]['max_channels']
        user_channels = storage.channels.get(user.id, [])
        
        if len(user_channels) >= max_channels:
            await message.reply_text(
                f"❌ Достигнут лимит каналов для тарифа '{TARIFFS[user_tariff]['name']}'\n"
                f"Максимум: {max_channels} каналов"
            )
            return
        
        # Проверяем, не добавлен ли уже
        for ch in user_channels:
            if ch['id'] == channel_id:
                await message.reply_text("❌ Этот канал уже добавлен!")
                return
        
        # Добавляем канал
        new_channel = {
            'id': channel_id,
            'title': channel_title,
            'added': datetime.now()
        }
        
        if user.id not in storage.channels:
            storage.channels[user.id] = []
        storage.channels[user.id].append(new_channel)
        
        await message.reply_text(
            f"✅ *Канал добавлен!*\n\n"
            f"📢 Название: {channel_title}\n"
            f"🆔 ID: {channel_id}\n\n"
            f"Теперь вы можете:\n"
            f"• Написать пост вручную\n"
            f"• Включить автопостинг\n"
            f"• Настроить репосты",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_channel'] = False
        
    except Exception as e:
        await message.reply_text(
            f"❌ Ошибка: {str(e)}\n\n"
            f"Убедитесь, что:\n"
            f"• Бот добавлен в канал как администратор\n"
            f"• У бота есть права на публикацию"
        )

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_channels = storage.channels.get(query.from_user.id, [])
    
    if not user_channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал через меню 'Мои каналы'",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel in user_channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {channel['title']}", callback_data=f"post_channel_{channel['id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_channel_", "")
    context.user_data['post_channel_id'] = channel_id
    
    await query.edit_message_text(
        "📝 *Напишите ваш пост*\n\n"
        "Вы можете отправить:\n"
        "• Текст сообщения\n"
        "• Фото с подписью\n"
        "• Видео с подписью\n\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_post'] = True

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel_id')
    
    if not channel_id:
        await update.message.reply_text("❌ Сессия истекла. Начните заново /start")
        return
    
    try:
        # Отправляем пост
        if update.message.text:
            await context.bot.send_message(chat_id=channel_id, text=update.message.text, parse_mode='Markdown')
        elif update.message.photo:
            caption = update.message.caption or ""
            await context.bot.send_photo(chat_id=channel_id, photo=update.message.photo[-1].file_id, caption=caption, parse_mode='Markdown')
        elif update.message.video:
            caption = update.message.caption or ""
            await context.bot.send_video(chat_id=channel_id, video=update.message.video.file_id, caption=caption, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Неподдерживаемый тип сообщения")
            return
        
        # Сохраняем в статистику
        storage.posts.append({
            'channel_id': channel_id,
            'user_id': user.id,
            'content': update.message.text or update.message.caption,
            'time': datetime.now()
        })
        
        await update.message.reply_text("✅ *Пост успешно опубликован!*", parse_mode='Markdown')
        
        context.user_data['awaiting_post'] = False
        context.user_data['post_channel_id'] = None
        
        # Показываем главное меню
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_channels = storage.channels.get(query.from_user.id, [])
    
    if not user_channels:
        await query.edit_message_text(
            "❌ *У вас нет добавленных каналов!*\n\n"
            "Сначала добавьте канал для автопостинга",
            parse_mode='Markdown'
        )
        return
    
    keyboard = await get_auto_keyboard(query.from_user.id)
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - автопостинг активен\n"
        "❌ - автопостинг неактивен\n\n"
        "Выберите канал:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_auto_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    context.user_data['auto_channel_id'] = channel_id
    
    settings = storage.auto_posting.get(channel_id, {})
    is_active = settings.get('active', False)
    topic = settings.get('topic')
    interval = settings.get('interval', 60)
    
    topic_name = TOPICS.get(topic, {}).get('name', 'Не выбрана') if topic else 'Не выбрана'
    interval_min = interval // 60
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval_min} мин.\n\n"
        f"Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал постинга", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    user_id = query.from_user.id
    
    settings = storage.auto_posting.get(channel_id, {})
    
    if settings.get('active', False):
        # Останавливаем автопостинг
        stop_auto_posting(channel_id)
        settings['active'] = False
        storage.auto_posting[channel_id] = settings
        await query.edit_message_text("⏹ *Автопостинг остановлен*", parse_mode='Markdown')
    else:
        # Проверяем выбрана ли тема
        if not settings.get('topic'):
            await query.edit_message_text(
                "❌ *Сначала выберите тему для постов!*\n"
                "Нажмите кнопку 'Выбрать тему'",
                parse_mode='Markdown'
            )
            await asyncio.sleep(2)
            await configure_auto_channel(update, context)
            return
        
        # Запускаем автопостинг
        settings['active'] = True
        storage.auto_posting[channel_id] = settings
        start_auto_posting(channel_id, user_id, context.bot)
        await query.edit_message_text("▶️ *Автопостинг запущен!*", parse_mode='Markdown')
    
    await asyncio.sleep(1)
    await configure_auto_channel(update, context)

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_", "")
    
    keyboard = []
    for topic_key, topic_info in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(f"{topic_info['name']}", callback_data=f"set_topic_{channel_id}_{topic_key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
    
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic_key = parts[3]
    
    if channel_id not in storage.auto_posting:
        storage.auto_posting[channel_id] = {}
    
    storage.auto_posting[channel_id]['topic'] = topic_key
    
    await query.edit_message_text(
        f"✅ *Тема выбрана:* {TOPICS[topic_key]['name']}\n\n"
        f"Теперь включите автопостинг!",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    
    keyboard = await get_interval_keyboard(channel_id)
    await query.edit_message_text(
        "⏱ *Выберите интервал постинга:*\n\n"
        "Как часто публиковать посты?",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    if channel_id not in storage.auto_posting:
        storage.auto_posting[channel_id] = {}
    
    storage.auto_posting[channel_id]['interval'] = interval
    
    # Если автопостинг был активен, перезапускаем с новым интервалом
    if storage.auto_posting[channel_id].get('active'):
        user_id = query.from_user.id
        stop_auto_posting(channel_id)
        start_auto_posting(channel_id, user_id, context.bot)
    
    interval_min = interval // 60
    await query.edit_message_text(
        f"✅ *Интервал установлен: {interval_min} минут*\n\n"
        f"Автопостинг {'продолжает' if storage.auto_posting[channel_id].get('active') else 'будет'} работать с новым интервалом",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    await configure_auto_channel(update, context)

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_tariff = storage.users[user_id]['tariff']
    
    text = "💎 *Доступные тарифы*\n\n"
    
    for tariff_key, tariff_info in TARIFFS.items():
        is_current = "✅ *ТЕКУЩИЙ* " if tariff_key == current_tariff else ""
        text += f"{is_current}{tariff_info['name']}\n"
        text += "📋 Возможности:\n"
        for feature in tariff_info['features']:
            text += f"{feature}\n"
        text += f"⏱ Интервал: каждые {tariff_info['post_interval']} сек.\n\n"
    
    keyboard = []
    for tariff_key in TARIFFS:
        if tariff_key != current_tariff:
            keyboard.append([InlineKeyboardButton(f"Выбрать {TARIFFS[tariff_key]['name']}", callback_data=f"select_tariff_{tariff_key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    storage.users[user_id]['tariff'] = tariff_key
    
    await query.edit_message_text(
        f"✅ *Тариф обновлен на {TARIFFS[tariff_key]['name']}*\n\n"
        f"Новые возможности уже доступны!",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    await show_tariffs(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = storage.users.get(user_id, {})
    tariff = user_data.get('tariff', 'free')
    
    user_channels = storage.channels.get(user_id, [])
    user_posts = [p for p in storage.posts if p['user_id'] == user_id]
    auto_channels = sum(1 for ch_id, settings in storage.auto_posting.items() if settings.get('active') and any(c['id'] == ch_id for c in user_channels))
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 Имя: {user_data.get('name', '')}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n"
        f"📢 Каналов: {len(user_channels)}/{TARIFFS[tariff]['max_channels']}\n"
        f"📝 Постов: {len(user_posts)}\n"
        f"🤖 Активный автопостинг: {auto_channels} каналов\n\n"
        f"📅 В системе с: {user_data.get('joined', datetime.now()).strftime('%d.%m.%Y')}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Сменить тариф", callback_data="tariffs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_posts = [p for p in storage.posts if p['user_id'] == user_id]
    
    today = datetime.now().date()
    posts_today = sum(1 for p in user_posts if p['time'].date() == today)
    posts_week = sum(1 for p in user_posts if p['time'] > datetime.now() - timedelta(days=7))
    
    text = (
        f"📊 *Ваша статистика*\n\n"
        f"📝 Всего постов: {len(user_posts)}\n"
        f"📆 Сегодня: {posts_today}\n"
        f"📅 За неделю: {posts_week}\n\n"
    )
    
    # Посты по каналам
    if user_posts:
        text += "📢 *По каналам:*\n"
        channels_stats = {}
        for post in user_posts:
            channel_id = post['channel_id']
            channels_stats[channel_id] = channels_stats.get(channel_id, 0) + 1
        
        for channel_id, count in list(channels_stats.items())[:5]:
            # Находим название канала
            channel_title = channel_id
            for ch in storage.channels.get(user_id, []):
                if ch['id'] == channel_id:
                    channel_title = ch['title']
                    break
            text += f"• {channel_title}: {count} постов\n"
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ *Действие отменено*", parse_mode='Markdown')
    
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ОБРАБОТЧИК CALLBACK ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "write_post":
        await write_post(update, context)
    elif data == "my_channels":
        keyboard = await get_channels_keyboard(query.from_user.id)
        await query.edit_message_text("📢 *Ваши каналы*", parse_mode='Markdown', reply_markup=keyboard)
    elif data == "add_channel":
        await add_channel(update, context)
    elif data == "reposts_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Репосты (в разработке)", callback_data="back_main")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
        ])
        await query.edit_message_text("🔄 *Репосты*\n\nФункция в разработке", parse_mode='Markdown', reply_markup=keyboard)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "help":
        help_text = (
            "❓ *Помощь*\n\n"
            "📋 *Инструкция:*\n\n"
            "1️⃣ *Добавьте канал*\n"
            "• Добавьте бота в канал как администратора\n"
            "• В меню 'Мои каналы' ➕ 'Добавить канал'\n"
            "• Перешлите сообщение из канала боту\n\n"
            "2️⃣ *Включите автопостинг*\n"
            "• В меню 'Автопостинг'\n"
            "• Выберите канал\n"
            "• Выберите тему\n"
            "• Установите интервал (от 1 минуты)\n"
            "• Включите автопостинг!\n\n"
            "3️⃣ *Ручная публикация*\n"
            "• 'Написать пост' ➡️ выберите канал\n"
            "• Отправьте текст/фото/видео\n\n"
            "💡 *Особенности:*\n"
            "• Автопостинг работает сразу после включения\n"
            "• Можно настроить для каждого канала\n"
            "• 9 тем на выбор\n"
            "• Интервал от 10 секунд до 1 часа\n\n"
            "🎁 *Все тарифы бесплатны!*"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    elif data.startswith("post_channel_"):
        await post_to_channel(update, context)
    elif data.startswith("auto_channel_"):
        await configure_auto_channel(update, context)
    elif data.startswith("toggle_auto_"):
        await toggle_auto(update, context)
    elif data.startswith("select_topic_"):
        await select_topic(update, context)
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    elif data.startswith("change_interval_"):
        await change_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Добавление каналов
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
        else (handle_post(u, c) if c.user_data.get('awaiting_post')
        else None)
    ))
    
    # Медиа для постов
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO,
        handle_post
    ))
    
    # Пересланные сообщения
    application.add_handler(MessageHandler(
        filters.FORWARDED,
        process_add_channel
    ))
    
    # Callback
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот запущен!")
    logger.info("✅ Автопостинг работает с интервалом от 1 минуты")
    logger.info("💾 Данные хранятся в памяти")
    
    application.run_polling()

if __name__ == '__main__':
    main()
