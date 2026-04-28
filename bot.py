import asyncio
import logging
import time
import random
import aiohttp
import io
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 3,
        "min_interval": 60,
        "max_posts_per_day": 100,
        "features": ["✅ 3 канала", "✅ Интервал от 1 мин", "✅ 100 постов/день", "✅ Текстовые посты"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 10,
        "min_interval": 30,
        "max_posts_per_day": 500,
        "features": ["✅ 10 каналов", "✅ Интервал от 30 сек", "✅ 500 постов/день", "✅ Картинки", "✅ Репосты"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 30,
        "min_interval": 10,
        "max_posts_per_day": 2000,
        "features": ["✅ 30 каналов", "✅ Интервал от 10 сек", "✅ 2000 постов/день", "✅ HD картинки", 
                    "✅ Поиск картинок", "✅ Видео", "✅ Репосты", "✅ ИИ контент"]
    }
}

# ==================== ТЕМЫ С ПОСТАМИ И КАРТИНКАМИ ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии",
        "emoji": "💻",
        "posts": [
            "🚀 **Новый прорыв в AI**\n\nИскусственный интеллект GPT-5 обучили на 100 триллионах параметров. Нейросеть способна создавать полноценные видео и решать сложные научные задачи.\n\n#технологии #AI #нейросети",
            "📱 **Смартфоны будущего**\n\nГибкие дисплеи, 200-мегапиксельные камеры, зарядка за 10 минут - технологии 2025 года уже здесь!\n\n#смартфоны #технологии #гаджеты",
            "🌐 **Квантовые компьютеры**\n\nGoogle объявила о создании квантового компьютера в 1000 кубитов. Это открывает новую эру в вычислениях!\n\n#кванты #технологии #наука",
            "💡 **Илон Маск показал Neuralink 2.0**\n\nНейрочип позволяет управлять техникой силой мысли и восстанавливать зрение. Уже начались испытания на людях.\n\n#neuralink #технологии #илонмаск",
            "🔋 **Супер-аккумуляторы**\n\nКитайские ученые создали батарею, которая заряжается за 30 секунд и держит заряд месяц!\n\n#аккумуляторы #технологии #энергия"
        ],
        "image_queries": ["technology", "AI", "smartphone", "robot", "computer"]
    },
    "business": {
        "name": "📊 Бизнес",
        "emoji": "📊",
        "posts": [
            "💰 **Как заработать первый миллион в 2025**\n\nТоп-5 ниш для стартапа: AI-услуги, экопродукты, онлайн-образование, финтех, здоровье.\n\n#бизнес #заработок #стартап",
            "📈 **Криптовалюта снова растет**\n\nБиткоин достиг $150,000. Эксперты прогнозируют дальнейший рост до $200,000.\n\n#биткоин #криптовалюта #инвестиции",
            "🏢 **Как открыть бизнес с нуля**\n\nПошаговая инструкция: регистрация, поиск клиентов, маркетинг. Реальные кейсы и советы.\n\n#бизнесидеи #стартап #предпринимательство",
            "💼 **Фриланс 2025**\n\nТоп-10 востребованных профессий: AI-инженеры, data scientists, дизайнеры нейросетей, копирайтеры.\n\n#фриланс #работа #заработок",
            "📊 **Секреты успешных предпринимателей**\n\nКак Маск, Безос и Цукерберг начинали. Уроки и инсайты от миллиардеров.\n\n#успех #бизнес #мотивация"
        ],
        "image_queries": ["business", "money", "startup", "success", "entrepreneur"]
    },
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "posts": [
            "🏃‍♂️ **10 минут для здоровья**\n\nПростая утренняя зарядка, которая изменит вашу жизнь. Всего 10 минут в день и вы полны энергии!\n\n#здоровье #спорт #фитнес",
            "🥗 **Правильное питание**\n\n10 продуктов, которые нужно есть каждый день. Простые рецепты для здоровья и долголетия.\n\n#питание #зож #рецепты",
            "💪 **Как сохранить молодость**\n\nСекреты долголетия от 100-летних долгожителей. Правила, которые работают.\n\n#молодость #здоровье #долголетие",
            "🧘‍♀️ **Медитация для начинающих**\n\nВсего 5 минут в день снижают стресс на 70%. Простая техника для спокойствия.\n\n#медитация #релакс #стресс",
            "😴 **Идеальный сон**\n\nКак спать 6 часов и высыпаться. Научный подход к качественному отдыху.\n\n#сон #здоровье #режим"
        ],
        "image_queries": ["health", "fitness", "meditation", "healthy food", "sport"]
    },
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "posts": [
            "📖 **Как выучить английский за 3 месяца**\n\nМетодика полиглотов: учим 20 слов в день, смотрим сериалы, разговариваем с носителями.\n\n#английский #обучение #языки",
            "🧠 **Скорочтение и память**\n\nТехники, которые увеличат скорость чтения в 3 раза и улучшат запоминание на 80%.\n\n#скорочтение #память #развитие",
            "💡 **Как стать экспертом в любой области**\n\nПравило 10000 часов, методика «интенсивного погружения», лучшие курсы.\n\n#эксперт #обучение #карьера",
            "🎓 **Топ-10 бесплатных курсов**\n\nЛучшие онлайн-курсы от Harvard, MIT, Stanford с сертификатами. Бесплатно!\n\n#образование #курсы #учеба",
            "📚 **Книги, которые изменят жизнь**\n\n50 книг по саморазвитию, бизнесу, психологии. Маст-рид для успешного человека.\n\n#книги #саморазвитие #библиотека"
        ],
        "image_queries": ["education", "study", "book", "learning", "school"]
    },
    "entertainment": {
        "name": "🎬 Развлечения",
        "emoji": "🎬",
        "posts": [
            "🍿 **Топ-10 фильмов 2024**\n\nЛучшие фильмы года: «Оппенгеймер», «Барби», «Дюна 2». Список обязательных к просмотру.\n\n#фильмы #кино #топ2024",
            "🎮 **Новые игры 2025**\n\nGTA 6, The Witcher 4, новый God of War. Обзор самых ожидаемых релизов.\n\n#игры #гейминг #новинки",
            "🎵 **Музыкальные хиты**\n\nТоп-10 песен, которые взорвали чарты. Плейлист для отличного настроения.\n\n#музыка #хиты #плейлист",
            "😂 **Самые смешные мемы**\n\nПодборка мемов, которые разорвали интернет. Улыбнитесь!\n\n#мемы #юмор #смех",
            "📺 **Лучшие сериалы**\n\nЧто посмотреть вечером: «Корона», «Ведьмак», «Очень странные дела». Рейтинг IMDB.\n\n#сериалы #кино #рейтинг"
        ],
        "image_queries": ["cinema", "game", "music", "funny meme", "movie"]
    },
    "lifestyle": {
        "name": "🌟 Лайфстайл",
        "emoji": "🌟",
        "posts": [
            "✨ **Утренние ритуалы успешных людей**\n\nКак начинают день Опра, Тим Кук, Ричард Брэнсон. Их секреты продуктивности.\n\n#утро #продуктивность #успех",
            "🏡 **Как создать идеальный дом**\n\n10 советов по дизайну интерьера, которые сделают ваш дом уютным и стильным.\n\n#дизайн #интерьер #уют",
            "💃 **Мода 2025**\n\nГлавные тренды года: цвета, фасоны, аксессуары. Что будет в гардеробе модников.\n\n#мода #стиль #тренды",
            "✈️ **Путешествие мечты**\n\nТоп-10 мест, которые нужно посетить в 2025 году. Мальдивы, Исландия, Япония.\n\n#путешествия #отдых #мечта",
            "🎨 **Хобби для души**\n\nКак найти любимое дело, которое приносит радость и деньги. Идеи для творчества.\n\n#хобби #творчество #вдохновение"
        ],
        "image_queries": ["lifestyle", "travel", "fashion", "hobby", "inspiration"]
    },
    "science": {
        "name": "🔬 Наука",
        "emoji": "🔬",
        "posts": [
            "🚀 **Космические открытия**\n\nТелескоп Джеймс Уэбб нашел признаки жизни на экзопланете в 100 световых годах.\n\n#космос #наука #открытия",
            "🧬 **Генная инженерия**\n\nУченые научились редактировать гены для лечения рака. Прорыв в медицине!\n\n#генетика #медицина #наука",
            "🌍 **Изменение климата**\n\nПоследние данные: средняя температура выросла на 2 градуса. Что нас ждет?\n\n#климат #экология #наука",
            "🐾 **Новые виды животных**\n\nВ Амазонии открыты 100 новых видов. Удивительные создания природы.\n\n#животные #биология #открытия",
            "⚛️ **Физика будущего**\n\nФизики создали кротовую нору в квантовом компьютере. Путешествия во времени?\n\n#физика #кванты #наука"
        ],
        "image_queries": ["science", "space", "dna", "planet", "discovery"]
    },
    "psychology": {
        "name": "🧠 Психология",
        "emoji": "🧠",
        "posts": [
            "🤔 **Как читать мысли людей**\n\n10 психологических трюков, которые помогут понять собеседника. Язык тела, жесты, мимика.\n\n#психология #общение #эмоции",
            "💪 **Как победить страх**\n\nМетодики преодоления тревожности и стресса. Практические упражнения для уверенности.\n\n#страх #уверенность #психология",
            "❤️ **Секреты счастливых отношений**\n\nЧто говорят психологи о любви, доверии и гармонии. Как сохранить семью.\n\n#отношения #любовь #психология",
            "🧘 **Как стать счастливее**\n\nНаучные исследования: привычки счастливых людей. Простые шаги к радости.\n\n#счастье #психология #радость",
            "💭 **Психология успеха**\n\nПочему одни достигают целей, а другие нет. Ментальные установки миллионеров.\n\n#успех #мышление #психология"
        ],
        "image_queries": ["psychology", "brain", "mind", "happy", "success"]
    },
    "crypto": {
        "name": "₿ Криптовалюта",
        "emoji": "₿",
        "posts": [
            "₿ **Биткоин обновил максимум**\n\nПервая криптовалюта достигла $150,000. Что дальше? Прогнозы аналитиков.\n\n#биткоин #криптовалюта #инвестиции",
            "📈 **Альткоины, которые выстрелят**\n\nТоп-10 перспективных монет на 2025 год. Инвестируйте с умом.\n\n#альткоины #крипта #инвестиции",
            "💰 **Как заработать на крипте**\n\nСтратегии трейдинга, стейкинг, майнинг. Пошаговое руководство для новичков.\n\n#крипта #заработок #трейдинг",
            "🔒 **Безопасность криптокошелька**\n\nКак защитить свои монеты от хакеров. Лучшие практики хранения.\n\n#безопасность #кошелек #крипта",
            "🚀 **NFT снова в тренде**\n\nЦифровое искусство продается за миллионы. Как создать и продать свой NFT.\n\n#nft #искусство #крипта"
        ],
        "image_queries": ["bitcoin", "cryptocurrency", "blockchain", "nft", "trading"]
    },
    "marketing": {
        "name": "📢 Маркетинг",
        "emoji": "📢",
        "posts": [
            "📱 **Как продвигать Telegram канал**\n\n5 работающих способов набрать 10,000 подписчиков. Бесплатные методы.\n\n#маркетинг #tg #продвижение",
            "💰 **Instagram реклама 2025**\n\nНовые алгоритмы, форматы, бюджеты. Как получить клиентов дешево.\n\n#instagram #реклама #маркетинг",
            "📧 **Email маркетинг**\n\nКак собирать базу и продавать через письма. Конверсия 30% - реально!\n\n#email #маркетинг #продажи",
            "🎯 **Таргетинг**\n\nНастройка рекламы на ЦА. Ошибки новичков и как их избежать.\n\n#таргетинг #реклама #маркетинг",
            "📊 **Аналитика для бизнеса**\n\nКакие метрики важны. Как отслеживать ROI и увеличивать прибыль.\n\n#аналитика #бизнес #маркетинг"
        ],
        "image_queries": ["marketing", "social media", "advertising", "analytics", "business"]
    }
}

