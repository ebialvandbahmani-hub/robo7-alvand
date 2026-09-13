import logging
import yfinance as yf
import pandas as pd
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# خواندن توکن از تنظیمات محیطی رندر، در صورت نبود از توکن پیش‌فرض استفاده می‌کند
TOKEN = os.getenv("BOT_TOKEN", "8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE")

SYMBOLS = {
    "gold": {"ticker": "GC=F", "name": "🥇 طلا (Gold / XAUUSD)"},
    "silver": {"ticker": "SI=F", "name": "🥈 نقره (Silver / XAGUSD)"},
    "oil": {"ticker": "CL=F", "name": "🛢 نفت خام (Crude Oil)"},
    "dow": {"ticker": "^DJI", "name": ":bar_chart: شاخص داوجونز (Dow Jones)"},
    "btc": {"ticker": "BTC-USD", "name": "🪙 بیت‌کوین (BTC/USDT)"},
    "eurusd": {"ticker": "EURUSD=X", "name": ":euro: یورو / دلار (EUR/USD)"}
}

def analyze_market(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1mo", interval="1h")
        if df.empty or len(df) < 30:
            df = ticker.history(period="1mo", interval="1d")
        
        if df.empty:
            return None
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        last_price = df['Close'].iloc[-1]
        last_rsi = df['RSI'].iloc[-1]
        ema20 = df['EMA20'].iloc[-1]
        ema50 = df['EMA50'].iloc[-1]
        
        support = df['Low'].tail(24).min()
        resistance = df['High'].tail(24).max()
        
        if last_price > ema20 > ema50 and last_rsi < 65:
            signal = "🟢 خرید (BUY) / روند صعودی"
            risk_tip = "ورود در اصلاح‌ها به سمت میانگین ۲۰"
        elif last_price < ema20 < ema50 and last_rsi > 35:
            signal = ":red_circle: فروش (SELL) / روند نزولی"
            risk_tip = "فروش در پولبک‌ها به مقاومت‌ها"
        elif last_rsi >= 70:
            signal = ":warning: اشباع خرید (Overbought) - احتیاط در ورود لانگ"
            risk_tip = "احتمال اصلاح قیمت بالا است"
        elif last_rsi <= 30:
            signal = ":warning: اشباع فروش (Oversold) - مراقب پوزیشن شورت باشید"
            risk_tip = "احتمال برگشت یا نوسان مثبت موقت"
        else:
            signal = ":white_circle: خنثی / رنج (Wait & See)"
            risk_tip = "صبر برای شکست حمایت یا مقاومت"

        return {
            "price": round(last_price, 2),
            "rsi": round(last_rsi, 1),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "signal": signal,
            "tip": risk_tip
        }
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🥇 انس طلا (Gold)", callback_data="gold"), InlineKeyboardButton("🥈 انس نقره (Silver)", callback_data="silver")],
        [InlineKeyboardButton("🛢 نفت (Crude Oil)", callback_data="oil"), InlineKeyboardButton(":bar_chart: داوجونز (US30)", callback_data="dow")],
        [InlineKeyboardButton("🪙 بیت‌کوین (BTC)", callback_data="btc"), InlineKeyboardButton(":euro: یورو/دلار (EUR/USD)", callback_data="eurusd")],
        [InlineKeyboardButton("🛡 راهنمای مدیریت ریسک و سرمایه", callback_data="risk_guide")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = ":crown: به ربات هوشمند تحلیلی Robo Alvand خوش آمدید!\n\n:point_down: لطفا بازار مورد نظرتان را انتخاب کنید:"
if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "main_menu":
        await start(update, context)
        return

    if data == "risk_guide":
        guide_text = "🛡 قوانین مدیریت ریسک (Robo Alvand):\n\n۱. قانون ۱-۲٪: ریسک حداکثر ۲٪ سرمایه.\n۲. سیو سود پله‌ای.\n۳. پرهیز از ترید در اخبار.\n\n:pushpin: حفظ سرمایه اولویت اول است."
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(":back: بازگشت به منو", callback_data="main_menu")]])
        await query.message.edit_text(guide_text, reply_markup=back_btn, parse_mode="Markdown")
        return

    if data in SYMBOLS:
        sym_info = SYMBOLS[data]
        await query.message.edit_text(f":hourglass_flowing_sand: در حال تحلیل {sym_info['name']} ...")
        result = analyze_market(sym_info["ticker"])
        if result:
            msg = f":bar_chart: تحلیل زنده {sym_info['name']}\n\n:heavy_dollar_sign: قیمت: {result['price']}\n:chart_with_upwards_trend: RSI: {result['rsi']}\n🟢 حمایت: {result['support']}\n:red_circle: مقاومت: {result['resistance']}\n\n:dart: سیگنال: {result['signal']}\n:bulb: توصیه: _{result['tip']}_"
        else:
            msg = ":x: خطا در دریافت داده‌ها."
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(":arrows_counterclockwise: بروزرسانی", callback_data=data)], [InlineKeyboardButton(":back: منو", callback_data="main_menu")]])
        await query.message.edit_text(msg, reply_markup=back_btn, parse_mode="Markdown")

# --- سرور Flask برای زنده نگه داشتن رندر ---
app = Flask(name)
@app.route('/')
def home():
    return "Robo Alvand is Active!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if name == 'main':
    Thread(target=run_flask).start()
    print(":rocket: Robo Alvand Bot is starting...")
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    bot_app.run_polling()
