from __future__ import annotations

import os
import secrets

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
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


def user_name(user) -> str:
    if user.full_name:
        return user.full_name

    if user.username:
        return f"@{user.username}"

    return str(user.id)


def create_game_id() -> str:
    return secrets.token_hex(4)


# ---------------------------------------------------------
# Main Mini App
# ---------------------------------------------------------

def main_mini_app_link(game_id: str) -> str:
    return (
        f"https://t.me/"
        f"{BOT_USERNAME}"
        f"?startapp={game_id}"
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


# ---------------------------------------------------------
# انتخاب تعداد بازیکنان
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# دکمه‌های اتاق بازی
# ---------------------------------------------------------

def room_keyboard(
    game_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎴 ورود / پیوستن به میز",
                    url=main_mini_app_link(game_id),
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات بازی",
                    callback_data=f"settings_{game_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 بروزرسانی",
                    callback_data=f"refresh_{game_id}",
                )
            ],
        ]
    )


# ---------------------------------------------------------
# نام حالت
# ---------------------------------------------------------

def mode_name(mode: int) -> str:

    if mode == 1:
        return "۱ نفره"

    if mode == 2:
        return "۲ نفره"

    return "۴ نفره"


# ---------------------------------------------------------
# تعداد بازیکنان واقعی
# ---------------------------------------------------------

def human_player_count(game) -> int:

    return len(
        [
            player
            for player in game.players
            if not player.is_bot
        ]
    )


# ---------------------------------------------------------
# متن اتاق
# ---------------------------------------------------------

def room_text(game_id: str) -> str:

    game = game_state.get_game(game_id)

    if not game:
        return "❌ بازی پیدا نشد."

    human_count = human_player_count(game)

    if game.mode == 1:
        description = (
            "🤖 شما در مقابل بازیکنان کامپیوتری بازی می‌کنید."
        )

    elif game.mode == 2:
        description = (
            "👥 یک بازیکن دیگر می‌تواند از همین میز وارد شود."
        )

    else:
        description = (
            "👥 سه بازیکن دیگر می‌توانند از همین میز وارد شوند."
        )

    return (
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        f"🎮 حالت بازی: <b>{mode_name(game.mode)}</b>\n"
        f"👥 بازیکنان: "
        f"<b>{human_count}</b>"
        f"/<b>{game.mode}</b>\n\n"
        f"{description}\n\n"
        "برای ورود به میز روی دکمه زیر بزنید."
    )


# ---------------------------------------------------------
# /start
# ---------------------------------------------------------

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

            game_id = command[len("join_"):]

            await join_game(
                update,
                context,
                game_id,
            )

            return

        if command.startswith("play_"):

            game_id = command[len("play_"):]

            await play_game(
                update,
                context,
                game_id,
            )

            return

        if command.startswith("settings_"):

            game_id = command[len("settings_"):]

            await settings_game(
                update,
                context,
                game_id,
            )

            return

    await message.reply_text(
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        "به بازی حکم خوش آمدید.\n\n"
        "برای ساخت یک میز جدید، دکمه زیر را بزنید.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ---------------------------------------------------------
# نمایش انتخاب حالت
# ---------------------------------------------------------

async def create_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        "🎮 <b>حالت بازی را انتخاب کنید</b>\n\n"
        "👤 <b>۱ نفره</b>\n"
        "بازی شما در برابر کامپیوتر است.\n\n"
        "👥 <b>۲ نفره</b>\n"
        "یک بازیکن دیگر می‌تواند وارد میز شود.\n\n"
        "👥👥 <b>۴ نفره</b>\n"
        "سه بازیکن دیگر می‌توانند وارد میز شوند.",
        parse_mode="HTML",
        reply_markup=mode_menu(),
    )


# ---------------------------------------------------------
# ساخت بازی با حالت انتخاب شده
# ---------------------------------------------------------

async def create_game_with_mode(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: int,
):

    query = update.callback_query

    if not query:
        return

    user = query.from_user

    await query.answer()

    game_id = create_game_id()

    game_state.create_game(
        game_id=game_id,
        creator_id=user.id,
        creator_name=user_name(user),
        max_players=mode,
    )

    game = game_state.get_game(game_id)

    if not game:
        await query.edit_message_text(
            "❌ خطا در ساخت بازی."
        )
        return

    await query.edit_message_text(
        room_text(game_id),
        parse_mode="HTML",
        reply_markup=room_keyboard(game_id),
    )


# ---------------------------------------------------------
# ورود قدیمی از /start
# ---------------------------------------------------------

async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    message = update.effective_message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    game = game_state.get_game(game_id)

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
        f"🎮 حالت: <b>{mode_name(game.mode)}</b>\n"
        f"👥 بازیکنان حاضر: "
        f"<b>{human_player_count(game)}</b>"
        f"/<b>{game.mode}</b>\n\n"
        "حالا وارد میز بازی شوید.",
        parse_mode="HTML",
        reply_markup=room_keyboard(game_id),
    )


# ---------------------------------------------------------
# ورود به بازی قدیمی
# ---------------------------------------------------------

async def play_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    message = update.effective_message

    if not message:
        return

    game = game_state.get_game(game_id)

    if not game:
        await message.reply_text(
            "❌ بازی پیدا نشد."
        )
        return

    await message.reply_text(
        room_text(game_id),
        parse_mode="HTML",
        reply_markup=room_keyboard(game_id),
    )


# ---------------------------------------------------------
# تنظیمات
# ---------------------------------------------------------

