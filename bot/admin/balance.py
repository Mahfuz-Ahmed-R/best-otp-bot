from bot.config import SUPPORT_LINK
from bot.utils.helpers import (
    ban_user,
    format_balance,
    get_user,
    is_user_banned,
    unban_user,
    update_db_balance,
    user_exists,
)


async def process_add_balance_user(update, context):
    uid_to_add = update.message.text.strip()
    if not uid_to_add.isdigit():
        await update.message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_add_int = int(uid_to_add)
    if not user_exists(uid_to_add_int):
        await update.message.reply_text("❌ USER NOT FOUND!")
        context.user_data["add_balance_mode"] = False
        return
    context.user_data["pending_add_user"] = uid_to_add_int
    await update.message.reply_text("💵 SEND AMOUNT TO ADD:")


async def process_remove_balance_user(update, context):
    uid_to_remove = update.message.text.strip()
    if not uid_to_remove.isdigit():
        await update.message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_remove_int = int(uid_to_remove)
    if not user_exists(uid_to_remove_int):
        await update.message.reply_text("❌ USER NOT FOUND!")
        context.user_data["remove_balance_mode"] = False
        return
    context.user_data["pending_remove_user"] = uid_to_remove_int
    await update.message.reply_text("💸 SEND AMOUNT TO REMOVE:")


async def process_add_balance_amount(update, context):
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ INVALID AMOUNT!")
        return
    uid = context.user_data.get("pending_add_user")
    if not uid:
        context.user_data["add_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED.")
        return
    new_balance = await update_db_balance(uid, amount)
    await update.message.reply_text(
        f"✅ **ADD BALANCE SUCCESSFUL**\n🆔 USER: `{uid}`\n"
        f"💰 ADDED: `{format_balance(amount)} BDT`\n"
        f"📈 NEW BALANCE: `{format_balance(new_balance)} BDT`",
        parse_mode="Markdown",
    )
    try:
        await context.bot.send_message(
            uid,
            f"🎉 ADMIN ADDED `{format_balance(amount)} BDT` TO YOUR ACCOUNT!\n"
            f"💵 NEW BALANCE: `{format_balance(new_balance)} BDT`",
            parse_mode="Markdown",
        )
    except Exception:
        pass
    context.user_data["add_balance_mode"] = False
    context.user_data["pending_add_user"] = None


async def process_remove_balance_amount(update, context):
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ INVALID AMOUNT!")
        return
    uid = context.user_data.get("pending_remove_user")
    if not uid:
        context.user_data["remove_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED.")
        return
    old_balance = get_user(uid).get("balance", 0)
    if amount > old_balance:
        await update.message.reply_text(f"❌ INSUFFICIENT BALANCE! Current: {format_balance(old_balance)} BDT")
        context.user_data["remove_balance_mode"] = False
        context.user_data["pending_remove_user"] = None
        return
    new_balance = await update_db_balance(uid, -amount)
    await update.message.reply_text(
        f"✅ **REMOVE BALANCE SUCCESSFUL**\n🆔 USER: `{uid}`\n"
        f"💸 REMOVED: `{format_balance(amount)} BDT`\n"
        f"📉 NEW BALANCE: `{format_balance(new_balance)} BDT`",
        parse_mode="Markdown",
    )
    try:
        await context.bot.send_message(
            uid,
            f"⚠️ ADMIN REMOVED `{format_balance(amount)} BDT` FROM YOUR ACCOUNT!\n"
            f"💵 NEW BALANCE: `{format_balance(new_balance)} BDT`",
            parse_mode="Markdown",
        )
    except Exception:
        pass
    context.user_data["remove_balance_mode"] = False
    context.user_data["pending_remove_user"] = None


async def process_ban_user(update, context):
    uid_to_ban = update.message.text.strip()
    if not uid_to_ban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_ban_int = int(uid_to_ban)
    if not user_exists(uid_to_ban_int):
        await update.message.reply_text("❌ USER NOT FOUND!")
        context.user_data["admin_ban_mode"] = False
        return
    if is_user_banned(uid_to_ban_int):
        await update.message.reply_text("⚠️ USER IS ALREADY BANNED!")
        context.user_data["admin_ban_mode"] = False
        return
    ban_user(uid_to_ban_int)
    try:
        await context.bot.send_message(
            uid_to_ban_int,
            f"🚫 **YOU HAVE BEEN BANNED**\n📞 Contact support: {SUPPORT_LINK}",
            parse_mode="Markdown",
        )
    except Exception:
        pass
    await update.message.reply_text(f"✅ USER `{uid_to_ban}` BANNED!", parse_mode="Markdown")
    context.user_data["admin_ban_mode"] = False


async def process_unban_user(update, context):
    uid_to_unban = update.message.text.strip()
    if not uid_to_unban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_unban_int = int(uid_to_unban)
    if not is_user_banned(uid_to_unban_int):
        await update.message.reply_text("⚠️ THIS USER IS NOT BANNED!")
        context.user_data["admin_unban_mode"] = False
        return
    unban_user(uid_to_unban_int)
    try:
        await context.bot.send_message(uid_to_unban_int, "✅ **YOU HAVE BEEN UNBANNED!** Use /start", parse_mode="Markdown")
    except Exception:
        pass
    await update.message.reply_text(f"✅ USER `{uid_to_unban}` UNBANNED!", parse_mode="Markdown")
    context.user_data["admin_unban_mode"] = False
