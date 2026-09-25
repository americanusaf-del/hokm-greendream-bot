from __future__ import annotations

import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from flask import Flask, jsonify, request, send_from_directory

from telegram_bot.config import Settings
from telegram_bot.game import game_state


app = Flask(
    __name__,
    static_folder="web",
)


# ============================================================
# Telegram Mini App authentication
# ============================================================

def validate_telegram_init_data(
    init_data: str,
) -> dict:

    if not init_data:
        raise ValueError(
            "initData is missing"
        )

    settings = Settings.from_environment()

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
        raise ValueError(
            "Telegram hash is missing"
        )

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(
            parsed.items()
        )
    )

    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
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
        raise ValueError(
            "Invalid Telegram initData"
        )

    return parsed


def get_current_user():

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        "",
    )

    parsed = validate_telegram_init_data(
        init_data
    )

    user_json = parsed.get(
        "user"
    )

    if not user_json:
        raise ValueError(
            "Telegram user information is missing"
        )

    return json.loads(
        user_json
    )


# ============================================================
# Helpers
# ============================================================

def card_to_dict(card):

    return {
        "rank": card.rank,
        "suit": card.suit,
        "text": str(card),
    }


def game_to_dict(
    game,
    user_id: int,
):

    players = []

    for player in game.players.values():

        players.append(
            {
                "id": player.user_id,
                "name": player.name,
                "position": player.position,
                "is_me": (
                    player.user_id
                    == user_id
                ),
                "is_hakim": (
                    player.user_id
                    == game.hakim_id
                ),
                "cards_count": len(
                    game.hands.get(
                        player.user_id,
                        [],
                    )
                ),
                "tricks_won": game.tricks_won.get(
                    player.user_id,
                    0,
                ),
            }
        )

    current_trick = []

    for (
        player_id,
        card,
    ) in game.current_trick:

        player = game.players.get(
            player_id
        )

        if player is None:
            continue

        current_trick.append(
            {
                "player_id": player_id,
                "player_position": (
                    player.position
                ),
                "card": card_to_dict(
                    card
                ),
            }
        )

    # فقط دست خود بازیکن ارسال می‌شود.
    my_hand = [
        card_to_dict(card)
        for card in game.hands.get(
            user_id,
            [],
        )
    ]

    return {
        "id": game.game_id,
        "creator_id": game.creator_id,
        "started": game.started,
        "finished": game.finished,
        "max_players": game.max_players,
        "hakim_id": game.hakim_id,
        "hokm": game.hokm,
        "current_player_id": (
            game.current_player_id
        ),
        "lead_suit": game.lead_suit,
        "winner_id": game.winner_id,
        "team_scores": game.team_scores,
        "players": players,
        "current_trick": current_trick,
        "my_hand": my_hand,
        "my_user_id": user_id,
    }


def require_player(
    game_id: str,
    user_id: int,
):

    game = game_state.get_game(
        game_id
    )

    if game is None:
        return None, (
            jsonify(
                {
                    "ok": False,
                    "error": "game_not_found",
                }
            ),
            404,
        )

    if user_id not in game.players:
        return None, (
            jsonify(
                {
                    "ok": False,
                    "error": "not_a_player",
                }
            ),
            403,
        )

    return game, None


# ============================================================
# Pages
# ============================================================

@app.get("/")
def index():

    return send_from_directory(
        "web",
        "index.html",
    )


# ============================================================
# Health
# ============================================================

@app.get("/api/health")
def health():

    return jsonify(
        {
            "ok": True,
            "service": "hokm-greendream",
        }
    )


# ============================================================
# Get game
# ============================================================

@app.get(
    "/api/game/<game_id>"
)
def get_game(game_id: str):

    try:

        user = get_current_user()

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 401

    user_id = int(
        user["id"]
    )

    game, error = require_player(
        game_id,
        user_id,
    )

    if error:
        return error

    return jsonify(
        {
            "ok": True,
            "game": game_to_dict(
                game,
                user_id,
            ),
        }
    )


# ============================================================
# Start game from Mini App
# ============================================================

@app.post(
    "/api/game/<game_id>/start"
)
def start_game(game_id: str):

    try:

        user = get_current_user()

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 401

    user_id = int(
        user["id"]
    )

    game, error = require_player(
        game_id,
        user_id,
    )

    if error:
        return error

    # فقط سازنده اجازه شروع دارد.
    if game.creator_id != user_id:

        return jsonify(
            {
                "ok": False,
                "error": "creator_only",
            }
        ), 403

    result = game_state.start_game(
        game_id
    )

    if result != "started":

        return jsonify(
            {
                "ok": False,
                "error": result,
            }
        ), 400

    return jsonify(
        {
            "ok": True,
            "game": game_to_dict(
                game,
                user_id,
            ),
        }
    )


# ============================================================
# Set Hokm
# ============================================================

@app.post(
    "/api/game/<game_id>/hokm"
)
def set_hokm(game_id: str):

    try:

        user = get_current_user()

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 401

    user_id = int(
        user["id"]
    )

    game, error = require_player(
        game_id,
        user_id,
    )

    if error:
        return error

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    suit = str(
        data.get(
            "suit",
            "",
        )
    )

    result = game_state.set_hokm(
        game_id,
        user_id,
        suit,
    )

    if result != "selected":

        return jsonify(
            {
                "ok": False,
                "error": result,
            }
        ), 400

    return jsonify(
        {
            "ok": True,
            "hokm": suit,
            "game": game_to_dict(
                game,
                user_id,
            ),
        }
    )


# ============================================================
# Play card
# ============================================================

@app.post(
    "/api/game/<game_id>/play"
)
def play_card(game_id: str):

    try:

        user = get_current_user()

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 401

    user_id = int(
        user["id"]
    )

    game, error = require_player(
        game_id,
        user_id,
    )

    if error:
        return error

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    card_text = str(
        data.get(
            "card",
            "",
        )
    )

    if not card_text:

        return jsonify(
            {
                "ok": False,
                "error": "card_missing",
            }
        ), 400

    hand = game.hands.get(
        user_id,
        [],
    )

    card_index = None

    for (
        index,
        card,
    ) in enumerate(hand):

        if str(card) == card_text:

            card_index = index

            break

    if card_index is None:

        return jsonify(
            {
                "ok": False,
                "error": "card_not_in_hand",
            }
        ), 400

    result = game_state.play_card(
        game_id,
        user_id,
        card_index,
    )

    if not result.get("ok"):

        return jsonify(
            {
                "ok": False,
                "error": result.get(
                    "reason",
                    "play_failed",
                ),
            }
        ), 400

    return jsonify(
        {
            "ok": True,
            "card": card_to_dict(
                result["card"]
            ),
            "trick_finished": result.get(
                "trick_finished",
                False,
            ),
            "winner_id": result.get(
                "winner_id"
            ),
            "next_player_id": result.get(
                "next_player_id"
            ),
            "game": game_to_dict(
                game,
                user_id,
            ),
        }
    )


# ============================================================
# Run locally / Render
# ============================================================

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
