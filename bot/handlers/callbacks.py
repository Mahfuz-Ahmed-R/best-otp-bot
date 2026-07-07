import asyncio
import html
import io
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.admin.callbacks import handle_admin_callback
from bot.config import ACTIVITY_LOGS_FILE, MIN_WITHDRAW, OTP_GROUP_LINK, USER_DATA_FILE
from bot.handlers.withdraw import (
    admin_approve_withdraw,
    admin_reject_withdraw,
    process_withdraw_cancel,
    process_withdraw_confirm,
)
from bot.services.numbers import fast_allocate_number_multi, process_numbers
from bot.services.stats import get_user_stats
from bot.state import last_range
from bot.utils.country import clean_country_display, get_country_info
from bot.utils.helpers import (
    format_balance,
    get_user,
    is_user_banned,
    load_data,
)
from bot.utils.keyboards import (
    build_countries_keyboard,
    build_services_keyboard,
    is_admin,
    main_keyboard,
    withdraw_method_keyboard,
)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()

    if not is_admin(uid) and is_user_banned(uid):
        await query.edit_message_text("🚫 YOU ARE BANNED 🚫")
        return

    context.user_data["admin_state"] = None
    context.user_data["add_balance_mode"] = False
    context.user_data["remove_balance_mode"] = False
    context.user_data["admin_ban_mode"] = False
    context.user_data["admin_unban_mode"] = False
    context.user_data["withdraw_mode"] = None
    context.user_data["broadcast_mode"] = False
    context.user_data["mode"] = None

    if data.startswith("adm_") or data.startswith("manage_svc_"):
        if await handle_admin_callback(update, context):
            return

    if data.startswith("svc_"):
        idx = int(data.replace("svc_", ""))
        services = context.user_data.get("la_services", [])
        if not services:
            services = context.user_data.get("la_services", [])
        if not services:
            from bot.services.service_loader import get_available_services
            services = await get_available_services()
            context.user_data["la_services"] = services
        if idx >= len(services):
            await query.answer("Service not found. Please try again.", show_alert=True)
            return

        svc = services[idx]
        sid = svc.get("sid", "Service")
        ranges = svc.get("ranges", [])

        if not ranges:
            await query.answer("No ranges available for this service.", show_alert=True)
            return

        context.user_data["la_svc_idx"] = idx
        context.user_data["la_sid"] = sid
        context.user_data["la_ranges"] = ranges

        keyboard = build_countries_keyboard(ranges, idx)
        await query.message.edit_text(
            f"📞 <b>GET NUMBER</b>\n\n"
            f"<blockquote>📱 Service: <b>{html.escape(sid)}</b></blockquote>\n"
            f"<blockquote>🌍 আপনার পছন্দের <b>Country</b> সিলেক্ট করুন:</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if data.startswith("rng_"):
        idx = int(data.replace("rng_", ""))
        ranges = context.user_data.get("la_ranges", [])
        if idx >= len(ranges):
            await query.answer("Range not found. Please try again.", show_alert=True)
            return

        range_item = ranges[idx]
        target_country = range_item.get("country", "")
        if not target_country:
            r_text = range_item.get("range", "")
            prefix = re.sub(r"[xX]+$", "", str(r_text)).strip()
            prefix_clean = re.sub(r"\D", "", prefix)
            flag, cname = get_country_info(prefix_clean)
            target_country = f"{flag} {cname}"

        all_country_ranges = []
        target_clean = clean_country_display(target_country)
        for r_item in ranges:
            c_disp = r_item.get("country", "")
            if not c_disp:
                pref = re.sub(r"[xX]+$", "", str(r_item.get("range", ""))).strip()
                pref_cl = re.sub(r"\D", "", pref)
                flg, cn = get_country_info(pref_cl)
                c_disp = f"{flg} {cn}"
            if clean_country_display(c_disp) == target_clean:
                all_country_ranges.append(r_item.get("range", ""))

        sid = context.user_data.get("la_sid", "")
        asyncio.create_task(fast_allocate_number_multi(query, context, all_country_ranges, sid))
        return

    if data == "back_services":
        from bot.services.service_loader import get_available_services

        services = await get_available_services()
        if not services:
            await query.message.edit_text("❌ Services লোড করা যায়নি।")
            return
        context.user_data["la_services"] = services
        keyboard = build_services_keyboard(services)
        await query.message.edit_text(
            "📞 <b>GET NUMBER</b>\n\n"
            "<blockquote>📱 নিচ থেকে একটি <b>Service</b> সিলেক্ট করুন:</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if data == "same_range":
        r_text = last_range.get(uid)
        if r_text:
            try:
                await query.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 OTP GROUP", url=OTP_GROUP_LINK, style="primary")],
                    ])
                )
            except Exception:
                pass
            await process_numbers(update, context, r_text, 1)
        return

    if data == "withdraw_start":
        balance = get_user(uid)["balance"]
        if balance < MIN_WITHDRAW:
            await query.message.reply_text(
                f"<blockquote>💵 BALANCE: {format_balance(balance)} BDT\n📉 MIN WITHDRAW: {MIN_WITHDRAW} BDT</blockquote>",
                parse_mode="HTML",
            )
            return
        context.user_data["withdraw_mode"] = "select_method"
        await query.message.reply_text("💳 SELECT YOUR PAYMENT METHOD!", reply_markup=withdraw_method_keyboard())
        return

    if data == "withdraw_confirm":
        await process_withdraw_confirm(update, context)
        return

    if data == "withdraw_cancel":
        await process_withdraw_cancel(update, context)
        return

    if data.startswith("admin_approve_"):
        await admin_approve_withdraw(update, context, data.replace("admin_approve_", ""))
        return

    if data.startswith("admin_reject_"):
        await admin_reject_withdraw(update, context, data.replace("admin_reject_", ""))
        return

    if data.startswith("my_ref_"):
        target_uid = data.replace("my_ref_", "")
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        my_referrals = [
            log for log in all_logs
            if str(log.get("uid")) == str(target_uid) and log.get("action") == "REFERRAL_JOINED"
        ]
        content = f"👥 REFERRAL REPORT — {target_uid}\n━━━━━━━━━━━━\nTOTAL: {len(my_referrals)}\n\n"
        for i, log in enumerate(my_referrals, 1):
            try:
                dt_obj = datetime.fromisoformat(log["timestamp"])
                ref_id = log.get("details", {}).get("referred_user", "N/A")
                content += f"{i}. ID: {ref_id} | {dt_obj.strftime('%d/%m/%Y %I:%M %p')}\n"
            except (ValueError, KeyError, TypeError):
                continue
        f = io.BytesIO(content.encode())
        f.name = f"REF_{target_uid}.txt"
        await context.bot.send_document(chat_id=uid, document=f, caption="✅ **REFERRAL DATA**", parse_mode="Markdown")
        return

    if data.startswith("full_logs_"):
        target_uid = data.replace("full_logs_", "")
        stats = get_user_stats(target_uid)
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        user_db = load_data(USER_DATA_FILE)
        user_info = user_db.get(str(target_uid), {})
        user_otps = [
            log for log in all_logs
            if str(log.get("uid")) == str(target_uid) and log.get("action") == "OTP_RECEIVED"
        ]
        content = (
            f"📊 USER DATA REPORT — {target_uid}\n"
            f"💰 BALANCE: {user_info.get('balance', 0):.2f} BDT\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"TODAY NUMBERS: {stats['today_numbers']}\n"
            f"TODAY OTPS: {stats['today_otps']}\n"
            f"7D NUMBERS: {stats['last7d_numbers']}\n"
            f"7D OTPS: {stats['last7d_otps']}\n"
            f"TOTAL NUMBERS: {stats['total_numbers']}\n"
            f"TOTAL OTPS: {stats['total_otps']}\n"
            f"━━━━━━━━━━━━━━━━━━\n\nOTP LOGS:\n"
        )
        for i, log in enumerate(user_otps, 1):
            try:
                dt_obj = datetime.fromisoformat(log["timestamp"])
                d = log.get("details", {})
                content += f"{i}. {dt_obj.strftime('%d/%m/%Y %I:%M %p')}\n   📞 {d.get('number', 'N/A')}\n   🔑 {d.get('otp', 'N/A')}\n\n"
            except (ValueError, KeyError, TypeError):
                continue
        f = io.BytesIO(content.encode())
        f.name = f"USER_{target_uid}.txt"
        await context.bot.send_document(
            chat_id=uid,
            document=f,
            caption=f"✅ <b>DATA FOR USER: <code>{target_uid}</code></b>",
            parse_mode="HTML",
        )
        return
