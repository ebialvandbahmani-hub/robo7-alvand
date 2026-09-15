import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {user_name} عزیز!\n"
        f"به ربات روبو۷ الوند خوش آمدید.\n"
        f"سیستم آماده و عملیاتی است."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "وضعیت":
        await update.message.reply_text("سیستم پایدار و در حال سرویس‌دهی است.")
    else:
        await update.message.reply_text(f"پیام شما دریافت شد: {text}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Robot Robo7Alvand is running...")
    app.run_polling()
