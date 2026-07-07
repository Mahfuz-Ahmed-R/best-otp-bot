from telegram import Update
from telegram.ext import ContextTypes

from bot.config import OTP_SOURCE_CHANNEL_ID
from bot.services.otp_delivery import deliver_otp, find_active_number
from bot.utils.helpers import extract_link_and_otp


async def handle_otp_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read OTP posts from your Telegram channel/group and forward them to users."""
    if not OTP_SOURCE_CHANNEL_ID:
        return

    message = update.channel_post or update.message
    if not message:
        return

    if message.chat_id != OTP_SOURCE_CHANNEL_ID:
        return

    text = message.text or message.caption
    if not text:
        return

    matched_key = find_active_number(text)
    if not matched_key:
        return

    otp_code, ext_link = extract_link_and_otp(text)
    sms_key = f"channel_{message.chat_id}_{message.message_id}"

    await deliver_otp(
        context.application,
        matched_key,
        text,
        otp_code=otp_code,
        ext_link=ext_link,
        sms_key=sms_key,
        post_to_channel=False,
        reply_chat_id=message.chat_id,
        reply_message_id=message.message_id,
    )
