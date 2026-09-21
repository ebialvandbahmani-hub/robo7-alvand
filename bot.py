import os
import logging
import threading
from dataclasses import dataclass
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

# توکن ربات
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
            setup.rejection_reason = f"نماد {sym} در لیست مجاز نیست.\nمجازها: {', '.join(sorted(ALLOWED_SYMBOLS))}"
            return setup

        if s not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت معامله فقط باید BUY یا SELL باشد."
            return setup

        if s == "BUY":
            if sl >= entry:
                setup.rejection_reason = "در BUY حد ضرر باید پایین‌تر از ورود باشد."
                return setup
            if tp <= entry:
                setup.rejection_reason = "در BUY حد سود باید بالاتر از ورود باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:
            if sl <= entry:
                setup.rejection_reason = "در SELL حد ضرر باید بالاتر از ورود باشد."
                return setup
            if tp >= entry:
                setup.rejection_reason = "در SELL حد سود باید پایین‌تر از ورود باشد."
                return setup
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            setup.rejection_reason = "مقادیر ریسک یا ریوارد منطقی نیستند."
            return setup

        rr = round(reward / risk, 2)
        setup.risk_amount = round(risk, 4)
        setup.reward_amount = round(reward, 4)
        setup.risk_reward_ratio = rr

        if rr < cls.MIN_RR_RATIO:
            setup.rejection_reason = f"نسبت R:R معادل 1:{rr} است که کمتر از حداقل (1:2) است.\n🚫 معامله به دلیل ریسک بالا رد شد."
            return setup

        setup.is_valid = True
        return setup

# سرور داخلی برای پینگ رندر
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ROBO7ALVAND_ONLINE")

    def log_message(self, format, *args):
        pass

def start_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# کیبورد اصلی
def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 راهنمای ثبت ترید", callback_data="help"),
            InlineKeyboardButton("📓 ژورنال معاملات", callback_data="journal")
        ],
        [
            InlineKeyboardButton("🛡 مرامنامه ضد FOMO", callback_data="rules"),
            InlineKeyboardButton("🏓 پینگ سرور", callback_data="ping")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

TEXT_RULES = (
    "🛡 **مرامنامه مدیریت ریسک Robo7Alvand:**\n\n"
    "۱. حداقل نسبت R:R باید ۱ به ۲ باشد.\n"
    "۲. استراتژی مارتینگل اکیداً ممنوع است.\n"
    "۳. ورود در میانه رنج قیمت ممنوع است.\n"
    "۴. اولویت اول: حفظ سرمایه."
)

TEXT_HELP = (
    "📊 **راهنمای ثبت ستاپ:**\n\n"
    "فرمت دستور:\n"
    "`/trade [نماد] [BUY/SELL] [ورود] [حدضرر] [تارگت]`\n\n"
    "نمونه:\n"
    "`/trade BTCUSDT BUY 64000 63500 65500`"
)

# دستورات تلگرام
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🦅 **سامانه تحلیلی Robo7Alvand آنلاین شد.**\n\n"
        "برای تست دکمه‌های زیر را لمس کنید:"
    )
    await update.effective_message.reply_text(msg, reply_markup=get_main_menu(), parse_mode="Markdown")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("🏓 پونگ! سرور فعال و ربات آماده دریافت دستورات است.")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(TEXT_RULES, parse_mode="Markdown")

async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not TRADE_JOURNAL:
        await update.effective_message.reply_text("📓 ژورنال خالی است. هنوز معامله‌ای ثبت نشده.")
        return
    res = "📓 **معاملات ثبت شده:**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        res += f"{i}. {t['symbol']} ({t['side']}) | ورود: {t['entry']} | SL: {t['sl']} | TP: {t['tp']} | R:R: 1:{t['rr']}\n"
    await update.effective_message.reply_text(res)

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
            f"✅ **ستاپ تایید و در ژورنال ذخیره شد.**\n\n"
            f"💎 نماد: {setup.symbol} ({setup.side})\n"
            f"📍 ورود: {setup.entry}\n"
            f"🛑 حد ضرر: {setup.stop_loss}\n"
            f"🎯 تارگت: {setup.take_profit}\n"
            f"⚖️ نسبت سود به ریسک: 1:{setup.risk_reward_ratio}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.effective_message.reply_text("⚠️ قیمت‌ها باید عدد انگلیسی باشند.")

# پاسخ به کلیک دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # رفع فوری ساعت‌شنی

    data = query.data
    logger.info(f"دکمه لمس شد: {data}")

    if data in ["ping", "btn_ping"]:
        await query.message.reply_text("🏓 پونگ! سیستم کاملاً فعال است.")
    elif data in ["rules", "btn_rules"]:
        await query.message.reply_text(TEXT_RULES, parse_mode="Markdown")
    elif data in ["journal", "btn_journal"]:
        if not TRADE_JOURNAL:
            await query.message.reply_text("📓 ژورنال خالی است.")
        else:
            res = "📓 **معاملات ثبت شده:**\n\n"
            for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
                res += f"{i}. {t['symbol']} ({t['side']}) | ورود: {t['entry']} | SL: {t['sl']} | TP: {t['tp']} | R:R: 1:{t['rr']}\n"
            await query.message.reply_text(res)
    elif data in ["help", "btn_help", "trade_help"]:
        await query.message.reply_text(TEXT_HELP, parse_mode="Markdown")
    else:
        await query.message.reply_text(f"گزینه {data} انتخاب شد.")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN یافت نشد!")

    # اجرای سرور وب در پس‌زمینه
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # ساخت ربات
    app = ApplicationBuilder().token(TOKEN).build()

    # هندلرهای دستورات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("journal", journal_command))
    app.add_handler(CommandHandler("trade", trade_command))

    # هندلر دکمه‌ها
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Robo7Alvand با موفقیت استارت خورد.")
    app.run_polling()

if __name__ == "__main__":
    main()
