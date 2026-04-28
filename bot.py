import asyncio
import logging
import random
import aiohttp
import io
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import re

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
        "max_posts_per_day": 50,
        "features": ["✅ 3 канала", "✅ Интервал от 1 мин", "✅ 50 постов/день", "✅ 10 тем", "✅ Текст + эмодзи"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 10,
        "min_interval": 30,
        "max_posts_per_day": 200,
        "features": ["✅ 10 каналов", "✅ Интервал от 30 сек", "✅ 200 постов/день", "✅ 20 тем", "✅ Картинки к постам"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 50,
        "min_interval": 10,
        "max_posts_per_day": 1000,
        "features": ["✅ 50 каналов", "✅ Интервал от 10 сек", "✅ 1000 постов/день", "✅ 30+ тем", "✅ Поиск картинок", "✅ Длинные посты"]
    }
}

# ==================== РАСШИРЕННЫЕ ТЕМЫ ====================
TOPICS = {
    "technology": {
        "name": "💻 Технологии и IT",
        "emoji": "💻",
        "posts": [
            "🚀 **Новый прорыв в ИИ!**\n\nУченые создали нейросеть, которая может предсказывать будущее с точностью 90%! Искусственный интеллект теперь способен анализировать огромные массивы данных и делать прогнозы на основе сложных алгоритмов машинного обучения.\n\n🤖 Инновации в области AI открывают новые горизонты для медицины, финансов и науки. В ближайшие годы нас ждет настоящая революция!\n\n#AI #Технологии #Инновации",
            "📱 **iPhone 15 Pro Max - полный обзор**\n\nТитан, USB-C, кнопка действия (Action Button) и чип A17 Pro. Смартфон получил 48-мегапиксельную камеру, 5-кратный оптический зум и невероятную производительность.\n\n🔋 Батарея держится на 30% дольше\n📸 Ночной режим стал еще лучше\n🎮 Игры теперь как на консолях\n\nСтоит ли обновляться? Определенно ДА!\n\n#iPhone #Apple #Обзор",
            "🖥 **Как выбрать идеальный ноутбук в 2024**\n\nДля работы, учебы или игр - мы подготовили полный гайд! \n\n💼 Для работы: MacBook Air M2, Lenovo ThinkPad\n🎓 Для учебы: Acer Swift, Huawei MateBook\n🎮 Для игр: ASUS ROG, MSI Gaming\n\nСоветы:\n• Оперативная память: минимум 16GB\n• Процессор: Intel i5/i7 или AMD Ryzen 5/7\n• SSD: от 512GB\n• Батарея: от 8 часов\n\nКакой ноутбук выбрали бы вы? \n\n#Ноутбук #Технологии #Гаджеты"
        ],
        "hashtags": ["#технологии", "#IT", "#гаджеты", "#инновации"]
    },
    "business": {
        "name": "📊 Бизнес и Финансы",
        "emoji": "📊",
        "posts": [
            "💰 **10 способов заработать в интернете в 2024**\n\n1. Фриланс (до $5000/мес)\n2. Дропшиппинг (до $10000/мес)\n3. Инфобизнес (до $50000/мес)\n4. YouTube канал (от $1000)\n5. Криптовалюты (риски!)\n6. SMM услуги (от $2000)\n7. Создание сайтов ($500-5000)\n8. Партнерский маркетинг (пассивный доход)\n9. Онлайн-курсы\n10. Торговля на маркетплейсах\n\n🚀 Начните сегодня! Главное - действие!\n\n#Бизнес #Заработок #Фриланс",
            "📈 **Топ-5 криптовалют для инвестиций**\n\nBitcoin (BTC) - цифровое золото\nEthereum (ETH) - смарт-контракты\nSolana (SOL) - высокая скорость\nCardano (ADA) - научный подход\nPolkadot (DOT) - интероперабельность\n\n💡 Совет: диверсифицируйте портфель и никогда не инвестируйте последние деньги!\n\n#Криптовалюта #Инвестиции #Биткоин",
            "🏢 **Как открыть ИП в 2024: пошаговая инструкция**\n\nШаг 1: Выберите систему налогообложения\nШаг 2: Подготовьте документы (паспорт, ИНН)\nШаг 3: Оплатите госпошлину - 800₽\nШаг 4: Подайте заявление в налоговую\nШаг 5: Получите документы (5 дней)\nШаг 6: Откройте расчетный счет\nШаг 7: Закажите печать (по желанию)\n\n💰 Стоимость: около 3000₽\n⏱ Время: 5-7 дней\n\nГотовы стать предпринимателем?\n\n#Бизнес #ИП #Предпринимательство"
        ],
        "hashtags": ["#бизнес", "#финансы", "#инвестиции", "#деньги"]
    },
    "health": {
        "name": "⚕️ Здоровье и Спорт",
        "emoji": "⚕️",
        "posts": [
            "🏋️ **Идеальная утренняя зарядка за 10 минут**\n\n☀️ Упражнение 1: Наклоны головы (30 сек)\n☀️ Упражнение 2: Вращение плечами (30 сек)\n☀️ Упражнение 3: Махи руками (1 мин)\n☀️ Упражнение 4: Повороты корпуса (1 мин)\n☀️ Упражнение 5: Приседания (2 мин)\n☀️ Упражнение 6: Выпады (2 мин)\n☀️ Упражнение 7: Планка (1 мин)\n☀️ Упражнение 8: Растяжка (2 мин)\n\n🌟 Польза:\n• Заряд бодрости на весь день\n• Улучшение метаболизма\n• Профилактика заболеваний\n\nНачните завтра утро с зарядки! 💪\n\n#Здоровье #Спорт #Зарядка",
            "🥗 **7 продуктов, которые продлят вашу жизнь**\n\n1️⃣ Оливковое масло - антиоксиданты\n2️⃣ Грецкие орехи - омега-3\n3️⃣ Голубика - для мозга\n4️⃣ Лосось - витамин D\n5️⃣ Брокколи - клетчатка\n6️⃣ Куркума - противовоспалительное\n7️⃣ Зеленый чай - долголетие\n\n🧪 Научно доказано: эти продукты снижают риск болезней сердца, рака и диабета на 30-50%!\n\nДобавьте их в свой рацион уже сегодня!\n\n#Питание #Долголетие #ЗОЖ",
            "😴 **Как спать 6 часов и высыпаться**\n\nСекреты продуктивного сна:\n\n⏰ Ложитесь до 23:00\n📱 Без гаджетов за час до сна\n🌡 Температура в комнате 18-20°C\n🛏 Удобный матрас и подушка\n🧘 Медитация перед сном\n🚫 Не ешьте за 3 часа до сна\n☕ Без кофеина после 16:00\n🌙 Полная темнота в комнате\n\nПлюсы качественного сна:\n• Высокая продуктивность\n• Хорошее настроение\n• Крепкий иммунитет\n• Молодая кожа\n\nСладких снов! 💤\n\n#Сон #Здоровье #Продуктивность"
        ],
        "hashtags": ["#здоровье", "#спорт", "#фитнес", "#ЗОЖ"]
    },
    "psychology": {
        "name": "🧠 Психология и Саморазвитие",
        "emoji": "🧠",
        "posts": [
            "🧘 **10 привычек успешных людей**\n\n1. Ранний подъем (5-6 утра)\n2. Медитация/планирование дня\n3. Чтение книг (30+ стр/день)\n4. Физическая активность\n5. Обучение новому\n6. Ведение дневника\n7. Позитивное мышление\n8. Отказ от соцсетей (до 2 часов)\n9. Здоровое питание\n10. Благодарность каждый день\n\n💫 Начните с одной привычки и добавляйте новую каждую неделю. Через месяц вы не узнаете себя!\n\nКакая привычка самая сложная для вас?\n\n#Саморазвитие #Привычки #Успех",
            "💪 **Как победить прокрастинацию: 5 работающих методов**\n\nМетод 1 - 🍅 Помидор (25 минут работы, 5 отдых)\nМетод 2 - 🎯 Правило 2 минут (если дело на 2 минуты - сделай сразу)\nМетод 3 - 📋 Разбей задачу на микро-шаги\nМетод 4 - 🏆 Награда после выполнения\nМетод 5 - 🚫 Уберите отвлекающие факторы\n\nПочему это работает:\n✅ Снижает тревожность\n✅ Создает ощущение прогресса\n✅ Формирует привычку\n\nПопробуйте прямо сейчас! Напишите 3 задачи на сегодня и начните с самой маленькой!\n\n#Психология #Продуктивность #Мотивация",
            "🎯 **Как найти свое призвание**\n\nПошаговый план:\n\n1️⃣ Вспомните, чем любили заниматься в детстве\n2️⃣ Выпишите 20 вещей, которые приносят радость\n3️⃣ Что бы вы делали бесплатно?\n4️⃣ За что вас хвалят другие?\n5️⃣ Пройдите тесты на профориентацию\n6️⃣ Изучите профессии будущего\n7️⃣ Попробуйте разные сферы (экспериментируйте!)\n8️⃣ Спросите совета у наставника\n9️⃣ Не бойтесь ошибаться\n🔟 Идите к мечте маленькими шагами\n\n💡 Помните: призвание - это то, где ваши таланты встречаются с пользой для мира!\n\nУже нашли свое призвание? Делитесь в комментариях!\n\n#Саморазвитие #Призвание #Карьера"
        ],
        "hashtags": ["#психология", "#саморазвитие", "#мотивация"]
    },
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "posts": [
            "🌍 **Топ-5 стран для бюджетных путешествий 2024**\n\n1️⃣ Грузия ($30/день)\n• Цены: еда $5, жилье $15\n• Визовый режим: не нужна\n\n2️⃣ Вьетнам ($25/день)\n• Цены: еда $3, жилье $10\n• Авиабилеты от $400\n\n3️⃣ Турция ($35/день)\n• Цены: еда $8, жилье $20\n• Все включено выгодно\n\n4️⃣ Казахстан ($25/день)\n• Цены: еда $5, жилье $12\n• Красивая природа\n\n5️⃣ Индия ($20/день)\n• Цены: еда $3, жилье $8\n• Йога и духовные практики\n\n💰 Лайфхак: летайте с пересадками, бронируйте заранее, используйте кэшбэк!\n\nКуда планируете в этом году?\n\n#Путешествия #БюджетныйТревел #Мир",
            "🏝 **Бали: полный гайд для новичков**\n\nГде жить:\n• Кута - тусовки ($15)\n• Чангу - серфинг ($20)\n• Убуд - йога ($12)\n• Семиньяк - люкс ($40+)\n\nЧто посмотреть:\n📍 Храм Улувату\n📍 Рисовые террасы Тегаллаланг\n📍 Вулкан Батур\n📍 Водопад Сепумпунг\n📍 Остров Нуса Пенида\n\nСоветы:\n🛵 Аренда байка - $5/день\n🍜 Местная еда - $2-3\n💳 Берите наличные\n📱 SIM Card - $10\n\nМечтаете о Бали? Самое время ехать!\n\n#Бали #Индонезия #ПутешествияМечты",
            "🗺 **Секреты дешевых авиабилетов**\n\nКак экономить до 70%:\n\n1️⃣ Покупайте за 2-3 месяца\n2️⃣ Летайте по вторникам/средам\n3️⃣ Используйте инкогнито-режим\n4️⃣ Следите за акциями\n5️⃣ Сравнивайте агрегаторы:\n   • Skyscanner\n   • Aviasales\n   • Google Flights\n   • Momondo\n\n6️⃣ Подпишитесь на рассылки\n7️⃣ Используйте мили/бонусы\n8️⃣ Летайте с пересадками\n9️⃣ Выбирайте лоукостеры:\n   • Ryanair\n   • Wizz Air\n   • Pobeda\n   • AirAsia\n\n💰 Пример: Москва-Бангкок от $150!\n\nЛетите дешево!\n\n#Авиабилеты #Экономия #ТревелХак"
        ],
        "hashtags": ["#путешествия", "#туризм", "#мир"]
    },
    "crypto": {
        "name": "🪙 Криптовалюты",
        "emoji": "🪙",
        "posts": [
            "📊 **Анализ рынка криптовалют**\n\nТекущая ситуация:\n\n📈 Bitcoin (BTC): $45,000\n• Доминирование: 52%\n• Поддержка: $42,000\n• Сопротивление: $48,000\n\n🚀 Ethereum (ETH): $2,800\n• Газ: 20-40 Gwei\n• Апгрейд Dencun скоро\n\n💎 Альткоины:\n• Solana (SOL): $100\n• Cardano (ADA): $0.5\n• Polkadot (DOT): $8\n\nПрогноз: бычий тренд, ожидаем рост к концу года\n\nЧто в вашем портфеле?\n\n#Криптовалюта #Bitcoin #Трейдинг"
        ],
        "hashtags": ["#криптовалюта", "#биткоин", "#трейдинг"]
    },
    "cooking": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "posts": [
            "👨‍🍳 **Идеальный ужин за 30 минут**\n\n🍝 Паста Карбонара:\nИнгредиенты:\n• Спагетти - 400г\n• Бекон - 200г\n• Яйца - 4 шт\n• Пармезан - 100г\n• Чеснок - 3 зубчика\n• Сливки - 200мл\n\nПриготовление:\n1. Сварите пасту\n2. Обжарьте бекон с чесноком\n3. Смешайте яйца с сыром\n4. Добавьте сливки\n5. Соедините все ингредиенты\n\nГотово за 30 минут! Вкуснее, чем в ресторане! 😋\n\n#Кулинария #Рецепты #Паста"
        ],
        "hashtags": ["#кулинария", "#рецепты", "#еда"]
    },
    "movies": {
        "name": "🎬 Кино и Сериалы",
        "emoji": "🎬",
        "posts": [
            "🍿 **Топ-10 сериалов 2024**\n\n1. «Одни из нас» (HBO) - 9.5/10\n2. «Медленные лошади» (Apple TV) - 9.3\n3. «Поколение V» (Amazon) - 9.0\n4. «Утреннее шоу» (Apple TV) - 8.8\n5. «Последние из нас» (HBO) - 9.6\n6. «Корона» (Netflix) - 8.9\n7. «Ведьмак» (Netflix) - 8.5\n8. «Фарго» (FX) - 9.2\n9. «Белый лотос» (HBO) - 8.7\n10. «Мандалорец» (Disney+) - 9.1\n\nЧто смотрите сейчас? Делитесь в комментариях!\n\n#Сериалы #Кино #Топ2024"
        ],
        "hashtags": ["#кино", "#сериалы", "#топ2024"]
    },
    "gaming": {
        "name": "🎮 Игры",
        "emoji": "🎮",
        "posts": [
            "🎮 **Топ игр 2024**\n\nОбязательны к прохождению:\n\n1️⃣ Spider-Man 2 (PS5) - 10/10\n2️⃣ Alan Wake 2 (PC/PS5/Xbox) - 9.5\n3️⃣ Baldur's Gate 3 (PC/PS5) - 10/10\n4️⃣ Starfield (PC/Xbox) - 8.5\n5️⃣ Lies of P (PC/PS5/Xbox) - 9.0\n\nБесплатные игры:\n• Genshin Impact\n• Warframe\n• Apex Legends\n• Valorant\n• Fortnite\n\nВ какую игру играете сейчас?\n\n#Игры #Gaming #Топ2024"
        ],
        "hashtags": ["#игры", "#гейминг", "#новинки"]
    },
    "fashion": {
        "name": "👗 Мода и Стиль",
        "emoji": "👗",
        "posts": [
            "👔 **Мужской гардероб: 12 вещей, которые должны быть**\n\nБаза:\n1. Белая рубашка\n2. Синий пиджак\n3. Черные брюки\n4. Джинсы\n5. Свитер кашемир\n6. Поло\n7. Футболки (белая/черная)\n8. Кожаная куртка\n9. Пальто\n10. Кроссовки минимализм\n11. Классические туфли\n12. Часы\n\n💡 Стильно и универсально!\n\n#Мода #Стиль #МужскойГардероб"
        ],
        "hashtags": ["#мода", "#стиль", "#look"]
    },
    "gadgets": {
        "name": "📱 Гаджеты",
        "emoji": "📱",
        "posts": [
            "⌚ **Революция в смарт-часах**\n\nНовые Apple Watch Ultra 2:\n• Титан\n• 36 часов батареи\n• Датчик температуры\n• Радар падений\n• 2000 нит дисплей\n• GPS L1 и L5\n\nПлюсы:\n✅ Монстр производительности\n✅ Для экстремалов\n✅ Защита до 100м\n\nМинусы:\n❌ Цена ($799)\n❌ Массивный дизайн\n\nСтоит брать?\n\n#Гаджеты #AppleWatch #Обзор"
        ],
        "hashtags": ["#гаджеты", "#технологии", "#обзор"]
    }
}

