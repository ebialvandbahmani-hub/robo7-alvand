import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# 1. Configuration
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
DB_NAME = "robo7alvand.db"

# 2. Database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT, market TEXT, capital TEXT, experience TEXT)")
    conn.commit()
    conn.close()

# 3. Keyboards
MAIN_MENU = ReplyKeyboardMarkup([["🏛 تالار معاملات", "📊 گزارش عملکرد"], ["👤 پروفایل کاربری", "📚 آکادمی و آموزش"], ["ℹ️ راهنما و قوانین"]], resize_keyboard=True)
TRADING_MENU = ReplyKeyboardMarkup([["🎯 دریافت ستاپ معاملاتی", "📊 تحلیل تکنیکال"], ["🔙 بازگشت به منوی اصلی"]], resize_keyboard=True)

# 4. Web Server
async def health_check(request):
    return web.Response(text="Robo7Alvand is online!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# 5. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("خوش آمدید.", reply_markup=MAIN_MENU)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🏛 تالار معاملات":
        await update.message.reply_text("منوی تالار معاملات:", reply_markup=TRADING_MENU)
    elif text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی:", reply_markup=MAIN_MENU)
    elif text == "🎯 دریافت ستاپ معاملاتی":
        setup = (
            "🎯 <b>ستاپ معاملاتی روبو۷ الوند</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💹 <b>نماد معاملاتی:</b> XAUUSD (انس جهانی طلا)\n"
            "🧭 <b>نوع معامله و سفارش:</b> BUY LIMIT (اوردر لیمیت)\n"
            "⏰ <b>تایم‌فریم تاییدیه:</b> 15M / ساختار: 1H\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 <b>محدوده ورود (Entry Zone):</b> 2641.50 <---> 2643.50\n"
            "🎯 <b>نقطه ورود طلایی و قوی (Sweet Spot):</b> 👉 <code>2642.10</code> 👈\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛑 <b>حد ضرر قطعی (Stop Loss):</b>\n"
            "سطح قیمت: <code>2638.10</code> (۴۰ پیپ / ۴ دلار فاصله)\n"
            "💵 <b>حداکثر ریسک فرضی ضرر:</b> $40 (به ازای هر 0.1 لات)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>اهداف سود، وضعیت ریسک و بازده دلاری:</b>\n"
            "TP1: <code>2646.10</code> | ریسک‌فری و سیو ۵۰٪ | بازده: (1R+) $40+\n"
            "TP2: <code>2650.10</code> | خروج ۲۵٪ حجم | بازده: (2R+) $80+\n"
            "TP3: <code>2654.10</code> | حفظ تریلینگ استاپ | بازده: (3R+) $120+\n"
            "TP4: <code>2660.10</code> | تارگت نقدینگی | بازده: (4.5R+) $180+\n"
            "🏁 <b>تارگت نهایی:</b> <code>2668.00</code> | خروج کامل | بازده: (6.5R+) $259+\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚖️ <b>نسبت برآیند ریسک به ریوارد:</b> 1:6.5\n"
            "💼 <b>مدیریت حجم پیشنهادی:</b> حداکثر ۱٪ کل حساب\n"
            "⚠️ <b>هشدار اسپرد و لغزش بروکر (Warning):</b>\n"
            "اسپرد نرمال حدود ۲ تا ۳ پیپ است. لطفاً فاصله حد ضرر را با احتساب اسپرد بروکرتان ست کنید.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏱ <b>اعتبار زمانی:</b> تا کلوز سشن لندن"
        )
        await update.message.reply_text(setup, parse_mode="HTML")
    elif text == "📊 تحلیل تکنیکال":
        await update.message.reply_text("📊 تحلیل زنده: XAUUSD در وضعیت اشباع خرید است.", parse_mode="HTML")
    else:
        await update.message.reply_text("لطفاً از دکمه‌های زیر استفاده کنید.", reply_markup=MAIN_MENU)

async def main():
    init_db()
    await start_web_server()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
