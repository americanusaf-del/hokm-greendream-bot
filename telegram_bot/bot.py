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


# =========================================================
# CONFIG
# =========================================================

LOGGER = logging.getLogger(__name__)

BOT_USERNAME = "HokmgreendreamBot"

CHANNEL_USERNAME = "@greendreamze"
CHANNEL_LINK = "https://t.me/greendreamze"
SECOND_CHANNEL_LINK = "https://t.me/+CkjlXmCqFaM2M2Jk"

WEB_APP_URL = os.environ.get(
    "WEB_APP_URL",
    "https://hokm-greendream-bot.onrender.com",
).strip()


# =========================================================
# TEMPORARY INLINE DATA
# =========================================================

# User ID -> Game ID
PENDING_INLINE_GAMES: dict[int, str] = {}

# Game ID -> Telegram inline message ID
INLINE_GAME_MESSAGES: dict[str, str] = {}


# =========================================================
# BASIC HELPERS
# =========================================================

def get_user_name(user) -> str:
    """Return a readable Telegram name."""

    if user.username:
        return f"@{user.username}"

    full_name = " ".join(
        part
        for part in [
            user.first_name,
            user.last_name,
        ]
        if part
    ).strip()

    return full_name or str(user.id)


def make_deep_link(
    action: str,
    game_id: str,
) -> str:
    """Create a Telegram bot deep link."""

    return (
        f"https://t.me/{BOT_USERNAME}"
        f"?start={action}_{game_id}"
    )


async def is_member(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:
    """Check membership in the required channel."""

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

        # If Telegram temporarily blocks the check,
        # do not completely prevent the game.
        return True


# =========================================================
# MAIN MENU
# =========================================================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main private bot menu."""

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


# =========================================================
# PRIVATE GAME KEYBOARD
# =========================================================

def private_game_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """Keyboard used in private chat."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ورود به میز بازی",
                    web_app=WebAppInfo(
                        url=(
                            f"{WEB_APP_URL}"
                            f"/?game={game_id}"
                        ),
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
                    "🔄 بروزرسانی",
                    callback_data=f"refresh:{game_id}",
                )
            ],
        ]
    )


def settings_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """Game settings."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👤 ۱ نفره",
                    callback_data=f"players:{game_id}:1",
                ),
                InlineKeyboardButton(
                    "👥 ۲ نفره",
                    callback_data=f"players:{game_id}:2",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👥👥 ۴ نفره",
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
    """Hokm suit selection."""

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


# =========================================================
# GROUP ROOM KEYBOARD
# =========================================================

def group_room_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:
    """
    Keyboard shown directly inside the group.

    The buttons use Telegram deep links so users can
    join the same game safely.
    """

    join_url = make_deep_link(
        "join",
        game_id,
    )

    play_url = make_deep_link(
        "play",
        game_id,
    )

    settings_url = make_deep_link(
        "settings",
        game_id,
    )

    start_url = make_deep_link(
        "start",
        game_id,
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ورود به بازی",
                    url=join_url,
                )
            ],
            [
                InlineKeyboardButton(
                    "🎮 ورود به میز بازی",
                    url=play_url,
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات",
                    url=settings_url,
                ),
                InlineKeyboardButton(
                    "▶️ شروع بازی",
                    url=start_url,
                ),
            ],
        ]
    )


# =========================================================
# GAME ROOM TEXT
# =========================================================

def room_text(game) -> str:
    """Build room message."""

    players = list(game.players.values())

    if players:
        player_lines = "\n".join(
            f"• {player.name}"
            for player in players
        )
    else:
        player_lines = "• هنوز بازیکنی وارد نشده است"

    if game.started:
        status = "🟢 بازی شروع شده"
    else:
        status = "🟡 منتظر بازیکنان"

    hokm = getattr(
        game,
        "hokm",
        None,
    )

    hokm_text = hokm if hokm else "انتخاب نشده"

    return (
        "🎴 *اتاق حکم Green Dream*\n\n"
        f"🆔 کد اتاق: `{game.game_id}`\n"
        f"👥 ظرفیت: {game.max_players} نفر\n"
        f"📊 وضعیت: {status}\n"
        f"👑 حکم: {hokm_text}\n\n"
        "👤 *بازیکنان:*\n"
        f"{player_lines}\n\n"
        "برای ورود به این بازی روی "
        "«➕ ورود به بازی» بزنید."
    )


# =========================================================
# UPDATE GROUP ROOM
# =========================================================

