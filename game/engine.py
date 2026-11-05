"""Логика игры: без единого print/input."""
from __future__ import annotations

import random

from .models import Cult, Event, Follower

WIN_DAY = 30

STAT_LIMITS = {
    "faith": (0, 100),
    "stability": (0, 100),
    "food": (0, 999),
}

NAMES = [
    "Марта", "Игнат", "Агата", "Фома", "Руфина", "Тимур", "Зоя", "Прохор",
    "Клавдия", "Савва", "Лукерья", "Мефодий", "Наталья", "Евлампий",
]
TRAITS = [
    "набожный", "скептик", "болтливый", "мастеровой", "робкий",
    "горячая голова", "хозяйственный", "мечтатель", "ворчун",
]


def create_cult(rng: random.Random) -> Cult:
    cult = Cult()
    cult.followers = [
        Follower("Марта", ["набожная", "болтливая"], 60),
        Follower("Игнат", ["скептик", "мастеровой"], 40,
                 secret="Тайно ходит молиться другим богам"),
        Follower("Агата", ["робкая", "мечтательница"], 55),
        Follower("Фома", ["хозяйственный", "ворчун"], 50),
        Follower("Руфина", ["горячая голова"], 65),
    ]
    return cult


def new_follower(cult: Cult, rng: random.Random) -> Follower:
    taken = {f.name for f in cult.followers}
    free = [n for n in NAMES if n not in taken] or NAMES
    return Follower(rng.choice(free), [rng.choice(TRAITS)], loyalty=rng.randint(35, 60))


def apply_effects(cult: Cult, effects: dict[str, int], rng: random.Random) -> None:
    for key, delta in effects.items():
        if key == "followers":
            if delta > 0:
                for _ in range(delta):
                    cult.followers.append(new_follower(cult, rng))
            else:
                for _ in range(min(-delta, len(cult.followers))):
                    cult.followers.remove(rng.choice(cult.followers))
        else:
            lo, hi = STAT_LIMITS[key]
            setattr(cult, key, max(lo, min(hi, getattr(cult, key) + delta)))


def by_mood(cult: Cult, light: str, dark: str) -> str:
    """Тон текста следует за состоянием культа: пока всё ок — ирония, иначе — мрак."""
    return light if cult.stability >= 50 else dark


def weakest(cult: Cult) -> Follower:
    return min(cult.followers, key=lambda f: f.loyalty)


def named(cult: Cult, name: str) -> Follower | None:
    """Последователь по имени или None, если его (уже) нет в культе."""
    return next((f for f in cult.followers if f.name == name), None)


def shift_loyalty(follower: Follower, delta: int) -> None:
    follower.loyalty = max(0, min(100, follower.loyalty + delta))


def pick_event(cult: Cult, events: list[Event], rng: random.Random) -> Event | None:
    pool = [
        e for e in events
        if e.condition(cult)
        and not (e.once and e.id in cult.seen_events)
        and (e.subject is None or e.subject(cult) is not None)
    ]
    if len(pool) > 1:  # не повторяем одно и то же событие два дня подряд
        pool = [e for e in pool if e.id != cult.last_event] or pool
    if not pool:
        return None
    return rng.choices(pool, weights=[e.weight for e in pool])[0]


def daily_tick(cult: Cult, rng: random.Random) -> list[str]:
    """Ежедневные последствия. Возвращает сообщения для показа игроку."""
    msgs: list[str] = []

    eaten = max(1, len(cult.followers) // 2)
    cult.food = max(0, cult.food - eaten)
    msgs.append(f"Паства съела {eaten} ед. еды.")

    if cult.faith >= 60:
        cult.food += 1
        msgs.append("Верные принесли подношения (+1 еды).")

    if cult.food == 0:
        apply_effects(cult, {"stability": -8, "faith": -4}, rng)
        msgs.append("Миски пусты. Паства ропщет.")

    for f in cult.followers:
        if "herald" in f.flags and f.loyalty >= 40:
            apply_effects(cult, {"faith": 1}, rng)
            msgs.append(f"Глашатай {f.name} разносит слово культа (+1 веры).")

    for f in [f for f in cult.followers if f.loyalty <= 0]:
        cult.followers.remove(f)
        msgs.append(f"{f.name} собрал(а) вещи и ушёл(ла) из культа.")

    return msgs


def check_defeat(cult: Cult) -> str | None:
    if cult.stability <= 0:
        return "Терпение паствы лопнуло. Начался бунт, и алтарь оказался в реке."
    if cult.faith <= 0:
        return "Вера иссякла. Последователи разошлись по домам, пожав плечами."
    if not cult.followers:
        return "В храме никого не осталось. Эхо — единственный, кто ещё отвечает на молитвы."
    return None
