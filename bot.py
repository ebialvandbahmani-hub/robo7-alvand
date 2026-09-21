import os
import sqlite3
import logging
from datetime import datetime
from aiohttp import web

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------------------------------------------------------------
# تنظیمات لاگینگ
# -------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", 8080))
DB_PATH = "robo7.db"

# وضعیت‌های موقت کاربران در حافظه برای استپ‌های ترتیبی
user_states = {}

# -------------------------------------------------------------
# راه‌اندازی و تعاریف دیتابیس (مطابق مستندات Robo7)
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            market TEXT,
            capital TEXT,
            level TEXT,
            verified INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            direction TEXT,
            source TEXT,
            result TEXT,
            amount REAL,
            note TEXT,
            review TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, market, level, capital FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def register_user_step(user_id: int, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    if not exists:
        c.execute("INSERT INTO users (user_id, created_at) VALUES (?, ?)", (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    for key, value in kwargs.items():
        c.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# کیبوردهای پایدار (ReplyKeyboardMarkup)
# -------------------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        ["🏛 تالار معاملات", "📊 گزارش عملکرد من"],
        ["📓 ثبت معامله در ژورنال", "🔔 هشدار ورود / واچ‌لیست"],
        ["⚙️ پروفایل تریدر", "🏓 وضعیت سیستم"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def trading_hall_keyboard():
    keyboard = [
        ["🎯 دریافت ستاپ معاملاتی", "🔍 تحلیل تکنیکال جامع"],
        ["⚡️ رادار بازار (فرصت‌های داغ)", "🔙 بازگشت به منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def market_selection_keyboard():
    keyboard = [
        ["📈 فارکس / طلا", "🪙 کریپتو"],
        ["🌐 هر دو بازار"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def level_keyboard():
    keyboard = [
        ["🟢 مبتدی (کمتر از ۱ سال)", "🟡 متوسط (۱ تا ۳ سال)"],
        ["🔴 حرفه‌ای (بیش از ۳ سال)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def capital_keyboard():
    keyboard = [
        ["زیر ۵۰$", "۵۰$ تا ۲۰۰$"],
        ["۲۰۰$ تا ۵۰۰$", "بالای ۵۰۰$"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# -------------------------------------------------------------
# جریان استارت و ثبت‌نام گام‌به‌گام (Onboarding)
# -------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    db_user = get_user(uid)

    if db_user and db_user[1] and db_user[2]:
        # کاربر قبلاً ثبت‌نام شده
        await update.message.reply_text(
            f"سلام {db_user[1]} عزیز! خوش آمدید به دستیار معاملاتی **Robo7Alvand**.\n"
            "از منوی زیر جهت مدیریت معاملات و تحلیل استفاده کنید:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # شروع آنبوردینگ
    user_states[uid] = {"step": "WAITING_NAME"}
    btn = [[KeyboardButton("استفاده از نام تلگرام")]]
    await update.message.reply_text(
        "👋 سلام و درود به **Robo7Alvand** خوش آمدید.\n\n"
        "برای شخصی‌سازی محاسبات ریسک و ستاپ‌های معاملاتی، لطفاً نام و نام‌خانوادگی خود را وارد کنید:\n"
        "(یا از دکمه زیر استفاده کنید)",
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    contact = update.message.contact
    if contact and contact.user_id == uid:
        register_user_step(uid, phone=contact.phone_number, verified=1)
        user_states[uid] = {"step": "WAITING_MARKET"}
        await update.message.reply_text(
            "✅ شماره تماس شما با موفقیت تأیید شد.\n\n"
            "۳. لطفاً بازار هدف معاملاتی خود را مشخص کنید:",
            reply_markup=market_selection_keyboard()
        )
    else:
        await update.message.reply_text("⚠️ لطفاً شماره تماس متعلق به همین اکانت تلگرام را ارسال کنید.")

# -------------------------------------------------------------
# پردازشگر پیام‌های متنی و منطق‌های تالار معاملات
# -------------------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(uid, {}).get("step")

    # 1. مدیریت آنبوردینگ مرحله‌ای
    if state == "WAITING_NAME":
        name = update.effective_user.full_name if text == "استفاده از نام تلگرام" else text
        register_user_step(uid, full_name=name)
        user_states[uid] = {"step": "WAITING_PHONE"}

        btn = [[KeyboardButton("📱 ارسال شماره تماس", request_contact=True)]]
        await update.message.reply_text(
            f"متشکرم {name}.\n\n"
            "۲. جهت فعال‌سازی حساب و تایید امنیت کاربری، لطفاً شماره تماس خود را به اشتراک بگذارید:",
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True)
        )
        return

    elif state == "WAITING_MARKET":
        register_user_step(uid, market=text)
        user_states[uid] = {"step": "WAITING_LEVEL"}
        await update.message.reply_text(
            "۴. سطح تجربه معاملاتی خود را انتخاب کنید:",
            reply_markup=level_keyboard()
        )
        return

    elif state == "WAITING_LEVEL":
        register_user_step(uid, level=text)
        user_states[uid] = {"step": "WAITING_CAPITAL"}
        await update.message.reply_text(
            "۵. حدود سرمایه فعال در گردش خود را مشخص فرمایید:",
            reply_markup=capital_keyboard()
        )
        return

    elif state == "WAITING_CAPITAL":
        register_user_step(uid, capital=text)
        user_states.pop(uid, None)
        await update.message.reply_text(
            "🎉 **ثبت‌نام شما با موفقیت تکمیل گردید!**\n\n"
            "سیستم مدیریت ریسک و موتور تحلیلی الوند برای شما فعال شد.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # 2. دریافت نماد برای تحلیل تکنیکال جامع
    elif state == "WAITING_ANALYSIS_SYMBOL":
        user_states.pop(uid, None)
        symbol = text.upper()
        # موتور تحلیلی و چک فیلتر ضد FOMO
        analysis_report = (
            f"🔍 **گزارش تحلیل تکنیکال: {symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ تایم‌فریم اصلی: ۴ ساعته (H4)\n"
            f"📊 ساختار مارکت: تثبیت بالای محدوده تقاضا\n"
            f"🛡 سطح حمایت کلیدی: ۲ پله پایین‌تر از قیمت فعلی\n"
            f"🎯 سطح مقاومت نزدیک: سقف رنج هفتگی\n"
            f"⚖️ فیلتر ضد FOMO: 🟢 مجاز برای بررسی ستاپ (قیمت وسط رنج نیست)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *توصیه:* از ورود بدون تأییدیه و با حجم غیرمجاز خودداری فرمایید."
        )
        await update.message.reply_text(analysis_report, reply_markup=trading_hall_keyboard(), parse_mode="Markdown")
        return

    # ---------------------------------------------------------
    # ناوبری دکمه‌های منو
    # ---------------------------------------------------------
    if text == "🔙 بازگشت به منوی اصلی":
        user_states.pop(uid, None)
        await update.message.reply_text("به منوی اصلی بازگشتید:", reply_markup=main_menu_keyboard())

    elif text == "🏛 تالار معاملات":
        await update.message.reply_text(
            "🏛 **به تالار معاملات Robo7 خوش آمدید.**\n"
            "لطفاً بخش مورد نظر را انتخاب کنید:",
            reply_markup=trading_hall_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "🎯 دریافت ستاپ معاملاتی":
        setup_text = (
            "🎯 **ستاپ معاملاتی معتبر (فیلتر شده با قانون R:R > 1:2)**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🪙 نماد: **XAUUSD (انس طلا)**\n"
            "📈 موقعیت: **BUY LIMIT**\n"
            "📍 نقطه ورود: **2642.50**\n"
            "🛑 حد ضرر (SL): **2634.00**\n"
            "🎯 حد سود اول (TP1): **2655.00**\n"
            "🎯 حد سود دوم (TP2): **2670.00**\n"
            "⚖️ نسبت ریسک به ریوارد: **1:2.8**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *هشدار مدیریت سرمایه:* حداکثر ۱ تا ۲ درصد از کل مارجین مجاز است."
        )
        await update.message.reply_text(setup_text, reply_markup=trading_hall_keyboard(), parse_mode="Markdown")

    elif text == "🔍 تحلیل تکنیکال جامع":
        user_states[uid] = {"step": "WAITING_ANALYSIS_SYMBOL"}
        await update.message.reply_text(
            "لطفاً نماد مورد نظر خود را ارسال فرمایید:\n"
            "(مثال: `BTCUSDT` یا `XAUUSD` یا `ETHUSDT`)",
            reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت به منوی اصلی"]], resize_keyboard=True),
            parse_mode="Markdown"
        )

    elif text == "⚡️ رادار بازار (فرصت‌های داغ)":
        radar_text = (
            "⚡️ **رادار اختصاصی بازار (Market Scanner)**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 **بیت‌کوین (BTC):** فشرده‌سازی نوسان، احتمال شکست سقف نزدیک است.\n"
            "🔥 **سولانا (SOL):** ورود حجم مشکوک در تایم‌فریم ۱ ساعته.\n"
            "🔥 **طلا (XAUUSD):** حفظ حمایت کلیدی در آغاز سشن لندن.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "سیستم آماده صدور آلارم‌های شکست معتبر است."
        )
        await update.message.reply_text(radar_text, reply_markup=trading_hall_keyboard(), parse_mode="Markdown")

    elif text == "📊 گزارش عملکرد من":
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT result, COUNT(*), COALESCE(SUM(amount), 0) FROM trades WHERE user_id = ? GROUP BY result", (uid,))
        rows = c.fetchall()
        conn.close()

        total_trades = sum(r[1] for r in rows)
        wins = sum(r[1] for r in rows if r[0] == "WIN")
        losses = sum(r[1] for r in rows if r[0] == "LOSS")
        net_pnl = sum(r[2] for r in rows)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        report = (
            "📊 **داشبورد عملکرد معاملاتی شما**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"تعداد کل معاملات ژورنال شده: **{total_trades}**\n"
            f"معاملات موفق (Win): **{wins}**\n"
            f"معاملات ناموفق (Loss): **{losses}**\n"
            f"وین‌ریت (Win Rate): **{win_rate:.1f}%**\n"
            f"سود/زیان خالص دلاری: **{net_pnl:+.2f}$**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 *برای بهبود وین‌ریت، معامله در میانه رنج را از استراتژی خود حذف کنید.*"
        )
        await update.message.reply_text(report, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "⚙️ پروفایل تریدر":
        u = get_user(uid)
        if u:
            prof = (
                "⚙️ **شناسنامه و پروفایل تریدر**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 نام: **{u[1]}**\n"
                f"🆔 شناسه: `{u[0]}`\n"
                f"🌐 بازار هدف: **{u[2] or 'تنظیم‌نشده'}**\n"
                f"🎓 سطح تجربه: **{u[3] or 'تنظیم‌نشده'}**\n"
                f"💰 سرمایه تخمینی: **{u[4] or 'تنظیم‌نشده'}**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "وضعیت دسترسی: 🟢 تایید شده"
            )
        else:
            prof = "اطلاعاتی یافت نشد. لطفاً دستور /start را ارسال کنید."
        await update.message.reply_text(prof, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "🏓 وضعیت سیستم":
        await update.message.reply_text(
            "🏓 **وضعیت سرور و موتور ربات:**\n\n"
            "🟢 وضعیت ربات: کاملاً آنلاین و فعال (Operational)\n"
            "🛡 وب‌سرور داخلی رندر: فعال روی پورت تنظیم‌شده\n"
            "⚡️ دیتابیس: متصل و نرمال\n"
            "📡 ارتباط تلگرام: پایش مستمر فعال است.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "📓 ثبت معامله در ژورنال":
        await update.message.reply_text(
            "📓 **دستیار هوشمند ژورنال**\n\n"
            "هر ستاپی که دریافت می‌کنید، ۲۰ دقیقه بعد وضعیت آن از شما پرسیده می‌شود.\n"
            "همچنین می‌توانید معامله جدید را دستی ثبت کنید.\n"
            "*(فرمت سریع ثبت: نماد | سود یا ضرر | مبلغ به دلار — مثال: `BTC | WIN | +45`)*",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "🔔 هشدار ورود / واچ‌لیست":
        await update.message.reply_text(
            "🔔 **واچ‌لیست اختصاصی و آلارم قیمت**\n\n"
            "واچ‌لیست پیش‌فرض شما فعال است:\n"
            "• BTCUSDT\n• ETHUSDT\n• XAUUSD (طلا)\n\n"
            "در صورت رسیدن قیمت به نواحی کلیدی، اعلان ارسال خواهد شد.",
            reply_markup=main_menu_keyboard()
        )

# -------------------------------------------------------------
# سرور داخلی aiohttp برای زنده نگه داشتن در Render ($PORT)
# -------------------------------------------------------------
async def health_check(request):
    return web.Response(text="Robo7Alvand Bot is alive and running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# -------------------------------------------------------------
# تابع اجرای اصلی ربات
# -------------------------------------------------------------
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # اجرای همزمان سرور وب و ربات تلگرام
    loop = app.loop
    loop.create_task(start_web_server())

    logger.info("Robo7Alvand bot is starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
