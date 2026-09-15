import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE"

def init_db():
    conn = sqlite3.connect("robo7alvand.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = f"سلام {user_name} عزیز!\nبه ربات روبو۷ الوند خوش آمدید.\nسیستم آماده و عملیاتی است."
    await update.message.reply_text(welcome_text)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "وضعیت":
        await update.message.reply_text("سیستم پایدار و در حال سرویس‌دهی است.")
    elif text == "ارتباط با مدیر":
        await update.message.reply_text("مدیریت انبار لوازم یدکی (ابی) در دسترس است.")
    else:
        await update.message.reply_text(f"پیام شما دریافت شد: {text}\nلطفاً یک گزینه معتبر انتخاب کنید.")

def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("Robot Robo7Alvand is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
