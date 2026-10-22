"""V3 技術指標計算模組：只計算指標，不改動圖表或交易決策規則。"""

import pandas as pd


def calculate_technicals(data):
    """沿用 V3 原本 MA、RSI、MACD 與 20 日均量計算方法。"""
    close = data["Close"]
    chart_data = pd.DataFrame({"收盤價": close})

    for days in [5, 10, 20, 60]:
        chart_data[f"MA{days}"] = close.rolling(window=days).mean()

    # RSI 14 日，保留原程式 Wilder 平滑及特殊情況處理。
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50)

    # MACD (12, 26, 9)。
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    histogram = dif - dea
    macd_data = pd.DataFrame({"DIF": dif, "訊號線": dea, "柱狀差值": histogram})

    avg_volume20 = data["Volume"].rolling(20).mean().iloc[-1]

    return {
        "close": close,
        "chart_data": chart_data,
        "rsi": rsi,
        "dif": dif,
        "dea": dea,
        "histogram": histogram,
        "macd_data": macd_data,
        "avg_volume20": avg_volume20,
    }
