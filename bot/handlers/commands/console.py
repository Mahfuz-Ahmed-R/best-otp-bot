import html
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot.api.client import fetch_console
from bot.handlers.commands._common import check_banned
from bot.utils.keyboards import is_admin, main_keyboard


async def console_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return

    hits = await fetch_console()
    if not hits:
        await update.message.reply_text("📭 No console hits right now.")
        return

    lines = ["🖥️ <b>PANEL CONSOLE (recent hits)</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, hit in enumerate(hits[:15], 1):
        ts = hit.get("time")
        when = ""
        if ts:
            try:
                when = datetime.fromtimestamp(int(ts) / 1000).strftime("%H:%M:%S")
            except (TypeError, ValueError, OSError):
                when = str(ts)
        lines.append(
            f"{i}. <b>{html.escape(str(hit.get('sid', '?')))}</b> "
            f"<code>{html.escape(str(hit.get('range', '')))}</code>\n"
            f"   {html.escape(str(hit.get('message', ''))[:80])}\n"
            f"   🕐 {when}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=main_keyboard(update.effective_user.id))
