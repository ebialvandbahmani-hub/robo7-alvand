import os
import sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- 1. FLASK WEB SERVER FOR RENDER HEALTH CHECK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Robo7Alvand is running smoothly!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. DATABASE SETUP ---
DB_NAME = "robo7.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            market TEXT,
            capital TEXT,
            experience TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 3. CONVERSATION STATES FOR ONBOARDING ---
NAME, PHONE, MARKET, CAPITAL, EXPERIENCE = range(5)

# --- KEYBOARDS ---
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ['📊 تحلیل نماد', '📋 لیست پایش'],
        ['⚙️ وضعیت سیستم', '❓ راهنما']
    ],
    resize_keyboard=True
)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await update.message.reply_text(
            f"سلام {user[0]} عزیز! 👋\nبه ربات روبو۷ الوند خوش آمدید.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "سلام! 👋 به ربات دستیار تحلیلی **روبو۷ الوند** خوش آمدید.\n\n"
            "جهت استفاده بهتر، لطفاً فرآیند ثبت‌نام کوتاه را تکمیل کنید.\n\n"
            "۱. لطفاً **نام و نام خانوادگی** خود را وارد کنید:"
        )
        return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("۲. لطفاً **شماره تماس** خود را وارد کنید (یا بنویسید 'ندارم'):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    market_keyboard = ReplyKeyboardMarkup([['بورس ایران', 'کریپتو'], ['فورکس', 'همه موارد']], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("۳. بازار اصلی فعالیت شما کدام است؟", reply_markup=market_keyboard)
    return MARKET

async def get_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['market'] = update.message.text
    capital_keyboard = ReplyKeyboardMarkup([['زیر ۵۰ میلیون', '۵۰ تا ۲۰۰ میلیون'], ['بالای ۲۰۰ میلیون']], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("۴. حدود سرمایه فعال شما چقدر است؟", reply_markup=capital_keyboard)
    return CAPITAL

async def get_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['capital'] = update.message.text
    exp_keyboard = ReplyKeyboardMarkup([['مبتدی', 'متوسط'], ['حرفه‌ای']], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("۵. سطح تجربه خود را در معامله‌گری مشخص کنید:", reply_markup=exp_keyboard)
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or ""

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, full_name, phone, market, capital, experience)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, username,
        context.user_data.get('full_name'),
        context.user_data.get('phone'),
        context.user_data.get('market'),
        context.user_data.get('capital'),
        context.user_data.get('experience')
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "✅ **ثبت‌نام شما با موفقیت انجام شد!**\n\nاکنون می‌توانید از تمام امکانات ربات استفاده کنید.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("فرآیند ثبت‌نام لغو شد. جهت شروع دوباره /start را بزنید.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

# --- COMMAND HANDLERS ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ **راهنمای ربات روبو۷ الوند:**\n\n"
        "📊 `/analyze [نام نماد]` - تحلیل سریع نماد (مثال: `/analyze فولاد`)\n"
        "📋 `/watch` - مشاهده لیست پایش شما\n"
        "⚙️ `/status` - وضعیت فنی و ارتباط ربات\n"
        "❓ `/help` - نمایش این راهنما"
    )
    await update.message.reply_text(help_text, reply_markup=MAIN_KEYBOARD)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        "⚙️ **وضعیت سیستم:**\n\n"
        "🟢 وضعیت ربات: آنلاین و فعال\n"
        "🗄 دیتابیس: متصل (SQLite)\n"
        "🌐 سرور: Render Web Service\n"
        "⏱ تاخیر پاسخگویی: عالی"
    )
    await update.message.reply_text(status_text, reply_markup=MAIN_KEYBOARD)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        symbol = context.args[0]
        await update.message.reply_text(f"📊 در حال بررسی نماد **{symbol}**...\n\nموتور تحلیلی در فاز آزمایشی قرار دارد. داده‌های پایه‌ای ثبت شدند. ✅", reply_markup=MAIN_KEYBOARD)
    else:
        await update.message.reply_text("لطفاً نام نماد را جلوی دستور بنویسید.\nمثال: `/analyze فولاد` یا `/analyze XAUUSD`", reply_markup=MAIN_KEYBOARD)

async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watch_text = (
        "📋 **واچ‌لیست شما:**\n\n"
        "۱. 🪙 طلا / XAUUSD\n"
        "۲. 📈 فولاد (بورس)\n"
        "۳. ₿ بیت‌کوین / BTCUSDT\n\n"
        "جهت افزودن نماد جدید از `/watch add [نماد]` استفاده کنید."
    )
    await update.message.reply_text(watch_text, reply_markup=MAIN_KEYBOARD)

# --- TEXT BUTTON HANDLER ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '📊 تحلیل نماد':
        await update.message.reply_text("لطفاً نماد مورد نظر را به این صورت وارد کنید:\n`/analyze نام_نماد` (مثال: `/analyze فولاد`)")
    elif text == '📋 لیست پایش':
        await watch_command(update, context)
    elif text == '⚙️ وضعیت سیستم':
        await status_command(update, context)
    elif text == '❓ راهنما':
        await help_command(update, context)
    else:
        await update.message.reply_text("پیام شما دریافت شد. برای دیدن گزینه‌ها از دکمه‌های پایین یا دستور /help استفاده کنید.", reply_markup=MAIN_KEYBOARD)

# --- MAIN FUNCTION ---
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable is missing!")
        return

    # Start Flask server in background thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram Bot
    app = ApplicationBuilder().token(token).build()

    # Onboarding Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            MARKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_market)],
            CAPITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_capital)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('analyze', analyze_command))
    app.add_handler(CommandHandler('watch', watch_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
