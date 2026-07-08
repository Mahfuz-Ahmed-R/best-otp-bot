import json
import os
from datetime import datetime, timedelta

from bot.config import ACTIVITY_LOGS_FILE, STATS_FILE
from bot.utils.helpers import get_bangladesh_time, get_date_reset_time, load_data, save_data


def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)


def add_number_taken(uid, count=1):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    stats[uid].setdefault("numbers_taken", [])
    now = get_bangladesh_time().isoformat()
    for _ in range(count):
        stats[uid]["numbers_taken"].append(now)
    log_global_activity(uid, "NUMBER_TAKEN", {"count": count})
    save_stats(stats)


def add_otp_received(uid):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    stats[uid].setdefault("otps_received", [])
    stats[uid]["otps_received"].append(get_bangladesh_time().isoformat())
    save_stats(stats)


def get_user_stats(uid):
    uid = str(uid)
    user_stats = load_stats().get(uid, {"numbers_taken": [], "otps_received": []})
    now = get_bangladesh_time()
    today_midnight = get_date_reset_time()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    numbers_taken = user_stats.get("numbers_taken", [])
    otps_received = user_stats.get("otps_received", [])

    today_numbers = today_otps = last24h_numbers = last24h_otps = 0
    last7d_numbers = last7d_otps = 0

    for t in numbers_taken:
        try:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight:
                today_numbers += 1
            if dt > last_24h:
                last24h_numbers += 1
            if dt > last_7d:
                last7d_numbers += 1
        except ValueError:
            continue

    for t in otps_received:
        try:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight:
                today_otps += 1
            if dt > last_24h:
                last24h_otps += 1
            if dt > last_7d:
                last7d_otps += 1
        except ValueError:
            continue

    return {
        "total_numbers": len(numbers_taken),
        "total_otps": len(otps_received),
        "today_numbers": today_numbers,
        "today_otps": today_otps,
        "last24h_numbers": last24h_numbers,
        "last24h_otps": last24h_otps,
        "last7d_numbers": last7d_numbers,
        "last7d_otps": last7d_otps,
    }


def _load_activity_logs():
    if not os.path.exists(ACTIVITY_LOGS_FILE):
        with open(ACTIVITY_LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    try:
        with open(ACTIVITY_LOGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(data, list):
        return data

    return []


def _save_activity_logs(logs):
    with open(ACTIVITY_LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4)


def log_global_activity(uid, action, details):
    logs = _load_activity_logs()
    now = get_bangladesh_time()
    logs.append({
        "uid": str(uid),
        "action": action,
        "details": details,
        "timestamp": now.isoformat(),
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S"),
    })
    _save_activity_logs(logs)


def get_global_system_stats():
    stats = load_stats()
    now = get_bangladesh_time()
    today_midnight = datetime(now.year, now.month, now.day)
    last_7d = now - timedelta(days=7)
    total_n = total_o = today_n = today_o = seven_n = seven_o = 0
    for user in stats.values():
        n_list = user.get("numbers_taken", [])
        o_list = user.get("otps_received", [])
        total_n += len(n_list)
        total_o += len(o_list)
        for t in n_list:
            try:
                dt = datetime.fromisoformat(t)
                if dt >= today_midnight:
                    today_n += 1
                if dt >= last_7d:
                    seven_n += 1
            except ValueError:
                continue
        for t in o_list:
            try:
                dt = datetime.fromisoformat(t)
                if dt >= today_midnight:
                    today_o += 1
                if dt >= last_7d:
                    seven_o += 1
            except ValueError:
                continue
    return today_n, today_o, seven_n, seven_o, total_n, total_o
