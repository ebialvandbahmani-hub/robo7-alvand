import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات محیطی ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- دفترچه ثبت معاملات (در حافظه) ---
journal = []

# --- وب‌سرور سبک Keep-Alive برای Render ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Robo7Alvand Core Engine is Active & Running.")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    server.serve_forever()

# --- کیبورد شیشه‌ای منوی اصلی ---
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 ثبت ستاپ معامله", callback_data="btn_trade_help"),
            InlineKeyboardButton("📓 دفترچه معاملات", callback_data="btn_journal")
        ],
        [
            InlineKeyboardButton("🏓 وضعیت سرور (Ping)", callback_data="btn_ping"),
            InlineKeyboardButton("🛡 قوانین ریسک", callback_data="btn_rules")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- هندلرهای دستورات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 **به دستیار تحلیلی Robo7Alvand خوش آمدید!**\n\n"
        "سیستم مجهز به هسته ضد FOMO و مدیریت ریسک سخت‌گیرانه است.\n"
        "از دکمه‌های زیر برای دسترسی سریع استفاده کنید:"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین و پایدار است.")

async def journal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not journal:
        await update.message.reply_text("📓 هنوز هیچ معامله‌ای ثبت نشده است.")
        return
    
    msg = "📓 **آخرین معاملات تایید شده:**\n\n"
    for i, t in enumerate(journal[-5:], 1):
        msg += f"{i}. {t['symbol']} ({t['side']}) | R:R: 1:{t['rr']} | Entry: {t['entry']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # فرمت: /trade BTCUSDT BUY 64000 63500 65500
    if len(context.args) < 5:
        await update.message.reply_text(
            "⚠️ فرمت صحیح دستور:\n"
            "`/trade [نماد] [BUY/SELL] [ورود] [SL] [TP]`\n\n"
            "مثال:\n`/trade BTCUSDT BUY 64000 63500 65500`",
            parse_mode="Markdown"
        )
        return

    try:
        symbol = context.args[0].upper()
        side = context.args[1].upper()
        entry = float(context.args[2])
        sl = float(context.args[3])
        tp = float(context.args[4])

        if side not in ["BUY", "SELL"]:
            await update.message.reply_text("⚠️ جهت معامله باید BUY یا SELL باشد.")
            return

        if side == "BUY":
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            await update.message.reply_text("⚠️ مقادیر حد ضرر یا تارگت با جهت معامله همخوانی ندارد!")
            return

        rr = round(reward / risk, 2)

        if rr < 2.0:
            await update.message.reply_text(
                f"🚫 **ستاپ معامله {symbol} رد شد!**\n\n"
                f"نسبت R:R محاسبه‌شده: 1:{rr}\n"
                f"حداقل مجاز: 1:2.0\n"
                f"⚠️ ریسک به ریوارد غیرمنطقی است (ضد FOMO).",
                parse_mode="Markdown"
            )
        else:
            trade_data = {"symbol": symbol, "side": side, "entry": entry, "sl": sl, "tp": tp, "rr": rr}
            journal.append(trade_data)
            await update.message.reply_text(
                f"✅ **ستاپ تایید و در دفترچه ثبت شد!**\n\n"
                f"نماد: {symbol} ({side})\n"
                f"ورود: {entry} | حد ضرر: {sl} | تارگت: {tp}\n"
                f"نسبت R:R معامله: 1:{rr}",
                parse_mode="Markdown"
            )
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً اعداد قیمت را به درستی وارد کنید.")

# --- مدیریت کلیک روی دکمه‌های شیشه‌ای ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_ping":
        await query.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین و پایدار است.")
    
    elif query.data == "btn_journal":
        if not journal:
            await query.message.reply_text("📓 هنوز هیچ معامله‌ای ثبت نشده است.")
        else:
            msg = "📓 **آخرین معاملات تایید شده:**\n\n"
            for i, t in enumerate(journal[-5:], 1):
                msg += f"{i}. {t['symbol']} ({t['side']}) | R:R: 1:{t['rr']} | Entry: {t['entry']}\n"
            await query.message.reply_text(msg, parse_mode="Markdown")
            
    elif query.data == "btn_rules":
        rules = (
            "🛡 **قوانین معاملاتی Robo7Alvand:**\n\n"
            "۱. حداقل نسبت R:R باید ۱ به ۲ باشد.\n"
            "۲. معامله در میانه رنج (Mid-Range) ممنوع است.\n"
            "۳. مارتینگل و دوبرابر کردن حجم در ضرر اکیداً ممنوع است.\n"
            "۴. حفظ سرمایه اولویت اول سیستم است."
        )
        await query.message.reply_text(rules, parse_mode="Markdown")
        
    elif query.data == "btn_trade_help":
        help_text = (
            "📊 **راهنمای ثبت ستاپ:**\n\n"
            "برای بررسی ستاپ توسط هسته ضد FOMO، دستور زیر را ارسال کنید:\n\n"
            "`/trade [نماد] [BUY/SELL] [ورود] [SL] [TP]`\n\n"
            "مثال:\n"
            "`/trade BTCUSDT BUY 64000 63500 65500`"
        )
        await query.message.reply_text(help_text, parse_mode="Markdown")

# --- تابع اصلی اجرای ربات ---
async def run_bot():
    app = Application.builder().token(TOKEN).build()

    # ثبت دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("journal", journal_cmd))
    app.add_handler(CommandHandler("trade", trade_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        print("Robo7Alvand Bot is Polling...")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")
    
    # اجرای وب‌سرور در ترد جداگانه
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # اجرای ربات با استاندارد پایتون جدید
    asyncio.run(run_bot())