# ==================== КАРТИНКИ ДЛЯ ТЕМ ====================
POST_IMAGES = {
    "technology": [
        "https://images.pexels.com/photos/2582937/pexels-photo-2582937.jpeg",
        "https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg"
    ],
    "business": [
        "https://images.pexels.com/photos/7567434/pexels-photo-7567434.jpeg",
        "https://images.pexels.com/photos/4164418/pexels-photo-4164418.jpeg"
    ],
    "health": [
        "https://images.pexels.com/photos/2254031/pexels-photo-2254031.jpeg",
        "https://images.pexels.com/photos/842711/pexels-photo-842711.jpeg"
    ],
    "travel": [
        "https://images.pexels.com/photos/415733/pexels-photo-415733.jpeg",
        "https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg"
    ]
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
class BotData:
    def __init__(self):
        self.users = {}
        self.channels = {}
        self.auto_posting = {}
        self.posting_tasks = {}
        self.user_tariffs = {}
        self.posts_count = {}
        self.last_posts = {}
    
    def init_user(self, user_id: int, username: str, first_name: str):
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "username": username,
                "first_name": first_name,
                "joined": datetime.now()
            }
            self.user_tariffs[user_id] = "free"
            self.channels[user_id] = []
            self.posts_count[user_id] = 0
    
    def add_channel(self, user_id: int, channel_id: str, channel_title: str):
        tariff = self.user_tariffs.get(user_id, "free")
        max_channels = TARIFFS[tariff]["max_channels"]
        
        if user_id not in self.channels:
            self.channels[user_id] = []
        
        if len(self.channels[user_id]) >= max_channels:
            return False, f"Лимит каналов: {max_channels}"
        
        for ch in self.channels[user_id]:
            if ch["id"] == channel_id:
                return False, "Канал уже добавлен"
        
        self.channels[user_id].append({
            "id": channel_id,
            "title": channel_title,
            "added": datetime.now()
        })
        return True, "Канал добавлен"
    
    def get_channels(self, user_id: int):
        return self.channels.get(user_id, [])
    
    def can_post(self, user_id: int) -> bool:
        tariff = self.user_tariffs.get(user_id, "free")
        max_posts = TARIFFS[tariff]["max_posts_per_day"]
        today = datetime.now().date()
        
        if user_id not in self.last_posts:
            self.last_posts[user_id] = {"date": today, "count": 0}
        
        if self.last_posts[user_id]["date"] != today:
            self.last_posts[user_id] = {"date": today, "count": 0}
        
        return self.last_posts[user_id]["count"] < max_posts
    
    def add_post(self, user_id: int):
        if user_id in self.last_posts:
            self.last_posts[user_id]["count"] += 1
    
    def set_auto(self, channel_id: str, user_id: int, topic: str, interval: int):
        self.auto_posting[channel_id] = {
            "user_id": user_id,
            "topic": topic,
            "interval": interval,
            "active": True,
            "last_post": datetime.now() - timedelta(minutes=interval)
        }
        return True
    
    def get_auto(self, channel_id: str):
        return self.auto_posting.get(channel_id)
    
    def toggle_auto(self, channel_id: str, active: bool):
        if channel_id in self.auto_posting:
            self.auto_posting[channel_id]["active"] = active
            return True
        return False

