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

# تنظیمات لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# خواندن متغیرها
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))

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
        f"⚖️ ریسک به ریوارد: {d.rr}\n"
        f"💼 پیشنهادی: {d.risk_percent}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 محدوده ورود: {d.entry_range}\n"
        f"🛑 حد ضرر: {d.sl}\n"
        f"🎯 اهداف: {d.tp1} | {d.tp2} | {d.tp3} | {d.tp4}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏰ یادآور ژورنال ۲۰ دقیقه دیگر ارسال می‌شود."
    )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Robo7Alvand آنلاین است. دستورات: /setup, /analyze, /status")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 سیستم فعال و آماده است.")

async def setup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "XAUUSD"
    setup = TradeSetupData(
        symbol=symbol, market="Forex", order_type="BUY", style="Scalp",
        rr="1:2", risk_level="متوسط", risk_percent="۱٪",
        entry_range="2635", entry_confirm="کندل M15",
        sl="2628", sl_loss_usd="70",
        tp1="2645", tp2="2652", tp3="2660", tp4="2675"
    )
    await update.message.reply_text(format_trading_setup(setup))
    context.job_queue.run_once(lambda ctx: ctx.bot.send_message(chat_id=update.effective_chat.id, text="یادآوری: معامله را در ژورنال ثبت کنید."), 1200)

async def health_check(request):
    return web.Response(text="Robo7Alvand is Live!")

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN یافت نشد!")
        return
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("setup", setup_cmd))
    
    # راه‌اندازی سرور برای Render
    runner = web.AppRunner(web.Application())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
