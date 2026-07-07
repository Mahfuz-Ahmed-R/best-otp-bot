import asyncio
import html
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import OTP_GROUP_ID, OTP_RATE, PAID_SMS_FILE
from bot.services.stats import add_otp_received, log_global_activity
from bot.config import CHECK_INTERVAL
from bot.state import active_numbers
from bot.api.client import fetch_success_otps
from bot.utils.country import get_country_info
from bot.utils.helpers import (
    detect_service,
    extract_link_and_otp,
    load_data,
    load_range_db,
    mask_number,
    normalize_number,
    numbers_match,
    save_data,
    update_db_balance,
)


async def monitor_loop(app):
    while True:
        try:
            otps = await fetch_success_otps()
            if otps:
                paid_data = load_data(PAID_SMS_FILE)
                range_db = load_range_db()
                paid_keys = set(paid_data.keys())
                processed = set()

                for otp in otps:
                    num = normalize_number(
                        otp.get("number") or otp.get("phone") or otp.get("to") or ""
                    )
                    full_sms = (
                        otp.get("message")
                        or otp.get("otp")
                        or otp.get("sms")
                        or otp.get("text")
                        or otp.get("msg")
                        or "No SMS Content"
                    )
                    ext_otp, ext_link = extract_link_and_otp(full_sms)
                    otp_code = otp.get("otp_code") or ext_otp
                    if not otp_code and isinstance(full_sms, str):
                        otp_code = ext_otp

                    otp_id = str(otp.get("otp_id", ""))
                    sms_key = otp_id if otp_id else f"{num}_{full_sms}"

                    matched_key = None
                    for active_num in active_numbers:
                        if numbers_match(num, active_num):
                            matched_key = active_num
                            break

                    if matched_key is None or sms_key in paid_keys or sms_key in processed:
                        continue

                    details = active_numbers[matched_key]
                    paid_keys.add(sms_key)
                    processed.add(sms_key)
                    paid_data[sms_key] = {"uid": details["uid"], "otp": otp_code}

                    await update_db_balance(details["uid"], OTP_RATE)
                    add_otp_received(details["uid"])
                    log_global_activity(
                        details["uid"],
                        "OTP_RECEIVED",
                        {"number": matched_key, "otp": otp_code, "sms": full_sms},
                    )

                    num_range = range_db.get(matched_key, {}).get("range", "") or details.get("range", "")
                    country_flag, country_name = get_country_info(matched_key)
                    service_name = detect_service(full_sms)
                    clean_num = matched_key.replace("+", "").strip()
                    safe_sms = html.escape(str(full_sms))
                    safe_otp = html.escape(str(otp_code or "N/A"))

                    link_section = ""
                    if ext_link:
                        link_section = f"<blockquote>🔗 <b>LINK:</b> <a href='{ext_link}'>{ext_link}</a></blockquote>\n"

                    user_msg = (
                        f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                        f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                        f"<blockquote>📞 NUMBER: <code>+{clean_num}</code></blockquote>\n"
                        f"<blockquote>🔑 OTP: <code>{safe_otp}</code></blockquote>\n"
                        f"{link_section}\n"
                        f"<blockquote>📩 FULL SMS:\n<code>{safe_sms}</code></blockquote>\n\n"
                        f"<b>💵 ADD BALANCE FOR {OTP_RATE:.2f} BDT</b>"
                    )

                    group_msg = (
                        f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                        f"<blockquote>📶 RANGE: <code>{num_range}</code></blockquote>\n"
                        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                        f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                        f"<blockquote>📞 NUMBER: <code>+{mask_number(clean_num)}</code></blockquote>\n"
                        f"<blockquote>🔑 OTP: <code>{safe_otp}</code></blockquote>\n"
                        f"{link_section}\n"
                        f"<blockquote>📩 FULL SMS:\n<code>{safe_sms}</code></blockquote>"
                    )

                    try:
                        await app.bot.send_message(details["uid"], user_msg, parse_mode="HTML")
                    except Exception as exc:
                        print(f"User OTP send fail: {exc}")

                    if OTP_GROUP_ID:
                        try:
                            await app.bot.send_message(
                                OTP_GROUP_ID,
                                group_msg,
                                parse_mode="HTML",
                                reply_markup=InlineKeyboardMarkup(
                                    [[InlineKeyboardButton("📢 BOT", url="https://t.me/")]]
                                ),
                            )
                        except Exception as exc:
                            print(f"Group OTP send fail: {exc}")

                    save_data(paid_data, PAID_SMS_FILE)

            now = datetime.now()
            for key in list(active_numbers.keys()):
                entry = active_numbers[key]
                entry.setdefault("timestamp", now)
                if (now - entry["timestamp"]).total_seconds() > 3600:
                    del active_numbers[key]

        except Exception as exc:
            print(f"Monitor error: {exc}")

        await asyncio.sleep(CHECK_INTERVAL)
