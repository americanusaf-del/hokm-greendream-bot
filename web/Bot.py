from __future__ import annotations

import logging
import random

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from .game import SUITS, Card, GameRoom, game_state


logger = logging.getLogger(__name__)

BOT_USERNAME = "HokmgreendreamBot"

CHANNEL_USERNAME = "@greendreamze"
CHANNEL_LINK = "https://t.me/greendreamze"
SECOND_CHANNEL_LINK = "https://t.me/+CkjlXmCqFaM2M2Jk"

SUIT_NAMES = {
    "♥": "دل ♥",
    "♦": "خشت ♦",
    "♣": "گشنیز ♣",
    "♠": "پیک ♠",
}


# =========================================================
# KEYBOARDS
# =========================================================

def first_keyboard(owner_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 ساخت بازی حکم",
                callback_data=f"create:{owner_id}",
            )
        ]
    ])


def membership_keyboard(owner_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 عضویت در کانال اول",
                url=CHANNEL_LINK,
            )
        ],
        [
            InlineKeyboardButton(
                "📢 عضویت در کانال دوم",
                url=SECOND_CHANNEL_LINK,
            )
        ],
        [
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data=f"check:{owner_id}",
            )
        ],
    ])


def player_count_keyboard(owner_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎯 بازی یک‌نفره (تست)",
                callback_data=f"choose:{owner_id}:1",
            )
        ],
        [
            InlineKeyboardButton(
                "👥 بازی ۲ نفره",
                callback_data=f"choose:{owner_id}:2",
            ),
            InlineKeyboardButton(
                "👥 بازی ۴ نفره",
                callback_data=f"choose:{owner_id}:4",
            ),
        ],
    ])


def room_keyboard(game_id: str, started: bool = False):
    if started:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🃏 کارت‌های من",
                    callback_data=f"hand:{game_id}",
                ),
                InlineKeyboardButton(
                    "👑 انتخاب حکم",
                    callback_data=f"hokm:{game_id}",
                ),
            ]
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ پیوستن به بازی",
                callback_data=f"join:{game_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data=f"settings:{game_id}",
            ),
            InlineKeyboardButton(
                "▶️ شروع بازی",
                callback_data=f"start:{game_id}",
            ),
        ],
    ])


def settings_keyboard(game_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎯 ۱ نفره",
                callback_data=f"setcount:{game_id}:1",
            )
        ],
        [
            InlineKeyboardButton(
                "👥 ۲ نفره",
                callback_data=f"setcount:{game_id}:2",
            ),
            InlineKeyboardButton(
                "👥 ۴ نفره",
                callback_data=f"setcount:{game_id}:4",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data=f"back:{game_id}",
            )
        ],
    ])


def card_keyboard(game_id: str, hand: list[Card]):
    buttons = []

    for index, card in enumerate(hand):
        buttons.append(
            InlineKeyboardButton(
                str(card),
                callback_data=f"card:{game_id}:{index}",
            )
        )

    rows = []

    for i in range(0, len(buttons), 5):
        rows.append(buttons[i:i + 5])

    return InlineKeyboardMarkup(rows)


def suit_keyboard(game_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "♥ دل",
                callback_data=f"suit:{game_id}:♥",
            ),
            InlineKeyboardButton(
                "♦ خشت",
                callback_data=f"suit:{game_id}:♦",
            ),
        ],
        [
            InlineKeyboardButton(
                "♣ گشنیز",
                callback_data=f"suit:{game_id}:♣",
            ),
            InlineKeyboardButton(
                "♠ پیک",
                callback_data=f"suit:{game_id}:♠",
            ),
        ],
    ])


# =========================================================
# GAME TEXT
# =========================================================

def players_text(game: GameRoom) -> str:
    if not game.players:
        return "هنوز بازیکنی وارد نشده است."

    lines = []

    for number, player in enumerate(
        game.players.values(),
        start=1,
    ):
        name = player.name

        if player.user_id == game.creator_id:
            name += " 👑"

        if player.is_bot:
            name += " 🤖"

        lines.append(
            f"{number}. {name}"
        )

    return "\n".join(lines)


