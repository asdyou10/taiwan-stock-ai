import streamlit as st
import pandas as pd
from data_sources import get_stock_history, get_company_info
from fundamental import render_revenue_analysis
from strategy import render_strategy_analysis
from technicals import calculate_technicals
from risk import render_risk_analysis
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
            # V3 基本面資料讀取測試
            with st.expander("📋 V3 基本面資料測試"):
                try:
                    info = get_company_info(matched_symbol)
                    st.write("公司名稱：", info.get("longName", "無資料"))
                    st.write("產業：", info.get("industry", "無資料"))
                    st.write("本益比：", info.get("trailingPE", "無資料"))
                    st.write("市值：", info.get("marketCap", "無資料"))
                except Exception as e:
                    st.warning(f"基本面資料讀取失敗：{e}")
            
            render_revenue_analysis(stock)
            # 統一從技術指標模組取得數值，保留原本圖表與交易規則。
            technicals = calculate_technicals(data)
            close = technicals["close"]
            chart_data = technicals["chart_data"]
            rsi = technicals["rsi"]
            dif = technicals["dif"]
            dea = technicals["dea"]
            histogram = technicals["histogram"]
            macd_data = technicals["macd_data"]
            avg_volume20 = technicals["avg_volume20"]

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

            render_strategy_analysis(
                mode, holding_cost, holding_shares, chart_data, close, dif, dea
            )

            render_risk_analysis(latest_close)
