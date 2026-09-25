from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
)

from telegram_bot.game import game_state


app = Flask(__name__)

BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    "",
).strip()


def validate_telegram_data(
    init_data: str,
):

    if not init_data:
        return None

    try:

        parsed = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True,
            )
        )

        received_hash = parsed.pop(
            "hash",
            None,
        )

        if not received_hash:
            return None

        auth_date = int(
            parsed.get(
                "auth_date",
                "0",
            )
        )

        if time.time() - auth_date > 86400:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(
                parsed.items()
            )
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash,
        ):
            return None

        user_json = parsed.get(
            "user"
        )

        if not user_json:
            return None

        return json.loads(
            user_json
        )

    except Exception as exc:

        print(
            "Telegram validation error:",
            exc,
        )

        return None


def current_user():

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        "",
    )

    return validate_telegram_data(
        init_data
    )


def require_player(
    game_id: str,
):

    user = current_user()

    if not user:

        return None, (
            jsonify(
                {
                    "error":
                        "کاربر تلگرام شناسایی نشد."
                }
            ),
            401,
        )

    player_id = int(
        user["id"]
    )

    game = game_state.get_game(
        game_id
    )

    if not game:

        return None, (
            jsonify(
                {
                    "error":
                        "بازی پیدا نشد."
                }
            ),
            404,
        )

    player = game_state.get_player(
        game,
        player_id,
    )

    if not player:

        return None, (
            jsonify(
                {
                    "error":
                        "شما بازیکن این بازی نیستید."
                }
            ),
            403,
        )

    return user, None


def advance_bots(
    game_id: str,
):

    """
    هر بار که صفحه وضعیت بازی را می‌گیرد،
    اگر نوبت ربات باشد، ربات حرکت می‌کند.

    این حلقه باعث می‌شود اگر چند ربات پشت سر هم
    نوبت داشته باشند، بازی گیر نکند.
    """

    for _ in range(8):

        game = game_state.get_game(
            game_id
        )

        if not game:
            return

        if not game.started:
            return

        if game.finished:
            return

        result = game_state.bot_turn(
            game_id
        )

        if result is None:
            return


@app.get("/")
def home():

    return send_from_directory(
        "web",
        "index.html",
    )


@app.get("/api/health")
def health():

    return jsonify(
        {
            "ok": True
        }
    )


@app.get(
    "/api/game/<game_id>"
)
def get_game(
    game_id,
):

    user, error = require_player(
        game_id
    )

    if error:
        return error

    player_id = int(
        user["id"]
    )

    # حرکت خودکار ربات‌ها
    advance_bots(
        game_id
    )

    state = game_state.state_for_player(
        game_id,
        player_id,
    )

    if state is None:

        return jsonify(
            {
                "error":
                    "بازی پیدا نشد."
            }
        ), 404

    return jsonify(
        state
    )


@app.post(
    "/api/game/<game_id>/start"
)
def start_game(
    game_id,
):

    user, error = require_player(
        game_id
    )

    if error:
        return error

    player_id = int(
        user["id"]
    )

    ok, message = game_state.start_game(
        game_id,
        player_id,
    )

    if not ok:

        return jsonify(
            {
                "error": message
            }
        ), 400

    # اگر حاکم ربات باشد،
    # همین‌جا حکم را انتخاب کند.
    advance_bots(
        game_id
    )

    return jsonify(
        {
            "ok": True,
            "message": message,
        }
    )


@app.post(
    "/api/game/<game_id>/hokm"
)
def set_hokm(
    game_id,
):

    user, error = require_player(
        game_id
    )

    if error:
        return error

    player_id = int(
        user["id"]
    )

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    suit = data.get(
        "suit"
    )

    ok, message = game_state.set_hokm(
        game_id,
        player_id,
        suit,
    )

    if not ok:

        return jsonify(
            {
                "error": message
            }
        ), 400

    # بعد از حکم، اگر نوبت ربات باشد،
    # ربات‌ها حرکت می‌کنند.
    advance_bots(
        game_id
    )

    return jsonify(
        {
            "ok": True,
            "message": message,
        }
    )


@app.post(
    "/api/game/<game_id>/play"
)
def play_card(
    game_id,
):

    user, error = require_player(
        game_id
    )

    if error:
        return error

    player_id = int(
        user["id"]
    )

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    suit = data.get(
        "suit"
    )

    rank = data.get(
        "rank"
    )

    try:

        rank = int(rank)

    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "error":
                    "کارت نامعتبر است."
            }
        ), 400

    ok, message = game_state.play_card(
        game_id,
        player_id,
        suit,
        rank,
    )

    if not ok:

        return jsonify(
            {
                "error": message
            }
        ), 400

    # بعد از بازی کارت،
    # اگر نوبت ربات‌ها باشد حرکت می‌کنند.
    advance_bots(
        game_id
    )

    return jsonify(
        {
            "ok": True,
            "message": message,
        }
    )


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
