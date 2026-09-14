import logging
import os
from flask import Flask
from threading import Thread
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توکن ربات روبو الوند
TOKEN = '8833221517:AAHfq4qVa_hJet60QnyG-p-yRyXuTN4jLWE'

# وب سرور Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "ربات فعال است!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="سلام ابی جان! ربات روبو الوند با موفقیت فعال شد :rocket:")

# تابع دکمه‌ها
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"گزینه انتخاب شد: {query.data}")

if __name__ == '__main__':
    # اجرای Flask در پس‌زمینه
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # ساخت و اجرای ربات تلگرام
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling()
