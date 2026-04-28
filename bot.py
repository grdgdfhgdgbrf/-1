import asyncio
import logging
import time
import random
import aiohttp
import io
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8359617420:AAEh9jNsRtQ2F3jshJ0rgBWMIAH2MHdvCxc"

# Состояния для создания своей темы
WAITING_TOPIC_NAME, WAITING_TOPIC_POSTS, WAITING_TOPIC_QUERIES = range(3)

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 3,
        "min_interval": 60,
        "max_posts_per_day": 100,
        "image_size": "medium",
        "features": ["✅ 3 канала", "✅ Интервал от 1 мин", "✅ 100 постов/день", "✅ Текстовые посты"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 10,
        "min_interval": 30,
        "max_posts_per_day": 500,
        "image_size": "large",
        "features": ["✅ 10 каналов", "✅ Интервал от 30 сек", "✅ 500 постов/день", "✅ Картинки", "✅ Свои темы"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 30,
        "min_interval": 10,
        "max_posts_per_day": 2000,
        "image_size": "hd",
        "features": ["✅ 30 каналов", "✅ Интервал от 10 сек", "✅ 2000 постов/день", "✅ HD картинки", 
                    "✅ Поиск картинок", "✅ Видео", "✅ Свои темы", "✅ Репосты"]
    }
}