def room_text(game: GameRoom) -> str:
    if game.max_players == 1:
        game_type = "🎯 بازی یک‌نفره (تست)"
    else:
        game_type = (
            f"👥 بازی {game.max_players} نفره"
        )

    text = (
        "🎮 اتاق حکم گرین دریم\n\n"
        f"{game_type}\n"
        f"🔑 کد بازی: {game.game_id}\n\n"
        "👥 بازیکنان:\n"
        f"{players_text(game)}\n\n"
        f"👤 تعداد: "
        f"{len(game.players)}/{game.max_players}"
    )

    if game.started:
        text += "\n\n🎉 بازی شروع شده است!"

        if game.hokm:
            text += (
                f"\n🃏 حکم: "
                f"{SUIT_NAMES[game.hokm]}"
            )

        if game.current_player_id:
            player = game.players.get(
                game.current_player_id
            )

            if player:
                text += (
                    f"\n\n🎯 نوبت: "
                    f"{player.name}"
                )

    elif len(game.players) >= game.max_players:
        text += (
            "\n\n"
            "✅ ظرفیت کامل شد.\n"
            "▶️ فقط سازنده می‌تواند بازی را شروع کند."
        )
    else:
        remaining = (
            game.max_players
            - len(game.players)
        )

        text += (
            f"\n\n⏳ منتظر "
            f"{remaining} بازیکن دیگر هستیم."
        )

    return text


# =========================================================
# START
# =========================================================

async def start(update, context):
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "❤️ به حکم گرین دریم خوش آمدید!\n\n"
        "برای ساخت بازی در گروه بنویسید:\n\n"
        "@HokmgreendreamBot"
    )


# =========================================================
# INLINE
# =========================================================

async def inline_query(update, context):
    query = update.inline_query

    if query is None:
        return

    owner_id = query.from_user.id

    result = InlineQueryResultArticle(
        id=f"hokm_{owner_id}",
        title="🎮 بیایید حکم بازی کنیم!",
        description=(
            "بازی حکم یک‌نفره، ۲ نفره و ۴ نفره"
        ),
        input_message_content=InputTextMessageContent(
            "🎮 بیایید حکم بازی کنیم!\n\n"
            "❤️ حکم گرین دریم\n\n"
            "🎯 بازی یک‌نفره برای تست\n"
            "👥 بازی ۲ نفره و ۴ نفره\n"
            "🎲 ساخت اتاق و بازی با دوستان\n"
            "🏆 حاکم به صورت تصادفی انتخاب می‌شود\n\n"
            "👇 کی پایه‌ست؟"
        ),
        reply_markup=first_keyboard(owner_id),
    )

    await query.answer(
        [result],
        cache_time=0,
        is_personal=True,
    )


# =========================================================
# MEMBERSHIP
# =========================================================

async def is_channel_member(
    context,
    user_id: int,
    channel: str,
) -> bool:
    try:
        member = await context.bot.get_chat_member(
            chat_id=channel,
            user_id=user_id,
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
        )

    except TelegramError as error:
        logger.error(
            "Membership error: %s",
            error,
        )
        return False


async def check_all_memberships(
    context,
    user_id: int,
):
    first = await is_channel_member(
        context,
        user_id,
        CHANNEL_USERNAME,
    )

    # کانال دوم فعلاً خصوصی است و Chat ID آن
    # در اختیار کد نیست.
    second = True

    return first, second


async def show_membership(
    query,
    owner_id: int,
    first_ok: bool = False,
    second_ok: bool = False,
):
    first_status = (
        "✅ عضو هستید"
        if first_ok
        else "❌ عضو نیستید"
    )

    second_status = (
        "✅ آماده بررسی"
        if second_ok
        else "❌ عضو نیستید"
    )

    await query.edit_message_text(
        "🔒 قبل از ساخت بازی باید عضو کانال‌ها باشید.\n\n"
        f"📢 کانال اول: {first_status}\n"
        f"📢 کانال دوم: {second_status}\n\n"
        "ابتدا عضو کانال‌ها شوید و سپس "
        "«✅ بررسی عضویت» را بزنید.",
        reply_markup=membership_keyboard(
            owner_id
        ),
    )


