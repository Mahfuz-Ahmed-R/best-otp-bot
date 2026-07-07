import json
import os
from pathlib import Path

from telegram import InlineKeyboardButton

from bot.config import DATA_DIR

# Verified from t.me/addemoji/logos_td (Social Media Icons pack).
DEFAULT_SERVICE_ICON_IDS = {
    "INSTAGRAM": "5454384461900689212",
    "FACEBOOK": "5456624751202019469",
    "WHATSAPP": "5460811944883660881",
    "TELEGRAM": "5460675841665019102",
    "YOUTUBE": "5456489236393895850",
    "TWITTER": "5458676268100757124",
    "TIKTOK": "5456282961999570188",
    "SNAPCHAT": "5460725813609506318",
    "DISCORD": "5463310026712032864",
    "PINTEREST": "5458489673246583528",
    "APPLE": "5460647142693547014",
}

SERVICE_EMOJI_FALLBACKS = {
    "INSTAGRAM": "📸",
    "FACEBOOK": "📘",
    "WHATSAPP": "💬",
    "TELEGRAM": "✈️",
    "TIKTOK": "🎵",
    "TWITTER": "🐦",
    "GOOGLE": "🔍",
    "GMAIL": "📧",
    "DISCORD": "🎮",
    "SNAPCHAT": "👻",
    "MESSENGER": "💬",
    "LINKEDIN": "💼",
    "MICROSOFT": "🪟",
    "OUTLOOK": "📨",
    "YAHOO": "📮",
    "PAYPAL": "💳",
    "BINANCE": "💰",
    "COINBASE": "🪙",
    "SPOTIFY": "🎧",
    "NETFLIX": "🎬",
    "UBER": "🚗",
    "APPLE": "🍎",
    "BKASH": "📱",
    "NAGAD": "💵",
    "AMAZON": "📦",
    "SIGNAL": "🔒",
    "VIBER": "📞",
    "LINE": "💚",
    "WECHAT": "💬",
    "PUBG": "🎮",
    "FREE FIRE": "🔥",
}

_ICON_IDS_FILE = DATA_DIR / "service_icon_ids.json"
_icon_ids_cache: dict[str, str] | None = None


def _load_icon_ids() -> dict[str, str]:
    global _icon_ids_cache
    if _icon_ids_cache is not None:
        return _icon_ids_cache

    ids = {k.upper(): v for k, v in DEFAULT_SERVICE_ICON_IDS.items()}

    if _ICON_IDS_FILE.exists():
        try:
            raw = json.loads(_ICON_IDS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if value:
                        ids[str(key).upper()] = str(value)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    for env_key, service in (
        ("INSTAGRAM_EMOJI_ID", "INSTAGRAM"),
        ("FACEBOOK_EMOJI_ID", "FACEBOOK"),
    ):
        value = os.getenv(env_key, "").strip()
        if value:
            ids[service] = value

    _icon_ids_cache = ids
    return ids


def get_service_icon_id(sid: str) -> str | None:
    return _load_icon_ids().get(str(sid).upper())


def get_service_emoji(sid: str) -> str:
    return SERVICE_EMOJI_FALLBACKS.get(str(sid).upper(), "📱")


def service_icon_html(sid: str) -> str:
    """HTML snippet for inline custom service logo in OTP group posts."""
    service_label = str(sid).upper()
    emoji = get_service_emoji(service_label)
    icon_id = get_service_icon_id(service_label)
    if icon_id:
        return f'<tg-emoji emoji-id="{icon_id}">{emoji}</tg-emoji>'
    return emoji


def make_service_button(
    sid: str,
    *,
    callback_data: str,
    style: str = "primary",
) -> InlineKeyboardButton:
    service_label = str(sid).upper()
    icon_id = get_service_icon_id(service_label)
    if icon_id:
        return InlineKeyboardButton(
            service_label,
            callback_data=callback_data,
            style=style,
            icon_custom_emoji_id=icon_id,
        )
    return InlineKeyboardButton(
        f"{get_service_emoji(service_label)} {service_label}",
        callback_data=callback_data,
        style=style,
    )