# ==================== НОВЫЕ ТЕМЫ ====================
TOPICS = {
    "nft": {
        "name": "🎨 NFT Искусство",
        "emoji": "🎨",
        "posts": [
            "🎨 **ТОП-5 NFT, которые взлетят в 2025**\n\nBored Ape, CryptoPunks, Azuki - какие NFT стоит купить уже сейчас? Аналитика и прогнозы от экспертов.\n\n#nft #искусство #токены",
            "🖼 **Как создать и продать свой NFT за $10,000**\n\nПошаговое руководство для художников и дизайнеров. Платформы, комиссии, продвижение.\n\n#nftart #токены #заработок",
            "🌐 **Цифровое искусство: новая эра**\n\nBeeple продал NFT за $69 миллионов. Почему коллекционеры скупают пиксели за миллионы?\n\n#nft #art #крипта",
            "🔥 **NFT-коллекции, которые взорвали рынок**\n\nОбзор самых дорогих и популярных коллекций. Инвестируйте с умом!\n\n#nftcollection #инвестиции #крипта",
            "🏺 **NFT в реальной жизни**\n\nКак токены меняют мир искусства, музыки и недвижимости. Реальные кейсы использования.\n\n#nft #реальность #технологии"
        ],
        "image_queries": ["nft art", "crypto art", "digital art", "nft collection", "rare nft"]
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "posts": [
            "🚀 **Как раскрутить Telegram канал до 100,000 подписчиков**\n\nРеальная стратегия 2025: реклама, взаимопиар, чат-боты. Никакой магии - только работающие методы.\n\n#telegram #продвижение #каналы",
            "🤖 **Топ-10 ботов для Telegram, которые облегчат жизнь**\n\nБоты для работы, учебы, развлечений и бизнеса. Список обязательных к установке.\n\n#telegramботы #полезное #автоматизация",
            "💎 **Монетизация Telegram канала: от 0 до $5000 в месяц**\n\nКак зарабатывать на своем канале: реклама, подписки, товары. Реальные цифры.\n\n#монетизация #telegram #заработок",
            "📊 **Аналитика Telegram каналов**\n\nКак отслеживать статистику, конкурентов и растить аудиторию. Лучшие сервисы.\n\n#аналитика #telegram #статистика",
            "🎯 **Полезные каналы для предпринимателей**\n\nТоп-50 Telegram каналов, которые стоит подписаться. Бизнес, маркетинг, инсайты.\n\n#telegram #бизнес #полезныессылки"
        ],
        "image_queries": ["telegram logo", "telegram app", "telegram channel", "social media", "messenger"]
    },
    "crypto": {
        "name": "₿ Криптовалюта",
        "emoji": "₿",
        "posts": [
            "₿ **Биткоин $200,000: реальность 2025**\n\nПрогнозы аналитиков, новости регуляций, куда движется рынок. Инвестируйте с умом.\n\n#биткоин #криптовалюта #прогнозы",
            "📈 **Альткоины, которые дадут 100x в 2025**\n\nТоп-10 перспективных монет: Solana, Avalanche, Arbitrum. Почему они выстрелят?\n\n#альткоины #крипта #инвестиции",
            "💰 **Как заработать на крипте без вложений**\n\nAirdrop, тестнеты, рефералы - реальные способы заработать свои первые монеты.\n\n#крипта #заработок #airdrop",
            "🔒 **Как защитить свою крипту от хакеров**\n\nHardware кошельки, двухфакторка, безопасность. Полное руководство.\n\n#безопасность #криптокошелек #хранение",
            "🚀 **DeFi и стейкинг: пассивный доход 20-50% годовых**\n\nКак получать проценты на свои токены. Лучшие протоколы и стратегии.\n\n#defi #стейкинг #пассивныйдоход"
        ],
        "image_queries": ["bitcoin", "cryptocurrency", "blockchain", "trading crypto", "mining"]
    },
    "aitop": {
        "name": "🤖 Искусственный Интеллект",
        "emoji": "🤖",
        "posts": [
            "🤖 **ChatGPT 5 уже здесь: что нового?**\n\nНейросеть научилась создавать видео, программировать и решать научные задачи. Обзор новых возможностей.\n\n#нейросети #ии #chatgpt",
            "🎨 **Midjourney V7: AI-художник создает шедевры**\n\nКак создавать фотореалистичные изображения с помощью нейросетей. Промпты для новичков.\n\n#midjourney #нейросети #искусство",
            "💻 **Как программировать с помощью AI и зарабатывать**\n\nGithub Copilot, Claude, DeepSeek - ваш персональный ассистент. Реальные кейсы.\n\n#aprogramming #нейросети #заработок",
            "🎥 **Sora от OpenAI: видео создается из текста**\n\nРеволюция в видеопроизводстве. Генерация 4K видео по описанию. Возможности и ограничения.\n\n#sora #нейросети #видео",
            "🧠 **ИИ-инструменты для бизнеса и жизни**\n\n50 нейросетей, которые упростят работу и сэкономят время. Лучшие сервисы 2025.\n\n#нейросети #инструменты #бизнес"
        ],
        "image_queries": ["artificial intelligence", "ai robot", "chatgpt", "machine learning", "ai brain"]
    },
    "nftart": {
        "name": "🖼 NFT Коллекции",
        "emoji": "🖼",
        "posts": [
            "🖼 **Самые дорогие NFT в истории**\n\nТоп-10 продаж: Beeple, Pak, XCOPY. Почему эти пиксели стоят миллионы?\n\n#nftart #коллекции #рекорды",
            "🎭 **Pudgy Penguins: как пингвины покорили мир**\n\nИстория взлета коллекции, награды, коллаборации с крупными брендами.\n\n#pudgypenguins #nft #историяуспеха",
            "👾 **Киберпанк в NFT: тренды и лучшие проекты**\n\nКиберпанк эстетика в цифровом искусстве. Обзор лучших проектов и коллекций.\n\n#киберпанк #nft #искусство",
            "🎨 **Как создать свою NFT коллекцию**\n\nГенерация 10,000 уникальных изображений, смарт-контракты, размещение на биржах.\n\n#создатьnft #токены #искусство",
            "🏆 **Azuki: история успеха японского NFT**\n\nКак аниме-стиль покорил рынок. Секреты успеха и дорожная карта.\n\n#azuki #nft #аниме"
        ],
        "image_queries": ["nft collection", "cryptopunk", "bored ape", "digital collectible", "rare nft art"]
    },
    "cryptogaming": {
        "name": "🎮 Crypto Gaming",
        "emoji": "🎮",
        "posts": [
            "🎮 **Play-to-Earn: как зарабатывать играя в 2025**\n\nAxie Infinity, Gods Unchained, The Sandbox - сколько можно заработать на криптоиграх.\n\n#playtoearn #cryptogames #заработок",
            "🌍 **Metaverse: будущее уже здесь**\n\nDecentraland, The Sandbox, Somnium Space - покупаем землю, строим бизнес, зарабатываем.\n\n#метавселенная #nft #crypto",
            "⚔️ **Новые криптоигры 2025: во что стоит играть**\n\nОбзор лучших проектов: Illuvium, Star Atlas, Big Time. Геймплей и экономика.\n\n#cryptogames #новинки #гейминг",
            "💎 **Как заработать на NFT в играх**\n\nСтратегии, гайды, лучшие практики. От новичка до профи в мире криптоигр.\n\n#nftgaming #заработок #стратегии",
            "🏆 **Турниры с призовым фондом в криптоиграх**\n\nЗарабатывай как профессионал. Расписание турниров, призы, стратегии.\n\n#киберспорт #cryptogames #турниры"
        ],
        "image_queries": ["crypto game", "metaverse", "play to earn", "nft game", "virtual world"]
    }
}

# ==================== ХРАНИЛИЩЕ СВОИХ ТЕМ ====================
class CustomTopics:
    def __init__(self):
        self.user_topics = {}  # user_id -> {topic_name: topic_data}
    
    def add_topic(self, user_id: int, name: str, posts: List[str], queries: List[str]):
        if user_id not in self.user_topics:
            self.user_topics[user_id] = {}
        
        topic_key = f"custom_{name.lower().replace(' ', '_')}"
        self.user_topics[user_id][topic_key] = {
            "name": f"✨ {name}",
            "emoji": "✨",
            "posts": posts,
            "image_queries": queries,
            "is_custom": True
        }
        return topic_key
    
    def get_user_topics(self, user_id: int):
        return self.user_topics.get(user_id, {})
    
    def get_all_topics(self, user_id: int, tariff: str):
        all_topics = dict(TOPICS)
        custom = self.get_user_topics(user_id)
        all_topics.update(custom)
        
        # Для бесплатного тарифа ограничиваем количество тем
        if tariff == "free":
            # Показываем только базовые темы + 2 пользовательские
            base_topics = list(TOPICS.keys())[:5]
            return {k: v for k, v in all_topics.items() if k in base_topics or k in custom}
        
        return all_topics

