import os
import asyncio
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

# لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حافظه موقت ژورنال معاملات
TRADE_JOURNAL = []

# وب‌سرور سبک برای زنده نگه داشتن پورت در Render
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

# دستورات بات
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

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین و پایدار است.")

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 5:
        await update.message.reply_text(
            "⚠️ الگو: /trade [نماد] [BUY/SELL] [ورود] [حد ضرر] [حد سود]\n"
            "مثال: /trade BTCUSDT BUY 64000 63000 66500"
        )
        return

    symbol = args[0].upper()
    side = args[1].upper()

    if side not in ["BUY", "SELL"]:
        await update.message.reply_text("❌ نوع معامله فقط BUY یا SELL است.")
        return

    try:
        entry = float(args[2])
        sl = float(args[3])
        tp = float(args[4])

        if side == "BUY":
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            await update.message.reply_text("❌ حد ضرر یا حد سود نامعتبر است.")
            return

        rr_ratio = round(reward / risk, 2)

        if rr_ratio < 2.0:
            result = (
                f"🚫 ستاپ معامله {symbol} رد شد!\n\n"
                f"نسبت R:R محاسبه‌شده: 1:{rr_ratio}\n"
                f"حداقل مجاز: 1:2.0\n"
                f"⚠️ ریسک به ریوارد غیرمنطقی است."
            )
            await update.message.reply_text(result)
            return

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
            f"✅ ستاپ تایید و در دفترچه ثبت شد!\n\n"
            f"نماد: {symbol} ({side})\n"
            f"ورود: {entry} | SL: {sl} | TP: {tp}\n"
            f"نسبت R:R معامله: 1:{rr_ratio}"
        )
        await update.message.reply_text(confirmation)

    except ValueError:
        await update.message.reply_text("❌ اعداد قیمت را به انگلیسی وارد کنید.")
    except Exception as e:
        logger.error(f"Error: {e}")

async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not TRADE_JOURNAL:
        await update.message.reply_text("📓 دفترچه معاملات خالی است.")
        return

    text = "📓 دفترچه ستاپ‌های معاملاتی:\n\n"
    for idx, item in enumerate(TRADE_JOURNAL[-5:], 1):
        text += (
            f"{idx}. [{item['time']}] {item['symbol']} | {item['side']}\n"
            f"ورود: {item['entry']} | SL: {item['sl']} | TP: {item['tp']} | R:R: 1:{item['rr']}\n"
            f"-------------------\n"
        )
    await update.message.reply_text(text)

async def run_bot():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        logger.error("BOT_TOKEN is missing!")
        return

    # اجرای سرور Keep-Alive در پس‌زمینه
    threading.Thread(target=run_server, daemon=True).start()

    # ساخت اپلیکیشن بات
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("journal", journal_command))

    logger.info("Robo7Alvand Core Engine is Active...")
    
    # راه‌اندازی اصولی و Async
    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(3600)

def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
