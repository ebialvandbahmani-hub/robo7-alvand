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
# ۱. پیکربندی
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
DB_NAME = "robo7alvand.db"

# ---------------------------------------------------------
# ۲. دیتابیس
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT, market TEXT, capital TEXT, experience TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user(user_id, data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, full_name, phone, market, capital, experience) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, data.get("name"), data.get("phone"), data.get("market"), data.get("capital"), data.get("experience")))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# ۳. کیبوردها
# ---------------------------------------------------------
MAIN_MENU = ReplyKeyboardMarkup([["🏛 تالار معاملات", "📊 گزارش عملکرد"], ["👤 پروفایل کاربری", "📚 آکادمی و آموزش"], ["ℹ️ راهنما و قوانین"]], resize_keyboard=True)
TRADING_MENU = ReplyKeyboardMarkup([["🎯 دریافت ستاپ معاملاتی", "📊 تحلیل تکنیکال"], ["🔙 بازگشت به منوی اصلی"]], resize_keyboard=True)

# ---------------------------------------------------------
# ۴. سرور (اصلاح شده)
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
async def start(update, context):
    await update.message.reply_text("خوش آمدید.", reply_markup=MAIN_MENU)

async def handle_text(update, context):
    text = update.message.text
    
    if text == "🏛 تالار معاملات":
        await update.message.reply_text("منوی تالار معاملات:", reply_markup=TRADING_MENU)
    elif text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی:", reply_markup=MAIN_MENU)
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
    elif text == "📊 تحلیل تکنیکال":
        analysis = (
            "📊 <b>تحلیل تکنیکال زنده - XAUUSD</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📉 <b>روند کلی:</b> صعودی در تایم‌فریم 4H\n"
            "🔥 <b>اندیکاتورها:</b> RSI در محدوده اشباع خرید\n"
            "💡 <b>سناریوی احتمالی:</b> اصلاح موقت به سمت محدوده تقاضا و ادامه روند"
        )
        await update.message.reply_text(analysis, parse_mode="HTML")
    else:
        await update.message.reply_text("از منو انتخاب کنید.", reply_markup=MAIN_MENU)

async def main():
    if not TOKEN: return
    init_db()
    await start_web_server()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
