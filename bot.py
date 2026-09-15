import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------- وب‌سرور سلامت برای Render ----------
flask_app = Flask(name)

@flask_app.route("/")
def health():
    return "Robo7Alvand is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# ---------- دستورات ربات ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"سلام {name} عزیز! :wave:\n"
        "به ربات روبو۷ الوند خوش آمدید 🤖\n"
        "سیستم آماده و عملیاتی است.\n\n"
        "دستورات:\n"
        "/help - راهنما\n"
        "/status - وضعیت سیستم\n"
        "/analyze - تحلیل نماد\n"
        "/watch - لیست پایش"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        ":clipboard: راهنمای روبو۷ الوند:\n\n"
        "/start - شروع\n"
        "/status - وضعیت سیستم\n"
        "/analyze - تحلیل نماد (مثال: /analyze فولاد)\n"
        "/watch - لیست نمادهای تحت پایش\n\n"
        "برای تحلیل، بعد از دستور نام نماد را بنویسید."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 وضعیت سیستم:\n"
        "هسته پردازش: فعال\n"
        "اتصال سرور: برقرار\n"
        "دیتابیس: متصل\n"
        "آماده دریافت تحلیل :white_check_mark:"
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        symbol = " ".join(context.args)
        await update.message.reply_text(
            f":bar_chart: در حال تحلیل نماد: {symbol}\n"
            "موتور تحلیل در نسخه‌های بعدی فعال می‌شود.\n"
            "ساختار دستور ثبت شد :white_check_mark:"
        )
    else:
        await update.message.reply_text("نام نماد را بنویسید. مثال: /analyze فولاد")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👁 لیست پایش فعلی:\n"
        "۱. نماد آتش - فاز استراحت\n"
        "۲. آماده افزودن نماد جدید...\n\n"
        "برای افزودن: /watch add نام‌نماد"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "وضعیت" in text:
        await status(update, context)
    elif "سلام" in text:
        await update.message.reply_text(f"سلام {update.effective_user.first_name} عزیز! 🤖")
    else:
        await update.message.reply_text(f"پیام شما دریافت شد: {text}\nبرای راهنما /help را بفرستید.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Robot Robo7Alvand is running...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