# Расширенные темы для PRO тарифа
EXTENDED_TOPICS = {
    "productivity": {
        "name": "⚡ Продуктивность",
        "emoji": "⚡",
        "posts": [
            "⚡ **Как работать по 4 часа и успевать все**\n\nМетодики тайм-менеджмента от мировых экспертов. Увеличьте эффективность на 300%.\n\n#продуктивность #работа #успех",
            "🎯 **Система GTD**\n\nGetting Things Done по Дэвиду Аллену. Полный разбор для максимальной продуктивности.\n\n#gtd #система #продуктивность",
            "📋 **Как ставить цели и достигать**\n\nSMART, OKR и другие методики. Пошаговый план к вашей мечте.\n\n#цели #план #успех",
            "🧠 **Управление энергией**\n\nКак не выгорать и сохранять высокую продуктивность целый день.\n\n#энергия #продуктивность #здоровье"
        ],
        "image_queries": ["productivity", "work", "goal", "success", "time management"]
    },
    "design": {
        "name": "🎨 Дизайн",
        "emoji": "🎨",
        "posts": [
            "🎨 **Тренды дизайна 2025**\n\nМинимализм, 3D, нейросети. Что актуально в UI/UX.\n\n#дизайн #тренды #uiux",
            "🖌️ **Как стать дизайнером с нуля**\n\nОбучение, портфолио, поиск клиентов. Реальный план.\n\n#дизайн #карьера #обучение",
            "🌟 **Лучшие инструменты дизайнера**\n\nFigma, Adobe, Canva. Что учить в 2025.\n\n#дизайн #инструменты #figma"
        ],
        "image_queries": ["design", "art", "creative", "modern design", "digital art"]
    }
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
            "use_extended": False
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

bot_data = BotData()

# ==================== ПОИСК КАРТИНОК ====================
class ImageFinder:
    @staticmethod
    async def search_image(query: str):
        """Поиск картинки по запросу"""
        # Unsplash API (бесплатный)
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://source.unsplash.com/featured/1200x800/?{query}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return url
        except:
            pass
        return None
    
    @staticmethod
    async def get_random_image(topic: str):
        """Получить случайную картинку по теме"""
        topic_data = TOPICS.get(topic, TOPICS["technology"])
        queries = topic_data.get("image_queries", ["nature"])
        query = random.choice(queries)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://picsum.photos/1200/800"
                async with session.get(url) as response:
                    if response.status == 200:
                        return url
        except:
            return None
        return None

bot_images = ImageFinder()

# ==================== АВТОПОСТИНГ С КАРТИНКАМИ ====================
async def auto_posting_worker(bot, channel_id: str):
    """Фоновый поток для автопостинга с картинками"""
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
                topic = settings.get("topic", "technology")
                topic_data = TOPICS.get(topic, TOPICS["technology"])
                posts = topic_data.get("posts", [])
                
                if posts:
                    post_text = random.choice(posts)
                    
                    # Добавляем призыв подписаться
                    footer = f"\n\n✨ Подписывайтесь! Еще больше интересного контента"
                    full_text = post_text + footer
                    
                    try:
                        user_id = settings.get("user_id")
                        tariff = bot_data.user_tariffs.get(user_id, "free")
                        
                        # Проверяем лимит постов
                        if not bot_data.can_post(user_id):
                            logger.warning(f"Лимит постов для пользователя {user_id} превышен")
                            await asyncio.sleep(300)
                            continue
                        
                        # Для PRO тарифа пробуем добавить картинку
                        if tariff == "pro" and settings.get("include_images", True):
                            image_url = await bot_images.get_random_image(topic)
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
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("🔄 Репосты", callback_data="reposts_menu")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard():
    keyboard = []
    for topic_key, topic_data in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(f"{topic_data['emoji']} {topic_data['name']}", callback_data=f"topic_{topic_key}")
        ])
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

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга в Telegram каналы с ИИ*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• 🔍 Поиск и публикация картинок\n"
        f"• ⚙️ Автопостинг с интервалом от 10 сек\n"
        f"• 🎯 10+ тем с готовыми постами\n"
        f"• 🖼 Автоматические картинки к постам\n"
        f"• 💎 Бесплатные тарифы с разными лимитами\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как администратора\n"
        f"2️⃣ Добавьте канал через кнопку 'Мои каналы'\n"
        f"3️⃣ Настройте автопостинг в меню\n\n"
        f"💡 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def search_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *Поиск картинок*\n\n"
        "Отправьте ключевое слово для поиска:\n"
        "Пример: `кот`, `природа`, `технологии`",
        parse_mode='Markdown'
    )
    context.user_data['searching_image'] = True

