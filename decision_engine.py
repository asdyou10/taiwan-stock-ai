"""V4 技術決策核心 v1：純函式，供即時畫面與歷史回測共用。

不使用未驗證財報；不輸出基本面買進許可。所有訊號僅依截至當日的收盤價。
"""
from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    trigger: str
    invalidation: str
    eligible: bool


def evaluate(close, ma20, ma60, macd_dif, macd_signal, holding=False, style="趨勢續抱型"):
    values = (close, ma20, ma60, macd_dif, macd_signal)
    if any(pd.isna(x) for x in values) or float(close) <= 0:
        return Decision("資料不足", "均線或 MACD 尚未形成有效訊號", "取得完整交易資料", "無", False)
    if style not in ("趨勢續抱型", "穩健保利型"):
        raise ValueError("未知的持股策略")
    bullish = macd_dif > macd_signal
    if not holding:
        if close > ma20 and close > ma60 and bullish:
            return Decision("買進觀察", "價格高於 MA20、MA60 且 MACD 偏多", "下一交易日確認可成交與風險條件", "跌回 MA20 或 MACD 轉弱", True)
        return Decision("觀望", "技術進場條件尚未全部符合", "站上 MA20、MA60 且 MACD 偏多", "均線與動能持續轉弱", False)
    support = ma60 if style == "趨勢續抱型" else ma20
    label = "MA60" if style == "趨勢續抱型" else "MA20"
    if close < support and not bullish:
        return Decision("賣出觀察", f"跌破 {label} 且 MACD 偏弱", "下一交易日依交易計畫出場", f"重新站回 {label} 且 MACD 轉強", False)
    if close >= support:
        return Decision("續抱", f"收盤價仍位於 {label} 之上", f"維持在 {label} 之上", f"跌破 {label} 且 MACD 轉弱", True)
    return Decision("觀察", f"跌破 {label}，但 MACD 尚未同步轉弱", f"觀察能否重新站回 {label}", "MACD 轉弱", True)


def add_indicators(prices):
    """傳回僅使用當下及過去價格的技術指標；不讀取未來資料。"""
    frame = pd.DataFrame(index=prices.index)
    frame["Close"] = pd.to_numeric(prices["Close"], errors="coerce")
    frame["MA20"] = frame["Close"].rolling(20, min_periods=20).mean()
    frame["MA60"] = frame["Close"].rolling(60, min_periods=60).mean()
    ema12 = frame["Close"].ewm(span=12, adjust=False).mean()
    ema26 = frame["Close"].ewm(span=26, adjust=False).mean()
    frame["DIF"] = ema12 - ema26
    frame["DEA"] = frame["DIF"].ewm(span=9, adjust=False).mean()
    return frame


def evaluate_latest(prices, holding=False, style="趨勢續抱型"):
    row = add_indicators(prices).iloc[-1]
    return evaluate(row["Close"], row["MA20"], row["MA60"], row["DIF"], row["DEA"], holding, style)
