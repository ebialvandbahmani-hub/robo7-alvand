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

# لاگ سیستم
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

# دریافت متغیر محیطی توکن
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# لیست نمادهای معتبر فاز ۱
ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XAUUSD", "EURUSD"}

# ژورنال معاملات در حافظه موقت
TRADE_JOURNAL: list[dict] = []

# --- ساختار هسته ریسک ---
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
        sym = symbol.upper().strip()
        s = side.upper().strip()
        setup = TradeSetup(symbol=sym, side=s, entry=entry, stop_loss=sl, take_profit=tp)

        if sym not in ALLOWED_SYMBOLS:
            setup.rejection_reason = f"نماد {sym} در لیست نمادهای مجاز فاز ۱ نیست.\nنمادهای مجاز: {', '.join(sorted(ALLOWED_SYMBOLS))}"
            return setup

        if s not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت معامله فقط می‌تواند BUY یا SELL باشد."
            return setup

        if s == "BUY":
            if sl >= entry:
                setup.rejection_reason = "در پوزیشن BUY، حد ضرر (SL) باید کمتر از قیمت ورود باشد."
                return setup
            if tp <= entry:
                setup.rejection_reason = "در پوزیشن BUY، حد سود (TP) باید بیشتر از قیمت ورود باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:  # SELL
            if sl <= entry:
                setup.rejection_reason = "در پوزیشن SELL، حد ضرر (SL) باید بیشتر از قیمت ورود باشد."
                return setup
            if tp >= entry:
                setup.rejection_reason = "در پوزیشن SELL، حد سود (TP) باید کمتر از قیمت ورود باشد."
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
            setup.rejection_reason = (
                f"نسبت ریسک به ریوارد ۱ به {rr} است که کمتر از حد مجاز (۱ به ۲.۰) است.\n"
                "🚫 ورود به دلیل عدم توجیه منطقی و نقض فیلتر ضد هیجان (Anti-FOMO) مسدود شد."
            )
            return setup

        setup.is_valid = True
        return setup

# --- وب‌سرور برای زنده نگه داشتن در رندر ---
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
            InlineKeyboardButton("📊 راهنمای ثبت ستاپ", callback_data="btn_trade_help"),
            InlineKeyboardButton("📓 ژورنال معاملات", callback_data="btn_journal")
        ],
        [
            InlineKeyboardButton("🛡 مرامنامه مدیریت ریسک", callback_data="btn_rules"),
            InlineKeyboardButton("🏓 وضعیت سرور (Ping)", callback_data="btn_ping")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# متن‌های بخش‌های مختلف
TEXT_RULES = (
    "🛡 **مرامنامه انضباط معاملاتی و مدیریت ریسک Robo7Alvand:**\n\n"
    "۱. **حداقل نسبت R:R معادل ۱:۲:** سیستم اجازه ورود به معاملاتی که پاداش آن‌ها کمتر از دو برابر ریسک است را نمی‌دهد.\n"
    "۲. **ممنوعیت کامل مارتینگل:** افزایش حجم در ضرر تحت هیچ شرایطی پذیرفته نیست.\n"
    "۳. **عدم ورود هیجانی و اورترید:** ستاپ فقط در سطوح تایید شده ساختار بازار بررسی می‌شود.\n"
    "۴. **حفظ اصل سرمایه اولویت اول است:** هر معامله صرفاً یک احتمال است، نه تضمین."
)

TEXT_TRADE_HELP = (
    "📊 **راهنمای ثبت ستاپ معامله در سیستم:**\n\n"
    "فرمت ارسال دستور:\n"
    "`/trade [نماد] [BUY/SELL] [قیمت ورود] [حد ضرر] [تارگت سود]`\n\n"
    "🔹 **نمونه کریپتو:**\n"
    "`/trade BTCUSDT BUY 64000 63500 65500`\n\n"
    "🔹 **نمونه فارکس:**\n"
    "`/trade XAUUSD SELL 2650 2660 2625`"
)

def get_journal_text() -> str:
    if not TRADE_JOURNAL:
        return "📓 هنوز هیچ معامله تایید‌شده‌ای در ژورنال ثبت نشده است."
    report = "📓 **دفترچه معاملات اخیر (تایید شده):**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        report += (
            f"*{i}. {t['symbol']}* ({t['side']})\n"
            f"🔹 ورود: `{t['entry']}`\n"
            f"🛑 حد ضرر: `{t['sl']}` | 🎯 تارگت: `{t['tp']}`\n"
            f"⚖️ نسبت R:R: `1:{t['rr']}`\n"
            "──────────────────\n"
        )
    return report

