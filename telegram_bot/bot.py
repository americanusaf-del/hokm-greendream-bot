"""Telegram bot handlers for Hokm."""

from __future__ import annotations

import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from .game import SUITS, game_state
from .config import Settings


LOGGER = logging.getLogger(__name__)

BOT_USERNAME = "HokmgreendreamBot"

CHANNEL_USERNAME = "@greendreamze"
CHANNEL_LINK = "https://t.me/greendreamze"
SECOND_CHANNEL_LINK = "https://t.me/+CkjlXmCqFaM2M2Jk"

WEB_APP_URL = os.environ.get(
    "WEB_APP_URL",
    "https://hokm-greendream-bot.onrender.com",
).strip()


SUIT_NAMES = {
    "♥": "♥️ دل",
    "♦": "♦️ خشت",
    "♣": "♣️ گشنیز",
    "♠": "♠️ پیک",
}


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ورود به Green Dream",
                    web_app=WebAppInfo(
                        url=WEB_APP_URL,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🎮 ساخت بازی",
                    callback_data="create_game",
                )
            ],
            [
                InlineKeyboardButton(
                    "📖 راهنما",
                    callback_data="help",
                )
            ],
        ]
    )


def membership_keyboard() -> InlineKeyboardMarkup:
    """Membership buttons."""
    return InlineKeyboardMarkup(
        [
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
                    callback_data="check_membership",
                )
            ],
        ]
    )


def game_keyboard(
    game_id: str,
    creator_id: int,
) -> InlineKeyboardMarkup:
    """Game room keyboard."""
    rows = [
        [
            InlineKeyboardButton(
                "➕ ورود به بازی",
                callback_data=f"join:{game_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data=f"settings:{game_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "▶️ شروع بازی",
                callback_data=f"start:{game_id}",
            )
        ],
    ]

    if WEB_APP_URL:
        rows.insert(
            0,
            [
                InlineKeyboardButton(
                    "🎮 ورود به میز بازی",
                    web_app=WebAppInfo(
                        url=f"{WEB_APP_URL}/?game={game_id}",
                    ),
                )
            ],
        )

    return InlineKeyboardMarkup(rows)


def settings_keyboard(game_id: str) -> InlineKeyboardMarkup:
    """Settings keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👥 تعداد بازیکنان",
                    callback_data=f"choose_players:{game_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data=f"back_room:{game_id}",
                )
            ],
        ]
    )


def card_keyboard(
    game_id: str,
    cards: list,
) -> InlineKeyboardMarkup:
    """Cards keyboard."""
    rows = []
    row = []

    for index, card in enumerate(cards):
        row.append(
            InlineKeyboardButton(
                str(card),
                callback_data=f"card:{game_id}:{index}",
            )
        )

        if len(row) == 4:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def suit_keyboard(game_id: str) -> InlineKeyboardMarkup:
    """Hokm selection keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    SUIT_NAMES["♥"],
                    callback_data=f"hokm:{game_id}:♥",
                ),
                InlineKeyboardButton(
                    SUIT_NAMES["♦"],
                    callback_data=f"hokm:{game_id}:♦",
                ),
            ],
            [
                InlineKeyboardButton(
                    SUIT_NAMES["♣"],
                    callback_data=f"hokm:{game_id}:♣",
                ),
                InlineKeyboardButton(
                    SUIT_NAMES["♠"],
                    callback_data=f"hokm:{game_id}:♠",
                ),
            ],
        ]
    )


def player_list_text(game) -> str:
    """Build player list."""
    lines = []

    for index, player in enumerate(
        game.players.values(),
        start=1,
    ):
        marker = (
            " 👑"
            if player.user_id == game.creator_id
            else ""
        )

        lines.append(
            f"{index}. {player.name}{marker}"
        )

    if not lines:
        return "هنوز بازیکنی وارد نشده است."

    return "\n".join(lines)


async def is_member(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:
    """Check membership in required channel."""
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id,
        )

        return member.status in {
            "member",
            "administrator",
            "creator",
        }

    except Exception:
        LOGGER.exception(
            "Membership check failed for user %s",
            user_id,
        )

        return True


