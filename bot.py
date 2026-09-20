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

# شناسه ادمین (ابی)
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW.strip())
except ValueError:
    ADMIN_ID = 0

# وب‌سرور سبک و استاندارد برای پینگ Render و UptimeRobot
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Robo7Alvand is active and running!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()

# دستور start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
        
    user = update.effective_user
    user_name = user.first_name if user.first_name else "دوست عزیز"
    
    keyboard = [
        ["📊 تحلیل بازار کریپتو", "📈 تحلیل فارکس و طلا"],
        ["🛡 قوانین مدیریت ریسک", "⚙️ وضعیت حساب و ربات"]
    ]
    
    # دکمه اختصاصی پنل مدیریت فقط برای ابی
    if user.id == ADMIN_ID:
        keyboard.append(["🛠 پنل مدیریت (تست سیگنال)"])
    
    welcome_text = (
        f"سلام {user_name} عزیز! 🌹\n\n"
        f"به **دستیار هوشمند Robo7Alvand** خوش آمدید. 🤖📈\n\n"
        f"🎯 **هدف:** تحلیل‌های منطقی و مدیریت ریسک سخت‌گیرانه (Anti-FOMO).\n\n"
        f"💎 **پوشش نمادها:**\n"
        f"• طلا و فارکس: `XAUUSD` | `EURUSD`\n"
        f"• کریپتو: `BTC` | `ETH` | `SOL`\n\n"
        f"از منوی زیر بخش مورد نظر را انتخاب کنید 👇"
    )
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# مدیریت دکمه‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    user = update.effective_user

    if text == "📊 تحلیل بازار کریپتو":
        res = (
            "🪙 **وضعیت مارکت کریپتو:**\n\n"
            "🔹 **BTC/USDT:** فاز تثبیت و بررسی حجم در حمایت‌های کلیدی\n"
            "🔹 **ETH/USDT:** منتظر تایید شکست ساختار\n"
            "🔹 **SOL/USDT:** حفظ کانال صعودی میان‌مدت\n\n"
            "⚠️ *ورود پله‌ای و R:R حداقل ۱:۲ الزامی است.*"
        )
        await update.message.reply_text(res, parse_mode="Markdown")
        
    elif text == "📈 تحلیل فارکس و طلا":
        res = (
            "🥇 **وضعیت انس طلا و جفت‌ارزها:**\n\n"
            "🔸 **XAUUSD (طلا):** رصد سشن‌های لندن و نیویورک برای شکار نقدینگی\n"
            "🔸 **EURUSD:** در محدوده رنج\n\n"
            "🛡 *بدون تاییدیه و استاپ‌لاس وارد نشوید.*"
        )
        await update.message.reply_text(res, parse_mode="Markdown")
        
    elif text == "🛡 قوانین مدیریت ریسک":
        rules = (
            "📋 **اصول مدیریت ریسک Robo7Alvand:**\n\n"
            "۱. 🚫 عدم FOMO (عدم ورود هیجانی)\n"
            "۲. ⚖️ حداقل نسبت سود به ضرر (R:R) = ۱:۲\n"
            "۳. 🛑 مارتینگل ممنوع (حفظ اصل سرمایه)"
        )
        await update.message.reply_text(rules, parse_mode="Markdown")
        
    elif text == "⚙️ وضعیت حساب و ربات":
        await update.message.reply_text(
            "🟢 وضعیت سرور: **آنلاین و پایدار**\n"
            "نسخه ربات: **Robo7Alvand v1.0**",
            parse_mode="Markdown"
        )
        
    elif text == "🛠 پنل مدیریت (تست سیگنال)" and user and user.id == ADMIN_ID:
        admin_res = (
            "👑 **پنل مدیریت اختصاصی (ابی):**\n\n"
            "✅ احراز هویت ادمین با موفقیت انجام شد.\n"
            "⚙️ وضعیت موتور تحلیل: آماده دریافت تنظیمات فاز ۲."
        )
        await update.message.reply_text(admin_res, parse_mode="Markdown")
        
    else:
        await update.message.reply_text("لطفاً از دکمه‌های منو استفاده کنید.")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found!")
        return

    # ۱. استارت وب‌سرور پورت ۸۰۸۰ در پس‌زمینه
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # ۲. استارت ربات تلگرام
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Robo7Alvand bot is polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
