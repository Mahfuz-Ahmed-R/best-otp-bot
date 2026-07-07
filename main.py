import os
import sys

from telegram import Update

from bot.app import build_application
from bot.config import BOT_TOKEN
from bot.health import start_health_server


def main():
    if not BOT_TOKEN:
        print("ERROR: Set BOT_TOKEN in .env file or environment variables")
        sys.exit(1)

    if os.environ.get("PORT"):
        start_health_server()

    app = build_application(BOT_TOKEN)
    print("🚀 BEST OTP BOT RUNNING...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
