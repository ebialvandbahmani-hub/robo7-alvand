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

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENu0i7wusuotX0X")
PORT = int(os.environ.get("PORT", 8080))

USER_MODES = {}

# ================== موتور ریسک داخلی ==================

@dataclass
class TradeSetup:
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: str
    note: str

def generate_setup(symbol: str, current_price: float, support: float, resistance: float) -> TradeSetup:
    """ستاپ ضد FOMO: ورود نزدیک حمایت، حداقل R:R برابر 1:2"""
    entry = support * 1.005
    stop_loss = support * 0.985
    risk_amount = entry - stop_loss
    tp1 = entry + (risk_amount * 2)
    tp2 = entry + (risk_amount * 3)
    return TradeSetup(
        entry=round(entry, 6),
        stop_loss=round(stop_loss, 6),
        take_profit_1=round(tp1, 6),
        take_profit_2=round(tp2, 6),
        risk_reward="1:2 (TP1) - 1:3 (TP2)",
        note="ورود فقط به صورت پله‌ای نزدیک حمایت؛ در وسط رنج یا هنگام هیجان (FOMO) پوزیشن باز نکنید. حفظ سرمایه اولویت اول است."
    )

def get_risk_management_guideline(text: str) -> str:
    """راهنمای مدیریت ریسک بر اساس سرمایه کاربر (منطق با اعداد انگلیسی)"""
    capital = 100.0
    if "بالای" in text:
        capital = 1000.0
    elif "200" in text:
        capital = 300.0
    elif "50" in text:
        capital = 100.0
    risk_amount = capital * 0.02
    body = (
        "سرمایه تخمینی: {} دلار\n"
        "حداکثر ریسک هر معامله (۲٪): {} دلار\n"
        "حداکثر پوزیشن باز همزمان: ۲ عدد\n"
        "روش ورود: پله‌ای (نصف حجم در تریگر، نصف در تاییدیه)"
    ).format(int(capital), int(risk_amount))
    return (
        "🛡 راهنمای مدیریت ریسک Robo7Alvand:\n\n"
        + body + "\n\n"
        "⚖️ قوانین ثابت:\n"
        "۱. حداقل نسبت سود به ریسک: 1:2\n"
        "۲. بدون مارتینگل و بدون میانگین کاهشی\n"
        "۳. بدون FOMO؛ فقط ستاپ‌های تعریف‌شده\n"
        "۴. حفظ سرمایه، اولویت اول است."
    )

# ================== دیتابیس نمادها ==================

BASE_MARKET_DATA = {
    "BTC": {"name": "بیت‌کوین (BTC/USDT)", "price": 64200, "sup": 62800, "res": 65500, "trend": "خنثی متمایل به صعودی"},
    "ETH": {"name": "اتریوم (ETH/USDT)", "price": 2650, "sup": 2520, "res": 2720, "trend": "استراحت در محدوده حمایتی"},
    "SOL": {"name": "سولانا (SOL/USDT)", "price": 148, "sup": 138, "res": 155, "trend": "روند صعودی پرشتاب"},
    "TRX": {"name": "ترون (TRX/USDT)", "price": 0.152, "sup": 0.146, "res": 0.158, "trend": "تثبیت بالای سطح کلیدی"},
    "TON": {"name": "تون‌کوین (TON/USDT)", "price": 5.65, "sup": 5.20, "res": 6.10, "trend": "نوسانی و انباشت"},
    "DOGE": {"name": "دوج‌کوین (DOGE/USDT)", "price": 0.108, "sup": 0.098, "res": 0.118, "trend": "رنج و نوسانی"},
    "ADA": {"name": "کاردانو (ADA/USDT)", "price": 0.365, "sup": 0.345, "res": 0.385, "trend": "فاز تجمیع"},
    "XAUUSD": {"name": "انس طلا جهانی (XAU/USD)", "price": 2625, "sup": 2600, "res": 2650, "trend": "نوسان بالا در سقف تاریخی"},
    "XAGUSD": {"name": "انس نقره جهانی (XAG/USD)", "price": 31.2, "sup": 30.5, "res": 32.4, "trend": "تثبیت روند صعودی"},
    "OIL": {"name": "نفت خام (WTI)", "price": 71.5, "sup": 69.2, "res": 73.8, "trend": "واکنش به سطوح ژئوپلیتیک"},
    "EURUSD": {"name": "یورو به دلار (EUR/USD)", "price": 1.114, "sup": 1.108, "res": 1.121, "trend": "فشار خرید ضعیف"},
    "GBPUSD": {"name": "پوند به دلار (GBP/USD)", "price": 1.328, "sup": 1.319, "res": 1.336, "trend": "روند خنثی"},
    "NASDAQ": {"name": "شاخص نزدک (NQ)", "price": 19850, "sup": 19600, "res": 20100, "trend": "صعودی"},
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
    "پوند": "GBPUSD", "gbpusd": "GBPUSD",
    "نزدک": "NASDAQ", "nasdaq": "NASDAQ",
}

def get_market_info(raw_text: str):
    """شناسایی هر نماد بدون محدودیت؛ اگر در دیتابیس نبود، چارچوب داینامیک ساخته می‌شود"""
    text_clean = raw_text.strip().lower()
    symbol_key = ALIASES.get(text_clean, raw_text.strip().upper())
    if symbol_key in BASE_MARKET_DATA:
        return symbol_key, BASE_MARKET_DATA[symbol_key]
    return symbol_key, {
        "name": "مارکت " + symbol_key,
        "price": 100.0, "sup": 95.0, "res": 108.0,
        "trend": "تثبیت در محدوده نوسانی (داینامیک)"
    }

