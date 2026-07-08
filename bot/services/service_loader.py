import re

from bot.utils.country import get_country_info
from bot.utils.helpers import load_custom_services


def _range_to_item(range_text: str) -> dict:
    prefix = re.sub(r"[xX]+$", "", str(range_text)).strip()
    prefix_clean = re.sub(r"\D", "", prefix)
    flag, cname = get_country_info(prefix_clean)
    return {
        "range": str(range_text),
        "country": f"{flag} {cname}",
    }


def _normalize_range_item(item) -> dict | None:
    if isinstance(item, str):
        return _range_to_item(item)
    if isinstance(item, dict):
        range_text = str(item.get("range", "")).strip()
        if not range_text:
            return None
        country = str(item.get("country", "")).strip()
        if not country:
            return _range_to_item(range_text)
        return {"range": range_text, "country": country}
    return None


def _normalize_api_service(svc: dict) -> dict:
    sid = str(svc.get("sid", "Service")).strip()
    ranges = []
    for item in svc.get("ranges", []):
        normalized = _normalize_range_item(item)
        if normalized:
            ranges.append(normalized)
    return {"sid": sid, "ranges": ranges}


def _normalize_custom_service(svc: dict) -> dict | None:
    sid = str(svc.get("sid", "")).strip()
    if not sid:
        return None

    ranges = []
    seen = set()
    for item in svc.get("ranges", []):
        normalized = _normalize_range_item(item)
        if not normalized:
            continue
        range_key = normalized["range"].upper()
        if range_key in seen:
            continue
        seen.add(range_key)
        ranges.append(normalized)

    return {"sid": sid, "ranges": ranges}


async def get_available_services() -> list[dict]:
    """Return only the admin-managed services that should be shown to users."""
    custom_raw = load_custom_services()
    if not isinstance(custom_raw, list):
        custom_raw = []

    custom_services = [
        service
        for service in (_normalize_custom_service(item) for item in custom_raw)
        if service and service.get("ranges")
    ]

    return custom_services
