"""Telegram bot handlers for Green Dream Hokm."""

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
    ChosenInlineResultHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from .config import Settings
from .game import game_state

LOGGER = logging.getLogger(__name__)

BOT_USERNAME = "HokmgreendreamBot"

CHANNEL_USERNAME = "@greendreamze"
CHANNEL_LINK = "https://t.me/greendreamze"
SECOND_CHANNEL_LINK = "https://t.me/+CkjlXmCqFaM2M2Jk"

WEB_APP_URL = os.environ.get(
    "WEB_APP_URL",
    "https://hokm-greendream-bot.onrender.com",
).strip()


# ---------------------------------------------------------
# Temporary inline-room storage
# ---------------------------------------------------------

# user_id -> game_id
PENDING_INLINE_GAMES: dict[int, str] = {}

# game_id -> inline_message_id
INLINE_GAME_MESSAGES: dict[str, str] = {}


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------


def user_name(user) -> str:
    """Return a readable Telegram user name."""
    if user.username:
        return f"@{user.username}"

    full_name = " ".join(
        part
        for part in [user.first_name, user.last_name]
        if part
    ).strip()

    return full_name or str(user.id)


def game_link(action: str, game_id: str) -> str:
    """Build a Telegram deep link."""
    return f"https://t.me/{BOT_USERNAME}?start={action}_{game_id}"


async def is_member(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:
    """Check required channel membership."""

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

        # Do not completely block the game if Telegram
        # temporarily refuses the membership lookup.
        return True


# ---------------------------------------------------------
# Main menu
# ---------------------------------------------------------


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main private-chat keyboard."""

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
                    "❓ راهنما",
                    callback_data="help",
                )
            ],
        ]
    )


# ---------------------------------------------------------
# Private game keyboard
# ---------------------------------------------------------


def private_game_keyboard(
    game_id: str,
    creator_id: int,
) -> InlineKeyboardMarkup:
    """Keyboard used inside private bot chat."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ورود به میز بازی",
                    web_app=WebAppInfo(
                        url=f"{WEB_APP_URL}/?game={game_id}",
                    ),
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
            [
                InlineKeyboardButton(
                    "🔄 بروزرسانی اتاق",
                    callback_data=f"refresh:{game_id}",
                )
            ],
        ]
    )


def settings_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """Game settings keyboard."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👤 بازی ۱ نفره",
                    callback_data=f"players:{game_id}:1",
                ),
                InlineKeyboardButton(
                    "👥 بازی ۲ نفره",
                    callback_data=f"players:{game_id}:2",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👥👥 بازی ۴ نفره",
                    callback_data=f"players:{game_id}:4",
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ بازگشت",
                    callback_data=f"back:{game_id}",
                )
            ],
        ]
    )


def suit_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """Hokm suit selection keyboard."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "♥️ دل",
                    callback_data=f"hokm:{game_id}:♥",
                ),
                InlineKeyboardButton(
                    "♦️ خشت",
                    callback_data=f"hokm:{game_id}:♦",
                ),
            ],
            [
                InlineKeyboardButton(
                    "♣️ گشنیز",
                    callback_data=f"hokm:{game_id}:♣",
                ),
                InlineKeyboardButton(
                    "♠️ پیک",
                    callback_data=f"hokm:{game_id}:♠",
                ),
            ],
        ]
    )


# ---------------------------------------------------------
# Group inline-room keyboard
# ---------------------------------------------------------


def group_room_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """
    Keyboard displayed directly inside the group.

    Joining happens through a Telegram deep-link to the bot.
    The actual room remains visible in the group.
    """

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ورود به بازی",
                    url=game_link(
                        "join",
                        game_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🎮 ورود به میز بازی",
                    url=game_link(
                        "play",
                        game_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات",
                    url=game_link(
                        "settings",
                        game_id,
                    ),
                    ),
                InlineKeyboardButton(
                    "▶️ شروع بازی",
                    url=game_link(
                        "start",
                        game_id,
                    ),
                ),
            ],
        ]
    )


