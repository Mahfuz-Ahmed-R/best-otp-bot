import html
import re

from bot.config import BOT_NAME, OTP_GROUP_ID, OTP_GROUP_LINK, OTP_RATE, PAID_SMS_FILE
from bot.services.stats import add_otp_received, log_global_activity
from bot.state import active_numbers
from bot.utils.country import get_country_info
from bot.utils.helpers import (
    detect_service,
    extract_link_and_otp,
    load_data,
    load_range_db,
    normalize_number,
    numbers_match,
    save_data,
    update_db_balance,
)
from bot.utils.keyboards import otp_group_keyboard, otp_user_keyboard
from bot.utils.service_icons import service_icon_html

_COUNTRY_SHORT_CODES = {
    "palestine": "PS",
    "montenegro": "ME",
    "guinea": "GN",
    "bangladesh": "BD",
    "india": "IN",
    "pakistan": "PK",
    "nigeria": "NG",
    "kenya": "KE",
    "egypt": "EG",
    "morocco": "MA",
    "algeria": "DZ",
    "tunisia": "TN",
    "cameroon": "CM",
    "ghana": "GH",
    "ivory coast": "CI",
    "united kingdom": "UK",
    "united states": "US",
}


def find_active_number(text: str) -> str | None:
    """Match a phone number from message text to an active allocation."""
    if not text:
        return None

    candidates = set()
    for match in re.findall(r"\+?\d{7,15}", text):
        candidates.add(normalize_number(match))

    for active_num in active_numbers:
        for candidate in candidates:
            if numbers_match(candidate, active_num):
                return active_num

    return None


def _range_label(matched_key: str, details: dict) -> str:
    range_db = load_range_db()
    num_range = range_db.get(matched_key, {}).get("range", "") or details.get("range", "")
    if not num_range and matched_key:
        digits = re.sub(r"\D", "", str(matched_key))
        num_range = (digits[:-3] + "XXX") if len(digits) > 3 else (digits + "XXX")
    return num_range


def _country_short_code(country_name: str) -> str:
    lower_name = str(country_name or "").strip().lower()
    for name, code in _COUNTRY_SHORT_CODES.items():
        if name in lower_name:
            return code
    letters = re.sub(r"[^A-Za-z]", "", country_name or "")
    return (letters[:2] or "XX").upper()


def _format_range_display(range_text: str) -> str:
    raw = str(range_text or "").strip().upper()
    if not raw:
        return "N/A"
    return re.sub(r"[^A-Z0-9X]", "", raw) or "N/A"


def _resolve_service_name(full_sms: str, details: dict) -> str:
    service_name = detect_service(full_sms)
    if service_name == "SMS SERVICE" and details.get("sid"):
        service_name = str(details["sid"]).upper()
    return service_name


def build_otp_user_message(matched_key: str, full_sms: str) -> str:
    details = active_numbers.get(matched_key, {})
    country_flag, _country_name = get_country_info(matched_key)
    service_name = _resolve_service_name(full_sms, details)
    service_logo = service_icon_html(service_name)
    clean_num = matched_key.replace("+", "").strip()
    phone_display = html.escape(f"+{clean_num}")

    return (
        f"<blockquote>{service_logo} {country_flag} "
        f'<a href="tel:{phone_display}">{phone_display}</a> '
        f"<code>#EN</code></blockquote>"
    )


def build_otp_group_message(
    matched_key: str,
    full_sms: str,
    otp_code: str | None,
    ext_link: str | None,
) -> str:
    details = active_numbers.get(matched_key, {})
    num_range = _range_label(matched_key, details)
    country_flag, country_name = get_country_info(matched_key)
    service_name = _resolve_service_name(full_sms, details)

    country_code = _country_short_code(country_name)
    range_code = html.escape(_format_range_display(num_range))
    service_logo = service_icon_html(service_name)
    bot_link = html.escape(OTP_GROUP_LINK, quote=True)
    bot_name = html.escape(BOT_NAME)

    return (
        f'<a href="{bot_link}"><b>{bot_name}</b></a>  <b>OTP</b>\n\n'
        f"{country_flag} {country_code} | {service_logo} <code>{range_code}</code> | 💬 English"
    )


def build_otp_messages(matched_key: str, full_sms: str, otp_code: str | None, ext_link: str | None):
    user_msg = build_otp_user_message(matched_key, full_sms)
    group_msg = build_otp_group_message(matched_key, full_sms, otp_code, ext_link)
    return user_msg, group_msg


async def deliver_otp(
    app,
    matched_key: str,
    full_sms: str,
    otp_code: str | None = None,
    ext_link: str | None = None,
    sms_key: str | None = None,
    *,
    post_to_channel: bool = True,
    reply_chat_id: int | None = None,
    reply_message_id: int | None = None,
) -> bool:
    """Forward OTP to the user (and optionally the OTP channel)."""
    if matched_key not in active_numbers:
        return False

    details = active_numbers[matched_key]
    paid_data = load_data(PAID_SMS_FILE)
    paid_keys = set(paid_data.keys())

    if not otp_code:
        otp_code, ext_link = extract_link_and_otp(full_sms)
    if not ext_link:
        _, ext_link = extract_link_and_otp(full_sms)

    if not sms_key:
        sms_key = f"{matched_key}_{full_sms}"
    if sms_key in paid_keys:
        return False

    paid_data[sms_key] = {"uid": details["uid"], "otp": otp_code}
    save_data(paid_data, PAID_SMS_FILE)

    await update_db_balance(details["uid"], OTP_RATE)
    add_otp_received(details["uid"])
    log_global_activity(
        details["uid"],
        "OTP_RECEIVED",
        {"number": matched_key, "otp": otp_code, "sms": full_sms},
    )

    user_msg, group_msg = build_otp_messages(matched_key, full_sms, otp_code, ext_link)

    try:
        await app.bot.send_message(
            details["uid"],
            user_msg,
            parse_mode="HTML",
            reply_markup=otp_user_keyboard(otp_code or ""),
        )
    except Exception as exc:
        print(f"User OTP send fail: {exc}")

    channel_id = reply_chat_id or OTP_GROUP_ID
    if channel_id and (post_to_channel or reply_chat_id):
        try:
            kwargs = {
                "parse_mode": "HTML",
                "reply_markup": otp_group_keyboard(otp_code or "", OTP_GROUP_LINK),
            }
            if reply_message_id:
                kwargs["reply_to_message_id"] = reply_message_id
            await app.bot.send_message(channel_id, group_msg, **kwargs)
        except Exception as exc:
            print(f"Channel OTP send fail: {exc}")

    return True
