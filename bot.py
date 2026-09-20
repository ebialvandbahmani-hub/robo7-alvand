import os
import logging
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# خواندن متغیرهای محیطی
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# سرور داخلی برای زنده نگه داشتن ربات در Render
async def health_check(request):
    return web.Response(text="Robo7Alvand is Active & Running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_head('/', health_check)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server successfully started on port {port}")

# دستور استارت
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name if user and user.first_name else "همراه گرامی"
    
    # دکمه‌های عمومی
    keyboard = [
        ["📊 تحلیل بازار کریپتو", "📈 تحلیل فارکس و طلا"],
        ["🛡 قوانین مدیریت ریسک", "⚙️ وضعیت حساب و ربات"]
    ]
    
    # اضافه کردن منوی ویژه برای ابی (مالک ربات)
    if user and user.id == ADMIN_ID:
        keyboard.append(["🛠 پنل مدیریت (تست سیگنال)"])
    
    welcome_text = (
        f"سلام {user_name} عزیز! 🌹\n\n"
        f"به **دستیار هوشمند معاملاتی Robo7Alvand** خوش آمدید. 🤖📈\n\n"
        f"🎯 **هدف ما:** ارائه تحلیل‌های منطقی، ستاپ‌های معاملاتی استاندارد و مدیریت ریسک سخت‌گیرانه (Anti-FOMO) در بازارهای کریپتو و فارکس.\n\n"
        f"💎 **پوشش بازارها:**\n"
        f"• فارکس و انس جهانی: `XAUUSD` | `EURUSD`\n"
        f"• کریپتوکارنسی: `BTC` | `ETH` | `SOL`\n\n"
        f"از منوی زیر می‌توانید بخش مورد نظر خود را انتخاب نمایید 👇"
    )
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# پردازش دکمه‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    
    if text == "📊 تحلیل بازار کریپتو":
        response = (
            "🪙 **وضعیت مارکت کریپتو:**\n\n"
            "🔹 **BTC/USDT:** فاز تثبیت و بررسی حجم در حمایت‌های کلیدی\n"
            "🔹 **ETH/USDT:** منتظر تایید شکست ساختار\n"
            "🔹 **SOL/USDT:** حفظ کانال صعودی میان‌مدت\n\n"
            "⚠️ *ورود پله‌ای و پایبندی به R:R حداقل ۱:۲ الزامی است.*"
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        
    elif text == "📈 تحلیل فارکس و طلا":
        response = (
            "🥇 **وضعیت انس طلا و جفت‌ارزها:**\n\n"
            "🔸 **XAUUSD (انس جهانی طلا):** رصد سشن‌های لندن و نیویورک برای شکار نقدینگی\n"
            "🔸 **EURUSD:** در محدوده رنج\n\n"
            "🛡 *بدون تاییدیه و استاپ‌لاس وارد هیچ پوزیشنی نشوید.*"
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        
    elif text == "🛡 قوانین مدیریت ریسک":
        rules = (
            "📋 **اصول طلایی مدیریت ریسک Robo7Alvand:**\n\n"
            "۱. 🚫 **عدم FOMO:** هرگز در کندل‌های هیجانی وارد نشوید.\n"
            "۲. ⚖️ **حداقل نسبت ریسک به ریوارد (R:R):** ۱ به ۲.\n"
            "۳. 🛑 **بدون مارتینگل:** افزودن حجم در ضرر ممنوع است.\n"
            "۴. 🛡 **حفظ اصل سرمایه:** همیشه اولویت اول معامله‌گر است."
        )
        await update.message.reply_text(rules, parse_mode="Markdown")
        
    elif text == "⚙️ وضعیت حساب و ربات":
        await update.message.reply_text(
            "🟢 وضعیت سرور: **آنلاین و پایدار**\n"
            "🔄 ارتباط دیتا: **فعال**\n"
            "نسخه ربات: **Robo7Alvand v1.0**",
            parse_mode="Markdown"
        )
        
    elif text == "🛠 پنل مدیریت (تست سیگنال)" and user and user.id == ADMIN_ID:
        admin_panel_text = (
            "👑 **پنل مدیریت اختصاصی ادمین (ابی):**\n\n"
            "✅ احراز هویت موفقیت‌آمیز بود.\n"
            "⚙️ وضعیت موتور تحلیل: **آماده دریافت دستورات فاز ۲**\n\n"
            "در این بخش می‌توانید ستاپ‌های آزمایشی را تست کرده و خروجی موتور ریسک را بررسی نمایید."
        )
        await update.message.reply_text(admin_panel_text, parse_mode="Markdown")
        
    else:
        await update.message.reply_text(
            f"پیام دریافت شد: `{text}`\nلطفاً از گزینه‌های منو استفاده کنید.",
            parse_mode="Markdown"
        )

# مدیریت خطاها
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable not set!")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())

    logger.info("Robo7Alvand is starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