async def create_game_for_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    user_name: str,
) -> None:
    """Create a game from a normal private chat message."""
    if update.message is None:
        return

    member = await is_member(
        context,
        user_id,
    )

    if not member:
        await update.message.reply_text(
            "🔒 قبل از ساخت بازی باید در کانال عضو باشی.\n\n"
            "بعد از عضویت روی «بررسی عضویت» بزن.",
            reply_markup=membership_keyboard(),
        )
        return

    game = game_state.create_game(
        creator_id=user_id,
        creator_name=user_name,
        max_players=1,
    )

    await update.message.reply_text(
        "🎮 اتاق بازی ساخته شد!\n\n"
        f"🆔 کد بازی: `{game.game_id}`\n\n"
        f"👥 بازیکنان:\n"
        f"{player_list_text(game)}\n\n"
        "تعداد بازیکنان را از تنظیمات انتخاب کن.",
        parse_mode="Markdown",
        reply_markup=game_keyboard(
            game.game_id,
            game.creator_id,
        ),
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start."""
    user = update.effective_user

    if user is None or update.message is None:
        return

    # اگر کاربر از دکمه «ساخت اتاق بازی» داخل گروه
    # وارد ربات شده باشد، این پارامتر دریافت می‌شود.
    args = context.args or []

    if args and args[0].lower() == "create":
        await create_game_for_message(
            update,
            context,
            user.id,
            user.first_name
            or user.username
            or "بازیکن",
        )
        return

    text = (
        "🃏 سلام!\n\n"
        "به ربات حکم Green Dream خوش آمدی 🌿\n\n"
        "🎮 برای ورود به میز بازی روی دکمه زیر بزن."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
    )


async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle inline queries."""
    query = update.inline_query

    if query is None:
        return

    text = (
        "🃏 حکم Green Dream\n\n"
        "برای ساخت یک اتاق بازی روی دکمه زیر بزن."
    )

    # به جای callback_data از لینک مستقیم ربات استفاده می‌کنیم.
    # این روش در گروه هم کار می‌کند و کاربر را به چت خصوصی
    # ربات می‌برد تا اتاق برای خودش ساخته شود.
    create_link = (
        f"https://t.me/{BOT_USERNAME}?start=create"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ساخت اتاق بازی",
                    url=create_link,
                )
            ]
        ]
    )

    result = InlineQueryResultArticle(
        id="hokm-room",
        title="🎮 ساخت اتاق حکم",
        description="ساخت اتاق جدید حکم",
        input_message_content=InputTextMessageContent(
            text
        ),
        reply_markup=keyboard,
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=True,
    )


async def send_membership_request(query) -> None:
    """Show membership requirement."""
    await query.edit_message_text(
        "🔒 قبل از شروع بازی باید در کانال عضو باشی.\n\n"
        "بعد از عضویت روی «بررسی عضویت» بزن.",
        reply_markup=membership_keyboard(),
    )


async def create_game(
    query,
    user_id: int,
    user_name: str,
) -> None:
    """Create a new game."""
    game = game_state.create_game(
        creator_id=user_id,
        creator_name=user_name,
        max_players=1,
    )

    await query.edit_message_text(
        "🎮 اتاق بازی ساخته شد!\n\n"
        f"🆔 کد بازی: `{game.game_id}`\n\n"
        f"👥 بازیکنان:\n"
        f"{player_list_text(game)}\n\n"
        "تعداد بازیکنان را از تنظیمات انتخاب کن.",
        parse_mode="Markdown",
        reply_markup=game_keyboard(
            game.game_id,
            game.creator_id,
        ),
    )


