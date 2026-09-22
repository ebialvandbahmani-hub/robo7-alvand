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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", 8080))

# ==========================================
# ۱. مدل داده و فرمت‌بندی
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
        f"━━━━━━━━━━━━━━━━━━\: str
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
        f"⚠️ **اسپرد:** ۳ الی ۵ پیپ فاصله را در ورود و SL لحاظ کنید.\n"
        f"⏰ یادآور ژورنال‌نویسی ۲۰ دقیقه دیگر ارسال می‌شود."
    )

def format_technical_analysis(symbol: str, rsi: str, macd: str, ma: str, scenario: str, risk: str)7Alvand آنلاین و آماده تحلیله.\n\n"
        "دستورات:\n"
        "🔹 /setup [نماد] - صدور ستاپ معاملاتی\n"
        "🔹 /analyze [نماد] - تحلیل تکنیکال\n"
        "🔹 /status - وضعیت سلامت ربات و سرور\n"
        "🔹 /spec - مشاهده مشخصات و قوانین سیستم"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 سیستم فعال است. تمام اندیکاتورها و موتور ریسک در دسترس هستند.")

async def spec_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    spec_text = (
        "📋 **سند فنی Robo7Alvand (Phase 1):**\n"
        "• بازارها: Crypto (BTC, ETH, SOL) و Forex (XAUUSD, EURUSD)\n"
        "• حداقل R:R مجاز: ۱:۲\n"
        "• استراتژی: Anti-FOMO، بدون مارتینگل، بدون ورود در میانه رنج\n"
        "• سیستم ژورنال: خودکار پس از ۲۰ دقیقه"
    )
    await update.message.reply_text(spec_text, parse_mode="Markdown")

async def analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "XAUUSD"
    text = format_technical_analysis(
        symbol=symbol,
        rsi="54.2 (خنثی متمایل به صعودی)",
        macd="کراس مثبت در تایم‌فریم ۴ ساعته",
        ma="بالای EMA 50 و نزدیک به EMA 200",
        scenario="در صورت حفظ سطح حمایتی، حرکت به سمت سقف محلی محتمل است.",
        risk="حجم معامله را متناسب با ۱٪ کل مارجین تنظیم کنید."
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
    await update.message.reply_text(msg_text, parse_mode="Markdown")

    # زمان‌بندی یادآور برای ۲۰ دقیقه بعد (1200 ثانیه)
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
        await query.edit_message_text("✅ نتیجه: سود ثبت شد. آفرین به انضباط معاملاتی!")
    elif "loss" in data:
        await query.edit_message_text("🛑 نتیجه: ضرر طبق پلن ثبت شد. بررسی علت در ژورنال توصیه می‌شود.")
    else:
        await query.edit_message_text("⏳ معامله انجام نشد یا کنسل گردید.")

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
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("لطفاً توکن ربات را در متغیرهای محیطی ست کنید.")

    # راه‌اندازی ربات
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("spec", spec_cmd))
    app.add_handler(CommandHandler("analyze", analyze_cmd))
    app.add_handler(CommandHandler("setup", setup_cmd))
    app.add_handler(CallbackQueryHandler(journal_callback, pattern="^journal_"))

    # راه‌اندازی سرور Health Check
    await run_web_server()

    # اجرای polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # نگه‌داشتن برنامه در حال اجرا
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
