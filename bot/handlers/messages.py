import asyncio
import io
import random
import re
import string

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.admin.balance import (
    process_add_balance_amount,
    process_add_balance_user,
    process_ban_user,
    process_remove_balance_amount,
    process_remove_balance_user,
    process_unban_user,
)
from bot.admin.keyboards import (
    build_admin_main_inline_keyboard,
    build_country_detail_keyboard,
    build_manage_services_inline_keyboard,
    get_admin_panel_text,
)
from bot.config import BOT_NAME, OTP_GROUP_LINK, SUPPORT_LINK, USER_DATA_FILE
from bot.handlers.commands.leaderboard import leaderboard_command
from bot.handlers.commands.profile import profile_command
from bot.handlers.commands.refer import refer_command
from bot.handlers.withdraw import (
    withdraw_amount_received,
    withdraw_method_selected,
    withdraw_number_received,
)
from bot.services.selection import show_app_selection
from bot.services.stats import get_user_stats
from bot.utils.country import get_country_info
from bot.utils.guard import is_state_cancelling_input
from bot.utils.helpers import is_user_banned, load_custom_services, load_data, save_custom_services
from bot.utils.keyboards import is_admin, main_keyboard
from bot.utils.text import make_bold_unicode, normalize_stylized_text


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    raw_text = update.message.text.strip() if update.message.text else ""

    text = normalize_stylized_text(raw_text).strip()

    if is_state_cancelling_input(text):
        context.user_data["admin_state"] = None
        context.user_data["temp_target_service"] = None
        context.user_data["temp_target_country"] = None
        context.user_data["temp_target_range"] = None
        context.user_data["add_balance_mode"] = False
        context.user_data["remove_balance_mode"] = False
        context.user_data["pending_add_user"] = None
        context.user_data["pending_remove_user"] = None
        context.user_data["admin_ban_mode"] = False
        context.user_data["admin_unban_mode"] = False
        context.user_data["withdraw_mode"] = None
        context.user_data["broadcast_mode"] = False
        context.user_data["mode"] = None

    admin_state = context.user_data.get("admin_state")
    if admin_state and is_admin(uid):
        if admin_state == "waiting_for_add_service_name_inline":
            svc_name = text.strip().upper()
            custom_svcs = load_custom_services()
            exists = any(s.get("sid", "").upper() == svc_name for s in custom_svcs)
            if exists:
                await update.message.reply_text(f"❌ **Service '{svc_name}' already exists!**", parse_mode="Markdown")
            else:
                custom_svcs.append({"sid": svc_name, "ranges": []})
                save_custom_services(custom_svcs)
                await update.message.reply_text(f"✅ **Service '{svc_name}' added successfully!**", parse_mode="Markdown")

            context.user_data["admin_state"] = None
            kb = build_manage_services_inline_keyboard()
            await update.message.reply_text(
                "⚙️ MANAGE SERVICES\n"
                "───────────────────\n"
                "SELECT A SERVICE:",
                reply_markup=kb,
            )
            return

        elif admin_state == "waiting_for_rename_service_inline":
            new_name = text.strip().upper()
            old_name = context.user_data.get("temp_target_service")

            custom_svcs = load_custom_services()
            for s in custom_svcs:
                if s.get("sid", "").upper() == old_name.upper():
                    s["sid"] = new_name
                    break
            save_custom_services(custom_svcs)

            await update.message.reply_text(
                f"✅ **Service renamed from '{old_name}' to '{new_name}' successfully!**",
                parse_mode="Markdown",
            )
            context.user_data["admin_state"] = None
            context.user_data["temp_target_service"] = None

            kb = build_manage_services_inline_keyboard()
            await update.message.reply_text(
                "⚙️ MANAGE SERVICES\n"
                "───────────────────\n"
                "SELECT A SERVICE:",
                reply_markup=kb,
            )
            return

        elif admin_state == "waiting_for_add_range_inline":
            range_val = text.strip().upper()
            svc_name = context.user_data.get("temp_target_service")
            country_name = context.user_data.get("temp_target_country")

            custom_svcs = load_custom_services()
            target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)

            if not target_svc:
                await update.message.reply_text("❌ Service not found!")
                context.user_data["admin_state"] = None
                return

            dup = any(r.get("range", "").upper() == range_val for r in target_svc.get("ranges", []))
            if dup:
                await update.message.reply_text(
                    f"❌ **Range '{range_val}' already exists under '{svc_name}'!**",
                    parse_mode="Markdown",
                )
            else:
                prefix = re.sub(r"[xX]+$", "", range_val).strip()
                prefix_clean = re.sub(r"\D", "", prefix)

                if country_name:
                    cname = country_name
                    flag, _ = get_country_info(prefix_clean)
                else:
                    flag, cname = get_country_info(prefix_clean)

                target_svc["ranges"].append({
                    "range": range_val,
                    "country": f"{flag} {cname}",
                })
                save_custom_services(custom_svcs)
                await update.message.reply_text(
                    f"✅ **Range '{range_val}' ({flag} {cname}) added to '{svc_name}' successfully!**",
                    parse_mode="Markdown",
                )

            context.user_data["admin_state"] = None
            context.user_data["temp_target_service"] = None
            context.user_data["temp_target_country"] = None

            kb = build_country_detail_keyboard(svc_name, cname)
            if kb:
                await update.message.reply_text(
                    f"RANGES → {svc_name.upper()} → {cname.upper()}\n"
                    f"───────────────────\n"
                    f"TAP TO DELETE / EDIT:",
                    reply_markup=kb,
                )
            return

        elif admin_state == "waiting_for_rename_country_inline":
            new_country_name = text.strip()
            svc_name = context.user_data.get("temp_target_service")
            old_country_name = context.user_data.get("temp_target_country")

            custom_svcs = load_custom_services()
            target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)

            if target_svc:
                flag = "🌍"
                for r in target_svc.get("ranges", []):
                    country_display = r.get("country", "")
                    match = re.match(r"^([^\w\s]*)\s*(.*)$", country_display)
                    cname = match.group(2).strip() if match else "Unknown"
                    if cname.upper() == old_country_name.upper():
                        flag = match.group(1).strip() if match else "🌍"
                        r["country"] = f"{flag} {new_country_name}"

                save_custom_services(custom_svcs)
                await update.message.reply_text(
                    f"✅ **Country renamed from '{old_country_name}' to '{new_country_name}' successfully!**",
                    parse_mode="Markdown",
                )

            context.user_data["admin_state"] = None
            context.user_data["temp_target_service"] = None
            context.user_data["temp_target_country"] = None

            kb = build_country_detail_keyboard(svc_name, new_country_name)
            if kb:
                await update.message.reply_text(
                    f"RANGES → {svc_name.upper()} → {new_country_name.upper()}\n"
                    f"───────────────────\n"
                    f"TAP TO DELETE / EDIT:",
                    reply_markup=kb,
                )
            return

        elif admin_state == "waiting_for_edit_range_inline":
            new_range = text.strip().upper()
            svc_name = context.user_data.get("temp_target_service")
            country_name = context.user_data.get("temp_target_country")
            old_range = context.user_data.get("temp_target_range")

            custom_svcs = load_custom_services()
            target_svc = next((s for s in custom_svcs if s.get("sid", "").upper() == svc_name.upper()), None)

            if target_svc:
                for r in target_svc.get("ranges", []):
                    if r.get("range", "").upper() == old_range.upper():
                        r["range"] = new_range
                        prefix = re.sub(r"[xX]+$", "", new_range).strip()
                        prefix_clean = re.sub(r"\D", "", prefix)
                        flag, _ = get_country_info(prefix_clean)
                        r["country"] = f"{flag} {country_name}"
                        break

                save_custom_services(custom_svcs)
                await update.message.reply_text(
                    f"✅ **Range edited from '{old_range}' to '{new_range}' successfully!**",
                    parse_mode="Markdown",
                )

            context.user_data["admin_state"] = None
            context.user_data["temp_target_service"] = None
            context.user_data["temp_target_country"] = None
            context.user_data["temp_target_range"] = None

            kb = build_country_detail_keyboard(svc_name, country_name)
            if kb:
                await update.message.reply_text(
                    f"RANGES → {svc_name.upper()} → {country_name.upper()}\n"
                    f"───────────────────\n"
                    f"TAP TO DELETE / EDIT:",
                    reply_markup=kb,
                )
            return

    if context.user_data.get("withdraw_mode") == "select_method":
        await withdraw_method_selected(update, context)
        return
    if context.user_data.get("withdraw_mode") == "amount":
        await withdraw_amount_received(update, context)
        return
    if context.user_data.get("withdraw_mode") == "number":
        await withdraw_number_received(update, context)
        return

    if context.user_data.get("add_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_add_user"):
            await process_add_balance_amount(update, context)
        else:
            await process_add_balance_user(update, context)
        return
    if context.user_data.get("remove_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_remove_user"):
            await process_remove_balance_amount(update, context)
        else:
            await process_remove_balance_user(update, context)
        return
    if context.user_data.get("admin_ban_mode") and is_admin(uid):
        await process_ban_user(update, context)
        return
    if context.user_data.get("admin_unban_mode") and is_admin(uid):
        await process_unban_user(update, context)
        return

    if context.user_data.get("mode") == "input_user_id" and is_admin(uid):
        target_uid = text.strip()
        if not target_uid.isdigit():
            await update.message.reply_text("❌ INVALID ID!")
            return
        context.user_data["mode"] = None
        stats = get_user_stats(target_uid)
        msg = (
            f"👤 <b>USER STATUS</b> — <code>{target_uid}</code>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ TODAY: 📱 {stats['today_numbers']} | 🔑 {stats['today_otps']}\n"
            f"🔥 7 DAYS: 📱 {stats['last7d_numbers']} | 🔑 {stats['last7d_otps']}\n"
            f"🌐 ALL TIME: 📱 {stats['total_numbers']} | 🔑 {stats['total_otps']}"
        )
        await update.message.reply_text(
            msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    make_bold_unicode("📂 CHECK ALL DATA"),
                    callback_data=f"full_logs_{target_uid}",
                    style="primary",
                )],
                [InlineKeyboardButton(
                    make_bold_unicode("🔙 BACK"),
                    callback_data="adm_menu_back_to_admin",
                    style="danger",
                )],
            ]),
        )
        return

    if not is_admin(uid) and is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    if text == "❌ CANCEL":
        context.user_data.clear()
        await update.message.reply_text("❌ CANCELLED", reply_markup=main_keyboard(uid))
        return

    if "PROFILE" in text:
        await profile_command(update, context)
        return

    if "REFER AND EARN" in text:
        await refer_command(update, context)
        return

    if "GET NUMBER" in text:
        await show_app_selection(update, context)
        return

    if "TRAFFIC" in text:
        await leaderboard_command(update, context)
        return

    if "2FA" in text:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 2FA ONLINE", url=OTP_GROUP_LINK, style="primary")],
        ])
        await update.message.reply_text(
            "🔐 <b>2FA ONLINE</b>\n\nJoin the OTP group for live 2FA codes:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    if "SUPPORT" in text:
        support_text = (
            f"👥 <b>{BOT_NAME}</b> SUPPORT\n\n"
            "Tap below to contact support:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 SUPPORT", url=SUPPORT_LINK, style="primary")],
        ])
        await update.message.reply_text(support_text, reply_markup=keyboard, parse_mode="HTML")
        return

    if "ADMIN PANEL" in text and is_admin(uid):
        context.user_data["admin_mode"] = "main"
        admin_text = get_admin_panel_text()
        await update.message.reply_text(
            admin_text,
            parse_mode="HTML",
            reply_markup=build_admin_main_inline_keyboard(),
        )
        return

    if context.user_data.get("broadcast_mode") and is_admin(uid):
        context.user_data["broadcast_mode"] = False

        user_db = load_data(USER_DATA_FILE)
        all_uids = list(user_db.keys())

        if not all_uids:
            await update.message.reply_text("❌ No users found to broadcast!")
            return

        success_ids, fail_ids = [], []
        status_msg = await update.message.reply_text(
            f"🚀 <b>Broadcast started...</b>\n🎯 Target: {len(all_uids)} users.",
            parse_mode="HTML",
        )

        def format_broadcast_caption(caption_text):
            if not caption_text:
                return f"<blockquote>📢 <b>{BOT_NAME} NOTICE :</b></blockquote>"
            formatted = re.sub(r"(\d{3,}[xX]{3,})", r"<code>\1</code>", str(caption_text))
            return f"<blockquote>📢 <b>{BOT_NAME} NOTICE :</b></blockquote>\n\n{formatted}"

        for user_id_str in all_uids:
            try:
                target_id = int(user_id_str)

                if update.message.text:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=format_broadcast_caption(update.message.text),
                        parse_mode="HTML",
                    )
                elif update.message.photo:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_photo(
                        chat_id=target_id,
                        photo=update.message.photo[-1].file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.video:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_video(
                        chat_id=target_id,
                        video=update.message.video.file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.document:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_document(
                        chat_id=target_id,
                        document=update.message.document.file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.audio:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_audio(
                        chat_id=target_id,
                        audio=update.message.audio.file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.voice:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_voice(
                        chat_id=target_id,
                        voice=update.message.voice.file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.animation:
                    caption = format_broadcast_caption(update.message.caption) if update.message.caption else None
                    await context.bot.send_animation(
                        chat_id=target_id,
                        animation=update.message.animation.file_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                elif update.message.sticker:
                    await context.bot.send_sticker(
                        chat_id=target_id,
                        sticker=update.message.sticker.file_id,
                    )
                else:
                    try:
                        await context.bot.copy_message(
                            chat_id=target_id,
                            from_chat_id=update.message.chat_id,
                            message_id=update.message.message_id,
                        )
                    except Exception:
                        await context.bot.send_message(
                            chat_id=target_id,
                            text=f"📢 <b>{BOT_NAME} NOTICE :</b>\n\nYou have a new message that could not be displayed.",
                            parse_mode="HTML",
                        )
                success_ids.append(user_id_str)
            except Exception as e:
                print(f"Broadcast fail to {user_id_str}: {e}")
                fail_ids.append(user_id_str)

            await asyncio.sleep(0.05)

        report_text = (
            f"✅ <b>{BOT_NAME} NOTICE COMPLETE !</b>\n\n"
            f"📊 <b>BROADCAST REPORT:</b>\n\n"
            f"<blockquote>✅ SUCCESSFULLY SENT: {len(success_ids)} USERS !</blockquote>\n"
            f"<blockquote>❌ FAILED TO SEND: {len(fail_ids)} USERS !</blockquote>"
        )

        await status_msg.delete()
        await context.bot.send_message(
            chat_id=uid,
            text=report_text,
            parse_mode="HTML",
            reply_markup=main_keyboard(uid),
        )

        random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if success_ids:
            s_file = io.BytesIO("\n".join(success_ids).encode())
            s_file.name = f"SUCCESS_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=s_file, caption="✅ Success User List")
        if fail_ids:
            f_file = io.BytesIO("\n".join(fail_ids).encode())
            f_file.name = f"FAILED_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=f_file, caption="❌ Failed User List")

        return

    await update.message.reply_text("🔹 PLEASE USE THE BUTTONS BELOW:", reply_markup=main_keyboard(uid))
