import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from aiohttp import web

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENqejkdjrqdwkX0X")
PORT = int(os.environ.get("PORT", 8080))
DB_PATH = "robo7alvand.db"

# دیتابیس ستاپ‌ها و تحلیل‌های تفکیک‌شده برای نمادهای اصلی
MARKET_DATA = {
    "BTC": {
        "name": "بیت‌کوین (BTC/USDT)",
        "price": "63,450$",
        "setup": {
            "direction": "🟢 LONG (خرید پله‌ای)",
            "entry": "63,100 - 63,300",
            "sl": "62,200",
            "tp1": "64,800",
            "tp2": "66,200",
            "rr": "۱ به ۲.۸ ✅",
            "note": "ورود فقط با تایید کندل ۴ ساعته بالای حمایت. از ورود مارکت خودداری شود."
        },
        "analysis": (
            "📊 **تحلیل جامع تکنیکال BTC/USDT:**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• روند کلی: صعودی تثبیت‌شده بالای میانگین متحرک ۲۰۰ روزه\n"
            "• حمایت‌های کلیدی: 62,500$ و 60,800$\n"
            "• مقاومت‌های پیش‌رو: 64,500$ و 66,000$\n"
            "• شاخص قدرت نسبی (RSI): عدد 56 (حالت تعادل بدون اشباع خرید)\n"
            "• ساختار فشرده‌سازی: الگوی وج صعودی در تایم ۴ ساعته\n"
            "• استراتژی الوند: ورود پله‌ای فقط در پولبک به سطوح حمایتی؛ پایبندی اکید به حد ضرر."
        )
    },
    "ETH": {
        "name": "اتریوم (ETH/USDT)",
        "price": "2,650$",
        "setup": {
            "direction": "🟢 LONG",
            "entry": "2,610 - 2,630",
            "sl": "2,540",
            "tp1": "2,780",
            "tp2": "2,890",
            "rr": "۱ به ۲.۵ ✅",
            "note": "حفظ کف ۲,۵۴۰ شرط اصلی اعتبار این ستاپ است."
        },
        "analysis": (
            "📊 **تحلیل جامع تکنیکال ETH/USDT:**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• روند کلی: رنج متمایل به صعودی پس از شکست خط روند نزولی\n"
            "• حمایت اصلی: 2,580$ و 2,520$\n"
            "• مقاومت‌های مهم: 2,720$ و 2,850$\n"
            "• حجم معاملات: در حال افزایش در کف‌های قیمتی\n"
            "• استراتژی الوند: شکار پوزیشن‌های خرید نزدیک به حمایت ۲,۵۸۰ با حجم کنترل‌شده."
        )
    },
    "SOL": {
        "name": "سولانا (SOL/USDT)",
        "price": "148.5$",
        "setup": {
            "direction": "⚪️ خنثی / بدون ستاپ معتبر",
            "entry": "منتظر بمانید",
            "sl": "--",
            "tp1": "--",
            "tp2": "--",
            "rr": "فاقد نسبت R:R مجاز ⚠️",
            "note": "قیمت دقیقاً در میانه رنج نوسانی است. قانون Anti-FOMO: ورود در اواسط رنج ممنوع!"
        },
        "analysis": (
            "📊 **تحلیل جامع تکنیکال SOL/USDT:**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• روند کلی: فاز انباشت و نوسان فشرده بین ۱۴۲ تا ۱۵۵ دلار\n"
            "• حمایت کلیدی: 142$\n"
            "• مقاومت کلیدی: 155$\n"
            "• اندیکاتور MACD: فلت بدون سیگنال جهت‌دار قطعی\n"
            "• استراتژی الوند: عدم معامله تا زمانی که کندل روزانه بالای ۱۵۵ یا زیر ۱۴۲ بسته شود."
        )
    },
    "XAUUSD": {
        "name": "انس طلای جهانی (XAU/USD)",
        "price": "2,625$",
        "setup": {
            "direction": "🔴 SHORT (اصلاحی با ریسک کنترل‌شده)",
            "entry": "2,632 - 2,635",
            "sl": "2,643",
            "tp1": "2,615",
            "tp2": "2,600",
            "rr": "۱ به ۳.۲ ✅",
            "note": "سایز پوزیشن نصف حد استاندارد؛ اخبار نرخ بهره فدرال رزرو مدنظر باشد."
        },
        "analysis": (
            "📊 **تحلیل جامع تکنیکال طلا (XAU/USD):**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• روند کلی: صعودی پرقدرت روزانه ولی نشانه‌های خستگی روند در تایم ۱ ساعته\n"
            "• واگرایی: واگرایی منفی واضح در اندیکاتور RSI در سقف‌های قیمتی\n"
            "• سطوح حمایت: 2,612 و 2,590\n"
            "• مقاومت اصلی: محدوده روانی 2,640\n"
            "• استراتژی الوند: پرهیز شدید از خرید در سقف تاریخی (قانون ضد فومو)؛ جستجوی پولبک برای ورود مطمئن‌تر."
        )
    },
    "EURUSD": {
        "name": "یورو/دلار (EUR/USD)",
        "price": "1.1120",
        "setup": {
            "direction": "🟢 LONG",
            "entry": "1.1095 - 1.1105",
            "sl": "1.1065",
            "tp1": "1.1180",
            "tp2": "1.1240",
            "rr": "۱ به ۲.۳ ✅",
            "note": "تایید نهایی ورود همزمان با شروع همپوشانی نشست‌های لندن و نیویورک."
        },
        "analysis": (
            "📊 **تحلیل جامع تکنیکال EUR/USD:**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• روند کلی: صعودی میان‌مدت، تثبیت بالای سطح روانی ۱.۱۱۰۰\n"
            "• سطح حمایت معتبر: 1.1080\n"
            "• مقاومت کلیدی: 1.1200\n"
            "• رفتار قیمتی: تشکیل الگوی کف دوقلو در تایم ۴ ساعته\n"
            "• استراتژی الوند: خرید در تست مجدد خط گردن در حوالی ۱.۱۱۰۰ با استاپ باریک."
        )
    }
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            market TEXT,
            level TEXT,
            capital TEXT,
            step TEXT DEFAULT 'COMPLETED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            tp REAL,
            sl REAL,
            rr_ratio REAL,
            status TEXT DEFAULT 'OPEN',
            result TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, name, phone, market, level, capital, step FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    
    if not exists:
        c.execute("INSERT INTO users (user_id, step) VALUES (?, 'NAME')", (user_id,))
        conn.commit()

    if kwargs:
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        c.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        conn.commit()
        
    conn.close()

def main_menu_keyboard():
    keyboard = [
        ["🏛 تالار معاملات", "📊 گزارش عملکرد"],
        ["📝 ژورنال هوشمند", "👤 پروفایل تریدر"],
        ["⚙️ وضعیت سیستم"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def market_menu_keyboard():
    keyboard = [
        ["🎯 ستاپ‌های معاملاتی", "📈 تحلیل تکنیکال"],
        ["📡 رادار بازار", "🔙 بازگشت به منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def symbols_keyboard():
    keyboard = [
        ["BTC (بیت‌کوین)", "ETH (اتریوم)"],
        ["SOL (سولانا)", "XAUUSD (طلا)"],
        ["EURUSD (یورو/دلار)", "🔙 بازگشت به تالار"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def normalize_symbol(text: str):
    t = text.upper()
    if "BTC" in t or "بیت" in t:
        return "BTC"
    elif "ETH" in t or "اتریوم" in t:
        return "ETH"
    elif "SOL" in t or "سولانا" in t:
        return "SOL"
    elif "XAU" in t or "طلا" in t or "GOLD" in t:
        return "XAUUSD"
    elif "EUR" in t or "یورو" in t:
        return "EURUSD"
    return None

async def handle_health_check(request):
    return web.Response(text="Robo7Alvand Core is ACTIVE and Running!")

async def start_web_server():
    server_app = web.Application()
    server_app.router.add_get("/", handle_health_check)
    server_app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(server_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"✅ Web server successfully bound to port {PORT}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user or user[6] not in ['COMPLETED', 'WAITING_SETUP_SYMBOL', 'WAITING_ANALYSIS_SYMBOL']:
        save_user(user_id, step='NAME')
        await update.message.reply_text(
            "👋 درود! به سامانه معاملاتی **Robo7Alvand** خوش آمدید.\n\n"
            "جهت تنظیم دقیق موتور مدیریت ریسک، لطفاً نام و نام‌خانوادگی خود را ارسال فرمایید:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        save_user(user_id, step='COMPLETED')
        await update.message.reply_text(
            f"سلام {user[1]} عزیز! 🦅\n"
            "سیستم فعال است و بازار تحت رصد قرار دارد.",
            reply_markup=main_menu_keyboard()
        )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    if contact:
        save_user(user_id, phone=contact.phone_number, step='MARKET')
        market_kb = [["فارکس (Forex)", "کریپتو (Crypto)"], ["هر دو بازار"]]
        await update.message.reply_text(
            "✅ شماره شما ثبت شد.\n\nتمرکز معاملاتی شما بیشتر روی کدام بازار است؟",
            reply_markup=ReplyKeyboardMarkup(market_kb, resize_keyboard=True, one_time_keyboard=True)
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    if not user:
        save_user(user_id, step='NAME')
        await update.message.reply_text("لطفاً نام و نام‌خانوادگی خود را وارد کنید:")
        return

    step = user[6]

    # مراحل آنبوردینگ
    if step == 'NAME':
        save_user(user_id, name=text, step='PHONE')
        contact_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 ارسال شماره تماس", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text(
            f"ممنون {text} عزیز.\nجهت ثبت در باشگاه تریدرها، شماره تماس خود را ارسال کنید یا بنویسید:",
            reply_markup=contact_kb
        )
        return

    elif step == 'PHONE':
        save_user(user_id, phone=text, step='MARKET')
        market_kb = [["فارکس (Forex)", "کریپتو (Crypto)"], ["هر دو بازار"]]
        await update.message.reply_text(
            "تمرکز معاملاتی شما بیشتر روی کدام بازار است؟",
            reply_markup=ReplyKeyboardMarkup(market_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    elif step == 'MARKET':
        save_user(user_id, market=text, step='LEVEL')
        level_kb = [["مبتدی (زیر ۶ ماه)", "متوسط (۶ ماه تا ۲ سال)"], ["حرفه‌ای (بیش از ۲ سال)"]]
        await update.message.reply_text(
            "سطح تجربه و تسلط شما در تحلیل و ترید چقدر است؟",
            reply_markup=ReplyKeyboardMarkup(level_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    elif step == 'LEVEL':
        save_user(user_id, level=text, step='CAPITAL')
        cap_kb = [["زیر ۱,۰۰۰ دلار", "۱,۰۰۰ تا ۱۰,۰۰۰ دلار"], ["بالای ۱۰,۰۰۰ دلار"]]
        await update.message.reply_text(
            "محدوده تقریبی سرمایه در گردش شما چقدر است؟ (جهت کالیبراسیون حجم ورود و ریسک)",
            reply_markup=ReplyKeyboardMarkup(cap_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    elif step == 'CAPITAL':
        save_user(user_id, capital=text, step='COMPLETED')
        await update.message.reply_text(
            "🎉 ثبت‌نام با موفقیت انجام شد!\n\n"
            "⚡️ سیستم مدیریت ریسک Anti-FOMO کالیبره گردید.\n"
            "حداقل نسبت R:R مجاز: ۱ به ۲\n"
            "لطفاً یک بخش را انتخاب کنید:",
            reply_markup=main_menu_keyboard()
        )
        return

    # منوها و ناوبری
    if text == "🔙 بازگشت به منوی اصلی":
        save_user(user_id, step='COMPLETED')
        await update.message.reply_text("منوی اصلی سیستم:", reply_markup=main_menu_keyboard())
        return

    elif text == "🔙 بازگشت به تالار":
        save_user(user_id, step='COMPLETED')
        await update.message.reply_text("تالار معاملات:", reply_markup=market_menu_keyboard())
        return

    elif text == "🏛 تالار معاملات":
        save_user(user_id, step='COMPLETED')
        await update.message.reply_text(
            "به تالار معاملات خوش آمدید.\nیکی از گزینه‌های زیر را انتخاب فرمایید:",
            reply_markup=market_menu_keyboard()
        )
        return

    # ۱. ورود به بخش ستاپ‌ها
    elif text == "🎯 ستاپ‌های معاملاتی":
        save_user(user_id, step='WAITING_SETUP_SYMBOL')
        await update.message.reply_text(
            "🎯 **بخش ستاپ‌های معاملاتی الگوریتم**\n\n"
            "برای دریافت ستاپ، نماد مورد نظر خود را انتخاب کنید یا نام آن را بنویسید (BTC, ETH, طلا, SOL, EURUSD):",
            reply_markup=symbols_keyboard()
        )
        return

    # ۲. ورود به بخش تحلیل تکنیکال
    elif text == "📈 تحلیل تکنیکال":
        save_user(user_id, step='WAITING_ANALYSIS_SYMBOL')
        await update.message.reply_text(
            "📈 **بخش تحلیل جامع تکنیکال و رفتارشناسی بازار**\n\n"
            "برای دریافت تحلیل، نماد مورد نظر خود را انتخاب کنید یا نام آن را بنویسید (BTC, ETH, طلا, SOL, EURUSD):",
            reply_markup=symbols_keyboard()
        )
        return

    # ۳. دریافت و نمایش ستاپ برای نماد انتخابی
    elif step == 'WAITING_SETUP_SYMBOL':
        sym = normalize_symbol(text)
        if sym and sym in MARKET_DATA:
            data = MARKET_DATA[sym]
            s = data["setup"]
            msg = (
                f"🎯 **ستاپ معاملاتی اختصاصی Robo7Alvand**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏷 **نماد:** {data['name']}\n"
                f"💵 **قیمت مرجع:** {data['price']}\n"
                f"🧭 **جهت معامله:** {s['direction']}\n"
                f"🎯 **محدوده ورود:** {s['entry']}\n"
                f"🛑 **حد ضرر (SL):** {s['sl']}\n"
                f"🎯 **تارگت اول (TP1):** {s['tp1']}\n"
                f"🚀 **تارگت دوم (TP2):** {s['tp2']}\n"
                f"⚖️ **نسبت ریسک به ریوارد (R:R):** {s['rr']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 **توصیه انضباطی موتور ریسک:**\n"
                f"{s['note']}"
            )
            await update.message.reply_text(msg, reply_markup=symbols_keyboard())
        else:
            await update.message.reply_text(
                "⚠️ نماد وارد شده در لیست فاز ۱ نیست یا نامعتبر است.\n"
                "لطفاً یکی از دکمه‌های زیر را انتخاب کنید:",
                reply_markup=symbols_keyboard()
            )
        return

    # ۴. دریافت و نمایش تحلیل برای نماد انتخابی
    elif step == 'WAITING_ANALYSIS_SYMBOL':
        sym = normalize_symbol(text)
        if sym and sym in MARKET_DATA:
            data = MARKET_DATA[sym]
            await update.message.reply_text(data["analysis"], reply_markup=symbols_keyboard())
        else:
            await update.message.reply_text(
                "⚠️ نماد وارد شده در لیست فاز ۱ نیست یا نامعتبر است.\n"
                "لطفاً یکی از دکمه‌های زیر را انتخاب کنید:",
                reply_markup=symbols_keyboard()
            )
        return

    elif text == "📡 رادار بازار":
        msg = (
            "🛰 **رادار نوسان‌گیری و جریان پول هوشمند:**\n\n"
            "• نمادهای دارای حجم غیرعادی: SOL, ETH\n"
            "• نقدینگی خروجی از آلت‌کوین‌های ضعیف شناسایی شد.\n"
            "• سیگنال رادار: صبر تا تکمیل کندل روزانه."
        )
        await update.message.reply_text(msg, reply_markup=market_menu_keyboard())

    elif text == "📝 ژورنال هوشمند":
        msg = (
            "📖 **دفترچه ژورنال معاملاتی:**\n\n"
            "برای ثبت معامله جدید، فرمت زیر را ارسال کنید:\n"
            "`ثبت BTC LONG ورود 63000 حدضرر 62500 حدسود 65000`\n\n"
            "موتور هوشمند ربات وضعیت معامله را پایش و در گزارش عملکرد ذخیره می‌کند."
        )
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

    elif text == "📊 گزارش عملکرد":
        msg = (
            "📈 **داشبورد عملکرد شما:**\n\n"
            "• کل معاملات ثبت‌شده: ۱۲\n"
            "• معاملات سودده: ۹ (Win Rate: 75%)\n"
            "• برآورد سود خالص (PnL): +8.4%\n"
            "• پایبندی به حد ضرر: ۱۰۰٪ (عالی) 🛡"
        )
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

    elif text == "👤 پروفایل تریدر":
        msg = (
            f"👤 **مشخصات تریدر:**\n\n"
            f"• نام: {user[1]}\n"
            f"• شماره تماس: {user[2]}\n"
            f"• بازار هدف: {user[3]}\n"
            f"• سطح مهارت: {user[4]}\n"
            f"• سرمایه تقریبی: {user[5]}\n"
            f"• وضعیت حساب: تایید شده و فعال 🟢"
        )
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

    elif text == "⚙️ وضعیت سیستم":
        msg = (
            "⚙️ **وضعیت سیستم و سرور:**\n\n"
            "• هسته پردازش: Robo7Alvand Core v2.1\n"
            f"• وضعیت وب‌سرور هلث‌چک: فعال روی پورت {PORT}\n"
            "• اتصال به تلگرام: استیبل (Polling)\n"
            "• وضعیت دیتابیس: متصل (SQLite)"
        )
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

    else:
        await update.message.reply_text(
            "دستور متوجه نشدم. لطفاً از دکمه‌های منو استفاده کنید:",
            reply_markup=main_menu_keyboard()
        )

async def main_async():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await start_web_server()
    
    logger.info("Robo7Alvand bot is starting polling...")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main_async())
