import json
import os
import random
import re
import string
from datetime import datetime, timedelta

from bot.config import (
    ACTIVITY_LOGS_FILE,
    BANNED_USERS_FILE,
    CUSTOM_SERVICES_FILE,
    DATA_RANGE_FILE,
    REFERRAL_DATA_FILE,
    USER_DATA_FILE,
    WITHDRAW_DATA_FILE,
)


def get_bangladesh_time() -> datetime:
    return datetime.utcnow() + timedelta(hours=6)


def normalize_number(number) -> str:
    if not number:
        return ""
    return re.sub(r"\D", "", str(number))


def mask_number(number) -> str:
    num_str = str(number)
    if len(num_str) <= 6:
        return num_str
    return num_str[:4] + "****" + num_str[-2:]


def is_valid_bangladesh_number(number) -> bool:
    clean = re.sub(r"\D", "", str(number))
    if len(clean) == 11 and clean.startswith("01"):
        return True
    if len(clean) == 13 and clean.startswith("8801"):
        return True
    return False


def format_balance(balance) -> str:
    try:
        return f"{float(balance):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def get_date_reset_time() -> datetime:
    bd_now = get_bangladesh_time()
    return datetime(bd_now.year, bd_now.month, bd_now.day)


def is_range_request(param) -> bool:
    return bool(re.match(r"^\d+[xX]+$", str(param)))


def is_referral_request(param) -> bool:
    return str(param).isdigit()


def extract_link_and_otp(full_sms):
    if not full_sms:
        return None, None
    otp_match = re.search(r"\b\d{4,8}\b", full_sms)
    otp = otp_match.group(0) if otp_match else None
    link_match = re.search(r"https?://[^\s]+", full_sms)
    link = link_match.group(0) if link_match else None
    return otp, link


def numbers_match(num1, num2) -> bool:
    n1 = re.sub(r"\D", "", str(num1))
    n2 = re.sub(r"\D", "", str(num2))
    if not n1 or not n2:
        return False
    return n1 in n2 or n2 in n1


def detect_service(full_sms: str) -> str:
    if not full_sms:
        return "SMS SERVICE"
    sms_lower = full_sms.lower()
    keywords = {
        "facebook": "FACEBOOK", "fb": "FACEBOOK",
        "instagram": "INSTAGRAM", "insta": "INSTAGRAM",
        "tiktok": "TIKTOK", "twitter": "TWITTER", "x.com": "TWITTER",
        "snapchat": "SNAPCHAT", "snap": "SNAPCHAT",
        "whatsapp": "WHATSAPP", "telegram": "TELEGRAM",
        "discord": "DISCORD", "messenger": "MESSENGER",
        "linkedin": "LINKEDIN", "google": "GOOGLE", "gmail": "GOOGLE",
        "amazon": "AMAZON", "microsoft": "MICROSOFT", "outlook": "MICROSOFT",
        "yahoo": "YAHOO", "paypal": "PAYPAL", "binance": "BINANCE",
        "coinbase": "COINBASE", "spotify": "SPOTIFY", "netflix": "NETFLIX",
        "uber": "UBER", "apple": "APPLE", "icloud": "APPLE",
        "bkash": "BKASH", "nagad": "NAGAD", "stripe": "STRIPE",
        "line": "LINE", "wechat": "WECHAT", "viber": "VIBER",
        "signal": "SIGNAL", "pubg": "PUBG", "free fire": "FREE FIRE",
    }
    for keyword, name in sorted(keywords.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in sms_lower:
            return name
    return "SMS SERVICE"


def _load_json(path: str, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_data(filename=USER_DATA_FILE):
    return _load_json(filename, {})


def save_data(data, filename=USER_DATA_FILE):
    _save_json(filename, data)


def get_user(uid):
    uid = str(uid)
    data = load_data()
    if uid not in data:
        data[uid] = {"user_id": uid, "balance": 0.0, "total_numbers": 0, "referral_count": 0}
        save_data(data)
    return data[uid]


async def update_db_balance(uid, amount):
    uid = str(uid)
    data = load_data()
    if uid in data:
        data[uid]["balance"] = round(data[uid].get("balance", 0.0) + amount, 2)
        save_data(data)
        return data[uid]["balance"]
    return 0.0


def get_all_users():
    return list(load_data(USER_DATA_FILE).keys())


def user_exists(uid):
    return str(uid) in load_data(USER_DATA_FILE)


def load_banned_users():
    return _load_json(BANNED_USERS_FILE, [])


def save_banned_users(banned_list):
    _save_json(BANNED_USERS_FILE, banned_list)


def is_user_banned(uid):
    return str(uid) in load_banned_users()


def ban_user(uid):
    banned = load_banned_users()
    uid_str = str(uid)
    if uid_str not in banned:
        banned.append(uid_str)
        save_banned_users(banned)
        return True
    return False


def unban_user(uid):
    banned = load_banned_users()
    uid_str = str(uid)
    if uid_str in banned:
        banned.remove(uid_str)
        save_banned_users(banned)
        return True
    return False


def load_referral_data():
    return _load_json(REFERRAL_DATA_FILE, {})


def save_referral_data(data):
    _save_json(REFERRAL_DATA_FILE, data)


def update_referral_count(uid, count):
    data = load_referral_data()
    uid_str = str(uid)
    if uid_str not in data:
        data[uid_str] = {"referral_count": 0}
    data[uid_str]["referral_count"] = count
    save_referral_data(data)


def get_referral_count(uid):
    return load_referral_data().get(str(uid), {}).get("referral_count", 0)


def load_range_db():
    return _load_json(DATA_RANGE_FILE, {})


def save_range_db(data):
    _save_json(DATA_RANGE_FILE, data)


def save_number_range_info(uid, number, range_text):
    from bot.utils.country import get_country_info

    db = load_range_db()
    flag, name = get_country_info(number)
    db[normalize_number(number)] = {
        "user_id": str(uid),
        "number": f"+{normalize_number(number)}",
        "range": range_text,
        "country": f"{flag} {name}",
    }
    save_range_db(db)


def load_custom_services():
    return _load_json(CUSTOM_SERVICES_FILE, [])


def save_custom_services(data):
    _save_json(CUSTOM_SERVICES_FILE, data)


def load_withdraw_requests():
    return _load_json(WITHDRAW_DATA_FILE, {})


def save_withdraw_requests(data):
    _save_json(WITHDRAW_DATA_FILE, data)


def generate_payment_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
