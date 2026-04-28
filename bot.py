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
import hashlib

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
        "max_channels": 50,
        "min_interval": 10,
        "max_posts_per_day": 5000,
        "features": ["✅ 50 каналов", "✅ Интервал от 10 сек", "✅ 5000 постов/день", "✅ HD картинки", 
                    "✅ Поиск картинок", "✅ Видео", "✅ Репосты", "✅ ИИ контент", "✅ Своя тема"]
    }
}

# ==================== ТЕМЫ С УНИКАЛЬНЫМИ ПОСТАМИ ====================
# Хранилище использованных постов
used_posts = {}

def get_unique_post(topic_key: str, topic_data: dict) -> str:
    """Получить уникальный пост, который не повторялся"""
    posts = topic_data.get("posts", [])
    if not posts:
        return "Новый пост скоро появится!"
    
    # Инициализируем список использованных постов для этой темы
    if topic_key not in used_posts:
        used_posts[topic_key] = []
    
    # Если все посты использованы, сбрасываем
    if len(used_posts[topic_key]) >= len(posts):
        used_posts[topic_key] = []
    
    # Выбираем неиспользованный пост
    available_posts = [p for i, p in enumerate(posts) if i not in used_posts[topic_key]]
    if not available_posts:
        available_posts = posts
    
    post = random.choice(available_posts)
    post_index = posts.index(post)
    used_posts[topic_key].append(post_index)
    
    return post

