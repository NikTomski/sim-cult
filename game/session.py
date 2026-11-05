"""Пошаговая игровая сессия.

Через этот класс идёт вся партия: и консольная версия (main.py), и веб-сервер (app.py).
Здесь нет ни print, ни input: сессия принимает команды (start / choose / next_day)
и отдаёт состояние (view), которое легко превратить в JSON.

Фазы:  setup → event → outcome → event → ... → over | won
"""
from __future__ import annotations

import random

from content.events import EVENTS

from .engine import (
    WIN_DAY, apply_effects, check_defeat, create_cult, daily_tick,
    pick_event, rename_cult, rename_follower,
)
from .models import Cult, Event, resolve

STAT_LABELS = {
    "faith": "Вера",
    "stability": "Стабильность",
    "food": "Еда",
    "followers": "Паства",
}


class GameError(Exception):
    """Команда недопустима в текущей фазе игры."""


def snapshot(cult: Cult) -> dict[str, int]:
    return {
        "faith": cult.faith,
        "stability": cult.stability,
        "food": cult.food,
        "followers": len(cult.followers),
    }


def victory_text(cult: Cult) -> str:
    return (
        f"Тридцать дней позади. Культ «{cult.name}» устоял, паства (в количестве "
        f"{len(cult.followers)}) сыта хотя бы духовно, а ты всё ещё стоишь у алтаря. "
        "Это уже можно назвать успехом."
    )


def defeat_summary(cult: Cult) -> str:
    return f"Культ «{cult.name}» продержался дней: {cult.day}."


class GameSession:
    def __init__(self, seed: int | None = None, events: list[Event] | None = None):
        self.rng = random.Random(seed)
        self.events = events if events is not None else EVENTS
        self.cult = create_cult(self.rng)
        self.phase = "setup"
        self.messages: list[str] = []
        self.event: Event | None = None
        self.event_text = ""
        self.outcome = ""
        self.changes: dict[str, int] = {}
        self.ending = ""

    # ── переименование (доступно в любой фазе) ────────────────────────────────

    def rename_cult(self, raw: str) -> str | None:
        return rename_cult(self.cult, raw)

    def rename_follower(self, index: int, raw: str) -> str | None:
        if not isinstance(index, int) or not 0 <= index < len(self.cult.followers):
            return "Нет такого последователя."
        return rename_follower(self.cult, self.cult.followers[index], raw)

    # ── ход игры ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._require("setup")
        self._begin_day()

    def choose(self, index: int) -> None:
        self._require("event")
        choices = self.event.choices
        if not isinstance(index, int) or not 0 <= index < len(choices):
            raise ValueError("Нет такого варианта.")
        choice = choices[index]
        cult = self.cult

        before = snapshot(cult)
        apply_effects(cult, choice.effects, self.rng)
        if choice.action:
            choice.action(cult, self.rng)

        cult.last_event = self.event.id
        if self.event.once:
            cult.seen_events.add(self.event.id)

        self.outcome = resolve(choice.outcome, cult)
        after = snapshot(cult)
        self.changes = {k: after[k] - before[k] for k in before if after[k] != before[k]}
        cult.subject = None

        ending = check_defeat(cult)
        if ending:
            self._finish(ending)
        else:
            self.phase = "outcome"

    def next_day(self) -> None:
        self._require("outcome")
        self.cult.day += 1
        if self.cult.day > WIN_DAY:
            self.phase = "won"
            self.messages, self.event_text, self.outcome, self.changes = [], "", "", {}
            return
        self._begin_day()

    # ── внутреннее ────────────────────────────────────────────────────────────

    def _require(self, phase: str) -> None:
        if self.phase != phase:
            raise GameError(f"Сейчас так нельзя (фаза игры: {self.phase}).")

    def _begin_day(self) -> None:
        cult = self.cult
        self.outcome, self.changes, self.event_text, self.event = "", {}, "", None
        self.messages = daily_tick(cult, self.rng)

        ending = check_defeat(cult)
        if ending:
            self._finish(ending)
            return

        self.event = pick_event(cult, self.events, self.rng)
        if self.event is None:
            self.event_text = "Тихий день: ничего не случилось."
            self.phase = "outcome"
            return
        cult.subject = self.event.subject(cult) if self.event.subject else None
        self.event_text = resolve(self.event.text, cult)
        self.phase = "event"

    def _finish(self, reason: str) -> None:
        self.phase = "over"
        self.ending = reason
        self.cult.subject = None

    # ── состояние для интерфейса ──────────────────────────────────────────────

    def view(self) -> dict:
        c = self.cult
        summary = ""
        if self.phase == "over":
            summary = defeat_summary(c)
        elif self.phase == "won":
            summary = victory_text(c)
        return {
            "phase": self.phase,
            "day": min(c.day, WIN_DAY),
            "win_day": WIN_DAY,
            "cult_name": c.name,
            "stats": snapshot(c),
            "followers": [{"name": f.name, "traits": list(f.traits)} for f in c.followers],
            "messages": list(self.messages),
            "event_text": self.event_text,
            "choices": [ch.text for ch in self.event.choices]
                       if self.phase == "event" and self.event else [],
            "outcome": self.outcome,
            "changes": [{"stat": k, "delta": d} for k, d in self.changes.items()],
            "ending": self.ending,
            "summary": summary,
        }
