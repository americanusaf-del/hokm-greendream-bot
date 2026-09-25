from __future__ import annotations

import os
import uuid
from typing import Optional

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

from .config import Settings
from .game import game_state


BOT_USERNAME = os.environ.get(
    "BOT_USERNAME",
    "HokmgreendreamBot",
)

WEB_APP_URL = os.environ.get(
    "WEB_APP_URL",
    "https://hokm-greendream-bot.onrender.com",
).rstrip("/")


# ---------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------

def user_name(user) -> str:
    if user.full_name:
        return user.full_name

    if user.username:
        return f"@{user.username}"

    return f"بازیکن {user.id}"


def create_game_id() -> str:
    return uuid.uuid4().hex[:8]


def mini_app_url(game_id: str) -> str:
    return f"{WEB_APP_URL}/?game={game_id}"


def bot_link(command: str, game_id: str) -> str:
    return (
        f"https://t.me/{BOT_USERNAME}"
        f"?start={command}_{game_id}"
    )


# ---------------------------------------------------------
# منوی اصلی
# ---------------------------------------------------------

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ساخت بازی",
                    callback_data="create_game",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❓ راهنما",
                    callback_data="help",
                ),
            ],
        ]
    )


# ---------------------------------------------------------
# صفحه بازی خصوصی
# ---------------------------------------------------------

def private_game_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ورود به بازی",
                    web_app=WebAppInfo(
                        url=mini_app_url(game_id)
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 بروزرسانی",
                    callback_data=f"refresh_{game_id}",
                ),
            ],
        ]
    )


# ---------------------------------------------------------
# متن اتاق
# ---------------------------------------------------------

def room_text(game_id: str) -> str:

    try:
        game = game_state.get_game(game_id)
    except Exception:
        return (
            "🎴 <b>بازی حکم</b>\n\n"
            "❌ این اتاق دیگر وجود ندارد."
        )

    players = list(game.players.values())

    lines = [
        "🎴 <b>بازی حکم گرین‌دریم</b>",
        "",
        f"🆔 کد اتاق: <code>{game_id}</code>",
        "",
        "👥 بازیکنان:",
    ]

    if not players:
        lines.append("هنوز کسی وارد نشده.")
    else:
        for index, player in enumerate(players, start=1):
            name = player.name
            lines.append(f"{index}. {name}")

    lines.extend(
        [
            "",
            f"👤 ظرفیت: {game.max_players} نفر",
            "",
        ]
    )

    if len(players) < game.max_players:
        lines.append(
            "🟢 برای ورود به بازی روی دکمه "
            "«پیوستن به بازی» بزنید."
        )
    else:
        lines.append(
            "🟢 ظرفیت اتاق تکمیل شده است."
        )

    return "\n".join(lines)


# ---------------------------------------------------------
# کیبورد اتاق
# ---------------------------------------------------------

def room_keyboard(
    game_id: str,
    creator_id: Optional[int] = None,
) -> InlineKeyboardMarkup:

    buttons = [
        [
            InlineKeyboardButton(
                "🎮 پیوستن به بازی",
                url=bot_link("join", game_id),
            ),
        ],
    ]

    buttons.append(
        [
            InlineKeyboardButton(
                "▶️ ورود به میز بازی",
                url=bot_link("play", game_id),
            ),
        ]
    )

    if creator_id is not None:
        buttons.append(
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات",
                    url=bot_link("settings", game_id),
                ),
            ]
        )

    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------
# /start
# ---------------------------------------------------------

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if update.effective_user is None:
        return

    user = update.effective_user
    args = context.args

    # ---------------------------------------------
    # لینک ورود به بازی
    # ---------------------------------------------

    if args:
        payload = args[0]

        if "_" in payload:
            action, game_id = payload.split(
                "_",
                1,
            )

            if action == "join":
                await join_game(
                    update,
                    context,
                    game_id,
                )
                return

            if action == "play":
                await play_game(
                    update,
                    context,
                    game_id,
                )
                return

            if action == "settings":
                await settings_game(
                    update,
                    context,
                    game_id,
                )
                return

    await update.message.reply_text(
        "🎴 <b>حکم گرین‌دریم</b>\n\n"
        "به بازی حکم خوش آمدید.\n\n"
        "برای شروع یک بازی جدید بسازید.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ---------------------------------------------------------
# ساخت بازی
# ---------------------------------------------------------

async def create_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query

    if query is not None:
        await query.answer()

    if update.effective_user is None:
        return

    user = update.effective_user

    game_id = create_game_id()

    game = game_state.create_game(
        game_id=game_id,
        creator_id=user.id,
        creator_name=user_name(user),
        max_players=4,
    )

    text = (
        "🎴 <b>اتاق جدید حکم ساخته شد!</b>\n\n"
        f"👑 سازنده: {user_name(user)}\n"
        f"🆔 کد اتاق: <code>{game_id}</code>\n\n"
        "👥 ظرفیت: ۴ نفر\n\n"
        "برای چندنفره شدن بازی، لینک "
        "«پیوستن به بازی» را برای دوستانتان بفرستید."
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=room_keyboard(
            game_id,
            user.id,
        ),
    )


# ---------------------------------------------------------
# پیوستن
# ---------------------------------------------------------

async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
) -> None:

    if update.effective_user is None:
        return

    user = update.effective_user

    try:
        game = game_state.get_game(game_id)
    except Exception:
        await update.message.reply_text(
            "❌ این اتاق پیدا نشد."
        )
        return

    try:
        already = user.id in game.players

        if not already:
            game_state.add_player(
                game_id=game_id,
                player_id=user.id,
                player_name=user_name(user),
            )

        text = (
            "🎴 <b>بازی حکم</b>\n\n"
            f"سلام {user_name(user)} 👋\n\n"
            "شما با موفقیت وارد اتاق شدید.\n\n"
            f"🆔 اتاق: <code>{game_id}</code>\n"
            f"👥 بازیکنان: {len(game.players)}/{game.max_players}"
        )

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=private_game_keyboard(
                game_id
            ),
        )

    except Exception as exc:
        await update.message.reply_text(
            f"❌ امکان ورود به بازی وجود ندارد.\n\n"
            f"{exc}"
        )