# ---------------------------------------------------------
# Game text
# ---------------------------------------------------------


def room_text(game) -> str:
    """Create the group/private room text."""

    players = list(game.players.values())

    if players:
        player_lines = "\n".join(
            f"• {player.name}"
            for player in players
        )
    else:
        player_lines = "• هنوز بازیکنی وارد نشده است"

    status = (
        "🟢 بازی شروع شده"
        if game.started
        else "🟡 منتظر بازیکنان"
    )

    hokm_text = (
        game.hokm
        if getattr(game, "hokm", None)
        else "هنوز انتخاب نشده"
    )

    return (
        "🎴 *اتاق بازی حکم Green Dream*\n\n"
        f"🆔 اتاق: `{game.game_id}`\n"
        f"👥 ظرفیت: {game.max_players} نفر\n"
        f"📊 وضعیت: {status}\n"
        f"👑 حکم: {hokm_text}\n\n"
        "👤 *بازیکنان:*\n"
        f"{player_lines}\n\n"
        "برای ورود به بازی روی دکمه «➕ ورود به بازی» بزنید."
    )


# ---------------------------------------------------------
# Update inline room message
# ---------------------------------------------------------


async def update_group_room(
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
) -> None:
    """Update the inline room message in the group."""

    inline_message_id = INLINE_GAME_MESSAGES.get(game_id)

    if not inline_message_id:
        return

    try:
        game = game_state.get_game(game_id)

        if game is None:
            return

        await context.bot.edit_message_text(
            inline_message_id=inline_message_id,
            text=room_text(game),
            parse_mode="Markdown",
            reply_markup=group_room_keyboard(
                game_id,
            ),
        )

    except Exception:
        LOGGER.exception(
            "Could not update inline room %s",
            game_id,
        )


