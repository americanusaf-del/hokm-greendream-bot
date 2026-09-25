from __future__ import annotations

import os
import secrets

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


def user_name(user) -> str:
    if user.full_name:
        return user.full_name

    if user.username:
        return f"@{user.username}"

    return str(user.id)


def create_game_id() -> str:
    return secrets.token_hex(4)


def mini_app_url(game_id: str) -> str:
    return (
        f"{WEB_APP_URL}/"
        f"?game={game_id}"
    )


def bot_link(game_id: str) -> str:
    return (
        f"https://t.me/"
        f"{BOT_USERNAME}"
        f"?start=join_{game_id}"
    )


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
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


def mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👤 ۱ نفره",
                    callback_data="mode_1",
                ),
                InlineKeyboardButton(
                    "👥 ۲ نفره",
                    callback_data="mode_2",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👥👥 ۴ نفره",
                    callback_data="mode_4",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home",
                )
            ],
        ]
    )


def private_game_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎴 ورود به میز بازی",
                    web_app=WebAppInfo(
                        url=mini_app_url(game_id)
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 ارسال لینک بازی",
                    switch_inline_query=(
                        f"بازی حکم {game_id}"
                    ),
                )
            ],
        ]
    )


def room_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 پیوستن به بازی",
                    url=bot_link(game_id),
                )
            ],
            [
                InlineKeyboardButton(
                    "🎴 ورود به میز بازی",
                    web_app=WebAppInfo(
                        url=mini_app_url(game_id)
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات",
                    callback_data=f"settings_{game_id}",
                )
            ],
        ]
    )


def mode_name(
    mode: int,
) -> str:

    if mode == 1:
        return "۱ نفره"

    if mode == 2:
        return "۲ نفره"

    return "۴ نفره"


def room_text(
    game_id: str,
) -> str:

    game = game_state.get_game(
        game_id
    )

    if not game:
        return "❌ بازی پیدا نشد."

    return (
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        f"🎮 حالت: <b>{mode_name(game.max_players)}</b>\n"
        f"👥 بازیکنان: "
        f"<b>{game.player_count if hasattr(game, 'player_count') else len(game.players)}</b>"
        f"/<b>{game.max_players}</b>\n\n"
        "برای ورود به بازی روی دکمه زیر بزنید.\n"
        "سازنده می‌تواند بازی را از داخل میز شروع کند."
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if not message:
        return

    args = context.args

    if args:

        command = args[0]

        if command.startswith("join_"):

            game_id = command[
                len("join_"):
            ]

            await join_game(
                update,
                context,
                game_id,
            )

            return

        if command.startswith("play_"):

            game_id = command[
                len("play_"):
            ]

            await play_game(
                update,
                context,
                game_id,
            )

            return

        if command.startswith("settings_"):

            game_id = command[
                len("settings_"):
            ]

            await settings_game(
                update,
                context,
                game_id,
            )

            return

    await message.reply_text(
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        "به بازی حکم خوش آمدید.\n\n"
        "از اینجا می‌توانید یک میز جدید بسازید "
        "یا وارد بازی دوستانتان شوید.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def create_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        "🎮 <b>تعداد بازیکنان را انتخاب کنید:</b>\n\n"
        "👤 <b>۱ نفره</b> — شما در برابر کامپیوتر\n"
        "👥 <b>۲ نفره</b> — یک بازیکن دیگر هم می‌تواند وارد شود\n"
        "👥👥 <b>۴ نفره</b> — چهار بازیکن واقعی",
        parse_mode="HTML",
        reply_markup=mode_menu(),
    )


async def create_game_with_mode(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: int,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    user = query.from_user

    game_id = create_game_id()

    game_state.create_game(
        game_id=game_id,
        creator_id=user.id,
        creator_name=user_name(user),
        max_players=mode,
    )

    if mode == 1:

        text = (
            "🎮 <b>بازی تک‌نفره ساخته شد!</b>\n\n"
            "شما در مقابل بازیکنان کامپیوتری بازی می‌کنید.\n\n"
            "🎴 وارد میز شوید و بازی را شروع کنید."
        )

    elif mode == 2:

        text = (
            "🎮 <b>بازی دونفره ساخته شد!</b>\n\n"
            "لینک بازی را برای بازیکن دوم بفرستید.\n\n"
            "بعد از ورود بازیکن دوم، سازنده می‌تواند "
            "بازی را شروع کند."
        )

    else:

        text = (
            "🎮 <b>بازی چهارنفره ساخته شد!</b>\n\n"
            "لینک بازی را در گروه بفرستید تا سه بازیکن "
            "دیگر وارد شوند.\n\n"
            "بعد از کامل شدن میز، سازنده بازی را شروع می‌کند."
        )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=private_game_keyboard(
            game_id
        ),
    )


async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    message = update.effective_message

    if not message:
        return

    user = update.effective_user

    game = game_state.get_game(
        game_id
    )

    if not game:

        await message.reply_text(
            "❌ این بازی دیگر وجود ندارد."
        )

        return

    ok, text = game_state.add_player(
        game_id=game_id,
        player_id=user.id,
        player_name=user_name(user),
    )

    if not ok:

        await message.reply_text(
            f"❌ {text}"
        )

        return

    await message.reply_text(
        "✅ <b>وارد بازی شدید!</b>\n\n"
        f"🎮 حالت: <b>{mode_name(game.max_players)}</b>\n"
        f"👥 بازیکنان حاضر: "
        f"<b>{len(game.players)}</b>"
        f"/<b>{game.max_players}</b>\n\n"
        "حالا وارد میز بازی شوید.",
        parse_mode="HTML",
        reply_markup=private_game_keyboard(
            game_id
        ),
    )


async def play_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    message = update.effective_message

    if not message:
        return

    user = update.effective_user

    game = game_state.get_game(
        game_id
    )

    if not game:

        await message.reply_text(
            "❌ بازی پیدا نشد."
        )

        return

    player = game_state.get_player(
        game,
        user.id,
    )

    if not player:

        await message.reply_text(
            "❌ شما عضو این بازی نیستید.\n\n"
            "ابتدا وارد بازی شوید."
        )

        return

    await message.reply_text(
        "🎴 <b>میز بازی آماده است.</b>\n\n"
        "برای ورود به میز روی دکمه زیر بزنید.",
        parse_mode="HTML",
        reply_markup=private_game_keyboard(
            game_id
        ),
    )


async def settings_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    query = update.callback_query

    if query:
        user = query.from_user

    else:
        user = update.effective_user

    game = game_state.get_game(
        game_id
    )

    if not game:

        if query:
            await query.answer(
                "بازی پیدا نشد.",
                show_alert=True,
            )

        return

    if user.id != game.creator_id:

        if query:
            await query.answer(
                "فقط سازنده بازی می‌تواند تنظیمات را تغییر دهد.",
                show_alert=True,
            )

        return

    text = (
        "⚙️ <b>تنظیمات بازی</b>\n\n"
        f"🎮 حالت فعلی: "
        f"<b>{mode_name(game.max_players)}</b>\n"
        f"👥 بازیکنان: "
        f"<b>{len(game.players)}</b>"
        f"/<b>{game.max_players}</b>\n\n"
        "تغییر تنظیمات بعد از شروع بازی امکان‌پذیر نیست."
    )

    if query:

        await query.answer()

        await query.edit_message_text(
            text,
            parse_mode="HTML",
        )

    else:

        await update.effective_message.reply_text(
            text,
            parse_mode="HTML",
        )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    text = (
        "📖 <b>راهنمای حکم گرین‌دریم</b>\n\n"
        "🎮 ابتدا حالت بازی را انتخاب کنید.\n"
        "👤 در حالت تک‌نفره با کامپیوتر بازی می‌کنید.\n"
        "👥 در حالت دونفره یک بازیکن دیگر می‌تواند وارد شود.\n"
        "👥👥 در حالت چهارنفره سه بازیکن دیگر باید وارد شوند.\n\n"
        "👑 حاکم ابتدا ۵ کارت خود را می‌بیند و حکم را انتخاب می‌کند.\n"
        "🎴 سپس بازی ادامه پیدا می‌کند.\n"
        "🏆 هر دست به بازیکنی می‌رسد که قوی‌ترین کارت قانونی را بازی کرده باشد."
    )

    if query:

        await query.answer()

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 برگشت",
                            callback_data="home",
                        )
                    ]
                ]
            ),
        )

    else:

        await update.effective_message.reply_text(
            text,
            parse_mode="HTML",
        )