bot_data = BotData()

# ==================== ПОИСК КАРТИНОК ====================
async def search_image(topic: str) -> Optional[str]:
    """Поиск картинки по теме (имитация, в реальности нужно API)"""
    images = POST_IMAGES.get(topic, POST_IMAGES.get("technology"))
    if images:
        return random.choice(images)
    return None

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_worker(bot, channel_id: str):
    """Фоновый поток для автопостинга"""
    while True:
        try:
            settings = bot_data.get_auto(channel_id)
            if not settings or not settings.get("active"):
                break
            
            now = datetime.now()
            last = settings.get("last_post", now - timedelta(minutes=60))
            interval = settings.get("interval", 60)
            
            if (now - last).total_seconds() >= interval:
                topic_key = settings.get("topic")
                user_id = settings.get("user_id")
                
                if bot_data.can_post(user_id):
                    topic = TOPICS.get(topic_key, TOPICS["technology"])
                    posts = topic.get("posts", [])
                    
                    if posts:
                        post_text = random.choice(posts)
                        
                        # Добавляем хэштеги
                        hashtags = " " + " ".join(topic.get("hashtags", []))
                        full_text = post_text + hashtags
                        
                        try:
                            # Пробуем добавить картинку
                            image_url = await search_image(topic_key)
                            
                            if image_url:
                                await bot.send_photo(
                                    chat_id=channel_id,
                                    photo=image_url,
                                    caption=full_text,
                                    parse_mode='Markdown'
                                )
                            else:
                                await bot.send_message(
                                    chat_id=channel_id,
                                    text=full_text,
                                    parse_mode='Markdown'
                                )
                            
                            settings["last_post"] = now
                            bot_data.add_post(user_id)
                            logger.info(f"✅ Автопост в {channel_id}: {topic_key}")
                            
                        except Exception as e:
                            logger.error(f"Ошибка отправки: {e}")
            
            await asyncio.sleep(min(interval, 30))
            
        except Exception as e:
            logger.error(f"Ошибка авто-постинга: {e}")
            await asyncio.sleep(60)

