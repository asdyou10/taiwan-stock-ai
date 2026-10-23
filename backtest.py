"""V3 第六階段：獨立 MA20/MA60 歷史回測原型。

與目前 app.py / strategy.py 完全分離，不宣稱重現 V3 完整策略。
執行：streamlit run backtest.py
"""

import math
import pandas as pd
import streamlit as st
import yfinance as yf

COMMISSION_RATE = 0.001425  # 台股券商牌告費率；實際折扣依券商而異
MIN_COMMISSION = 20.0      # 以一般整股交易常見最低手續費假設
SELL_TAX_RATE = 0.003      # 一般股票賣出證交稅；不適用所有商品／特殊情況


def commission(gross):
    return max(MIN_COMMISSION, gross * COMMISSION_RATE) if gross > 0 else 0.0


def affordable_shares(cash, price):
    """以整股股數模擬，不考慮槓桿與融資；此版本未模擬零股成交機制。"""
    if price <= 0 or cash <= MIN_COMMISSION:
        return 0
    n = int((cash - MIN_COMMISSION) / (price * (1 + COMMISSION_RATE)))
    while n > 0 and n * price + commission(n * price) > cash + 1e-8:
        n -= 1
    return max(0, n)


def simulate(data, initial_cash=1_000_000.0, strategy="ma"):
    """訊號在前一交易日收盤形成，下一交易日開盤成交，避免同日收盤價偷看。"""
    if data is None or len(data) < 62:
        raise ValueError("歷史資料不足，至少需要 62 個交易日。")
    df = data[["Open", "Close"]].copy().dropna()
    df = df[(df["Open"] > 0) & (df["Close"] > 0)].copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    if len(df) < 62:
        raise ValueError("有效股價資料不足，無法回測。")

    cash = float(initial_cash)
    shares = 0
    entries = []
    history = []
    flat_periods = []
    flat_start = None
    fee_total = 0.0
    tax_total = 0.0
    completed = []
    open_trade = None
    first_trade_index = 60
    for i in range(first_trade_index, len(df)):
        today = df.iloc[i]
        yesterday = df.iloc[i - 1]
        date = df.index[i]
        op = float(today["Open"])
        close = float(today["Close"])
        if strategy == "ma":
            desired_holding = bool(yesterday["MA20"] > yesterday["MA60"])
        else:
            desired_holding = True

        if desired_holding and shares == 0:
            quantity = affordable_shares(cash, op)
            if quantity:
                gross = quantity * op
                fee = commission(gross)
                cash -= gross + fee
                fee_total += fee
                if flat_start is not None:
                    flat_periods.append({"賣出後空手起日": flat_start["date"], "重新買進日": date.strftime("%Y-%m-%d"), "賣出價": flat_start["price"], "重新買進價": op, "空手期間價格變動率": op / flat_start["price"] - 1, "交易日數": i - flat_start["index"], "期末仍空手": False})
                    flat_start = None
                shares = quantity
                open_trade = {"買進日": date.strftime("%Y-%m-%d"), "買進價": op,
                              "股數": quantity, "買進總成本": gross + fee}
                entries.append({"日期": date.strftime("%Y-%m-%d"), "動作": "買進", "價格": op,
                                "股數": quantity, "手續費": fee, "證交稅": 0.0})
        elif not desired_holding and shares > 0:
            gross = shares * op
            fee = commission(gross)
            tax = gross * SELL_TAX_RATE
            cash += gross - fee - tax
            fee_total += fee
            tax_total += tax
            flat_start = {"date": date.strftime("%Y-%m-%d"), "price": op, "index": i}
            entries.append({"日期": date.strftime("%Y-%m-%d"), "動作": "賣出", "價格": op,
                            "股數": shares, "手續費": fee, "證交稅": tax})
            if open_trade is not None:
                completed.append({**open_trade, "賣出日": date.strftime("%Y-%m-%d"),
                                  "賣出價": op, "已實現損益": gross - fee - tax - open_trade["買進總成本"]})
            shares = 0
            open_trade = None
        history.append({"日期": date, "資產淨值": cash + shares * close})

    if flat_start is not None:
        last_close = float(df.iloc[-1]["Close"])
        flat_periods.append({"賣出後空手起日": flat_start["date"], "重新買進日": "尚未買回", "賣出價": flat_start["price"], "重新買進價": last_close, "空手期間價格變動率": last_close / flat_start["price"] - 1, "交易日數": len(df) - 1 - flat_start["index"], "期末仍空手": True})
    curve = pd.DataFrame(history).set_index("日期")["資產淨值"]
    total_return = curve.iloc[-1] / initial_cash - 1
    max_drawdown = (curve / pd.concat([pd.Series([initial_cash]), curve], ignore_index=True).cummax().iloc[1:].to_numpy() - 1).min()
    wins = sum(x["已實現損益"] > 0 for x in completed)
    win_rate = wins / len(completed) if completed else None
    return {"curve": curve, "return": total_return, "max_drawdown": max_drawdown,
            "completed": completed, "trades": entries, "win_rate": win_rate,
            "shares_at_end": shares, "final_equity": curve.iloc[-1],
            "flat_periods": flat_periods, "fee_total": fee_total, "tax_total": tax_total}


@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(stock, years):
    # auto_adjust=False 保留未調整 OHLC，避免股利調整價格與實際交易現金流混用。
    period = f"{years}y"
    for suffix in (".TW", ".TWO"):
        symbol = stock + suffix
        try:
            df = yf.Ticker(symbol).history(period=period, auto_adjust=False, actions=False)
            if not df.empty:
                return symbol, df
        except Exception:
            pass
    raise ValueError("查不到歷史股價。請檢查股票代號或稍後再試。")


