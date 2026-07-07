from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.commands._common import check_banned
from bot.utils.helpers import format_balance, get_user
from bot.utils.keyboards import main_keyboard


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return
    balance = get_user(update.effective_user.id)["balance"]
    await update.message.reply_text(
        f"💰 BALANCE: `{format_balance(balance)} BDT`",
        parse_mode="Markdown",
        reply_markup=main_keyboard(update.effective_user.id),
    )
