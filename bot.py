import os
import logging
from dataclasses import dataclass
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
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

# دریافت توکن
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# لیست نمادهای مجاز
ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XAUUSD", "EURUSD"}

# ژورنال معاملات
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

# --- سرور وب برای پینگ و آپ‌تایم رندر ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ROBO7ALVAND_OK")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- کیبورد اصلی ---
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 راهنمای ثبت ستاپ", callback_data="btn_help"),
            InlineKeyboardButton("📓 ژورنال معاملات", callback_data="btn_journal")
        ],
        [
            InlineKeyboardButton("🛡 مرامنامه مدیریت ریسک", callback_data="btn_rules"),
            InlineKeyboardButton("🏓 وضعیت سرور (Ping)", callback_data="btn_ping")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

TEXT_RULES = (
    "🛡 **مرامنامه مدیریت ریسک Robo7Alvand:**\n\n"
    "۱. حداقل نسبت R:R باید ۱ به ۲ باشد.\n"
    "۲. استراتژی مارتینگل (Martingale) اکیداً ممنوع و مسدود است.\n"
    "۳. ورود در میانه رنج قیمت ممنوع است؛ فقط نواحی کلیدی عرضه و تقاضا.\n"
    "۴. حفظ سرمایه اولویت اول است؛ بدون تایید ستاپ ترید نکنید."
)

TEXT_HELP = (
    "📊 **فرمت ثبت ستاپ معاملاتی:**\n\n"
    "`/trade [نماد] [BUY/SELL] [ورود] [حدضرر] [تارگت]`\n\n"
    "مثال:\n"
    "`/trade BTCUSDT BUY 64000 63500 65500`"
)

def get_journal_text():
    if not TRADE_JOURNAL:
        return "📓 ژورنال خالی است. هنوز معامله‌ای ثبت نشده است."
    res = "📓 **آخرین معاملات تایید شده:**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        res += f"{i}. {t['symbol']} ({t['side']}) | ورود: {t['entry']} | SL: {t['sl']} | TP: {t['tp']} | R:R: 1:{t['rr']}\n"
    return res

# --- دستورات متنی تلگرام ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🦅 **به سامانه هوشمند Robo7Alvand خوش آمدید**\n\n"
        "این سیستم بر پایه انضباط، فیلترهای ضد هیجان و پرایس اکشن طراحی شده است.\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=main_keyboard(), parse_mode="Markdown")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین و پایدار است.")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(TEXT_RULES, parse_mode="Markdown")

async def journal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(get_journal_text())

async def trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if len(context.args) < 5:
        await update.message.reply_text(TEXT_HELP, parse_mode="Markdown")
        return

    try:
        sym, side = context.args[0], context.args[1]
        entry, sl, tp = float(context.args[2]), float(context.args[3]), float(context.args[4])
        setup = RiskEngine.evaluate(sym, side, entry, sl, tp)

        if not setup.is_valid:
            await update.message.reply_text(
                f"🚫 **ستاپ معامله رد شد!**\n\n"
                f"{setup.rejection_reason}",
                parse_mode="Markdown"
            )
            return

        TRADE_JOURNAL.append({
            "symbol": setup.symbol, "side": setup.side,
            "entry": setup.entry, "sl": setup.stop_loss,
            "tp": setup.take_profit, "rr": setup.risk_reward_ratio
        })

        await update.message.reply_text(
            f"✅ **ستاپ معاملاتی تایید و در ژورنال ثبت شد.**\n\n"
            f"💎 نماد: {setup.symbol} ({setup.side})\n"
            f"📍 قیمت ورود: {setup.entry}\n"
            f"🛑 حد ضرر: {setup.stop_loss} (ریسک: {setup.risk_amount})\n"
            f"🎯 تارگت سود: {setup.take_profit} (ریوارد: {setup.reward_amount})\n"
            f"⚖️ نسبت R:R: 1 : {setup.risk_reward_ratio}\n\n"
            f"📌 با تعهد کامل به استراتژی وارد شوید.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("⚠️ مقادیر قیمت ورود، حد ضرر و تارگت باید اعداد معتبر باشند.")

# --- مدیریت کلیک تمام دکمه‌ها ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # پاسخ سریع به تلگرام برای قطع شدن لودینگ دکمه
    await query.answer()

    data = query.data
    logger.info(f"Button clicked: {data}")

    if data in ["btn_ping", "ping"]:
        await query.message.reply_text("🏓 پونگ! سیستم کاملاً آنلاین و پایدار است.")
    elif data in ["btn_rules", "rules"]:
        await query.message.reply_text(TEXT_RULES, parse_mode="Markdown")
    elif data in ["btn_journal", "journal"]:
        await query.message.reply_text(get_journal_text())
    elif data in ["btn_help", "trade_help"]:
        await query.message.reply_text(TEXT_HELP, parse_mode="Markdown")
    else:
        await query.message.reply_text("گزینه دریافت شد.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("خطای سیستمی:", exc_info=context.error)

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN ست نشده است!")

    # اجرای سرور وب در پس‌زمینه
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # ساخت اپلیکیشن با متد استاندارد پایدار
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("journal", journal_cmd))
    application.add_handler(CommandHandler("rules", rules_cmd))
    application.add_handler(CommandHandler("trade", trade_cmd))
    
    # ثبت هندلر دکمه‌ها
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_error_handler(error_handler)

    logger.info("ربات در حال اجرا است...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
