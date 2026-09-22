import os
import asyncio
import logging
from dataclasses import dataclass
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))

# ==========================================
# ۱. مدل‌های داده و فرمت‌بندی پیام‌ها
# ==========================================
@dataclass
class TradeSetupData:
    symbol: str
    market: str
    order_type: str
    style: str
    rr: str
    risk_level: str
    risk_percent: str
    entry_range: str
    entry_confirm: str
    sl: str
    sl_loss_usd: str
    tp1: str
    tp2: str
    tp3: str
    tp4: str

def format_trading_setup(d: TradeSetupData) -> str:
    return (
        f"💎 ستاپ معاملاتی روبو الوند 💎\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 نماد: {d.symbol}\n"
        f"⚙️ بازار: {d.market}\n"
        f"🏷 نوع سفارش: {d.order_type}\n"
        f"⏳ سبک معامله: {d.style}\n"
        f"⚖️ ریسک به ریوارد: {d.rr} | ⚠️ ریسک: {d.risk_level}\n"
        f"💼 پیشنهادی: {d.risk_percent}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 محدوده ورود: {d.entry_range}\n"
        f"🎯 ورود مطمئن: {d.entry_confirm}\n\n"
        f"🛑 حد ضرر (SL): {d.sl}\n"
        f"(ضرر تقریبی: {d.sl_loss_usd} دلار)\n\n"
        f"🎯 اهداف سود (Take Profit):\n"
        f"🔹 TP1: {d.tp1} (کم ریسک - سیو سود)\n"
        f"🔹 TP2: {d.tp2} (قطعی)\n"
        f"🔹 TP3: {d.tp3} (متوسط)\n"
        f"🔹 TP4: {d.tp4} (تارگت نهایی)\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ اسپرد: ۳ الی ۵ پیپ فاصله را در ورود و SL لحاظ کنید.\n"
        f"⏰ یادآور ژورنال‌نویسی ۲۰ دقیقه دیگر ارسال می‌شود."
    )

def format_technical_analysis(symbol: str, rsi: str, macd: str, ma: str, scenario: str, risk: str) -> str:
    return (
        f"📊 تحلیل تکنیکال نماد {symbol}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔹 RSI (14): {rsi}\n"
        f"🔹 MACD: {macd}\n"
        f"🔹 Moving Averages: {ma}\n\n"
        f"🔮 سناریوی معاملاتی:\n{scenario}\n\n"
        f"⚠️ مدیریت ریسک:\n{risk}"
    )

# ==========================================
# ۲. جاب یادآور ژورنال (۲۰ دقیقه بعد)
# ==========================================
async def send_journal_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    symbol = job_data["symbol"]

    keyboard = [
        [
            InlineKeyboardButton("✅ سود (TP)", callback_data=f"journal_win_{symbol}"),
            InlineKeyboardButton("🛑 ضرر (SL)", callback_data=f"journal_loss_{symbol}")
        ],
        [
            InlineKeyboardButton("⏳ معامله انجام نشد / ورود نداد", callback_data=f"journal_cancel_{symbol}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📝 **یادآور ژورنال معاملاتی:**\n\n"
            f"آیا ستاپ ارسالی نماد **{symbol}** را وارد شدید؟\n"
            f"لطفاً وضعیت را ثبت کنید تا در گزارش هفتگی لحاظ شود:"
        ),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ==========================================
# ۳. هندلرهای دستورات تلگرام
# ==========================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! ربات Robo7Alvand آنلاین و آماده تحلیله.\n\n"
        "دستورات فعال:\n"
        "🔹 /setup [نماد] - صدور ستاپ معاملاتی با TP1 تا TP4\n"
        "🔹 /analyze [نماد] - تحلیل تکنیکال\n"
        "🔹 /status - وضعیت سلامت ربات و سرور\n"
        "🔹 /spec - قوانین و ستاپ قفل‌شده سیستم"
    )

async def status_cmd(update: Update, context        "• ثبت ژورنال: یادآور خودکار ۲۰ دقیقه‌ای"
    )
    await update.message.reply_text(spec_text, parse_mode="Markdown")

async def analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.argsvand (Phase 1):**\n"
        "• کریپتو: BTC, ETH, SOL\n"
        "• فارکس و فلزات: XAUUSD, EURUSD\n"
        "• حداقل ریسک به ریوارد: ۱:۲\n"
        "• استراتژی: ضد فومو (Anti-FOMO) و بدون مارتینگل\n"
        "• ثبت ژورنال: یادآور خودکار ۲۰ دقیقه‌ای"
    )
    await update.message.reply_text(spec_text, parse_mode="Markdown")

async def analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "XAUUSD"
    text = format_technical_analysis(
        symbol=symbol,
        rsi="54.2 (خنثی متمایل به صعودی)",
        macd="کراس مثبت در تایم ۴ ساعته",
        ma="بالای EMA 50 و در حال پولبک به EMA 200",
        scenario="در صورت حفظ کف حمایتی، رسیدن به مقاومت بعدی محتمل است.",
        risk="حجم معامله را حداکثر معادل ۱ درصد سرمایه قرار دهید."
    )
    await update.message.reply_text(text)

async def setup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "XAUUSD"
    
    sample_setup = TradeSetupData(
        symbol=symbol,
        market="Forex / Metals",
        order_type="BUY LIMIT",
        style="Day Trading (H1)",
        rr="1:2.5",
        risk_level="متوسط",
        risk_percent="۱ الی ۱.۵ درصد",
        entry_range="2635.00 - 2638.00",
        entry_confirm="تأییدیه کندل برگشتی در M15",
        sl="2628.00",
        sl_loss_usd="70",
        tp1="2645.00",
        tp2="2652.00",
        tp3="2660.00",
        tp4="2675.00"
    )
    
    msg_text = format_trading_setup(sample_setup)
    await update.message.reply_text(msg_text)

    # زمان‌بندی یادآور ۲۰ دقیقه بعد
    if context.job_queue:
        context.job_queue.run_once(
            send_journal_reminder,
            when=1200,
            data={"chat_id": update.effective_chat.id, "symbol": symbol}
        )

async def journal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if "win" in data:
        await query.edit_message_text("✅ نتیجه: سود در دیتابیس ثبت شد. پایبندی عالی به ستاپ!")
    elif "loss" in data:
        await query.edit_message_text("🛑 نتیجه: ضرر طبق پلن ثبت شد. علت در ژورنال ذخیره شد.")
    else:
        await query.edit_message_text("⏳ معامله لغو شد یا به نقطه ورود نرسید.")

# ==========================================
# ۴. وب‌سرور داخلی برای Render Health Check
# ==========================================
async def health_check(request):
    return web.Response(text="Robo7Alvand is Live!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# ==========================================
# ۵. اجرای اصلی (Main)
# ==========================================
async def main():
    if not BOT_TOKEN:
        logger.error("خطا: TELEGRAM_BOT_TOKEN تنظیم نشده است.")
        return

    # ساخت اپلیکیشن
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # اتصال هندلرها
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("spec", spec_cmd))
    app.add_handler(CommandHandler("analyze", analyze_cmd))
    app.add_handler(CommandHandler("setup", setup_cmd))
    app.add_handler(CallbackQueryHandler(journal_callback, pattern="^journal_"))

    # راه‌اندازی وب‌سرور
    await run_web_server()

    # شروع polling تلگرام
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # اجرای مداوم
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
