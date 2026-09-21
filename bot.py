import os
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from risk import RiskEngine, TradeSetup, ALLOWED_SYMBOLS

# لاگینگ دقیق برای پنل رندر
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Robo7Alvand")

# خواندن توکن ربات تلگرام
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# ژورنال معاملات در حافظه
TRADE_JOURNAL: list[dict] = []

# --- وب‌سرور داخلی aiohttp جهت پاسخ به Health Check رندر و آپ‌تایم‌ربات ---
async def health_check(request):
    return web.Response(text="Robo7Alvand Core Engine is Active & Running.", status=200)

async def start_aiohttp_server():
    port = int(os.getenv("PORT", 8080))
    server_app = web.Application()
    server_app.router.add_get("/", health_check)
    server_app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(server_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"aiohttp health server running on port {port}")

# --- منوی شیشه‌ای اصلی ---
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 ثبت ستاپ معامله", callback_data="btn_trade_guide"),
            InlineKeyboardButton("📓 دفترچه معاملات", callback_data="btn_journal")
        ],
        [
            InlineKeyboardButton("🏓 پینگ وضعیت سرور", callback_data="btn_ping"),
            InlineKeyboardButton("🛡 مرامنامه ریسک", callback_data="btn_rules")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- دستورات تلگرام ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 **دستیار تحلیلی معاملاتی Robo7Alvand**\n\n"
        "⚡ فاز ۱: بازارهای کریپتو و فارکس\n"
        "🛡 مجهز به هسته ضد FOMO، محاسبه‌گر R:R و مدیریت ریسک سخت‌گیرانه.\n\n"
        "گزینه مورد نظر خود را انتخاب کنید:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🏓 **PONG!** هسته تحلیلی ربات و وب‌سرور داخلی کاملاً آنلاین و پایدار هستند."
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown")

async def journal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if not TRADE_JOURNAL:
        await target.reply_text("📓 دفترچه معاملات خالی است. هنوز ستاپ تایید‌شده‌ای ثبت نشده است.")
        return

    text = "📓 **آخرین معاملات تایید شده در سیستم:**\n\n"
    for i, t in enumerate(TRADE_JOURNAL[-5:], 1):
        text += (
            f"*{i}. {t['symbol']}* ({t['side']})\n"
            f"ورود: `{t['entry']}` | حد ضرر: `{t['sl']}` | تارگت: `{t['tp']}`\n"
            f"نسبت ریسک/ریوارد: `1:{t['rr']}`\n"
            "───────────────\n"
        )
    await target.reply_text(text, parse_mode="Markdown")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    rules = (
        "🛡 **مرامنامه معاملاتی و هسته ضد FOMO:**\n\n"
        "۱. **حداقل R:R معتبر:** ۱:۲.۰ (هر ستاپی با نسبت کمتر فوراً ریجکت می‌شود).\n"
        "۲. **ورود ممنوع در میانه رنج:** هیچ معامله‌ای بدون شکست معتبر یا برخورد به سطوح کلیدی پذیرفته نیست.\n"
        "۳. **مارتینگل اکیداً ممنوع:** افزایش حجم در ضرر خط قرمز مطلق است.\n"
        "۴. **نمادهای مجاز فاز ۱:**\n"
        f"`{', '.join(sorted(ALLOWED_SYMBOLS))}`\n"
        "۵. **اصل بنیادین:** حفظ سرمایه همیشه بر کسب سود تقدم دارد."
    )
    await target.reply_text(rules, parse_mode="Markdown")

async def trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.message.reply_text(
            "⚠️ **فرمت ارسال ستاپ اشتباه است.**\n\n"
            "الگوی صحیح:\n"
            "`/trade [نماد] [BUY/SELL] [ورود] [حدضرر] [تارگت]`\n\n"
            "مثال معتبر:\n"
            "`/trade BTCUSDT BUY 64000 63500 65500`",
            parse_mode="Markdown"
        )
        return

    try:
        symbol = context.args[0]
        side = context.args[1]
        entry = float(context.args[2])
        sl = float(context.args[3])
        tp = float(context.args[4])

        # ارسال به موتور ریسک
        result: TradeSetup = RiskEngine.validate_and_calculate(symbol, side, entry, sl, tp)

        if not result.is_valid:
            msg = (
                f"🚫 **ستاپ معامله {result.symbol} رد شد! (ضد FOMO)**\n\n"
                f"علت رد ستاپ:\n{result.rejection_reason}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        # در صورت تایید هسته
        TRADE_JOURNAL.append({
            "symbol": result.symbol,
            "side": result.side,
            "entry": result.entry,
            "sl": result.stop_loss,
            "tp": result.take_profit,
            "rr": result.risk_reward_ratio
        })

        success_msg = (
            f"✅ **ستاپ معاملاتی تایید و ثبت شد.**\n\n"
            f"نماد: *{result.symbol}* ({result.side})\n"
            f"قیمت ورود: `{result.entry}`\n"
            f"حد ضرر: `{result.stop_loss}` (ریسک: {result.risk_amount})\n"
            f"تارگت: `{result.take_profit}` (ریوارد: {result.reward_amount})\n"
            f"📊 **نسبت ریسک به ریوارد:** `1:{result.risk_reward_ratio}`\n\n"
            "🎯 مدیریت پوزیشن و پایبندی به حد ضرر الزامی است."
        )
        await update.message.reply_text(success_msg, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("⚠️ مقادیر عددی قیمت، حد ضرر و تارگت را به صورت عدد صحیح یا اعشاری وارد کنید.")

# --- مدیریت دکمه‌های شیشه‌ای ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_ping":
        await ping_cmd(update, context)
    elif query.data == "btn_journal":
        await journal_cmd(update, context)
    elif query.data == "btn_rules":
        await rules_cmd(update, context)
    elif query.data == "btn_trade_guide":
        guide = (
            "📊 **راهنمای بررسی و ثبت ستاپ معامله:**\n\n"
            "دستور را با الگوی زیر ارسال کنید:\n"
            "`/trade [نماد] [BUY/SELL] [ورود] [حد ضرر] [تارگت]`\n\n"
            "نمونه‌ها:\n"
            "▫️ `/trade BTCUSDT BUY 64000 63500 65500`\n"
            "▫️ `/trade XAUUSD SELL 2650 2660 2625`"
        )
        await query.message.reply_text(guide, parse_mode="Markdown")

# --- مدیریت خطای سراسری (Global Error Handler) ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("بروز استثنا در زمان پردازش آپدیت:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ خطایی در اجرای درخواست رخ داد. سیستم فعال و لاگ در کنسول ثبت شد."
        )

# --- تابع اصلی اجرای همزمان بات و وب‌سرور ---
async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN یا TELEGRAM_BOT_TOKEN تعریف نشده است!")

    # راه‌اندازی سرور aiohttp در پس‌زمینه
    await start_aiohttp_server()

    # راه‌اندازی ربات تلگرام
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("journal", journal_cmd))
    application.add_handler(CommandHandler("rules", rules_cmd))
    application.add_handler(CommandHandler("trade", trade_cmd))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_error_handler(error_handler)

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Robo7Alvand Engine Polling Started Successfully.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
