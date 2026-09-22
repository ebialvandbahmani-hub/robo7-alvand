import os
import asyncio
import logging
from dataclasses import dataclass
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# تنظیم لاگ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# کانفیگ
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENfluy2ymmkd5X0X")
PORT = int(os.environ.get("PORT", 8080))
USER_MODES = {}

@dataclass
class TradeSetup:
    entry: float; stop_loss: float; take_profit_1: float; take_profit_2: float; risk_reward: str; note: str

def generate_setup(symbol: str, current_price: float, support: float, resistance: float) -> TradeSetup:
    entry = support * 1.005
    stop_loss = support * 0.985
    risk = entry - stop_loss
    return TradeSetup(round(entry, 4), round(stop_loss, 4), round(entry + (risk*2), 4), round(entry + (risk*3), 4), "1:2 و 1:3", "فقط ورود پله‌ای نزدیک حمایت. حفظ سرمایه اولویت اول.")

def get_risk_management_guideline(text: str) -> str:
    risk_info = "ریسک حداکثر ۲٪ سرمایه در هر معامله.\nقوانین: بدون مارتینگل، بدون FOMO."
    return "🛡 راهنمای مدیریت ریسک:\n\n" + risk_info

BASE_MARKET_DATA = {
    "BTC": {"name": "بیت‌کوین", "price": 64000, "sup": 62000, "res": 66000, "trend": "صعودی"},
    "ETH": {"name": "اتریوم", "price": 2600, "sup": 2500, "res": 2700, "trend": "نوسانی"},
    "SOL": {"name": "سولانا", "price": 145, "sup": 135, "res": 155, "trend": "صعودی"},
    "TRX": {"name": "ترون", "price": 0.15, "sup": 0.14, "res": 0.16, "trend": "تثبیت"},
    "XAUUSD": {"name": "انس طلا", "price": 2620, "sup": 2600, "res": 2650, "trend": "نوسان بالا"}
}

ALIASES = {"بیت کوین": "BTC", "اتریوم": "ETH", "سولانا": "SOL", "ترون": "TRX", "طلا": "XAUUSD", "انس": "XAUUSD"}

def get_market_info(text: str):
    key = text.upper()
    key = ALIASES.get(text, key)
    if key in BASE_MARKET_DATA: return key, BASE_MARKET_DATA[key]
    return key, {"name": key, "price": 100.0, "sup": 90.0, "res": 110.0, "trend": "نامشخص (داینامیک)"}

# کیبوردها
def main_menu():
    return ReplyKeyboardMarkup([["🎯 ستاپ‌های معاملاتی", "📊 تحلیل تکنیکال"], ["💰 مدیریت ریسک", "📋 راهنما"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! Robo7Alvand آماده است.", reply_markup=main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # مسیریابی با استفاده از کلمات کلیدی (مقاوم در برابر ایموجی)
    if "بازگشت" in text:
        USER_MODES[user_id] = None
        await update.message.reply_text("به منوی اصلی برگشتید.", reply_markup=main_menu())
    
    elif "ستاپ" in text:
        USER_MODES[user_id] = "SETUP"
        await update.message.reply_text("لطفاً نام نماد را تایپ کنید (مثلا: BTC یا طلا):", reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت به منوی اصلی"]], resize_keyboard=True))
        
    elif "تحلیل" in text:
        USER_MODES[user_id] = "ANALYSIS"
        await update.message.reply_text("لطفاً نام نماد را تایپ کنید:", reply_markup=ReplyKeyboardMarkup([["🔙 بازگشت به منوی اصلی"]], resize_keyboard=True))
    
    elif USER_MODES.get(user_id) == "SETUP":
        sym, info = get_market_info(text)
        s = generate_setup(sym, info["price"], info["sup"], info["res"])
        await update.message.reply_text(f"🎯 ستاپ {info['name']}\nورود: {s.entry}\nحد ضرر: {s.stop_loss}\nاهداف: {s.take_profit_1} و {s.take_profit_2}\n{s.note}")
        
    elif USER_MODES.get(user_id) == "ANALYSIS":
        sym, info = get_market_info(text)
        await update.message.reply_text(f"📊 تحلیل {info['name']}\nروند: {info['trend']}\nحمایت: {info['sup']}\nمقاومت: {info['res']}")
        
    else:
        await update.message.reply_text("لطفاً از منوی زیر استفاده کنید:", reply_markup=main_menu())

# اجرای وب سرور و ربات
async def health(request): return web.Response(text="OK")
async def main():
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT); await site.start()
    
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))
    await bot_app.run_polling()

if __name__ == "__main__": asyncio.run(main())
