import io
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.admin.keyboards import (
    build_admin_main_inline_keyboard,
    build_country_detail_keyboard,
    build_manage_services_inline_keyboard,
    build_service_detail_keyboard,
    build_system_config_inline_keyboard,
    build_user_management_inline_keyboard,
    get_admin_panel_text,
    get_grouped_countries_for_service,
)
from bot.config import USER_DATA_FILE
from bot.services.stats import get_global_system_stats
from bot.utils.helpers import (
    get_all_users,
    load_banned_users,
    load_custom_services,
    load_data,
    save_custom_services,
)
from bot.utils.keyboards import is_admin, main_keyboard
from bot.utils.text import make_bold_unicode


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin inline callbacks (adm_*, manage_svc_*). Returns True if handled."""
    query = update.callback_query
    data = query.data
    uid = query.from_user.id

    if not data.startswith("adm_") and not data.startswith("manage_svc_"):
        return False

    if not is_admin(uid):
        await query.answer("Admin only.", show_alert=True)
        return True

    if data == "adm_menu_back_to_admin":
        await query.message.edit_text(
            get_admin_panel_text(),
            parse_mode="HTML",
            reply_markup=build_admin_main_inline_keyboard(),
        )
        return True

    if data == "adm_menu_back_to_main":
        await query.message.delete()
        await context.bot.send_message(
            chat_id=uid,
            text="🔙 Returned to main user panel.",
            reply_markup=main_keyboard(uid),
        )
        return True

    if data == "adm_menu_user_mgnt":
        await query.message.edit_text(
            "👥 <b>USER MANAGEMENT PANEL</b>\n───────────────────\nSelect an action from below:",
            parse_mode="HTML",
            reply_markup=build_user_management_inline_keyboard(),
        )
        return True

    if data == "adm_menu_sys_config":
        await query.message.edit_text(
            "⚙️ <b>SYSTEM CONFIGURATION PANEL</b>\n───────────────────\nSelect an action from below:",
            parse_mode="HTML",
            reply_markup=build_system_config_inline_keyboard(),
        )
        return True

    if data == "adm_usermgnt_broadcast":
        context.user_data["broadcast_mode"] = True
        await query.message.edit_text(
            "📢 <b>ADMIN BROADCAST SYSTEM</b>\n───────────────────\n"
            "💬 Please send the message (Text/Photo/Video/Document etc.) - which will be sent to all users with a professional notification header.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_user_mgnt", style="danger")],
            ]),
        )
        return True

    if data == "adm_usermgnt_get_ids":
        users = get_all_users()
        if users:
            content = "\n".join(f"{i}. {u}" for i, u in enumerate(users, 1))
            f = io.BytesIO(content.encode())
            f.name = f"ALL_USERS_{len(users)}.txt"
            await context.bot.send_document(chat_id=uid, document=f, caption=f"👥 Total Users: {len(users)}")
        else:
            await query.message.reply_text("No users found.")
        return True

    if data == "adm_usermgnt_all_balance":
        user_db = load_data(USER_DATA_FILE)
        if user_db:
            total_bal = sum(v.get("balance", 0) for v in user_db.values())
            lines = [f"{i}. {uid_}: {v.get('balance', 0):.2f} BDT" for i, (uid_, v) in enumerate(user_db.items(), 1)]
            content = f"💰 TOTAL BALANCE: {total_bal:.2f} BDT\n\n" + "\n".join(lines)
            f = io.BytesIO(content.encode())
            f.name = f"BALANCES_{total_bal:.0f}.txt"
            await context.bot.send_document(chat_id=uid, document=f, caption=f"💵 Total Balance: {total_bal:.2f} BDT")
        else:
            await query.message.reply_text("No data.")
        return True

    if data == "adm_sys_stats":
        t_n, t_o, s_n, s_o, tot_n, tot_o = get_global_system_stats()
        msg = (
            f"📊 <b>SYSTEM STATUS</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ <b>TODAY</b>\n📱 NUMBERS: {t_n}\n🔑 OTPS: {t_o}\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n📱 NUMBERS: {s_n}\n🔑 OTPS: {s_o}\n\n"
            f"🌐 <b>ALL TIME</b>\n📱 NUMBERS: {tot_n}\n🔑 OTPS: {tot_o}"
        )
        await query.message.edit_text(
            msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_user_check":
        context.user_data["mode"] = "input_user_id"
        await query.message.edit_text(
            "🔍 <b>USER STATUS CHECK</b>\n───────────────────\nPlease send the target Telegram ID:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_ban":
        context.user_data["admin_ban_mode"] = True
        await query.message.edit_text(
            "🚫 <b>BAN USER</b>\n───────────────────\nPlease send the Telegram ID to BAN:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_unban":
        context.user_data["admin_unban_mode"] = True
        await query.message.edit_text(
            "🔓 <b>UNBAN USER</b>\n───────────────────\nPlease send the Telegram ID to UNBAN:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_banned_list":
        banned_list = load_banned_users()
        if not banned_list:
            await query.message.edit_text(
                "📜 NO BANNED USERS.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_sys_config", style="danger")],
                ]),
            )
            return True
        text = "📜 <b>BANNED USER LIST</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, b_id in enumerate(banned_list, 1):
            text += f"{i}. <code>{b_id}</code>\n"
        text += f"\n📊 Total: {len(banned_list)}"
        await query.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("🔙 BACK"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_add_bal":
        context.user_data["add_balance_mode"] = True
        await query.message.edit_text(
            "💰 <b>ADD BALANCE</b>\n───────────────────\nPlease send the Telegram ID to add balance:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "adm_sys_rem_bal":
        context.user_data["remove_balance_mode"] = True
        await query.message.edit_text(
            "💸 <b>REMOVE BALANCE</b>\n───────────────────\nPlease send the Telegram ID to remove balance:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="adm_menu_sys_config", style="danger")],
            ]),
        )
        return True

    if data == "manage_svc_back_to_list":
        await query.message.edit_text(
            "⚙️ MANAGE SERVICES\n"
            "───────────────────\n"
            "SELECT A SERVICE:",
            reply_markup=build_manage_services_inline_keyboard(),
        )
        return True

    if data == "manage_svc_add":
        context.user_data["admin_state"] = "waiting_for_add_service_name_inline"
        await query.message.edit_text(
            "📝 <b>Send the new service name (e.g. FACEBOOK):</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data="manage_svc_back_to_list", style="danger")],
            ]),
        )
        return True

    if data.startswith("manage_svc_rename_init_"):
        svc_name = data.replace("manage_svc_rename_init_", "")
        context.user_data["admin_state"] = "waiting_for_rename_service_inline"
        context.user_data["temp_target_service"] = svc_name
        await query.message.edit_text(
            f"✏️ <b>RENAME SERVICE: {svc_name.upper()}</b>\n───────────────────\n"
            f"Please send the new name for this service:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=f"manage_svc_view_{svc_name}", style="danger")],
            ]),
        )
        return True

    if data.startswith("manage_svc_delete_init_"):
        svc_name = data.replace("manage_svc_delete_init_", "")
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(make_bold_unicode("✅ CONFIRM"), callback_data=f"manage_svc_delete_do_{svc_name}", style="danger"),
                InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=f"manage_svc_view_{svc_name}", style="primary"),
            ],
        ])
        await query.message.edit_text(
            f"🗑️ <b>Are you sure you want to delete service {svc_name.upper()} and all of its countries/ranges?</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return True

    if data.startswith("manage_svc_delete_do_"):
        svc_name = data.replace("manage_svc_delete_do_", "")
        custom_svcs = load_custom_services()
        custom_svcs = [s for s in custom_svcs if s.get("sid", "").upper() != svc_name.upper()]
        save_custom_services(custom_svcs)
        await query.answer(f"Deleted {svc_name}", show_alert=True)
        await query.message.edit_text(
            "⚙️ MANAGE SERVICES\n"
            "───────────────────\n"
            "SELECT A SERVICE:",
            reply_markup=build_manage_services_inline_keyboard(),
        )
        return True

    if data.startswith("manage_svc_view_"):
        svc_name = data.replace("manage_svc_view_", "")
        kb = build_service_detail_keyboard(svc_name)
        if not kb:
            await query.answer("Service not found!", show_alert=True)
            return True
        await query.message.edit_text(
            f"📁 SERVICE: <b>{svc_name.upper()}</b>\n"
            f"───────────────────\n"
            f"SELECT A COUNTRY TO MANAGE RANGES:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return True

    if data.startswith("manage_svc_country_view_"):
        parts = data.replace("manage_svc_country_view_", "").split("_", 1)
        svc_name = parts[0]
        country_name = parts[1]

        custom_svcs = load_custom_services()
        target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)
        if not target_svc:
            await query.answer("Service not found!", show_alert=True)
            return True

        grouped = get_grouped_countries_for_service(target_svc)
        info = grouped.get(country_name, {"flag": "🌍", "ranges": []})
        flag = info["flag"]
        kb = build_country_detail_keyboard(svc_name, country_name)
        await query.message.edit_text(
            f"{flag} RANGES → {svc_name.upper()} → {country_name.upper()}\n"
            f"───────────────────\n"
            f"TAP TO DELETE / EDIT:",
            reply_markup=kb,
        )
        return True

    if data.startswith("manage_svc_add_range_"):
        parts = data.replace("manage_svc_add_range_", "").split("_", 1)
        svc_name = parts[0]
        country_name = parts[1] if len(parts) > 1 else None

        context.user_data["admin_state"] = "waiting_for_add_range_inline"
        context.user_data["temp_target_service"] = svc_name
        context.user_data["temp_target_country"] = country_name

        cancel_cb = f"manage_svc_country_view_{svc_name}_{country_name}" if country_name else f"manage_svc_view_{svc_name}"
        await query.message.edit_text(
            f"📶 <b>SERVICE: {svc_name.upper()}</b>\n"
            f"───────────────────\n"
            f"Please send the new range value (e.g. <code>23672XXX</code>):\n"
            f"<i>(Country and flag will be auto-detected instantly)</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=cancel_cb, style="danger")],
            ]),
        )
        return True

    if data.startswith("manage_svc_delete_range_"):
        parts = data.replace("manage_svc_delete_range_", "").rsplit("_", 2)
        if len(parts) < 3:
            await query.answer("Invalid request!", show_alert=True)
            return True
        svc_name, country_name, range_val = parts[0], parts[1], parts[2]

        custom_svcs = load_custom_services()
        target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)
        if target_svc:
            target_svc["ranges"] = [
                r for r in target_svc.get("ranges", []) if r.get("range", "").upper() != range_val.upper()
            ]
            save_custom_services(custom_svcs)
            await query.answer(f"Deleted range {range_val}", show_alert=True)

            grouped = get_grouped_countries_for_service(target_svc)
            if country_name in grouped:
                kb = build_country_detail_keyboard(svc_name, country_name)
                flag = grouped[country_name]["flag"]
                await query.message.edit_text(
                    f"{flag} RANGES → {svc_name.upper()} → {country_name.upper()}\n"
                    f"───────────────────\n"
                    f"TAP TO DELETE / EDIT:",
                    reply_markup=kb,
                )
            else:
                kb = build_service_detail_keyboard(svc_name)
                await query.message.edit_text(
                    f"📁 SERVICE: <b>{svc_name.upper()}</b>\n"
                    f"───────────────────\n"
                    f"SELECT A COUNTRY TO MANAGE RANGES:",
                    parse_mode="HTML",
                    reply_markup=kb,
                )
        return True

    if data.startswith("manage_svc_delete_country_confirm_"):
        parts = data.replace("manage_svc_delete_country_confirm_", "").split("_", 1)
        svc_name = parts[0]
        country_name = parts[1]
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(make_bold_unicode("✅ CONFIRM"), callback_data=f"manage_svc_delete_country_do_{svc_name}_{country_name}", style="danger"),
                InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=f"manage_svc_country_view_{svc_name}_{country_name}", style="primary"),
            ],
        ])
        await query.message.edit_text(
            f"🗑️ <b>Are you sure you want to delete {country_name.upper()} and all of its ranges from {svc_name.upper()}?</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return True

    if data.startswith("manage_svc_delete_country_do_"):
        parts = data.replace("manage_svc_delete_country_do_", "").split("_", 1)
        svc_name = parts[0]
        country_name = parts[1]

        custom_svcs = load_custom_services()
        target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)
        if target_svc:
            new_ranges = []
            for r in target_svc.get("ranges", []):
                country_display = r.get("country", "")
                match = re.match(r"^([^\w\s]*)\s*(.*)$", country_display)
                cname = match.group(2).strip() if match else "Unknown"
                if cname.upper() != country_name.upper():
                    new_ranges.append(r)
            target_svc["ranges"] = new_ranges
            save_custom_services(custom_svcs)

            await query.answer(f"Deleted {country_name}", show_alert=True)
            kb = build_service_detail_keyboard(svc_name)
            await query.message.edit_text(
                f"📁 SERVICE: <b>{svc_name.upper()}</b>\n"
                f"───────────────────\n"
                f"SELECT A COUNTRY TO MANAGE RANGES:",
                parse_mode="HTML",
                reply_markup=kb,
            )
        return True

    if data.startswith("manage_svc_rename_country_init_"):
        parts = data.replace("manage_svc_rename_country_init_", "").split("_", 1)
        svc_name = parts[0]
        country_name = parts[1]

        context.user_data["admin_state"] = "waiting_for_rename_country_inline"
        context.user_data["temp_target_service"] = svc_name
        context.user_data["temp_target_country"] = country_name

        await query.message.edit_text(
            f"✏️ <b>RENAME COUNTRY: {country_name.upper()}</b>\n"
            f"───────────────────\n"
            f"Please send the new name for this country:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=f"manage_svc_country_view_{svc_name}_{country_name}", style="danger")],
            ]),
        )
        return True

    if data.startswith("manage_svc_edit_range_init_"):
        parts = data.replace("manage_svc_edit_range_init_", "").rsplit("_", 2)
        svc_name, country_name, range_val = parts[0], parts[1], parts[2]

        context.user_data["admin_state"] = "waiting_for_edit_range_inline"
        context.user_data["temp_target_service"] = svc_name
        context.user_data["temp_target_country"] = country_name
        context.user_data["temp_target_range"] = range_val

        await query.message.edit_text(
            f"✏️ <b>EDIT RANGE: {range_val}</b>\n"
            f"───────────────────\n"
            f"Please send the new range value (e.g. <code>23672XXX</code>):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(make_bold_unicode("❌ CANCEL"), callback_data=f"manage_svc_country_view_{svc_name}_{country_name}", style="danger")],
            ]),
        )
        return True

    return False
