import os
import asyncio
import logging
from dataclasses import dataclass
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENbj8jlkcwyaX0X")
PORT = int(os.environ.get("PORT", 8080))

USER_MODES = {}

# ================== موتور ریسک و تحلیل ==================

@dataclass
class TradeSetup:
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: str
    note: str

def generate_setup(symbol: str, current_price: float, support: float, resistance: float) -> TradeSetup:
    entry = round(support * 1.005, 4)
    stop_loss = round(support * 0.985, 4)
    risk_amount = entry - stop_loss
    tp1 = round(entry + (risk_amount * 2), 4)
    tp2 = round(entry + (risk_amount * 3), 4)
    return TradeSetup(
        entry=entry,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        risk_reward="1:2 (TP1) - 1:3 (TP2)",
        note="ورود فقط پله‌ای نزدیک حمایت. عدم ورود در هیجان (FOMO). حفظ سرمایه اولویت اول است."
    )

def get_risk_management_guideline(text: str = "") -> str:
    capital = 100.0
    if "بالای" in text or "500" in text or "۵۰۰" in text:
        capital = 1000.0
    elif "200" in text or "۲۰۰" in text:
        capital = 300.0
    elif "50" in text or "۵۰" in text:
        capital = 100.0
    risk_amount = capital * 0.02
    return (
        "🛡 راهنمای مدیریت ریسک Robo7Alvand:\n\n"
        f"💵 سرمایه تخمینی: {int(capital)} دلار\n"
        f"⚠️ حداکثر ریسک هر معامله (۲٪): {int(risk_amount)} دلار\n"
        "📊 حداکثر پوزیشن باز همزمان: ۲ عدد\n"
        "🪜 روش ورود: پله‌ای (۵۰٪ در تریگر حمایت، ۵۰٪ پس از تاییدیه کندلی)\n\n"
        "⚖️ قوانین غیرقابل تغییر:\n"
        "۱. حداقل نسبت R:R برابر 1:2\n"
        "۲. بدون مارتینگل و بدون میانگین کم کردن در ضرر\n"
        "۳. پایبندی به استاپ لاس تحت هر شرایط"
    )

BASE_MARKET_DATA = {
    "BTC": {"name": "بیت‌کوین (BTC/USDT)", "price": 64200, "sup": 62800, "res": 65500, "trend": "خنثی متمایل به صعودی"},
    "ETH": {"name": "اتریوم (ETH/USDT)", "price": 2650, "sup": 2520, "res": 2720, "trend": "استراحت روی حمایت"},
    "SOL": {"name": "سولانا (SOL/USDT)", "price": 148, "sup": 138, "res": 155, "trend": "صعودی پرشتاب"},
    "TRX": {"name": "ترون (TRX/USDT)", "price": 0.152, "sup": 0.146, "res": 0.158, "trend": "تثبیت روند"},
    "TON": {"name": "تون‌کوین (TON/USDT)", "price": 5.65, "sup": 5.20, "res": 6.10, "trend": "انباشت"},
    "DOGE": {"name": "دوج‌کوین (DOGE/USDT)", "price": 0.108, "sup": 0.098, "res": 0.118, "trend": "نوسانی"},
    "ADA": {"name": "کاردانو (ADA/USDT)", "price": 0.365, "sup": 0.345, "res": 0.385, "trend": "فاز تجمیع"},
    "XAUUSD": {"name": "انس طلا جهانی (XAU/USD)", "price": 2625, "sup": 2600, "res": 2650, "trend": "نوسان بالا در سقف تاریخی"},
    "XAGUSD": {"name": "انس نقره جهانی (XAG/USD)", "price": 31.2, "sup": 30.5, "res": 32.4, "trend": "صعودی"},
    "OIL": {"name": "نفت خام (WTI)", "price": 71.5, "sup": 69.2, "res": 73.8, "trend": "نوسانی"},
    "EURUSD": {"name": "یورو به دلار (EUR/USD)", "price": 1.114, "sup": 1.108, "res": 1.121, "trend": "خنثی"},
}

ALIASES = {
    "بیت کوین": "BTC", "بیتکوین": "BTC", "btc": "BTC",
    "اتریوم": "ETH", "eth": "ETH",
    "سولانا": "SOL", "sol": "SOL",
    "ترون": "TRX", "tron": "TRX", "trx": "TRX",
    "تون": "TON", "تون کوین": "TON", "ton": "TON",
    "دوج": "DOGE", "دوج کوین": "DOGE", "doge": "DOGE",
    "کاردانو": "ADA", "ada": "ADA",
    "طلا": "XAUUSD", "انس طلا": "XAUUSD", "gold": "XAUUSD", "xauusd": "XAUUSD",
    "نقره": "XAGUSD", "انس نقره": "XAGUSD", "silver": "XAGUSD", "xagusd": "XAGUSD",
    "نفت": "OIL", "oil": "OIL", "wti": "OIL",
    "یورو": "EURUSD", "eurusd": "EURUSD",
}

def get_market_info(raw_text: str):
    clean = raw_text.strip().lower()
    symbol_key = ALIASES.get(clean, raw_text.strip().upper())
    if symbol_key in BASE_MARKET_DATA:
        return symbol_key, BASE_MARKET_DATA[symbol_key]
    return symbol_key, {
        "name": f"مارکت {symbol_key}",
        "price": 100.0,
        "sup": 95.0,
        "res": 108.0,
        "trend": "تحلیل داینامیک و نوسانی"
    }

