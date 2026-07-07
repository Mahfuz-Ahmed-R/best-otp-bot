import asyncio
import html
from datetime import datetime

from bot.api.client import fetch_success_otps
from bot.config import CHECK_INTERVAL, PAID_SMS_FILE
from bot.services.otp_delivery import deliver_otp
from bot.state import active_numbers
from bot.utils.helpers import extract_link_and_otp, load_data, normalize_number, numbers_match


async def monitor_loop(app):
    while True:
        try:
            otps = await fetch_success_otps()
            if otps:
                paid_data = load_data(PAID_SMS_FILE)
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

                    otp_id = str(otp.get("otp_id", ""))
                    sms_key = otp_id if otp_id else f"{num}_{full_sms}"

                    matched_key = None
                    for active_num in active_numbers:
                        if numbers_match(num, active_num):
                            matched_key = active_num
                            break

                    if matched_key is None or sms_key in paid_keys or sms_key in processed:
                        continue

                    processed.add(sms_key)
                    await deliver_otp(
                        app,
                        matched_key,
                        str(full_sms),
                        otp_code=otp_code,
                        ext_link=ext_link,
                        sms_key=sms_key,
                        post_to_channel=True,
                    )

            now = datetime.now()
            for key in list(active_numbers.keys()):
                entry = active_numbers[key]
                entry.setdefault("timestamp", now)
                if (now - entry["timestamp"]).total_seconds() > 3600:
                    del active_numbers[key]

        except Exception as exc:
            print(f"Monitor error: {exc}")

        await asyncio.sleep(CHECK_INTERVAL)
