import os
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TRADE_JOURNAL = []

# ۱. وب‌سرور داخلی سبک برای زنده ماندن در رندر
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ROBO7_ONLINE")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

# ۲. دستور /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🟢 دستیار تحلیلی Robo7Alvand متصل و آماده است.\n\n"
        "دستورات عملیاتی:\n"
        "۱. ثبت ستاپ و بررسی ریسک:\n"
        "/trade [نماد] [نوع: BUY/SELL] [ورود] [حدضرر] [تارگت]\n"
        "مثال: /trade BTCUSDT BUY 64000 63500 65500\n\n"
        "۲. مشاهده دفترچه معاملات:\n"
        "/journal\n\n"
        "۳. بررسی وضعیت ارتباط:\n"
        "/ping"
    )
    await update.message.reply_text(msg)

# ۳. دستور /ping
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین، پایدار و آماده دریافت دستورات است.")

# ۴. موتور ثبت ستاپ معاملاتی و تحلیل ریسک (Anti-FOMO)
async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 5:
        await update.message.reply_text(
            "⚠️ فرمت دستور اشتباه است!\n"
            "الگو: /trade [نماد] [BUY/SELL] [قیمت ورود] [حد ضرر] [حد سود]\n"
            "مثال: /trade BTCUSDT BUY 64000 63000 66500"
        )
        return

    symbol = args[0].upper()
    side = args[1].upper()

    if side not in ["BUY", "SELL"]:
        await update.message.reply_text("❌ نوع معامله فقط باید BUY یا SELL باشد.")
        return

    try:
        entry = float(args[2])
        sl = float(args[3])
        tp = float(args[4])

        # محاسبه ریسک به ریوارد (R:R)
        if side == "BUY":
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            await update.message.reply_text("❌ مقادیر حد ضرر یا حد سود منطقی نیستند! لطفاً اعداد را چک کنید.")
            return

        rr_ratio = round(reward / risk, 2)

        # فیلتر سخت‌گیرانه ضد فومو
        if rr_ratio < 2.0:
            result = (
                f"🚫 ستاپ معامله {symbol} رد شد! (نقض قوانین مدیریت ریسک)\n\n"
                f"نسبت R:R محاسبه‌شده: 1:{rr_ratio}\n"
                f"حداقل R:R مجاز: 1:2.0\n"
                f"⚠️ اجازه ورود ندارید؛ این معامله ریسک به ریوارد منطقی ندارد."
            )
            await update.message.reply_text(result)
            return

        # تایید ستاپ و ثبت در دفترچه
        record = {
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr_ratio
        }
        TRADE_JOURNAL.append(record)

        confirmation = (
            f"✅ ستاپ معاملاتی تایید و در دفترچه ثبت شد!\n\n"
            f"نماد: {symbol} ({side})\n"
            f"نقطه ورود: {entry}\n"
            f"حد ضرر (SL): {sl}\n"
            f"حد سود (TP): {tp}\n"
            f"نسبت سود به زیان: 1:{rr_ratio} 🔥\n\n"
            f"💡 قانون طلایی: پایبند به حد ضرر باشید و حجم را دو برابر نکنید!"
        )
        await update.message.reply_text(confirmation)

    except ValueError:
        await update.message.reply_text("❌ اعداد قیمت را به صورت انگلیسی و صحیح وارد کنید.")
    except Exception as e:
        logger.error(f"Error in trade: {e}")

# ۵. دفترچه ژورنال معاملات
async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not TRADE_JOURNAL:
        await update.message.reply_text("📓 دفترچه معاملات فعلاً خالی است.")
        return

    text = "📓 دفترچه ستاپ‌های معاملاتی تایید شده:\n\n"
    for idx, item in enumerate(TRADE_JOURNAL[-5:], 1):
        text += (
            f"{idx}. [{item['time']}] {item['symbol']} | {item['side']}\n"
            f"ورود: {item['entry']} | SL: {item['sl']} | TP: {item['tp']} | R:R: 1:{item['rr']}\n"
            f"-------------------\n"
        )
    await update.message.reply_text(text)

def main():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        logger.error("BOT_TOKEN is GAPGPTMASKTOKENz9k9es43aegX0X")
        return

    # استارت سرور کیپ‌الایو
    threading.Thread(target=run_server, daemon=True).start()

    # استارت بات تلگرام
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("journal", journal_command))

    logger.info("Robo7Alvand Core Engine is Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