async def show_room(
    query,
    game_id: str,
) -> None:
    """Show game room."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "این اتاق دیگر وجود ندارد.",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        "🎮 اتاق حکم\n\n"
        f"🆔 کد بازی: `{game.game_id}`\n\n"
        f"👥 بازیکنان "
        f"({len(game.players)}/{game.max_players}):\n"
        f"{player_list_text(game)}\n\n"
        "سازنده می‌تواند بازی را شروع کند.",
        parse_mode="Markdown",
        reply_markup=game_keyboard(
            game.game_id,
            game.creator_id,
        ),
    )


async def show_settings(
    query,
    game_id: str,
    user_id: int,
) -> None:
    """Show settings."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "اتاق پیدا نشد.",
            show_alert=True,
        )
        return

    if game.creator_id != user_id:
        await query.answer(
            "⚠️ فقط سازنده اتاق می‌تواند تنظیمات را تغییر دهد.",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        "⚙️ تنظیمات بازی\n\n"
        f"تعداد بازیکنان فعلی: {game.max_players}\n\n"
        "تعداد بازیکنان را انتخاب کن:",
        reply_markup=settings_keyboard(game_id),
    )


async def choose_players(
    query,
    game_id: str,
    user_id: int,
) -> None:
    """Choose player count."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "اتاق پیدا نشد.",
            show_alert=True,
        )
        return

    if game.creator_id != user_id:
        await query.answer(
            "⚠️ فقط سازنده می‌تواند این تنظیم را تغییر دهد.",
            show_alert=True,
        )
        return

    await query.edit_message_text(
        "👥 تعداد بازیکنان را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👤 ۱ نفر",
                        callback_data=f"setplayers:{game_id}:1",
                    ),
                    InlineKeyboardButton(
                        "👥 ۲ نفر",
                        callback_data=f"setplayers:{game_id}:2",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "👥 ۴ نفر",
                        callback_data=f"setplayers:{game_id}:4",
                    )
                ],
            ]
        ),
    )


async def set_players(
    query,
    game_id: str,
    user_id: int,
    count: int,
) -> None:
    """Set player count."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "اتاق پیدا نشد.",
            show_alert=True,
        )
        return

    if game.creator_id != user_id:
        await query.answer(
            "⚠️ فقط سازنده اتاق می‌تواند این کار را انجام دهد.",
            show_alert=True,
        )
        return

    if game.started:
        await query.answer(
            "بازی شروع شده و نمی‌توان تنظیمات را تغییر داد.",
            show_alert=True,
        )
        return

    if count not in (1, 2, 4):
        await query.answer(
            "تعداد بازیکن نامعتبر است.",
            show_alert=True,
        )
        return

    if len(game.players) > count:
        await query.answer(
            "تعداد بازیکنان فعلی بیشتر از این مقدار است.",
            show_alert=True,
        )
        return

    game.max_players = count

    await query.edit_message_text(
        "⚙️ تنظیمات ذخیره شد.\n\n"
        f"👥 تعداد بازیکنان: {count}\n\n"
        f"بازیکنان فعلی:\n"
        f"{player_list_text(game)}",
        reply_markup=game_keyboard(
            game_id,
            game.creator_id,
        ),
    )


