from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_IDS, MAX_WITHDRAW, MIN_WITHDRAW, SUPPORT_LINK
from bot.utils.helpers import (
    format_balance,
    generate_payment_id,
    get_user,
    is_valid_bangladesh_number,
    load_withdraw_requests,
    save_withdraw_requests,
    update_db_balance,
)
from bot.utils.keyboards import cancel_keyboard, is_admin, main_keyboard, withdraw_method_keyboard


async def withdraw_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    if "CANCEL" in text.upper():
        context.user_data["withdraw_mode"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid))
        return

    method_map = {
        "BKASH": "BKASH", "NAGAD": "NAGAD", "ROCKET": "ROCKET", "BINANCE": "BINANCE",
    }
    method = next((v for k, v in method_map.items() if k in text.upper()), None)
    if method:
        balance = get_user(uid)["balance"]
        context.user_data["withdraw_method"] = method
        context.user_data["withdraw_mode"] = "amount"
        await update.message.reply_text(
            f"<blockquote>💸 SEND AMOUNT\n💵 BALANCE: {format_balance(balance)} BDT</blockquote>\n\n"
            f"<blockquote>📉 MIN: {MIN_WITHDRAW} BDT</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    else:
        await update.message.reply_text("⚠️ SELECT A VALID METHOD!", reply_markup=withdraw_method_keyboard())


async def withdraw_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    if "CANCEL" in text.upper():
        context.user_data["withdraw_mode"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid))
        return
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ SEND A VALID AMOUNT!", reply_markup=cancel_keyboard())
        return
    balance = get_user(uid)["balance"]
    if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
        await update.message.reply_text(f"📉 MIN: {MIN_WITHDRAW} | MAX: {MAX_WITHDRAW} BDT", reply_markup=cancel_keyboard())
        return
    if amount > balance:
        await update.message.reply_text("🚫 INSUFFICIENT BALANCE!", reply_markup=cancel_keyboard())
        return
    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_mode"] = "number"
    await update.message.reply_text(
        "📞 SEND YOUR PAYMENT NUMBER!\n\n<blockquote>🔢 EXAMPLE: 017XXXXXXXX</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    if "CANCEL" in text.upper():
        context.user_data["withdraw_mode"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid))
        return
    if not is_valid_bangladesh_number(text):
        await update.message.reply_text("⚠️ SEND VALID BD NUMBER!", reply_markup=cancel_keyboard())
        return

    payment_id = generate_payment_id()
    context.user_data["temp_withdraw"] = {
        "method": context.user_data.get("withdraw_method"),
        "amount": context.user_data.get("withdraw_amount"),
        "number": text,
        "payment_id": payment_id,
    }
    await update.message.reply_text(
        "✨ <b>CONFIRM PAYMENT DETAILS</b> ✨\n\n"
        f"<blockquote>📝 METHOD: {context.user_data['temp_withdraw']['method']}\n"
        f"📞 NUMBER: {text}</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ CANCEL", callback_data="withdraw_cancel"),
                InlineKeyboardButton("✅ CONFIRM", callback_data="withdraw_confirm"),
            ]
        ]),
    )


async def process_withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    temp = context.user_data.get("temp_withdraw")
    if not temp:
        await query.message.reply_text("⚠️ SESSION EXPIRED.", reply_markup=main_keyboard(uid))
        return

    amount = temp["amount"]
    payment_id = temp["payment_id"]
    new_balance = await update_db_balance(uid, -amount)
    wr = load_withdraw_requests()
    wr[str(payment_id)] = {
        "user_id": uid,
        "method": temp["method"],
        "amount": amount,
        "number": temp["number"],
        "payment_id": payment_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
    }
    save_withdraw_requests(wr)
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None

    await query.message.edit_text(
        f"✅ <b>WITHDRAW REQUEST SUBMITTED</b>\n\n"
        f"<blockquote>💵 AMOUNT: {format_balance(amount)} BDT\n"
        f"💰 NEW BALANCE: {format_balance(new_balance)} BDT\n"
        f"🆔 ID: <code>{payment_id}</code></blockquote>",
        parse_mode="HTML",
    )

    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"admin_approve_{payment_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"admin_reject_{payment_id}"),
        ]
    ])
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💸 <b>NEW WITHDRAW REQUEST</b>\n\n"
                f"👤 USER: <code>{uid}</code>\n"
                f"💵 AMOUNT: {format_balance(amount)} BDT\n"
                f"📱 METHOD: {temp['method']}\n"
                f"📞 NUMBER: {temp['number']}\n"
                f"🆔 ID: <code>{payment_id}</code>",
                parse_mode="HTML",
                reply_markup=admin_kb,
            )
        except Exception as exc:
            print(f"Admin withdraw notify fail: {exc}")


async def process_withdraw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    await query.message.edit_text("❌ WITHDRAW CANCELLED")
    await context.bot.send_message(query.from_user.id, "🔹 MAIN MENU:", reply_markup=main_keyboard(query.from_user.id))


async def admin_approve_withdraw(update, context, payment_id):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    wr = load_withdraw_requests()
    req = wr.get(str(payment_id))
    if not req:
        await query.message.edit_text("❌ Request not found.")
        return
    req["status"] = "approved"
    save_withdraw_requests(wr)
    await query.message.edit_text(f"✅ Approved withdraw {payment_id}")
    try:
        await context.bot.send_message(req["user_id"], f"✅ Withdraw <code>{payment_id}</code> approved!", parse_mode="HTML")
    except Exception:
        pass


async def admin_reject_withdraw(update, context, payment_id):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    wr = load_withdraw_requests()
    req = wr.get(str(payment_id))
    if not req:
        await query.message.edit_text("❌ Request not found.")
        return
    await update_db_balance(req["user_id"], req["amount"])
    req["status"] = "rejected"
    save_withdraw_requests(wr)
    await query.message.edit_text(f"❌ Rejected withdraw {payment_id} — balance restored.")
    try:
        await context.bot.send_message(
            req["user_id"],
            f"❌ **WITHDRAWAL REQUEST REJECTED**\n\nContact support: {SUPPORT_LINK}",
            parse_mode="Markdown",
        )
    except Exception:
        pass