custom_topics_manager = CustomTopics()

# ==================== РАЗМЕРЫ ИЗОБРАЖЕНИЙ ====================
IMAGE_SIZES = {
    "small": "400x300",
    "medium": "800x600", 
    "large": "1200x800",
    "hd": "1920x1080"
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
class BotData:
    def __init__(self):
        self.users = {}
        self.channels = {}
        self.auto_posting = {}
        self.posting_tasks = {}
        self.user_tariffs = {}
        self.daily_post_counts = {}
        self.image_cache = {}
        self.user_image_size = {}  # user_id -> size
        
    def init_user(self, user_id: int, username: str, first_name: str):
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "username": username,
                "first_name": first_name,
                "joined": datetime.now(),
                "last_active": datetime.now()
            }
            self.user_tariffs[user_id] = "free"
            self.channels[user_id] = []
            self.daily_post_counts[user_id] = {"date": datetime.now().date(), "count": 0}
            self.user_image_size[user_id] = "medium"
    
    def add_channel(self, user_id: int, channel_id: str, channel_title: str):
        tariff = self.user_tariffs.get(user_id, "free")
        max_channels = TARIFFS[tariff]["max_channels"]
        
        if len(self.channels.get(user_id, [])) >= max_channels:
            return False, f"Достигнут лимит каналов для тарифа {TARIFFS[tariff]['name']}"
        
        if user_id not in self.channels:
            self.channels[user_id] = []
        
        for ch in self.channels[user_id]:
            if ch["id"] == channel_id:
                return False, "Этот канал уже добавлен"
        
        self.channels[user_id].append({
            "id": channel_id,
            "title": channel_title,
            "added": datetime.now()
        })
        return True, "Канал успешно добавлен!"
    
    def get_channels(self, user_id: int):
        return self.channels.get(user_id, [])
    
    def set_auto_posting(self, channel_id: str, user_id: int, topic: str, interval: int, is_active: bool = False):
        self.auto_posting[channel_id] = {
            "user_id": user_id,
            "topic": topic,
            "interval": interval,
            "is_active": is_active,
            "last_post": datetime.now(),
            "channel_title": self.get_channel_title(user_id, channel_id),
            "include_images": True,
            "use_extended": False,
            "topic_type": "crypto"  # тип темы
        }
        return True
    
    def get_auto_settings(self, channel_id: str):
        return self.auto_posting.get(channel_id)
    
    def toggle_auto(self, channel_id: str, is_active: bool):
        if channel_id in self.auto_posting:
            self.auto_posting[channel_id]["is_active"] = is_active
            if is_active:
                self.auto_posting[channel_id]["last_post"] = datetime.now()
            return True
        return False
    
    def get_channel_title(self, user_id: int, channel_id: str) -> str:
        for ch in self.channels.get(user_id, []):
            if ch["id"] == channel_id:
                return ch["title"]
        return channel_id
    
    def can_post(self, user_id: int) -> bool:
        tariff = self.user_tariffs.get(user_id, "free")
        max_posts = TARIFFS[tariff]["max_posts_per_day"]
        
        today = datetime.now().date()
        if user_id not in self.daily_post_counts:
            self.daily_post_counts[user_id] = {"date": today, "count": 0}
        
        if self.daily_post_counts[user_id]["date"] != today:
            self.daily_post_counts[user_id] = {"date": today, "count": 0}
        
        if self.daily_post_counts[user_id]["count"] >= max_posts:
            return False
        
        self.daily_post_counts[user_id]["count"] += 1
        return True
    
    def get_image_size(self, user_id: int) -> str:
        tariff = self.user_tariffs.get(user_id, "free")
        size_key = TARIFFS[tariff]["image_size"]
        return IMAGE_SIZES.get(size_key, "800x600")

bot_data = BotData()

# ==================== ПОИСК КАРТИНОК ====================
class ImageFinder:
    @staticmethod
    async def search_image(query: str, size: str = "800x600"):
        """Поиск картинки с нужным размером"""
        try:
            width, height = size.split('x')
            async with aiohttp.ClientSession() as session:
                url = f"https://picsum.photos/{width}/{height}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return url
        except:
            pass
        return None
    
    @staticmethod
    async def get_random_image(topic: str, user_id: int):
        """Получить случайную картинку по теме с учетом размера"""
        size = bot_data.get_image_size(user_id)
        
        # Получаем все доступные темы
        tariff = bot_data.user_tariffs.get(user_id, "free")
        all_topics = custom_topics_manager.get_all_topics(user_id, tariff)
        
        topic_data = all_topics.get(topic, TOPICS.get(topic, TOPICS["nft"]))
        queries = topic_data.get("image_queries", ["art"])
        query = random.choice(queries)
        
        return await ImageFinder.search_image(query, size)

