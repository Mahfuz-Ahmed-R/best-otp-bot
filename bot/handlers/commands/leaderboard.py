import html
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import USER_DATA_FILE
from bot.handlers.commands._common import check_banned
from bot.services.stats import get_user_stats, load_stats
from bot.utils.helpers import get_date_reset_time, load_data
from bot.utils.keyboards import main_keyboard


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update, context):
        return

    uid = update.effective_user.id
    stats_data = load_stats()
    today_midnight = get_date_reset_time()
    users = load_data(USER_DATA_FILE)
    ranked = []

    for uid_str, user_stats in stats_data.items():
        today_count = 0
        for ts in user_stats.get("otps_received", []):
            try:
                if datetime.fromisoformat(ts) >= today_midnight:
                    today_count += 1
            except ValueError:
                continue
        if today_count > 0:
            name = users.get(uid_str, {}).get("full_name") or users.get(uid_str, {}).get("username") or f"User {uid_str}"
            ranked.append((uid_str, today_count, html.escape(str(name))))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top10 = ranked[:10]

    if not top10:
        msg = (
            "<b>🏆 TOP 10 OTP LEADERBOARD 🏆</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ No OTPs received today yet.\n"
        )
    else:
        msg = "<b>🏆 TOP 10 OTP RECEIVERS (TODAY) 🏆</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, (_, count, name) in enumerate(top10, 1):
            medal = medals.get(idx, f"{idx}️⃣")
            msg += f"{medal} <b>{name}</b>\n   🔑 <code>{count}</code> OTPs\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n📊 <i>Resets daily at midnight (BD time)</i>"

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=main_keyboard(uid))
