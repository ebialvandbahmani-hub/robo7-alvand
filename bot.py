from dataclasses import dataclass
from typing import Optional, Tuple

ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XAUUSD", "EURUSD"}

@dataclass
class TradeSetup:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_amount: float = 0.0
    reward_amount: float = 0.0
    risk_reward_ratio: float = 0.0
    is_valid: bool = False
    rejection_reason: Optional[str] = None

class RiskEngine:
    MIN_RR_RATIO: float = 2.0  # حداقل نسبت ریسک به ریوارد مجاز ۱ به ۲

    @classmethod
    def validate_and_calculate(cls, symbol: str, side: str, entry: float, sl: float, tp: float) -> TradeSetup:
        symbol = symbol.upper()
        side = side.upper()

        setup = TradeSetup(
            symbol=symbol,
            side=side,
            entry=entry,
            stop_loss=sl,
            take_profit=tp
        )

        # اعتبارسنجی نماد مجاز
        if symbol not in ALLOWED_SYMBOLS:
            setup.rejection_reason = (
                f"نماد {symbol} در لیست مجاز فاز ۱ نیست.\n"
                f"نمادهای مجاز: {', '.join(sorted(ALLOWED_SYMBOLS))}"
            )
            return setup

        # اعتبارسنجی جهت معامله
        if side not in ["BUY", "SELL"]:
            setup.rejection_reason = "جهت معامله فقط می‌تواند BUY یا SELL باشد."
            return setup

        # بررسی منطق حد ضرر و تارگت نسبت به نقطه ورود
        if side == "BUY":
            if sl >= entry:
                setup.rejection_reason = "در معامله خرید (BUY)، حد ضرر باید پایین‌تر از نقطه ورود باشد."
                return setup
            if tp <= entry:
                setup.rejection_reason = "در معامله خرید (BUY)، تارگت سود باید بالاتر از نقطه ورود باشد."
                return setup
            risk = entry - sl
            reward = tp - entry
        else:  # SELL
            if sl <= entry:
                setup.rejection_reason = "در معامله فروش (SELL)، حد ضرر باید بالاتر از نقطه ورود باشد."
                return setup
            if tp >= entry:
                setup.rejection_reason = "در معامله فروش (SELL)، تارگت سود باید پایین‌تر از نقطه ورود باشد."
                return setup
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            setup.rejection_reason = "محاسبه فاصله ریسک یا ریوارد نامعتبر است."
            return setup

        rr = round(reward / risk, 2)
        setup.risk_amount = round(risk, 4)
        setup.reward_amount = round(reward, 4)
        setup.risk_reward_ratio = rr

        # فیلتر سخت‌گیرانه ضد FOMO
        if rr < cls.MIN_RR_RATIO:
            setup.rejection_reason = (
                f"نسبت ریسک به ریوارد 1:{rr} ضعیف‌تر از حداقل استاندارد (1:{cls.MIN_RR_RATIO}) است.\n"
                "ورود در میانه رنج یا با ریسک غیرمنطقی نقض صریح قوانین سیستم است."
            )
            return setup

        setup.is_valid = True
        return setup