# =========================================================
# CREATE
# =========================================================

async def show_player_count(
    query,
    owner_id: int,
):
    await query.edit_message_text(
        "🎮 نوع بازی را انتخاب کنید:\n\n"
        "🎯 یک‌نفره برای تست\n"
        "👥 دو نفره\n"
        "👥 چهار نفره",
        reply_markup=player_count_keyboard(
            owner_id
        ),
    )


async def create_game(
    query,
    player_count: int,
    owner_id: int,
):
    if query.from_user.id != owner_id:
        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند این کار را انجام دهد.",
            show_alert=True,
        )
        return

    user = query.from_user

    game = game_state.create_game(
        creator_id=owner_id,
        creator_name=user.full_name,
        max_players=player_count,
    )

    await query.answer(
        "🎮 بازی ساخته شد."
    )

    await query.edit_message_text(
        room_text(game),
        reply_markup=room_keyboard(
            game.game_id
        ),
    )


# =========================================================
# JOIN
# =========================================================

async def join_game(
    query,
    game_id: str,
    context,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    user = query.from_user

    if user.id in game.players:
        await query.answer(
            "✅ شما از قبل عضو بازی هستید.",
            show_alert=True,
        )
        return

    if game.started:
        await query.answer(
            "❌ بازی شروع شده است.",
            show_alert=True,
        )
        return

    first_ok, second_ok = (
        await check_all_memberships(
            context,
            user.id,
        )
    )

    if not first_ok:
        await query.answer(
            "🔒 ابتدا عضو کانال اول شوید.",
            show_alert=True,
        )
        return

    if not second_ok:
        await query.answer(
            "🔒 ابتدا عضو کانال دوم شوید.",
            show_alert=True,
        )
        return

    result = game_state.add_player(
        game_id,
        user.id,
        user.full_name,
    )

    if result == "full":
        await query.answer(
            "❌ ظرفیت بازی تکمیل است.",
            show_alert=True,
        )
        return

    await query.answer(
        "✅ با موفقیت وارد بازی شدید."
    )

    await query.edit_message_text(
        room_text(game),
        reply_markup=room_keyboard(
            game_id
        ),
    )


# =========================================================
# SETTINGS
# =========================================================

async def show_settings(
    query,
    game_id: str,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    if query.from_user.id != game.creator_id:
        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند تنظیمات را تغییر دهد.",
            show_alert=True,
        )
        return

    if game.started:
        await query.answer(
            "❌ بازی شروع شده است.",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        "⚙️ تنظیمات بازی\n\n"
        f"تعداد فعلی: {game.max_players} نفر\n\n"
        "تعداد بازیکنان را انتخاب کنید:",
        reply_markup=settings_keyboard(
            game_id
        ),
    )


async def change_player_count(
    query,
    game_id: str,
    new_count: int,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    if query.from_user.id != game.creator_id:
        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند تنظیمات را تغییر دهد.",
            show_alert=True,
        )
        return

    if game.started:
        await query.answer(
            "❌ بازی شروع شده است.",
            show_alert=True,
        )
        return

    current = len(game.players)

    if new_count < current:
        await query.answer(
            f"❌ الان {current} بازیکن داخل بازی هستند.",
            show_alert=True,
        )
        return

    game.max_players = new_count

    await query.answer(
        "✅ تعداد بازیکنان تغییر کرد."
    )

    await query.edit_message_text(
        room_text(game),
        reply_markup=room_keyboard(
            game_id
        ),
    )


async def back_to_room(
    query,
    game_id: str,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        room_text(game),
        reply_markup=room_keyboard(
            game_id,
            game.started,
        ),
    )


# =========================================================
# START GAME
# =========================================================

async def start_game(
    query,
    game_id: str,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    if query.from_user.id != game.creator_id:
        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند بازی را شروع کند.",
            show_alert=True,
        )
        return

    if len(game.players) != game.max_players:
        await query.answer(
            f"⏳ هنوز "
            f"{game.max_players - len(game.players)} "
            "بازیکن لازم است.",
            show_alert=True,
        )
        return

    result = game_state.start_game(
        game_id
    )

    if result != "started":
        await query.answer(
            f"❌ شروع بازی ممکن نشد: {result}",
            show_alert=True,
        )
        return

    # حالت تست: حکم خودکار
    if game.max_players == 1:
        game_state.set_hokm(
            game_id,
            game.creator_id,
            "♠",
        )

    hakim = game.players.get(
        game.hakim_id
    )

    hakim_name = (
        hakim.name
        if hakim
        else "نامشخص"
    )

    await query.answer(
        "🎉 بازی شروع شد!"
    )

    await query.edit_message_text(
        "🎉 بازی شروع شد!\n\n"
        f"👥 تعداد بازیکنان: {game.max_players}\n\n"
        "👥 بازیکنان:\n"
        f"{players_text(game)}\n\n"
        f"👑 حاکم: {hakim_name}\n\n"
        + (
            "🃏 حکم تست: پیک ♠\n\n"
            if game.max_players == 1
            else "👑 حاکم باید حکم را انتخاب کند.\n\n"
        )
        + "🃏 برای دیدن کارت‌ها روی "
        "«کارت‌های من» بزنید.",
        reply_markup=room_keyboard(
            game_id,
            True,
        ),
    )


# =========================================================
# SHOW HAND
# =========================================================

async def show_hand(
    query,
    game_id: str,
    context,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    user_id = query.from_user.id

    if user_id not in game.players:
        await query.answer(
            "⛔ شما بازیکن این بازی نیستید.",
            show_alert=True,
        )
        return

    hand = game_state.get_hand(
        game_id,
        user_id,
    )

    if not hand:
        await query.answer(
            "🃏 کارت دیگری ندارید.",
            show_alert=True,
        )
        return

    turn_text = ""

    if game.current_player_id == user_id:
        turn_text = "🎯 نوبت شماست."
    else:
        current = game.players.get(
            game.current_player_id
        )

        if current:
            turn_text = (
                f"⏳ نوبت {current.name} است."
            )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🃏 کارت‌های شما\n\n"
                f"{turn_text}\n\n"
                f"🃏 تعداد کارت: {len(hand)}\n\n"
                "روی کارت مجاز بزنید."
            ),
            reply_markup=card_keyboard(
                game_id,
                hand,
            ),
        )

        await query.answer(
            "🃏 کارت‌های شما باز شد."
        )

    except TelegramError:
        await query.answer(
            "⚠️ ابتدا در خصوصی ربات /start را بزنید.",
            show_alert=True,
        )


