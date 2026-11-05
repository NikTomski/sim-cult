"""Весь ввод/вывод. Движок про консоль ничего не знает."""
from __future__ import annotations

import textwrap

from .engine import rename_cult, rename_follower
from .models import Choice, Cult
from .session import STAT_LABELS, defeat_summary, victory_text

WIDTH = 70

# Команды: латиница и та же клавиша на русской раскладке
QUIT = ("q", "й")
RENAME_CULT = ("r", "к")
RENAME_FOLLOWER = ("f", "а")

HINT = "[r] переименовать культ   [f] переименовать последователя   [q] выход"


def bar(value: int, width: int = 20) -> str:
    filled = round(max(0, min(100, value)) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def say(text: str) -> None:
    if text:
        print()
        print(textwrap.fill(text, WIDTH))


def setup(cult: Cult) -> None:
    """Основание культа: даём игроку назвать культ и, если хочет, паству."""
    print("═" * WIDTH)
    print(" ОСНОВАНИЕ КУЛЬТА")
    print("═" * WIDTH)
    print(f"\nКак назовёшь свой культ? (Enter — оставить «{cult.name}»)")
    while True:
        raw = input("> ")
        if not raw.strip():
            break
        err = rename_cult(cult, raw)
        if err:
            print(err)
            continue
        print(f"Готово: «{cult.name}».")
        break

    answer = input("\nХочешь переименовать кого-то из паствы? [y/N] ").strip().lower()
    if answer in ("y", "yes", "д", "да"):
        rename_followers_flow(cult)


def rename_cult_flow(cult: Cult) -> None:
    raw = input(f"Новое название культа (сейчас «{cult.name}», Enter — отмена): ")
    if not raw.strip():
        return
    err = rename_cult(cult, raw)
    print(err or f"Готово: «{cult.name}».")


def rename_followers_flow(cult: Cult) -> None:
    """Выбор последователя по номеру и ввод нового имени. Пустой ввод — выход."""
    while True:
        print()
        for i, f in enumerate(cult.followers, 1):
            print(f"  {i}. {f.name} ({', '.join(f.traits)})")
        raw = input("Номер последователя (Enter — назад): ").strip()
        if not raw:
            return
        if not (raw.isdigit() and 1 <= int(raw) <= len(cult.followers)):
            print("Нет такого номера.")
            continue
        follower = cult.followers[int(raw) - 1]
        new = input(f"Новое имя для «{follower.name}» (Enter — отмена): ")
        if not new.strip():
            continue
        err = rename_follower(cult, follower, new)
        print(err or f"Готово: {follower.name}.")


def intro(cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(f" {cult.name}".upper())
    print(" Продержись 30 дней, не потеряв ни веру, ни паству, ни голову.")
    print("═" * WIDTH)


def show_status(cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(f" День {cult.day} · {cult.name}")
    print(f" Вера          {bar(cult.faith)} {cult.faith}")
    print(f" Стабильность  {bar(cult.stability)} {cult.stability}")
    print(f" Еда: {cult.food}    Паства: {len(cult.followers)}")
    print("═" * WIDTH)


def show_changes(changes: dict[str, int]) -> None:
    parts = [f"{STAT_LABELS[k]} {d:+d}" for k, d in changes.items() if d]
    if parts:
        print("\n  [" + ", ".join(parts) + "]")


def ask_choice(choices: list[Choice], cult: Cult | None = None) -> Choice:
    while True:
        print()
        for i, ch in enumerate(choices, 1):
            print(textwrap.fill(f"{i}. {ch.text}", WIDTH, subsequent_indent="   "))
        if cult is not None:
            print("\n" + HINT)

        # Внутренний цикл: после команды выбор показывается заново
        while True:
            raw = input("\n> ").strip().lower()
            if raw in QUIT:
                raise SystemExit("Культ распущен по желанию основателя.")
            if cult is not None and raw in RENAME_CULT:
                rename_cult_flow(cult)
                break
            if cult is not None and raw in RENAME_FOLLOWER:
                rename_followers_flow(cult)
                break
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                return choices[int(raw) - 1]
            print("Введи номер варианта.")


def pause() -> None:
    input("\n[Enter — следующий день]")


def game_over(reason: str, cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(" КОНЕЦ")
    print("═" * WIDTH)
    say(reason)
    say(defeat_summary(cult))


def victory(cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(" ПОБЕДА")
    print("═" * WIDTH)
    say(victory_text(cult))
