"""Орден Тихой Козы — симулятор культа. Точка входа и игровой цикл."""
from __future__ import annotations

import random
import sys

from content.events import EVENTS
from game import ui
from game.engine import (
    WIN_DAY, apply_effects, check_defeat, create_cult, daily_tick, pick_event,
)
from game.models import resolve


def snapshot(cult) -> dict[str, int]:
    return {
        "Вера": cult.faith,
        "Стабильность": cult.stability,
        "Еда": cult.food,
        "Паства": len(cult.followers),
    }


def play(seed=None, ask=ui.ask_choice, pause=ui.pause) -> bool:
    """Одна партия. Возвращает True при победе. ask/pause можно подменить в тестах."""
    rng = random.Random(seed)
    cult = create_cult(rng)
    ui.intro(cult)

    while cult.day <= WIN_DAY:
        ui.show_status(cult)
        for line in daily_tick(cult, rng):
            ui.say(line)

        ending = check_defeat(cult)
        if ending:
            ui.game_over(ending, cult)
            return False

        event = pick_event(cult, EVENTS, rng)
        if event:
            cult.subject = event.subject(cult) if event.subject else None
            ui.say(resolve(event.text, cult))
            choice = ask(event.choices)

            before = snapshot(cult)
            apply_effects(cult, choice.effects, rng)
            if choice.action:
                choice.action(cult, rng)

            cult.last_event = event.id
            if event.once:
                cult.seen_events.add(event.id)

            ui.say(resolve(choice.outcome, cult))
            ui.show_changes(before, snapshot(cult))
            cult.subject = None

        ending = check_defeat(cult)
        if ending:
            ui.game_over(ending, cult)
            return False

        cult.day += 1
        pause()

    ui.victory(cult)
    return True


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else None
    try:
        play(seed)
    except (KeyboardInterrupt, EOFError):
        print("\nКульт распущен по желанию основателя.")
