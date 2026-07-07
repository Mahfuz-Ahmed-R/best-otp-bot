import re

from bot.api.client import fetch_live_services
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


def _normalize_api_service(svc: dict) -> dict:
    sid = svc.get("sid", "Service")
    raw_ranges = svc.get("ranges", [])
    ranges = []
    for item in raw_ranges:
        if isinstance(item, str):
            ranges.append(_range_to_item(item))
        elif isinstance(item, dict):
            ranges.append(item)
    return {"sid": sid, "ranges": ranges}


async def get_available_services() -> list[dict]:
    """Merge live API services with admin custom services."""
    live = await fetch_live_services()
    services = [_normalize_api_service(s) for s in live]

    custom = load_custom_services()
    if not isinstance(custom, list):
        custom = []

    by_sid = {s.get("sid", "").upper(): s for s in services}
    for svc in custom:
        sid = svc.get("sid", "").upper()
        if not sid:
            continue
        if sid in by_sid:
            existing_ranges = {r.get("range", "").upper() for r in by_sid[sid].get("ranges", [])}
            for r in svc.get("ranges", []):
                rv = r.get("range", "").upper() if isinstance(r, dict) else str(r).upper()
                if rv and rv not in existing_ranges:
                    by_sid[sid]["ranges"].append(r if isinstance(r, dict) else _range_to_item(r))
        else:
            normalized = {
                "sid": svc.get("sid"),
                "ranges": [
                    r if isinstance(r, dict) else _range_to_item(r)
                    for r in svc.get("ranges", [])
                ],
            }
            by_sid[sid] = normalized

    return list(by_sid.values())
