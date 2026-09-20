import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# شناسه ادمین
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW.strip())
except ValueError:
    ADMIN_ID = 0

# وب‌سرور برای رندر (بدون Async)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Robo7Alvand OK")
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        ["📊 تحلیل بازار کریپتو", "📈 تحلیل فارکس و طلا"],
        ["🛡 قوانین مدیریت ریسک", "⚙️ وضعیت حساب و ربات"]
    ]
    if user and user.id == ADMIN_ID:
        keyboard.append(["🛠 پنل مدیریت (تست سیگنال)"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("سلام! خوش آمدید. من دستیار هوشمند Robo7Alvand هستم.", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⚙️ وضعیت حساب و ربات":
        await update.message.reply_text("🟢 وضعیت سرور: آنلاین و پایدار")
    elif text == "🛠 پنل مدیریت (تست سیگنال)" and update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("👑 پنل ادمین فعال است.")
    else:
        await update.message.reply_text("منو را انتخاب کنید.")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return

    # استارت ترد وب‌سرور
    threading.Thread(target=run_web_server, daemon=True).start()

    # استارت بات تلگرام
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == "__main__":
    main()
