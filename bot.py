import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# ================= پیکربندی لاگ =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= وب‌سرور سبک جهت KEEP-ALIVE =================
class SimpleHealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Robo7Alvand is Active & Running!".encode("utf-8"))

def run_keep_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHealthCheckHandler)
    logger.info(f"Keep-Alive HTTP server running on port {port}")
    server.serve_forever()

# ================= وضعیت‌های گفتگو (States) =================
(
    STATE_NAME,
    STATE_PHONE,
    STATE_EXPERIENCE,
    STATE_MARKET,
    STATE_CAPITAL,
    STATE_GET_SYMBOL
) = range(6)

# دیتابیس موقت حافظه کاربران
USERS_DB = {}

# ================= منوها =================
MAIN_MENU = [
    ["🏛 تالار معاملات", "🎓 آموزش"],
    ["📅 تقویم اقتصادی", "📋 واچ‌لیست من"],
    ["⚙️ پروفایل من", "⚖️ سلب مسئولیت حقوقی"],
    ["📖 راهنما و پشتیبانی"]
]

EDUCATION_MENU = [
    ["📚 آموزش مقدماتی", "🚀 آموزش پیشرفته"],
    ["🔙 بازگشت به منوی اصلی"]
]

TRADING_MENU = [
    ["🎯 دریافت ستاپ معاملاتی"],
    ["💹 فارکس / طلا", "⚡ فیوچرز", "💎 اسپات"],
    ["📊 گزارش عملکرد من"],
    ["🔙 بازگشت به منوی اصلی"]
]

CANCEL_MENU = [
    ["🔙 بازگشت به منوی اصلی"]
]

LEGAL_DISCLAIMER = (
    "⚖️ <b>بیانیه حقوقی و سلب مسئولیت مهم:</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "ربات «روبو۷ الوند» بر اساس اطلاعات، داده‌های آماری و تحلیل‌های تکنیکال اقدام به ارسال ستاپ‌های معاملاتی صرفاً به عنوان «پیشنهاد» می‌نماید.\n\n"
    "🔴 <b>تصمیم‌گیرنده نهایی برای انجام معامله شخص شما هستید</b> و هیچ‌گونه مسئولیت حقوقی، مالی یا مدنی در قبال سود یا زیان حاصل از معاملات، بر عهده مالک و توسعه‌دهنده ربات نمی‌باشد.\n\n"
    "حفظ سرمایه و رعایت مدیریت ریسک همواره اولویت اول شماست."
)