async def settings_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    query = update.callback_query

    if not query:
        return

    user = query.from_user

    game = game_state.get_game(game_id)

    if not game:

        await query.answer(
            "بازی پیدا نشد.",
            show_alert=True,
        )

        return

    if user.id != game.creator_id:

        await query.answer(
            "فقط سازنده بازی می‌تواند تنظیمات را تغییر دهد.",
            show_alert=True,
        )

        return

    await query.answer()

    text = (
        "⚙️ <b>تنظیمات بازی</b>\n\n"
        f"🎮 حالت فعلی: "
        f"<b>{mode_name(game.mode)}</b>\n"
        f"👥 بازیکنان حاضر: "
        f"<b>{human_player_count(game)}</b>"
        f"/<b>{game.mode}</b>\n\n"
        "نوع بازی پس از ساخت میز انتخاب شده است.\n"
        "بعد از شروع بازی امکان تغییر آن وجود ندارد."
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 برگشت به میز",
                        callback_data=f"room_{game_id}",
                    )
                ]
            ]
        ),
    )


# ---------------------------------------------------------
# راهنما
# ---------------------------------------------------------

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    text = (
        "📖 <b>راهنمای حکم گرین‌دریم</b>\n\n"
        "🎮 ابتدا یک میز بسازید.\n\n"
        "👤 <b>۱ نفره:</b>\n"
        "شما در مقابل کامپیوتر بازی می‌کنید.\n\n"
        "👥 <b>۲ نفره:</b>\n"
        "یک بازیکن دیگر می‌تواند وارد میز شود.\n\n"
        "👥👥 <b>۴ نفره:</b>\n"
        "سه بازیکن دیگر می‌توانند وارد میز شوند.\n\n"
        "👑 حاکم ابتدا ۵ کارت دریافت می‌کند و حکم را انتخاب می‌کند.\n\n"
        "🎴 سپس بازی شروع می‌شود."
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

        return

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
    )


# ---------------------------------------------------------
# خانه
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# برگشت به اتاق
# ---------------------------------------------------------

async def room_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    game = game_state.get_game(game_id)

    if not game:

        await query.edit_message_text(
            "❌ بازی پیدا نشد."
        )

        return

    await query.edit_message_text(
        room_text(game_id),
        parse_mode="HTML",
        reply_markup=room_keyboard(game_id),
    )


# ---------------------------------------------------------
# بروزرسانی اتاق
# ---------------------------------------------------------

async def refresh_room(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    game_id = query.data[len("refresh_"):]

    game = game_state.get_game(game_id)

    if not game:

        await query.edit_message_text(
            "❌ بازی پیدا نشد."
        )

        return

    await query.edit_message_text(
        room_text(game_id),
        parse_mode="HTML",
        reply_markup=room_keyboard(game_id),
    )


# ---------------------------------------------------------
# Inline Mode
# ---------------------------------------------------------

async def inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.inline_query

    if not query:
        return

    user = query.from_user

    if not user:
        return

    # نکته مهم:
    # اینجا دیگر بازی ساخته نمی‌شود.
    # ابتدا پیام انتخاب حالت داخل گروه فرستاده می‌شود.
    text = (
        "♠️ <b>حکم گرین‌دریم</b> ♥️\n\n"
        f"سازنده: <b>{user_name(user)}</b>\n\n"
        "🎮 برای ساخت میز، حالت بازی را انتخاب کنید."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 انتخاب حالت بازی",
                    callback_data="choose_mode",
                )
            ]
        ]
    )

    result = InlineQueryResultArticle(
        id="hokm_create_room",
        title="🎴 ساخت میز حکم",
        description="ساخت میز حکم داخل همین گروه",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
        reply_markup=keyboard,
    )

    await query.answer(
        results=[result],
        cache_time=0,
        is_personal=False,
    )


# ---------------------------------------------------------
# Callback Handler
# ---------------------------------------------------------

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    # ساخت بازی
    if data == "create_game":

        await create_game(
            update,
            context,
        )

        return

    # انتخاب حالت داخل گروه
    if data == "choose_mode":

        await query.answer()

        await query.edit_message_text(
            "🎮 <b>حالت بازی را انتخاب کنید:</b>\n\n"
            "👤 ۱ نفره — بازی با کامپیوتر\n"
            "👥 ۲ نفره — دو بازیکن\n"
            "👥👥 ۴ نفره — چهار بازیکن",
            parse_mode="HTML",
            reply_markup=mode_menu(),
        )

        return

    # حالت ۱ نفره
    if data == "mode_1":

        await create_game_with_mode(
            update,
            context,
            1,
        )

        return

    # حالت ۲ نفره
    if data == "mode_2":

        await create_game_with_mode(
            update,
            context,
            2,
        )

        return

    # حالت ۴ نفره
    if data == "mode_4":

        await create_game_with_mode(
            update,
            context,
            4,
        )

        return

    # راهنما
    if data == "help":

        await help_command(
            update,
            context,
        )

        return

    # خانه
    if data == "home":

        await home(
            update,
            context,
        )

        return

    # بروزرسانی
    if data.startswith("refresh_"):

        await refresh_room(
            update,
            context,
        )

        return

    # تنظیمات
    if data.startswith("settings_"):

        game_id = data[len("settings_"):]

        await settings_game(
            update,
            context,
            game_id,
        )

        return

    # برگشت به اتاق
    if data.startswith("room_"):

        game_id = data[len("room_"):]

        await room_view(
            update,
            context,
            game_id,
        )

        return


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

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