async def update_group_room(
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
) -> None:
    """Update the room message inside the group."""

    inline_message_id = INLINE_GAME_MESSAGES.get(
        game_id
    )

    if not inline_message_id:
        return

    game = game_state.get_game(
        game_id
    )

    if game is None:
        return

    try:
        await context.bot.edit_message_text(
            inline_message_id=inline_message_id,
            text=room_text(game),
            parse_mode="Markdown",
            reply_markup=group_room_keyboard(
                game_id
            ),
        )

    except Exception:
        LOGGER.exception(
            "Failed to update group room %s",
            game_id,
        )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and deep links."""

    if not update.effective_user:
        return

    user = update.effective_user
    message = update.effective_message
    args = context.args or []

    # -----------------------------------------------------
    # Normal /start
    # -----------------------------------------------------

    if not args:
        await message.reply_text(
            "🎴 سلام!\n\n"
            "به Green Dream Hokm خوش آمدی.\n\n"
            "برای شروع بازی یکی از گزینه‌های زیر را انتخاب کن.",
            reply_markup=main_menu_keyboard(),
        )
        return

    parameter = args[0].strip()

    # -----------------------------------------------------
    # Legacy create
    # -----------------------------------------------------

    if parameter == "create":
        game = game_state.create_game(
            creator_id=user.id,
            creator_name=get_user_name(user),
            max_players=4,
        )

        await message.reply_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game.game_id
            ),
        )
        return

    # -----------------------------------------------------
    # Deep link format
    # -----------------------------------------------------

    if "_" not in parameter:
        await message.reply_text(
            "❌ لینک بازی معتبر نیست."
        )
        return

    action, game_id = parameter.split(
        "_",
        1,
    )

    game = game_state.get_game(
        game_id
    )

    if game is None:
        await message.reply_text(
            "❌ این اتاق بازی دیگر وجود ندارد."
        )
        return

    # =====================================================
    # JOIN
    # =====================================================

    if action == "join":

        if not await is_member(
            context,
            user.id,
        ):
            await message.reply_text(
                "⛔ برای ورود به بازی ابتدا باید عضو کانال شوی:\n\n"
                f"{CHANNEL_LINK}\n\n"
                "بعد دوباره روی ورود به بازی بزن."
            )
            return

        if game.started:
            await message.reply_text(
                "⛔ این بازی قبلاً شروع شده است."
            )
            return

        if user.id not in game.players:
            try:
                game_state.add_player(
                    game_id,
                    user.id,
                    get_user_name(user),
                )
            except Exception as exc:
                await message.reply_text(
                    f"❌ ورود به بازی انجام نشد:\n{exc}"
                )
                return

        await update_group_room(
            context,
            game_id,
        )

        await message.reply_text(
            "✅ با موفقیت وارد بازی شدی!\n\n"
            f"🎴 کد اتاق: {game_id}\n"
            f"👥 بازیکنان: "
            f"{len(game.players)}/{game.max_players}",
            reply_markup=private_game_keyboard(
                game_id
            ),
        )

        return

    # =====================================================
    # PLAY
    # =====================================================

    if action == "play":

        if user.id not in game.players:
            await message.reply_text(
                "⛔ ابتدا باید وارد بازی شوی.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ ورود به بازی",
                                url=make_deep_link(
                                    "join",
                                    game_id,
                                ),
                            )
                        ]
                    ]
                ),
            )
            return

        await message.reply_text(
            "🎮 میز بازی آماده است.\n\n"
            "روی دکمه زیر بزن:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎮 ورود به میز بازی",
                            web_app=WebAppInfo(
                                url=(
                                    f"{WEB_APP_URL}"
                                    f"/?game={game_id}"
                                ),
                            ),
                        )
                    ]
                ]
            ),
        )

        return

    # =====================================================
    # SETTINGS
    # =====================================================

    if action == "settings":

        if user.id != game.creator_id:
            await message.reply_text(
                "⛔ فقط سازنده اتاق می‌تواند تنظیمات را تغییر دهد."
            )
            return

        await message.reply_text(
            "⚙️ تنظیمات بازی\n\n"
            "تعداد بازیکنان را انتخاب کن:",
            reply_markup=settings_keyboard(
                game_id
            ),
        )

        return

    # =====================================================
    # START GAME
    # =====================================================

    if action == "start":

        if user.id != game.creator_id:
            await message.reply_text(
                "⛔ فقط سازنده اتاق می‌تواند بازی را شروع کند."
            )
            return

        if game.started:
            await message.reply_text(
                "🟢 بازی قبلاً شروع شده است.",
                reply_markup=private_game_keyboard(
                    game_id
                ),
            )
            return

        if len(game.players) < game.max_players:
            await message.reply_text(
                "⏳ هنوز بازیکنان کامل نشده‌اند.\n\n"
                f"👥 بازیکنان: "
                f"{len(game.players)}/{game.max_players}"
            )
            return

        try:
            game_state.start_game(
                game_id
            )
        except Exception as exc:
            await message.reply_text(
                f"❌ شروع بازی انجام نشد:\n{exc}"
            )
            return

        await update_group_room(
            context,
            game_id,
        )

        if game.hakim_id == user.id:
            await message.reply_text(
                "👑 تو حاکم شدی!\n\n"
                "خال حکم را انتخاب کن:",
                reply_markup=suit_keyboard(
                    game_id
                ),
            )
        else:
            await message.reply_text(
                "🟢 بازی شروع شد.",
                reply_markup=private_game_keyboard(
                    game_id
                ),
            )

        return

    await message.reply_text(
        "❌ عملیات ناشناخته است."
    )


# =========================================================
# INLINE QUERY
# =========================================================

async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Create an inline game room.

    The room is posted directly into the group
    when the user selects the result.
    """

    query = update.inline_query

    if query is None:
        return

    user = query.from_user

    game = None

    # Reuse an existing pending room for this creator.
    existing_game_id = PENDING_INLINE_GAMES.get(
        user.id
    )

    if existing_game_id:
        existing_game = game_state.get_game(
            existing_game_id
        )

        if (
            existing_game is not None
            and not existing_game.started
            and existing_game.creator_id == user.id
        ):
            game = existing_game

    # Create a new room if necessary.
    if game is None:
        try:
            game = game_state.create_game(
                creator_id=user.id,
                creator_name=get_user_name(user),
                max_players=4,
            )

            PENDING_INLINE_GAMES[user.id] = (
                game.game_id
            )

        except Exception:
            LOGGER.exception(
                "Could not create inline game."
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
        description="ساخت اتاق مستقیماً داخل همین گروه",
        input_message_content=InputTextMessageContent(
            room_text(game),
            parse_mode="Markdown",
        ),
        reply_markup=group_room_keyboard(
            game.game_id
        ),
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=True,
    )


