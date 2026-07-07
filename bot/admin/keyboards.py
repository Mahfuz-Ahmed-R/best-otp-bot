import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import BOT_NAME
from bot.services.stats import load_stats
from bot.utils.helpers import (
    get_all_users,
    load_banned_users,
    load_custom_services,
)
from bot.utils.text import make_bold_unicode


def get_grouped_countries_for_service(service):
    grouped = {}
    for r in service.get("ranges", []):
        r_text = r.get("range", "")
        country_display = r.get("country", "")

        match = re.match(r"^([^\w\s]*)\s*(.*)$", country_display)
        if match:
            flag = match.group(1).strip()
            cname = match.group(2).strip()
        else:
            flag = "🌍"
            cname = "Unknown"

        if not cname:
            cname = "Unknown"

        if cname not in grouped:
            grouped[cname] = {"flag": flag, "ranges": []}
        if r_text not in grouped[cname]["ranges"]:
            grouped[cname]["ranges"].append(r_text)
    return grouped


def build_admin_main_inline_keyboard():
    buttons = [
        [InlineKeyboardButton(make_bold_unicode("👥 USER MANAGEMENT"), callback_data="adm_menu_user_mgnt", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("⚙️ SYSTEM CONFIGURATION"), callback_data="adm_menu_sys_config", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("🛠️ MANAGE SERVICES"), callback_data="manage_svc_back_to_list", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("🔙 BACK TO MAIN MENU"), callback_data="adm_menu_back_to_main", style="danger")],
    ]
    return InlineKeyboardMarkup(buttons)


def build_user_management_inline_keyboard():
    buttons = [
        [InlineKeyboardButton(make_bold_unicode("📢 BROADCAST TO ALL"), callback_data="adm_usermgnt_broadcast", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("🆔 GET ALL USER ID"), callback_data="adm_usermgnt_get_ids", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("💰 ALL USER BALANCE"), callback_data="adm_usermgnt_all_balance", style="primary")],
        [InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_back_to_admin", style="danger")],
    ]
    return InlineKeyboardMarkup(buttons)


def build_system_config_inline_keyboard():
    buttons = [
        [
            InlineKeyboardButton(make_bold_unicode("📈 SYSTEM STATS"), callback_data="adm_sys_stats", style="primary"),
            InlineKeyboardButton(make_bold_unicode("👤 USER CHECK"), callback_data="adm_sys_user_check", style="primary"),
        ],
        [
            InlineKeyboardButton(make_bold_unicode("⛔ BAN USER"), callback_data="adm_sys_ban", style="danger"),
            InlineKeyboardButton(make_bold_unicode("🔓 UNBAN USER"), callback_data="adm_sys_unban", style="success"),
        ],
        [InlineKeyboardButton(make_bold_unicode("📜 BANNED LIST"), callback_data="adm_sys_banned_list", style="primary")],
        [
            InlineKeyboardButton(make_bold_unicode("➕ ADD BALANCE"), callback_data="adm_sys_add_bal", style="success"),
            InlineKeyboardButton(make_bold_unicode("➖ REMOVE BALANCE"), callback_data="adm_sys_rem_bal", style="danger"),
        ],
        [InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_back_to_admin", style="danger")],
    ]
    return InlineKeyboardMarkup(buttons)


def build_manage_services_inline_keyboard():
    custom_svcs = load_custom_services()
    buttons = []
    for s in custom_svcs:
        sid = s.get("sid", "UNKNOWN")
        buttons.append(
            [InlineKeyboardButton(make_bold_unicode(f"📁 {sid.upper()}"), callback_data=f"manage_svc_view_{sid}", style="primary")]
        )
    buttons.append([InlineKeyboardButton(make_bold_unicode("➕ ADD SERVICE"), callback_data="manage_svc_add", style="success")])
    buttons.append([InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_back_to_admin", style="danger")])
    return InlineKeyboardMarkup(buttons)


def build_service_detail_keyboard(service_name):
    custom_svcs = load_custom_services()
    target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == service_name.upper()), None)
    if not target_svc:
        return None

    grouped = get_grouped_countries_for_service(target_svc)
    buttons = []

    for cname, info in grouped.items():
        flag = info["flag"]
        buttons.append(
            [InlineKeyboardButton(make_bold_unicode(f"{flag} {cname.upper()}"), callback_data=f"manage_svc_country_view_{service_name}_{cname}", style="primary")]
        )

    buttons.append([
        InlineKeyboardButton(make_bold_unicode("➕ ADD RANGE"), callback_data=f"manage_svc_add_range_{service_name}", style="success"),
        InlineKeyboardButton(make_bold_unicode("✏️ RENAME"), callback_data=f"manage_svc_rename_init_{service_name}", style="primary"),
    ])
    buttons.append([
        InlineKeyboardButton(make_bold_unicode("🗑️ DELETE SERVICE"), callback_data=f"manage_svc_delete_init_{service_name}", style="danger"),
    ])
    buttons.append([InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="manage_svc_back_to_list", style="danger")])
    return InlineKeyboardMarkup(buttons)


def build_country_detail_keyboard(service_name, country_name):
    custom_svcs = load_custom_services()
    target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == service_name.upper()), None)
    if not target_svc:
        return None

    grouped = get_grouped_countries_for_service(target_svc)
    info = grouped.get(country_name, {"flag": "🌍", "ranges": []})

    buttons = []
    for r_val in info["ranges"]:
        buttons.append([
            InlineKeyboardButton(make_bold_unicode(f"❌ {r_val}"), callback_data=f"manage_svc_delete_range_{service_name}_{country_name}_{r_val}", style="danger"),
            InlineKeyboardButton(make_bold_unicode("✏️ EDIT"), callback_data=f"manage_svc_edit_range_init_{service_name}_{country_name}_{r_val}", style="primary"),
        ])

    buttons.append([
        InlineKeyboardButton(make_bold_unicode("➕ ADD RANGE"), callback_data=f"manage_svc_add_range_{service_name}_{country_name}", style="success"),
        InlineKeyboardButton(make_bold_unicode("✏️ RENAME COUNTRY"), callback_data=f"manage_svc_rename_country_init_{service_name}_{country_name}", style="primary"),
    ])
    buttons.append([InlineKeyboardButton(make_bold_unicode("🗑️ DELETE COUNTRY"), callback_data=f"manage_svc_delete_country_confirm_{service_name}_{country_name}", style="danger")])
    buttons.append([InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data=f"manage_svc_view_{service_name}", style="primary")])
    return InlineKeyboardMarkup(buttons)


def get_admin_panel_text():
    users_list = get_all_users()
    users = len(users_list)
    banned = len(load_banned_users())

    custom_svcs = load_custom_services()
    total_ranges = sum(len(s.get("ranges", [])) for s in custom_svcs)

    stats_data = load_stats()
    total_otps = 0
    for u in stats_data.values():
        total_otps += len(u.get("otps_received", []))

    text = (
        "👑 <b>ADMIN CONTROL PANEL</b> 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>REAL-TIME DATABASE STATS</b>\n\n"
        f"👥 <b>Total Users:</b> <code>{users}</code>\n"
        f"📶 <b>Active Ranges:</b> <code>{total_ranges}</code>\n"
        f"🔑 <b>Processed OTPs:</b> <code>{total_otps}</code>\n"
        f"🚫 <b>Banned Accounts:</b> <code>{banned}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <i>{BOT_NAME} • Live & Operating</i>"
    )
    return text
