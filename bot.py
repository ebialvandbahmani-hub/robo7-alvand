import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE"

app = Flask(__name__)

@app.route('/')
def home():
    return "Robo Alvand is Online and Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(":bar_chart: تحلیل تکنیکال", callback_data="tech")],
        [InlineKeyboardButton(":moneybag: واچ‌لیست و طلا/نقره", callback_data="watchlist")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام ابی عزیز! خوش اومدی به روبو الوند :rocket:\nیکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "tech":
        await query.edit_message_text(":bar_chart: بخش تحلیل تکنیکال به زودی فعال می‌شود.")
    elif query.data == "watchlist":
        await query.edit_message_text(":moneybag: واچ‌لیست و قیمت‌ها در حال اتصال هستند.")

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling(drop_pending_updates=True)
