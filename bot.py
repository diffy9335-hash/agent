import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import game
from game import fmt

dp = Dispatcher()


def kb(rows, back=True):
    b = InlineKeyboardBuilder()
    for text, data in rows:
        b.button(text=text, callback_data=data)
    if back:
        b.button(text="⬅️ В меню", callback_data="menu")
    b.adjust(1 if len(rows) > 4 else 2)
    return b.as_markup()


async def render(target, text, markup):
    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=markup)
        else:
            await target.answer(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


def pline(p):
    mood = p.get("mood", 70)
    face = "😊" if mood >= 60 else "😐" if mood >= 35 else "😡"
    inj = f" · 🤕{p['inj']}н" if p.get("inj") else ""
    return (f"{p['name']} · {p['pos']} · {p['age']}л · OVR {p['ovr']}/{p['pot']} · "
            f"{p['club']} · {fmt(p['value'])} · {face}{mood}{inj} · 📝{p.get('ctr', 80)}н")


def menu_text(st):
    return (f"🕴 Агент {st['name']}\n"
            f"📅 Неделя {st['week']} (сезон {(st['week'] - 1) // 52 + 1})\n"
            f"{game.window_text(st)}\n"
            f"💰 {fmt(st['money'])} / цель {fmt(game.GOAL)}\n"
            f"⭐ Репутация: {st['rep']} ({game.rank(st['rep'])}) · комиссия {commission_pct(st)}%\n"
            f"🏢 Офис ур.{st['office']} · клиенты {len(st['clients'])}/{game.capacity(st)}\n"
            f"🤝 Сделок: {st.get('deals', 0)} · место среди агентов: {game.standing(st)}/4\n"
            f"📨 Офферов: {len(st['offers'])}")


def commission_pct(st):
    return round(game.commission_rate(st) * 100, 1)


MENU = [("🔍 Скаутинг", "scout"), ("👥 Клиенты", "clients"), ("📨 Офферы", "offers"),
        ("🏢 Офис", "office"), ("🏆 Рейтинг", "top"), ("🎯 Задания", "quests"), ("⏭ Следующая неделя", "next")]


def menu_kb(st):
    b = InlineKeyboardBuilder()
    dil = bool(st.get("dilemma"))
    if dil:
        b.button(text="❗ Принять решение", callback_data="dil")
    for t, d in MENU:
        b.button(text=t, callback_data=d)
    b.adjust(*([1] if dil else []), 2, 2, 2, 2)
    return b.as_markup()


@dp.message(Command("start"))
async def start(m: Message):
    game.touch_player(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
    st = game.load(m.from_user.id)
    if not st or st["over"]:
        st = game.new_game(m.from_user.first_name or "Агент")
        game.save(m.from_user.id, st)
        await m.answer("⚽ Добро пожаловать в карьеру футбольного агента!\n"
                       f"Заработайте {fmt(game.GOAL)}, не уйдя в минус. Удачи!")
    await m.answer(menu_text(st), reply_markup=menu_kb(st))


@dp.message(Command("stats"))
async def stats(m: Message):
    if str(m.from_user.id) != os.environ.get("ADMIN_ID", ""):
        return
    (cnt, games, wins), act, best = game.admin_stats()
    txt = f"📊 Игроков: {cnt} (активны за 7 дней: {act})\nИгр сыграно: {games}, побед: {wins}\n\nТоп по деньгам:\n"
    txt += "\n".join(f"{i + 1}. {n} @{u} — {fmt(mn)}" for i, (n, u, mn) in enumerate(best))
    await m.answer(txt)


@dp.message(Command("newgame"))
async def newgame(m: Message):
    game.save(m.from_user.id, game.new_game(m.from_user.first_name or "Агент"))
    await start(m)


@dp.callback_query()
async def cb(c: CallbackQuery):
    uid = c.from_user.id
    st = game.load(uid)
    if not st:
        await c.answer("Нажмите /start")
        return
    if st["over"] and c.data != "restart":
        await c.answer()
        await end_screen(c, st)
        return
    a = c.data.split(":")
    cmd = a[0]
    note = ""

    if cmd == "menu":
        await render(c, menu_text(st), menu_kb(st))

    elif cmd == "scout":
        if a[-1] == "go":
            if st["money"] < game.scout_cost(st):
                note = "❌ Не хватает денег на скаутинг."
            else:
                game.scout(st)
        if st["cands"]:
            txt = "🔍 Найденные кандидаты:\n\n"
            rows = []
            for i, p in enumerate(st["cands"]):
                txt += f"{i + 1}. {pline(p)}\n   Бонус: {fmt(p['ask'])} · нужна реп. {p['rep_req']}\n"
                rows.append((f"✍️ Подписать {i + 1}", f"sign:{i}"))
            await render(c, note + "\n" + txt, kb(rows))
        else:
            await render(c, f"{note}\n🔍 Скаутинг стоит {fmt(game.scout_cost(st))}. Искать новых игроков?",
                         kb([("Искать", "scout:go")]))

    elif cmd == "sign":
        note = game.sign(st, int(a[1]))
        txt = note + "\n\n" + menu_text(st)
        await render(c, txt, menu_kb(st))

    elif cmd == "clients":
        if len(a) > 1 and a[1] == "drop":
            st["clients"] = [p for p in st["clients"] if p["id"] != int(a[2])]
            st["offers"] = [o for o in st["offers"] if o["pid"] != int(a[2])]
        if len(a) > 1 and a[1] == "train":
            note = game.train(st, int(a[2]))
        elif len(a) > 1 and a[1] == "renew":
            note = game.renew(st, int(a[2]))
        txt = (note + "\n\n" if note else "") + "👥 Ваши клиенты:\n\n" + (
            "\n".join(pline(p) for p in st["clients"]) or "Пока никого.")
        txt += "\n\n🏋️ тренировка · 📝 продлить контракт (📝Nн = недель осталось) · ❌ расстаться"
        rows = []
        for p in st["clients"]:
            rows += [(f"🏋️ {p['name']}", f"clients:train:{p['id']}"), (f"📝 {p['name']}", f"clients:renew:{p['id']}"),
                     (f"❌ {p['name']}", f"clients:drop:{p['id']}")]
        await render(c, txt, kb(rows))

    elif cmd == "offers":
        if len(a) > 1:
            i = int(a[2])
            if i < len(st["offers"]):
                if a[1] == "acc":
                    note = game.sell(st, i)
                elif a[1] == "neg":
                    note = game.negotiate(st, i)
                elif a[1] == "rej":
                    note = game.reject(st, i)
        txt = (note + "\n\n" if note else "") + "📨 Офферы от клубов:\n\n"
        rows = []
        for i, o in enumerate(st["offers"]):
            p = next(x for x in st["clients"] if x["id"] == o["pid"])
            com = int(o["fee"] * game.commission_rate(st))
            txt += f"{i + 1}. {p['name']} → {o['club']}\n   Сумма {fmt(o['fee'])} · ваша комиссия {fmt(com)}\n"
            rows += [(f"✅ {i + 1}", f"offers:acc:{i}"), (f"💬 {i + 1}", f"offers:neg:{i}"),
                     (f"🚫 {i + 1}", f"offers:rej:{i}")]
        if not st["offers"]:
            txt += f"Пока предложений нет. {game.window_text(st)}."
        b = InlineKeyboardBuilder()
        for t, d in rows:
            b.button(text=t, callback_data=d)
        b.button(text="⬅️ В меню", callback_data="menu")
        b.adjust(3)
        await render(c, txt + "\n✅ принять · 💬 торговаться · 🚫 отклонить", b.as_markup())

    elif cmd == "office":
        if len(a) > 1 and a[1] == "up":
            cost = game.upgrade_cost(st)
            if st["money"] >= cost and st["office"] < 5:
                st["money"] -= cost
                st["office"] += 1
                note = "✅ Офис улучшен!\n\n"
            else:
                note = "❌ Не хватает денег или максимальный уровень.\n\n"
        txt = (f"{note}🏢 Офис ур.{st['office']}/5\nМест: {game.capacity(st)}\n"
               f"Аренда: {fmt(3 + 3 * st['office'])}/нед\nСкаутинг: {fmt(game.scout_cost(st))}\n")
        rows = [(f"⬆️ Улучшить за {fmt(game.upgrade_cost(st))}", "office:up")] if st["office"] < 5 else []
        await render(c, txt, kb(rows))

    elif cmd == "next":
        if st.get("dilemma"):
            await c.answer("Сначала примите решение ❗", show_alert=True)
            return
        log = game.next_week(st)
        if st["over"]:
            game.record_game(uid, st)
            game.save(uid, st)
            await end_screen(c, st)
            await c.answer()
            return
        await render(c, "⏭ Неделя прошла:\n\n" + "\n".join(log) + "\n\n" + menu_text(st),
                     menu_kb(st))

    elif cmd == "dil":
        v = game.dilemma_view(st) if st.get("dilemma") else None
        if len(a) > 1:
            note = game.decide(st, int(a[1]))
            await render(c, note + "\n\n" + menu_text(st), menu_kb(st))
        elif v:
            rows = [(lab, f"dil:{i}") for i, lab in enumerate(v[1])]
            await render(c, "❗ Решение агента\n\n" + v[0], kb(rows, back=False))
        else:
            await render(c, menu_text(st), menu_kb(st))

    elif cmd == "top":
        rows = game.top()
        txt = "🏆 Рейтинг агентов:\n\n" + "\n".join(
            f"{i + 1}. {n} — {fmt(m)} · реп. {r} · нед. {w}" for i, (n, m, r, w) in enumerate(rows))
        await render(c, txt, kb([]))

    elif cmd == "quests":
        txt = "🎯 Задания:\n\n"
        for q in st["quests"]:
            pr = min(q["t"], st["stats"][q["kind"]] - q["base"])
            txt += f"• {q['text']} — {pr}/{q['t']} (награда {fmt(q['money'])}, реп. +{q['rep']})\n"
        txt += "\n🏅 Достижения:\n"
        for aid, name, _c, rew in game.ACH:
            txt += f"{'✅' if aid in st['ach'] else '🔒'} {name} (+{fmt(rew)})\n"
        txt += "\n🦈 Конкуренты:\n" + "\n".join(f"• {r['name']} — {fmt(r['money'])}" for r in st["rivals"])
        await render(c, txt, kb([]))

    elif cmd == "restart":
        st = game.new_game(c.from_user.first_name or "Агент")
        await render(c, menu_text(st), menu_kb(st))

    msgs = game.check(st)
    if st["over"]:
        game.record_game(uid, st)
    game.save(uid, st)
    if st["over"]:
        await end_screen(c, st)
    if msgs:
        await c.message.answer("\n\n".join(msgs))
    await c.answer()


async def end_screen(c: CallbackQuery, st):
    if st["over"] == "win":
        txt = f"🏆 Вы заработали {fmt(game.GOAL)} за {st['week']} нед. — легенда агентского бизнеса!"
    elif st["over"] == "rival":
        txt = "🦈 Конкурент первым достиг цели. Гонку агентов вы проиграли!"
    else:
        txt = "💀 Агентство обанкротилось. Попробуйте ещё раз!"
    await render(c, txt, kb([("🔄 Новая игра", "restart")], back=False))


def load_env(path=".env"):
    """Минимальный загрузчик .env (без внешних библиотек)."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def main():
    logging.basicConfig(level=logging.INFO)
    load_env()
    token = os.environ.get("BOT_TOKEN", "").strip().strip("'\"")
    if ":" not in token:
        raise SystemExit("BOT_TOKEN не задан или неверный. Формат: 123456789:AAH... (без кавычек и пробелов)")
    bot = Bot(token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
