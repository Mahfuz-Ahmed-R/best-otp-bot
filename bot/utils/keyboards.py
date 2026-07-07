from bot.config import ADMIN_IDS
from bot.utils.text import make_bold_unicode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=f"📞 {make_bold_unicode('GET NUMBER')}")],
        [
            KeyboardButton(text=f"👥 {make_bold_unicode('REFER AND EARN')}"),
            KeyboardButton(text=f"👤 {make_bold_unicode('PROFILE')}"),
        ],
        [KeyboardButton(text=f"🏆 {make_bold_unicode('LEADERBOARD')}")],
        [KeyboardButton(text=f"💬 {make_bold_unicode('SUPPORT')}")],
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton(text=f"⚙️ {make_bold_unicode('ADMIN PANEL')} ⚙️")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(f"❌ {make_bold_unicode('CANCEL')}")]],
        resize_keyboard=True,
    )


def withdraw_method_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(f"📱 {make_bold_unicode('BKASH')}"),
                KeyboardButton(f"💵 {make_bold_unicode('NAGAD')}"),
            ],
            [
                KeyboardButton(f"🚀 {make_bold_unicode('ROCKET')}"),
                KeyboardButton(f"🏦 {make_bold_unicode('BINANCE')}"),
            ],
            [KeyboardButton(f"❌ {make_bold_unicode('CANCEL')}")],
        ],
        resize_keyboard=True,
    )


def number_result_keyboard() -> InlineKeyboardMarkup:
    from bot.config import OTP_GROUP_LINK

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 SAME RANGE", callback_data="same_range")],
            [InlineKeyboardButton("📢 OTP GROUP", url=OTP_GROUP_LINK)],
        ]
    )


def build_services_keyboard(services) -> InlineKeyboardMarkup:
    buttons = []
    for i, svc in enumerate(services):
        sid = svc.get("sid", f"Service {i + 1}")
        count = len(svc.get("ranges", []))
        buttons.append(
            InlineKeyboardButton(f"🚀 {sid} ({count})", callback_data=f"svc_{i}")
        )
    rows = [buttons[j : j + 2] for j in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def build_countries_keyboard(ranges, service_idx: int) -> InlineKeyboardMarkup:
    from bot.utils.country import clean_country_display, get_country_info
    import re

    btns = []
    seen = {}
    for i, item in enumerate(ranges[:24]):
        r_text = item.get("range", "") if isinstance(item, dict) else str(item)
        country_display = item.get("country", "") if isinstance(item, dict) else ""
        if not country_display:
            prefix = re.sub(r"[xX]+$", "", str(r_text)).strip()
            prefix_clean = re.sub(r"\D", "", prefix)
            flag, cname = get_country_info(prefix_clean)
            country_display = f"{flag} {cname}"
        label = country_display
        if label not in seen:
            seen[label] = i
            btns.append(InlineKeyboardButton(label, callback_data=f"rng_{i}"))
    rows = [btns[j : j + 2] for j in range(0, len(btns), 2)]
    rows.append([InlineKeyboardButton("◀️ BACK", callback_data="back_services")])
    return InlineKeyboardMarkup(rows)