# ================== کیبوردها ==================

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎯 ستاپ‌های معاملاتی"), KeyboardButton("📊 تحلیل تکنیکال")],
        [KeyboardButton("💰 مدیریت ریسک"), KeyboardButton("📋 راهنما و قوانین")]
    ], resize_keyboard=True)

def symbols_shortcut_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("BTC"), KeyboardButton("ETH"), KeyboardButton("SOL")],
        [KeyboardButton("TRX"), KeyboardButton("TON"), KeyboardButton("DOGE")],
        [KeyboardButton("XAUUSD (طلا)"), KeyboardButton("XAGUSD (نقره)"), KeyboardButton("OIL (نفت)")],
        [KeyboardButton("EURUSD"), KeyboardButton("NASDAQ"), KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

def capital_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("زیر ۵۰ دلار"), KeyboardButton("۵۰ تا ۲۰۰ دلار")],
        [KeyboardButton("۲۰۰ تا ۵۰۰ دلار"), KeyboardButton("بالای ۵۰۰ دلار")],
        [KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

# ================== هندلرها ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_MODES[update.effective_user.id] = None
    await update.message.reply_text(
        "سلام ابی جان! به Robo7Alvand خوش اومدی 🦅\n\n"
        "دستیار معاملاتی ضد هیجان، مبتنی بر مدیریت سرمایه.\n\n"
        "💡 نام هر نمادی را تایپ کنید (مثل: TRX یا ADA یا نفت) یا از دکمه‌های میانبر استفاده کنید.",
        reply_markup=main_menu_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    mode = USER_MODES.get(user_id)

    if text == "🔙 بازگشت به منوی اصلی":
        USER_MODES[user_id] = None
        await update.message.reply_text("به منوی اصلی برگشتید:", reply_markup=main_menu_keyboard())
        return

    if text == "🎯        await updateهای معاملاتی":
        USER_MODES[user_id] = "SETUP"
        await update.message.reply_text(
            "🎯 بخش ستاپ معاملاتی\n\nنماد را از دکمه‌ها انتخاب کنید یا اسم هر نمادی را تایپ کنید (بدون محدودیت):",
            reply_markup=symbols_shortcut_keyboard()
        )
        return

    if text == "📊 تحلیل تکنیکال":
        USER_MODES[user_id] = "ANALYSIS"
        await update.message.reply_text(
            "📊 بخش تحلیل تکنیکال\n\nنماد را انتخاب یا تایپ کنید:",
            reply_markup=symbols_shortcut_keyboard()
        )
        return

    if text == "💰 مدیریت ریسک":
        USER_MODES[user_id] = "RISK"
        await update.message.reply_text("میزان سرمایه فعال خود را انتخاب کنید:", reply_markup=capital_keyboard())
        return

    if text == "📋 راهنما و قوانین":
        await update.message.reply_text(
            "🛡 قوانین کلیدی Robo7Alvand:\n\n"
            "۱. ورود پله‌ای، بدون FOMO\n"
            "۲. حداقل R:R برابر 1:2\n"
            "۳. حداکثر ریسک هر معامله: ۲٪ سرمایه\n"
            "۴. هر نمادی را تایپ کنید، ستاپ و تحلیل دریافت کنید.",
            reply_markup=main_menu_keyboard()
        )
        return

    if mode in ["SETUP", "ANALYSIS"]:
        sym_key, info = get_market_info(text.split(" ")[0])
        if mode == "SETUP":
            s = generate_setup(sym_key, info["price"], info["sup"], info["res"])
            await update.message.reply_text(
                "🎯 ستاپ معاملاتی: " + info["name"] + "\n\n"
                "🔹 روند: " + info["trend"] + "\n"
                "📍 قیمت رفرنس: " + str(info["price"]) + "\n"
                "🟢 نقطه ورود: " + str(s.entry) + "\n"
                "🔴 حد ضرر: " + str(s.stop_loss) + "\n"
                "🎯 TP1: " + str(s.take_profit_1) + "\n"
                "🎯 TP2: " + str(s.take_profit_2) + "\n"
                "⚖️ R:R: " + s.risk_reward + "\n\n"
                "⚠️ " + s.note
            )
        else:
            await update.message.reply_text(
                "📊 تحلیل: " + info["name"] + "\n\n"
                "▫️ قیمت: " + str(info["price"]) + "\n"
                "▫️ حمایت: " + str(info["sup"]) + "\n"
                "▫️ مقاومت: " + str(info["res"]) + "\n"
                "▫️ وضعیت: " + info["trend"] + "\n\n"
                "💡 نزدیک حمایت با تاییدیه کندلی وارد شوید یا شکست معتبر مقاومت را بخرید."
            )
        return

    if mode == "RISK" or ("دلار" in text):
        await update.message.reply_text(
            get_risk_management_guideline(text),
            reply_markup=main_menu_keyboard()
        )
        USER_MODES[user_id] = None
        return

    # ورود مستقیم نام نماد بدون رفتن به زیرمنو
    sym_key, info = get_market_info(text.split(" ")[0])
    await update.message.reply_text(
        "🔎 نماد شناسایی شد: " + info["name"] + "\n"
        "قیمت: " + str(info["price"]) + " | حمایت: " + str(info["sup"]) + " | مقاومت: " + str(info["res"]) + "\n\n"
        "برای ستاپ کامل، «🎯 ستاپ‌های معاملاتی» را بزنید.",
        reply_markup=main_menu_keyboard()
    )

# ================== سرور سلامت ==================

async def health_check(request):
    return web.Response(text="Robo7Alvand Core is ACTIVE and Running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Health server started on port %s", PORT)

async def main():
    await start_web_server()
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    logger.info("Robo7Alvand is polling...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
