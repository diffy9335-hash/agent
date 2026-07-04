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
    5: 30
}

def get_difficulty_menu():
    kb = [
        [KeyboardButton(text="🟢 Легкая"), KeyboardButton(text="🟡 Нормальная")],
        [KeyboardButton(text="🔴 Хардкор")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_menu():
    kb = [
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔍 Скаутинг ($5,000)")],
        [KeyboardButton(text="⏳ Следующая неделя"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🏆 Лидеры и Рейтинг"), KeyboardButton(text="👥 Всего агентов")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_shop_menu(diff):
    edu_chance = 30 if diff == "Easy" else 15 if diff == "Normal" else 5
    kb = [
        [KeyboardButton(text=f"📚 Обучение (Шанс {edu_chance}%) - $50,000")],
        [KeyboardButton(text="🏎 Спорткар - $250,000"), KeyboardButton(text="🏢 Элитный офис - $500,000")],
        [KeyboardButton(text="🏰 Особняк - $3,500,000"), KeyboardButton(text="✈️ Самолет - $5,500,000")],
        [KeyboardButton(text="🔙 Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Хелпер для проверки, играет ли человек (выбрал ли сложность)
def is_playing(user_id):
    return user_id in users_db and users_db[user_id].get('state') == 'playing'

async def check_endings(message: Message, user_id: int):
    if not is_playing(user_id):
        return False
        
    user = users_db[user_id]
    diff = user['difficulty']
    
    # Динамический лимит банкротства
    bank_limit = -50000 if diff == "Easy" else -25000 if diff == "Normal" else -10000
    
    if user['rep'] > 100:
        user['rep'] = 100
    
    if user['money'] < bank_limit:
        await message.answer(
            f"❌ **БАНКРОТСТВО!**\nДолги превысили лимит (${bank_limit:,}). Всё имущество распродано с молотка, а ты с позором изгнан из индустрии.\n\nНажми /start, чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    elif user['rep'] <= 0:
        await message.answer(
            "📉 **ИЗГНАНИЕ!**\nРепутация упала до нуля. Никто из игроков и клубов больше не хочет вести с тобой дела.\n\nНажми /start, чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    elif user['money'] >= 1000000000 and user['rating'] >= 5:
        await message.answer(
            "🏆 **АБСОЛЮТНАЯ ЛЕГЕНДА!**\n"
            "Поздравляем! Ты заработал невероятный **$1,000,000,000** и стал самым богатым агентом в истории футбола. Игра пройдена!\n\nНажми /start, чтобы перепройти на другой сложности.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
        
    return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Устанавливаем статус "выбор сложности"
    users_db[message.from_user.id] = {'state': 'choosing_difficulty'}
    
    await message.answer(
        "👋 Добро пожаловать в хардкорный симулятор агента!\n\n"
        "🎯 **Твоя главная цель:** Заработать **$1,000,000,000** и достичь 5-го уровня рейтинга.\n"
        "Следи за репутацией (максимум 100) и избегай долгов. Чем выше сложность, тем меньше у тебя прав на ошибку.\n\n"
        "⚙️ **Выбери уровень сложности для старта:**",
        reply_markup=get_difficulty_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text.in_(["🟢 Легкая", "🟡 Нормальная", "🔴 Хардкор"]))
async def set_difficulty(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db or users_db[user_id].get('state') != 'choosing_difficulty':
        return

    diff_text = message.text
    if "Легкая" in diff_text:
        diff_code = "Easy"
        start_money = 25000
    elif "Нормальная" in diff_text:
        diff_code = "Normal"
        start_money = 10000
    else:
        diff_code = "Hard"
        start_money = 5000

    users_db[user_id] = {
        'state': 'playing',
        'difficulty': diff_code,
        'name': message.from_user.first_name or "Агент",
        'money': start_money,
        'rep': 50 if diff_code != "Hard" else 30,
        'players': [], # Оставляем список пустышек для расчета количества
        'age': 23,
        'weeks': 0,
        'rating': 1
    }
    
    await message.answer(
        f"✅ Выбрана сложность: **{diff_text}**.\nСтартовый капитал: **${start_money:,}**.\n\nУдачи, она тебе понадобится!", 
        reply_markup=get_main_menu(), 
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
    
    u = users_db[user_id]
    u['rep'] = min(100, u['rep'])

    text = (
        f"👔 **Агент:** {u['name']} | **Возраст:** {u['age']}\n"
        f"🔥 **Сложность:** {u['difficulty']}\n"
        f"⭐ **Рейтинг:** {u['rating']}/5 (Лимит клиентов: {RATING_LIMITS[u['rating']]})\n"
        f"💰 **Капитал:** ${u['money']:,}\n"
        f"🌟 **Репутация:** {u['rep']}/100\n\n"
        f"📋 **Твои клиенты:** {len(u['players'])} чел."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔍 Скаутинг ($5,000)")
async def scouting(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
    
    u = users_db[user_id]
    
    if len(u['players']) >= RATING_LIMITS[u['rating']]:
        return await message.answer("⚠️ Лимит игроков исчерпан! Повышай рейтинг в Магазине.")

    u['money'] -= 5000
    if await check_endings(message, user_id): return
    
    # Динамический шанс скаутинга в зависимости от сложности
    diff = u['difficulty']
    chance = 0.50 if diff == "Easy" else 0.30 if diff == "Normal" else 0.15
    
    if random.random() < chance:
        u['players'].append(1) 
        await message.answer("✅ Успех! Ты отыскал талантливого клиента и подписал с ним контракт.", parse_mode="Markdown")
    else:
        await message.answer("❌ Провал. Скауты вернулись ни с чем, а деньги потрачены зря.")

@dp.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    if not is_playing(message.from_user.id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
    
    u = users_db[message.from_user.id]
    await message.answer("🛒 VIP-Магазин. Здесь ты можешь повысить свой престиж и рейтинг.", reply_markup=get_shop_menu(u['difficulty']))

@dp.message(F.text == "🔙 Назад в меню")
async def back_menu(message: Message):
    if not is_playing(message.from_user.id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
    await message.answer("Возвращаемся к суровым будням.", reply_markup=get_main_menu())

@dp.message(F.text == "👥 Всего агентов")
async def show_total_agents(message: Message):
    if not is_playing(message.from_user.id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
    
    total = sum(1 for user in users_db.values() if user.get('state') == 'playing')
    await message.answer(f"📊 В данный момент на сервере активно строят карьеру агентов: **{total}**\n\n*Конкуренты дышат в спину!*", parse_mode="Markdown")

# --- ПОКУПКИ В МАГАЗИНЕ ---
@dp.message(F.text.startswith("📚 Обучение"))
async def buy_education(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    if u['rating'] >= 5: return await message.answer("Ты уже на максимальном уровне!")
    if u['money'] < 50000: return await message.answer("❌ Недостаточно средств ($50,000).")
    
    u['money'] -= 50000
    
    diff = u['difficulty']
    chance = 0.30 if diff == "Easy" else 0.15 if diff == "Normal" else 0.05
    
    if random.random() < chance:
        u['rating'] += 1
        await message.answer(f"🎓 Потрясающе! Экзамен сдан! Твой рейтинг теперь **{u['rating']}**.", parse_mode="Markdown")
    else:
        await message.answer("❌ Ты завалил экзамены. Наблюдатели сочли тебя некомпетентным. Деньги улетели на ветер.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏎 Спорткар"))
async def buy_car(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    if u['money'] < 250000: return await message.answer("❌ Нужно $250,000.")
    u['money'] -= 250000
    u['rep'] += 10
    await message.answer("🏎 Куплен спорткар! Игроки видят твой статус. Репутация +10.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏢 Элитный офис"))
async def buy_office(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    if u['money'] < 500000: return await message.answer("❌ Нужно $500,000.")
    u['money'] -= 500000
    u['rep'] += 15
    await message.answer("🏢 Куплен шикарный офис в центре! Репутация +15.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("🏰 Особняк"))
async def buy_mansion(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    if u['money'] < 3500000: return await message.answer("❌ Нужно $3,500,000.")
    u['money'] -= 3500000
    u['rep'] += 25
    await message.answer("🏰 Огромный особняк куплен! Все профильные газеты пишут о тебе. Репутация +25.")
    await check_endings(message, user_id)

@dp.message(F.text.startswith("✈️ Самолет"))
async def buy_jet(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    if u['money'] < 5500000: return await message.answer("❌ Нужно $5,500,000.")
    u['money'] -= 5500000
    u['rep'] += 40
    await message.answer("✈️ Частный самолет твой! Топовые игроки сами хотят к тебе в агентство. Репутация +40.")
    await check_endings(message, user_id)

@dp.message(F.text == "🏆 Лидеры и Рейтинг")
async def show_leaders(message: Message):
    if not is_playing(message.from_user.id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
        
    sorted_users = sorted([user for user in users_db.values() if user.get('state') == 'playing'], key=lambda x: x['money'], reverse=True)
    leaderboard = "🏆 **Форбс Футбольных Агентов:**\n\n"
    for i, u in enumerate(sorted_users[:10], 1):
        leaderboard += f"{i}. {u['name']} ({u['difficulty']}) | Капитал: ${u['money']:,}\n"
    
    if not sorted_users:
        leaderboard += "Пока никого нет."
        
    await message.answer(leaderboard, parse_mode="Markdown")

@dp.message(F.text == "⏳ Следующая неделя")
async def next_week(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
        
    u = users_db[user_id]
    diff = u['difficulty']
    
    u['weeks'] += 1
    if u['weeks'] >= 10:
        u['age'] += 1
        u['weeks'] = 0
        await message.answer(f"🎂 Прошел год! Твой возраст: {u['age']}.")

    # Расходы на выживание зависят от сложности
    expense = 2000 if diff == "Easy" else 5000 if diff == "Normal" else 10000
    players_count = len(u['players'])

    if players_count == 0:
        await message.answer(f"📉 Нет клиентов. Расходы на проживание и офис списываются в минус: -${expense:,}.")
        u['money'] -= expense
    else:
        # Жесткая настройка шансов под уровни сложности
        mega_chance = 0.03 if diff == "Easy" else 0.01 if diff == "Normal" else 0.001
        norm_chance = 0.40 if diff == "Easy" else 0.30 if diff == "Normal" else 0.15
        scand_chance = 0.20 if diff == "Easy" else 0.35 if diff == "Normal" else 0.50
        
        event_roll = random.random()
        
        if event_roll < mega_chance: # Мега-трансфер
            max_payout = 20_000_000 if diff == "Easy" else 10_000_000 if diff == "Normal" else 5_000_000
            mega_profit = random.randint(2_000_000, max_payout) * u['rating']
            u['money'] += mega_profit
            u['rep'] += 5
            await message.answer(f"🔥 **МЕГА-ТРАНСФЕР!** Твой клиент перешел в топ-клуб! Сумасшедшие комиссионные: +${mega_profit:,}", parse_mode="Markdown")
            
        elif event_roll < mega_chance + norm_chance: # Обычный доход
            prof_multi = 1.0 if diff == "Easy" else 0.7 if diff == "Normal" else 0.4
            profit = int(players_count * random.randint(10000, 40000) * u['rating'] * prof_multi)
            u['money'] += profit
            u['rep'] += 1
            await message.answer(f"⚽️ Клиенты получили зарплату. Твои проценты составили: +${profit:,}")
            
        elif event_roll < mega_chance + norm_chance + scand_chance: # Скандал
            fine_multi = 1.0 if diff == "Easy" else 2.0 if diff == "Normal" else 4.0
            fine = int(random.randint(20000, 75000) * fine_multi)
            u['money'] -= fine
            u['rep'] -= 5 if diff == "Easy" else 10 if diff == "Normal" else 20
            await message.answer(f"🚨 **Скандал!** Клиент вляпался в неприятности. Штрафы и адвокаты обошлись в -${fine:,}. Репутация серьезно пострадала!", parse_mode="Markdown")
            
        else: # Ничего (Тихая неделя)
            await message.answer(f"📅 Тихая неделя. Новостей нет, а вот налоги и счета за офис оплатить нужно (-${expense:,}).")
            u['money'] -= expense

    await check_endings(message, user_id)

async def main():
    print("Бот запущен. Версия: Хардкорное Агентство (Без бизнесов)!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
