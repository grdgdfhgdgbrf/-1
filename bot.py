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

# Состояния
WAITING_TOPIC_NAME, WAITING_TOPIC_POSTS, WAITING_TOPIC_QUERIES = range(3)

# ==================== ТАРИФЫ ====================
TARIFFS = {
    "free": {
        "name": "🌟 Бесплатный",
        "max_channels": 3,
        "min_interval": 60,
        "max_posts_per_day": 100,
        "image_size": "medium",
        "text_size": "medium",
        "features": ["✅ 3 канала", "✅ Интервал от 1 мин", "✅ 100 постов/день"]
    },
    "basic": {
        "name": "📘 Базовый",
        "max_channels": 10,
        "min_interval": 30,
        "max_posts_per_day": 500,
        "image_size": "large",
        "text_size": "large",
        "features": ["✅ 10 каналов", "✅ Интервал от 30 сек", "✅ 500 постов/день", "✅ Свои темы"]
    },
    "pro": {
        "name": "💎 PRO",
        "max_channels": 30,
        "min_interval": 10,
        "max_posts_per_day": 2000,
        "image_size": "hd",
        "text_size": "xlarge",
        "features": ["✅ 30 каналов", "✅ Интервал от 10 сек", "✅ 2000 постов/день", "✅ HD картинки", "✅ Свои темы"]
    }
}

# ==================== ТЕКСТОВЫЕ РАЗМЕРЫ ====================
TEXT_SIZES = {
    "small": {
        "prefix": "📝 ",
        "suffix": "\n\n✨ Коротко и ясно!",
        "max_length": 500
    },
    "medium": {
        "prefix": "📄 ",
        "suffix": "\n\n📌 Подробный разбор темы.\n✨ Подписывайтесь на канал!",
        "max_length": 1000
    },
    "large": {
        "prefix": "📖 ",
        "suffix": "\n\n🔍 Глубокий анализ и экспертные выводы.\n📢 Больше полезного контента каждый день!\n✨ Подпишись, чтобы не пропустить!",
        "max_length": 2000
    },
    "xlarge": {
        "prefix": "📚 ",
        "suffix": "\n\n💎 Эксклюзивный материал от экспертов.\n🎯 Только проверенная информация.\n🔥 Самые актуальные новости и тренды.\n✨ Подписывайтесь и будьте в курсе!",
        "max_length": 3000
    }
}