async def join_game(
    query,
    game_id: str,
    user_id: int,
    user_name: str,
) -> None:
    """Join a game."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "این اتاق دیگر وجود ندارد.",
            show_alert=True,
        )
        return

    if game.started:
        await query.answer(
            "این بازی قبلاً شروع شده است.",
            show_alert=True,
        )
        return

    result = game_state.add_player(
        game_id=game_id,
        user_id=user_id,
        name=user_name,
    )

    messages = {
        "joined": "✅ با موفقیت وارد بازی شدی.",
        "already_joined": "تو قبلاً وارد این بازی شده‌ای.",
        "full": "❌ ظرفیت بازی تکمیل است.",
        "started": "❌ بازی شروع شده است.",
        "no_game": "❌ بازی پیدا نشد.",
    }

    await query.answer(
        messages.get(
            result,
            "خطایی رخ داد.",
        ),
        show_alert=True,
    )

    await show_room(
        query,
        game_id,
    )


async def start_game(
    query,
    game_id: str,
    user_id: int,
) -> None:
    """Start game."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "اتاق پیدا نشد.",
            show_alert=True,
        )
        return

    if game.creator_id != user_id:
        await query.answer(
            "⚠️ فقط سازنده اتاق می‌تواند بازی را شروع کند.",
            show_alert=True,
        )
        return

    result = game_state.start_game(game_id)

    if result == "wrong_count":
        await query.answer(
            f"برای شروع باید دقیقاً "
            f"{game.max_players} بازیکن داخل اتاق باشد.",
            show_alert=True,
        )
        return

    if result == "already_started":
        await query.answer(
            "بازی قبلاً شروع شده است.",
            show_alert=True,
        )
        return

    if result != "started":
        await query.answer(
            "شروع بازی ناموفق بود.",
            show_alert=True,
        )
        return

    game = game_state.get_game(game_id)

    if game is None:
        return

    if (
        game.hokm is None
        and game.hakim_id == user_id
    ):
        await query.edit_message_text(
            "🃏 بازی شروع شد!\n\n"
            "👑 تو حکیم هستی.\n"
            "خال حکم را انتخاب کن:",
            reply_markup=suit_keyboard(game_id),
        )
        return

    await query.edit_message_text(
        "🃏 بازی شروع شد!\n\n"
        "منتظر انتخاب خال حکم توسط حکیم بمان.",
    )


async def show_hand(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    game_id: str,
) -> None:
    """Show player's cards."""
    game = game_state.get_game(game_id)

    if game is None:
        return

    cards = game_state.get_hand(
        game_id,
        user_id,
    )

    if not cards:
        await context.bot.send_message(
            chat_id=user_id,
            text="🃏 کارتی در دستت نیست.",
        )
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "🃏 کارت‌های تو:\n\n"
            "برای بازی کردن یک کارت را انتخاب کن."
        ),
        reply_markup=card_keyboard(
            game_id,
            cards,
        ),
    )


async def select_card(
    query,
    game_id: str,
    user_id: int,
    card_index: int,
) -> None:
    """Play selected card."""
    game = game_state.get_game(game_id)

    if game is None:
        await query.answer(
            "بازی پیدا نشد.",
            show_alert=True,
        )
        return

    result = game_state.play_card(
        game_id,
        user_id,
        card_index,
    )

    if not result.get("ok"):
        reasons = {
            "not_your_turn": "⏳ نوبت تو نیست.",
            "hokm_not_selected": (
                "خال حکم هنوز انتخاب نشده است."
            ),
            "must_follow_suit": (
                "⚠️ اگر از خال شروع‌شده داری، "
                "باید همان خال را بازی کنی."
            ),
            "invalid_card": "این کارت معتبر نیست.",
            "finished": "این بازی تمام شده است.",
            "not_started": "بازی هنوز شروع نشده است.",
        }

        await query.answer(
            reasons.get(
                result.get("reason"),
                "بازی کردن کارت ناموفق بود.",
            ),
            show_alert=True,
        )
        return

    card = result["card"]

    await query.answer(
        f"🃏 کارت {card} بازی شد."
    )

    if result.get("trick_finished"):
        winner_id = result.get("winner_id")

        winner_name = "بازیکن"

        if winner_id in game.players:
            winner_name = game.players[
                winner_id
            ].name

        if game.finished:
            await query.edit_message_text(
                "🏁 بازی تمام شد!\n\n"
                f"🏆 برنده: {winner_name}",
            )
            return

        await query.edit_message_text(
            "🃏 دست تمام شد.\n\n"
            f"🏆 برنده این دست: {winner_name}\n\n"
            "نوبت نفر برنده است.",
        )
        return

    await query.edit_message_text(
        "🃏 کارت بازی شد.\n\n"
        f"کارت: {card}\n\n"
        "⏳ منتظر حرکت بازیکن بعدی باش.",
    )