async def start_auto(bot, channel_id: str):
    if channel_id in bot_data.posting_tasks:
        old = bot_data.posting_tasks[channel_id]
        if not old.done():
            old.cancel()
    
    task = asyncio.create_task(auto_posting_worker(bot, channel_id))
    bot_data.posting_tasks[channel_id] = task

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Ручной пост", callback_data="write_post")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("🎯 Все темы", callback_data="all_topics")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(action: str, channel_id: str = None):
    keyboard = []
    for key, topic in TOPICS.items():
        callback = f"{action}_{key}"
        if channel_id:
            callback = f"{action}_{channel_id}_{key}"
        keyboard.append([InlineKeyboardButton(f"{topic['emoji']} {topic['name']}", callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("1 минута", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("5 минут", callback_data=f"interval_{channel_id}_300")],
        [InlineKeyboardButton("10 минут", callback_data=f"interval_{channel_id}_600")],
        [InlineKeyboardButton("30 минут", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_3600")],
        [InlineKeyboardButton("3 часа", callback_data=f"interval_{channel_id}_10800")],
        [InlineKeyboardButton("6 часов", callback_data=f"interval_{channel_id}_21600")],
        [InlineKeyboardButton("12 часов", callback_data=f"interval_{channel_id}_43200")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_channels_list_keyboard(user_id: int, action: str):
    channels = bot_data.get_channels(user_id)
    keyboard = []
    
    for ch in channels:
        suffix = ""
        if action == "auto":
            settings = bot_data.get_auto(ch['id'])
            suffix = " ✅" if settings and settings.get("active") else " ❌"
        keyboard.append([InlineKeyboardButton(f"📢 {ch['title']}{suffix}", callback_data=f"{action}_channel_{ch['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга с ИИ*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная и автоматическая публикация\n"
        f"• 🎯 Более {len(TOPICS)} тем с уникальным контентом\n"
        f"• 🖼 Поиск и добавление картинок\n"
        f"• 📊 Объемные информативные посты\n"
        f"• ⏱ Гибкие интервалы (от 1 минуты)\n"
        f"• 💎 3 бесплатных тарифа\n\n"
        f"🚀 *Как начать:*\n"
        f"1️⃣ Добавьте меня в канал как админа\n"
        f"2️⃣ Добавьте канал в бота (кнопка ниже)\n"
        f"3️⃣ Настройте автопостинг\n\n"
        f"💡 *Все тарифы бесплатны!*"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ID или ссылку\n\n"
        "📝 Примеры:\n"
        "• `@channel_name`\n"
        "• `https://t.me/channel_name`\n\n"
        "Отправьте ссылку:",
        parse_mode='Markdown'
    )
    context.user_data['adding'] = True

async def process_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    if "t.me/" in channel_input:
        channel_input = "@" + channel_input.split("t.me/")[-1]
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_input)
        
        if chat.type not in ['channel', 'supergroup']:
            await update.message.reply_text("❌ Это не канал")
            return
        
        success, msg = bot_data.add_channel(user.id, str(chat.id), chat.title)
        
        if success:
            await update.message.reply_text(
                f"✅ {msg}\n\n📢 {chat.title}\n🆔 {chat.id}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {msg}")
        
        context.user_data['adding'] = False
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Сначала добавьте канал")
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"post_to_{ch['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text("📝 Выберите канал:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['post_channel'] = channel_id
    
    # Показываем темы для быстрого поста
    keyboard = await get_topics_keyboard("quick", channel_id)
    await query.edit_message_text(
        "📝 *Напишите пост или выберите тему:*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    context.user_data['awaiting_post'] = True

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        await update.message.reply_text("❌ Ошибка")
        return
    
    if not bot_data.can_post(user.id):
        await update.message.reply_text("❌ Лимит постов на сегодня")
        return
    
    text = update.message.text
    
    try:
        await context.bot.send_message(chat_id=channel_id, text=text, parse_mode='Markdown')
        await update.message.reply_text("✅ Пост опубликован!")
        bot_data.add_post(user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    context.user_data['awaiting_post'] = False
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def quick_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic_key = parts[3]
    user_id = query.from_user.id
    
    if not bot_data.can_post(user_id):
        await query.edit_message_text("❌ Лимит постов на сегодня")
        return
    
    topic = TOPICS.get(topic_key, TOPICS["technology"])
    post_text = random.choice(topic.get("posts", []))
    hashtags = " " + " ".join(topic.get("hashtags", []))
    full_text = post_text + hashtags
    
    try:
        # Пробуем добавить картинку
        image_url = await search_image(topic_key)
        
        if image_url:
            await context.bot.send_photo(
                chat_id=channel_id,
                photo=image_url,
                caption=full_text,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=channel_id,
                text=full_text,
                parse_mode='Markdown'
            )
        
        bot_data.add_post(user_id)
        await query.edit_message_text(f"✅ Пост на тему '{topic['name']}' опубликован!")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    await asyncio.sleep(2)
    await back_to_main(update, context)

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_channels_list_keyboard(query.from_user.id, "auto")
    await query.edit_message_text(
        "⚙️ *Выберите канал для автопостинга*\n\n✅ - активен ❌ - неактивен",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def auto_channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    context.user_data['auto_channel'] = channel_id
    
    settings = bot_data.get_auto(channel_id)
    topic_key = settings.get("topic", "technology") if settings else "technology"
    interval = settings.get("interval", 3600) if settings else 3600
    active = settings.get("active", False) if settings else False
    
    topic_name = TOPICS.get(topic_key, TOPICS["technology"])["name"]
    interval_min = interval // 60
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {'✅ АКТИВЕН' if active else '❌ НЕАКТИВЕН'}\n"
        f"📝 Тема: {topic_name}\n"
        f"⏱ Интервал: {interval_min} мин\n\n"
        f"Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Включить/Выключить", callback_data=f"toggle_{channel_id}")],
        [InlineKeyboardButton("📝 Выбрать тему", callback_data=f"select_topic_{channel_id}")],
        [InlineKeyboardButton("⏱ Выбрать интервал", callback_data=f"select_interval_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_topic_for_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_", "")
    keyboard = await get_topics_keyboard("set_topic", channel_id)
    await query.edit_message_text("📝 Выберите тему:", reply_markup=keyboard)

async def set_auto_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic_key = parts[3]
    
    settings = bot_data.get_auto(channel_id)
    if settings:
        settings["topic"] = topic_key
    else:
        bot_data.set_auto(channel_id, query.from_user.id, topic_key, 3600)
    
    await query.edit_message_text(f"✅ Тема установлена: {TOPICS[topic_key]['name']}")
    await asyncio.sleep(2)
    await auto_channel_settings(update, context)

async def select_interval_for_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_interval_", "")
    keyboard = await get_interval_keyboard(channel_id)
    await query.edit_message_text("⏱ Выберите интервал:", reply_markup=keyboard)

async def set_auto_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    interval = int(parts[2])
    
    user_id = query.from_user.id
    tariff = bot_data.user_tariffs.get(user_id, "free")
    min_interval = TARIFFS[tariff]["min_interval"]
    
    if interval < min_interval:
        await query.edit_message_text(f"❌ Минимальный интервал: {min_interval // 60} мин")
        return
    
    settings = bot_data.get_auto(channel_id)
    if settings:
        settings["interval"] = interval
    else:
        bot_data.set_auto(channel_id, user_id, "technology", interval)
    
    await query.edit_message_text(f"✅ Интервал: {interval // 60} минут")
    await asyncio.sleep(2)
    await auto_channel_settings(update, context)

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_", "")
    settings = bot_data.get_auto(channel_id)
    
    if not settings:
        await query.edit_message_text("❌ Сначала настройте тему и интервал")
        return
    
    new_status = not settings.get("active", False)
    
    if new_status:
        # Проверка лимитов
        user_id = settings.get("user_id")
        if bot_data.can_post(user_id):
            settings["active"] = True
            await start_auto(context.bot, channel_id)
            await query.edit_message_text("✅ Автопостинг ВКЛЮЧЕН")
        else:
            await query.edit_message_text("❌ Лимит постов на сегодня")
            return
    else:
        settings["active"] = False
        await query.edit_message_text("❌ Автопостинг ВЫКЛЮЧЕН")
    
    await asyncio.sleep(2)
    await auto_channel_settings(update, context)

async def show_all_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *Все доступные темы*\n\n"
    for key, topic in TOPICS.items():
        text += f"{topic['emoji']} **{topic['name']}**\n"
        text += f"📝 Постов в теме: {len(topic['posts'])}\n"
        text += f"🏷 Хэштеги: {', '.join(topic['hashtags'][:2])}\n\n"
    
    text += "💡 *Совет:* Выберите тему в настройках автопостинга"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current = bot_data.user_tariffs.get(user_id, "free")
    
    text = "💎 *Тарифы*\n\n"
    for key, t in TARIFFS.items():
        marker = "✅ *ТЕКУЩИЙ* " if key == current else ""
        text += f"{marker}{t['name']}\n"
        text += f"• Каналов: {t['max_channels']}\n"
        text += f"• Интервал: от {t['min_interval']} сек\n"
        text += f"• Постов/день: {t['max_posts_per_day']}\n"
        for f in t['features']:
            text += f"  {f}\n"
        text += "\n"
    
    text += "🎁 *Все тарифы бесплатны!*"
    
    keyboard = []
    for key in TARIFFS:
        if key != current:
            keyboard.append([InlineKeyboardButton(f"Выбрать {TARIFFS[key]['name']}", callback_data=f"tariff_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace("tariff_", "")
    user_id = query.from_user.id
    
    bot_data.user_tariffs[user_id] = tariff_key
    
    await query.edit_message_text(f"✅ Тариф изменен на {TARIFFS[tariff_key]['name']}")
    await asyncio.sleep(2)
    await show_tariffs(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = bot_data.users.get(user_id, {})
    tariff = bot_data.user_tariffs.get(user_id, "free")
    channels = bot_data.get_channels(user_id)
    
    active_auto = 0
    for ch in channels:
        settings = bot_data.get_auto(ch['id'])
        if settings and settings.get("active"):
            active_auto += 1
    
    today_posts = bot_data.last_posts.get(user_id, {}).get("count", 0)
    max_posts = TARIFFS[tariff]["max_posts_per_day"]
    
    text = (
        f"👤 *Профиль*\n\n"
        f"📝 {user.get('first_name')}\n"
        f"💎 Тариф: {TARIFFS[tariff]['name']}\n"
        f"📢 Каналов: {len(channels)}/{TARIFFS[tariff]['max_channels']}\n"
        f"⚙️ Автопостингов: {active_auto}\n"
        f"📊 Постов сегодня: {today_posts}/{max_posts}\n"
        f"📅 В системе: {user.get('joined', datetime.now()).strftime('%d.%m.%Y')}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    channels = bot_data.get_channels(user_id)
    
    text = f"📊 *Статистика*\n\n"
    text += f"📢 Всего каналов: {len(channels)}\n\n"
    
    for ch in channels:
        settings = bot_data.get_auto(ch['id'])
        if settings:
            topic = TOPICS.get(settings.get("topic"), TOPICS["technology"])
            status = "✅" if settings.get("active") else "❌"
            interval = settings.get("interval", 3600) // 60
            text += f"{status} {ch['title']}\n"
            text += f"   📝 {topic['name']}, ⏱ {interval} мин\n"
    
    text += "\n💡 Давай автоматизации - больше охватов!"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 *Главное меню*", parse_mode='Markdown', reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено")
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "write_post":
        await write_post(update, context)
    elif data == "my_channels":
        keyboard = await get_channels_list_keyboard(query.from_user.id, "channels")
        await query.edit_message_text("📢 Ваши каналы:", reply_markup=keyboard)
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "all_topics":
        await show_all_topics(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "help":
        await show_all_topics(update, context)
    elif data.startswith("post_to_"):
        await send_post(update, context)
    elif data.startswith("auto_channel_"):
        await auto_channel_settings(update, context)
    elif data.startswith("select_topic_"):
        await select_topic_for_auto(update, context)
    elif data.startswith("set_topic_"):
        await set_auto_topic(update, context)
    elif data.startswith("select_interval_"):
        await select_interval_for_auto(update, context)
    elif data.startswith("interval_"):
        await set_auto_interval(update, context)
    elif data.startswith("toggle_"):
        await toggle_auto(update, context)
    elif data.startswith("tariff_"):
        await select_tariff(update, context)
    elif data.startswith("quick_"):
        await quick_post(update, context)
    elif data.startswith("channels_channel_"):
        await query.answer()
    else:
        await query.answer()

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
        lambda u, c: process_add(u, c) if c.user_data.get('adding')
        else (handle_post(u, c) if c.user_data.get('awaiting_post')
        else None)
    ))
    
    # Callback
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот с ИИ и поиском картинок запущен!")
    logger.info(f"📚 Доступно {len(TOPICS)} тем с контентом")
    logger.info("🖼 Поддержка картинок к постам")
    logger.info("💎 Все тарифы бесплатны!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
