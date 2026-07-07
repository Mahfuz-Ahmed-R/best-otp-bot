import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.handlers.commands._common import check_banned
from bot.services.stats import get_user_stats
from bot.utils.helpers import format_balance, get_user
from bot.utils.text import make_bold_unicode


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return

    uid = update.effective_user.id
    user_data = get_user(uid)
    stats = get_user_stats(uid)
    user = update.effective_user

    profile_text = (
        f"👤 <b>ACCOUNT PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Name:</b> <code>{html.escape(user.full_name or '')}</code>\n"
        f"🆔 <b>Username:</b> <code>@{html.escape(user.username or 'none')}</code>\n"
        f"🗝 <b>ID:</b> <code>{uid}</code>\n\n"
        f"💰 <b>Balance:</b> <code>{format_balance(user_data.get('balance', 0))} BDT</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>Today:</b> 📱 {stats['today_numbers']} | 🔑 {stats['today_otps']}\n"
        f"🔥 <b>7 Days:</b> 📱 {stats['last7d_numbers']} | 🔑 {stats['last7d_otps']}\n"
        f"🌐 <b>All-Time:</b> 📱 {stats['total_numbers']} | 🔑 {stats['total_otps']}"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"💸 {make_bold_unicode('WITHDRAW')}", callback_data="withdraw_start")]]
    )
    await update.message.reply_text(profile_text, parse_mode="HTML", reply_markup=keyboard)
