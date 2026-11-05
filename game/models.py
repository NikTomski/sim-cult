"""Модели данных: состояние культа, последователи, события."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Union

# Текст может быть строкой или функцией от состояния культа
TextSource = Union[str, Callable[["Cult"], str]]


@dataclass
class Follower:
    name: str
    traits: list[str]
    loyalty: int = 50
    secret: str | None = None
    # Личная история: флаги вроде "herald", "tolerated", "renounced"
    flags: set[str] = field(default_factory=set)


@dataclass
class Cult:
    name: str = "Орден Тихой Козы"
    faith: int = 50
    stability: int = 50
    food: int = 20
    day: int = 1
    followers: list[Follower] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    seen_events: set[str] = field(default_factory=set)
    last_event: str | None = None
    # Герой текущего личного события (ставит main.py перед показом текста)
    subject: Follower | None = None


def resolve(text: TextSource, cult: Cult) -> str:
    """Возвращает текст: либо саму строку, либо результат функции."""
    return text(cult) if callable(text) else text


@dataclass
class Choice:
    text: str
    effects: dict[str, int] = field(default_factory=dict)
    outcome: TextSource = ""
    # Необязательное действие со сложной логикой: action(cult, rng)
    action: Callable[[Cult, random.Random], None] | None = None


@dataclass
class Event:
    id: str
    text: TextSource
    choices: list[Choice]
    condition: Callable[[Cult], bool] = lambda cult: True
    weight: int = 1
    once: bool = False
    # Личное событие: функция выбирает героя (или None, если событие недоступно).
    # Во время события герой доступен как cult.subject.
    subject: Callable[[Cult], Follower | None] | None = None
