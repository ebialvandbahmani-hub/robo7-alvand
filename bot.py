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

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XAUUSD", "EURUSD"}
TRADE_JOURNAL = []

# --- هسته مدیریت ریسک ---
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

        if sym not in ALLOWED_SYMBOLS:
            setup.rejection_reason = f"نماد {sym} در لیست مجاز نیست.\nمجازها: {', '.join(sorted(ALLOWED_SYMBOLS))}"
            return setup

        if s not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت معامله فقط BUY یا SELL است."
            return setup

        if s == "BUY":
            if sl >= entry or tp <= entry:
                setup.rejection_reason = "در BUY حد ضرر باید زیر نقطه ورود و حد سود بالای آن باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:
            if sl <= entry or tp >= entry:
                setup.rejection_reason = "در SELL حد ضرر باید بالای نقطه ورود و حد سود زیر آن باشد."
                return setup
            risk = sl - entry
            reward = entry - tp

        rr = round(reward / risk, 2)
        setup.risk_reward_ratio = rr

        if rr < cls.MIN_RR_RATIO:
            setup.rejection_reason = f"نسبت R:R معادل 1:{rr} است (حداقل 1:2 الزامی است)."
            return setup

        setup.is_valid = True
        return setup

# سرور وب برای زنده نگه داشتن رندر (Health Check)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ROBO7ALVAND_ONLINE")

    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# --- متون سیستم ---
TEXT_RULES = (
    "🛡 **مرامنامه مدیریت ریسک Robo7Alvand:**\n\n"
    "۱. حداقل نسبت R:R باید ۱ به ۲ باشد.\n"
    "۲. استراتژی مارتینگل اکیداً ممنوع است.\n"
    "۳. ورود در میانه رنج قیمت ممنوع است.\n"
    "۴. اولویت اول: حفظ سرمایه."
)

TEXT_HELP = (
    "📊 **راهنمای ثبت ستاپ معاملاتی:**\n\n"
    "فرمت دستور:\n"
    "`/trade [نماد] [BUY/SELL] [ورود] [حدضرر] [تارگت]`\n\n"
    "نمونه:\n"
    "`/trade BTCUSDT BUY 64000 63500 65500`"
)

def get_journal_text():
    if not TRADE_JOURNAL:
        return "📓 ژورنال خالی است. هنوز معامله‌ای ثبت نشده."
    res = "📓 **معاملات ثبت شده در ژورنال:**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        res += f"{i}. {t['symbol']} ({t['side']}) | ورود: {t['entry']} | SL: {t['sl']} | TP: {t['tp']} | R:R: 1:{t['rr']}\n"
    return res

def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📊 راهنما", "📓 ژورنال"],
            ["🛡 مرامنامه", "🏓 پینگ"]
        ],
        resize_keyboard=True
    )

# --- هندلرهای تلگرام ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🦅 **دستیار معاملاتی Robo7Alvand فعال شد.**\n\n"
        "از دکمه‌های منوی پایین برای مدیریت و بررسی ستاپ‌ها استفاده کن."
    )
    await update.effective_message.reply_text(
        msg,
        reply_markup=get_reply_keyboard(),
        parse_mode="Markdown"
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "پینگ" in text:
        await update.effective_message.reply_text("🏓 پونگ! سیستم بدون تأخیر کار می‌کند.")
    elif "مرامنامه" in text:
        await update.effective_message.reply_text(TEXT_RULES, parse_mode="Markdown")
    elif "ژورنال" in text:
        await update.effective_message.reply_text(get_journal_text())
    elif "راهنما" in text:
        await update.effective_message.reply_text(TEXT_HELP, parse_mode="Markdown")

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.effective_message.reply_text(TEXT_HELP, parse_mode="Markdown")
        return

    try:
        sym, side = context.args[0], context.args[1]
        entry, sl, tp = float(context.args[2]), float(context.args[3]), float(context.args[4])
        setup = RiskEngine.evaluate(sym, side, entry, sl, tp)

        if not setup.is_valid:
            await update.effective_message.reply_text(
                f"🚫 **رد ستاپ معاملاتی!**\n\n{setup.rejection_reason}",
                parse_mode="Markdown"
            )
            return

        TRADE_JOURNAL.append({
            "symbol": setup.symbol, "side": setup.side,
            "entry": setup.entry, "sl": setup.stop_loss,
            "tp": setup.take_profit, "rr": setup.risk_reward_ratio
        })

        await update.effective_message.reply_text(
            f"✅ **ستاپ تایید و در ژورنال ثبت شد.**\n\n"
            f"💎 نماد: {setup.symbol} ({setup.side})\n"
            f"📍 نقطه ورود: {setup.entry}\n"
            f"🛑 حد ضرر: {setup.stop_loss}\n"
            f"🎯 حد سود: {setup.take_profit}\n"
            f"⚖️ نسبت R:R: معادل 1:{setup.risk_reward_ratio}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.effective_message.reply_text("⚠️ مقادیر عددی را به درستی وارد کنید.")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN ست نشده است!")

    # وب‌سرور برای UptimeRobot و Render
    threading.Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("trade", trade_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Robo7Alvand آماده است.")
    app.run_polling()

if __name__ == "__main__":
    main()