# ==================== НОВЫЕ ТЕМЫ ====================
TOPICS = {
    "nft": {
        "name": "🎨 NFT Искусство",
        "emoji": "🎨",
        "image_queries": ["nft art", "digital art", "crypto art", "nft collection"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🖼 **Топ-10 самых дорогих NFT 2025**\n\n1. «Everydays» - $69 млн\n2. «Clock» - $52 млн\n3. «Human One» - $28 млн\n4. «CryptoPunk #5822» - $23 млн\n5. «Beeple» - $15 млн\n\n🔥 NFT рынок продолжает расти!\n\n#nft #криптоискусство #цифровоеискусство",
            "🎨 **Как создать свой NFT за 5 минут**\n\nПошаговая инструкция:\n1️⃣ Выберите изображение/видео\n2️⃣ Зарегистрируйтесь на OpenSea\n3️⃣ Загрузите файл\n4️⃣ Настройте роялти (до 10%)\n5️⃣ Выставьте на продажу\n\n💰 Первые продажи уже сегодня!\n\n#nft #каксоздатьnft #заработок",
            "🚀 **Почему NFT не умрут**\n\n3 причины:\n✅ Цифровая собственность\n✅ Уникальность и редкость\n✅ Пассивный доход от роялти\n\nИнвестиции в NFT - это будущее!\n\n#nft #инвестиции #криптовалюта",
            "🌟 **Самые перспективные NFT коллекции 2025**\n\n• Bored Ape Yacht Club\n• CryptoPunks\n• Azuki\n• Pudgy Penguins\n• Moonbirds\n\nВложения окупились за 3 месяца!\n\n#nftколлекции #топnft #инвестиции",
            "💎 **Секреты успешных NFT проектов**\n\nЧто делает проект вирусным:\n✔️ Уникальный дизайн\n✔️ Активное комьюнити\n✔️ Реальные utility\n✔️ Маркетинг в соцсетях\n\nСоздайте свой успешный проект!\n\n#nftпроекты #крипто #успех"
        ]
    },
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "image_queries": ["telegram", "telegram logo", "messenger", "tg"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🚀 **Telegram обновился до версии 10.0**\n\nЧто нового:\n• Автоматический перевод сообщений\n• Бизнес-аккаунты\n• Улучшенные стикеры\n• Групповые видеозвонки до 1000 человек\n\nОбновляйтесь прямо сейчас!\n\n#telegram #обновление #мессенджер",
            "💰 **Как заработать в Telegram 2025**\n\nТоп-5 способов:\n1️⃣ Реклама в каналах\n2️⃣ Платные подписки\n3️⃣ Свой бот-магазин\n4️⃣ Партнерские программы\n5️⃣ Продажа авторских курсов\n\n🔥 Реальные деньги уже сегодня!\n\n#telegram #заработок #бизнес",
            "🤖 **Топ-10 полезных Telegram ботов**\n\n• @vote - опросы\n• @image_search_bot - поиск фото\n• @SaveVideoBot - загрузка видео\n• @utubebot - YouTube в TG\n• @weather_bot - погода\n\n😍 Бесплатно и без рекламы!\n\n#telegramботы #полезное #лайфхак",
            "📈 **Как раскрутить Telegram канал до 100к**\n\nСтратегия роста:\n📊 Регулярный качественный контент\n🤝 Взаимопиар с другими каналами\n💰 Таргетированная реклама\n🎁 Конкурсы и розыгрыши\n\n🏆 Результат через 3 месяца!\n\n#телеграм #раскрутка #продвижение",
            "🔒 **Секретные фишки Telegram**\n\n📱 Скрытые функции:\n• Пересылка с отключенным форвардом\n• Самоуничтожающиеся фото\n• Скрытый номер телефона\n• Папки с чатами\n\n😎 Станьте экспертом Telegram!\n\n#телеграмсекреты #фишки #мессенджер"
        ]
    },
    "crypto": {
        "name": "₿ Криптовалюта",
        "emoji": "₿",
        "image_queries": ["cryptocurrency", "bitcoin", "blockchain", "crypto trading"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "₿ **Биткоин обновил исторический максимум**\n\n💰 BTC достиг $150,000\n📈 Рост на 300% за год\n🔮 Прогноз на 2026: $250,000\n\nПора инвестировать!\n\n#биткоин #криптовалюта #btc",
            "📊 **Топ-10 альткоинов для инвестиций 2025**\n\n1️⃣ Ethereum - $10,000\n2️⃣ Solana - $500\n3️⃣ Cardano - $3\n4️⃣ Polkadot - $50\n5️⃣ Chainlink - $100\n\n🚀 Потенциал роста до 1000%!\n\n#альткоины #инвестиции #крипта",
            "💎 **Как заработать на крипте новичку**\n\nСтратегии:\n✅ Покупка и хранение (HODL)\n✅ Майнинг (ASIC, GPU)\n✅ Стейкинг (6-20% годовых)\n✅ Трейдинг\n\n💰 Начните с $100!\n\n#крипта #заработок #новичкам",
            "🚨 **Срочно! Биткоин-киты активизировались**\n\n🐋 Крупные игроки скупают BTC\n📉 Ожидайте резкий рост\n🎯 Цель: $200,000\n\nНе упустите момент!\n\n#биткоин #аналитика #криптановости",
            "🔮 **Прогноз крипторынка 2026**\n\nПо мнению экспертов:\n• BTC: $250,000-300,000\n• ETH: $15,000-20,000\n• Общая капитализация: $10 трлн\n\nГотовьте кошельки!\n\n#прогноз #криптовалюта #будущее"
        ]
    },
    "defi": {
        "name": "💎 DeFi",
        "emoji": "💎",
        "image_queries": ["defi", "decentralized finance", "blockchain finance"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "💰 **Лучшие DeFi протоколы для пассивного дохода**\n\n• Uniswap - до 50% APY\n• Aave - до 30% APY\n• Curve - до 40% APY\n• Compound - до 25% APY\n\n💸 Зарабатывайте на своих криптоактивах!\n\n#defi #пассивныйдоход #крипта",
            "🌊 **Что такое Yield Farming?**\n\nСтратегия получения дохода:\n1️⃣ Предоставьте ликвидность\n2️⃣ Получите LP токены\n3️⃣ Застейкайте их\n4️⃣ Получайте до 100% годовых\n\n🚀 Ваши деньги работают за вас!\n\n#yieldfarming #defi #заработок",
            "🔒 **Безопасность в DeFi**\n\nКак не потерять деньги:\n✔️ Используйте проверенные протоколы\n✔️ Диверсифицируйте средства\n✔️ Храните ключи отдельно\n✔️ Следите за новостями\n\n💡 Умные инвестиции - безопасные инвестиции!\n\n#defiбезопасность #крипта #советы",
            "📊 **Топ-5 DeFi токенов 2025**\n\n1. UNI - лидер DEX\n2. AAVE - кредитование\n3. MKR - стейблкоины\n4. CRV - стейблсвапы\n5. SNX - синтетика\n\n📈 Потенциал роста огромен!\n\n#defiтокены #инвестиции #крипта",
            "🎯 **Как получить майнинг ликвидности**\n\nПошаговый план:\n• Ищите новые проекты\n• Входите на ранних этапах\n• Предоставляйте LP\n• Собирайте токены\n• Фиксируйте прибыль\n\n💰 Пассивный доход от $1000/месяц!\n\n#майнингликвидности #defi #заработок"
        ]
    },
    "web3": {
        "name": "🌐 Web3",
        "emoji": "🌐",
        "image_queries": ["web3", "blockchain", "decentralized web", "web3 technology"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🌍 **Web3: Интернет будущего уже здесь**\n\nЧто изменится:\n• Децентрализация данных\n• Владельцы контента\n• Токенизация всего\n• DAO управление\n\n✨ Станьте частью новой эры!\n\n#web3 #будущее #технологии",
            "🆔 **Децентрализованные идентификаторы (DID)**\n\nВаша цифровая личность:\n✔️ Полный контроль данных\n✔️ Без посредников\n✔️ Безопасно и приватно\n✔️ Работает во всем мире\n\n🌐 Ваши данные - ваши правила!\n\n#web3 #did #блокчейн",
            "🏛️ **DAO: компании без боссов**\n\nКак работают децентрализованные организации:\n• Управление через голосование\n• Прозрачные финансы\n• Смарт-контракты\n• Общая казна\n\n💎 Будущее корпораций уже здесь!\n\n#dao #web3 #децентрализация",
            "🎮 **Web3 игры: Play-to-Earn 2.0**\n\nТоп проекты 2025:\n• Axie Infinity\n• The Sandbox\n• Decentraland\n• Illuvium\n• Gala Games\n\n💰 Играй и зарабатывай реальные деньги!\n\n#web3игры #p2e #заработок",
            "📱 **Как войти в Web3 сегодня**\n\nПошаговый гайд:\n1️⃣ Установите MetaMask\n2️⃣ Купите немного ETH\n3️⃣ Исследуйте dApps\n4️⃣ Получите ENS домен\n\n🚀 Не отставайте от прогресса!\n\n#web3 #гайд #блокчейн"
        ]
    },
    "memes": {
        "name": "😄 Мемы Крипта",
        "emoji": "😄",
        "image_queries": ["crypto meme", "bitcoin meme", "dogecoin", "memecoin"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🐕 **Dogecoin взлетел на 500%**\n\nИлон Маск снова твитнул про DOGE! Мемкоины бессмертны. Кто купил на дне? 🚀\n\n#dogecoin #мемкоины #илонмаск",
            "🪙 **Памятка криптоинвестора**\n\nКогда BTC падает: «Купи дешевле»\nКогда BTC растет: «Купи дороже»\nРезультат: денег нет, но вы держитесь 😂\n\n#криптомемы #биткоин #юмор",
            "🐸 **Pepe вернулся? PEPE вырос на 1000%**\n\nИнтернет помнит! Лягушонок снова в деле. Успели заскочить? 🐸🚀\n\n#pepe #мемкоины #крипта",
            "💎 **Бриллиантовые ручки**\n\nКогда весь рынок падает, а вы HODL:\n«Бриллиантовые руки не продают на дне»\n😎 А герои не сдаются!\n\n#hodl #бриллиантовыеручки #крипта",
            "🎢 **Американские горки биткоина**\n\nКупил на хае, продал на дне\nПеревел на биржу, забыл пароль\nНашел, увидел +1000%\n\nОбычный день криптоинвестора 😅\n\n#биткоин #криптоюмор #мемы"
        ]
    },
    "blockchain": {
        "name": "⛓️ Блокчейн",
        "emoji": "⛓️",
        "image_queries": ["blockchain", "blockchain technology", "distributed ledger"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "⛓️ **Что такое блокчейн простыми словами**\n\nПредставьте общую тетрадь, которую нельзя подделать. Каждая запись связана с предыдущей и хранится у миллионов людей.\n\n✅ Прозрачно\n✅ Безопасно\n✅ Нельзя изменить\n\n#блокчейн #технологии #обучение",
            "🔗 **Как работают смарт-контракты**\n\nЭто цифровые контракты, которые исполняются автоматически при выполнении условий.\n\nПример: Отправил деньги → получил товар\n\nНикаких посредников и обмана!\n\n#смартконтракты #блокчейн #децентрализация",
            "⚡ **Масштабируемость блокчейна: решения 2025**\n\n• Sharding (фрагментация)\n• Layer 2 решения\n• Sidechains\n• Новые консенсусы\n\n🚀 Блокчейн готов к миллиарду пользователей!\n\n#масштабируемость #блокчейн #технологии",
            "🔐 **Криптография в блокчейне**\n\nКак обеспечивается безопасность:\n• Хэширование SHA-256\n• Асимметричное шифрование\n• Цифровые подписи\n• Консенсус Proof-of-Work\n\n💰 Ваши средства под надежной защитой!\n\n#криптография #безопасность #блокчейн",
            "🌿 **Экологичный блокчейн**\n\nРешение проблемы энергопотребления:\n• Proof-of-Stake (99% энергии)\n• Зеленый майнинг\n• Углеродная нейтральность\n\n💚 Сохраняем планету вместе!\n\n#эко #блокчейн #зеленый"
        ]
    },
    "gaming": {
        "name": "🎮 GameFi",
        "emoji": "🎮",
        "image_queries": ["gamefi", "crypto gaming", "play to earn", "nft game"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🎮 **Топ-10 GameFi проектов 2025**\n\n1. Axie Infinity\n2. The Sandbox\n3. Decentraland\n4. Illuvium\n5. Star Atlas\n6. Gala Games\n7. My Neighbor Alice\n8. Big Time\n9. Heroes of Mavia\n10. Gods Unchained\n\n💰 Зарабатывай играя!\n\n#gamefi #playtoearn #криптоигры",
            "💎 **Как заработать $1000 в месяц в Play-to-Earn**\n\nСтратегия:\n• Выберите проект\n• Изучите механику\n• Инвестируйте время\n• Повышайте уровень\n• Продавайте токены\n\n🎮 Игры приносят реальные деньги!\n\n#playtoearn #gamefi #заработок",
            "🏆 **Самые дорогие игровые NFT**\n\n• Axie - $1.5 млн\n• The Sandbox LAND - $500k\n• CryptoKitties - $390k\n• Gods Unchained - $250k\n\n🖼 Ваши скины и персонажи - это активы!\n\n#геймингnft #крипто #игры",
            "⚡ **Будущее GameFi**\n\nТренды 2025-2026:\n• AAA проекты от крупных студий\n• VR и AR интеграция\n• Кроссплатформенность\n• Реальная экономика\n\n🎮 Игровая индустрия меняется!\n\n#gamefi #будущее #криптоигры",
            "🆓 **Бесплатные Play-to-Earn игры**\n\nНачните без вложений:\n• Alien Worlds\n• Splinterlands\n• Gods Unchained\n• Upland\n• Blankos Block Party\n\n💰 Зарабатывайте с нуля!\n\n#freeplaytoearn #gamefi #заработок"
        ]
    },
    "metaverse": {
        "name": "🌌 Метавселенная",
        "emoji": "🌌",
        "image_queries": ["metaverse", "virtual reality", "vr world", "digital world"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🌍 **Топ-5 метавселенных 2025**\n\n1. The Sandbox\n2. Decentraland\n3. Somnium Space\n4. Voxels\n5. Wilder World\n\n🚀 Покупайте землю сейчас - цены вырастут!\n\n#метавселенная #thesandbox #decentraland",
            "🏠 **Инвестиции в виртуальную недвижимость**\n\nЦены на LAND в 2025:\n• Sandbox: $50,000+\n• Decentraland: $30,000+\n• Somnium: $20,000+\n\n📈 Рост 1000% за год!\n\n#виртуальнаянедвижимость #метавселенная #инвестиции",
            "🕶️ **Как начать жить в метавселенной**\n\nГайд для начинающих:\n1️⃣ Купите VR шлем\n2️⃣ Создайте аватар\n3️⃣ Выберите платформу\n4️⃣ Приобретите землю\n5️⃣ Зарабатывайте на аренде\n\n💫 Добро пожаловать в будущее!\n\n#метавселенная #vr #будущее",
            "💼 **Бизнес в метавселенной**\n\nИдеи для заработка:\n• Виртуальная аренда\n• NFT галереи\n• Проведение мероприятий\n• Внутриигровая экономика\n\n💰 Реальный бизнес в виртуальном мире!\n\n#бизнесвметавселенной #заработок",
            "🔮 **Будущее метавселенных**\n\nЧто нас ждет к 2030:\n• Полное погружение через нейроинтерфейсы\n• Общая экономика\n• Виртуальные рабочие места\n• Цифровое гражданство\n\n🌌 Это уже реальность!\n\n#метавселенная #будущее #технологии"
        ]
    },
    "staking": {
        "name": "💰 Стейкинг",
        "emoji": "💰",
        "image_queries": ["crypto staking", "staking rewards", "passive income crypto"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "💰 **Лучшие монеты для стейкинга 2025**\n\n• Ethereum - 5% APY\n• Solana - 7% APY\n• Cardano - 5% APY\n• Polkadot - 14% APY\n• Cosmos - 17% APY\n\n💎 Пассивный доход без рисков!\n\n#стейкинг #пассивныйдоход #крипта",
            "📊 **Сравнение доходности стейкинга**\n\nТоп-10 криптовалют:\n1. Cosmos - 17%\n2. Polkadot - 14%\n3. Solana - 7%\n4. Avalanche - 8%\n5. Polygon - 6%\n\n💸 Ваши токены работают на вас!\n\n #доходностьстейкинга #крипта",
            "🔒 **Пошаговый гайд: как начать стейкинг**\n\n1️⃣ Купите криптовалюту\n2️⃣ Выберите кошелек (Ledger, MetaMask)\n3️⃣ Перейдите в раздел стейкинга\n4️⃣ Выберите валидатора\n5️⃣ Застейкайте токены\n\n✅ Стабильный доход от 5% годовых!\n\n#стейкинггайд #пассивныйдоход",
            "⚠️ **Риски стейкинга и как их избежать**\n\nОсновные риски:\n• Слэшинг (штрафы)\n• Падение цены токена\n• Ликвидность (заморозка)\n• Валидаторы-мошенники\n\n💡 Диверсифицируйте и проверяйте!\n\n #рискистейкинга #безопасность",
            "🚀 **Лучшие платформы для стейкинга**\n\nCEX (битки):\n• Binance - 20+ монет\n• Kraken - 15+ монет\n\nDeFi:\n• Lido\n• Rocket Pool\n• Aave\n\n🔐 Храните ключи на кошельках!\n\n #платформыстейкинга #defi"
        ]
    },
    "airdrop": {
        "name": "🎁 Аирдропы",
        "emoji": "🎁",
        "image_queries": ["crypto airdrop", "free crypto", "airdrop claim"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "🎁 **Топ-10 аирдропов 2025 года**\n\nСамые ожидаемые:\n1. LayerZero - $100k+\n2. zkSync - $50k+\n3. Scroll - $30k+\n4. Starknet - $20k+\n5. Arbitrum - $15k+\n\n💰 Бесплатные токены от стартапов!\n\n#аирдропы #бесплатнокрипта #заработок",
            "🪂 **Как получить аирдроп на $10,000**\n\nСтратегия:\n• Используйте новые протоколы\n• Делайте транзакции (~$50-100)\n• Предоставляйте ликвидность\n• Участвуйте в тестнетах\n• Будьте ранним пользователем\n\n💎 Пассивный доход с нуля!\n\n #какполучитьаирдроп #заработок",
            "✅ **Чек-лист: Готовимся к аирдропу**\n\nДо начала:\n⚡️ Зарегистрируйте ENS\n⚡️ Пополните кошелек ($100-200)\n⚡️ Сделайте 10-20 транзакций\n⚡️ Застейкайте токены\n⚡️ Вступайте в Discord/Twitter\n\n🎯 Максимизируйте дроп!\n\n #аирдропчеклист #подготовка",
            "⚠️ **Как отличить реальный аирдроп от скама**\n\nКрасные флаги:\n❌ Просят приватный ключ\n❌ Требуют оплату\n❌ Подозрительные ссылки\n❌ Непроверенные проекты\n\n✅ Только официальные источники!\n\n #безопасностьаирдропов #скам",
            "📈 **Лучшие аирдропы прошлого года**\n\nИстории успеха:\n• Arbitrum - $10,000+\n• Aptos - $5,000+\n• Optimism - $3,000+\n• Blur - $20,000+\n\n💰 Вы тоже можете получить токены!\n\n #успешныеаирдропы #кейсы"
        ]
    },
    "trading": {
        "name": "📈 Трейдинг",
        "emoji": "📈",
        "image_queries": ["crypto trading", "trading chart", "technical analysis"],
        "post_sizes": ["Короткий", "Средний", "Полный"],
        "posts": [
            "📊 **Прогноз биткоина на неделю**\n\nBTC текущий: $150,000\n• Сопротивление: $160,000\n• Поддержка: $140,000\n• Цель до конца месяца: $180,000\n\n📉 Тренд восходящий! Покупаем на откатах.\n\n #биткоинпрогноз #btc #трейдинг",
            "💹 **Топ-5 индикаторов для прибыльной торговли**\n\n1. RSI - перекупленность/перепроданость\n2. MACD - направление тренда\n3. Bollinger Bands - волатильность\n4. Moving Averages - поддержка/сопротивление\n5. Volume - подтверждение сигналов\n\n📈 Стабильная прибыль 20% в месяц!\n\n #индикаторы #трейдинг #аналитика",
            "🎯 **Стратегия скальпинга на 5 минут**\n\nАлгоритм:\n1️⃣ Только по тренду\n2️⃣ Тейк-профит 0.5-1%\n3️⃣ Стоп-лосс 0.3%\n4️⃣ 3-5 сделок в день\n5️⃣ Не трейдить новости\n\n💰 5-10% стабильно!\n\n #скальпинг #стратегия #трейдинг",
            "🚨 **Сигнал: Биткоин пробил сопротивление**\n\n$150,000 - новый уровень\nСледующая цель: $200,000\n\nПоддержки:\n• $145,000\n• $140,000\n• $135,000\n\n🎯 Цель по тейку: $180,000\n\n #сигнал #биткоин #трейдинг",
            "💡 **10 ошибок новичков в трейдинге**\n\n❌ FOMO (страх упустить)\n❌ Отсутствие стоп-лосса\n❌ Усреднение убыточных позиций\n❌ Перегрузка депозита\n❌ Трейдинг на заемные средства\n\n✅ Учитесь на ошибках других!\n\n #ошибкитрейдинга #новичкам"
        ]
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
        self.user_custom_topics = {}  # Свои темы пользователей
        
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
            self.user_custom_topics[user_id] = {}
    
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
    
    def set_auto_posting(self, channel_id: str, user_id: int, topic: str, interval: int, 
                         post_size: str = "Средний", is_active: bool = False):
        self.auto_posting[channel_id] = {
            "user_id": user_id,
            "topic": topic,
            "interval": interval,
            "is_active": is_active,
            "last_post": datetime.now(),
            "channel_title": self.get_channel_title(user_id, channel_id),
            "include_images": True,
            "post_size": post_size,
            "custom_topic": None
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
    
    def add_custom_topic(self, user_id: int, topic_name: str, posts: list, image_queries: list):
        if user_id not in self.user_custom_topics:
            self.user_custom_topics[user_id] = {}
        
        topic_key = f"custom_{len(self.user_custom_topics[user_id]) + 1}"
        self.user_custom_topics[user_id][topic_key] = {
            "name": topic_name,
            "emoji": "📝",
            "posts": posts,
            "image_queries": image_queries,
            "post_sizes": ["Короткий", "Средний", "Полный"],
            "is_custom": True
        }
        return topic_key

bot_data = BotData()

# ==================== ПОИСК КАРТИНОК ====================
class ImageFinder:
    @staticmethod
    async def search_image(query: str):
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
    async def get_random_image(topic: str, topic_data: dict):
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

# ==================== АВТОПОСТИНГ ====================
async def auto_posting_worker(bot, channel_id: str):
    while True:
        try:
            settings = bot_data.get_auto_settings(channel_id)
            if not settings or not settings.get("is_active", False):
                break
            
            current_time = datetime.now()
            last_post = settings.get("last_post", datetime.now() - timedelta(days=1))
            interval_seconds = settings.get("interval", 60)
            
            if (current_time - last_post).total_seconds() >= interval_seconds:
                topic = settings.get("topic", "nft")
                post_size = settings.get("post_size", "Средний")
                
                # Получаем данные темы
                if topic.startswith("custom_"):
                    user_id = settings.get("user_id")
                    topic_data = bot_data.user_custom_topics.get(user_id, {}).get(topic, {})
                else:
                    topic_data = TOPICS.get(topic, TOPICS["nft"])
                
                # Получаем уникальный пост
                if topic_data:
                    post_text = get_unique_post(topic, topic_data)
                    
                    # Добавляем призыв
                    footer = f"\n\n✨ Подписывайтесь! Еще больше интересного контента\n#autoposting"
                    full_text = post_text + footer
                    
                    user_id = settings.get("user_id")
                    tariff = bot_data.user_tariffs.get(user_id, "free")
                    
                    if bot_data.can_post(user_id):
                        if tariff == "pro" and settings.get("include_images", True):
                            image_url = await bot_images.get_random_image(topic, topic_data)
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
                        logger.info(f"✅ Пост отправлен в {channel_id}")
            
            await asyncio.sleep(min(interval_seconds, 30))
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
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
        [InlineKeyboardButton("🎨 Мои темы", callback_data="my_topics")],
        [InlineKeyboardButton("⚙️ Автопостинг", callback_data="auto_posting")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_topics_keyboard(channel_id: str = None):
    keyboard = []
    for topic_key, topic_data in TOPICS.items():
        keyboard.append([
            InlineKeyboardButton(f"{topic_data['emoji']} {topic_data['name']}", 
                               callback_data=f"topic_{channel_id}_{topic_key}" if channel_id else f"select_topic_{topic_key}")
        ])
    
    # Добавляем свои темы пользователя
    if channel_id:
        user_id = int(channel_id.split('_')[0]) if '_' in channel_id else 0
        if user_id and user_id in bot_data.user_custom_topics:
            for custom_key, custom_data in bot_data.user_custom_topics[user_id].items():
                keyboard.append([
                    InlineKeyboardButton(f"📝 {custom_data['name']}", 
                                       callback_data=f"topic_{channel_id}_{custom_key}")
                ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="auto_posting" if channel_id else "back_main")])
    return InlineKeyboardMarkup(keyboard)

async def get_post_sizes_keyboard(channel_id: str, topic: str):
    keyboard = [
        [InlineKeyboardButton("📄 Короткий (до 500 симв)", callback_data=f"size_{channel_id}_{topic}_Короткий")],
        [InlineKeyboardButton("📚 Средний (500-1000 симв)", callback_data=f"size_{channel_id}_{topic}_Средний")],
        [InlineKeyboardButton("📖 Полный (1000-2000 симв)", callback_data=f"size_{channel_id}_{topic}_Полный")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"select_topic_auto_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_interval_keyboard(channel_id: str):
    keyboard = [
        [InlineKeyboardButton("10 сек (PRO)", callback_data=f"interval_{channel_id}_10")],
        [InlineKeyboardButton("30 сек (BASIC)", callback_data=f"interval_{channel_id}_30")],
        [InlineKeyboardButton("1 мин", callback_data=f"interval_{channel_id}_60")],
        [InlineKeyboardButton("5 мин", callback_data=f"interval_{channel_id}_300")],
        [InlineKeyboardButton("10 мин", callback_data=f"interval_{channel_id}_600")],
        [InlineKeyboardButton("30 мин", callback_data=f"interval_{channel_id}_1800")],
        [InlineKeyboardButton("1 час", callback_data=f"interval_{channel_id}_3600")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"auto_channel_{channel_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_auto_channels_keyboard(user_id: int):
    channels = bot_data.get_channels(user_id)
    keyboard = []
    for ch in channels:
        settings = bot_data.get_auto_settings(ch['id'])
        status = "✅" if settings and settings.get("is_active") else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {ch['title']}", callback_data=f"auto_channel_{ch['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.init_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!*\n\n"
        f"🤖 *Я бот для автопостинга с уникальными темами*\n\n"
        f"📋 *Мои возможности:*\n"
        f"• 📝 Ручная публикация постов\n"
        f"• 🔍 Поиск картинок\n"
        f"• 🎨 15+ тем с уникальными постами\n"
        f"• 📏 Выбор размера постов\n"
        f"• 🎯 Создание своей темы (PRO)\n"
        f"• ⚙️ Автопостинг от 10 сек\n"
        f"• 💎 Бесплатные тарифы\n\n"
        f"🚀 *Новые темы:* NFT, Telegram, Крипта, DeFi, Web3, Мемы, Блокчейн, GameFi и другие!\n\n"
        f"Начните с добавления канала в меню 'Мои каналы'"
    )
    
    keyboard = await get_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 *Добавление канала*\n\n"
        "1️⃣ Добавьте бота в канал как администратора\n"
        "2️⃣ Отправьте ссылку на канал\n\n"
        "Примеры:\n"
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
            await update.message.reply_text(f"✅ *{message}*\n\n📢 {chat.title}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ {message}")
        
        context.user_data['adding_channel'] = False
        keyboard = await get_main_keyboard(user.id)
        await update.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)
        
    except Exception as e:
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='Markdown')

async def auto_posting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = await get_auto_channels_keyboard(query.from_user.id)
    await query.edit_message_text(
        "⚙️ *Настройка автопостинга*\n\n"
        "✅ - активен\n"
        "❌ - неактивен\n\n"
        "Выберите канал:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def configure_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("auto_channel_", "")
    settings = bot_data.get_auto_settings(channel_id)
    
    if settings:
        is_active = settings.get("is_active", False)
        interval = settings.get("interval", 60)
        topic = settings.get("topic", "nft")
        post_size = settings.get("post_size", "Средний")
        include_images = settings.get("include_images", True)
        
        if topic.startswith("custom_"):
            user_id = settings.get("user_id")
            topic_name = bot_data.user_custom_topics.get(user_id, {}).get(topic, {}).get("name", "Своя тема")
        else:
            topic_name = TOPICS.get(topic, TOPICS["nft"])["name"]
    else:
        is_active = False
        interval = 60
        topic = "nft"
        post_size = "Средний"
        include_images = True
        topic_name = TOPICS["nft"]["name"]
    
    status_text = "✅ АКТИВЕН" if is_active else "❌ НЕАКТИВЕН"
    interval_display = f"{interval // 60} мин" if interval >= 60 else f"{interval} сек"
    
    text = (
        f"⚙️ *Настройки автопостинга*\n\n"
        f"📢 Канал: {channel_id}\n"
        f"🔄 Статус: {status_text}\n"
        f"📝 Тема: {topic_name}\n"
        f"📏 Размер: {post_size}\n"
        f"⏱ Интервал: {interval_display}\n"
        f"🖼 Картинки: {'✅ Да' if include_images else '❌ Нет'}\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"toggle_auto_{channel_id}")],
        [InlineKeyboardButton("🎯 Выбрать тему", callback_data=f"select_topic_auto_{channel_id}")],
        [InlineKeyboardButton("📏 Размер постов", callback_data=f"select_size_{channel_id}")],
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
    
    keyboard = await get_topics_keyboard(channel_id)
    await query.edit_message_text(
        "📝 *Выберите тему для автопостинга:*\n\n"
        "• NFT, Telegram, Криптовалюта\n"
        "• DeFi, Web3, Мемы\n"
        "• Блокчейн, GameFi и другие",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def select_post_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.replace("select_size_", "")
    settings = bot_data.get_auto_settings(channel_id)
    current_topic = settings.get("topic", "nft") if settings else "nft"
    
    keyboard = await get_post_sizes_keyboard(channel_id, current_topic)
    await query.edit_message_text(
        "📏 *Выберите размер постов:*\n\n"
        "• Короткий - быстрые новости\n"
        "• Средний - стандартный пост\n"
        "• Полный - подробная статья",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def set_post_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    topic = parts[2]
    size = parts[3]
    
    settings = bot_data.get_auto_settings(channel_id)
    if settings:
        settings["post_size"] = size
    else:
        bot_data.set_auto_posting(channel_id, query.from_user.id, topic, 60, size, False)
    
    await query.edit_message_text(f"✅ Размер постов: {size}")
    await asyncio.sleep(1)
    await configure_auto(update, context)

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[1]
    topic = parts[2]
    user_id = query.from_user.id
    
    # Получаем размер из настроек или ставим по умолчанию
    settings = bot_data.get_auto_settings(channel_id)
    current_size = settings.get("post_size", "Средний") if settings else "Средний"
    
    if settings:
        settings["topic"] = topic
    else:
        bot_data.set_auto_posting(channel_id, user_id, topic, 60, current_size, False)
    
    if topic.startswith("custom_"):
        topic_data = bot_data.user_custom_topics.get(user_id, {}).get(topic, {})
        topic_name = topic_data.get("name", "Своя тема")
    else:
        topic_name = TOPICS.get(topic, TOPICS["nft"])["name"]
    
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
        bot_data.set_auto_posting(channel_id, user_id, "nft", interval, "Средний", False)
    
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
        text += f"⏱ Мин интервал: {tariff_info['min_interval']} сек\n"
        text += f"📢 Макс каналов: {tariff_info['max_channels']}\n"
        text += f"📝 Постов в день: {tariff_info['max_posts_per_day']}\n"
        text += "✨ Возможности:\n"
        for feature in tariff_info['features']:
            text += f"  {feature}\n"
        text += "\n"
    
    text += "🎁 *Все тарифы бесплатны!*\n\n💡 PRO дает доступ к своим темам и картинкам"
    
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
        f"✅ *Тариф обновлен!*\n\nВаш тариф: {TARIFFS[tariff_key]['name']}",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(user_id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

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

# ==================== ГЛАВНЫЙ ОБРАБОТЧИК ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "back_main":
        await back_to_main(update, context)
    elif data == "write_post":
        await query.edit_message_text("📝 Напишите пост и отправьте его боту", parse_mode='Markdown')
        context.user_data['awaiting_post'] = True
    elif data == "search_images":
        await query.edit_message_text("🔍 Введите ключевое слово для поиска картинки", parse_mode='Markdown')
        context.user_data['searching_image'] = True
    elif data == "my_channels":
        keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"channel_{ch['id']}")] 
                    for ch in bot_data.get_channels(query.from_user.id)]
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
        await query.edit_message_text("📢 *Ваши каналы*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_channel":
        await add_channel_start(update, context)
    elif data == "auto_posting":
        await auto_posting_menu(update, context)
    elif data == "tariffs":
        await show_tariffs(update, context)
    elif data == "profile":
        user_id = query.from_user.id
        user = bot_data.users.get(user_id, {})
        tariff = bot_data.user_tariffs.get(user_id, "free")
        channels = bot_data.get_channels(user_id)
        text = f"👤 *Профиль*\n\n📝 {user.get('first_name')}\n💎 {TARIFFS[tariff]['name']}\n📢 Каналов: {len(channels)}/{TARIFFS[tariff]['max_channels']}"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "stats":
        user_id = query.from_user.id
        channels = bot_data.get_channels(user_id)
        active = sum(1 for ch in channels if bot_data.get_auto_settings(ch['id']) and bot_data.get_auto_settings(ch['id']).get("is_active"))
        text = f"📊 *Статистика*\n\n📢 Каналов: {len(channels)}\n⚙️ Активных: {active}\n📝 Постов сегодня: {bot_data.daily_post_counts.get(user_id, {}).get('count', 0)}"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "my_topics":
        user_id = query.from_user.id
        tariff = bot_data.user_tariffs.get(user_id, "free")
        if tariff != "pro":
            await query.edit_message_text("❌ Свои темы доступны только на PRO тарифе", parse_mode='Markdown')
            return
        
        await query.edit_message_text(
            "🎨 *Создание своей темы*\n\n"
            "Отправьте:\n"
            "1️⃣ Название темы\n"
            "2️⃣ 5+ постов (каждый с новой строки)\n"
            "3️⃣ Ключевые слова для поиска картинок\n\n"
            "Пример:\n"
            "Тема: Космос\n"
            "Пост 1: Текст...\n"
            "Пост 2: Текст...\n"
            "Ключи: space, galaxy, cosmos",
            parse_mode='Markdown'
        )
        context.user_data['creating_custom_topic'] = True
    elif data == "help":
        text = (
            "ℹ️ *Помощь*\n\n"
            "📋 *Доступные темы:*\n"
            "• NFT, Telegram, Криптовалюта\n"
            "• DeFi, Web3, Мемы\n"
            "• Блокчейн, GameFi, Метавселенная\n"
            "• Стейкинг, Аирдропы, Трейдинг\n\n"
            "🎯 *Возможности:*\n"
            "• Выбор размера постов\n"
            "• Автоматические картинки\n"
            "• Своя тема (PRO)\n"
            "• Автопостинг от 10 сек\n\n"
            "💡 *PRO тариф:*\n"
            "• 50 каналов\n"
            "• Интервал от 10 сек\n"
            "• Свои темы\n"
            "• Картинки к постам"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    elif data.startswith("auto_channel_"):
        await configure_auto(update, context)
    elif data.startswith("select_topic_auto_"):
        await select_topic_for_auto(update, context)
    elif data.startswith("select_size_"):
        await select_post_size(update, context)
    elif data.startswith("size_"):
        await set_post_size(update, context)
    elif data.startswith("topic_"):
        parts = data.split("_")
        if len(parts) == 3:
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

async def get_channels_keyboard(user_id: int):
    channels = bot_data.get_channels(user_id)
    keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"channel_{ch['id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('adding_channel'):
        await process_add_channel(update, context)
    elif context.user_data.get('awaiting_post'):
        channel_id = context.user_data.get('post_channel')
        if not channel_id:
            # Нужно выбрать канал
            channels = bot_data.get_channels(update.effective_user.id)
            if not channels:
                await update.message.reply_text("❌ Сначала добавьте канал")
                return
            keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"post_to_{ch['id']}")] for ch in channels]
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
            await update.message.reply_text("📝 *Выберите канал:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data['temp_post_text'] = update.message.text
        else:
            # Отправляем пост
            try:
                await context.bot.send_message(chat_id=channel_id, text=update.message.text)
                await update.message.reply_text("✅ Пост опубликован!")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data['awaiting_post'] = False
            context.user_data['post_channel'] = None
    elif context.user_data.get('searching_image'):
        await handle_image_search(update, context)
    elif context.user_data.get('creating_custom_topic'):
        await handle_custom_topic(update, context)

async def handle_image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.message.text.strip()
    
    tariff = bot_data.user_tariffs.get(user.id, "free")
    if tariff != "pro":
        await update.message.reply_text("❌ Поиск картинок доступен на PRO тарифе")
        context.user_data['searching_image'] = False
        return
    
    channels = bot_data.get_channels(user.id)
    if not channels:
        await update.message.reply_text("❌ Сначала добавьте канал")
        context.user_data['searching_image'] = False
        return
    
    keyboard = [[InlineKeyboardButton(f"📢 {ch['title']}", callback_data=f"send_image_{ch['id']}_{query}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await update.message.reply_text(f"🔍 Ищу картинки по запросу '{query}'...\n\nВыберите канал:", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['searching_image'] = Falseasync def send_image_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    channel_id = parts[2]
    search_query = parts[3]
    
    await query.edit_message_text(f"🖼 Ищу картинку...")
    
    image_url = await bot_images.search_image(search_query)
    
    if image_url:
        try:
            await context.bot.send_photo(chat_id=channel_id, photo=image_url, caption=f"🖼 {search_query}\n\n✨ Подписывайтесь!")
            await query.edit_message_text("✅ Картинка отправлена!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    else:
        await query.edit_message_text("❌ Не удалось найти картинку")
    
    await asyncio.sleep(2)
    keyboard = await get_main_keyboard(query.from_user.id)
    await query.message.reply_text("🎯 Главное меню:", reply_markup=keyboard)

async def handle_custom_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if 'custom_topic_data' not in context.user_data:
        context.user_data['custom_topic_data'] = {}
        await update.message.reply_text("📝 Введите название темы:")
        return
    
    if 'name' not in context.user_data['custom_topic_data']:
        context.user_data['custom_topic_data']['name'] = text
        await update.message.reply_text("📝 Введите 5+ постов (каждый с новой строки):")
        return
    
    if 'posts' not in context.user_data['custom_topic_data']:
        posts = text.split('\n')
        if len(posts) < 5:
            await update.message.reply_text("❌ Нужно минимум 5 постов. Попробуйте еще раз:")
            return
        context.user_data['custom_topic_data']['posts'] = posts
        await update.message.reply_text("🔍 Введите ключевые слова для поиска картинок (через запятую):")
        return
    
    if 'keywords' not in context.user_data['custom_topic_data']:
        keywords = [k.strip() for k in text.split(',')]
        context.user_data['custom_topic_data']['keywords'] = keywords
        
        # Сохраняем тему
        data = context.user_data['custom_topic_data']
        topic_key = bot_data.add_custom_topic(user.id, data['name'], data['posts'], data['keywords'])
        
        await update.message.reply_text(
            f"✅ *Своя тема создана!*\n\n"
            f"📝 Название: {data['name']}\n"
            f"📊 Постов: {len(data['posts'])}\n"
            f"🔍 Ключи: {', '.join(data['keywords'])}\n\n"
            f"Теперь выберите эту тему в настройках автопостинга!",
            parse_mode='Markdown'
        )
        
        context.user_data['creating_custom_topic'] = False
        del context.user_data['custom_topic_data']

# ==================== ЗАПУСК ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчики
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: None))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🚀 Бот запущен!")
    logger.info("✅ 15+ тем с уникальными постами")
    logger.info("🎨 NFT, Telegram, Крипта, DeFi, Web3, Мемы и другие")
    logger.info("📏 Выбор размера постов")
    logger.info("🖼 Поддержка картинок")
    logger.info("🎯 Свои темы для PRO")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
