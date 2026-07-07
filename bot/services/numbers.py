import asyncio
import html
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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


def _is_provider_error(res: dict | None) -> bool:
    return bool(res and res.get("error"))


def _allocation_error_text(api_error: dict | None, *, multi: bool) -> str:
    if not api_error:
        title = "Numbers not available." if multi else "No numbers found."
        body = (
            "No numbers in this country right now. Try another service or country."
            if multi
            else "Try a valid range."
        )
        return f"<b>{title}</b>\n\n<blockquote>{body}</blockquote>"
        return f"âŒ <b>{title}</b>\n\n<blockquote>âš ï¸ {body}</blockquote>"

    raw_message = str(api_error.get("error") or "Provider request failed.")
    lower_message = raw_message.lower()
    error_code = api_error.get("error_code")

    if error_code == 2941 or "unauthorized" in lower_message or "expired api key" in lower_message:
        detail = "Panel API authentication failed. Update <code>MAUTHAPI_KEY</code> with a valid working key."
    elif "connection failed" in lower_message:
        detail = "The bot could not reach the provider API. Check server network access and API availability."
    else:
        detail = html.escape(raw_message)

    return f"<b>Provider error.</b>\n\n<blockquote>{detail}</blockquote>"
    return f"âŒ <b>Provider error.</b>\n\n<blockquote>âš ï¸ {detail}</blockquote>"


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


NUMBERS_PER_COUNTRY = 2


async def _fetch_multiple_numbers(
    ranges_list: list[str], count: int = NUMBERS_PER_COUNTRY
) -> tuple[list[dict], dict | None]:
    """Fetch up to `count` unique numbers, rotating through available ranges."""
    if not ranges_list:
        return [], None

    results: list[dict] = []
    seen: set[str] = set()
    range_idx = 0
    max_attempts = max(count * len(ranges_list) * 2, count * 2)
    last_error: dict | None = None

    for _ in range(max_attempts):
        if len(results) >= count:
            break

        batch_size = min(count - len(results), len(ranges_list))
        tasks = [
            fetch_number_async(ranges_list[(range_idx + i) % len(ranges_list)])
            for i in range(batch_size)
        ]
        range_idx += batch_size

        fetched = await asyncio.gather(*tasks)
        for i, res in enumerate(fetched):
            if _is_provider_error(res):
                last_error = res
                if res.get("error_code") == 2941:
                    return results, last_error
                continue
            if not res or not res.get("number"):
                continue
            clean_num = normalize_number(res["number"])
            if not clean_num or clean_num in seen:
                continue
            seen.add(clean_num)
            r_text = ranges_list[(range_idx - batch_size + i) % len(ranges_list)]
            results.append({"num": clean_num, "range": r_text, **res})

    return results, last_error


def _format_multi_number_message(entries: list[dict], sid: str, country_flag: str, country_name: str) -> str:
    otp_lines = []
    for entry in entries:
        if entry.get("otp_now") and entry.get("otp"):
            otp_lines.append(
                f"<blockquote>📞 +{entry['num']}\n"
                f"🔑 OTP: <code>{html.escape(str(entry['otp']))}</code></blockquote>"
            )

    any_instant = any(e.get("otp_now") and e.get("otp") for e in entries)
    if any_instant:
        return (
            f"<b>✅ OTP received</b>\n"
            f"<blockquote>🌍 {country_flag} {html.escape(country_name)}</blockquote>\n\n"
            f"{chr(10).join(otp_lines)}"
        )
    return (
        f"<b>📩 Waiting for SMS...</b>\n"
        f"<blockquote>🌍 {country_flag} {html.escape(country_name)}</blockquote>\n"
        f"<i>Tap a number below to copy it.</i>"
    )