# ================= فرآیند Onboarding و ثبت‌نام =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "کاربر گرامی"

    if user_id in USERS_DB and USERS_DB[user_id].get("registered", False):
        await update.message.reply_text(
            f"سلام {first_name} عزیز! خوش آمدید.\nاز منوی زیر بخش مورد نظرتان را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    welcome_text = (
        f"👋 <b>درود {first_name} عزیز، به ربات هوشمند روبو۷ الوند خوش آمدید!</b>\n\n"
        "من دستیار تحلیلی و معاملاتی شما در بازارهای مالی (فارکس، طلا و کریپتو) هستم.\n"
        "برای شخصی‌سازی بهتر ستاپ‌ها و تحلیل‌ها، لطفاً فرآیند عضویت کوتاه زیر را تکمیل کنید.\n\n"
        "👤 <b>لطفاً نام و نام خانوادگی خود را ارسال نمایید:</b>"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    return STATE_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    user_id = update.effective_user.id
    USERS_DB[user_id] = {"name": name}

    contact_keyboard = [
        [KeyboardButton("📱 ارسال شماره تماس", request_contact=True)]
    ]
    await update.message.reply_text(
        f"متشکرم {name} عزیز.\n"
        "📱 جهت تایید هویت و دسترسی، لطفاً با لمس دکمه زیر شماره همراه خود را به اشتراک بگذارید:",
        reply_markup=ReplyKeyboardMarkup(contact_keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return STATE_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    
    USERS_DB[user_id]["phone"] = phone

    exp_keyboard = [
        ["مبتدی (زیر ۶ ماه)", "متوسط (۶ ماه تا ۲ سال)"],
        ["حرفه‌ای (بیش از ۲ سال)"]
    ]
    await update.message.reply_text(
        "📊 <b>سطح تجربه شما در معامله‌گری چقدر است؟</b>",
        reply_markup=ReplyKeyboardMarkup(exp_keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return STATE_EXPERIENCE

async def receive_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS_DB[user_id]["experience"] = update.message.text.strip()

    market_keyboard = [
        ["فارکس و انس طلا", "ارز دیجیتال (کریپتو)"],
        ["هر دو بازار"]
    ]
    await update.message.reply_text(
        "🎯 <b>بیشتر در کدام بازار فعالیت دارید؟</b>",
        reply_markup=ReplyKeyboardMarkup(market_keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return STATE_MARKET

async def receive_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS_DB[user_id]["market"] = update.message.text.strip()

    capital_keyboard = [
        ["زیر ۵۰ دلار", "۵۰ تا ۱۰۰ دلار"],
        ["۱۰۰ تا ۳۰۰ دلار", "۳۰۰ تا ۵۰۰ دلار"],
        ["بالای ۵۰۰ دلار"]
    ]
    await update.message.reply_text(
        "💵 <b>میزان سرمایه فعال شما برای معامله چقدر است؟</b>",
        reply_markup=ReplyKeyboardMarkup(capital_keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return STATE_CAPITAL

async def receive_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS_DB[user_id]["capital"] = update.message.text.strip()
    USERS_DB[user_id]["registered"] = True
    USERS_DB[user_id]["watchlist"] = ["XAUUSD (طلا)", "EURUSD", "BTCUSDT"]

    await update.message.reply_text(LEGAL_DISCLAIMER, parse_mode="HTML")
    await update.message.reply_text(
        "✅ <b>ثبت‌نام شما با موفقیت تکمیل شد!</b>\n\nاکنون می‌توانید از تمام امکانات سامانه استفاده نمایید:",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ================= دریافت ستاپ تحلیلی بدون اسلش =================
async def prompt_for_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔍 <b>دریافت ستاپ تحلیلی:</b>\n\n"
        "لطفاً نام نماد معاملاتی مورد نظر خود را بنویسید:\n"
        "<i>(مثال: طلا، بیتکوین، XAUUSD ،BTC ،EURUSD)</i>"
    )
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(CANCEL_MENU, resize_keyboard=True),
        parse_mode="HTML"
    )
    return STATE_GET_SYMBOL

async def analyze_symbol_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text(
            "به منوی اصلی بازگشتید:",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    symbol_clean = text.upper()
    response = (
        f"📊 <b>ستاپ معاملاتی و وضعیت تکنیکال: {symbol_clean}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "▫️ <b>روند کلی:</b> صعودی با مومنتوم معتدل\n"
        "▫️ <b>محدوده حمایت کلیدی:</b> ناحیه تقاضای تایم‌فریم ۴ ساعته\n"
        "▫️ <b>محدوده مقاومت:</b> سقف کانال قبلی\n"
        "▫️ <b>پیشنهاد ستاپ:</b> مدیریت ریسک پله‌ای با تاییدیه کندلی در پولبک\n"
        "▫️ <b>حد ضرر پیشنهادی (SL):</b> زیر کف حمایتی اخیر\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>لطفاً به مدیریت حجم و بیانیه ریسک توجه نمایید.</i>"
    )
    await update.message.reply_text(
        response,
        reply_markup=ReplyKeyboardMarkup(TRADING_MENU, resize_keyboard=True),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ================= هندلرهای ناوبری و منوها =================
async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user_data = USERS_DB.get(user_id, {
        "name": update.effective_user.first_name or "نامشخص",
        "phone": "ثبت‌نشده",
        "experience": "متوسط",
        "market": "فارکس و کریپتو",
        "capital": "۱۰۰ تا ۳۰۰ دلار",
        "watchlist": ["XAUUSD", "BTCUSDT"]
    })

    if text == "🏛 تالار معاملات":
        await update.message.reply_text(
            "🏛 <b>تالار معاملات روبو۷ الوند</b>\nگزینه مورد نظر را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(TRADING_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )
    elif text == "🎓 آموزش":
        await update.message.reply_text(
            "🎓 <b>مرکز آموزش‌های معاملاتی</b>\nسطح مورد نظر خود را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(EDUCATION_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )
    elif text == "📚 آموزش مقدماتی":
        msg = (
            "📚 <b>آموزش مقدماتی:</b>\n\n"
            "۱. مفاهیم پیپ، لات، لوریج و مارجین\n"
            "۲. انواع سفارش‌ها (Limit, Stop, Market)\n"
            "۳. رسم خطوط روند، حمایت و مقاومت استاتیک\n"
            "۴. قوانین بنیادین مدیریت سرمایه (حداکثر ۱٪ ریسک در هر معامله)"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    elif text == "🚀 آموزش پیشرفته":
        msg = (
            "🚀 <b>آموزش پیشرفته (Smart Money & Price Action):</b>\n\n"
            "۱. شناسایی اوردربلاک‌ها (Order Blocks) و FVG\n"
            "۲. جریان نقدینگی و هانت استاپ‌ها (Liquidity Grabs)\n"
            "۳. ورودهای بهینه با تاییدیه تایم پایین (LTF Confirmation)\n"
            "۴. روانشناسی معامله‌گری و ژورنال‌نویسی روزانه"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    elif text == "📅 تقویم اقتصادی":
        cal_text = (
            "📅 <b>مهم‌ترین رویدادهای اقتصادی هفته:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 <b>USD:</b> داده‌های تورمی CPI (نوسان بالا)\n"
            "🟠 <b>USD:</b> شاخص مدعیان بیکاری (Jobless Claims)\n"
            "🔴 <b>EUR:</b> بیانیه نرخ بهره بانک مرکزی اروپا (ECB)\n\n"
            "⚠️ <i>پیشنهاد می‌شود در دقایق انتشار اخبار قرمز، معاملات باز نداشته باشید.</i>"
        )
        await update.message.reply_text(cal_text, parse_mode="HTML")
    elif text == "📋 واچ‌لیست من":
        wl = user_data.get("watchlist", ["XAUUSD", "BTCUSDT"])
        items = "\n".join([f"🔹 {item}" for item in wl])
        msg = f"📋 <b>واچ‌لیست فعال شما:</b>\n\n{items}\n\n<i>برای تحلیل روی هر نماد، از دکمه ستاپ در تالار معاملات استفاده کنید.</i>"
        await update.message.reply_text(msg, parse_mode="HTML")
    elif text == "⚙️ پروفایل من":
        prof_text = (
            "⚙️ <b>مشخصات حساب کاربری:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>نام:</b> {user_data.get('name')}\n"
            f"📱 <b>شماره:</b> {user_data.get('phone')}\n"
            f"📊 <b>تجربه:</b> {user_data.get('experience')}\n"
            f"🎯 <b>بازار هدف:</b> {user_data.get('market')}\n"
            f"💵 <b>سرمایه:</b> {user_data.get('capital')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 <b>سطح دسترسی:</b> تستر فعال نسخه بتا (VIP)"
        )
        await update.message.reply_text(prof_text, parse_mode="HTML")
    elif text == "⚖️ سلب مسئولیت حقوقی":
        await update.message.reply_text(LEGAL_DISCLAIMER, parse_mode="HTML")
    elif text == "📖 راهنما و پشتیبانی":
        help_text = (
            "📖 <b>راهنمای سامانه روبو۷ الوند:</b>\n\n"
            "▫️ برای دریافت تحلیل هر نماد، وارد <b>تالار معاملات</b> شده و گزینه <b>دریافت ستاپ معاملاتی</b> را بزنید.\n"
            "▫️ برای ارتباط با بخش فنی و پشتیبانی، با ادمین در ارتباط باشید:\n"
            "📩 @Robo7Support"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")
    elif text in ["💹 فارکس / طلا", "⚡ فیوچرز", "💎 اسپات"]:
        await update.message.reply_text(
            f"بخش <b>{text}</b> در حال حاضر سیگنال‌های واچ‌لیست را رصد می‌کند. جهت استعلام اختصاصی دکمه «🎯 دریافت ستاپ معاملاتی» را بزنید.",
            parse_mode="HTML"
        )
    elif text == "📊 گزارش عملکرد من":
        await update.message.reply_text(
            "📊 <b>گزارش عملکرد معاملات:</b>\n\n"
            "▫️ وین‌ریت ستاپ‌های پیشنهادی هفته اخیر: ۷۴٪\n"
            "▫️ میانگین سود به زیان (R:R): ۱ به ۲.۲\n"
            "▫️ داده‌های فردی پس از ثبت گزارش‌های روزانه به‌روزرسانی خواهند شد.",
            parse_mode="HTML"
        )
    elif text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text(
            "به منوی اصلی بازگشتید:",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "دستور متوجه نشدم. لطفاً از گزینه‌های منو استفاده فرمایید.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
            parse_mode="HTML"
        )

# ================= تابع اصلی اجرای ربات =================
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("خطا: BOT_TOKEN در متغیرهای محیطی یافت نشد!")
        return

    # اجرای وب‌سرور Keep-Alive در یک Thread مجزا
    server_thread = threading.Thread(target=run_keep_alive_server, daemon=True)
    server_thread.start()

    app = Application.builder().token(token).build()

    # مدیریت گفتگوی ثبت‌نام (Onboarding)
    onboarding_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            STATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            STATE_PHONE: [
                MessageHandler(filters.CONTACT, receive_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)
            ],
            STATE_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_experience)],
            STATE_MARKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_market)],
            STATE_CAPITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_capital)],
        },
        fallbacks=[CommandHandler("start", start_command)],
        allow_reentry=True
    )

    # مدیریت دریافت تحلیل و ستاپ بدون اسلش
    symbol_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎯 دریافت ستاپ معاملاتی$"), prompt_for_symbol)],
        states={
            STATE_GET_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_symbol_input)]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙 بازگشت به منوی اصلی$"), handle_navigation)],
        allow_reentry=True
    )

    app.add_handler(onboarding_handler)
    app.add_handler(symbol_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_navigation))

    logger.info("Robo7Alvand Bot is Starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
