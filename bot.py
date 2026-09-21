import os
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# لاگینگ سیستم
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

# دریافت توکن
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# لیست نمادهای معتبر فاز ۱
ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XAUUSD", "EURUSD"}

# --- ساختار هسته ریسک و ستاپ معاملات ---
@dataclass
class TradeSetup:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_amount: float = 0.0
    reward_amount: float = 0.0
    risk_reward_ratio: float = 0.0
    is_valid: bool = False
    rejection_reason: Optional[str] = None

class RiskEngine:
    MIN_RR_RATIO: float = 2.0

    @classmethod
    def evaluate(cls, symbol: str, side: str, entry: float, sl: float, tp: float) -> TradeSetup:
        sym = symbol.upper()
        s = side.upper()
        setup = TradeSetup(symbol=sym, side=s, entry=entry, stop_loss=sl, take_profit=tp)

        if sym not in ALLOWED_SYMBOLS:
            setup.rejection_reason = f"نماد {sym} در لیست نمادهای مجاز فاز ۱ نیست.\nنمادهای مجاز: {', '.join(sorted(ALLOWED_SYMBOLS))}"
            return setup

        if s not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت معامله فقط باید BUY یا SELL باشد."
            return setup

        if s == "BUY":
            if sl >= entry:
                setup.rejection_reason = "در پوزیشن BUY، حد ضرر باید پایین‌تر از قیمت ورود باشد."
                return setup
            if tp <= entry:
                setup.rejection_reason = "در پوزیشن BUY، تارگت سود باید بالاتر از قیمت ورود باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:
            if sl <= entry:
                setup.rejection_reason = "در پوزیشن SELL، حد ضرر باید بالاتر از قیمت ورود باشد."
                return setup
            if tp >= entry:
                setup.rejection_reason = "در پوزیشن SELL، تارگت سود باید پایین‌تر از قیمت ورود باشد."
                return setup
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            setup.rejection_reason = "محاسبه فاصله ریسک یا ریوارد غیرمنطقی است."
            return setup

        rr = round(reward / risk, 2)
        setup.risk_amount = round(risk, 4)
        setup.reward_amount = round(reward, 4)
        setup.risk_reward_ratio = rr

        if rr < cls.MIN_RR_RATIO:
            setup.rejection_reason = f"نسبت ریسک به ریوارد ۱ به {rr} است که کمتر از حداقل مجاز (۱ به ۲.۰) است.\n🚫 ورود به دلیل ریسک نامتعارف و نقض قوانین ضد FOMO مسدود شد."
            return setup

        setup.is_valid = True
        return setup

# دفترچه ثبت معاملات در حافظه
TRADE_JOURNAL: list[dict] = []

