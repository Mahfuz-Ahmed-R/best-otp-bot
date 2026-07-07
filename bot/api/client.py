import re
from typing import Any

from bot.state import API_ENDPOINTS, client_async


def _api_ok(payload: dict) -> bool:
    meta = payload.get("meta") or {}
    return meta.get("code") == 200 or meta.get("status") == "ok"


async def fetch_number(rid: str) -> dict | None:
    """Allocate a number from the panel API."""
    try:
        response = await client_async.post(API_ENDPOINTS["getnum"], json={"rid": rid})
        if response.status_code != 200:
            return None

        data = response.json()
        if not _api_ok(data):
            return None

        info = data.get("data") or {}
        number = (
            info.get("no_plus_number")
            or info.get("national_number")
            or info.get("full_number")
            or info.get("number")
        )
        if not number:
            return None

        return {
            "number": str(number).lstrip("+"),
            "country": info.get("country"),
            "operator": info.get("operator"),
            "otp_now": False,
            "otp": None,
            "sms": None,
        }
    except Exception as exc:
        print(f"fetch_number error ({rid}): {exc}")
        return None


async def fetch_live_services() -> list[dict[str, Any]]:
    """Fetch live services and ranges from the panel."""
    try:
        response = await client_async.get(API_ENDPOINTS["liveaccess"])
        if response.status_code != 200:
            return []

        payload = response.json()
        if not _api_ok(payload):
            return []

        services = (payload.get("data") or {}).get("services") or []
        return services if isinstance(services, list) else []
    except Exception as exc:
        print(f"fetch_live_services error: {exc}")
        return []


async def fetch_success_otps() -> list[dict[str, Any]]:
    """Fetch newly received OTP messages."""
    try:
        response = await client_async.get(API_ENDPOINTS["success_otp"])
        if response.status_code != 200:
            return []

        payload = response.json()
        if not _api_ok(payload):
            return []

        otps = (payload.get("data") or {}).get("otps") or []
        return otps if isinstance(otps, list) else []
    except Exception as exc:
        print(f"fetch_success_otps error: {exc}")
        return []


async def fetch_console() -> list[dict[str, Any]]:
    """Fetch recent console hits (admin/debug)."""
    try:
        response = await client_async.get(API_ENDPOINTS["console"])
        if response.status_code != 200:
            return []

        payload = response.json()
        if not _api_ok(payload):
            return []

        hits = (payload.get("data") or {}).get("hits") or []
        return hits if isinstance(hits, list) else []
    except Exception as exc:
        print(f"fetch_console error: {exc}")
        return []


def normalize_rid(rid: str) -> str:
    """Strip XXX suffix if API expects digits-only range id."""
    rid = str(rid).strip()
    if re.match(r"^\d+[xX]{3}$", rid):
        return re.sub(r"[xX]+$", "", rid)
    return rid