async def handle_image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.message.text.strip()
    
    # Проверяем тариф
    tariff = bot_data.user_tariffs.get(user.id, "free")
    if tariff != "pro":
        await update.message.reply_text("❌ Поиск картинок доступен только на PRO тарифе")
        context.user_data['searching_image'] = False
        return
    
    await update.message.reply_text(f"🔍 Ищу картинки по запросу: {query}...")
    
    # Ищем картинки
    channels = bot_data.get_channels(user.id)
    if not channels:
        await update.message.reply_text("❌ Сначала добавьте канал в меню 'Мои каналы'")
        context.user_data['searching_image'] = False
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"send_image_{ch['id']}_{query}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.message.reply_text(
        f"🔍 Найдены картинки по запросу: {query}\n\nВыберите канал для публикации:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['searching_image'] = False

async def send_image_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    search_query = parts[3]
    
    await query.edit_message_text(f"🖼 Ищу картинку по запросу '{search_query}'...")
    
    # Получаем картинку
    image_url = await bot_images.search_image(search_query)
    
    if image_url:
        try:
            await context.bot.send_photo(chat_id=channel_id, photo=image_url, caption=f"🖼 Поиск: {search_query}\n\n✨ Подписывайтесь на канал!")
            await query.edit_message_text(f"✅ Картинка успешно отправлена в канал!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    else:
        await query.edit_message_text("❌ Не удалось найти картинку")
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID канала или ссылку\n\n"
        "📝 Как получить ID:\n"
        "• `@channel_username`\n"
        "• `https://t.me/channel_username`\n\n"
        "Отправьте ссылку на канал:",
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
    
    # Показываем выбор типа поста
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
    context.user_data['post_type_selection'] = True

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
            "Отправьте фото с подписью или команду /cancel",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_image_post'] = True

async def handle_image_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка")
        return
    
    tariff = bot_data.user_tariffs.get(user.id, "free")
    if tariff != "pro":
        await update.message.reply_text("❌ Посты с картинками доступны только на PRO тарифе")
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
    
    if settings:
        is_active = settings.get("is_active", False)
        interval = settings.get("interval", 60)
        topic = settings.get("topic", "technology")
        include_images = settings.get("include_images", True)
        topic_name = TOPICS.get(topic, TOPICS["technology"])["name"]
    else:
        is_active = False
        interval = 60
        topic = "technology"
        include_images = True
        topic_name = TOPICS["technology"]["name"]
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    interval_min = interval // 60 if interval >= 60 else f"{interval} сек"
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval_min}\n"
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
    
    keyboard = [[InlineKeyboardButton(f"{topic['emoji']} {topic['name']}", callback_data=f"set_topic_{channel_id}_{key}")] 
                for key, topic in TOPICS.items()]
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
    topic = parts[3]
    user_id = query.from_user.id
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["topic"] = topic
    else:
        bot_data.set_auto_posting(channel_id, user_id, topic, 60, False)
    
    topic_name = TOPICS.get(topic, TOPICS["technology"])["name"]
    await query.edit_message_text(f"✅ Тема установлена: {topic_name}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if not settings:
        await query.edit_message_text("❌ Сначала настройте тему и интервал")
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
        bot_data.set_auto_posting(channel_id, user_id, "technology", interval, False)
    
    interval_display = f"{interval // 60} мин" if interval >= 60 else f"{interval} сек"
    await query.edit_message_text(f"✅ Интервал установлен: {interval_display}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

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
    
    active_auto = sum(1 for ch in channels if bot_data.get_auto_settings(ch['id']) and bot_data.get_auto_settings(ch['id']).get("is_active"))
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 Имя: {user.get('first_name', 'Unknown')}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n"
        f"📢 Каналов: {len(channels)}/{TARIFFS[tariff]['max_channels']}\n"
        f"⚙️ Активных автопостингов: {active_auto}\n"
        f"📅 В системе с: {user.get('joined', datetime.now()).strftime('%d.%m.%Y')}\n\n"
        f"Чтобы сменить тариф - используйте меню 'Тарифы'"
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
        f"• Используйте разные темы\n"
        f"• Для лучшего охвата ставьте интервал 30-60 мин\n"
        f"• PRO тариф дает максимум возможностей"
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
    elif data == "reposts_menu":
        await query.edit_message_text("🔄 Репосты будут доступны в следующем обновлении", parse_mode='Markdown')
    elif data == "help":
        help_text = (
            "ℹ️ *Помощь*\n\n"
            "📋 *Функции бота:*\n"
            "• 📝 Ручная публикация постов\n"
            "• 🔍 Поиск и публикация картинок\n"
            "• ⚙️ Автопостинг с интервалом от 10 сек\n"
            "• 🎯 10+ тем с готовыми постами\n"
            "• 🖼 Автоматические картинки к постам\n\n"
            "💡 *Советы:*\n"
            "• Для автопостинга выберите тему и интервал\n"
            "• PRO тариф дает доступ к картинкам\n"
            "• Настройте интервал под свою аудиторию\n\n"
            "🚀 *Активные тарифы:*\n"
            "• FREE - базовые функции\n"
            "• BASIC - больше каналов и постов\n"
            "• PRO - все возможности\n\n"
            "❓ Вопросы: @support_bot"
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
    elif data.startswith("send_image_"):
        await send_image_post(update, context)

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
    logger.info("✅ 10+ тем с готовыми постами")
    logger.info("🖼 Поиск и публикация картинок")
    logger.info("⚡ Интервал автопостинга от 10 секунд")
    logger.info("💎 Все тарифы бесплатны!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
