import streamlit as st
import yfinance as yf
import pandas as pd
@st.cache_data(ttl=900, show_spinner=False)
def get_stock_history(symbol, period):
    return yf.Ticker(symbol).history(period=period)
st.set_page_config(page_title="台股AI趨勢研究室", layout="wide")

st.title("📈 台股AI趨勢研究室")
st.write("第三版：股價、均線、RSI、MACD與成交量分析")
st.subheader("交易分析模式")
mode = st.radio(
    "請選擇目前的持股狀態",
    ["持股模式", "空手模式"],
    horizontal=True
)

if mode == "持股模式":
    holding_cost = st.number_input(
        "請輸入每股持有成本（元）",
        min_value=0.0,
        value=0.0,
        step=1.0
    )
    holding_shares = st.number_input(
        "請輸入持有股數（股）",
        min_value=0,
        value=0,
        step=100
    )
else:
    holding_cost = None
    holding_shares = 0
stock = st.text_input("請輸入股票代號", "3491")
period = st.selectbox(
    "查詢期間", ["1mo", "3mo", "6mo", "1y", "2y"], index=3
)

if st.button("查詢股價"):
    st.session_state["stock_queried"] = True

if st.session_state.get("stock_queried", False):
    stock = stock.strip()

    if not stock.isdigit():
        st.error("請輸入台股數字代號，例如 3491")
    else:
        with st.spinner("正在取得股價資料..."):
            data = None
            matched_symbol = None
            errors = []

            for suffix in [".TW", ".TWO"]:
                symbol = stock + suffix
                try:
                    result = get_stock_history(symbol, period)
                    if not result.empty:
                        data = result
                        matched_symbol = symbol
                        break
                except Exception as e:
                    errors.append(f"{symbol}: {e}")

        if data is None:
            st.warning("上市與上櫃市場都查不到資料，請確認股票代號或稍後重試。")
            if errors:
                with st.expander("查看查詢錯誤"):
                    st.write("\n".join(errors))
        else:
            st.success(f"查詢成功！資料代碼：{matched_symbol}")

            close = data["Close"]
            chart_data = pd.DataFrame({"收盤價": close})

            # 四條移動平均線
            for days in [5, 10, 20, 60]:
                chart_data[f"MA{days}"] = close.rolling(
                    window=days
                ).mean()

            st.subheader(f"{stock} 股價與均線走勢")
            st.line_chart(chart_data[["收盤價", "MA20", "MA60"]])

            st.metric(
                "最新一筆收盤價",
                f"{close.iloc[-1]:.2f} 元"
            )
            st.caption(
                f"最新資料日期：{data.index[-1].strftime('%Y-%m-%d')}"
            )

            st.subheader("最新均線數值")
            for days in [20, 60]:
                ma = chart_data[f"MA{days}"].iloc[-1]
                if pd.notna(ma):
                    st.write(f"MA{days}：{ma:.2f} 元")
                else:
                    st.write(f"MA{days}：資料不足")

            # RSI 14日，使用Wilder平滑法
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)

            avg_gain = gain.ewm(
                alpha=1/14, adjust=False, min_periods=14
            ).mean()
            avg_loss = loss.ewm(
                alpha=1/14, adjust=False, min_periods=14
            ).mean()

            rs = avg_gain / avg_loss.replace(0, float("nan"))
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
            rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)
            rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50)

            st.subheader("RSI（14日）相對強弱指標")
            st.line_chart(rsi.rename("RSI"))
            latest_rsi = rsi.iloc[-1]

            if pd.notna(latest_rsi):
                st.metric("最新 RSI", f"{latest_rsi:.2f}")
                if latest_rsi >= 70:
                    st.write("RSI 位於70以上：動能偏強，留意過熱風險。")
                elif latest_rsi <= 30:
                    st.write("RSI 位於30以下：動能偏弱，留意超賣情況。")
                else:
                    st.write("RSI 位於30至70之間。")
            else:
                st.write("RSI 資料不足。")

            # MACD（12、26、9）
            ema12 = close.ewm(
                span=12, adjust=False
            ).mean()
            ema26 = close.ewm(
                span=26, adjust=False
            ).mean()

            dif = ema12 - ema26
            dea = dif.ewm(
                span=9, adjust=False
            ).mean()
            histogram = dif - dea

            macd_data = pd.DataFrame({
                "DIF": dif,
                "訊號線": dea,
                "柱狀差值": histogram
            })

            st.subheader("MACD 趨勢動能")
            st.line_chart(macd_data)

            st.write(f"最新 DIF：{dif.iloc[-1]:.2f}")
            st.write(f"最新訊號線：{dea.iloc[-1]:.2f}")
            st.write(
                f"最新柱狀差值：{histogram.iloc[-1]:.2f}"
            )

            # 成交量
            st.subheader("每日成交量")
            st.bar_chart(data["Volume"])

            st.caption(
                "技術指標僅供研究參考，不構成投資建議。"
                "短期資料可能不足，指標也不保證預測未來走勢。"
            )

            # 技術面自動分析報告
            st.subheader("📋 技術面自動分析報告")

            latest_close = close.iloc[-1]
            latest_ma20 = chart_data["MA20"].iloc[-1]
            latest_ma60 = chart_data["MA60"].iloc[-1]

            if pd.notna(latest_ma20) and pd.notna(latest_ma60):
                if latest_close > latest_ma20 and latest_close > latest_ma60:
                    st.write("【均線】股價位於20日與60日均線之上，價格結構相對偏強。")
                elif latest_close < latest_ma20 and latest_close < latest_ma60:
                    st.write("【均線】股價位於20日與60日均線之下，價格結構相對偏弱。")
                else:
                    st.write("【均線】股價未同時站上或跌破20日與60日均線，短中期訊號尚未一致，需觀察後續走勢。")
            else:
                st.write("【均線】歷史資料不足，暫不判斷。")

            if pd.notna(latest_rsi):
                if latest_rsi >= 70:
                    st.write("【RSI】動能偏強，但需留意過熱風險。")
                elif latest_rsi <= 30:
                    st.write("【RSI】動能偏弱，可能出現超賣狀態。")
                else:
                    st.write("【RSI】位於30至70之間，未達常用超買或超賣門檻。")
            else:
                st.write("【RSI】資料不足，暫不判斷。")

            if dif.iloc[-1] > dea.iloc[-1]:
                st.write("【MACD】DIF高於訊號線，動能相對偏多。")
            elif dif.iloc[-1] < dea.iloc[-1]:
                st.write("【MACD】DIF低於訊號線，動能相對偏空。")
            else:
                st.write("【MACD】DIF與訊號線接近重合。")

            volume = data["Volume"]
            avg_volume20 = volume.rolling(20).mean().iloc[-1]

            if pd.notna(avg_volume20) and avg_volume20 > 0:
                volume_ratio = volume.iloc[-1] / avg_volume20
                st.write(f"【成交量】最新成交量為20日均量的 {volume_ratio:.2f} 倍。")
                if volume_ratio >= 1.5:
                    st.write("成交量明顯放大，需配合股價方向判斷。")
                elif volume_ratio < 0.7:
                    st.write("成交量相對萎縮，市場交易活躍度較低。")
                else:
                    st.write("成交量接近近期平均水準。")
            else:
                st.write("【成交量】資料不足，暫不判斷。")

            st.info("以上為規則式技術分析，並非AI預測或買賣建議。")

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
                        "股價站上MA20與MA60，且MACD動能偏強。",
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

            from decimal import Decimal, ROUND_FLOOR

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