# ---------------------------------------------------------
# /start
# ---------------------------------------------------------


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and Telegram deep links."""

    if not update.effective_user:
        return

    user = update.effective_user
    args = context.args or []

    # -----------------------------------------------------
    # Normal /start
    # -----------------------------------------------------

    if not args:
        await update.effective_message.reply_text(
            "🎴 سلام!\n\n"
            "به Green Dream Hokm خوش آمدی.\n"
            "برای شروع یک بازی بساز یا وارد میز بازی شو.",
            reply_markup=main_menu_keyboard(),
        )
        return

    parameter = args[0].strip()

    # -----------------------------------------------------
    # Legacy create
    # -----------------------------------------------------

    if parameter == "create":
        if not await is_member(
            context,
            user.id,
        ):
            await update.effective_message.reply_text(
                "⛔ برای بازی ابتدا باید عضو کانال ما شوی:\n\n"
                f"{CHANNEL_LINK}\n\n"
                "بعد دوباره تلاش کن."
            )
            return

        game = game_state.create_game(
            creator_id=user.id,
            creator_name=user_name(user),
            max_players=4,
        )

        await update.effective_message.reply_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game.game_id,
                user.id,
            ),
        )
        return

    # -----------------------------------------------------
    # Deep-link parser
    # -----------------------------------------------------

    if "_" not in parameter:
        await update.effective_message.reply_text(
            "❌ لینک بازی معتبر نیست.",
            reply_markup=main_menu_keyboard(),
        )
        return

    action, game_id = parameter.split(
        "_",
        1,
    )

    game = game_state.get_game(game_id)

    if game is None:
        await update.effective_message.reply_text(
            "❌ این اتاق بازی دیگر وجود ندارد."
        )
        return

    # -----------------------------------------------------
    # JOIN
    # -----------------------------------------------------

    if action == "join":

        if not await is_member(
            context,
            user.id,
        ):
            await update.effective_message.reply_text(
                "⛔ برای ورود به بازی باید عضو کانال باشی:\n\n"
                f"{CHANNEL_LINK}\n\n"
                "بعد از عضویت دوباره روی «ورود به بازی» بزن."
            )
            return

        if game.started:
            await update.effective_message.reply_text(
                "⛔ این بازی قبلاً شروع شده است."
            )
            return

        if user.id not in game.players:
            try:
                game_state.add_player(
                    game_id,
                    user.id,
                    user_name(user),
                )
            except Exception as exc:
                await update.effective_message.reply_text(
                    f"❌ ورود به بازی انجام نشد:\n{exc}"
                )
                return

        await update_group_room(
            context,
            game_id,
        )

        await update.effective_message.reply_text(
            "✅ با موفقیت وارد اتاق شدی!\n\n"
            f"🎴 اتاق: {game_id}\n"
            f"👥 بازیکنان: {len(game.players)}/{game.max_players}",
            reply_markup=private_game_keyboard(
                game_id,
                game.creator_id,
            ),
        )
        return

    # -----------------------------------------------------
    # PLAY / MINI APP
    # -----------------------------------------------------

    if action == "play":

        if user.id not in game.players:
            await update.effective_message.reply_text(
                "⛔ ابتدا باید وارد بازی شوی.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ ورود به بازی",
                                url=game_link(
                                    "join",
                                    game_id,
                                ),
                            )
                        ]
                    ]
                ),
            )
            return

        await update.effective_message.reply_text(
            "🎮 میز بازی آماده است.\n\n"
            "روی دکمه زیر بزن تا وارد میز حکم شوی.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎮 ورود به میز بازی",
                            web_app=WebAppInfo(
                                url=f"{WEB_APP_URL}/?game={game_id}",
                            ),
                        )
                    ]
                ]
            ),
        )
        return

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    if action == "settings":

        if user.id != game.creator_id:
            await update.effective_message.reply_text(
                "⛔ فقط سازنده اتاق می‌تواند تنظیمات را تغییر دهد."
            )
            return

        await update.effective_message.reply_text(
            "⚙️ تنظیمات بازی\n\n"
            "تعداد بازیکنان را انتخاب کن:",
            reply_markup=settings_keyboard(
                game_id,
            ),
        )
        return

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if action == "start":

        if user.id != game.creator_id:
            await update.effective_message.reply_text(
                "⛔ فقط سازنده اتاق می‌تواند بازی را شروع کند."
            )
            return

        if game.started:
            await update.effective_message.reply_text(
                "🟢 بازی قبلاً شروع شده است.",
                reply_markup=private_game_keyboard(
                    game_id,
                    game.creator_id,
                ),
            )
            return

        if len(game.players) < game.max_players:
            await update.effective_message.reply_text(
                "⏳ هنوز بازیکنان کامل نشده‌اند.\n\n"
                f"👥 بازیکنان فعلی: "
                f"{len(game.players)}/{game.max_players}\n\n"
                "لینک اتاق را در گروه نگه دارید تا بازیکنان وارد شوند."
            )
            return

        try:
            game_state.start_game(
                game_id,
            )
        except Exception as exc:
            await update.effective_message.reply_text(
                f"❌ شروع بازی انجام نشد:\n{exc}"
            )
            return

        await update_group_room(
            context,
            game_id,
        )

        # If the creator is hakim, ask for hokm.
        if game.hakim_id == user.id:
            await update.effective_message.reply_text(
                "👑 تو حاکم شدی!\n\n"
                "خال حکم را انتخاب کن:",
                reply_markup=suit_keyboard(
                    game_id,
                ),
            )
        else:
            await update.effective_message.reply_text(
                "🟢 بازی شروع شد.",
                reply_markup=private_game_keyboard(
                    game_id,
                    game.creator_id,
                ),
            )

        return

    # -----------------------------------------------------
    # Unknown action
    # -----------------------------------------------------

    await update.effective_message.reply_text(
        "❌ عملیات ناشناخته است."
    )


# ---------------------------------------------------------
# Inline query
# ---------------------------------------------------------


async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Create a game room when the creator selects
    the inline result.

    The room message itself is posted directly
    into the current group.
    """

    query = update.inline_query

    if not query:
        return

    user = query.from_user

    existing_game_id = PENDING_INLINE_GAMES.get(
        user.id
    )

    game = None

    if existing_game_id:
        game = game_state.get_game(
            existing_game_id
        )

        if game and not game.started:
            if game.creator_id != user.id:
                game = None

    if game is None:
        try:
            game = game_state.create_game(
                creator_id=user.id,
                creator_name=user_name(user),
                max_players=4,
            )

            PENDING_INLINE_GAMES[user.id] = (
                game.game_id
            )

        except Exception:
            LOGGER.exception(
                "Could not create inline game"
            )

            await query.answer(
                results=[],
                cache_time=0,
                is_personal=True,
            )
            return

    result = InlineQueryResultArticle(
        id=f"hokm-room-{game.game_id}",
        title="🎮 ساخت اتاق بازی حکم",
        description=(
            "اتاق را مستقیماً داخل همین گروه ایجاد کن"
        ),
        input_message_content=InputTextMessageContent(
            room_text(game),
            parse_mode="Markdown",
        ),
        reply_markup=group_room_keyboard(
            game.game_id,
        ),
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=True,
    )


