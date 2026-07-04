import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Твой токен
TOKEN = "8800738908:AAGi-AbB2OYPEEbUtv37C8kNE78JZ-am9J8"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временная БД (очищается при перезапуске скрипта)
users_db = {}

RATING_LIMITS = {
    1: 2,
    2: 4,
    3: 7,
    4: 12,
    5: 30  # Максимум 30 игроков, чтобы статистика не превышала лимит сообщения Telegram
}

# Генераторы вымышленных имен и названий бизнесов
F_NAMES = ["Леон", "Оливер", "Макс", "Джулиан", "Эван", "Кристиан", "Алан", "Томас", "Мартин", "Дэвид"]
L_NAMES = ["Кросс", "Блэйк", "Стил", "Вэнс", "Риверс", "Фокс", "Хант", "Шоу", "Прайс", "Уорд"]
BIZ_TYPES = ["Сеть ресторанов", "Сеть спортзалов", "Бренд одежды", "Киберспорт-клуб", "Академия футбола", "Агентство недвижимости", "Сеть барбершопов"]

def get_main_menu():
    kb = [
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔍 Скаутинг ($5,000)")],
        [KeyboardButton(text="⏳ Следующая неделя"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🏆 Лидеры и Рейтинг"), KeyboardButton(text="👥 Всего агентов")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_shop_menu():
    kb = [
        [KeyboardButton(text="📚 Обучение (Шанс 29%) - $50,000")],
        [KeyboardButton(text="🏎 Спорткар - $250,000"), KeyboardButton(text="🏢 Элитный офис - $500,000")],
        [KeyboardButton(text="💼 Купить бизнес - $1,000,000")],
        [KeyboardButton(text="🏰 Особняк - $3,500,000"), KeyboardButton(text="✈️ Самолет - $5,500,000")],
        [KeyboardButton(text="🔙 Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

async def check_endings(message: Message, user_id: int):
    # Защита от несуществующего пользователя
    if user_id not in users_db:
        return False
        
    user = users_db[user_id]
    
    if user['rep'] > 100:
        user['rep'] = 100
    
    if user['money'] < -50000:
        await message.answer(
            "❌ **БАНКРОТСТВО!**\nДолги превысили -$50,000. Всё имущество распродано с молотка.\n\nНажми /start, чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    elif user['rep'] <= 0:
        await message.answer(
            "📉 **ИЗГНАНИЕ!**\nРепутация упала до нуля. Никто больше не ведет с тобой дела.\n\nНажми /start, чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    elif user['money'] >= 200000000 and user['rating'] >= 5:
        await message.answer(
            "🏆 **АБСОЛЮТНАЯ ЛЕГЕНДА!**\n"
            "Поздравляем! Ты заработал $200,000,000 и стал самым влиятельным агентом в истории футбола. Игра пройдена!\n\nНажми /start, чтобы перепройти.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    users_db[message.from_user.id] = {
        'name': message.from_user.first_name or "Агент",
        'money': 50000,
        'rep': 50,
        'players': [],
        'age': 23,
        'weeks': 0,
        'rating': 1,
        'businesses': []
    }
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "🎯 **Цель игры:** Заработать **$200,000,000** и достичь 5-го уровня рейтинга.\n"
        "Следи за репутацией (максимум 100) и не уходи в долги (лимит -$50,000).\n\n"
        "Выбирай действие:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await message.answer("Игра была перезапущена или ты еще не начал. Жми /start")
    
    u = users_db[user_id]
    u['rep'] = min(100, u['rep'])
    
    stats = "".join([f"{i}. {p['name']} | М: {p['matches']} | Г: {p['goals']} | О: {p['tackles']} | С: {p['saves']}\n" for i, p in enumerate(u['players'], 1)])
    if not stats:
        stats = "Нет клиентов."

    biz_list = ", ".join(u['businesses']) if u['businesses'] else "Нет бизнесов"

    text = (
        f"👔 **Агент:** {u['name']} | **Возраст:** {u['age']}\n"
        f"⭐ **Рейтинг:** {u['rating']}/5 (Лимит: {RATING_LIMITS[u['rating']]})\n"
        f"💰 **Капитал:** ${u['money']:,}\n"
        f"🌟 **Репутация:** {u['rep']}/100\n"
        f"💼 **Бизнесы ({len(u['businesses'])}):** {biz_list}\n\n"
        f"📋 **Игроки:**\n{stats}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔍 Скаутинг ($5,000)")
async def scouting(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    
    if len(u['players']) >= RATING_LIMITS[u['rating']]:
        return await message.answer("⚠️ Лимит игроков исчерпан! Повышай рейтинг в Магазине.")

    u['money'] -= 5000
    if await check_endings(message, user_id): return
    
    if random.random() < 0.6:
        new_name = f"{random.choice(F_NAMES)} {random.choice(L_NAMES)}"
        u['players'].append({'name': new_name, 'matches': 0, 'goals': 0, 'tackles': 0, 'saves': 0})
        await message.answer(f"✅ Успех! Подписан новый клиент: **{new_name}**.", parse_mode="Markdown")
    else:
        await message.answer("❌ Скауты вернулись ни с чем.")

@dp.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    if message.from_user.id not in users_db:
        return await message.answer("Сначала жми /start")
    await message.answer("🛒 VIP-Магазин. Куда инвестируем миллионы?", reply_markup=get_shop_menu())

@dp.message(F.text == "🔙 Назад в меню")
async def back_menu(message: Message):
    if message.from_user.id not in users_db:
        return await message.answer("Сначала жми /start")
    await message.answer("Возвращаемся к делам.", reply_markup=get_main_menu())

@dp.message(F.text == "👥 Всего агентов")
async def show_total_agents(message: Message):
    if message.from_user.id not in users_db:
        return await message.answer("Сначала жми /start")
    
    total = len(users_db)
    await message.answer(f"📊 В данный момент на сервере активно строят карьеру агентов: **{total}**\n\n*Твоя конкуренция не дремлет!*", parse_mode="Markdown")

# --- ПОКУПКИ В МАГАЗИНЕ ---
@dp.message(F.text.startswith("📚 Обучение"))
async def buy_education(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    
    if u['rating'] >= 5: return await message.answer("Ты уже на максимальном уровне!")
    if u['money'] < 50000: return await message.answer("❌ Недостаточно средств ($50,000).")
    
    u['money'] -= 50000
    if random.random() < 0.29: # Шанс 29%
        u['rating'] += 1
        await message.answer(f"🎓 Экзамен сдан! Твой рейтинг теперь **{u['rating']}**.", parse_mode="Markdown")
    else:
        await message.answer("❌ Ты завалил экзамены. Деньги улетели на ветер, рейтинг не повышен.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏎 Спорткар"))
async def buy_car(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db: return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    if u['money'] < 250000: return await message.answer("❌ Нужно $250,000.")
    u['money'] -= 250000
    u['rep'] += 10
    await message.answer("🏎 Куплен спорткар! Репутация +10.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏢 Элитный офис"))
async def buy_office(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db: return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    if u['money'] < 500000: return await message.answer("❌ Нужно $500,000.")
    u['money'] -= 500000
    u['rep'] += 15
    await message.answer("🏢 Куплен шикарный офис в центре! Репутация +15.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("💼 Купить бизнес"))
async def buy_business(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db: return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    if u['money'] < 1000000: return await message.answer("❌ Нужно $1,000,000.")
    u['money'] -= 1000000
    
    new_biz = random.choice(BIZ_TYPES)
    u['businesses'].append(new_biz)
    
    await message.answer(f"💼 Успешная сделка! Приобретен актив: **{new_biz}**. Теперь он приносит пассивный доход!", parse_mode="Markdown")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏰 Особняк"))
async def buy_mansion(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db: return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    if u['money'] < 3500000: return await message.answer("❌ Нужно $3,500,000.")
    u['money'] -= 3500000
    u['rep'] += 25
    await message.answer("🏰 Огромный особняк куплен! Все газеты пишут о тебе. Репутация +25.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("✈️ Самолет"))
async def buy_jet(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db: return await message.answer("Сначала жми /start")
    
    u = users_db[user_id]
    if u['money'] < 5500000: return await message.answer("❌ Нужно $5,500,000.")
    u['money'] -= 5500000
    u['rep'] += 40
    await message.answer("✈️ Частный самолет твой! Топовые игроки сами хотят к тебе в агентство. Репутация +40.")
    await check_endings(message, user_id)

@dp.message(F.text == "🏆 Лидеры и Рейтинг")
async def show_leaders(message: Message):
    if message.from_user.id not in users_db:
        return await message.answer("Сначала жми /start")
        
    sorted_users = sorted(users_db.values(), key=lambda x: x['money'], reverse=True)
    leaderboard = "🏆 **Форбс Футбольных Агентов:**\n\n"
    for i, u in enumerate(sorted_users[:10], 1):
        leaderboard += f"{i}. {u['name']} | Капитал: ${u['money']:,}\n"
    await message.answer(leaderboard, parse_mode="Markdown")

@dp.message(F.text == "⏳ Следующая неделя")
async def next_week(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await message.answer("Сначала жми /start")
        
    u = users_db[user_id]
    
    u['weeks'] += 1
    if u['weeks'] >= 10:
        u['age'] += 1
        u['weeks'] = 0
        await message.answer(f"🎂 Прошел год! Твой возраст: {u['age']}.")

    # Доход от бизнеса
    if len(u['businesses']) > 0:
        biz_income = len(u['businesses']) * random.randint(20000, 60000)
        u['money'] += biz_income
        await message.answer(f"📈 Твои бизнесы принесли прибыль: +${biz_income:,}")

    # Прокачка характеристик игроков
    for p in u['players']:
        if random.random() > 0.3:
            p['matches'] += 1
            p['goals'] += random.randint(0, 2)
            p['tackles'] += random.randint(0, 4)
            p['saves'] += random.randint(0, 1)
    
    if len(u['players']) == 0:
        await message.answer("Нет клиентов. Расходы на жизнь и офис: -$5,000.")
        u['money'] -= 5000
    else:
        event_roll = random.random()
        
        if event_roll < 0.03: # 3% Мега-трансфер
            mega_profit = random.randint(500_000, 3_000_000) * u['rating']
            u['money'] += mega_profit
            u['rep'] += 5
            await message.answer(f"🔥 **МЕГА-ТРАНСФЕР!** Твой клиент перешел в топ-клуб! Агентские: +${mega_profit:,}", parse_mode="Markdown")
            
        elif event_roll < 0.48: # 45% Обычный доход
            profit = len(u['players']) * random.randint(5000, 25000) * u['rating']
            u['money'] += profit
            u['rep'] += 1
            await message.answer(f"⚽️ Игроки получили зарплату. Твой процент: +${profit:,}")
            
        elif event_roll < 0.70: # 22% Скандал
            fine = random.randint(20000, 75000)
            u['money'] -= fine
            u['rep'] -= 5
            await message.answer(f"🚨 **Скандал!** Штрафы и адвокаты обошлись в -${fine:,}. Репутация -5", parse_mode="Markdown")
            
        else: # 30% Ничего
            await message.answer("📅 Тихая неделя. Никаких новостей, но счета за офис платить надо (-$2,000).")
            u['money'] -= 2000

    await check_endings(message, user_id)

async def main():
    print("Бот запущен. Игра настроена на хардкор!")
    # Безопасный запуск: игнорируем все старые нажатия, пока бот был оффлайн
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
