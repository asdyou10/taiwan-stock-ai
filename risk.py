"""V3 風險控管：維持既有參考跌幅及台股價格級距試算。"""

import streamlit as st
from decimal import Decimal, ROUND_FLOOR


def render_risk_analysis(latest_close):
    """顯示原有風險試算；latest_close 由主程式明確傳入。"""
    # V3 風險控管
    st.subheader("🛡️ V3 風險控管")

    risk_pct = st.slider(
        "可承受的參考跌幅（%）",
        min_value=1,
        max_value=20,
        value=8,
        step=1
    )

    reference_price = latest_close
    stop_price = reference_price * (1 - risk_pct / 100)

    # 台股一般股票最小升降單位
    if stop_price < 10:
        tick = 0.01
    elif stop_price < 50:
        tick = 0.05
    elif stop_price < 100:
        tick = 0.1
    elif stop_price < 500:
        tick = 0.5
    elif stop_price < 1000:
        tick = 1
    else:
        tick = 5

    adjusted_stop = float(
        (Decimal(str(stop_price)) / Decimal(str(tick)))
        .to_integral_value(rounding=ROUND_FLOOR)
        * Decimal(str(tick))
    )

    st.metric(
        "理論停損價",
        f"{stop_price:.2f} 元"
    )

    st.metric(
        "符合台股報價級距的參考價",
        f"{adjusted_stop:.2f} 元"
    )

    st.caption(
        f"以最新收盤價 {reference_price:.2f} 元為基準，"
        f"下跌 {risk_pct}% 計算。"
        "此為情境試算，非技術支撐位或實際停損建議。"
    )