# ================== کیبوردها ==================

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎯 ستاپ‌های معاملاتی"), KeyboardButton("📊 تحلیل تکنیکال")],
        [KeyboardButton("💰 مدیریت ریسک"), KeyboardButton("📋 راهنما و قوانین")]
    ], resize_keyboard=True)

def symbols_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("BTC"), KeyboardButton("ETH"), KeyboardButton("SOL")],
        [KeyboardButton("TRX"), KeyboardButton("TON"), KeyboardButton("DOGE")],
        [KeyboardButton("طلا"), KeyboardButton("نقره"), KeyboardButton("نفت")],
        [KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

def capital_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("زیر ۵۰ دلار"), KeyboardButton("۵۰ تا ۲۰۰ دلار")],
        [KeyboardButton("۲۰۰ تا ۵۰۰ دلار"), KeyboardButton("بالای ۵۰۰ دلار")],
        [KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

# ================== هندلرهای پیام ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_MODES[update.effective_user.id] = None
    await update.message.reply_text(
        "سلام ابی جان! 🦅\n"
        "دستیار معاملاتی Robo7Alvand آنلاین و آماده است.\n\n"
        "یک گزینه را انتخاب کنید یا نام هر نمادی را مستقیماً تایپ کنید:",
        reply_markup=main_menu_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    mode = USER_MODES.get(user_id)

    # 1. بازگشت
    if "بازگشت" in text:
        USER_MODES[user_id] = None
        await update.message.reply_text("به منوی اصلی برگشتید:", reply_markup=main_menu_keyboard())
        return

    # 2. منوهای اصلی (بررسی کلمات کلیدی تا ایموجی‌ها شرط را نشکنند)
    if "ستاپ" in text:
        USER_MODES[user_id] = "SETUP"
        await update.message.reply_text(
            "🎯 **بخش ستاپ معاملاتی**\n\nنماد مورد نظر را انتخاب کنید یا نام آن را تایپ کنید (مثلاً TRX یا ترون):",
            reply_markup=symbols_keyboard()
        )
        return

    if "تحلیل" in text:
        USER_MODES[user_id] = "ANALYSIS"
        await update.message.reply_text(
            "📊 **بخش تحلیل تکنیکال**\n\nنماد مورد نظر را انتخاب یا تایپ کنید:",
            reply_markup=symbols_keyboard()
        )
        return

    if "مدیریت" in text or "ریسک" in text:
        USER_MODES[user_id] = "RISK"
        await update.message.reply_text("میزان سرمایه معاملاتی خود را انتخاب کنید:", reply_markup=capital_keyboard())
        return

    if "راهنما" in text or "قوانین" in text:
        await update.message.reply_text(
            "📋 **قوانین و راهنمای Robo7Alvand:**\n\n"
            "۱. تمام ستاپ‌ها دارای نسبت سود به ریسک حداقل ۱ به ۲ هستند.\n"
            "۲. ورودها پله‌ای و فقط در نزدیکی سطوح حمایتی معتبر انجام می‌شود.\n"
            "۳. استفاده از مارتینگل و خریدهای هیجانی ممنوع است.",
            reply_markup=main_menu_keyboard()
        )
        return

    # 3. پاسخ در وضعیت‌های انتخابی
    if mode == "SETUP":
        sym_key, info = get_market_info(text)
        s = generate_setup(sym_key, info["price"], info["sup"], info["res"])
        await update.message.reply_text(
            f"🎯 ستاپ معاملاتی: {info['name']}\n\n"
            f"📍 قیمت مبنا: {info['price']}\n"
            f"🟢 نقطه ورود پله‌ای: {s.entry}\n"
            f"🔴 حد ضرر (SL): {s.stop_loss}\n"
            f"🎯 هدف اول (TP1): {s.take_profit_1}\n"
            f"🎯 هدف دوم (TP2): {s.take_profit_2}\n"
            f"⚖️ نسبت R:R: {s.risk_reward}\n\n"
            f"⚠️ {s.note}"
        )
        return

    if mode == "ANALYSIS":
        sym_key, info = get_market_info(text)
        await update.message.reply_text(
            f"📊 تحلیل تکنیکال: {info['name']}\n\n"
            f"▫️ قیمت مبنا: {info['price']}\n"
            f"▫️ حمایت کلیدی: {info['sup']}\n"
            f"▫️ مقاومت پیش‌رو: {info['res']}\n"
            f"▫️ وضعیت روند: {info['trend']}\n\n"
            "💡 استراتژی: منتظر تاییدیه واکنش در حمایت یا تثبیت بالای مقاومت بمانید."
        )
        return

    if mode == "RISK" or ("دلار" in text):
        await update.message.reply_text(get_risk_management_guideline(text), reply_markup=main_menu_keyboard())
        USER_MODES[user_id] = None
        return

    # 4. تایپ مستقیم نماد در منوی اصلی
    sym_key, info = get_market_info(text)
    s = generate_setup(sym_key, info["price"], info["sup"], info["res"])
    await update.message.reply_text(
        f"🔎 نماد شناسایی شد: {info['name']}\n"
        f"💵 قیمت: {info['price']} | حمایت: {info['sup']} | مقاومت: {info['res']}\n\n"
        f"🟢 ورود ستاپ: {s.entry} | 🔴 حد ضرر: {s.stop_loss}\n"
        f"🎯 اهداف: {s.take_profit_1} و {s.take_profit_2}",
        reply_markup=main_menu_keyboard()
    )

# ================== وب‌سرور سلامت Render ==================

async def health_check(request):
    return web.Response(text="Robo7Alvand is Live and Healthy!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Health server running on port %s", PORT)

async def main():
    await start_web_server()
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    logger.info("Bot polling is active...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
