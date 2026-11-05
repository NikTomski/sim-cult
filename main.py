"""Орден Тихой Козы — симулятор культа (консольная версия)."""
from __future__ import annotations

import sys

from game import ui
from game.session import GameSession


def play(seed=None, ask=ui.ask_choice, pause=ui.pause, setup=ui.setup) -> bool:
    """Одна партия. Возвращает True при победе. ask/pause/setup можно подменить в тестах."""
    game = GameSession(seed)
    cult = game.cult
    setup(cult)  # название культа и имена паствы
    ui.intro(cult)
    game.start()

    while True:
        ui.show_status(cult)
        for line in game.messages:
            ui.say(line)
        if game.phase == "over":  # поражение уже при утреннем подсчёте
            ui.game_over(game.ending, cult)
            return False

        ui.say(game.event_text)
        if game.phase == "event":
            choices = game.event.choices
            choice = ask(choices, cult)
            index = next(i for i, c in enumerate(choices) if c is choice)
            game.choose(index)
            ui.say(game.outcome)
            ui.show_changes(game.changes)
            if game.phase == "over":
                ui.game_over(game.ending, cult)
                return False

        pause()
        game.next_day()
        if game.phase == "won":
            ui.victory(cult)
            return True


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else None
    try:
        play(seed)
    except (KeyboardInterrupt, EOFError):
        print("\nКульт распущен по желанию основателя.")