# ---------------------------------------------------------
# Chosen inline result
# ---------------------------------------------------------


async def chosen_inline_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Save the inline_message_id after the room
    has actually been posted in the group.
    """

    chosen = update.chosen_inline_result

    if not chosen:
        return

    result_id = chosen.result_id

    prefix = "hokm-room-"

    if not result_id.startswith(prefix):
        return

    game_id = result_id[len(prefix):]

    if chosen.inline_message_id:
        INLINE_GAME_MESSAGES[game_id] = (
            chosen.inline_message_id
        )

        LOGGER.info(
            "Inline room %s posted as %s",
            game_id,
            chosen.inline_message_id,
        )


# ---------------------------------------------------------
# Callback queries
# ---------------------------------------------------------


async def callback_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle private-chat callback buttons."""

    query = update.callback_query

    if not query:
        return

    await query.answer()

    user = query.from_user
    data = query.data or ""

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if data == "help":
        await query.edit_message_text(
            "❓ *راهنمای Green Dream Hokm*\n\n"
            "1️⃣ بازی را بساز.\n"
            "2️⃣ بازیکنان وارد اتاق شوند.\n"
            "3️⃣ سازنده بازی را شروع کند.\n"
            "4️⃣ حاکم خال حکم را انتخاب کند.\n"
            "5️⃣ همه وارد میز بازی شوند.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↩️ بازگشت",
                            callback_data="home",
                        )
                    ]
                ]
            ),
        )
        return

    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    if data == "home":
        await query.edit_message_text(
            "🎴 Green Dream Hokm\n\n"
            "یک گزینه انتخاب کن:",
            reply_markup=main_menu_keyboard(),
        )
        return

    # -----------------------------------------------------
    # CREATE GAME
    # -----------------------------------------------------

    if data == "create_game":

        if not await is_member(
            context,
            user.id,
        ):
            await query.edit_message_text(
                "⛔ ابتدا باید عضو کانال شوی:\n\n"
                f"{CHANNEL_LINK}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📢 عضویت در کانال",
                                url=CHANNEL_LINK,
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📢 کانال دوم",
                                url=SECOND_CHANNEL_LINK,
                            )
                        ]
                    ]
                ),
            )
            return

        game = game_state.create_game(
            creator_id=user.id,
            creator_name=user_name(user),
            max_players=4,
        )

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game.game_id,
                user.id,
            ),
        )
        return

    # -----------------------------------------------------
    # Everything below uses game_id
    # -----------------------------------------------------

    parts = data.split(":")

    if len(parts) < 2:
        return

    action = parts[0]
    game_id = parts[1]

    game = game_state.get_game(
        game_id
    )

    if game is None:
        await query.edit_message_text(
            "❌ اتاق بازی پیدا نشد."
        )
        return

    # -----------------------------------------------------
    # REFRESH
    # -----------------------------------------------------

    if action == "refresh":

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id,
                game.creator_id,
            ),
        )
        return

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    if action == "settings":

        if user.id != game.creator_id:
            await query.answer(
                "⛔ فقط سازنده اتاق دسترسی دارد.",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            "⚙️ تنظیمات بازی\n\n"
            "تعداد بازیکنان را انتخاب کن:",
            reply_markup=settings_keyboard(
                game_id,
            ),
        )
        return

    # -----------------------------------------------------
    # PLAYER COUNT
    # -----------------------------------------------------

    if action == "players":

        if user.id != game.creator_id:
            await query.answer(
                "⛔ فقط سازنده اتاق می‌تواند تنظیمات را تغییر دهد.",
                show_alert=True,
            )
            return

        if len(parts) != 3:
            return

        try:
            count = int(parts[2])
        except ValueError:
            return

        if count not in {1, 2, 4}:
            return

        if game.started:
            await query.answer(
                "⛔ بازی شروع شده و تنظیمات قفل است.",
                show_alert=True,
            )
            return

        game.max_players = count

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id,
                game.creator_id,
            ),
        )

        await update_group_room(
            context,
            game_id,
        )

        return

    # -----------------------------------------------------
    # BACK
    # -----------------------------------------------------

    if action == "back":

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id,
                game.creator_id,
            ),
        )
        return

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if action == "start":

        if user.id != game.creator_id:
            await query.answer(
                "⛔ فقط سازنده اتاق می‌تواند بازی را شروع کند.",
                show_alert=True,
            )
            return

        if game.started:
            await query.answer(
                "بازی قبلاً شروع شده است.",
                show_alert=True,
            )
            return

        if len(game.players) < game.max_players:
            await query.answer(
                f"هنوز بازیکنان کامل نیستند: "
                f"{len(game.players)}/{game.max_players}",
                show_alert=True,
            )
            return

        try:
            game_state.start_game(
                game_id
            )
        except Exception as exc:
            await query.answer(
                str(exc),
                show_alert=True,
            )
            return

        await update_group_room(
            context,
            game_id,
        )

        if game.hakim_id == user.id:
            await query.edit_message_text(
                "👑 تو حاکم شدی!\n\n"
                "خال حکم را انتخاب کن:",
                reply_markup=suit_keyboard(
                    game_id,
                ),
            )
        else:
            await query.edit_message_text(
                "🟢 بازی شروع شد.",
                reply_markup=private_game_keyboard(
                    game_id,
                    game.creator_id,
                ),
            )

        return

    # -----------------------------------------------------
    # HOKM
    # -----------------------------------------------------

    if action == "hokm":

        if len(parts) != 3:
            return

        suit = parts[2]

        if user.id != game.hakim_id:
            await query.answer(
                "⛔ فقط حاکم می‌تواند حکم را انتخاب کند.",
                show_alert=True,
            )
            return

        try:
            game_state.set_hokm(
                game_id,
                suit,
            )
        except Exception as exc:
            await query.answer(
                str(exc),
                show_alert=True,
            )
            return

        await update_group_room(
            context,
            game_id,
        )

        await query.edit_message_text(
            f"✅ حکم انتخاب شد: {suit}\n\n"
            "🎮 حالا وارد میز بازی شو.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎮 ورود به میز بازی",
                            web_app=WebAppInfo(
                                url=f"{WEB_APP_URL}/?game={game_id}",
                            ),
                        ]
                    ]
                ]
            ),
        )
        return


# ---------------------------------------------------------
# Error handler
# ---------------------------------------------------------


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log unexpected errors."""

    LOGGER.exception(
        "Unhandled bot error",
        exc_info=context.error,
    )


# ---------------------------------------------------------
# Run bot
# ---------------------------------------------------------


def run() -> None:
    """Start Telegram polling."""

    settings = Settings.from_environment()

    logging.basicConfig(
        format=(
            "%(asctime)s - "
            "%(name)s - "
            "%(levelname)s - "
            "%(message)s"
        ),
        level=logging.INFO,
    )

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
        ChosenInlineResultHandler(
            chosen_inline_result,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_query,
        )
    )

    application.add_error_handler(
        error_handler
    )

    LOGGER.info(
        "Green Dream Hokm bot started."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )
