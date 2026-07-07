import asyncio
import html
import re
from datetime import datetime

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.api.client import fetch_number, normalize_rid
from bot.services.stats import add_number_taken, add_otp_received
from bot.state import active_numbers, last_range, request_queue
from bot.utils.country import get_country_info
from bot.utils.helpers import (
    is_user_banned,
    normalize_number,
    save_number_range_info,
)
from bot.utils.keyboards import main_keyboard, number_result_keyboard


async def fetch_number_async(range_str: str):
    rid = normalize_rid(range_str)
    return await fetch_number(rid)


def _format_number_message(clean_num, range_text, res):
    country_flag, country_name = get_country_info(clean_num)
    if res.get("otp_now") and res.get("otp"):
        otp_safe = html.escape(str(res["otp"]))
        sms_safe = html.escape(str(res.get("sms") or ""))
        return (
            f"✅ <b>YOUR NUMBER</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {html.escape(country_name)}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n"
            f"<blockquote>📞 NUMBER: <code>+{clean_num}</code></blockquote>\n"
            f"<blockquote>🔑 OTP: <code>{otp_safe}</code></blockquote>"
            + (f"\n<blockquote>📩 SMS: <code>{sms_safe}</code></blockquote>" if sms_safe else "")
            + "\n\n<b>✅ OTP RECEIVED INSTANTLY!</b>"
        )
    return (
        f"✅ <b>YOUR NUMBER</b> ✅\n\n"
        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {html.escape(country_name)}</code></blockquote>\n"
        f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n"
        f"<blockquote>📞 NUMBER: <code>+{clean_num}</code></blockquote>\n\n"
        f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
    )


async def fast_allocate_number_multi(query, context, ranges_list, sid):
    uid = query.from_user.id
    if is_user_banned(uid):
        await query.message.edit_text("🚫 YOU ARE BANNED 🚫")
        return

    try:
        await query.message.edit_text(
            "⚡ <b>ALLOCATING YOUR NUMBER</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 <i>Searching active pool... Please wait.</i>",
            parse_mode="HTML",
        )
    except Exception as exc:
        print(f"Loading state error: {exc}")

    res = None
    successful_range = None
    for r_text in ranges_list:
        res = await fetch_number_async(r_text)
        if res and res.get("number"):
            successful_range = r_text
            break

    if not res or not res.get("number"):
        await query.message.edit_text(
            "❌ <b>Number not available.</b>\n\n"
            "<blockquote>⚠️ No number in this range right now. Try another service or country.</blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 BACK", callback_data="back_services")]]
            ),
        )
        return

    clean_num = normalize_number(res["number"])
    add_number_taken(uid, 1)
    last_range[uid] = successful_range
    active_numbers[clean_num] = {"uid": uid, "range": successful_range, "timestamp": datetime.now()}
    save_number_range_info(uid, clean_num, successful_range)

    if res.get("otp_now") and res.get("otp"):
        add_otp_received(uid)

    text = _format_number_message(clean_num, successful_range, res)
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=number_result_keyboard())


async def process_auto_number(update: Update, context: ContextTypes.DEFAULT_TYPE, range_text: str):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_user_banned(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING...")
    res = await fetch_number_async(range_text)
    if not res or not res.get("number"):
        await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
        return

    generated_num = normalize_number(res["number"])
    add_number_taken(uid, 1)
    last_range[uid] = range_text
    active_numbers[generated_num] = {"uid": uid, "range": range_text, "timestamp": datetime.now()}
    save_number_range_info(uid, generated_num, range_text)

    if res.get("otp_now") and res.get("otp"):
        add_otp_received(uid)

    text = _format_number_message(generated_num, range_text, res).replace("YOUR NUMBER", "YOUR NUMBER DETAILS")
    await status_msg.edit_text(text, parse_mode="HTML", reply_markup=number_result_keyboard())


async def process_numbers(update_or_query, context, range_text: str, count: int):
    if isinstance(update_or_query, Update) and update_or_query.callback_query:
        uid = update_or_query.callback_query.from_user.id
        chat_id = update_or_query.callback_query.message.chat_id
    else:
        uid = update_or_query.effective_user.id
        chat_id = update_or_query.effective_chat.id

    if is_user_banned(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING . . .")
    add_number_taken(uid, count)
    last_range[uid] = range_text

    results = await asyncio.gather(*[fetch_number_async(range_text) for _ in range(count)])
    valid = [r for r in results if r and r.get("number")]
    if not valid:
        await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
        return

    entries = []
    for r in valid:
        clean_num = normalize_number(r["number"])
        active_numbers[clean_num] = {"uid": uid, "range": range_text, "timestamp": datetime.now()}
        save_number_range_info(uid, clean_num, range_text)
        entries.append({"num": clean_num, **r})

    country_flag, country_name = get_country_info(entries[0]["num"])
    lines = []
    for entry in entries:
        if entry.get("otp_now") and entry.get("otp"):
            add_otp_received(uid)
            lines.append(
                f"<blockquote>📞 NUMBER: <code>+{entry['num']}</code>\n"
                f"🔑 OTP: <code>{html.escape(str(entry['otp']))}</code></blockquote>"
            )
        else:
            lines.append(f"<blockquote>📞 NUMBER: <code>+{entry['num']}</code></blockquote>")

    any_instant = any(e.get("otp_now") and e.get("otp") for e in entries)
    sms_status = "✅ OTP RECEIVED INSTANTLY!" if any_instant else "📩 SMS STATUS: ⏳ WAITING..."
    final_text = (
        f"✅ <b>YOUR NUMBER DETAILS</b> ✅\n\n"
        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
        f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n\n"
        f"{chr(10).join(lines)}\n\n"
        f"<b>{sms_status}</b>"
    )
    await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=number_result_keyboard())


async def worker():
    while True:
        task = await request_queue.get()
        try:
            if task["type"] == "process_numbers":
                await process_numbers(task["update"], task["context"], task["range_text"], task["count"])
            elif task["type"] == "auto_number":
                await process_auto_number(task["update"], task["context"], task["range_text"])
        except Exception as exc:
            print(f"Worker error: {exc}")
        finally:
            request_queue.task_done()