st.set_page_config(page_title="V3 歷史回測（獨立測試版）", layout="wide")
st.title("📊 V3 歷史回測｜第六階段獨立原型")
st.info("此版本只比較 MA20／MA60 趨勢規則與買進持有，不代表完整 V3 策略回測。現有 APP 不受影響。")
with st.form("backtest_inputs"):
    stock = st.text_input("台股代號", value="3491").strip()
    years = st.selectbox("歷史期間", ["1", "2", "5", "10"], index=2)
    capital = st.number_input("初始資金（新台幣）", min_value=10000, value=1000000, step=100000)
    submitted = st.form_submit_button("開始回測")

if submitted:
    if not stock.isdigit():
        st.error("請輸入數字股票代號，例如 3491。")
    else:
        try:
            with st.spinner("取得資料並計算回測中..."):
                symbol, prices = load_prices(stock, years)
                trend = simulate(prices, capital, "ma")
                hold = simulate(prices, capital, "hold")
            st.success(f"回測完成：{symbol}｜{len(trend['curve'])} 個交易日（已排除均線暖機期間）")
            comparison = pd.DataFrame({
                "MA20/MA60 趨勢策略": trend["curve"],
                "買進持有": hold["curve"],
            })
            st.line_chart(comparison)
            st.dataframe(pd.DataFrame([
                {"策略": "MA20/MA60 趨勢", "總報酬率": f"{trend['return']:.2%}",
                 "最大回撤": f"{trend['max_drawdown']:.2%}", "已完成交易筆數": len(trend["completed"]),
                 "已完成交易勝率": "無已完成交易" if trend["win_rate"] is None else f"{trend['win_rate']:.2%}",
                 "期末資產（元）": round(trend["final_equity"], 0)},
                {"策略": "買進持有", "總報酬率": f"{hold['return']:.2%}",
                 "最大回撤": f"{hold['max_drawdown']:.2%}", "已完成交易筆數": len(hold["completed"]),
                 "已完成交易勝率": "無已完成交易" if hold["win_rate"] is None else f"{hold['win_rate']:.2%}",
                 "期末資產（元）": round(hold["final_equity"], 0)},
            ]), hide_index=True, use_container_width=True)
            st.caption("未平倉部位以最後收盤價評價，尚未扣除假設當天清倉的賣出費用與證交稅。")
            with st.expander("檢視趨勢策略交易紀錄"):
                if trend["trades"]:
                    st.dataframe(pd.DataFrame(trend["trades"]), hide_index=True, use_container_width=True)
                else:
                    st.write("期間內沒有成交交易。")
            st.subheader("🔎 策略落後原因診斷")
            st.caption("空手期間漲跌幅採賣出日開盤價至下一次買進日開盤價；期末尚未買回則採最後收盤價。這是價格機會成本指標，不等於可直接累加的實際損益。")
            gap = hold["final_equity"] - trend["final_equity"]
            c1, c2, c3 = st.columns(3)
            c1.metric("與買進持有期末資產差額", f"{gap:,.0f} 元", help="正數表示趨勢策略期末資產較少；負數表示趨勢策略較多")
            c2.metric("趨勢策略累計手續費", f"{trend['fee_total']:,.0f} 元")
            c3.metric("趨勢策略累計證交稅", f"{trend['tax_total']:,.0f} 元")
            st.caption(f"趨勢策略交易總成本：{trend['fee_total'] + trend['tax_total']:,.0f} 元；買進持有交易總成本：{hold['fee_total'] + hold['tax_total']:,.0f} 元。總成本已包含在期末資產內，不能再從績效扣除一次。")
            if trend["completed"]:
                detail = pd.DataFrame(trend["completed"]).copy()
                detail["報酬率（含交易成本）"] = detail["已實現損益"] / detail["買進總成本"]
                st.markdown("**已完成交易損益（含手續費與證交稅）**")
                st.dataframe(detail.assign(**{"報酬率（含交易成本）": detail["報酬率（含交易成本）"].map(lambda x: f"{x:.2%}")}), hide_index=True, use_container_width=True)
                st.caption(f"已完成交易合計已實現損益：{detail['已實現損益'].sum():,.0f} 元；不含期末尚未賣出的部位。")
            else:
                st.info("此期間沒有已完成的趨勢策略交易。")
            if trend["flat_periods"]:
                periods = pd.DataFrame(trend["flat_periods"])
                positive = periods[periods["空手期間價格變動率"] > 0]
                st.markdown("**賣出後空手期間的價格變化**")
                st.dataframe(periods.assign(**{"空手期間價格變動率": periods["空手期間價格變動率"].map(lambda x: f"{x:+.2%}")}), hide_index=True, use_container_width=True)
                st.caption(f"共 {len(periods)} 段賣出後空手期間，其中 {len(positive)} 段股價上漲。正報酬代表該段空手可能錯過上漲；負報酬代表該段空手可能避開下跌。不能直接把各段百分比相加當作策略損失。")
            else:
                st.info("此期間沒有賣出後的空手區間。")
            st.warning("回測限制：使用前日收盤訊號、次日開盤成交；假設可按開盤價成交、無滑價，按整股股數計算但未模擬零股撮合；買賣手續費 0.1425%（每筆最低 20 元），一般股票賣出稅 0.3%；未計股利、除權息現金流、融資、停牌與下市樣本，亦未納入完整 V3 基本面、持股成本或停損策略。此結果不適合作為直接買賣依據。")
        except Exception as exc:
            st.error(f"回測失敗：{exc}")
