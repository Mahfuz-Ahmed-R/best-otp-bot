import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_NAME = "BEST OTP BOT"

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api",
)


def _default_mauthapi_key() -> str:
    match = re.search(r"api\.2oo9\.cloud/([^/]+)/", API_BASE_URL)
    return match.group(1) if match else ""


def _normalize_mauthapi_key(raw: str) -> str:
    """Accept a bare key or a full panel API URL pasted by mistake."""
    value = raw.strip()
    if not value:
        return _default_mauthapi_key()
    match = re.search(r"api\.2oo9\.cloud/([^/]+)/", value)
    if match:
        return match.group(1)
    return value


def _env_int(name: str, default: int = 0) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None if default == 0 else default
    try:
        value = int(raw)
    except ValueError:
        return None
    return value or None


MAUTHAPI_KEY = _normalize_mauthapi_key(os.getenv("MAUTHAPI_KEY", ""))

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

OTP_GROUP_ID = _env_int("OTP_GROUP_ID")
OTP_SOURCE_CHANNEL_ID = _env_int("OTP_SOURCE_CHANNEL_ID") or OTP_GROUP_ID
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support")
OTP_GROUP_LINK = os.getenv("OTP_GROUP_LINK", "https://t.me/BestOTP07")

USER_DATA_FILE = str(DATA_DIR / "users.json")
PAID_SMS_FILE = str(DATA_DIR / "paid_sms.json")
STATS_FILE = str(DATA_DIR / "user_stats.json")
REFERRAL_DATA_FILE = str(DATA_DIR / "referral_data.json")
BANNED_USERS_FILE = str(DATA_DIR / "banned_users.json")
WITHDRAW_DATA_FILE = str(DATA_DIR / "withdraw_requests.json")
ACTIVITY_LOGS_FILE = str(DATA_DIR / "activity_logs.json")
DATA_RANGE_FILE = str(DATA_DIR / "datarange.json")
CUSTOM_SERVICES_FILE = str(DATA_DIR / "custom_services.json")

WELCOME_MESSAGE = f"""⚡ **{BOT_NAME}** ⚡
━━━━━━━━━━━━━━━━━━━━━━
🟢 Premium & ⚡ Fast OTP Service 🟢"""

OTP_RATE = float(os.getenv("OTP_RATE", "0.00"))
REFERRAL_PRICE = float(os.getenv("REFERRAL_PRICE", "0"))
MIN_WITHDRAW = float(os.getenv("MIN_WITHDRAW", "50"))
MAX_WITHDRAW = float(os.getenv("MAX_WITHDRAW", "10000"))

CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL", "0.2"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "20"))