async def select_hokm(
    query,
    game_id: str,
    user_id: int,
    suit: str,
) -> None:
    """Select Hokm suit."""
    result = game_state.set_hokm(
        game_id,
        user_id,
        suit,
    )

    messages = {
        "no_game": "بازی پیدا نشد.",
        "not_started": "بازی هنوز شروع نشده.",
        "finished": "بازی تمام شده.",
        "not_hakim": (
            "⚠️ فقط حکیم می‌تواند حکم را انتخاب کند."
        ),
        "already_selected": (
            "حکم قبلاً انتخاب شده."
        ),
        "invalid_suit": "خال نامعتبر است.",
        "selected": "حکم انتخاب شد.",
    }

    await query.answer(
        messages.get(
            result,
            "خطایی رخ داد.",
        ),
        show_alert=True,
    )

    if result != "selected":
        return

    game = game_state.get_game(game_id)

    if game is None:
        return

    await query.edit_message_text(
        "👑 حکم انتخاب شد!\n\n"
        f"🃏 خال حکم: {SUIT_NAMES[suit]}\n\n"
        "🎮 بازی ادامه دارد.",
    )


async def help_command(query) -> None:
    """Show help."""
    await query.edit_message_text(
        "📖 راهنمای حکم\n\n"
        "🃏 بازی حکم به صورت اتاقی انجام می‌شود.\n\n"
        "👤 بازی ۱ نفره برای تست\n"
        "👥 بازی ۲ نفره\n"
        "👥 بازی ۴ نفره\n\n"
        "🎮 نسخه اصلی بازی در Mini App اجرا خواهد شد.",
        reply_markup=main_menu_keyboard(),
    )


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle callback buttons."""
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    user = query.from_user
    data = query.data or ""

    if data == "help":
        await help_command(query)
        return

    if data == "create_game":
        member = await is_member(
            context,
            user.id,
        )

        if not member:
            await send_membership_request(query)
            return

        await create_game(
            query,
            user.id,
            user.first_name
            or user.username
            or "بازیکن",
        )
        return

    if data == "check_membership":
        member = await is_member(
            context,
            user.id,
        )

        if not member:
            await query.answer(
                "❌ هنوز عضویتت تأیید نشده است.",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            "✅ عضویت تأیید شد.\n\n"
            "حالا می‌توانی بازی بسازی.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data.startswith("setplayers:"):
        _, game_id, count_text = data.split(":")

        await set_players(
            query,
            game_id,
            user.id,
            int(count_text),
        )
        return

    if data.startswith("choose_players:"):
        _, game_id = data.split(
            ":",
            1,
        )

        await choose_players(
            query,
            game_id,
            user.id,
        )
        return

    if data.startswith("settings:"):
        _, game_id = data.split(
            ":",
            1,
        )

        await show_settings(
            query,
            game_id,
            user.id,
        )
        return

    if data.startswith("back_room:"):
        _, game_id = data.split(
            ":",
            1,
        )

        await show_room(
            query,
            game_id,
        )
        return

    if data.startswith("join:"):
        _, game_id = data.split(
            ":",
            1,
        )

        await join_game(
            query,
            game_id,
            user.id,
            user.first_name
            or user.username
            or "بازیکن",
        )
        return

    if data.startswith("start:"):
        _, game_id = data.split(
            ":",
            1,
        )

        await start_game(
            query,
            game_id,
            user.id,
        )
        return

    if data.startswith("card:"):
        _, game_id, index_text = data.split(":")

        await select_card(
            query,
            game_id,
            user.id,
            int(index_text),
        )
        return

    if data.startswith("hokm:"):
        _, game_id, suit = data.split(
            ":",
            2,
        )

        await select_hokm(
            query,
            game_id,
            user.id,
            suit,
        )
        return


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log unexpected errors."""
    LOGGER.exception(
        "Unhandled exception",
        exc_info=context.error,
    )


def build_application(
    settings: Settings,
) -> Application:
    """Build Telegram application."""
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
            callback_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    return application


def run() -> None:
    """Run Telegram bot."""
    logging.basicConfig(
        format=(
            "%(asctime)s - %(name)s - "
            "%(levelname)s - %(message)s"
        ),
        level=logging.INFO,
    )

    settings = Settings.from_environment()

    application = build_application(
        settings
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    run()
