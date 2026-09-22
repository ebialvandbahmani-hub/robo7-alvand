import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# ۱. پیکربندی لاگینگ و متغیرهای محیطی
# ---------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دریافت توکن و پورت از محیط سرور Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
PORT = int(os.getenv("PORT", 8080))
DB_NAME = "robo7alvand.db"

# ---------------------------------------------------------
# ۲. مدیریت دیتابیس (SQLite)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # جدول کاربران
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            market TEXT,
            capital TEXT,
            experience TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # جدول ژورنال معاملات
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            trade_type TEXT,
            entry REAL,
            tp REAL,
            sl REAL,
            result TEXT,
            profit_loss REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user(user_id: int, data: dict):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (user_id, full_name, phone, market, capital, experience)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("name"),
        data.get("phone"),
        data.get("market"),
        data.get("capital"),
        data.get("experience")
    ))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# ۳. کیبوردهای دسترسی سریع (UI Keyboards)
# ---------------------------------------------------------
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🏛 تالار معاملات", "📊 گزارش عملکرد"],
        ["👤 پروفایل کاربری", "📚 آکادمی و آموزش"],
        ["ℹ️ راهنما و قوانین"]
    ],
    resize_keyboard=True
)

TRADING_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎯 دریافت ستاپ معاملاتی", "📈 تقویم اقتصادی"],
        ["🪙 فیوچرز و اسپات کریپتو", "🥇 فارکس و انس طلا"],
        ["🔙 بازگشت به منوی اصلی"]
    ],
    resize_keyboard=True
)

QUESTIONS = [
    {
        "key": "market",
        "text": "حوزه اصلی فعالیت شما در بازارهای مالی چیست؟",
        "keyboard": [["فارکس (Forex)", "کریپتو (Crypto)"], ["هر دو بازار"]]
    },
    {
        "key": "capital",
        "text": "میزان تقریبی سرمایه فعال شما برای معاملات چقدر است؟",
        "keyboard": [["زیر ۵۰۰ دلار", "۵۰۰ تا ۲۰۰۰ دلار"], ["۲۰۰۰ تا ۵۰۰۰ دلار", "بیش از ۵۰۰۰ دلار"]]
    },
    {
        "key": "experience",
        "text": "سطح آشنایی و سابقه شما در تریدینگ به چه صورت است؟",
        "keyboard": [["مبتدی (آشنایی کم)", "متوسط (۱ تا ۲ سال)"], ["حرفه‌ای (بیش از ۲ سال)"]]
    }
]

# ---------------------------------------------------------
# ۴. وب‌سرور داخلی جهت زنده نگه‌داشتن روی رندر (Health Check)
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="Robo7Alvand is online & healthy!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check web server running on port {PORT}")

