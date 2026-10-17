import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="台股AI趨勢研究室", layout="wide")

st.title("📈 台股AI趨勢研究室")
st.write("第三版：股價、均線、RSI、MACD與成交量分析")

stock = st.text_input("請輸入股票代號", "3491")
period = st.selectbox(
    "查詢期間", ["1mo", "3mo", "6mo", "1y", "2y"], index=3
)

if st.button("查詢股價"):
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
                    result = yf.Ticker(symbol).history(period=period)
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
            st.line_chart(chart_data)

            st.metric(
                "最新一筆收盤價",
                f"{close.iloc[-1]:.2f} 元"
            )
            st.caption(
                f"最新資料日期：{data.index[-1].strftime('%Y-%m-%d')}"
            )

            st.subheader("最新均線數值")
            for days in [5, 10, 20, 60]:
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