# --- سرور Keep Alive برای رندر ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Robo7Alvand Core Engine is Active.")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- کیبورد اصلی ---
def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 راهنمای ثبت معامله", callback_data="menu_trade"),
            InlineKeyboardButton("📓 ژورنال معاملات", callback_data="menu_journal")
        ],
        [
            InlineKeyboardButton("🛡 قوانین و مرامنامه ریسک", callback_data="menu_rules"),
            InlineKeyboardButton("🏓 وضعیت سرور (Ping)", callback_data="menu_ping")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- دستورات اصلی تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🦅 **به هسته معاملاتی Robo7Alvand خوش آمدید**\n\n"
        "این سیستم با اتکا به تحلیل داده‌محور، فیلترهای ضد هیجان (Anti-FOMO) و پایبندی به اصول حفظ سرمایه طراحی شده است.\n\n"
        "🎯 **پوشش بازارها:** کریپتوکارنسی (BTC, ETH, SOL) و فارکس (XAUUSD, EURUSD)\n"
        "🛡 **مدیریت ریسک:** حداقل R:R ۱:۲ | بدون مارتینگل | ثبت دقیق در ژورنال\n\n"
        "از منوی زیر فرمان مورد نظرتان را انتخاب کنید:"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🏓 **PONG!** هسته تحلیلی ربات فعال و وب‌سرویس پایش پایدار است."
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    rules_text = (
        "🛡 **مرامنامه انضباط مالی و مدیریت ریسک Robo7Alvand:**\n\n"
        "۱. **حداقل R:R ۱:۲:** هیچ پوزیشنی با سود احتمالی کمتر از دو برابر حدضرر تایید نخواهد شد.\n"
        "۲. **ممنوعیت کامل مارتینگل:** دو برابر کردن حجم در ضرر خط قرمز مطلق است.\n"
        "۳. **عدم ورود در میانه رنج (Mid-Range):** ورود فقط در سطوح تایید شده و واکنش معتبر به نواحی عرضه و تقاضا.\n"
        "۴. **حفظ سرمایه:** اولویت سیستم در گام اول بقا و صیانت از دارایی، و در گام دوم کسب سود است."
    )
    await target.reply_text(rules_text, parse_mode="Markdown")

async def journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if not TRADE_JOURNAL:
        await target.reply_text("📓 هنوز هیچ معامله تایید‌شده‌ای در ژورنال ثبت نشده است.")
        return

    report = "📓 **دفترچه معاملات اخیر (تایید شده):**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        report += (
            f"*{i}. {t['symbol']}* ({t['side']})\n"
            f"🔹 نقطه ورود: `{t['entry']}`\n"
            f"🛑 حد ضرر: `{t['sl']}` | 🎯 تارگت: `{t['tp']}`\n"
            f"📊 نسبت ریسک/ریوارد: `1:{t['rr']}`\n"
            "──────────────────\n"
        )
    await target.reply_text(report, parse_mode="Markdown")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.message.reply_text(
            "⚠️ **الگوی ارسال ستاپ:**\n\n"
            "`/trade [نماد] [BUY/SELL] [قیمت ورود] [حد ضرر] [تارگت سود]`\n\n"
            "🔹 **مثال کریپتو:**\n"
            "`/trade BTCUSDT BUY 64000 63500 65500`\n\n"
            "🔹 **مثال فارکس:**\n"
            "`/trade XAUUSD SELL 2650 2660 2625`",
            parse_mode="Markdown"
        )
        return

    try:
        sym, side = context.args[0], context.args[1]
        entry = float(context.args[2])
        sl = float(context.args[3])
        tp = float(context.args[4])

        setup = RiskEngine.evaluate(sym, side, entry, sl, tp)

        if not setup.is_valid:
            await update.message.reply_text(
                f"🚫 **ستاپ معامله رد شد!**\n\n{setup.rejection_reason}",
                parse_mode="Markdown"
            )
            return

        TRADE_JOURNAL.append({
            "symbol": setup.symbol,
            "side": setup.side,
            "entry": setup.entry,
            "sl": setup.stop_loss,
            "tp": setup.take_profit,
            "rr": setup.risk_reward_ratio
        })

        await update.message.reply_text(
            f"✅ **ستاپ معاملاتی تایید و در ژورنال ثبت شد.**\n\n"
            f"💎 نماد: *{setup.symbol}* ({setup.side})\n"
            f"📍 ورود: `{setup.entry}`\n"
            f"🛑 حد ضرر (SL): `{setup.stop_loss}` (فاصله: {setup.risk_amount})\n"
            f"🎯 حد سود (TP): `{setup.take_profit}` (فاصله: {setup.reward_amount})\n"
            f"⚖️ **نسبت ریسک به ریوارد:** `1:{setup.risk_reward_ratio}`\n\n"
            "📌 لطفاً دقیقاً بر اساس پلن مدیریت پوزیشن عمل کنید.",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.message.reply_text("⚠️ لطفاً مقادیر قیمت، حد ضرر و تارگت را به درستی و عددی وارد کنید.")

# --- کال‌بک دکمه‌های شیشه‌ای ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_ping":
        await ping(update, context)
    elif query.data == "menu_journal":
        await journal(update, context)
    elif query.data == "menu_rules":
        await rules(update, context)
    elif query.data == "menu_trade":
        guide = (
            "📊 **نحوه ثبت معامله در سیستم:**\n\n"
            "دستور را همراه با مشخصات ستاپ به شکل زیر ارسال کنید:\n\n"
            "`/trade [نماد] [BUY/SELL] [ورود] [SL] [TP]`\n\n"
            "مثال:\n"
            "`/trade BTCUSDT BUY 64000 63500 65500`"
        )
        await query.message.reply_text(guide, parse_mode="Markdown")

# --- مدیریت خطای سراسری ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("خطا در هنگام پردازش درخواست:", exc_info=context.error)

# --- اجرای برنامه ---
async def run_bot():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("journal", journal))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("trade", trade))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_error_handler(error_handler)

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("ربات Robo7Alvand با موفقیت استارت خورد.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("BOT_TOKEN تعریف نشده است!")

    # اجرای وب‌سرور در ترد مجزا جهت پایدار نگه‌داشتن سرور رندر
    threading.Thread(target=run_web_server, daemon=True).start()

    # اجرای رویداد تلگرام
    asyncio.run(run_bot())