# ---------------------------------------------------------
# ورود به بازی
# ---------------------------------------------------------

async def play_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
) -> None:

    if update.effective_user is None:
        return

    user = update.effective_user

    try:
        game = game_state.get_game(game_id)
    except Exception:
        await update.message.reply_text(
            "❌ این اتاق وجود ندارد."
        )
        return

    if user.id not in game.players:
        await update.message.reply_text(
            "❌ شما هنوز وارد این اتاق نشده‌اید.\n\n"
            "ابتدا روی «پیوستن به بازی» بزنید.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👥 پیوستن به بازی",
                            url=bot_link(
                                "join",
                                game_id,
                            ),
                        )
                    ]
                ]
            ),
        )
        return

    await update.message.reply_text(
        "🎴 <b>میز بازی حکم</b>\n\n"
        "برای باز کردن میز بازی روی دکمه زیر بزنید.",
        parse_mode="HTML",
        reply_markup=private_game_keyboard(
            game_id
        ),
    )


# ---------------------------------------------------------
# تنظیمات
# ---------------------------------------------------------

async def settings_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
) -> None:

    if update.effective_user is None:
        return

    user = update.effective_user

    try:
        game = game_state.get_game(game_id)
    except Exception:
        await update.message.reply_text(
            "❌ اتاق پیدا نشد."
        )
        return

    if user.id != game.creator_id:
        await update.message.reply_text(
            "❌ فقط سازنده اتاق می‌تواند تنظیمات را تغییر دهد."
        )
        return

    await update.message.reply_text(
        "⚙️ <b>تنظیمات بازی</b>\n\n"
        f"👥 تعداد بازیکنان: {game.max_players}\n\n"
        "در این مرحله تنظیمات اصلی اتاق "
        "از داخل میز بازی مدیریت می‌شود.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎮 ورود به میز",
                        web_app=WebAppInfo(
                            url=mini_app_url(game_id)
                        ),
                    )
                ]
            ]
        ),
    )


# ---------------------------------------------------------
# دکمه‌های callback
# ---------------------------------------------------------

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    data = query.data or ""

    if data == "create_game":
        await create_game(
            update,
            context,
        )
        return

    if data == "help":
        await query.edit_message_text(
            "❓ <b>راهنمای حکم</b>\n\n"
            "🎮 یک اتاق بسازید.\n"
            "👥 دوستانتان را وارد اتاق کنید.\n"
            "🎴 میز بازی را باز کنید.\n"
            "🏆 بازی حکم را انجام دهید.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 بازگشت",
                            callback_data="home",
                        )
                    ]
                ]
            ),
        )
        return

    if data == "home":
        await query.edit_message_text(
            "🎴 <b>حکم گرین‌دریم</b>\n\n"
            "یک گزینه انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return

    if data.startswith("refresh_"):
        game_id = data.split(
            "_",
            1,
        )[1]

        try:
            game = game_state.get_game(game_id)

            await query.edit_message_text(
                room_text(game_id),
                parse_mode="HTML",
                reply_markup=room_keyboard(
                    game_id,
                    game.creator_id,
                ),
            )

        except Exception:
            await query.edit_message_text(
                "❌ اتاق پیدا نشد."
            )


# ---------------------------------------------------------
# inline mode
# ---------------------------------------------------------

async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.inline_query

    if query is None:
        return

    user = query.from_user

    game_id = create_game_id()

    try:
        game_state.create_game(
            game_id=game_id,
            creator_id=user.id,
            creator_name=user_name(user),
            max_players=4,
        )
    except Exception:
        return

    result = InlineQueryResultArticle(
        id=game_id,
        title="🎴 ساخت اتاق حکم",
        description="ساخت اتاق ۴ نفره برای بازی حکم",
        input_message_content=InputTextMessageContent(
            message_text=(
                "🎴 <b>اتاق حکم گرین‌دریم</b>\n\n"
                f"👑 سازنده: {user_name(user)}\n"
                f"🆔 کد اتاق: <code>{game_id}</code>\n\n"
                "👥 برای ورود به اتاق روی دکمه زیر بزنید."
            ),
            parse_mode="HTML",
        ),
        reply_markup=room_keyboard(
            game_id,
            user.id,
        ),
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=False,
    )


# ---------------------------------------------------------
# خطا
# ---------------------------------------------------------

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    print(
        "BOT ERROR:",
        context.error,
    )


# ---------------------------------------------------------
# اجرای ربات
# ---------------------------------------------------------

def run() -> None:

    settings = Settings.from_environment()

    application = (
        Application.builder()
        .token(settings.bot_token)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
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
        error_handler,
    )

    print(
        "Hokm Green Dream bot is starting..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    run()
