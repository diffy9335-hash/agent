import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Токен: сначала пробуем взять из переменной окружения, иначе — хардкод
TOKEN = os.getenv("BOT_TOKEN", "8800738908:AAFl5Bcz74JwAR4xzWDDvesOnXuXURnxyVA")

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

# --- ВОЗРАСТНАЯ СИСТЕМА ---
MAX_AGE = 70              # Абсолютный предел (пенсия)
RETIREMENT_OFFER_AGE = 60 # В этом возрасте бот предлагает уйти на пенсию

def get_age_multiplier(age):
    """Множитель дохода в зависимости от возраста."""
    if age < 25:   return 0.7   # молодой, мало связей
    if age < 40:   return 1.0   # пик карьеры
    if age < 50:   return 0.85  # опыт есть, энергии меньше
    if age < 60:   return 0.6   # сдаёт
    if age < 70:   return 0.4   # почти всё
    return 0.2

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

def get_retirement_menu():
    kb = [
        [KeyboardButton(text="🚪 Уйти на пенсию"), KeyboardButton(text="💪 Продолжить карьеру")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_shop_menu(diff):
    edu_chance = 40 if diff == "Easy" else 25 if diff == "Normal" else 15
    kb = [
        [KeyboardButton(text=f"📚 Обучение (Шанс {edu_chance}%) - $50,000")],
        [KeyboardButton(text="🏎 Спорткар - $250,000"), KeyboardButton(text="🏢 Элитный офис - $500,000")],
        [KeyboardButton(text="🏰 Особняк - $3,500,000"), KeyboardButton(text="✈️ Самолет - $5,500,000")],
        [KeyboardButton(text="🔙 Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def is_playing(user_id):
    return user_id in users_db and users_db[user_id].get('state') == 'playing'

async def check_endings(message: Message, user_id: int):
    if not is_playing(user_id):
        return False
        
    user = users_db[user_id]
    diff = user['difficulty']
    
    bank_limit = -50000 if diff == "Easy" else -35000 if diff == "Normal" else -20000
    
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
        user['money'] = 1000000000
        user['state'] = 'won'
        
        await message.answer(
            "🏆 **АБСОЛЮТНАЯ ЛЕГЕНДА!**\n"
            "Поздравляем! Ты заработал невероятный **$1,000,000,000** и стал самым богатым агентом в истории футбола.\n\n"
            "Твой агент навсегда сохранен в Зале Славы (Топ Лидеров) с 1 миллиардом на счету!\n\nНажми /start, если хочешь начать карьеру заново.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        return True
        
    return False

async def check_age_ending(message: Message, user_id: int):
    """Проверка пенсионного возраста. Возвращает True, если игра завершена."""
    if not is_playing(user_id):
        return False
    
    u = users_db[user_id]
    
    if u['age'] >= MAX_AGE:
        await message.answer(
            f"🎂 **ТЕБЕ {u['age']} ЛЕТ. ПОРА НА ПЕНСИЮ.**\n\n"
            "Здоровье уже не то, молодые агенты отбирают клиентов, "
            "а твоё имя стало легендой. Ты уходишь красиво.\n\n"
            f"💰 **Финальный капитал:** ${u['money']:,}\n"
            f"⭐ **Рейтинг:** {u['rating']}/5\n"
            f"📋 **Клиентов на момент ухода:** {len(u['players'])}\n"
            f"📅 **Прожито лет в профессии:** {u['age'] - 23}\n\n"
            "Нажми /start, чтобы начать новую карьеру.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
        )
        del users_db[user_id]
        return True
    
    return False

async def trigger_retirement_offer(message: Message, user_id: int):
    """В 60 лет предлагаем выбор: пенсия или продолжение со штрафом."""
    u = users_db[user_id]
    if u.get('retirement_offer_shown'):
        return
    
    u['retirement_offer_shown'] = True
    await message.answer(
        "🎂 **ТЕБЕ 60 ЛЕТ.**\n\n"
        "Ты уже ветеран индустрии. Можно уйти на заслуженный отдых, "
        "сохранив капитал и репутацию. А можно рискнуть и продолжить — "
        "но доход упадёт, а здоровье будет подводить.\n\n"
        "Что выбираешь?",
        reply_markup=get_retirement_menu(),
        parse_mode="Markdown"
    )

def get_age_event(age):
    """Возвращает случайное возрастное событие или None."""
    events = []
    if age >= 40:
        events.append(("🏥 **Проблемы со здоровьем.** Месяц на лечение. -$100,000", -100000, 0))
    if age >= 45:
        events.append(("👴 **Молодой агент переманил одного из твоих клиентов!**", 0, 'lose_player'))
    if age >= 50:
        events.append(("💔 **Развод.** Половина капитала ушла жене. -50% денег", 'half', 0))
    if age >= 55:
        events.append(("📉 **Пресса пишет: «Старый агент не тянет».** Репутация -10", 0, -10))
    
    if events and random.random() < 0.15:
        return random.choice(events)
    return None

@dp.message(Command("start"))
async def cmd_start(message: Message):
    users_db[message.from_user.id] = {'state': 'choosing_difficulty'}
    
    await message.answer(
        "👋 Добро пожаловать в симулятор агента!\n\n"
        "🎯 **Твоя главная цель:** Заработать **$1,000,000,000** и достичь 5-го уровня рейтинга.\n"
        "Следи за репутацией (максимум 100) и избегай долгов. Чем выше сложность, тем меньше у тебя прав на ошибку.\n\n"
        "⏳ **Помни:** твоя карьера конечна. В 70 лет — пенсия, хочешь ты того или нет.\n\n"
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
        'players': [], 
        'age': 23,
        'weeks': 0,
        'rating': 1,
        'retirement_offer_shown': False,
        'age_penalty': 1.0
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

    # Предупреждение о возрасте
    age_warn = ""
    if u['age'] >= 68:
        age_warn = " 🚨"
    elif u['age'] >= 60:
        age_warn = " ⚠️"
    
    # Множитель дохода
    age_mult = get_age_multiplier(u['age']) * u.get('age_penalty', 1.0)
    
    text = (
        f"👔 **Агент:** {u['name']} | **Возраст:** {u['age']} лет{age_warn}\n"
        f"🔥 **Сложность:** {u['difficulty']}\n"
        f"⭐ **Рейтинг:** {u['rating']}/5 (Лимит клиентов: {RATING_LIMITS[u['rating']]})\n"
        f"💰 **Капитал:** ${u['money']:,}\n"
        f"🌟 **Репутация:** {u['rep']}/100\n"
        f"📊 **Работоспособность:** {int(age_mult * 100)}%\n\n"
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
    
    diff = u['difficulty']
    chance = 0.60 if diff == "Easy" else 0.40 if diff == "Normal" else 0.25
    
    if random.random() < chance:
        u['players'].append(1) 
        await message.answer("✅ Успех! Ты отыскал талантливого клиента и подписал с ним контракт.", parse_mode="Markdown")
    else:
        await message.answer("❌ Провал. Скауты вернулись ни с чем, а деньги потрачены зря.")
    
    await check_endings(message, user_id)

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
    
    total = sum(1 for user in users_db.values() if user.get('state') in ['playing', 'won'])
    await message.answer(f"📊 В данный момент в нашей базе зарегистрировано агентов: **{total}**\n\n*Конкуренты дышат в спину!*", parse_mode="Markdown")

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
    chance = 0.40 if diff == "Easy" else 0.25 if diff == "Normal" else 0.15
    
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
    user_state = users_db.get(message.from_user.id, {}).get('state')
    if user_state not in ['playing', 'won']:
        return await message.answer("Сначала выбери сложность или нажми /start.")
        
    valid_users = [u for u in users_db.values() if u.get('state') in ['playing', 'won']]
    
    def generate_top(diff_code, title):
        users_diff = [u for u in valid_users if u.get('difficulty') == diff_code]
        sorted_users = sorted(users_diff, key=lambda x: x['money'], reverse=True)[:10]
        
        block = f"**{title}**\n"
        if not sorted_users:
            block += "Пока никого нет.\n"
        else:
            for i, u in enumerate(sorted_users, 1):
                status = "👑 ПРОЙДЕНО" if u.get('state') == 'won' else f"⭐ {u['rating']}/5"
                block += f"{i}. {u['name']} | ${u['money']:,} | {status}\n"
        return block + "\n"

    leaderboard = "🏆 **ФОРБС ФУТБОЛЬНЫХ АГЕНТОВ (Топ-10)** 🏆\n\n"
    leaderboard += generate_top("Easy", "🟢 Легкая сложность")
    leaderboard += generate_top("Normal", "🟡 Нормальная сложность")
    leaderboard += generate_top("Hard", "🔴 Хардкор")
        
    await message.answer(leaderboard, parse_mode="Markdown")

# --- ВЫБОР НА ПЕНСИИ ---
@dp.message(F.text == "🚪 Уйти на пенсию")
async def retire_choice(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    
    await message.answer(
        f"🎂 **ТЫ УХОДИШЬ НА ПЕНСИЮ В {u['age']} ЛЕТ.**\n\n"
        "Ты собрал чемоданы, попрощался с клиентами и оставил свой след в истории футбола.\n\n"
        f"💰 **Финальный капитал:** ${u['money']:,}\n"
        f"⭐ **Рейтинг:** {u['rating']}/5\n"
        f"📋 **Клиентов на момент ухода:** {len(u['players'])}\n"
        f"📅 **Лет в профессии:** {u['age'] - 23}\n\n"
        "Нажми /start, чтобы начать новую карьеру.",
        reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown"
    )
    del users_db[user_id]

@dp.message(F.text == "💪 Продолжить карьеру")
async def keep_going(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id): return
    
    u = users_db[user_id]
    u['age_penalty'] = 0.5  # доход режется вдвое
    u['rep'] -= 5           # пресса не одобряет
    u['retirement_offer_shown'] = True
    
    await message.answer(
        "💪 **Ты решил продолжить.**\n\n"
        "Пресса пишет: «Старик не уходит». Клиенты качают головами, но ты всё ещё в деле.\n\n"
        "⚠️ **Штрафы:** доход -50%, репутация -5.\n"
        "Работай, пока есть силы. В 70 лет — финал, хочешь ты того или нет.",
        reply_markup=get_main_menu(), parse_mode="Markdown"
    )

@dp.message(F.text == "⏳ Следующая неделя")
async def next_week(message: Message):
    user_id = message.from_user.id
    if not is_playing(user_id):
        return await message.answer("Сначала выбери сложность или нажми /start.")
        
    u = users_db[user_id]
    diff = u['difficulty']
    
    # --- СТАРЕНИЕ ---
    u['weeks'] += 1
    age_changed = False
    if u['weeks'] >= 10:
        u['age'] += 1
        u['weeks'] = 0
        age_changed = True
        await message.answer(f"🎂 Прошел год! Твой возраст: **{u['age']}** лет.")
        
        # Проверка пенсионного возраста (жёсткий финал)
        if await check_age_ending(message, user_id):
            return
        
        # Предложение пенсии в 60 лет
        if u['age'] >= RETIREMENT_OFFER_AGE and not u.get('retirement_offer_shown'):
            await trigger_retirement_offer(message, user_id)
            return
    
    # --- РАСХОДЫ ---
    expense = 2000 if diff == "Easy" else 4000 if diff == "Normal" else 7000
    players_count = len(u['players'])
    
    # Множитель возраста
    age_mult = get_age_multiplier(u['age']) * u.get('age_penalty', 1.0)
    
    if players_count == 0:
        await message.answer(f"📉 Нет клиентов. Расходы на проживание и офис списываются в минус: -${expense:,}.")
        u['money'] -= expense
    else:
        mega_chance = 0.03 if diff == "Easy" else 0.02 if diff == "Normal" else 0.01
        norm_chance = 0.50 if diff == "Easy" else 0.40 if diff == "Normal" else 0.30
        scand_chance = 0.15 if diff == "Easy" else 0.25 if diff == "Normal" else 0.35
        
        event_roll = random.random()
        
        if event_roll < mega_chance: # Мега-трансфер
            max_payout = 20_000_000 if diff == "Easy" else 15_000_000 if diff == "Normal" else 10_000_000
            mega_profit = int(random.randint(2_000_000, max_payout) * u['rating'] * age_mult)
            u['money'] += mega_profit
            u['rep'] += 5
            await message.answer(f"🔥 **МЕГА-ТРАНСФЕР!** Твой клиент перешел в топ-клуб! Сумасшедшие комиссионные: +${mega_profit:,}", parse_mode="Markdown")
            
        elif event_roll < mega_chance + norm_chance: # Обычный доход
            prof_multi = 1.0 if diff == "Easy" else 0.8 if diff == "Normal" else 0.6
            profit = int(players_count * random.randint(10000, 40000) * u['rating'] * prof_multi * age_mult)
            u['money'] += profit
            u['rep'] += 1
            await message.answer(f"⚽️ Клиенты получили зарплату. Твои проценты составили: +${profit:,}")
            
        elif event_roll < mega_chance + norm_chance + scand_chance: # Скандал
            fine_multi = 1.0 if diff == "Easy" else 1.5 if diff == "Normal" else 2.5
            fine = int(random.randint(20000, 75000) * fine_multi)
            u['money'] -= fine
            u['rep'] -= 5 if diff == "Easy" else 8 if diff == "Normal" else 15
            await message.answer(f"🚨 **Скандал!** Клиент вляпался в неприятности. Штрафы и адвокаты обошлись в -${fine:,}. Репутация серьезно пострадала!", parse_mode="Markdown")
            
        else: # Тихая неделя
            await message.answer(f"📅 Тихая неделя. Новостей нет, а вот налоги и счета за офис оплатить нужно (-${expense:,}).")
            u['money'] -= expense
    
    # --- ВОЗРАСТНЫЕ СОБЫТИЯ (только если год сменился) ---
    if age_changed and u['age'] >= 40:
        event = get_age_event(u['age'])
        if event:
            text, money_delta, other = event
            if money_delta == 'half':
                lost = u['money'] // 2
                u['money'] -= lost
                await message.answer(f"{text}\n💸 Потеряно: ${lost:,}", parse_mode="Markdown")
            else:
                u['money'] += money_delta
                if other == 'lose_player' and u['players']:
                    u['players'].pop()
                elif isinstance(other, int) and other != 0 and other != 'lose_player':
                    u['rep'] += other
                await message.answer(text, parse_mode="Markdown")
    
    await check_endings(message, user_id)

async def main():
    print("Бот запущен. Версия: Конечная карьера с пенсией в 70!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