# ==================== 20 УНИКАЛЬНЫХ ТЕМ ====================
TOPICS = {
    # 1
    "nft_art": {
        "name": "🎨 NFT Искусство",
        "emoji": "🎨",
        "posts": [
            "🎨 **Шедевры цифрового искусства NFT**\n\nБезликие (CryptoPunks) проданы за $23.7 млн. Beeple создал работу за 13 лет. Почему пиксели стоят миллионы?\n\n#NFT #ЦифровоеИскусство #Крипта",
            "🖼 **Как создать NFT с нуля за 15 минут**\n\nПошаговый гайд для художника. Платформы: OpenSea, Rarible. Комиссии, роялти, продвижение.\n\n#СоздатьNFT #Токены #Заработок",
            "🌟 **Самые дорогие NFT 2025**\n\nТоп-10 продаж: Beeple ($69M), CryptoPunk ($23.7M), Pak ($16.8M). Инвестиции в цифру окупаются!\n\n #NFTКоллекции #Рекорды",
            "🏺 **Музеи скупают NFT шедевры**\n\nЛувр, Эрмитаж, MoMA создают цифровые коллекции. Искусство будущего уже здесь.\n\n #NFT #Музеи #Искусство",
            "⚡ **AI генерирует NFT за секунды**\n\nНейросети создают уникальные изображения. Как заработать на AI-арте.\n\n #AIарт #Нейросети #NFT"
        ],
        "image_queries": ["digital art masterpiece", "nft collection", "crypto art gallery", "rare nft art", "digital painting abstract"]
    },
    # 2
    "telegram": {
        "name": "📱 Telegram Бизнес",
        "emoji": "📱",
        "posts": [
            "📱 **Как набрать 100к в Telegram за месяц**\n\nРеальная стратегия 2025: таргет, взаимопиар, чат-боты. Бюджет: от 0 до $1000.\n\n #Telegram #Продвижение #Бизнес",
            "🤖 **10 ботов для автоматизации бизнеса**\n\n@ControllerBot, @SaleBot, @SupportBot. Сэкономьте 20 часов в неделю!\n\n #TelegramБоты #Автоматизация",
            "💰 **Монетизация канала: $10,000/мес**\n\nРеклама, подписки, партнерки, товары. Реальные кейсы и чеки.\n\n #Монетизация #Telegram #Заработок",
            "📊 **Секреты аналитики конкурентов**\n\nTelemetr, TGStat, Teletype. Как шпионить и расти быстрее.\n\n #Аналитика #Telegram",
            "🎯 **Топ-50 каналов для бизнеса**\n\nМаркетинг, стартапы, инвестиции. Подпишись и будь в тренде.\n\n #TelegramКаналы #Бизнес"
        ],
        "image_queries": ["telegram app interface", "social media marketing", "business growth chart", "telegram channel", "digital marketing strategy"]
    },
    # 3
    "crypto": {
        "name": "₿ Крипто Инвестиции",
        "emoji": "₿",
        "posts": [
            "₿ **Биткоин $300,000 к 2026?**\n\nАналитика: халвинг, ETF, институционалы. Прогнозы Cathie Wood и Michael Saylor.\n\n #Биткоин #Крипта #Инвестиции",
            "💰 **10 монет которые дадут 100x**\n\nSolana, Avalanche, Arbitrum, Aptos. Фундаментальный анализ.\n\n #Альткоины #Крипта #Прибыль",
            "🔒 **Как хранить крипту безопасно**\n\nLedger, Trezor, холодные кошельки. Защита от хакеров 100%.\n\n #Безопасность #Криптокошелек",
            "💎 **DeFi доход 50% годовых**\n\nСтейкинг, фарминг, лендинг. Лучшие протоколы 2025.\n\n #DeFi #ПассивныйДоход",
            "🚀 **Мемкоины которые взлетели**\n\nDogecoin, Shiba, Pepe. История успеха обычных ребят.\n\n #Мемкоины #Крипта"
        ],
        "image_queries": ["bitcoin chart analysis", "crypto trading desk", "blockchain technology", "cryptocurrency mining", "digital coins"]
    },
    # 4
    "ai_master": {
        "name": "🤖 AI Мастер",
        "emoji": "🤖",
        "posts": [
            "🤖 **ChatGPT 5 уже изменил все**\n\n100 млн пользователей за 2 дня. Пишет код, создает видео, решает науку. Тест-драйв.\n\n #ChatGPT #Нейросети #AI",
            "🎨 **Midjourney V7 vs DALL-E 4**\n\nСравнение нейросетей. Качество, скорость, цена. Что выбрать?\n\n #Midjourney #DALLE #Генерация",
            "💻 **Как программировать с AI и не сойти с ума**\n\nGitHub Copilot, Claude, Codeium. Лучшие практики.\n\n #AIпрограммирование #Код",
            "🎥 **Sora: видео из текста 4K**\n\nOpenAI совершил революцию. Создаем кино без камеры.\n\n #Sora #ВидеоAI #Креатив",
            "🧠 **100 AI инструментов для работы**\n\nChatGPT, Midjourney, Notion AI, Perplexity. Список на год.\n\n #AIинструменты #Продуктивность"
        ],
        "image_queries": ["artificial intelligence robot", "chatgpt interface", "ai neural network", "machine learning", "future technology ai"]
    },
    # 5
    "nft_collections": {
        "name": "🖼 NFT Коллекции",
        "emoji": "🖼",
        "posts": [
            "🖼 **Bored Ape: как обезьяны покорили мир**\n\nИстория взлета, инвестиции, коллаборации с Adidas и Gucci.\n\n #BoredApe #NFTКоллекции",
            "👾 **CryptoPunks: первые NFT миллионеры**\n\n9 punks за $17 в 2017, сейчас $23 млн. Уроки истории.\n\n #CryptoPunks #Инвестиции",
            "🎭 **Azuki: аниме NFT революция**\n\n10,000 персонажей, $30 млн продаж. Секрет успеха.\n\n #Azuki #NFT #Аниме",
            "🐧 **Pudgy Penguins: как бренд стал культовым**\n\nИгрушки в Walmart, токенизация, фанаты.\n\n #PudgyPenguins #NFTБренд",
            "🌿 **Art Blocks: генеративное искусство**\n\nАлгоритмы создают уникальные работы. Инвестиции в код.\n\n #ArtBlocks #ГенеративноеИскусство"
        ],
        "image_queries": ["bored ape yacht club", "cryptopunks collection", "azuki nft art", "pudgy penguins", "rare nft collectibles"]
    },
    # 6
    "crypto_games": {
        "name": "🎮 Crypto Games",
        "emoji": "🎮",
        "posts": [
            "🎮 **Заработок на играх $5000/мес**\n\nAxie, Gods, Illuvium. Реальные стратегии и гайды.\n\n #PlayToEarn #CryptoGames",
            "🌍 **Metaverse земля дорожает**\n\nDecentraland, Sandbox. Участки по $100к. Инвестируй в виртуальную недвижимость.\n\n #Метавселенная #NFTЗемля",
            "⚔️ **Illuvium: самый красивый криптоигровой мир**\n\nРейтинг, геймплей, экономика. Стоит ли играть?\n\n #Illuvium #Гейминг",
            "💎 **Как заработать на NFT в играх**\n\nСтратегии, лучшие игры, ROI. Полный гайд.\n\n #NFTGaming #Заработок",
            "🏆 **Турниры с призовым фондом $1 млн**\n\nКиберспорт в метавселенной. Как стать профессионалом.\n\n #Киберспорт #CryptoGames"
        ],
        "image_queries": ["crypto gaming platform", "metaverse virtual world", "play to earn game", "nft game characters", "blockchain gaming"]
    },
    # 7
    "defi": {
        "name": "💰 DeFi Протоколы",
        "emoji": "💰",
        "posts": [
            "💰 **DeFi доход 500% в год реально**\n\nFarming, стейкинг, ликвидность. Топ протоколы 2025.\n\n #DeFi #ПассивныйДоход #Крипта",
            "🔄 **Uniswap V4: революция в трейдинге**\n\nБез комиссий, смарт-контракты, новые фичи.\n\n #Uniswap #DeFi #Обменники",
            "🔐 **Как не потерять деньги в DeFi**\n\nРиски, аудит, страховки. Безопасность превыше всего.\n\n #DeFiБезопасность",
            "💎 **Лучшие стейблкоины для дохода**\n\nDAI, USDC, USDT. Где получать 20% APR.\n\n #Стейблкоины #Доход",
            "📈 **Aave и Compound: кредиты под крипту**\n\nБерите взаймы, зарабатывайте на процентах.\n\n #Aave #Compound #DeFiКредиты"
        ],
        "image_queries": ["defi protocol", "decentralized finance", "crypto lending", "yield farming", "blockchain finance"]
    },
    # 8
    "web3": {
        "name": "🌐 Web3 Будущее",
        "emoji": "🌐",
        "posts": [
            "🌐 **Web3 заменит интернет к 2030**\n\nДецентрализация, токенизация, DAO. Что нас ждет.\n\n #Web3 #Будущее #Интернет",
            "🗳 **DAO: как управлять миром через токены**\n\nКонституция DAO, голосования, казначейство.\n\n #DAO #Децентрализация #Управление",
            "🔗 **Layer 2 решения побеждают**\n\nArbitrum, Optimism, zkSync. Масштабирование Ethereum.\n\n #Layer2 #Эфириум",
            "💎 **Топ проектов Web3 для инвестиций**\n\nPolkadot, Chainlink, Filecoin. Перспективы.\n\n #Web3 #Инвестиции",
            "🚀 **Децентрализованные соцсети взлетают**\n\nLens, Farcaster, Nostr. Будущее социальных сетей.\n\n #DeSo #Соцсети"
        ],
        "image_queries": ["web3 concept", "decentralized internet", "blockchain network", "future technology", "digital transformation"]
    },
    # 9
    "psychology": {
        "name": "🧠 Психология Успеха",
        "emoji": "🧠",
        "posts": [
            "🧠 **Как читать мысли собеседника**\n\n10 психологических трюков для переговоров и общения.\n\n #Психология #Общение",
            "💪 **Победить страх и тревогу за 5 минут**\n\nДыхание, визуализация, якоря. Рабочие техники.\n\n #Страх #Уверенность",
            "❤️ **Секреты счастливых отношений**\n\nЧто говорят психологи о любви, доверии и близости.\n\n #Отношения #Психология #Любовь",
            "🧘 **Как войти в поток (flow state)**\n\nСостояние гения: техники для работы и творчества.\n\n #Flow #Продуктивность",
            "⭐ **Психология миллионеров**\n\nМентальные установки богатых. Как мыслить по-другому.\n\n #Успех #Мышление"
        ],
        "image_queries": ["psychology brain", "mental health", "success mindset", "positive psychology", "emotional intelligence"]
    },
    # 10
    "marketing": {
        "name": "📢 Маркетинг 2025",
        "emoji": "📢",
        "posts": [
            "📢 **Тренды маркетинга 2025**\n\nAI, короткие видео, персонализация. Что работает сейчас.\l\n #Маркетинг #Тренды",
            "💸 **Как получить клиентов из Telegram бесплатно**\n\nСтратегии, партнерства, виральный контент.\n\n #Продвижение #Telegram",
            "🎯 **Таргет который продает**\n\nНастройка в VK и FB: структура и бюджеты.\n\n #Таргет #Контекст",
            "📧 **Email маркетинг конверсия 30%**\n\nКак собирать базу, прогревы, продажи. Примеры.\n\n #EmailМаркетинг",
            "🤖 **AI для маркетинга**\n\nChatGPT пишет тексты, Midjourney создает креативы. Экономия бюджета.\n\n #AIмаркетинг"
        ],
        "image_queries": ["digital marketing strategy", "social media marketing", "online advertising", "marketing analytics", "brand growth"]
    },
    # 11
    "productivity": {
        "name": "⚡ Продуктивность",
        "emoji": "⚡",
        "posts": [
            "⚡ **Как работать 4 часа и успевать всё**\n\nМетодики тайм-менеджмента. Эффективность 300%.\n\n #Продуктивность #ТаймМенеджмент",
            "🎯 **Система GTD: полный разбор**\n\nGetting Things Done. Как организовать задачи.\n\n #GTD #Система",
            "📋 **Notion для жизни: шаблоны**\n\nПланирование, заметки, база знаний. Бесплатные шаблоны.\n\n #Notion #Планирование",
            "🧠 **Pomodoro техника: 25 минут фокуса**\n\nКак работать без выгорания. Лучшие таймеры.\n\n #Pomodoro #Фокус",
            "💎 **10 привычек успешных людей**\n\nУтро, день, вечер. Чек-лист для продуктивности.\n\n #Привычки #Успех"
        ],
        "image_queries": ["productivity tools", "time management", "workspace organization", "task planning", "efficiency concept"]
    },
    # 12
    "design": {
        "name": "🎨 Дизайн UI/UX",
        "emoji": "🎨",
        "posts": [
            "🎨 **Тренды дизайна 2025**\n\nМинимализм, 3D, стекломорфизм, макро-типографика.\n\n #Дизайн #UI #Тренды",
            "🖌️ **Figma: профессиональный дизайн бесплатно**\n\nПолный гайд для начинающих. Компоненты, авто-лейауты.\n\n #Figma #ДизайнИнтерфейсов",
            "🌟 **Как найти первых клиентов на дизайн**\n\nПортфолио, Behance, биржи. Заработок от $1000.\n\n #ДизайнПортфолио #Заработок",
            "🎨 **Секреты психологии цвета**\n\nКак цвета влияют на конверсию. Подбор палитры.\n\n #ПсихологияЦвета #Дизайн",
            "💻 **Лучшие UI/UX инструменты 2025**\n\nFigma, Sketch, Adobe XD, Penpot. Сравнение.\n\n #UIUX #Инструменты"
        ],
        "image_queries": ["ui ux design", "web design trends", "mobile app interface", "color palette design", "user experience concept"]
    },
    # 13
    "startup": {
        "name": "🚀 Стартапы",
        "emoji": "🚀",
        "posts": [
            "🚀 **Как запустить стартап без денег**\n\nMVP, инкубаторы, гранты. Реальная история.\n\n #Стартап #Идеи",
            "💡 **Топ идей для бизнеса 2025**\n\nAI, экология, здоровье. Ниши с потенциалом.\n\n #БизнесИдеи #Предпринимательство",
            "💰 **Привлечение инвестиций: питч-дек**\n\nКак сделать презентацию и получить $1 млн.\n\n #Инвестиции #Венчур",
            "📈 **Кейс: от идеи до $10 млн в год**\n\nПошаговый разбор успеха реального стартапа.\n\n #Кейс #Успех",
            "👥 **Как собрать команду мечты**\n\nГде искать, как мотивировать, как делить доли.\n\n #Команда #Стартап"
        ],
        "image_queries": ["startup pitch deck", "business growth", "entrepreneurship", "innovation lab", "venture capital"]
    },
    # 14
    "finance": {
        "name": "💎 Личные Финансы",
        "emoji": "💎",
        "posts": [
            "💎 **Как накопить миллион за 3 года**\n\nСтратегия, инвестиции, экономия. Реальные цифры.\n\n #Финансы #Накопления",
            "📈 **Инвестиции для начинающих**\n\nАкции, облигации, фонды. Минимальный порог входа.\n\n #Инвестиции #Портфель",
            "💰 **Как избавиться от долгов навсегда**\n\nМетод снежного кома и лавины. Свобода от кредитов.\n\n #Долги #ФинансоваяСвобода",
            "📊 **Бюджетирование: 50/30/20 правило**\n\nПланирование расходов и накоплений.\n\n #Бюджет #Планирование",
            "🏦 **Пассивный доход: 10 способов**\n\nДивиденды, аренда, инвестиции. Работает!\n\n #ПассивныйДоход"
        ],
        "image_queries": ["personal finance", "money saving", "investment portfolio", "financial growth", "wealth management"]
    },
    # 15
    "health": {
        "name": "⚕️ Здоровье",
        "emoji": "⚕️",
        "posts": [
            "⚕️ **10 привычек для долголетия**\n\nПравила 100-летних. Питание, сон, движение.\n\n #Здоровье #Долголетие",
            "💪 **Фитнес дома: 15 минут в день**\n\nКомплексы без оборудования. Результат через месяц.\n\n #Фитнес #ЗОЖ",
            "🥗 **Как питаться вкусно и полезно**\n\nРецепты ПП на каждый день. Просто и быстро.\n\n #ПП #Рецепты",
            "🧘 **Медицина стресса и как победить**\n\nПриемы из нейробиологии. Спокойствие и фокус.\n\n #Стресс #Релакс",
            "😴 **Sleep Hacking: спать 6 часов и высыпаться**\n\nЦиклы сна, мелатонин, темная комната. Советы.\n\n #Сон #Биохакинг"
        ],
        "image_queries": ["healthy lifestyle", "fitness workout", "nutrition food", "wellness concept", "mental health"]
    },
    # 16
    "education": {
        "name": "📚 Образование",
        "emoji": "📚",
        "posts": [
            "📚 **Как выучить английский за 3 месяца**\n\nМетодика 20 слов в день. Реально работает!\n\n #Английский #Обучение",
            "🧠 **Техники запоминания 1000 фактов**\n\nМнемотехника, дворец памяти. Суперпамять.\n\n #Память #Скорочтение",
            "🎓 **5 бесплатных курсов Stanford и MIT**\n\nС сертификатами. Машинное обучение, бизнес.\n\n #Курсы #Образование",
            "📖 **50 книг которые изменят жизнь**\n\nСписок на год. Саморазвитие, бизнес, психология.\n\n #Книги #Саморазвитие",
            "💡 **Как стать экспертом за 6 месяцев**\n\nИнтенсивное погружение, практика, менторы. План.\n\n #Эксперт #Карьера"
        ],
        "image_queries": ["education learning", "study habits", "online courses", "knowledge growth", "academic success"]
    },
    # 17
    "travel": {
        "name": "✈️ Путешествия",
        "emoji": "✈️",
        "posts": [
            "✈️ **Топ-10 мест для посещения в 2025**\n\nЯпония, Новая Зеландия, Исландия. Список мечты.\n\n #Путешествия #Тревел",
            "🏝 **Бюджетные поездки: $500 в месяц**\n\nСекреты тревел-блогеров. Вьетнам, Индия, Мексика.\n\n #БюджетныеПутешествия",
            "🎒 **Как путешествовать и работать**\n\nDigital nomad: лучшие коворкинги и визы.\n\n #ДижиталНомад #Работа",
            "📸 **Секреты идеального тревел-фото**\n\niPhone vs камера, композиция, свет.\n\n #ТревелФото #Фотография",
            "🏔 **Одиночное путешествие: безопасно и круто**\n\nЛучшие направления для соло. Советы и лайфхаки.\n\n #Соло #Тревел"
        ],
        "image_queries": ["travel destinations", "nature landscape", "adventure travel", "beautiful places", "vacation planning"]
    },
    # 18
    "gaming": {
        "name": "🎮 Киберспорт",
        "emoji": "🎮",
        "posts": [
            "🎮 **Игры 2025: топ ожидаемых релизов**\n\nGTA 6, The Witcher 4, Star Wars: Eclipse. Что поиграть.\n\n #Игры #Gaming",
            "🏆 **Киберспорт: как стать профессионалом**\n\nCS2, Dota 2, Valorant. Тренировки, команды, доходы.\n\n #Киберспорт #Про",
            "💻 **Как собрать ПК для игр за $1000**\n\nRTX 4060, Ryzen 5. Оптимальная сборка.\n\n #ИгровойПК #Сборка",
            "📈 **Стриминг: как зарабатывать на Twitch**\n\nНабор аудитории, монетизация. Примеры успеха.\n\n #Twitch #Стриминг",
            "🎯 **Лучшие инди-игры 2025**\n\nСкрытые жемчужины Steam. Стоит попробовать.\n\n #IndieGames #Гейминг"
        ],
        "image_queries": ["gaming setup", "esports tournament", "video game development", "pc gaming", "console gaming"]
    },
    # 19
    "food": {
        "name": "🍳 Кулинария",
        "emoji": "🍳",
        "posts": [
            "🍳 **Ресторанные блюда за 30 минут**\n\nРецепты от шеф-повара. Вкусно и быстро.\n\n #Кулинария #Рецепты",
            "🥘 **Как готовить полезно и бюджетно**\n\nПП рецепты на неделю. Экономия времени и денег.\n\n #ЗОЖ #БюджетноеПитание",
            "🎂 **Торт за 10 минут без выпечки**\n\nРецепт для занятых хозяек. Шоколадный рай.\n\n #Десерты #БезВыпечки",
            "🍜 **Лучшие рестораны 50 стран мира**\n\nГастрономический гид по планетам. Список must visit.\n\n #Рестораны #ТревелЕда",
            "👩‍🍳 **Секреты идеального мяса**\n\nСтейк рибай, прожарка, специи. Мастер-класс.\n\n #Мясо #Стейк"
        ],
        "image_queries": ["gourmet food", "cooking recipes", "kitchen utensils", "food photography", "culinary art"]
    },
    # 20
    "motivation": {
        "name": "💪 Мотивация",
        "emoji": "💪",
        "posts": [
            "💪 **Цитаты которые изменят жизнь**\n\nЭмоциональный интеллект. Статьи от коучей.\n\n #Мотивация #Вдохновение",
            "🔥 **Как не сдаваться когда всё плохо**\n\nМетоды анти-хрупкости. Выдержка и стойкость.\n\n #СилаДуха #Жизнь",
            "⭐ **Утренние ритуалы миллиардеров**\n\nЧто делают успешные люди до 8 утра.\n\n #Привычки #Успех",
            "🎯 **Почему одни достигают целей, а другие нет**\n\nПсихология достижений, курсы и тренинги.\n\n #Цели #Мышление",
            "🌟 **Измени себя за 21 день**\n\nЧеллендж для прокачки жизни. Присоединяйся!\n\n #Челлендж #Изменения"
        ],
        "image_queries": ["motivation quote", "success concept", "inspirational speaker", "personal growth", "positive mindset"]
    }
}