# =========================================================
# CHOSEN INLINE RESULT
# =========================================================

async def chosen_inline_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Remember the inline message ID after
    the room is posted in the group.
    """

    chosen = update.chosen_inline_result

    if chosen is None:
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
            "Saved inline message for game %s",
            game_id,
        )


# =========================================================
# CALLBACK QUERY
# =========================================================

async def callback_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle private bot buttons."""

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    user = query.from_user
    data = query.data or ""

    # =====================================================
    # HELP
    # =====================================================

    if data == "help":
        await query.edit_message_text(
            "❓ *راهنمای Green Dream Hokm*\n\n"
            "1️⃣ اتاق بازی را بساز.\n"
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

    # =====================================================
    # HOME
    # =====================================================

    if data == "home":
        await query.edit_message_text(
            "🎴 Green Dream Hokm\n\n"
            "یک گزینه انتخاب کن:",
            reply_markup=main_menu_keyboard(),
        )
        return

    # =====================================================
    # CREATE GAME
    # =====================================================

    if data == "create_game":

        if not await is_member(
            context,
            user.id,
        ):
            await query.edit_message_text(
                "⛔ ابتدا باید عضو کانال شوی:",
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
                        ],
                    ]
                ),
            )
            return

        game = game_state.create_game(
            creator_id=user.id,
            creator_name=get_user_name(user),
            max_players=4,
        )

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game.game_id
            ),
        )

        return

    # =====================================================
    # GAME CALLBACKS
    # =====================================================

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

    # =====================================================
    # REFRESH
    # =====================================================

    if action == "refresh":
        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id
            ),
        )
        return

    # =====================================================
    # SETTINGS
    # =====================================================

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
                game_id
            ),
        )

        return

    # =====================================================
    # PLAYER COUNT
    # =====================================================

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
                "⛔ بازی شروع شده است.",
                show_alert=True,
            )
            return

        game.max_players = count

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id
            ),
        )

        await update_group_room(
            context,
            game_id,
        )

        return

    # =====================================================
    # BACK
    # =====================================================

    if action == "back":

        await query.edit_message_text(
            room_text(game),
            parse_mode="Markdown",
            reply_markup=private_game_keyboard(
                game_id
            ),
        )

        return

    # =====================================================
    # START
    # =====================================================

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
                (
                    f"بازیکنان کامل نیستند: "
                    f"{len(game.players)}/{game.max_players}"
                ),
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
                    game_id
                ),
            )
        else:
            await query.edit_message_text(
                "🟢 بازی شروع شد.",
                reply_markup=private_game_keyboard(
                    game_id
                ),
            )

        return

    # =====================================================
    # HOKM
    # =====================================================

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
                                url=(
                                    f"{WEB_APP_URL}"
                                    f"/?game={game_id}"
                                ),
                            ),
                        )
                    ]
                ]
            ),
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log unexpected errors."""

    LOGGER.error(
        "Unhandled exception: %s",
        context.error,
        exc_info=context.error,
    )


# =========================================================
# RUN
# =========================================================

def run() -> None:
    """Start the Telegram bot."""

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

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Inline mode
    application.add_handler(
        InlineQueryHandler(
            inline_query,
        )
    )

    # Detect when an inline room is actually
    # posted into a group.
    application.add_handler(
        ChosenInlineResultHandler(
            chosen_inline_result,
        )
    )

    # Private buttons
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
