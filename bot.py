# -*- coding: utf-8 -*-
"""
Robo7Alvand - Telegram Trading Bot (Monolithic Version)
All risk-engine functions integrated. No external module dependencies.
"""

import os
import re
import time
import threading
import requests
from flask import Flask

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
PORT = int(os.environ.get("PORT", 8080))
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Alias mapping for common symbols
ALIASES = {
    "بیت‌کوین": "BTCUSDT", "بیت کوین": "BTCUSDT", "btc": "BTCUSDT", "bitcoin": "BTCUSDT",
    "اتریوم": "ETHUSDT", "eth": "ETHUSDT", "ethereum": "ETHUSDT",
    "سولانا": "SOLUSDT", "sol": "SOLUSDT", "solana": "SOLUSDT",
    "ترون": "TRXUSDT", "trx": "TRXUSDT", "tron": "TRXUSDT",
    "دوج": "DOGEUSDT", "doge": "DOGEUSDT",
    "کاردانو": "ADAUSDT", "ada": "ADAUSDT",
    "طلا": "XAUUSD", "گلد": "XAUUSD", "xauusd": "XAUUSD", "gold": "XAUUSD",
    "مارکت": "MARKET", "بازار": "MARKET", "market": "MARKET",
}

DEFAULT_MARKET = {
    "name": "مارکت 🎯",
    "price": 100.0,
    "support": 95.0,
    "resistance": 108.0,
}

# ================= RISK ENGINE (integrated) =================

def normalize_symbol(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s*/\s*", "", t)
    return ALIASES.get(t, t.upper())


def get_market_info(symbol_raw: str) -> dict:
    """Return market data for any symbol. Tries Binance API for crypto."""
    symbol = normalize_symbol(symbol_raw)

    if symbol == "MARKET":
        return dict(DEFAULT_MARKET)

    if symbol == "XAUUSD":
        return {"name": "طلا (XAUUSD)", "price": 2650.0, "support": 2600.0, "resistance": 2720.0}

    # Try live price from Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                         params={"symbol": symbol}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = float(data["lastPrice"])
            high = float(data["highPrice"])
            low = float(data["lowPrice"])
            return {
                "name": f"نماد شناسایی شد: {symbol}",
                "price": price,
                "support": round(low * 0.99, 6),
                "resistance": round(high * 1.01, 6),
            }
    except Exception:
        pass

    # Fallback: generic standard framework for unknown symbols
    return {
        "name": f"نماد شناسایی شد: {symbol}",
        "price": 100.0,
        "support": 95.0,
        "resistance": 108.0,
    }


def generate_setup(info: dict) -> str:
    """Generate a trade setup with entry ladders, SL, and TP (min R:R 1:2)."""
    price = info["price"]
    support = info["support"]
    resistance = info["resistance"]
    name = info["name"]

    # Long setup (laddered entry near support)
    entry1 = support * 1.005
    entry2 = support * 0.995
    stop_loss = support * 0.97          # ~3% below support
    target = entry1 + (entry1 - stop_loss) * 2   # forces R:R >= 1:2

    risk_pct = abs((entry1 - stop_loss) / entry1) * 100

    msg = (
        f"🔍 {name}\n"
        f"💵 قیمت فعلی: {price:.4f}\n\n"
        f"📍 ورود پله ۱: {entry1:.4f}\n"
        f"📍 ورود پله ۲: {entry2:.4f}\n"
        f"🛑 حد ضرر (SL): {stop_loss:.4f}\n"
        f"🎯 حد سود (TP): {target:.4f}\n"
        f"⚖️ نسبت ریسک به ریوارد: 1:2 (حداقل)\n"
        f"📉 ریسک هر معامله: حداکثر 2٪ سرمایه\n"
        f"📊 ریسک این ستاپ: {risk_pct:.2f}٪\n\n"
        f"💡 مدیریت سرمایه: با ریسک ۲٪ و فاصله استاپ {risk_pct:.2f}٪، "
        f"حجم پوزیشن = (2 ÷ {risk_pct:.2f}) از کل سرمایه در هر پله تقسیم شود.\n\n"
        f"برای ستاپ کامل، «🎯 ستاپ‌های معاملاتی» را بزنید."
    )
    return msg


def get_risk_management_guideline() -> str:
    return (
        "💰 رهنما و قوانین مدیریت سرمایه:\n\n"
        "1️⃣ ریسک هر معامله: حداکثر ۲٪ کل سرمایه\n"
        "2️⃣ ریسک کل پرتفوی (همه پوزیشن‌های باز): حداکثر ۶٪\n"
        "3️⃣ نسبت ریسک به ریوارد: حداقل 1:2\n"
        "4️⃣ ورود پله‌ای: ۵۰٪ پله اول، ۵۰٪ پله دوم\n"
        "5️⃣ پس از ۳ استاپ متوالی، ۲۴ ساعت معامله نکنید\n"
        "6️⃣ هیچ‌گاه بدون حد ضرر وارد نشوید\n"
        "7️⃣ سودهای پله‌ای را برداشت کنید (Trail Stop)"
    )

# ================= TELEGRAM =================

KEYBOARD = {
    "keyboard": [
        [{"text": "🎯 ستاپ‌های معاملاتی"}, {"text": "📊 تحلیل تکنیکال"}],
        [{"text": "💰 مدیریت ریسک"}, {"text": "📋 راهنما و قوانین"}],
    ],
    "resize_keyboard": True,
}

WELCOME = (
    "👋 به ربات Robo7Alvand خوش آمدید!\n\n"
    "🔍 نام هر نمادی را تایپ کنید (فارسی یا انگلیسی):\n"
    "مثال: بیت‌کوین، ترون، دوج، طلا، BTC، TRX ...\n\n"
    "یا از دکمه‌های زیر استفاده کنید."
)


def send_message(chat_id: str, text: str, keyboard=True):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = KEYBOARD
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"[send_message error] {e}")


def handle_update(update: dict):
    msg = update.get("message")
    if not msg:
        return
    chat_id = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()

    if text.startswith("/start"):
        send_message(chat_id, WELCOME)
        return

    if "مدیریت ریسک" in text or "مدیریت" in text:
        send_message(chat_id, get_risk_management_guideline())
        return

    if "راهنما" in text or "قوانین" in text:
        send_message(chat_id, WELCOME + "\n\n" + get_risk_management_guideline())
        return

    if "تحلیل تکنیکال" in text or "تکنیکال" in text:
        info = get_market_info("market")
        send_message(chat_id, generate_setup(info))
        return

    if "ستاپ" in text or "معاملاتی" in text:
        info = get_market_info("market")
        send_message(chat_id, generate_setup(info))
        return

    # Free-typed symbol (dynamic)
    info = get_market_info(text)
    send_message(chat_id, generate_setup(info))


def poll():
    print("[bot] Long polling started...")
    offset = 0
    while True:
        try:
            r = requests.get(f"{TELEGRAM_API}/getUpdates",
                             params={"offset": offset, "timeout": 30}, timeout=35)
            data = r.json()
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        except Exception as e:
            print(f"[poll error] {e}")
            time.sleep(3)

# ================= FLASK HEALTH SERVER =================
app = Flask(__name__)


@app.route("/")
@app.route("/health")
def health():
    return {"status": "ok", "bot": "Robo7Alvand", "version": "2.1-monolithic"}, 200


def run_flask():
    app.run(host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    run_flask()