# ==================== РАЗМЕРЫ ====================
IMAGE_SIZES = {
    "small": "400x300", "medium": "800x600", "large": "1200x800", "hd": "1920x1080"
}

# ==================== ХРАНИЛИЩЕ ====================
class CustomTopics:
    def __init__(self):
        self.user_topics = {}
    
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

class BotData:
    def __init__(self):
        self.users = {}
        self.channels = {}
        self.auto_posting = {}
        self.posting_tasks = {}
        self.user_tariffs = {}
        self.daily_post_counts = {}
        self.user_image_size = {}
    
    def init_user(self, user_id: int, username: str, first_name: str):
        if user_id not in self.users:
            self.users[user_id] = {"id": user_id, "username": username, "first_name": first_name, "joined": datetime.now()}
            self.user_tariffs[user_id] = "free"
            self.channels[user_id] = []
            self.daily_post_counts[user_id] = {"date": datetime.now().date(), "count": 0}
    
    def add_channel(self, user_id: int, channel_id: str, channel_title: str):
        tariff = self.user_tariffs.get(user_id, "free")
        max_channels = TARIFFS[tariff]["max_channels"]
        
        if len(self.channels.get(user_id, [])) >= max_channels:
            return False, f"Достигнут лимит каналов"
        
        for ch in self.channels.get(user_id, []):
            if ch["id"] == channel_id:
                return False, "Канал уже добавлен"
        
        self.channels[user_id].append({"id": channel_id, "title": channel_title, "added": datetime.now()})
        return True, "Канал добавлен!"
    
    def get_channels(self, user_id: int):
        return self.channels.get(user_id, [])
    
    def set_auto_posting(self, channel_id: str, user_id: int, topic: str, interval: int, is_active: bool = False):
        self.auto_posting[channel_id] = {
            "user_id": user_id, "topic": topic, "interval": interval,
            "is_active": is_active, "last_post": datetime.now(),
            "last_post_index": 0, "last_image_index": 0
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
    
    def can_post(self, user_id: int) -> bool:
        tariff = self.user_tariffs.get(user_id, "free")
        max_posts = TARIFFS[tariff]["max_posts_per_day"]
        
        today = datetime.now().date()
        if user_id not in self.daily_post_counts or self.daily_post_counts[user_id]["date"] != today:
            self.daily_post_counts[user_id] = {"date": today, "count": 0}
        
        if self.daily_post_counts[user_id]["count"] >= max_posts:
            return False
        
        self.daily_post_counts[user_id]["count"] += 1
        return True

bot_data = BotData()
custom_topics = CustomTopics()

# ==================== ПОИСК КАРТИНОК ====================
class ImageFinder:
    @staticmethod
    async def search_image(query: str, size: str = "800x600"):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://picsum.photos/{size}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return url
        except:
            pass
        return None
    
    @staticmethod
    async def get_random_image(topic: str, user_id: int):
        size = IMAGE_SIZES.get(bot_data.user_tariffs.get(user_id, "free"), "800x600")
        
        all_topics = dict(TOPICS)
        custom = custom_topics.user_topics.get(user_id, {})
        all_topics.update(custom)
        
        topic_data = all_topics.get(topic, TOPICS["nft_art"])
        queries = topic_data.get("image_queries", ["art"])
        query = random.choice(queries)
        
        return await ImageFinder.search_image(query, size)

# ==================== ФОРМАТИРОВАНИЕ ТЕКСТА ====================
def format_text(post_text: str, user_id: int) -> str:
    tariff = bot_data.user_tariffs.get(user_id, "free")
    size = TARIFFS[tariff]["text_size"]
    size_config = TEXT_SIZES.get(size, TEXT_SIZES["medium"])
    
    formatted = size_config["prefix"] + post_text + size_config["suffix"]
    
    # Обрезаем если слишком длинный
    if len(formatted) > size_config["max_length"]:
        formatted = formatted[:size_config["max_length"] - 100] + "\n\n... Читать далее в канале!"
    
    return formatted

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_worker(bot, channel_id: str):
    while True:
        try:
            settings = bot_data.get_auto_settings(channel_id)
            if not settings or not settings.get("is_active"):
                break
            
            current_time = datetime.now()
            last_post = settings.get("last_post", datetime.now() - timedelta(days=1))
            interval_seconds = settings.get("interval", 60)
            
            if (current_time - last_post).total_seconds() >= interval_seconds:
                topic = settings.get("topic", "nft_art")
                user_id = settings.get("user_id")
                
                all_topics = dict(TOPICS)
                custom = custom_topics.user_topics.get(user_id, {})
                all_topics.update(custom)
                
                topic_data = all_topics.get(topic, TOPICS["nft_art"])
                posts = topic_data.get("posts", TOPICS["nft_art"]["posts"])
                
                if posts:
                    # Циклический перебор постов для разнообразия
                    last_index = settings.get("last_post_index", 0)
                    post_index = (last_index + 1) % len(posts)
                    post_text = posts[post_index]
                    settings["last_post_index"] = post_index
                    
                    # Форматируем текст под размер тарифа
                    full_text = format_text(post_text, user_id)
                    
                    if bot_data.can_post(user_id):
                        tariff = bot_data.user_tariffs.get(user_id, "free")
                        
                        if tariff in ["basic", "pro"]:
                            image_url = await ImageFinder.get_random_image(topic, user_id)
                            if image_url:
                                try:
                                    await bot.send_photo(chat_id=channel_id, photo=image_url, caption=full_text)
                                except:
                                    await bot.send_message(chat_id=channel_id, text=full_text)
                            else:
                                await bot.send_message(chat_id=channel_id, text=full_text)
                        else:
                            await bot.send_message(chat_id=channel_id, text=full_text)
                        
                        settings["last_post"] = datetime.now()
                        logger.info(f"✅ Автопост в {channel_id}")
            
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await asyncio.sleep(60)

# ==================== КЛАВИАТУРЫ ====================
async def get_main_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("📝 Написать пост", callback_data="write_post")],
        [InlineKeyboardButton("🔍 Поиск картинок", callback_data="search_images")],
        [InlineKeyboardButton("✨ Создать тему", callback_data="create_topic")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_all_topics_keyboard(user_id: int, channel_id: str = None):
    tariff = bot_data.user_tariffs.get(user_id, "free")
    all_topics = dict(TOPICS)
    custom = custom_topics.user_topics.get(user_id, {})
    all_topics.update(custom)
    
    keyboard = []
    row = []
    for key, data in all_topics.items():
        row.append(InlineKeyboardButton(f"{data['emoji']}", callback_data=f"set_topic_{channel_id}_{key}" if channel_id else f"topic_{key}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    if channel_id:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")])
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("10 сек", callback_data=f"interval_{channel_id}_10"),
         InlineKeyboardButton("30 сек", callback_data=f"interval_{channel_id}_30"),
         InlineKeyboardButton("1 мин", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("5 мин", callback_data=f"interval_{channel_id}_300"),
         InlineKeyboardButton("10 мин", callback_data=f"interval_{channel_id}_600"),
         InlineKeyboardButton("30 мин", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_3600"),
         InlineKeyboardButton("3 часа", callback_data=f"interval_{channel_id}_10800")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    topics_count = len(TOPICS)
    welcome = f"✨ Привет! У меня {topics_count} уникальных тем!\n\nNFT, Telegram, DeFi, Web3, Психология, Маркетинг и другие.\n\nСоздавай свои темы, настраивай автопостинг!"
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=keyboard)

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
        keyboard.append([InlineKeyboardButton(f"{status} {ch['title'][:20]}", callback_data=f"auto_channel_{ch['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await query.edit_message_text("⚙️ Автопостинг\n✅ активен ❌ неактивен", reply_markup=InlineKeyboardMarkup(keyboard))

async def configure_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    settings = bot_data.get_auto_settings(channel_id)
    user_id = query.from_user.id
    
    if settings:
        is_active = settings.get("is_active", False)
        interval = settings.get("interval", 60)
    else:
        is_active = False
        interval = 60
    
    status = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    interval_disp = f"{interval // 60} мин" if interval >= 60 else f"{interval} сек"
    
    text = f"Канал: {channel_id}\nСтатус: {status}\nИнтервал: {interval_disp}\n\nВыберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("🎯 Выбрать тему (20+)", callback_data=f"select_topic_auto_{channel_id}")],
        [InlineKeyboardButton("⏱ Интервал", callback_data=f"change_interval_{channel_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="auto_posting")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def select_topic_for_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_topic_auto_", "")
    keyboard = await get_all_topics_keyboard(query.from_user.id, channel_id)
    await query.edit_message_text("🎯 Выберите тему (20+ тем):", reply_markup=keyboard)

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    topic = "_".join(parts[3:])
    user_id = query.from_user.id
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["topic"] = topic
    else:
        bot_data.set_auto_posting(channel_id, user_id, topic, 60, False)
    
    all_topics = dict(TOPICS)
    custom = custom_topics.user_topics.get(user_id, {})
    all_topics.update(custom)
    topic_name = all_topics.get(topic, TOPICS["nft_art"])["name"]
    
    await query.edit_message_text(f"✅ Тема: {topic_name}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("toggle_auto_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if not settings:
        await query.edit_message_text("❌ Сначала выберите тему")
        return
    
    is_active = not settings.get("is_active", False)
    
    if is_active:
        tariff = bot_data.user_tariffs.get(settings['user_id'], "free")
        min_interval = TARIFFS[tariff]["min_interval"]
        if settings.get("interval", 60) < min_interval:
            await query.edit_message_text(f"❌ Мин. интервал: {min_interval} сек")
            return
        
        bot_data.toggle_auto(channel_id, True)
        await start_auto_posting(context.bot, channel_id)
    else:
        bot_data.toggle_auto(channel_id, False)
        await stop_auto_posting(channel_id)
    
    await query.edit_message_text(f"{'✅ Включен' if is_active else '❌ Выключен'}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("change_interval_", "")
    keyboard = await get_interval_keyboard(channel_id)
    await query.edit_message_text("⏱ Выберите интервал:", reply_markup=keyboard)

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
        await query.edit_message_text(f"❌ Мин. интервал: {min_interval} сек")
        await asyncio.sleep(1)
        await change_interval(update, context)
        return
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["interval"] = interval
    else:
        bot_data.set_auto_posting(channel_id, user_id, "nft_art", interval, False)
    
    await query.edit_message_text(f"✅ Интервал: {interval//60} мин" if interval >= 60 else f"✅ {interval} сек")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def start_auto_posting(bot, channel_id: str):
    if channel_id in bot_data.posting_tasks:
        task = bot_data.posting_tasks[channel_id]
        if not task.done():
            task.cancel()
    task = asyncio.create_task(auto_posting_worker(bot, channel_id))
    bot_data.posting_tasks[channel_id] = task

async def stop_auto_posting(channel_id: str):
    if channel_id in bot_data.posting_tasks:
        task = bot_data.posting_tasks[channel_id]
        if not task.done():
            task.cancel()
        del bot_data.posting_tasks[channel_id]

async def create_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff = bot_data.user_tariffs.get(query.from_user.id, "free")
    if tariff == "free":
        await query.edit_message_text("❌ Доступно на BASIC/PRO")
        return
    
    await query.edit_message_text("✨ Название темы:")
    return WAITING_TOPIC_NAME

async def receive_topic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_name'] = update.message.text
    await update.message.reply_text("📝 Напишите 5-10 постов (каждый с новой строки):")
    return WAITING_TOPIC_POSTS

async def receive_topic_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = [p.strip() for p in update.message.text.split('\n') if p.strip()]
    if len(posts) < 3:
        await update.message.reply_text("❌ Минимум 3 поста")
        return WAITING_TOPIC_POSTS
    context.user_data['new_posts'] = posts
    await update.message.reply_text("🔍 Ключевые слова для картинок (через запятую):")
    return WAITING_TOPIC_QUERIES

async def receive_topic_queries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    queries = [q.strip() for q in update.message.text.split(',') if q.strip()]
    
    name = context.user_data['new_name']
    posts = context.user_data['new_posts']
    
    custom_topics.add_topic(user_id, name, posts, queries)
    
    await update.message.reply_text(f"✅ Тема '{name}' создана! Постов: {len(posts)}")
    
    keyboard = await get_main_keyboard(user_id)
    await update.message.reply_text("Главное меню:", reply_markup=keyboard)
    return ConversationHandler.END

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "💎 Тарифы:\n\n"
    for key, t in TARIFFS.items():
        text += f"{t['name']}\n- {t['max_channels']} каналов\n- от {t['min_interval']} сек\n- {t['max_posts_per_day']} постов/день\n\n"
    
    keyboard = [[InlineKeyboardButton(t['name'], callback_data=f"select_tariff_{k}")] for k, t in TARIFFS.items()]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff = query.data.replace("select_tariff_", "")
    bot_data.user_tariffs[query.from_user.id] = tariff
    await query.edit_message_text(f"✅ Тариф {TARIFFS[tariff]['name']}")
    await asyncio.sleep(1)
    await back_to_main(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tariff = bot_data.user_tariffs.get(user_id, "free")
    channels = len(bot_data.get_channels(user_id))
    active = sum(1 for s in bot_data.auto_posting.values() if s.get("user_id") == user_id and s.get("is_active"))
    
    text = f"👤 Профиль\nТариф: {TARIFFS[tariff]['name']}\nКаналов: {channels}\nАвтопостингов: {active}\n\n20+ тем доступно!"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    today_count = bot_data.daily_post_counts.get(user_id, {}).get('count', 0)
    
    text = f"📊 Статистика\nСегодня постов: {today_count}\n\nВсего тем в боте: {len(TOPICS)}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.edit_message_text("🎯 Главное меню", reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 Отправьте ссылку на канал:\n@username или https://t.me/...")
    context.user_data['adding_channel'] = True

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_input = update.message.text.strip()
    
    if "t.me/" in channel_input:
        channel_id = "@" + channel_input.split("t.me/")[-1]
    else:
        channel_id = channel_input
    
    try:
        chat = await context.bot.get_chat(chat_id=channel_id)
        success, msg = bot_data.add_channel(user.id, str(chat.id), chat.title)
        await update.message.reply_text(f"{'✅' if success else '❌'} {msg}")
        context.user_data['adding_channel'] = False
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("Меню:", reply_markup=keyboard)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def write_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channels = bot_data.get_channels(query.from_user.id)
    if not channels:
        await query.edit_message_text("❌ Нет каналов")
        return
    
    keyboard = [[InlineKeyboardButton(ch['title'][:20], callback_data=f"post_to_{ch['id']}")] for ch in channels[:5]]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await query.edit_message_text("📝 Выберите канал:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("post_to_", "")
    context.user_data['post_channel'] = channel_id
    await query.edit_message_text("📝 Напишите текст поста:")
    context.user_data['awaiting_post'] = True

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channel_id = context.user_data.get('post_channel')
    
    if not channel_id:
        return
    
    text = format_text(update.message.text, user.id)
    
    try:
        await context.bot.send_message(chat_id=channel_id, text=text)
        await update.message.reply_text("✅ Опубликовано")
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")
    
    context.user_data['awaiting_post'] = False
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text("Меню:", reply_markup=keyboard)

async def search_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tariff = bot_data.user_tariffs.get(query.from_user.id, "free")
    if tariff != "pro":
        await query.edit_message_text("❌ Только PRO тариф")
        return
    
    await query.edit_message_text("🔍 Введите запрос для поиска картинки:")
    context.user_data['searching_image'] = True

async def handle_image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query_text = update.message.text.strip()
    
    size = IMAGE_SIZES.get(bot_data.user_tariffs.get(user.id, "free"), "800x600")
    image_url = await ImageFinder.search_image(query_text, size)
    
    if image_url:
        channels = bot_data.get_channels(user.id)
        if channels:
            keyboard = [[InlineKeyboardButton(ch['title'][:15], callback_data=f"send_img_{ch['id']}_{query_text}")] for ch in channels[:3]]
            await update.message.reply_photo(photo=image_url, caption=f"По запросу: {query_text}\nВыберите канал:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_photo(photo=image_url, caption=f"По запросу: {query_text}")
    else:
        await update.message.reply_text("❌ Картинка не найдена")
    
    context.user_data['searching_image'] = False

async def send_search_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    search = "_".join(parts[3:])
    
    size = IMAGE_SIZES.get(bot_data.user_tariffs.get(query.from_user.id, "free"), "800x600")
    image_url = await ImageFinder.search_image(search, size)
    
    if image_url:
        try:
            await context.bot.send_photo(chat_id=channel_id, photo=image_url, caption=f"🔍 {search}\n✨ Подпишитесь!")
            await query.edit_message_text("✅ Отправлено")
        except Exception as e:
            await query.edit_message_text(f"❌ {str(e)}")
    else:
        await query.edit_message_text("❌ Ошибка")
    
    await asyncio.sleep(1)
    await back_to_main(update, context)

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
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "help":
        await query.edit_message_text("📚 20+ тем\nNFT, Crypto, AI, Web3, DeFi, и другие\n\nСоздавайте свои темы!\nНастраивайте автопостинг!")
    elif data.startswith("post_to_"):
        await send_post(update, context)
    elif data.startswith("auto_channel_"):
        await configure_auto(update, context)
    elif data.startswith("select_topic_auto_"):
        await select_topic_for_auto(update, context)
    elif data.startswith("set_topic_"):
        await set_topic(update, context)
    elif data.startswith("toggle_auto_"):
        await toggle_auto(update, context)
    elif data.startswith("change_interval_"):
        await change_interval(update, context)
    elif data.startswith("interval_"):
        await set_interval(update, context)
    elif data.startswith("select_tariff_"):
        await select_tariff(update, context)
    elif data.startswith("send_img_"):
        await send_search_image(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено")
    keyboard = await get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("Меню:", reply_markup=keyboard)

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # ConversationHandler для создания темы
    create_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_topic_start, pattern="^create_topic$")],
        states={
            WAITING_TOPIC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_name)],
            WAITING_TOPIC_POSTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_posts)],
            WAITING_TOPIC_QUERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_queries)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(create_handler)
    
    # Обработчики
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: process_add_channel(u, c) if c.user_data.get('adding_channel')
        else (handle_post(u, c) if c.user_data.get('awaiting_post')
        else (handle_image_search(u, c) if c.user_data.get('searching_image')
        else None))
    ))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот запущен! 20+ тем, автопостинг, свои темы")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