# ---------------------------------------------------------
# ۵. هندلرهای تلگرام (Telegram Handlers)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)

    if user:
        await update.message.reply_text(
            f"سلام {update.effective_user.first_name} عزیز! خوش آمدی.\nبه منوی ربات روبو۷ الوند دسترسی داری:",
            reply_markup=MAIN_MENU_KEYBOARD
        )
    else:
        context.user_data["onb"] = {"step": "name", "data": {}}
        await update.message.reply_text(
            "به دستیار معاملاتی <b>روبو۷ الوند</b> خوش آمدید.\n\n"
            "لطفاً جهت ثبت‌نام و فعال‌سازی حساب، <b>نام و نام خانوادگی</b> خود را وارد کنید:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    onb = context.user_data.get("onb")
    if onb and onb.get("step") == "phone":
        onb["data"]["phone"] = contact.phone_number
        onb["step"] = 0  # ورود به اولین سوال
        q = QUESTIONS[0]
        kb = ReplyKeyboardMarkup(q["keyboard"], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(q["text"], reply_markup=kb)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    onb = context.user_data.get("onb")

    # --- فرآیند آنبوردینگ (ثبت‌نام) ---
    if onb:
        step = onb.get("step")
        if step == "name":
            onb["data"]["name"] = text
            onb["step"] = "phone"
            phone_btn = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
            kb = ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(
                "سپاس. برای تکمیل اطلاعات، دکمه زیر را لمس کرده و شماره همراه خود را به اشتراک بگذارید:",
                reply_markup=kb
            )
            return
        elif isinstance(step, int):
            q_idx = step
            current_q = QUESTIONS[q_idx]
            onb["data"][current_q["key"]] = text
            next_idx = q_idx + 1

            if next_idx < len(QUESTIONS):
                onb["step"] = next_idx
                next_q = QUESTIONS[next_idx]
                kb = ReplyKeyboardMarkup(next_q["keyboard"], resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text(next_q["text"], reply_markup=kb)
                return
            else:
                # پایان ثبت‌نام
                save_user(uid, onb["data"])
                context.user_data.pop("onb", None)
                await update.message.reply_text(
                    "✅ ثبت‌نام شما با موفقیت تکمیل شد.\nبه خانواده روبو۷ الوند خوش آمدید!",
                    reply_markup=MAIN_MENU_KEYBOARD
                )
                # اطلاع‌رسانی به ادمین در صورت ست بودن آیدی
                if ADMIN_ID:
                    try:
                        admin_msg = (
                            f"🔔 <b>ثبت‌نام کاربر جدید:</b>\n"
                            f"👤 نام: {onb['data'].get('name')}\n"
                            f"📞 شماره: {onb['data'].get('phone')}\n"
                            f"🆔 شناسه: {uid}\n"
                            f"📊 بازار: {onb['data'].get('market')}\n"
                            f"💵 سرمایه: {onb['data'].get('capital')}\n"
                            f"🎓 سطح: {onb['data'].get('experience')}"
                        )
                        await context.bot.send_message(chat_id=int(ADMIN_ID), text=admin_msg, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Error alerting admin: {e}")
                return

    # --- ناوبری و منوهای عملیاتی ---
    if text == "🏛 تالار معاملات":
        await update.message.reply_text(
            "به تالار معاملات روبو۷ خوش آمدید.\nگزینه مورد نظر خود را انتخاب کنید:",
            reply_markup=TRADING_MENU_KEYBOARD
        )

    elif text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی:", reply_markup=MAIN_MENU_KEYBOARD)

    elif text == "🎯 دریافت ستاپ معاملاتی":
        setup_text = (
            "🎯 <b>ستاپ معاملاتی روبو۷ الوند</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>نماد معاملاتی:</b> XAUUSD (انس جهانی طلا)\n"
            "🧭 <b>نوع معامله و سفارش:</b> BUY LIMIT (اوردر لیمیت)\n"
            "⏱ <b>تایم‌فریم تاییدیه:</b> 15M / ساختار: 1H\n\n"
            "📍 <b>محدوده ورود (Entry Zone):</b>\n"
            "2641.50  ◄───►  2643.50\n"
            "🎯 <b>نقطه ورود طلایی و قوی (Sweet Spot):</b>\n"
            "👉 <code>2642.10</code> 👈\n\n"
            "🛑 <b>حد ضرر قطعی (Stop Loss):</b>\n"
            "سطح قیمت: <code>2638.10</code> (۴۰ پیپ / ۴ دلار فاصله)\n"
            "💵 <b>حداکثر ریسک فرضی ضرر:</b> <code>40$</code> (به ازای هر 0.1 لات)\n\n"
            "🎯 <b>اهداف سود، وضعیت ریسک و بازده دلاری:</b>\n"
            "▫️ <b>تارگت ۱:</b> <code>2646.10</code> | ریسک‌فری و سیو ۵۰٪ | بازده: <b>+40$</b> (+1R)\n"
            "▫️ <b>تارگت ۲:</b> <code>2650.10</code> | خروج ۲۵٪ حجم | بازده: <b>+80$</b> (+2R)\n"
            "▫️ <b>تارگت ۳:</b> <code>2654.10</code> | حفظ تریلینگ استاپ | بازده: <b>+120$</b> (+3R)\n"
            "▫️ <b>تارگت ۴:</b> <code>2660.10</code> | تارگت نقدینگی | بازده: <b>+180$</b> (+4.5R)\n"
            "▫️ 🏁 <b>تارگت نهایی:</b> <code>2668.00</code> | خروج کامل | بازده: <b>+259$</b> (+6.5R)\n\n"
            "⚖️ <b>نسبت برآیند ریسک به ریوارد:</b> 1:6.5\n"
            "💼 <b>مدیریت حجم پیشنهادی:</b> حداکثر ۱٪ کل حساب\n\n"
            "⚠️ <b>هشدار اسپرد و لغزش بروکر (Spread Warning):</b>\n"
            "اسپرد نرمال نماد حدود ۲ تا ۳ پیپ است. لطفاً فاصله حد ضرر را با احتساب اسپرد بروکرتان ست کنید.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏱ <b>اعتبار زمانی:</b> تا کلوز سشن لندن"
        )
        await update.message.reply_text(setup_text, parse_mode="HTML")

    elif text == "📈 تقویم اقتصادی":
        cal_text = (
            "📅 <b>رویدادهای کلیدی تقویم اقتصادی امروز:</b>\n\n"
            "🔴 <b>CPI (شاخص تورم آمریکا)</b> - ساعت ۱۶:۰۰\n"
            "▫️ پیش‌بینی تاثیر: نوسان شدید روی انس طلا و جفت‌ارزهای دلاری\n\n"
            "🟡 <b>سخنرانی رئیس فدرال رزرو</b> - ساعت ۲۰:۳۰\n"
            "▫️ توصیه: در زمان انتشار اخبار با های‌مپکت معامله جدید باز نکنید."
        )
        await update.message.reply_text(cal_text, parse_mode="HTML")

    elif text in ["🪙 فیوچرز و اسپات کریپتو", "🥇 فارکس و انس طلا"]:
        await update.message.reply_text(
            f"بخش {text} در حال حاضر فعال است و ستاپ‌های جاری از طریق دکمه «دریافت ستاپ معاملاتی» صادر می‌گردند."
        )

    elif text == "📊 گزارش عملکرد":
        await update.message.reply_text(
            "📊 <b>گزارش عملکرد ماه جاری سیستم:</b>\n"
            "▫️ تعداد کل ستاپ‌ها: ۲۴\n"
            "▫️ نرخ موفقیت (Win Rate): ۷۵٪\n"
            "▫️ برآیند سود به ضرر: +14.2R\n"
            "حفظ سرمایه و انضباط معاملاتی رمز ماندگاری است.",
            parse_mode="HTML"
        )

    elif text == "👤 پروفایل کاربری":
        user = get_user(uid)
        if user:
            p_text = (
                f"👤 <b>اطلاعات حساب کاربری شما:</b>\n\n"
                f"▫️ نام: {user[1]}\n"
                f"▫️ شماره تماس: {user[2]}\n"
                f"▫️ بازار اصلی: {user[3]}\n"
                f"▫️ بازه سرمایه: {user[4]}\n"
                f"▫️ سطح تجربه: {user[5]}\n"
                f"▫️ تاریخ پیوستن: {user[6]}"
            )
        else:
            p_text = "اطلاعات کاربری یافت نشد. لطفاً مجدداً دستور /start را ارسال کنید."
        await update.message.reply_text(p_text, parse_mode="HTML")

    elif text == "📚 آکادمی و آموزش":
        await update.message.reply_text(
            "📚 <b>آکادمی تحلیلی روبو۷ الوند:</b>\n\n"
            "۱. مدیریت سرمایه و محاسبه دقیق حجم بر اساس پیپ\n"
            "۲. شناسایی نقاط طلایی نقدینگی و پرایس اکشن تاییدیه\n"
            "۳. اصول ضد FOMO و کنترل احساسات در معامله‌گری\n\n"
            "مطالب تکمیلی به‌زودی در دسترس قرار می‌گیرد.",
            parse_mode="HTML"
        )

    elif text == "ℹ️ راهنما و قوانین":
        disclaimer_text = (
            "⚖️ <b>بیانیه سلب مسئولیت و قوانین فعالیت:</b>\n\n"
            "۱. تمام ستاپ‌ها و تحلیل‌های ارائه‌شده جنبه آموزشی و دیدگاه سیستم هوشمند را دارند.\n"
            "۲. بازارهای مالی دارای ریسک ذاتی هستند و مسئولیت مدیریت سرمایه بر عهده شخص معامله‌گر است.\n"
            "۳. رعایت دقیق حد ضرر و ریسک حداکثر ۱٪ در هر معامله الزامی است."
        )
        await update.message.reply_text(disclaimer_text, parse_mode="HTML")

    else:
        await update.message.reply_text("لطفاً از دکمه‌های منوی ربات استفاده نمایید.", reply_markup=MAIN_MENU_KEYBOARD)

# ---------------------------------------------------------
# ۶. راه‌اندازی هم‌زمان وب‌سرور و پولینگ تلگرام
# ---------------------------------------------------------
async def main():
    if not TOKEN:
        raise ValueError("خطا: توکن ربات تلگرام (TELEGRAM_BOT_TOKEN) تنظیم نشده است!")

    # ساخت پایگاه داده
    init_db()

    # اجرای هلث‌چک در پس‌زمینه برای پورت رندر
    await start_web_server()

    # ساخت اپلیکیشن تلگرام
    app = Application.builder().token(TOKEN).build()

    # رجیستر کردن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Robo7Alvand Application started polling successfully.")
    
    # اجرای بات تا زمان توقف دستی
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # نگه داشتن اجرای async به صورت پیوسته
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