async def fast_allocate_number_multi(query, context, ranges_list, sid, count: int = NUMBERS_PER_COUNTRY):
    uid = query.from_user.id
    if is_user_banned(uid):
        await query.message.edit_text("🚫 YOU ARE BANNED 🚫")
        return

    context.user_data["la_country_ranges"] = ranges_list
    context.user_data["la_sid"] = sid

    try:
        await query.message.edit_text(
            "⚡ <b>ALLOCATING YOUR NUMBERS</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 <i>Fetching {count} numbers... Please wait.</i>",
            parse_mode="HTML",
        )
    except Exception as exc:
        print(f"Loading state error: {exc}")

    entries, api_error = await _fetch_multiple_numbers(ranges_list, count)
    if not entries and api_error:
        await query.message.edit_text(
            _allocation_error_text(api_error, multi=True),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="back_countries",
                            style="danger",
                        )
                    ]
                ]
            ),
        )
        return
    if not entries and api_error:
        await query.message.edit_text(
            _allocation_error_text(api_error, multi=True),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="back_countries",
                            style="danger",
                        )
                    ]
                ]
            ),
        )
        return
    if not entries:
        await query.message.edit_text(
            "❌ <b>Numbers not available.</b>\n\n"
            "<blockquote>⚠️ No numbers in this country right now. Try another service or country.</blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="back_countries",
                            style="danger",
                        )
                    ]
                ]
            ),
        )
        return

    add_number_taken(uid, len(entries))
    last_range[uid] = entries[0]["range"]

    for entry in entries:
        active_numbers[entry["num"]] = {
            "uid": uid,
            "range": entry["range"],
            "sid": sid,
            "timestamp": datetime.now(),
        }
        save_number_range_info(uid, entry["num"], entry["range"])
        if entry.get("otp_now") and entry.get("otp"):
            add_otp_received(uid)

    country_flag, country_name = get_country_info(entries[0]["num"])
    text = _format_multi_number_message(entries, sid, country_flag, country_name)
    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=number_result_keyboard(entries, sid, country_flag),
    )


async def process_auto_number(update: Update, context: ContextTypes.DEFAULT_TYPE, range_text: str):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_user_banned(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING...")
    res = await fetch_number_async(range_text)
    if _is_provider_error(res):
        await status_msg.edit_text(
            _allocation_error_text(res, multi=False),
            parse_mode="HTML",
        )
        return
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

    country_flag, country_name = get_country_info(generated_num)
    sid = active_numbers.get(generated_num, {}).get("sid", "NUMBER")
    text = _format_number_message(generated_num, range_text, res).replace("YOUR NUMBER", "YOUR NUMBER DETAILS")
    entries = [{"num": generated_num, **res}]
    await status_msg.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=number_result_keyboard(entries, sid, country_flag),
    )


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
    api_error = next((r for r in results if _is_provider_error(r)), None)
    if api_error and not any(r and r.get("number") for r in results):
        await status_msg.edit_text(
            _allocation_error_text(api_error, multi=False),
            parse_mode="HTML",
        )
        return
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
    sid = context.user_data.get("la_sid", "NUMBER")
    lines = []
    for entry in entries:
        if entry.get("otp_now") and entry.get("otp"):
            add_otp_received(uid)
            lines.append(
                f"<blockquote>📞 +{entry['num']}\n"
                f"🔑 OTP: <code>{html.escape(str(entry['otp']))}</code></blockquote>"
            )

    any_instant = any(e.get("otp_now") and e.get("otp") for e in entries)
    if any_instant:
        final_text = (
            f"<b>✅ OTP received</b>\n"
            f"<blockquote>🌍 {country_flag} {country_name}</blockquote>\n\n"
            f"{chr(10).join(lines)}"
        )
    else:
        final_text = (
            f"<b>📩 Waiting for SMS...</b>\n"
            f"<blockquote>🌍 {country_flag} {country_name}</blockquote>\n"
            f"<i>Tap a number below to copy it.</i>"
        )
    await status_msg.edit_text(
        final_text,
        parse_mode="HTML",
        reply_markup=number_result_keyboard(entries, sid, country_flag),
    )


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
