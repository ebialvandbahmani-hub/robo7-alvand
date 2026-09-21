import os
import logging
import threading
from dataclasses import dataclass
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# تنظیمات لاگ سیستم
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# نمادهای مجاز فاز ۱ (کریپتو و فارکس)
ALLOWED_CRYPTO = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ALLOWED_FOREX = ["XAUUSD", "EURUSD"]
ALLOWED_ALL = set(ALLOWED_CRYPTO + ALLOWED_FOREX)

TRADE_JOURNAL = []

# --- هسته ارزیابی ریسک (Anti-FOMO Risk Engine) ---
@dataclass
class TradeSetup:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
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

        if sym not in ALLOWED_ALL:
            setup.rejection_reason = (
                f"نماد {sym} در لیست مجاز فاز ۱ نیست.\n"
                f"کریپتو مجاز: {', '.join(ALLOWED_CRYPTO)}\n"
                f"فارکس مجاز: {', '.join(ALLOWED_FOREX)}"
            )
            return setup

        if s not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت پوزیشن فقط باید BUY یا SELL باشد."
            return setup

        if s == "BUY":
            if sl >= entry:
                setup.rejection_reason = "در پوزیشن BUY، حد ضرر (SL) باید پایین‌تر از نقطه ورود باشد."
                return setup
            if tp <= entry:
                setup.rejection_reason = "در پوزیشن BUY، حد سود (TP) باید بالاتر از نقطه ورود باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:  # SELL
            if sl <= entry:
                setup.rejection_reason = "در پوزیشن SELL، حد ضرر (SL) باید بالاتر از نقطه ورود باشد."
                return setup
            if tp >= entry:
                setup.rejection_reason = "در پوزیشن SELL، حد سود (TP) باید پایین‌تر از نقطه ورود باشد."
                return setup
            risk = sl - entry
            reward = entry - tp

        if risk <= 0:
            setup.rejection_reason = "محاسبه ریسک نامعتبر است."
            return setup

        rr = round(reward / risk, 2)
        setup.risk_reward_ratio = rr

        if rr < cls.MIN_RR_RATIO:
            setup.rejection_reason = f"نسبت ریسک به ریوارد 1:{rr} است. (حداقل R:R مجاز ۱ به ۲ است)."
            return setup

        setup.is_valid = True
        return setup

# --- سرور Health Check برای Render و UptimeRobot ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ROBO7ALVAND_ACTIVE_200_OK")

    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# --- کیبورد جامع و پایدار ---
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🎯 ستاپ معاملاتی", "🏛 تالار معاملات"],
            ["📓 ژورنال معاملات", "🛡 مدیریت ریسک"],
            ["ℹ️ راهنمای دستورات", "🏓 وضعیت سیستم"]
        ],
        resize_keyboard=True
    )

# --- متون و بخش‌های پروژه ---
TEXT_WELCOME = (
    "🦅 **سامانه دستیار معاملاتی Robo7Alvand**\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "پروژه اختصاصی دستیار معامله‌گری و مدیریت ریسک\n"
    "جهت دسترسی به بخش‌ها از کلیدهای زیر استفاده کنید:"
)

TEXT_MARKET_HALL = (
    "🏛 **تالار معاملات مجاز (فاز ۱):**\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "🪙 **کریپتو (Crypto):**\n"
    "• `BTCUSDT` (بیت‌کوین)\n"
    "• `ETHUSDT` (اتریوم)\n"
    "• `SOLUSDT` (سولانا)\n\n"
    "📈 **فارکس و طلا (Forex / Metals):**\n"
    "• `XAUUSD` (انس طلای جهانی)\n"
    "• `EURUSD` (یورو / دلار)"
)

TEXT_RULES = (
    "🛡 **اصول هسته ریسک (Anti-FOMO):**\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "۱. **حداقل R:R مجاز ۱:۲ است** (ورود به معاملات با سود کمتر ممنوع).\n"
    "۲. **استراتژی مارتینگل اکیداً ممنوع** است.\n"
    "۳. **ورود در میانه رنج قیمت (Mid-Range) ممنوع** است.\n"
    "۴. اولویت شماره یک: **حفظ سرمایه اولیه**."
)

