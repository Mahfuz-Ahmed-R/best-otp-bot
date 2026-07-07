from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.commands._common import check_banned
from bot.services.selection import show_app_selection


async def get1number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return
    await show_app_selection(update, context)
