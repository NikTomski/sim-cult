"""Весь ввод/вывод. Движок про консоль ничего не знает."""
from __future__ import annotations

import textwrap

from .models import Choice, Cult

WIDTH = 70


def bar(value: int, width: int = 20) -> str:
    filled = round(max(0, min(100, value)) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def say(text: str) -> None:
    if text:
        print()
        print(textwrap.fill(text, WIDTH))


def intro(cult: Cult) -> None:
    print("═" * WIDTH)
    print(f" {cult.name}".upper())
    print(" Продержись 30 дней, не потеряв ни веру, ни паству, ни голову.")
    print(" (q — выход)")
    print("═" * WIDTH)


def show_status(cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(f" День {cult.day}")
    print(f" Вера          {bar(cult.faith)} {cult.faith}")
    print(f" Стабильность  {bar(cult.stability)} {cult.stability}")
    print(f" Еда: {cult.food}    Паства: {len(cult.followers)}")
    print("═" * WIDTH)


def show_changes(before: dict[str, int], after: dict[str, int]) -> None:
    parts = []
    for key, old in before.items():
        delta = after[key] - old
        if delta:
            parts.append(f"{key} {delta:+d}")
    if parts:
        print("\n  [" + ", ".join(parts) + "]")


def ask_choice(choices: list[Choice]) -> Choice:
    print()
    for i, ch in enumerate(choices, 1):
        print(textwrap.fill(f"{i}. {ch.text}", WIDTH, subsequent_indent="   "))
    while True:
        raw = input("\n> ").strip().lower()
        if raw in ("q", "й"):
            raise SystemExit("Культ распущен по желанию основателя.")
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
    say(f"Культ продержался дней: {cult.day}.")


def victory(cult: Cult) -> None:
    print()
    print("═" * WIDTH)
    print(" ПОБЕДА")
    print("═" * WIDTH)
    say(f"Тридцать дней позади. {cult.name} жив, паства (в количестве {len(cult.followers)}) "
        "сыта хотя бы духовно, а ты всё ещё стоишь у алтаря. Это уже можно назвать успехом.")
