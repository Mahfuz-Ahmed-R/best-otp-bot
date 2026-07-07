from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import REFERRAL_PRICE
from bot.handlers.commands._common import check_banned
from bot.utils.helpers import format_balance, get_referral_count, get_user


async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return

    uid = update.effective_user.id
    get_user(uid)
    bot_info = await context.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={uid}"
    refers = get_referral_count(uid)
    total_reward = float(refers) * REFERRAL_PRICE

    msg = (
        f"🎁 <b>REFER AND EARN</b> 🎁\n\n"
        f"<blockquote>🚀 Invite friends &amp; earn {int(REFERRAL_PRICE)} BDT each!</blockquote>\n\n"
        f"<b>🔗 YOUR LINK:</b>\n"
        f"<blockquote><code>{referral_link}</code></blockquote>\n\n"
        f"<b>📊 STATS:</b>\n"
        f"<blockquote>👥 REFERS: {refers}\n"
        f"💰 EARNED: {format_balance(total_reward)} BDT</blockquote>"
    )
    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("👥 YOUR REFERRALS", callback_data=f"my_ref_{uid}")]]
        ),
    )
