from telegram import Update
from telegram.ext import ContextTypes

from bot.services.service_loader import get_available_services
from bot.utils.helpers import is_user_banned
from bot.utils.keyboards import build_services_keyboard, main_keyboard


async def show_app_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    services = await get_available_services()
    if not services:
        await update.message.reply_text(
            "⚠️ <b>No services available right now.</b>\nPlease try again later.",
            parse_mode="HTML",
            reply_markup=main_keyboard(uid),
        )
        return

    context.user_data["la_services"] = services
    await update.message.reply_text(
        "📞 <b>GET NUMBER</b>\n\n"
        "<blockquote>✨ Select a <b>Service</b> below:</blockquote>",
        parse_mode="HTML",
        reply_markup=build_services_keyboard(services),
    )
