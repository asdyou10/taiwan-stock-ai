"""V3 交易決策模組：保留既有持股／空手及兩種策略的判斷與顯示。"""

import streamlit as st
import pandas as pd


def render_strategy_analysis(mode, holding_cost, holding_shares, chart_data, close, dif, dea):
    """呈現雙模式分析與最終決策；不修改原有決策門檻。"""
    # 持股與空手雙模式分析
    st.subheader("📊 V3 雙模式技術決策")

    ma20 = chart_data["MA20"].iloc[-1]
    ma60 = chart_data["MA60"].iloc[-1]
    macd_bullish = dif.iloc[-1] > dea.iloc[-1]

    trend_ready = pd.notna(ma20) and pd.notna(ma60)

    if mode == "持股模式":
        st.write("### 持股者分析")
        strategy = st.radio(
            "請選擇持股策略",
            ["趨勢續抱型", "穩健保利型"],
            horizontal=True
        )
        if not trend_ready:
            st.info("均線資料不足，暫時無法判斷持股策略。")
        elif strategy == "趨勢續抱型":
            if latest_close >= ma60:
                st.info("【趨勢續抱】股價仍在 MA60 之上，長期趨勢尚未出現此項轉弱訊號。")
            else:
                st.warning("【趨勢續抱】股價跌破 MA60，應檢查價格結構及長期趨勢。")
        else:
            if latest_close >= ma20:
                st.info("【穩健保利】股價仍在 MA20 之上，持續觀察短期趨勢。")
            else:
                st.warning("【穩健保利】股價跌破 MA20，應提高獲利回吐風險警覺。")

        if holding_cost > 0:
            return_pct = (
                (latest_close - holding_cost)
                / holding_cost * 100
            )
            st.metric(
                "未實現報酬率（未扣交易成本）",
                f"{return_pct:+.2f}%"
            )
            if holding_shares > 0:
                total_cost = holding_cost * holding_shares
                market_value = latest_close * holding_shares
                profit_loss = market_value - total_cost
                # 台股一般現股交易成本（未計券商折扣）
                fee_rate = 0.001425
                tax_rate = 0.003

                buy_fee = total_cost * fee_rate
                sell_fee = market_value * fee_rate
                sell_tax = market_value * tax_rate

                net_profit = profit_loss - buy_fee - sell_fee - sell_tax
                breakeven_price = (
                holding_cost * (1 + fee_rate)
                / (1 - fee_rate - tax_rate)
                )
                if breakeven_price < 10:
                    be_tick = 0.01
                elif breakeven_price < 50:
                    be_tick = 0.05
                elif breakeven_price < 100:
                    be_tick = 0.1
                elif breakeven_price < 500:
                    be_tick = 0.5
                elif breakeven_price < 1000:
                    be_tick = 1
                else:
                    be_tick = 5
                from decimal import Decimal, ROUND_CEILING

                adjusted_breakeven = float(
                    (Decimal(str(breakeven_price)) / Decimal(str(be_tick)))
                    .to_integral_value(rounding=ROUND_CEILING)
                    * Decimal(str(be_tick))
                )
                st.metric("持股總成本", f"{total_cost:,.0f} 元")
                st.metric("目前持股市值", f"{market_value:,.0f} 元")
                st.metric("未實現損益（未扣交易成本）", f"{profit_loss:+,.0f} 元")
                st.metric(
                "預估淨損益（扣除交易成本）",
                f"{net_profit:+,.0f} 元"
                )
                st.metric(
                "損益兩平價（未調整台股報價級距）",
                f"{adjusted_breakeven:.2f} 元"
                )
        else:
            st.warning("尚未輸入持股成本，無法計算報酬率。")

        if not trend_ready:
            st.write("均線資料不足，暫不判斷持股趨勢。")
        elif latest_close < ma20 and not macd_bullish:
            st.warning(
                "股價低於20日均線且MACD偏弱，"
                "應留意持股風險，評估減碼或出場條件。"
            )
        elif latest_close > ma20 and macd_bullish:
            st.success(
                "股價站上20日均線且MACD偏強，"
                "可持續觀察趨勢是否延續。"
            )
        else:
            st.info(
                "技術訊號分歧，建議觀察均線與MACD變化，"
                "避免只依單一指標決策。"
            )

    else:
        st.write("### 空手者分析")

        if not trend_ready:
            st.write("技術資料不足，暫不判斷進場條件。")
        elif (
            latest_close > ma20
            and latest_close > ma60
            and macd_bullish                    
        ):
            st.success(
                "股價站上MA20與MA60，且MACD動能偏強。"
                "可列入觀察名單，但仍須規劃進場價與停損。"
            )
        elif latest_close < ma20 and not macd_bullish:
            st.warning(
                "股價低於20日均線且MACD偏弱，"
                "目前宜等待更明確的轉強訊號。"
            )
        else:
            st.info(
                "技術訊號尚未一致，"
                "可等待均線與動能進一步確認。"
            )

    # V3 最終極簡決策（依交易模式與策略判斷）
    st.subheader("🎯 V3 最終極簡決策")

    if not trend_ready:
        st.info("決策：資料不足")
        st.write("原因：MA20 或 MA60 資料不足，暫時無法判斷。")
        st.write("觸發條件：取得足夠的均線資料。")
        st.write("失效條件：無。")

    elif mode == "持股模式":

        if strategy == "趨勢續抱型":

            if latest_close < ma60 and not macd_bullish:
                st.warning("決策：減碼觀察")
                st.write("原因：股價跌破 MA60，且 MACD 動能偏弱，長期趨勢出現風險。")
                st.write("觸發條件：確認跌破 MA60 並持續走弱。")
                st.write("失效條件：重新站回 MA60 且 MACD 轉強。")

            elif latest_close >= ma60:
                st.success("決策：續抱")
                st.write("原因：股價仍在 MA60 之上，長期趨勢尚未破壞。")
                st.write("觸發條件：維持在 MA60 之上。")
                st.write("失效條件：確認跌破 MA60。")

            else:
                st.info("決策：觀察")
                st.write("原因：股價低於 MA60，但 MACD 尚未同步轉弱。")
                st.write("觸發條件：觀察能否重新站回 MA60。")
                st.write("失效條件：MACD 轉弱且股價持續低於 MA60。")

        else:
            # 穩健保利型
            if latest_close < ma20 and not macd_bullish:
                st.warning("決策：減碼觀察")
                st.write("原因：股價跌破 MA20，且 MACD 動能偏弱，短中期風險升高。")
                st.write("觸發條件：確認跌破 MA20 並持續走弱。")
                st.write("失效條件：重新站回 MA20 且 MACD 轉強。")

            elif latest_close >= ma20:
                st.success("決策：續抱")
                st.write("原因：股價仍在 MA20 之上，短中期趨勢尚未破壞。")
                st.write("觸發條件：維持在 MA20 之上。")
                st.write("失效條件：確認跌破 MA20。")

            else:
                st.info("決策：觀察")
                st.write("原因：股價低於 MA20，但 MACD 尚未同步轉弱。")
                st.write("觸發條件：觀察能否重新站回 MA20。")
                st.write("失效條件：MACD 轉弱且股價持續低於 MA20。")

    else:
        # 空手模式
        if latest_close > ma20 and latest_close > ma60 and macd_bullish:
            st.success("決策：買進觀察")
            st.write("原因：股價站上 MA20、MA60，且 MACD 動能偏強。")
            st.write("觸發條件：確認突破並符合風險報酬條件。")
            st.write("失效條件：跌回關鍵均線下方。")

        else:
            st.info("決策：觀望")
            st.write("原因：目前技術條件尚未全部符合。")
            st.write("觸發條件：股價站上 MA20、MA60 且 MACD 轉強。")
            st.write("失效條件：技術條件持續惡化。")

    st.caption("目前僅依技術面判斷，尚未整合基本面、估值與產業分析。")

    st.caption(
        "此為規則式技術分析，尚未整合基本面8題。"
        "不構成個人化投資建議。"
    )

