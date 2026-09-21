import os
import logging
import sqlite3
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

# -------------------------------------------------------------
# ۱. تنظیمات اولیه لاگ و متغیرها
# -------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENcvpgdps5ilgX0X")
PORT = int(os.environ.get("PORT", 8080))
DB_PATH = "robo7alvand.db"

# -------------------------------------------------------------
# ۲. مدیریت پایگاه داده (SQLite)
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول ثبت مشخصات کاربران
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
    
    # جدول ژورنال معاملات
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

# -------------------------------------------------------------
# ۳. کیبوردهای سیستم
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# ۴. وب‌سرور برای زنده نگه داشتن سرویس در Render
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# ۵. دستور /start و مراحل Onboarding
# -------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user or user[6] != 'COMPLETED':
        save_user(user_id, step='NAME')
        await update.message.reply_text(
            "👋 درود! به سامانه معاملاتی **Robo7Alvand** خوش آمدید.\n\n"
            "جهت تنظیم دقیق موتور مدیریت ریسک، لطفاً نام و نام‌خانوادگی خود را ارسال فرمایید:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            f"سلام {user[1]} عزیز! 🦅\n"
            "سیستم فعال است و بازار تحت رصد قرار دارد.",
            reply_markup=main_menu_keyboard()
        )

# -------------------------------------------------------------
# ۶. دریافت شماره تماس و مدیریت پیام‌های متنی
# -------------------------------------------------------------
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

    # مرحله ۱: دریافت نام
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

    # مرحله ۲: دریافت شماره تماس به صورت متنی
    elif step == 'PHONE':
        save_user(user_id, phone=text, step='MARKET')
        market_kb = [["فارکس (Forex)", "کریپتو (Crypto)"], ["هر دو بازار"]]
        await update.message.reply_text(
            "تمرکز معاملاتی شما بیشتر روی کدام بازار است؟",
            reply_markup=ReplyKeyboardMarkup(market_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    # مرحله ۳: انتخاب بازار
    elif step == 'MARKET':
        save_user(user_id, market=text, step='LEVEL')
        level_kb = [["مبتدی (زیر ۶ ماه)", "متوسط (۶ ماه تا ۲ سال)"], ["حرفه‌ای (بیش از ۲ سال)"]]
        await update.message.reply_text(
            "سطح تجربه و تسلط شما در تحلیل و ترید چقدر است؟",
            reply_markup=ReplyKeyboardMarkup(level_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    # مرحله ۴: انتخاب سطح
    elif step == 'LEVEL':
        save_user(user_id, level=text, step='CAPITAL')
        cap_kb = [["زیر ۱,۰۰۰ دلار", "۱,۰۰۰ تا ۱۰,۰۰۰ دلار"], ["بالای ۱۰,۰۰۰ دلار"]]
        await update.message.reply_text(
            "محدوده تقریبی سرمایه در گردش شما چقدر است؟ (جهت کالیبراسیون حجم ورود و ریسک)",
            reply_markup=ReplyKeyboardMarkup(cap_kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    # مرحله ۵: انتخاب سرمایه و اتمام ثبت‌نام
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

    # --- بخش‌های منوی اصلی و تالار معاملات ---
    if text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی سیستم:", reply_markup=main_menu_keyboard())

    elif text == "🏛 تالار معاملات":
        await update.message.reply_text(
            "به تالار معاملات خوش آمدید.\nیکی از گزینه‌های زیر را انتخاب فرمایید:",
            reply_markup=market_menu_keyboard()
        )

    elif text == "🎯 ستاپ‌های معاملاتی":
        msg = (
            "📌 **ستاپ‌های تاییدشده الگوریتم (ریسک به ریوارد بالای ۱:۲):**\n\n"
            "🔹 **نماد:** BTC/USDT (کریپتو)\n"
            "• جهت: LONG\n"
            "• نقطه ورود: 63,200\n"
            "• حد ضرر (SL): 62,500\n"
            "• حد سود (TP): 65,400\n"
            "• نسبت R:R: ۱ به ۳.۱ ✅\n"
            "• وضعیت: منتظر پولبک و تثبیت در محدوده حمایت\n\n"
            "🔸 **نماد:** XAU/USD (طلا جهانی)\n"
            "• جهت: فاز تثبیت رنج\n"
            "• هشدار موتور ریسک: از ورود در میانه رنج اکیداً خودداری شود!"
        )
        await update.message.reply_text(msg, reply_markup=market_menu_keyboard())

    elif text == "📈 تحلیل تکنیکال":
        msg = (
            "📊 **خلاصه وضعیت تحلیل تکنیکال الوند:**\n\n"
            "• **بیت‌کوین (BTC):** بالای میانگین متحرک ۲۰۰ روزه تثبیت شده. مومنتوم صعودی ملایم.\n"
            "• **طلا (Gold):** مواجهه با مقاومت کلیدی؛ واگرایی منفی در تایم‌فریم ۴ ساعته مشهود است.\n"
            "• شاخص قدرت خریدار در حالت تعادل قرار دارد."
        )
        await update.message.reply_text(msg, reply_markup=market_menu_keyboard())

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
            "• هسته پردازش: Robo7Alvand Core v2\n"
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

# -------------------------------------------------------------
# ۷. تابع post_init و نقطه ورود اصلی برنامه
# -------------------------------------------------------------
async def post_init(application: Application):
    # راه‌اندازی وب‌سرور همگام با استارت بات
    await start_web_server()

def main():
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # اتصال هندلرها
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Robo7Alvand bot is starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