TEXT_HELP = (
    "ℹ️ **راهنمای ثبت سریع معامله:**\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "دستور ثبت ستاپ:\n"
    "`/trade [نماد] [BUY/SELL] [ورود] [حدضرر] [تارگت]`\n\n"
    "📌 **مثال کریپتو:**\n"
    "`/trade BTCUSDT BUY 64000 63500 65500`\n\n"
    "📌 **مثال طلا:**\n"
    "`/trade XAUUSD BUY 2500 2490 2530`"
)

def get_journal_summary():
    if not TRADE_JOURNAL:
        return "📓 **ژورنال خالی است.**\nهنوز هیچ معامله تایید‌شده‌ای ثبت نشده است."
    
    msg = f"📓 **ژورنال معاملات ({len(TRADE_JOURNAL)} ستاپ فعال/ثبت‌شده):**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    for i, t in enumerate(reversed(TRADE_JOURNAL[-6:]), 1):
        msg += (
            f"{i}. **{t['symbol']}** | {t['side']}\n"
            f"   ورود: `{t['entry']}` | SL: `{t['sl']}` | TP: `{t['tp']}`\n"
            f"   ⚖️ R:R: `1:{t['rr']}`\n"
            "───────────────────\n"
        )
    return msg

# --- هندلرهای تلگرام ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        TEXT_WELCOME,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

async def trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.effective_message.reply_text(TEXT_HELP, parse_mode="Markdown")
        return

    try:
        sym = context.args[0].upper()
        side = context.args[1].upper()
        entry = float(context.args[2])
        sl = float(context.args[3])
        tp = float(context.args[4])

        setup = RiskEngine.evaluate(sym, side, entry, sl, tp)

        if not setup.is_valid:
            await update.effective_message.reply_text(
                f"🚫 **ستاپ توسط موتور ریسک رد شد!**\n\n⚠️ علت: {setup.rejection_reason}",
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

        await update.effective_message.reply_text(
            f"✅ **ستاپ تایید و در ژورنال ثبت شد.**\n\n"
            f"💎 نماد: `{setup.symbol}` ({setup.side})\n"
            f"📍 ورود: `{setup.entry}`\n"
            f"🛑 حد ضرر: `{setup.stop_loss}`\n"
            f"🎯 حد سود: `{setup.take_profit}`\n"
            f"⚖️ نسبت R:R: `1:{setup.risk_reward_ratio}`",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.effective_message.reply_text("⚠️ مقادیر عددی را به صورت انگلیسی و صحیح وارد کنید.")

async def message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "تالار معاملات" in text:
        await update.effective_message.reply_text(TEXT_MARKET_HALL, parse_mode="Markdown")
    elif "ستاپ معاملاتی" in text or "راهنما" in text:
        await update.effective_message.reply_text(TEXT_HELP, parse_mode="Markdown")
    elif "ژورنال" in text:
        await update.effective_message.reply_text(get_journal_summary(), parse_mode="Markdown")
    elif "مدیریت ریسک" in text or "مرامنامه" in text:
        await update.effective_message.reply_text(TEXT_RULES, parse_mode="Markdown")
    elif "وضعیت سیستم" in text or "پینگ" in text:
        await update.effective_message.reply_text(
            "🟢 **وضعیت سیستم: آنلاین و پایدار**\n"
            "⚡ سرور: Render (Health 200 OK)\n"
            "🛡 RiskEngine: فعال\n"
            "🏓 پینگ پاسخگویی: آنی",
            parse_mode="Markdown"
        )
    else:
        await update.effective_message.reply_text(
            "دستور نامشخص است. لطفاً از گزینه‌های کیبورد زیر استفاده کنید.",
            reply_markup=main_keyboard()
        )

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN ست نشده است!")

    # اجرای پورت وب‌سرور برای UptimeRobot
    threading.Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("trade", trade_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_dispatcher))

    logger.info("Robo7Alvand آنلاین شد.")
    app.run_polling()

if __name__ == "__main__":
    main()
