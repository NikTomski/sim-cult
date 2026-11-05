"""Веб-сервер игры: Flask + JSON API.

Партии хранятся в памяти процесса (по одной на игрока), поэтому запускай ровно один
рабочий процесс (gunicorn -w 1). После перезапуска сервера активные партии сбрасываются.

Локально:   python app.py   →  http://127.0.0.1:5000
"""
from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from game.session import GameError, GameSession

WEB_DIR = Path(__file__).parent / "web"
STATIC_FILES = {"style.css", "game.js"}

SESSION_TTL = 6 * 60 * 60   # партия без активности живёт 6 часов
MAX_SESSIONS = 2000         # защита памяти сервера

app = Flask(__name__)
app.json.ensure_ascii = False             # кириллица в JSON без \uXXXX
app.config["MAX_CONTENT_LENGTH"] = 4096   # тела запросов крошечные


# ── хранилище сессий ─────────────────────────────────────────────────────────

@dataclass
class _Entry:
    game: GameSession
    touched: float
    lock: threading.Lock = field(default_factory=threading.Lock)


_sessions: dict[str, _Entry] = {}
_sessions_lock = threading.Lock()


def _prune(now: float) -> None:
    """Убирает просроченные партии; при переполнении выкидывает самые старые."""
    for token in [t for t, e in _sessions.items() if now - e.touched > SESSION_TTL]:
        del _sessions[token]
    if len(_sessions) >= MAX_SESSIONS:
        oldest = sorted(_sessions, key=lambda t: _sessions[t].touched)
        for token in oldest[: len(_sessions) - MAX_SESSIONS + 1]:
            del _sessions[token]


def _create() -> tuple[str, _Entry]:
    now = time.monotonic()
    token = secrets.token_urlsafe(16)
    entry = _Entry(GameSession(), now)
    with _sessions_lock:
        _prune(now)
        _sessions[token] = entry
    return token, entry


def _lookup(token: str) -> _Entry | None:
    now = time.monotonic()
    with _sessions_lock:
        entry = _sessions.get(token)
        if entry is None:
            return None
        if now - entry.touched > SESSION_TTL:
            del _sessions[token]
            return None
        entry.touched = now
        return entry


def game_endpoint(fn):
    """Находит партию по заголовку X-Session и вызывает fn(game) под её замком."""
    @wraps(fn)
    def wrapper():
        entry = _lookup(request.headers.get("X-Session", ""))
        if entry is None:
            return jsonify(error="Сессия не найдена или истекла.", code="no_session"), 401
        with entry.lock:
            try:
                return fn(entry.game)
            except GameError as exc:
                return jsonify(error=str(exc), view=entry.game.view()), 409
            except ValueError as exc:
                return jsonify(error=str(exc)), 400
    return wrapper


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ── API ──────────────────────────────────────────────────────────────────────

@app.post("/api/new")
def api_new():
    token, entry = _create()
    return jsonify(token=token, view=entry.game.view())


@app.get("/api/state")
@game_endpoint
def api_state(game):
    return jsonify(view=game.view())


@app.post("/api/start")
@game_endpoint
def api_start(game):
    game.start()
    return jsonify(view=game.view())


@app.post("/api/choose")
@game_endpoint
def api_choose(game):
    index = _body().get("index")
    if not _is_int(index):
        return jsonify(error="Нужен номер варианта."), 400
    game.choose(index)
    return jsonify(view=game.view())


@app.post("/api/next")
@game_endpoint
def api_next(game):
    game.next_day()
    return jsonify(view=game.view())


@app.post("/api/rename/cult")
@game_endpoint
def api_rename_cult(game):
    name = _body().get("name")
    if not isinstance(name, str):
        return jsonify(error="Нужно название."), 400
    error = game.rename_cult(name)
    if error:
        return jsonify(error=error), 400
    return jsonify(view=game.view())


@app.post("/api/rename/follower")
@game_endpoint
def api_rename_follower(game):
    body = _body()
    index, name = body.get("index"), body.get("name")
    if not _is_int(index) or not isinstance(name, str):
        return jsonify(error="Нужны номер последователя и имя."), 400
    error = game.rename_follower(index, name)
    if error:
        return jsonify(error=error), 400
    return jsonify(view=game.view())


# ── страница и статика ───────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/<path:name>")
def static_file(name):
    if name not in STATIC_FILES:
        abort(404)
    return send_from_directory(WEB_DIR, name)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Слишком большой запрос."), 413


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; frame-ancestors 'none'")
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