# --- هندلرهای تلگرام ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🦅 **به هسته تحلیلی و معاملاتی Robo7Alvand خوش آمدید**\n\n"
        "این سیستم بر پایه انضباط، فیلترهای ضد هیجان (Anti-FOMO) و پایبندی به بقای سرمایه فعال است.\n\n"
        "🎯 **پوشش بازارها:** کریپتوکارنسی (BTC, ETH, SOL) و فارکس (XAUUSD, EURUSD)\n"
        "🛡 **کنترل ریسک:** حداقل R:R ۱:۲ | بدون مارتینگل | ژورنال خودکار\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await update.message.reply_text(welcome, reply_markup=get_main_menu(), parse_mode="Markdown")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 **PONG!** ارتباط فعال و سرویس در وضعیت پایدار است.", parse_mode="Markdown")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXT_RULES, parse_mode="Markdown")

async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_journal_text(), parse_mode="Markdown")

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.message.reply_text(TEXT_TRADE_HELP, parse_mode="Markdown")
        return

    try:
        sym = context.args[0]
        side = context.args[1]
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
            f"📍 قیمت ورود: `{setup.entry}`\n"
            f"🛑 حد ضرر: `{setup.stop_loss}` (ریسک: {setup.risk_amount})\n"
            f"🎯 تارگت سود: `{setup.take_profit}` (ریوارد: {setup.reward_amount})\n"
            f"⚖️ **نسبت R:R:** `1:{setup.risk_reward_ratio}`\n\n"
            "📌 با تعهد کامل به استراتژی وارد شوید.",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.message.reply_text("⚠️ مقادیر ورود، حد ضرر و تارگت سود باید حتماً عددی باشند.")

# هندلر کلیک دکمه‌های شیشه‌ای
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # پاسخ به تلگرام جهت حذف ساعت شنی لودینگ روی دکمه

    data = query.data
    if data == "btn_ping":
        await query.message.reply_text("🏓 **PONG!** ارتباط فعال و سرویس در وضعیت پایدار است.", parse_mode="Markdown")
    elif data == "btn_rules":
        await query.message.reply_text(TEXT_RULES, parse_mode="Markdown")
    elif data == "btn_journal":
        await query.message.reply_text(get_journal_text(), parse_mode="Markdown")
    elif data == "btn_trade_help":
        await query.message.reply_text(TEXT_TRADE_HELP, parse_mode="Markdown")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("خطا در پردازش رویداد:", exc_info=context.error)

# تابع اصلی
async def main():
    app = Application.builder().token(TOKEN).build()

    # ثبت هندلرهای دستورات متنی
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("journal", journal_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("trade", trade_command))

    # ثبت هندلر دکمه‌های شیشه‌ای
    app.add_handler(CallbackQueryHandler(button_handler))

    # ثبت مدیریت خطا
    app.add_error_handler(error_handler)

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Robo7Alvand با موفقیت استارت شد و آماده پاسخگویی است.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("BOT_TOKEN یافت نشد!")

    # اجرای وب‌سرور سبک در پس‌زمینه
    threading.Thread(target=run_web_server, daemon=True).start()

    # اجرای حلقه اصلی
    asyncio.run(main())
