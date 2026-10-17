import streamlit as st
import yfinance as yf

st.set_page_config(page_title="台股AI趨勢研究室", layout="wide")

st.title("📈 台股AI趨勢研究室")
st.write("第一版：台股歷史股價與趨勢觀察")

stock = st.text_input("請輸入股票代號", "3491")
period = st.selectbox("查詢期間", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)

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
                st.warning("上市與上櫃市場都查不到股價資料，請確認股票代號，或稍後重試。")
                if errors:
                    with st.expander("查看查詢錯誤"):
                        st.write("\n".join(errors))
            else:
                st.success(f"查詢成功！資料代碼：{matched_symbol}")
                st.subheader(f"{stock} 歷史收盤價")
                st.line_chart(data["Close"])
                st.metric("最新一筆收盤價", f"{data['Close'].iloc[-1]:.2f} 元")
                st.caption("資料可能延遲，僅供研究，不構成投資建議。")