bot_images = ImageFinder()

# ==================== АВТОПОСТИНГ С КАРТИНКАМИ ====================
async def auto_posting_worker(bot, channel_id: str):
    """Фоновый поток для автопостинга"""
    while True:
        try:
            settings = bot_data.get_auto_settings(channel_id)
            if not settings or not settings.get("is_active", False):
                break
            
            current_time = datetime.now()
            last_post = settings.get("last_post", datetime.now() - timedelta(days=1))
            interval_seconds = settings.get("interval", 60)
            
            time_diff = (current_time - last_post).total_seconds()
            
            if time_diff >= interval_seconds:
                topic = settings.get("topic", "nft")
                user_id = settings.get("user_id")
                
                # Получаем все доступные темы пользователя
                tariff = bot_data.user_tariffs.get(user_id, "free")
                all_topics = custom_topics_manager.get_all_topics(user_id, tariff)
                
                topic_data = all_topics.get(topic, TOPICS.get(topic, TOPICS["nft"]))
                posts = topic_data.get("posts", TOPICS["nft"]["posts"])
                
                if posts:
                    post_text = random.choice(posts)
                    
                    footer = f"\n\n✨ Подписывайтесь! 🔥 Еще больше интересного контента по теме!"
                    full_text = post_text + footer
                    
                    try:
                        if not bot_data.can_post(user_id):
                            await asyncio.sleep(300)
                            continue
                        
                        tariff = bot_data.user_tariffs.get(user_id, "free")
                        
                        # Добавляем картинку для BASIC и PRO
                        if tariff in ["basic", "pro"] and settings.get("include_images", True):
                            image_url = await bot_images.get_random_image(topic, user_id)
                            if image_url:
                                try:
                                    await bot.send_photo(chat_id=channel_id, photo=image_url, caption=full_text)
                                    logger.info(f"✅ Автопост с картинкой в {channel_id}")
                                except:
                                    await bot.send_message(chat_id=channel_id, text=full_text)
                            else:
                                await bot.send_message(chat_id=channel_id, text=full_text)
                        else:
                            await bot.send_message(chat_id=channel_id, text=full_text)
                        
                        settings["last_post"] = datetime.now()
                        logger.info(f"✅ Автопост отправлен в канал {channel_id}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
            
            await asyncio.sleep(min(interval_seconds, 30))
            
        except Exception as e:
            logger.error(f"Ошибка в авто-постинге: {e}")
            await asyncio.sleep(60)

async def start_auto_posting(bot, channel_id: str):
    if channel_id in bot_data.posting_tasks:
        old_task = bot_data.posting_tasks[channel_id]
        if not old_task.done():
            old_task.cancel()
    
    task = asyncio.create_task(auto_posting_worker(bot, channel_id))
    bot_data.posting_tasks[channel_id] = task
    return task

async def stop_auto_posting(channel_id: str):
    if channel_id in bot_data.posting_tasks:
        task = bot_data.posting_tasks[channel_id]
        if not task.done():
            task.cancel()
        del bot_data.posting_tasks[channel_id]

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("🔍 Поиск картинок", callback_data="search_images")],
        [InlineKeyboardButton("✨ Создать свою тему", callback_data="create_topic")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🖼 Размер картинок", callback_data="image_size_menu")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(user_id: int, channel_id: str = None):
    tariff = bot_data.user_tariffs.get(user_id, "free")
    all_topics = custom_topics_manager.get_all_topics(user_id, tariff)
    
    keyboard = []
    for topic_key, topic_data in all_topics.items():
        callback = f"set_topic_{channel_id}_{topic_key}" if channel_id else f"topic_{topic_key}"
        keyboard.append([
            InlineKeyboardButton(f"{topic_data.get('emoji', '📌')} {topic_data['name']}", callback_data=callback)
        ])
    
    if channel_id:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(keyboard)

async def get_image_size_keyboard():
    keyboard = [
        [InlineKeyboardButton("🖼 Маленький (400x300)", callback_data="size_small")],
        [InlineKeyboardButton("🖼 Средний (800x600)", callback_data="size_medium")],
        [InlineKeyboardButton("🖼 Большой (1200x800)", callback_data="size_large")],
        [InlineKeyboardButton("🖼 HD (1920x1080) - PRO", callback_data="size_hd")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("10 секунд (PRO)", callback_data=f"interval_{channel_id}_10")],
        [InlineKeyboardButton("30 секунд (BASIC)", callback_data=f"interval_{channel_id}_30")],
        [InlineKeyboardButton("1 минута", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("5 минут", callback_data=f"interval_{channel_id}_300")],
        [InlineKeyboardButton("10 минут", callback_data=f"interval_{channel_id}_600")],
        [InlineKeyboardButton("30 минут", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_3600")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== СОЗДАНИЕ СВОЕЙ ТЕМЫ ====================
async def create_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tariff = bot_data.user_tariffs.get(user_id, "free")
    
    if tariff == "free":
        await query.edit_message_text(
            "❌ *Создание своих тем доступно на тарифах BASIC и PRO*\n\n"
            "Перейдите на более высокий тариф в меню 'Тарифы'",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        "✨ *Создание новой темы контента*\n\n"
        "Шаг 1 из 3:\n"
        "📝 *Введите название темы*\n"
        "Примеры: Космос, Автомобили, Финансы\n\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    return WAITING_TOPIC_NAME

async def receive_topic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic_name = update.message.text.strip()
    context.user_data['new_topic_name'] = topic_name
    
    await update.message.reply_text(
        f"✨ *Тема: {topic_name}*\n\n"
        "Шаг 2 из 3:\n"
        "📝 *Введите 5-10 постов для этой темы*\n"
        "Каждый пост должен быть на новой строке\n"
        "Пример:\n"
        "Пост 1 о теме\n"
        "Пост 2 о теме\n"
        "Пост 3 о теме\n\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    return WAITING_TOPIC_POSTS

async def receive_topic_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts_text = update.message.text.strip()
    posts = [p.strip() for p in posts_text.split('\n') if p.strip()]
    
    if len(posts) < 3:
        await update.message.reply_text("❌ Минимум 3 поста. Добавьте еще и отправьте заново")
        return WAITING_TOPIC_POSTS
    
    context.user_data['new_topic_posts'] = posts
    
    await update.message.reply_text(
        f"✨ *Посты получены! ({len(posts)} постов)*\n\n"
        "Шаг 3 из 3:\n"
        "🔍 *Введите ключевые слова для поиска картинок*\n"
        "Через запятую (3-5 слов)\n"
        "Пример: космос, планеты, звезды, галактика\n\n"
        "Используйте /cancel для отмены",
        parse_mode='Markdown'
    )
    return WAITING_TOPIC_QUERIES

async def receive_topic_queries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    queries_text = update.message.text.strip()
    queries = [q.strip() for q in queries_text.split(',') if q.strip()]
    
    if len(queries) < 2:
        await update.message.reply_text("❌ Минимум 2 ключевых слова. Отправьте заново")
        return WAITING_TOPIC_QUERIES
    
    topic_name = context.user_data['new_topic_name']
    posts = context.user_data['new_topic_posts']
    
    # Сохраняем тему
    topic_key = custom_topics_manager.add_topic(user_id, topic_name, posts, queries)
    
    await update.message.reply_text(
        f"✅ *Тема '{topic_name}' успешно создана!*\n\n"
        f"📝 Постов: {len(posts)}\n"
        f"🔍 Ключевые слова: {', '.join(queries)}\n\n"
        f"Теперь вы можете использовать эту тему в автопостинге!",
        parse_mode='Markdown'
    )
    
    # Очищаем данные
    context.user_data.clear()
    
    # Показываем главное меню
    keyboard = await get_main_keyboard(user_id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
    return ConversationHandler.END

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга в Telegram каналы*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• 🔍 Поиск и публикация картинок\n"
        f"• ✨ Создание своих тем с уникальным контентом\n"
        f"• 🖼 Настройка размера картинок (от 400x300 до HD)\n"
        f"• ⚙️ Автопостинг с интервалом от 10 сек\n"
        f"• 🎯 10+ готовых тем (NFT, Telegram, AI, Crypto и др.)\n\n"
        f"🎁 *Все тарифы бесплатны!*\n\n"
        f"💡 *Новые темы:* NFT Art, Crypto Gaming, Telegram, AI, NFT Collections"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def image_size_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    current_size = bot_data.get_image_size(query.from_user.id)
    size_name = [k for k, v in IMAGE_SIZES.items() if v == current_size][0] if current_size else "medium"
    
    text = (
        f"🖼 *Настройка размера изображений*\n\n"
        f"Текущий размер: {size_name.upper()} ({current_size})\n\n"
        f"Выберите желаемый размер:"
    )
    
    keyboard = await get_image_size_keyboard()
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def set_image_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    size_key = query.data.replace("size_", "")
    user_id = query.from_user.id
    tariff = bot_data.user_tariffs.get(user_id, "free")
    
    if size_key == "hd" and tariff != "pro":
        await query.edit_message_text("❌ HD размер доступен только на PRO тарифе")
        return
    
    size_map = {
        "small": "400x300",
        "medium": "800x600", 
        "large": "1200x800",
        "hd": "1920x1080"
    }
    
    new_size = size_map.get(size_key, "800x600")
    
    await query.edit_message_text(f"✅ Размер изображений изменен на {size_key.upper()} ({new_size})")
    await asyncio.sleep(1)
    
    keyboard = await get_main_keyboard(user_id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID канала или ссылку\n\n"
        "📝 Форматы:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "Отправьте ссылку:",
        parse_mode='Markdown'
    )
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    channel_id = channel_input
    if "t.me/" in channel_input:
        channel_id = "@" + channel_input.split("t.me/")[-1]
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_id)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал")
            return
        
        success, message = bot_data.add_channel(user.id, str(chat.id), chat.title)
        
        if success:
            await update.message.reply_text(
                f"✅ *{message}*\n\n"
                f"📢 Название: {chat.title}\n"
                f"🆔 ID: {chat.id}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {message}")
        
        context.user_data['adding_channel'] = False
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='Markdown')

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Сначала добавьте канал")
        return
    
    keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"post_to_{ch['id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(
        "📝 *Выберите канал для публикации:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['post_channel'] = channel_id
    
    keyboard = [
        [InlineKeyboardButton("📝 Текст", callback_data="post_type_text")],
        [InlineKeyboardButton("🖼 Текст + картинка", callback_data="post_type_image")],
        [InlineKeyboardButton("🔙 Назад", callback_data="write_post")]
    ]
    await query.edit_message_text(
        "📝 *Выберите тип поста:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_post_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    post_type = query.data.replace("post_type_", "")
    context.user_data['post_type'] = post_type
    
    if post_type == "text":
        await query.edit_message_text("📝 *Напишите текст поста:*", parse_mode='Markdown')
        context.user_data['awaiting_post'] = True
    elif post_type == "image":
        await query.edit_message_text(
            "🖼 *Отправьте пост с картинкой*\n\n"
            "Отправьте фото с подписью",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_image_post'] = True

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка")
        return
    
    message_text = update.message.text
    
    try:
        await context.bot.send_message(chat_id=channel_id, text=message_text)
        await update.message.reply_text("✅ Пост успешно опубликован!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data['awaiting_post'] = False
    context.user_data['post_channel'] = None
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def handle_image_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка")
        return
    
    tariff = bot_data.user_tariffs.get(user.id, "free")
    if tariff not in ["basic", "pro"]:
        await update.message.reply_text("❌ Посты с картинками доступны на BASIC и PRO тарифах")
        return
    
    caption = update.message.caption or "📸 Новый пост!"
    photo = update.message.photo[-1]
    
    try:
        await context.bot.send_photo(chat_id=channel_id, photo=photo.file_id, caption=caption)
        await update.message.reply_text("✅ Пост с картинкой опубликован!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data['awaiting_image_post'] = False
    context.user_data['post_channel'] = None
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Сначала добавьте канал")
        return
    
    keyboard = []
    for ch in channels:
        settings = bot_data.get_auto_settings(ch['id'])
        status = "✅" if settings and settings.get("is_active") else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {ch['title']}", callback_data=f"auto_channel_{ch['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - активен\n"
        "❌ - неактивен",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def configure_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    settings = bot_data.get_auto_settings(channel_id)
    user_id = query.from_user.id
    
    if settings:
        is_active = settings.get("is_active", False)
        interval = settings.get("interval", 60)
        topic = settings.get("topic", "nft")
        include_images = settings.get("include_images", True)
        
        # Получаем все темы пользователя
        tariff = bot_data.user_tariffs.get(user_id, "free")
        all_topics = custom_topics_manager.get_all_topics(user_id, tariff)
        topic_data = all_topics.get(topic, TOPICS.get(topic, TOPICS["nft"]))
        topic_name = topic_data["name"]
    else:
        is_active = False
        interval = 60
        topic = "nft"
        include_images = True
        topic_name = "NFT Искусство"
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    interval_display = f"{interval // 60} мин" if interval >= 60 else f"{interval} сек"
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval_display}\n"
        f"🖼 Картинки: {'✅ Да' if include_images else '❌ Нет'}\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Включить/Выключить", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("🎯 Выбрать тему", callback_data=f"select_topic_auto_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("🖼 Картинки", callback_data=f"toggle_images_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_topic_for_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_auto_", "")
    context.user_data['topic_channel'] = channel_id
    
    keyboard = await get_topics_keyboard(query.from_user.id, channel_id)
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*\n\n"
        "🎨 NFT Искусство | 📱 Telegram | ₿ Криптовалюта\n"
        "🤖 ИИ | 🖼 NFT Коллекции | 🎮 Crypto Gaming\n"
        "✨ Свои темы - ваши уникальные посты!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic = "_".join(parts[3:])  # Для составных ключей
    user_id = query.from_user.id
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["topic"] = topic
    else:
        bot_data.set_auto_posting(channel_id, user_id, topic, 60, False)
    
    # Получаем название темы
    tariff = bot_data.user_tariffs.get(user_id, "free")
    all_topics = custom_topics_manager.get_all_topics(user_id, tariff)
    topic_data = all_topics.get(topic, TOPICS.get(topic, TOPICS["nft"]))
    topic_name = topic_data["name"]
    
    await query.edit_message_text(f"✅ Тема установлена: {topic_name}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if not settings:
        await query.edit_message_text("❌ Сначала выберите тему и интервал")
        return
    
    is_active = not settings.get("is_active", False)
    
    if is_active:
        tariff = bot_data.user_tariffs.get(settings['user_id'], "free")
        min_interval = TARIFFS[tariff]["min_interval"]
        current_interval = settings.get("interval", 60)
        
        if current_interval < min_interval:
            await query.edit_message_text(f"❌ Для вашего тарифа минимальный интервал: {min_interval} сек")
            return
        
        bot_data.toggle_auto(channel_id, True)
        await start_auto_posting(context.bot, channel_id)
        await query.edit_message_text(f"✅ Автопостинг ВКЛЮЧЕН")
    else:
        bot_data.toggle_auto(channel_id, False)
        await stop_auto_posting(channel_id)
        await query.edit_message_text(f"❌ Автопостинг ВЫКЛЮЧЕН")
    
    await asyncio.sleep(2)
    await configure_auto(update, context)

async def toggle_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_images_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if settings:
        settings["include_images"] = not settings.get("include_images", True)
        status = "включены" if settings["include_images"] else "выключены"
        await query.edit_message_text(f"🖼 Картинки {status}")
    
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    keyboard = await get_interval_keyboard(channel_id)
    await query.edit_message_text("⏱ *Выберите интервал:*", parse_mode='Markdown', reply_markup=keyboard)

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    user_id = query.from_user.id
    
    tariff = bot_data.user_tariffs.get(user_id, "free")
    min_interval = TARIFFS[tariff]["min_interval"]
    
    if interval < min_interval:
        await query.edit_message_text(f"❌ Для вашего тарифа минимальный интервал: {min_interval} сек")
        await asyncio.sleep(2)
        await change_interval(update, context)
        return
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["interval"] = interval
    else:
        bot_data.set_auto_posting(channel_id, user_id, "nft", interval, False)
    
    interval_display = f"{interval // 60} мин" if interval >= 60 else f"{interval} сек"
    await query.edit_message_text(f"✅ Интервал установлен: {interval_display}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def search_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff = bot_data.user_tariffs.get(query.from_user.id, "free")
    if tariff != "pro":
        await query.edit_message_text("❌ Поиск картинок доступен только на PRO тарифе")
        return
    
    await query.edit_message_text(
        "🔍 *Поиск картинок*\n\n"
        "Отправьте ключевое слово для поиска:\n"
        "Пример: `кот`, `природа`, `технологии`\n\n"
        "Размер картинок зависит от вашего тарифа",
        parse_mode='Markdown'
    )
    context.user_data['searching_image'] = True

async def handle_image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query_text = update.message.text.strip()
    
    await update.message.reply_text(f"🔍 Ищу картинки по запросу: {query_text}...")
    
    size = bot_data.get_image_size(user.id)
    image_url = await bot_images.search_image(query_text, size)
    
    if image_url:
        channels = bot_data.get_channels(user.id)
        if channels:
            keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"send_search_{ch['id']}_{query_text}")] for ch in channels[:5]]
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
            
            await update.message.reply_photo(photo=image_url, caption=f"🔍 Результат поиска: {query_text}\n\nВыберите канал для публикации:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_photo(photo=image_url, caption=f"🔍 Результат поиска: {query_text}")
    else:
        await update.message.reply_text("❌ Не удалось найти картинку")
    
    context.user_data['searching_image'] = False

async def send_search_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    search_query = "_".join(parts[3:])
    
    size = bot_data.get_image_size(query.from_user.id)
    image_url = await bot_images.search_image(search_query, size)
    
    if image_url:
        try:
            await context.bot.send_photo(chat_id=channel_id, photo=image_url, caption=f"🖼 Поиск: {search_query}\n\n✨ Подписывайтесь на канал!")
            await query.edit_message_text(f"✅ Картинка отправлена в канал!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    else:
        await query.edit_message_text("❌ Не удалось найти картинку")
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_tariff = bot_data.user_tariffs.get(user_id, "free")
    
    text = "💎 *Доступные тарифы*\n\n"
    for tariff_key, tariff_info in TARIFFS.items():
        is_current = "✅ *ТЕКУЩИЙ* " if tariff_key == current_tariff else ""
        text += f"{is_current}{tariff_info['name']}\n"
        text += f"⏱ Мин. интервал: {tariff_info['min_interval']} сек\n"
        text += f"📢 Макс. каналов: {tariff_info['max_channels']}\n"
        text += f"📝 Постов в день: {tariff_info['max_posts_per_day']}\n"
        text += f"🖼 Размер фото: {tariff_info['image_size'].upper()}\n"
        text += "✨ Возможности:\n"
        for feature in tariff_info['features']:
            text += f"  {feature}\n"
        text += "\n"
    
    text += "🎁 *Все тарифы полностью бесплатны!*"
    
    keyboard = [[InlineKeyboardButton(tariff_info['name'], callback_data=f"select_tariff_{key}")] 
                for key, tariff_info in TARIFFS.items()]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("select_tariff_", "")
    user_id = query.from_user.id
    
    bot_data.user_tariffs[user_id] = tariff_key
    
    await query.edit_message_text(
        f"✅ *Тариф обновлен!*\n\n"
        f"Ваш тариф: {TARIFFS[tariff_key]['name']}\n\n"
        f"Теперь доступны новые возможности!",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(user_id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot_data.users.get(user_id, {})
    tariff = bot_data.user_tariffs.get(user_id, "free")
    channels = bot_data.get_channels(user_id)
    custom_topics = custom_topics_manager.get_user_topics(user_id)
    
    active_auto = sum(1 for ch in channels if bot_data.get_auto_settings(ch['id']) and bot_data.get_auto_settings(ch['id']).get("is_active"))
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 Имя: {user.get('first_name', 'Unknown')}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n"
        f"📢 Каналов: {len(channels)}/{TARIFFS[tariff]['max_channels']}\n"
        f"✨ Своих тем: {len(custom_topics)}\n"
        f"⚙️ Активных автопостингов: {active_auto}\n"
        f"🖼 Размер фото: {bot_data.get_image_size(user_id)}\n"
        f"📅 В системе с: {user.get('joined', datetime.now()).strftime('%d.%m.%Y')}\n\n"
        f"У вас есть уникальные темы! Создавайте свои в меню"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    channels = bot_data.get_channels(user_id)
    auto_settings = bot_data.auto_posting
    
    auto_for_user = [s for s in auto_settings.values() if s.get("user_id") == user_id]
    active_auto = [s for s in auto_for_user if s.get("is_active")]
    
    text = (
        f"📊 *Статистика*\n\n"
        f"📢 Всего каналов: {len(channels)}\n"
        f"⚙️ Настроено автопостингов: {len(auto_for_user)}\n"
        f"✅ Активных автопостингов: {len(active_auto)}\n\n"
        f"📈 Сегодня опубликовано: {bot_data.daily_post_counts.get(user_id, {}).get('count', 0)} постов\n\n"
        f"💡 *Рекомендации:*\n"
        f"• Создавайте свои темы для уникального контента\n"
        f"• Используйте PRO тариф для HD картинок\n"
        f"• Для лучшего охвата ставьте интервал 30-60 мин"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено")
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "write_post":
        await write_post(update, context)
    elif data == "search_images":
        await search_images(update, context)
    elif data == "create_topic":
        await create_topic_start(update, context)
    elif data == "my_channels":
        keyboard = await get_channels_keyboard(query.from_user.id)
        await query.edit_message_text("📢 *Ваши каналы*", parse_mode='Markdown', reply_markup=keyboard)
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "image_size_menu":
        await image_size_menu(update, context)
    elif data.startswith("size_"):
        await set_image_size(update, context)
    elif data == "help":
        help_text = (
            "ℹ️ *Помощь*\n\n"
            "📋 *Новые функции:*\n"
            "• ✨ Создание своих тем с уникальными постами\n"
            "• 🖼 4 размера картинок (от 400x300 до HD)\n"
            "• 🎨 NFT Art, NFT Collections, Crypto Gaming\n"
            "• 📱 Telegram продвижение и монетизация\n"
            "• 🤖 Искусственный Интеллект и нейросети\n"
            "• ₿ Криптовалюта и NFT\n\n"
            "🎯 *Как создать свою тему:*\n"
            "1. Нажмите 'Создать свою тему'\n"
            "2. Введите название\n"
            "3. Напишите 5-10 уникальных постов\n"
            "4. Укажите ключевые слова для картинок\n\n"
            "💡 *Советы:*\n"
            "• Для HD картинок нужен PRO тариф\n"
            "• Свои темы доступны на BASIC и PRO\n"
            "• Посты не повторяются - уникальный контент"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    elif data.startswith("post_to_"):
        await send_post(update, context)
    elif data.startswith("post_type_"):
        await handle_post_type(update, context)
    elif data.startswith("auto_channel_"):
        await configure_auto(update, context)
    elif data.startswith("select_topic_auto_"):
        await select_topic_for_auto(update, context)
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    elif data.startswith("toggle_auto_"):
        await toggle_auto(update, context)
    elif data.startswith("toggle_images_"):
        await toggle_images(update, context)
    elif data.startswith("change_interval_"):
        await change_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)
    elif data.startswith("send_search_"):
        await send_search_image(update, context)

async def get_channels_keyboard(user_id: int):
    channels = bot_data.get_channels(user_id)
    keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"channel_{ch['id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # ConversationHandler для создания темы
    create_topic_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_topic_start, pattern="^create_topic$")],
        states={
            WAITING_TOPIC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_name)],
            WAITING_TOPIC_POSTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_posts)],
            WAITING_TOPIC_QUERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_queries)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(create_topic_handler)
    
    # Обработчики
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
        else (handle_post(u, c) if c.user_data.get('awaiting_post')
        else (handle_image_search(u, c) if c.user_data.get('searching_image')
        else None))
    ))
    
    application.add_handler(MessageHandler(
        filters.PHOTO,
        lambda u, c: handle_image_post(u, c) if c.user_data.get('awaiting_image_post') else None
    ))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот для автопостинга запущен!")
    logger.info("✅ 10+ тем: NFT Art, NFT Коллекции, Telegram, AI, Crypto Gaming")
    logger.info("✨ Создание своих тем с уникальными постами")
    logger.info("🖼 4 размера картинок от 400x300 до HD")
    logger.info("⚡ Интервал автопостинга от 10 секунд")
    logger.info("💎 Все тарифы бесплатны!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
