from telegram import Update
from telegram.ext import ContextTypes

from bot.config import REFERRAL_PRICE, WELCOME_MESSAGE
from bot.handlers.commands._common import check_banned
from bot.services.stats import log_global_activity
from bot.state import request_queue
from bot.utils.helpers import (
    format_balance,
    get_referral_count,
    get_user,
    is_range_request,
    is_referral_request,
    load_data,
    update_db_balance,
    update_referral_count,
    user_exists,
)
from bot.config import USER_DATA_FILE
from bot.utils.keyboards import main_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)

    existing = load_data(USER_DATA_FILE)
    is_new = uid_str not in existing
    if is_new:
        get_user(uid)

    if context.args:
        param = context.args[0]
        if is_range_request(param):
            await request_queue.put({
                "type": "auto_number",
                "update": update,
                "context": context,
                "range_text": param,
            })
            return
        if is_referral_request(param) and is_new:
            try:
                referrer_id = int(param)
                if referrer_id != uid and user_exists(referrer_id):
                    count = get_referral_count(referrer_id) + 1
                    update_referral_count(referrer_id, count)
                    await update_db_balance(referrer_id, REFERRAL_PRICE)
                    log_global_activity(referrer_id, "REFERRAL_JOINED", {"referred_user": uid})
                    try:
                        await context.bot.send_message(
                            referrer_id,
                            f"🎉 <b>NEW REFERRAL!</b>\n\n"
                            f"<blockquote>🗝️ ID: <code>{uid}</code>\n"
                            f"💰 REWARD: {format_balance(REFERRAL_PRICE)} BDT\n"
                            f"👥 TOTAL: {count}</blockquote>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
            except (TypeError, ValueError) as exc:
                print(f"Referral error: {exc}")

    context.user_data.clear()
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")
    await update.message.reply_text("🔹 USE THE BUTTONS BELOW:", reply_markup=main_keyboard(uid))