async def home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        "یک گزینه را انتخاب کنید:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def refresh_room(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    game_id = query.data[
        len("refresh_"):
    ]

    game = game_state.get_game(
        game_id
    )

    if not game:

        await query.edit_message_text(
            "❌ بازی پیدا نشد."
        )

        return

    await query.edit_message_text(
        room_text(game_id),
        parse_mode="HTML",
        reply_markup=room_keyboard(
            game_id
        ),
    )


async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.inline_query

    if not query:
        return

    user = query.from_user

    game_id = create_game_id()

    game_state.create_game(
        game_id=game_id,
        creator_id=user.id,
        creator_name=user_name(user),
        max_players=4,
    )

    text = (
        "♠️ <b>بازی حکم گرین‌دریم</b> ♥️\n\n"
        f"سازنده: <b>{user_name(user)}</b>\n"
        "🎮 حالت: <b>۴ نفره</b>\n"
        "👥 بازیکنان: <b>1/4</b>\n\n"
        "برای پیوستن به بازی روی دکمه زیر بزنید."
    )

    result = InlineQueryResultArticle(
        id=game_id,
        title="🎴 ساخت میز حکم",
        description="ساخت یک میز حکم چهارنفره برای گروه",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
        reply_markup=room_keyboard(
            game_id
        ),
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=False,
    )


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    if data == "create_game":

        await create_game(
            update,
            context,
        )

        return

    if data == "mode_1":

        await create_game_with_mode(
            update,
            context,
            1,
        )

        return

    if data == "mode_2":

        await create_game_with_mode(
            update,
            context,
            2,
        )

        return

    if data == "mode_4":

        await create_game_with_mode(
            update,
            context,
            4,
        )

        return

    if data == "help":

        await help_command(
            update,
            context,
        )

        return

    if data == "home":

        await home(
            update,
            context,
        )

        return

    if data.startswith("refresh_"):

        await refresh_room(
            update,
            context,
        )

        return

    if data.startswith("settings_"):

        game_id = data[
            len("settings_"):
        ]

        await settings_game(
            update,
            context,
            game_id,
        )

        return


def run():

    settings = Settings.from_environment()

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
            inline_query
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    print(
        "Hokm Green Dream bot is starting..."
    )

    application.run_polling(
        drop_pending_updates=True
    )
