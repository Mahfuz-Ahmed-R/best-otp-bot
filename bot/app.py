import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import MAX_WORKERS
from bot.handlers.callbacks import button_callback
from bot.handlers.commands.balance import balance_command
from bot.handlers.commands.get1number import get1number_command
from bot.handlers.commands.leaderboard import leaderboard_command
from bot.handlers.commands.console import console_command
from bot.handlers.commands.profile import profile_command
from bot.handlers.commands.refer import refer_command
from bot.handlers.commands.start import start_command
from bot.handlers.channel_otp import handle_otp_channel_message
from bot.handlers.messages import handle_message
from bot.config import OTP_SOURCE_CHANNEL_ID
from bot.services.monitor import monitor_loop
from bot.services.numbers import worker


async def post_init(application):
    from bot.api.client import fetch_live_services
    from bot.config import MAUTHAPI_KEY, OTP_SOURCE_CHANNEL_ID

    if not MAUTHAPI_KEY:
        print("WARNING: MAUTHAPI_KEY is not set. Panel API calls will fail.")
    else:
        services = await fetch_live_services()
        if services:
            print(f"Panel API OK — {len(services)} live service(s) loaded.")
        else:
            print("WARNING: Panel API returned no services. Check MAUTHAPI_KEY or add custom services in Admin Panel.")

    if OTP_SOURCE_CHANNEL_ID:
        print(f"OTP channel listener enabled for chat ID: {OTP_SOURCE_CHANNEL_ID}")
    else:
        print("INFO: Set OTP_GROUP_ID / OTP_SOURCE_CHANNEL_ID to forward OTPs from your Telegram channel.")

    for _ in range(MAX_WORKERS):
        asyncio.create_task(worker())
    asyncio.create_task(monitor_loop(application))


def build_application(token: str):
    from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

    app = (
        ApplicationBuilder()
        .token(token)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("get1number", get1number_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("refer", refer_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("console", console_command))

    app.add_handler(CallbackQueryHandler(button_callback))

    if OTP_SOURCE_CHANNEL_ID:
        channel_filter = filters.Chat(chat_id=OTP_SOURCE_CHANNEL_ID) & (
            filters.UpdateType.CHANNEL_POSTS | filters.UpdateType.MESSAGE
        )
        app.add_handler(
            MessageHandler(
                channel_filter & (filters.TEXT | filters.CAPTION),
                handle_otp_channel_message,
            )
        )

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    return app
