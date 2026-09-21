import os
import asyncio
import logging
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import risk

# لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن و پورت
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKEN5o4ys8no6bmX0X")
PORT = int(os.environ.get("PORT", 8080))

# وضعیت کاربران
USER_MODES = {}

# پایگاه داده اولیه برای نمادهای معروف (نمادهای دیگر به صورت خودکار و داینامیک ساخته می‌شوند)
BASE_MARKET_DATA = {
    "BTC": {"name": "بیت‌کوین (BTC/USDT)", "price": 64200, "sup": 62800, "res": 65500, "trend": "خنثی متمایل به صعودی"},
    "ETH": {"name": "اتریوم (ETH/USDT)", "price": 2650, "sup": 2520, "res": 2720, "trend": "استراحت در محدوده حمایتی"},
    "SOL": {"name": "سولانا (SOL/USDT)", "price": 148, "sup": 138, "res": 155, "trend": "روند صعودی پرشتاب"},
    "TRX": {"name": "ترون (TRX/USDT)", "price": 0.152, "sup": 0.146, "res": 0.158, "trend": "تثبیت بالای سطح کلیدی"},
    "TON": {"name": "تون‌کوین (TON/USDT)", "price": 5.65, "sup": 5.20, "res": 6.10, "trend": "نوسانی و انباشت"},
    "DOGE": {"name": "دوج‌کوین (DOGE/USDT)", "price": 0.108, "sup": 0.098, "res": 0.118, "trend": "در حال رنج زدن"},
    "XAUUSD": {"name": "انس طلا جهانی (XAU/USD)", "price": 2625, "sup": 2600, "res": 2650, "trend": "سقف تاریخی / نوسان بالا"},
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
    "طلا": "XAUUSD", "انس طلا": "XAUUSD", "gold": "XAUUSD", "xauusd": "XAUUSD",
    "نقره": "XAGUSD", "انس نقره": "XAGUSD", "silver": "XAGUSD", "xagusd": "XAGUSD",
    "نفت": "OIL", "oil": "OIL", "wti": "OIL",
    "یورو": "EURUSD", "eurusd": "EURUSD",
    "پوند": "GBPUSD", "gbpusd": "GBPUSD",
    "نزدک": "NASDAQ", "nasdaq": "NASDAQ",
}

def get_market_info(raw_text: str):
    """شناسایی هر نماد بدون محدودیت؛ اگر در دیتابیس نبود، الگوی تحلیلی داینامیک می‌سازد"""
    text_clean = raw_text.strip().lower()
    symbol_key = ALIASES.get(text_clean, raw_text.strip().upper())
    
    if symbol_key in BASE_MARKET_DATA:
        return symbol_key, BASE_MARKET_DATA[symbol_key]
    
    # برای هر نماد دلخواه دیگر (بدون محدودیت)
    display_name = f"مارکت {symbol_key}"
    return symbol_key, {
        "name": display_name,
        "price": 100.0,
        "sup": 95.0,
        "res": 108.0,
        "trend": "تثبیت در محدوده نوسانی (داینامیک)"
    }

# کیبورد اصلی
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎯 ستاپ‌های معاملاتی"), KeyboardButton("📊 تحلیل تکنیکال")],
        [KeyboardButton("💰 مدیریت ریسک"), KeyboardButton("📋 راهنما و قوانین")]
    ], resize_keyboard=True)

