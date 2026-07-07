from bot.config import ADMIN_IDS
from bot.utils.service_icons import make_service_button
from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _service_header_button(sid: str) -> InlineKeyboardButton:
    service_label = str(sid or "SERVICE").upper()
    button = make_service_button(
        service_label,
        callback_data="noop_service",
        style="success",
    )
    return button


def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📱 GET NUMBER", style="primary")],
        [
            KeyboardButton(text="📊 TRAFFIC", style="success"),
            KeyboardButton(text="🔐 2FA ONLINE", style="primary"),
        ],
        [KeyboardButton(text="👥 SUPPORT", style="primary")],
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton(text="⚙️ ADMIN PANEL", style="primary")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ CANCEL", style="danger")]],
        resize_keyboard=True,
    )


def withdraw_method_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("📱 BKASH", style="primary"),
                KeyboardButton("💵 NAGAD", style="primary"),
            ],
            [
                KeyboardButton("🚀 ROCKET", style="primary"),
                KeyboardButton("🏦 BINANCE", style="primary"),
            ],
            [KeyboardButton("❌ CANCEL", style="danger")],
        ],
        resize_keyboard=True,
    )


def number_result_keyboard(
    entries: list[dict] | None = None,
    sid: str = "",
    country_flag: str = "",
) -> InlineKeyboardMarkup:
    from bot.config import OTP_GROUP_LINK

    rows: list[list[InlineKeyboardButton]] = []
    rows.append([_service_header_button(sid)])

    for entry in entries or []:
        num = str(entry.get("num", "")).strip()
        if not num:
            continue
        flag = country_flag or "📞"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{flag} 📋 +{num}",
                    copy_text=CopyTextButton(text=f"+{num}"),
                    style="primary",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🔄 Change Number",
                callback_data="refresh_numbers",
                style="danger",
            ),
            InlineKeyboardButton(
                "🛡️ OTP Group",
                url=OTP_GROUP_LINK,
                style="primary",
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                "❌ Close",
                callback_data="close_numbers",
                style="danger",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_services_keyboard(services) -> InlineKeyboardMarkup:
    buttons = [
        make_service_button(
            str(svc.get("sid", f"Service {i + 1}")),
            callback_data=f"svc_{i}",
            style="primary",
        )
        for i, svc in enumerate(services)
    ]
    rows = [[button] for button in buttons]
    rows.append(
        [
            InlineKeyboardButton(
                "❌ Close",
                callback_data="close_services",
                style="danger",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def otp_user_keyboard(otp_code: str) -> InlineKeyboardMarkup:
    otp_text = str(otp_code or "N/A").strip()
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🛡️ 📋 {otp_text}",
                    copy_text=CopyTextButton(text=otp_text),
                    style="success",
                )
            ]
        ]
    )


def otp_group_keyboard(otp_code: str, bot_link: str) -> InlineKeyboardMarkup:
    otp_text = str(otp_code or "N/A").strip()
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🛡️ 📋 {otp_text}",
                    copy_text=CopyTextButton(text=otp_text),
                    style="success",
                ),
                InlineKeyboardButton(
                    "😍 Number",
                    url=bot_link,
                    style="primary",
                ),
            ]
        ]
    )


def build_countries_keyboard(ranges, service_idx: int) -> InlineKeyboardMarkup:
    from bot.utils.country import clean_country_display, get_country_info
    import re

    btns = []
    seen = {}
    for i, item in enumerate(ranges):
        r_text = item.get("range", "") if isinstance(item, dict) else str(item)
        country_display = item.get("country", "") if isinstance(item, dict) else ""
        if not country_display:
            prefix = re.sub(r"[xX]+$", "", str(r_text)).strip()
            prefix_clean = re.sub(r"\D", "", prefix)
            flag, cname = get_country_info(prefix_clean)
            country_display = f"{flag} {cname}"
        label = " ".join(str(country_display).split())
        label_key = clean_country_display(label)
        if label_key not in seen:
            seen[label_key] = i
            btns.append(
                InlineKeyboardButton(
                    label,
                    callback_data=f"rng_{i}",
                    style="success",
                )
            )
    rows = [[button] for button in btns]
    rows.append(
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_services",
                style="danger",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)