# =========================================================
# PLAY CARD
# =========================================================

async def select_card(
    query,
    game_id: str,
    card_index: int,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    user_id = query.from_user.id

    if user_id not in game.players:
        await query.answer(
            "⛔ شما بازیکن این بازی نیستید.",
            show_alert=True,
        )
        return

    result = game_state.play_card(
        game_id,
        user_id,
        card_index,
    )

    if not result["ok"]:

        messages = {
            "not_your_turn":
                "⏳ هنوز نوبت شما نیست.",

            "hokm_not_selected":
                "👑 ابتدا باید حکم انتخاب شود.",

            "must_follow_suit":
                "❌ باید از خال شروع بازی کنید.",

            "invalid_card":
                "❌ این کارت معتبر نیست.",

            "finished":
                "🏁 بازی تمام شده است.",

            "not_started":
                "❌ بازی هنوز شروع نشده است.",
        }

        await query.answer(
            messages.get(
                result["reason"],
                "❌ امکان بازی کردن این کارت نیست.",
            ),
            show_alert=True,
        )

        return

    card = result["card"]

    if result["trick_finished"]:

        winner_id = result["winner_id"]

        winner = game.players.get(
            winner_id
        )

        winner_name = (
            winner.name
            if winner
            else "بازیکن"
        )

        if game.finished:

            await query.answer(
                f"🏆 {winner_name} برنده آخرین دست شد!"
            )

            await query.edit_message_text(
                "🏆 بازی تمام شد!\n\n"
                f"آخرین دست را {winner_name} برد.\n\n"
                f"🎯 امتیاز تیم ۱: "
                f"{game.team_scores[0]}\n"
                f"🎯 امتیاز تیم ۲: "
                f"{game.team_scores[1]}"
            )

            return

        await query.answer(
            f"🃏 {card} بازی شد.\n"
            f"🏆 {winner_name} این دست را برد."
        )

        remaining = len(
            game_state.get_hand(
                game_id,
                user_id,
            )
        )

        await query.edit_message_text(
            "🃏 کارت‌های شما\n\n"
            f"✅ کارت بازی‌شده: {card}\n\n"
            f"🏆 این دست را {winner_name} برد.\n\n"
            f"🃏 کارت‌های باقی‌مانده: {remaining}\n\n"
            f"🎯 نوبت: {winner_name}",
            reply_markup=(
                card_keyboard(
                    game_id,
                    game_state.get_hand(
                        game_id,
                        user_id,
                    ),
                )
                if game_state.get_hand(
                    game_id,
                    user_id,
                )
                else None
            ),
        )

        return

    next_player_id = result[
        "next_player_id"
    ]

    next_player = game.players.get(
        next_player_id
    )

    next_name = (
        next_player.name
        if next_player
        else "بازیکن بعدی"
    )

    hand = game_state.get_hand(
        game_id,
        user_id,
    )

    await query.answer(
        f"🃏 {card} بازی شد."
    )

    await query.edit_message_text(
        "🃏 کارت‌های شما\n\n"
        f"✅ کارت بازی‌شده: {card}\n\n"
        f"⏳ نوبت {next_name} است.\n\n"
        f"🃏 کارت‌های باقی‌مانده: {len(hand)}",
        reply_markup=(
            card_keyboard(
                game_id,
                hand,
            )
            if hand
            else None
        ),
    )


# =========================================================
# HOKM
# =========================================================

async def show_hokm(
    query,
    game_id: str,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    if query.from_user.id != game.hakim_id:
        await query.answer(
            "⛔ فقط حاکم می‌تواند حکم را انتخاب کند.",
            show_alert=True,
        )
        return

    if game.hokm is not None:
        await query.answer(
            f"🃏 حکم: "
            f"{SUIT_NAMES[game.hokm]}",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        "👑 شما حاکم هستید.\n\n"
        "🃏 حکم را انتخاب کنید:",
        reply_markup=suit_keyboard(
            game_id
        ),
    )


async def select_suit(
    query,
    game_id: str,
    suit: str,
):
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )
        return

    result = game_state.set_hokm(
        game_id,
        query.from_user.id,
        suit,
    )

    if result != "selected":
        messages = {
            "not_hakim":
                "⛔ فقط حاکم می‌تواند حکم را انتخاب کند.",
            "already_selected":
                "❌ حکم قبلاً انتخاب شده.",
            "invalid_suit":
                "❌ حکم نامعتبر.",
        }

        await query.answer(
            messages.get(
                result,
                "❌ امکان انتخاب حکم نیست.",
            ),
            show_alert=True,
        )
        return

    await query.answer(
        "✅ حکم انتخاب شد!"
    )

    await query.edit_message_text(
        "🎉 حکم انتخاب شد!\n\n"
        f"👑 حاکم: {query.from_user.full_name}\n"
        f"🃏 حکم: {SUIT_NAMES[suit]}\n\n"
        "🎯 بازی آماده ادامه است.",
        reply_markup=room_keyboard(
            game_id,
            True,
        ),
    )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(
    update,
    context,
):
    query = update.callback_query

    if query is None:
        return

    data = query.data or ""

    logger.info(
        "Button: %s | User: %s",
        data,
        query.from_user.id,
    )

    # CREATE
    if data.startswith("create:"):

        try:
            owner_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        if query.from_user.id != owner_id:
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند این کار را انجام دهد.",
                show_alert=True,
            )
            return

        first_ok, second_ok = (
            await check_all_memberships(
                context,
                owner_id,
            )
        )

        if not first_ok or not second_ok:
            await show_membership(
                query,
                owner_id,
                first_ok,
                second_ok,
            )
            return

        await show_player_count(
            query,
            owner_id,
        )
        return

    # CHECK
    if data.startswith("check:"):

        try:
            owner_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        if query.from_user.id != owner_id:
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند این کار را انجام دهد.",
                show_alert=True,
            )
            return

        first_ok, second_ok = (
            await check_all_memberships(
                context,
                owner_id,
            )
        )

        if not first_ok or not second_ok:
            await query.answer(
                "❌ هنوز عضویت کامل تأیید نشده است.",
                show_alert=True,
            )

            await show_membership(
                query,
                owner_id,
                first_ok,
                second_ok,
            )
            return

        await query.answer(
            "✅ عضویت تأیید شد!"
        )

        await show_player_count(
            query,
            owner_id,
        )
        return

    # CHOOSE
    if data.startswith("choose:"):

        parts = data.split(":")

        if len(parts) != 3:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        try:
            owner_id = int(parts[1])
            player_count = int(parts[2])
        except ValueError:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        if query.from_user.id != owner_id:
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند این کار را انجام دهد.",
                show_alert=True,
            )
            return

        if player_count not in (1, 2, 4):
            await query.answer(
                "❌ تعداد بازیکن نامعتبر.",
                show_alert=True,
            )
            return

        await create_game(
            query,
            player_count,
            owner_id,
        )
        return

    # JOIN
    if data.startswith("join:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await join_game(
            query,
            game_id,
            context,
        )
        return

    # SETTINGS
    if data.startswith("settings:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await show_settings(
            query,
            game_id,
        )
        return

    # SET COUNT
    if data.startswith("setcount:"):

        parts = data.split(":")

        if len(parts) != 3:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        game_id = parts[1]

        try:
            new_count = int(parts[2])
        except ValueError:
            await query.answer(
                "❌ تعداد نامعتبر.",
                show_alert=True,
            )
            return

        await change_player_count(
            query,
            game_id,
            new_count,
        )
        return

    # BACK
    if data.startswith("back:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await back_to_room(
            query,
            game_id,
        )
        return

    # START
    if data.startswith("start:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await start_game(
            query,
            game_id,
        )
        return

    # HAND
    if data.startswith("hand:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await show_hand(
            query,
            game_id,
            context,
        )
        return

    # CARD
    if data.startswith("card:"):

        parts = data.split(":")

        if len(parts) != 3:
            await query.answer(
                "❌ کارت نامعتبر.",
                show_alert=True,
            )
            return

        game_id = parts[1]

        try:
            card_index = int(parts[2])
        except ValueError:
            await query.answer(
                "❌ کارت نامعتبر.",
                show_alert=True,
            )
            return

        await select_card(
            query,
            game_id,
            card_index,
        )
        return

    # HOKM
    if data.startswith("hokm:"):
        game_id = data.split(
            ":",
            1,
        )[1]

        await show_hokm(
            query,
            game_id,
        )
        return

    # SUIT
    if data.startswith("suit:"):

        parts = data.split(
            ":",
            2,
        )

        if len(parts) != 3:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        game_id = parts[1]
        suit = parts[2]

        await select_suit(
            query,
            game_id,
            suit,
        )
        return

    await query.answer(
        "❌ دکمه نامعتبر است.",
        show_alert=True,
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context,
):
    logger.error(
        "BOT ERROR: %s",
        context.error,
        exc_info=context.error,
    )


# =========================================================
# APPLICATION
# =========================================================

def build_application(settings):

    application = (
        Application.builder()
        .token(settings.bot_token)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        InlineQueryHandler(
            inline_query,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler,
        )
    )

    application.add_error_handler(
        error_handler,
    )

    return application


# =========================================================
# RUN
# =========================================================

def run():

    logging.basicConfig(
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        level=logging.INFO,
    )

    from .config import Settings

    settings = Settings.from_environment()

    application = build_application(
        settings
    )

    logger.info(
        "❤️ Hokm Green Dream Bot started"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    run()