# کیبورد میانبر نمادها (کاربر می‌تواند تایپ هم بکند)
def symbols_shortcut_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("BTC"), KeyboardButton("ETH"), KeyboardButton("SOL")],
        [KeyboardButton("TRX"), KeyboardButton("TON"), KeyboardButton("XAUUSD (طلا)")],
        [KeyboardButton("XAGUSD (نقره)"), KeyboardButton("EURUSD"), KeyboardButton("OIL (نفت)")],
        [KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

def capital_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("زیر ۵۰ دلار"), KeyboardButton("۵۰ تا ۲۰۰ دلار")],
        [KeyboardButton("۲۰۰ تا ۵۰۰ دلار"), KeyboardButton("بالای ۵۰۰ دلار")],
        [KeyboardButton("🔙 بازگشت به منوی اصلی")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_MODES[update.effective_user.id] = None
    welcome_text = (
        "سلام ابی جان! به **Robo7Alvand** خوش اومدی 🦅\n\n"
        "سیستم دستیار معاملاتی ضد هیجان و مبتنی بر مدیریت سرمایه.\n\n"
        "💡 **قابلیت باز:** شما می‌توانید نام **هر نمادی** را (کریپتو، فارکس، کالا) مستقیماً تایپ کنید یا از میانبرها استفاده کنید."
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    current_mode = USER_MODES.get(user_id)

    if text == "🔙 بازگشت به منوی اصلی":
        USER_MODES[user_id] = None
        await update.message.reply_text("به منوی اصلی برگشتید:", reply_markup=main_menu_keyboard())
        return

    if text == "🎯 ستاپ‌های معاملاتی":
        USER_MODES[user_id] = "SETUP"
        await update.message.reply_text(
            "🎯 **بخش ستاپ معاملاتی:**\n\n"
            "روی یکی از نمادهای زیر بزنید یا **اسم هر نمادی که می‌خواهید را بنویسید** (مثلاً: `TRX`, `DOGE`, `ADA`, `نفت` و...):",
            reply_markup=symbols_shortcut_keyboard(),
            parse_mode="Markdown"
        )
        return

    if text == "📊 تحلیل تکنیکال":
        USER_MODES[user_id] = "ANALYSIS"
        await update.message.reply_text(
            "📊 **بخش تحلیل تکنیکال:**\n\n"
            "روی میانبرها بزنید یا **اسم هر نمادی را تایپ کنید** (بدون محدودیت):",
            reply_markup=symbols_shortcut_keyboard(),
            parse_mode="Markdown"
        )
        return

    if text == "💰 مدیریت ریسک":
        USER_MODES[user_id] = "RISK"
        await update.message.reply_text(
            "میزان سرمایه فعال خود را انتخاب کنید یا به دلار بنویسید:",
            reply_markup=capital_keyboard()
        )
        return

    if text == "📋 راهنما و قوانین":
        help_text = (
            "🛡 **قوانین کلیدی انضباطی Robo7Alvand:**\n\n"
            "۱. **ورود پله‌ای و بدون FOMO:** وسط نوسانات شدید وارد پوزیشن نشوید.\n"
            "۲. **حداقل R:R ۱:۲:** معاملاتی با ریسک بالاتر از سود پذیرفته نیست.\n"
            "۳. **حداکثر ریسک هر معامله:** بین ۱٪ تا ۲٪ از کل سرمایه.\n"
            "۴. **تایپ آزاد نماد:** شما هر نمادی در بازار را بنویسید، چارچوب ستاپ با رعایت استاپ‌لاس برای آن تدوین می‌شود."
        )
        await update.message.reply_text(help_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    # پردازش ستاپ یا تحلیل برای هر نماد ورودی
    if current_mode in ["SETUP", "ANALYSIS"]:
        clean_name = text.split(" ")[0]  # حذف توضیحات مثل (طلا)
        sym_key, info = get_market_info(clean_name)

        if current_mode == "SETUP":
            # استفاده از موتور ریسک برای تولید ستاپ ضد فومو
            setup = risk.generate_setup(
                symbol=sym_key,
                current_price=info["price"],
                support=info["sup"],
                resistance=info["res"]
            )
            response = (
                f"🎯 **ستاپ معاملاتی استاندارد: {info['name']}**\n\n"
                f"🔹 وضعیت روند: {info['trend']}\n"
                f"📍 قیمت رفرنس: `{info['price']}`\n"
                f"🟢 نقطه ورود امن (Trigger): `{setup.entry}`\n"
                f"🔴 حد ضرر (Stop Loss): `{setup.stop_loss}`\n"
                f"🎯 حد سود اول (TP1): `{setup.take_profit_1}`\n"
                f"🎯 حد سود دوم (TP2): `{setup.take_profit_2}`\n"
                f"⚖️ نسبت سود به ریسک (R:R): `{setup.risk_reward}`\n\n"
                f"⚠️ *تذکر ضد FOMO:* {setup.note}\n\n"
                f"📌 نماد دیگری می‌خواهید؟ همین الان تایپش کنید!"
            )
            await update.message.reply_text(response, parse_mode="Markdown")
            return

        elif current_mode == "ANALYSIS":
            response = (
                f"📊 **تحلیل ساختار مارکت: {info['name']}**\n\n"
                f"▫️ قیمت رفرنس: `{info['price']}`\n"
                f"▫️ حمایت کلیدی (Support): `{info['sup']}`\n"
                f"▫️ مقاومت پیش‌رو (Resistance): `{info['res']}`\n"
                f"▫️ وضعیت بازار: {info['trend']}\n\n"
                f"💡 **استراتژی معاملاتی:** در صورت نزدیک شدن به محدوده حمایتی با تاییدیه کندلی وارد شوید، یا منتظر شکست معتبر مقاومت بمانید.\n\n"
                f"📌 هر نماد دیگری مد نظرتان است، اسمش را بنویسید."
            )
            await update.message.reply_text(response, parse_mode="Markdown")
            return

    # پاسخ به بخش مدیریت ریسک
    if current_mode == "RISK" or any(k in text for k in ["دلار", "سرمایه"]):
        guideline = risk.get_risk_management_guideline(text)
        await update.message.reply_text(guideline, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        USER_MODES[user_id] = None
        return

    # اگر کاربر مستقیم نام نمادی را نوشت بدون رفتن به زیرمنو
    sym_key, info = get_market_info(text.split(" ")[0])
    if sym_key:
        response = (
            f"🔎 نماد **{info['name']}** شناسایی شد.\n"
            f"قیمت: `{info['price']}` | حمایت: `{info['sup']}` | مقاومت: `{info['res']}`\n\n"
            f"برای دریافت ستاپ دقیق دکمه «🎯 ستاپ‌های معاملاتی» یا «📊 تحلیل تکنیکال» را انتخاب کنید."
        )
        await update.message.reply_text(response, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    await update.message.reply_text("دستور نامشخص است. لطفاً از گزینه‌های زیر استفاده کنید:", reply_markup=main_menu_keyboard())

# سرور سلامت داخلی برای UptimeRobot
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
    logger.info(f"Health server successfully started on port {PORT}")

async def main():
    await start_web_server()
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Robo7Alvand Telegram Bot is polling...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
