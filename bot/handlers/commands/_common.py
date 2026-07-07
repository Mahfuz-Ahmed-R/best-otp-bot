from bot.utils.helpers import is_user_banned
from bot.utils.keyboards import main_keyboard


async def check_banned(update, context):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return True
    return False
