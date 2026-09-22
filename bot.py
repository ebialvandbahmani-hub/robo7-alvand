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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
PORT = int(os.getenv("PORT", 8080))
DB_NAME = "robo7alvand.db"

# ---------------------------------------------------------
# ۲. مدیریت دیتابیس
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
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
# ۳. کیبوردها
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
        ["🎯 دریافت ستاپ معاملاتی", "📊 تحلیل تکنیکال"],
        ["🔙 بازگشت به منوی اصلی"]
    ],
    resize_keyboard=True
)

QUESTIONS = [
    {"key": "market", "text": "حوزه اصلی فعالیت شما؟", "keyboard": [["فارکس (Forex)", "کریپتو (Crypto)"], ["هر دو بازار"]]},
    {"key": "capital", "text": "میزان سرمایه فعال؟", "keyboard": [["زیر ۵۰۰ دلار", "۵۰۰ تا ۲۰۰۰ دلار"], ["۲۰۰۰ تا ۵۰۰۰ دلار", "بیش از ۵۰۰۰ دلار"]]},
    {"key": "experience", "text": "سطح سابقه تریدینگ؟", "keyboard": [["مبتدی", "متوسط"], ["حرفه‌ای"]]}
]

# ---------------------------------------------------------
# ۴. وب‌سرور برای Render (Health Check)
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="Robo7Alvand is online!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# ---------------------------------------------------------
# ۵. هندلرها
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if get_user(uid):
        await update.message.reply_text("خوش آمدید.", reply_markup=MAIN_MENU_KEYBOARD)
    else:
        context.user_data["onb"] = {"step": "name", "data": {}}
        await update.message.reply_text("لطفاً نام و نام خانوادگی خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    onb = context.user_data.get("onb")
    if onb and onb.get("step") == "phone":
        onb["data"]["phone"] = contact.phone_number
        onb["step"] = 0
        q = QUESTIONS[0]
        kb = ReplyKeyboardMarkup(q["keyboard"], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(q["text"], reply_markup=kb)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    onb = context.user_data.get("onb")

    if onb:
        if onb.get("step") == "name":
            onb["data"]["name"] = text
            onb["step"] = "phone"
            phone_btn = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
            await update.message.reply_text(
                "شماره تماس خود را بفرستید:",
                reply_markup=ReplyKeyboardMarkup([[phone_btn]], resize_keyboard=True)
            )
            return
        elif isinstance(onb.get("step"), int):
            q_idx = onb["step"]
            onb["data"][QUESTIONS[q_idx]["key"]] = text
            next_idx = q_idx + 1
            if next_idx < len(QUESTIONS):
                onb["step"] = next_idx
                kb = ReplyKeyboardMarkup(QUESTIONS[next_idx]["keyboard"], resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text(QUESTIONS[next_idx]["text"], reply_markup=kb)
            else:
                save_user(uid, onb["data"])
                context.user_data.pop("onb")
                await update.message.reply_text("✅ ثبت‌نام کامل شد.", reply_markup=MAIN_MENU_KEYBOARD)
            return

    # --- ناوبری اصلی ---
    if text == "🏛 تالار معاملات":
        await update.message.reply_text("منوی تالار معاملات:", reply_markup=TRADING_MENU_KEYBOARD)
    
    elif text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی:", reply_markup=MAIN_MENU_KEYBOARD)
        
    # --- ستاپ معاملاتی مهندسی‌شده ---
    elif text == "🎯 دریافت ستاپ معاملاتی":
        setup = (
            "🎯 <b>ستاپ معاملاتی روبو۷ الوند</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💹 <b>نماد:</b> XAUUSD\n"
            "🔄 <b>نوع سفارش:</b> Limit Order\n"
            "🧭 <b>جهت:</b> Long (Buy)\n"
            "⏰ <b>تایم‌فریم تاییدیه:</b> 1H / 4H\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 <b>محدوده ورود:</b> 2640 - 2644\n"
            "✨ <b>نقطه ورود طلایی (Sweet Spot):</b> <code>2642.10</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 <b>مدیریت ریسک:</b>\n"
            "🛑 <b>حد ضرر (SL):</b> <code>2638.10</code>\n"
            "📉 <b>ریسک به ریوارد (R:R):</b> 1:6.5\n"
            "⚠️ <b>هشدار:</b> اسپرد و لغزش بروکر لحاظ شود.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>اهداف سود (TPs):</b>\n"
            "TP1: <code>2648.00</code> | بازده: +1.5$\n"
            "TP2: <code>2654.00</code> | بازده: +3.2$\n"
            "TP3: <code>2662.00</code> | بازده: +5.8$\n"
            "TP4: <code>2668.00</code> | بازده: +8.5$\n"
            "🏆 <b>تارگت نهایی:</b> <code>2680.00</code>"
        )
        await update.message.reply_text(setup, parse_mode="HTML")
        
    # --- تحلیل تکنیکال ---
    elif text == "📊 تحلیل تکنیکال":
        analysis = (
            "📊 <b>تحلیل تکنیکال زنده - XAUUSD</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📉 <b>روند کلی:</b> صعودی در تایم‌فریم 4H\n"
            "🔥 <b>اندیکاتورها:</b> RSI در محدوده اشباع خرید (خروج تدریجی)\n"
            "💡 <b>سناریوی احتمالی:</b> اصلاح موقت به سمت محدوده تقاضا و ادامه روند\n"
            "📝 <b>یادداشت تریدر:</b> منتظر کندل تایید در نقطه ورود طلایی بمانید."
        )
        await update.message.reply_text(analysis, parse_mode="HTML")

    # سایر منوهای اصلی
    elif text == "📊 گزارش عملکرد":
        await update.message.reply_text("گزارش عملکرد: نرخ موفقیت ۷۵٪.")
    elif text == "👤 پروفایل کاربری":
        user = get_user(uid)
        await update.message.reply_text(f"اطلاعات شما: {user[1] if user else 'ناشناس'}")
    elif text == "📚 آکادمی و آموزش":
        await update.message.reply_text("بخش آکادمی...")
    elif text == "ℹ️ راهنما و قوانین":
        await update.message.reply_text("راهنما و سلب مسئولیت...")
    else:
        await update.message.reply_text("از منو انتخاب کنید.", reply_markup=MAIN_MENU_KEYBOARD)

async def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return

    init_db()
    await start_web_server()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # زنده نگه داشتن سرور به صورت دائم
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    asyncio.run(main())
