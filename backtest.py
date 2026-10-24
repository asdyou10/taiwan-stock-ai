"""V3 第六階段 V5：未調整成交價與公司行動事件版。

與目前 app.py / strategy.py 完全分離，不宣稱重現 V3 完整策略。
執行：streamlit run backtest.py
"""

import math
from datetime import date, timedelta
import pandas as pd
import streamlit as st
import yfinance as yf
from decision_engine import add_indicators, evaluate

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


def simulate(data, initial_cash=1_000_000.0, strategy="ma", start_date=None, slippage_bps=0.0,
             max_position_pct=1.0, risk_per_trade_pct=None, stop_buffer_pct=0.0):
    """訊號在前一交易日收盤形成，下一交易日開盤成交，避免同日收盤價偷看。"""
    if not 0 < max_position_pct <= 1:
        raise ValueError("單檔投入比例須介於 0%（不含）與 100%。")
    if risk_per_trade_pct is not None and not 0 < risk_per_trade_pct <= 0.1:
        raise ValueError("每筆風險預算須介於 0%（不含）與 10%。")
    if not 0 <= stop_buffer_pct <= 0.2:
        raise ValueError("停損緩衝須介於 0% 至 20%。")
    if not 0 <= slippage_bps <= 500:
        raise ValueError("滑價必須介於 0 至 500 bps。")
    if data is None or len(data) < 62:
        raise ValueError("歷史資料不足，至少需要 62 個交易日。")
    df = data[["Open", "Close", "Adj Close", "Dividends", "Stock Splits"]].copy()
    df = df.dropna(subset=["Open", "Close", "Adj Close"])
    df[["Dividends", "Stock Splits"]] = df[["Dividends", "Stock Splits"]].fillna(0.0)
    df = df[(df["Open"] > 0) & (df["Close"] > 0)].copy()
    # 訊號使用調整後收盤價，避免除權息造成虛假均線跌破；實際交易使用原始開盤價。
    df["MA20"] = df["Adj Close"].rolling(20).mean()
    df["MA60"] = df["Adj Close"].rolling(60).mean()
    if len(df) < 62:
        raise ValueError("有效股價資料不足，無法回測。")
    # V4 專用訊號與 APP 共用同一計算函式；舊 MA 策略不受影響。
    v4_indicators = add_indicators(df) if strategy.startswith("v4_") else None

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
    dividends_total = 0.0
    splits_seen = []
    action_events = []
    sizing_events = []
    first_trade_index = 60
    if start_date is not None:
        valid = df.index >= pd.Timestamp(start_date).tz_localize(df.index.tz) if df.index.tz is not None else df.index >= pd.Timestamp(start_date)
        candidates = [i for i in range(60, len(df)) if valid[i]]
        if not candidates:
            raise ValueError("指定區間內沒有足夠的有效交易日。")
        first_trade_index = candidates[0]
    for i in range(first_trade_index, len(df)):
        today = df.iloc[i]
        yesterday = df.iloc[i - 1]
        date = df.index[i]
        op = float(today["Open"])
        close = float(today["Close"])
        # 除權息生效日開盤前，先依「前一交易日已持有」股數處理公司行動。
        # 現金股利以除息日認列並視同可用現金，是近似值；實際入帳日在後。
        split_ratio = float(today["Stock Splits"])
        if split_ratio > 0:
            before = shares
            shares = shares * split_ratio
            if open_trade is not None:
                open_trade["股數"] = shares
                open_trade["買進價"] = open_trade["買進總成本"] / shares if shares else 0
            splits_seen.append(date.strftime("%Y-%m-%d"))
            action_events.append({"日期": date.strftime("%Y-%m-%d"), "類型": "股票分割/合併", "每股數量變動倍數": split_ratio, "現金入帳": 0.0, "處理前股數": before})
        dividend = float(today["Dividends"])
        dividend_cash = shares * dividend if dividend > 0 else 0.0
        if dividend_cash:
            cash += dividend_cash
            dividends_total += dividend_cash
            action_events.append({"日期": date.strftime("%Y-%m-%d"), "類型": "現金股利（除息日近似認列）", "每股數量變動倍數": 1.0, "現金入帳": dividend_cash, "處理前股數": shares})
            if open_trade is not None:
                open_trade["累計股利"] += dividend_cash
        if strategy == "ma":
            desired_holding = bool(yesterday["MA20"] > yesterday["MA60"])
        elif strategy.startswith("v4_"):
            style = "穩健保利型" if strategy == "v4_conservative" else "趨勢續抱型"
            signal = v4_indicators.iloc[i - 1]
            decision = evaluate(signal["Close"], signal["MA20"], signal["MA60"],
                                signal["DIF"], signal["DEA"], holding=shares > 0, style=style)
            # 觀察／續抱保持原倉；只有明確賣出觀察才全數出場。
            desired_holding = (decision.action == "買進觀察") if shares == 0 else (decision.action != "賣出觀察")
        else:
            desired_holding = True

        if desired_holding and shares == 0:
            execution_price = op * (1 + slippage_bps / 10000)
            quantity = affordable_shares(cash, execution_price)
            if strategy.startswith("v4_") and risk_per_trade_pct is not None:
                # 用前日可見的均線估計停損參考價；不使用當日收盤資訊。
                support_col = "MA20" if strategy == "v4_conservative" else "MA60"
                support = float(v4_indicators.iloc[i - 1][support_col])
                stop_reference = support * (1 - stop_buffer_pct)
                per_share_risk = execution_price - stop_reference
                equity_before = cash
                max_notional = equity_before * max_position_pct
                by_allocation = affordable_shares(min(cash, max_notional), execution_price)
                # 風險距離無效時禁止進場，不以零距離計算無限部位。
                by_risk = int(equity_before * risk_per_trade_pct / per_share_risk) if per_share_risk > 0 and math.isfinite(per_share_risk) else 0
                quantity = min(quantity, by_allocation, by_risk)
                sizing_events.append({"日期": date.strftime("%Y-%m-%d"), "前日支撐均線": support,
                                      "參考停損價": stop_reference, "預估每股風險": per_share_risk,
                                      "單檔上限股數": by_allocation, "風險預算股數": by_risk,
                                      "實際買進股數": quantity, "因限制未進場": quantity == 0})
            if quantity:
                gross = quantity * execution_price
                fee = commission(gross)
                cash -= gross + fee
                fee_total += fee
                if flat_start is not None:
                    flat_periods.append({"賣出後空手起日": flat_start["date"], "重新買進日": date.strftime("%Y-%m-%d"), "賣出價": flat_start["price"], "重新買進價": execution_price, "空手期間價格變動率": execution_price / flat_start["price"] - 1, "交易日數": i - flat_start["index"], "期末仍空手": False})
                    flat_start = None
                shares = quantity
                open_trade = {"買進日": date.strftime("%Y-%m-%d"), "買進價": execution_price,
                              "股數": quantity, "買進總成本": gross + fee, "累計股利": 0.0}
                entries.append({"日期": date.strftime("%Y-%m-%d"), "動作": "買進", "價格": execution_price,
                                "股數": quantity, "手續費": fee, "證交稅": 0.0})
        elif not desired_holding and shares > 0:
            execution_price = op * (1 - slippage_bps / 10000)
            gross = shares * execution_price
            fee = commission(gross)
            tax = gross * SELL_TAX_RATE
            cash += gross - fee - tax
            fee_total += fee
            tax_total += tax
            flat_start = {"date": date.strftime("%Y-%m-%d"), "price": execution_price, "index": i}
            entries.append({"日期": date.strftime("%Y-%m-%d"), "動作": "賣出", "價格": execution_price,
                            "股數": shares, "手續費": fee, "證交稅": tax})
            if open_trade is not None:
                completed.append({**open_trade, "賣出日": date.strftime("%Y-%m-%d"),
                                  "賣出價": execution_price, "已實現損益": gross - fee - tax + open_trade["累計股利"] - open_trade["買進總成本"]})
            shares = 0
            open_trade = None
        history.append({"日期": date, "資產淨值": cash + shares * close, "持股股數": shares, "收盤價": close, "現金": cash})

    if flat_start is not None:
        last_close = float(df.iloc[-1]["Close"])
        flat_periods.append({"賣出後空手起日": flat_start["date"], "重新買進日": "尚未買回", "賣出價": flat_start["price"], "重新買進價": last_close, "空手期間價格變動率": last_close / flat_start["price"] - 1, "交易日數": len(df) - 1 - flat_start["index"], "期末仍空手": True})
    history_df = pd.DataFrame(history).set_index("日期")
    curve = history_df["資產淨值"]
    total_return = curve.iloc[-1] / initial_cash - 1
    max_drawdown = (curve / pd.concat([pd.Series([initial_cash]), curve], ignore_index=True).cummax().iloc[1:].to_numpy() - 1).min()
    wins = sum(x["已實現損益"] > 0 for x in completed)
    win_rate = wins / len(completed) if completed else None
    elapsed_days = (curve.index[-1] - curve.index[0]).total_seconds() / 86400
    annualized = (curve.iloc[-1] / initial_cash) ** (365.25 / elapsed_days) - 1 if elapsed_days > 0 and curve.iloc[-1] > 0 else None
    daily_returns = curve.pct_change().dropna()
    volatility = float(daily_returns.std(ddof=1) * math.sqrt(252)) if len(daily_returns) > 1 else None
    return {"curve": curve, "return": total_return, "max_drawdown": max_drawdown,
            "annualized_return": annualized, "annualized_volatility": volatility, "slippage_bps": slippage_bps,
            "completed": completed, "trades": entries, "win_rate": win_rate,
            "shares_at_end": shares, "final_equity": curve.iloc[-1],
            "flat_periods": flat_periods, "fee_total": fee_total, "tax_total": tax_total,
            "dividends_total": dividends_total, "action_events": action_events,
            "splits_seen": splits_seen, "daily": history_df,
            "sizing_events": sizing_events}


@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(stock, start_date, end_date):
    # 額外抓取約 150 個日曆日作為 MA60 暖機資料，避免測試期間起點缺少均線。
    fetch_start = pd.Timestamp(start_date) - pd.Timedelta(days=150)
    fetch_end = pd.Timestamp(end_date) + pd.Timedelta(days=1)  # yfinance 的 end 不包含當日
    for suffix in (".TW", ".TWO"):
        symbol = stock + suffix
        try:
            df = yf.Ticker(symbol).history(
                start=fetch_start.strftime("%Y-%m-%d"),
                end=fetch_end.strftime("%Y-%m-%d"),
                auto_adjust=False, actions=True,
            )
            if not df.empty and all(c in df.columns for c in ("Open", "Close", "Adj Close", "Dividends", "Stock Splits")):
                return symbol, df
        except Exception:
            pass
    raise ValueError("查不到歷史股價。請檢查股票代號或稍後再試。")


def daily_attribution(trend, hold, initial_cash):
    """每日兩策略淨值增量差，逐日累加精確對帳期末資產差額。"""
    frame = pd.DataFrame({"趨勢策略淨值": trend["curve"], "買進持有淨值": hold["curve"]})
    frame["趨勢每日損益"] = frame["趨勢策略淨值"].diff().fillna(frame["趨勢策略淨值"].iloc[0] - initial_cash)
    frame["持有每日損益"] = frame["買進持有淨值"].diff().fillna(frame["買進持有淨值"].iloc[0] - initial_cash)
    frame["當日績效差額變動"] = frame["持有每日損益"] - frame["趨勢每日損益"]
    frame["累積差額"] = frame["當日績效差額變動"].cumsum()
    frame["趨勢當日收盤持股"] = trend["daily"]["持股股數"]
    return frame

st.set_page_config(page_title="V3 歷史回測（獨立測試版）", layout="wide")
st.title("📊 V3 歷史回測｜第六階段 V5 交易價格與公司行動版")
st.info("此版本只比較 MA20／MA60 趨勢規則與買進持有，不代表完整 V3 策略回測。現有 APP 不受影響。")
with st.form("backtest_inputs"):
    stock = st.text_input("台股代號", value="3491").strip()
    default_end = date(2026, 10, 1)
    default_start = date(2021, 10, 1)
    start_date = st.date_input("回測起始日期（固定日期可重現比較）", value=default_start)
    end_date = st.date_input("回測結束日期（含當日）", value=default_end)
    capital = st.number_input("初始資金（新台幣）", min_value=10000, value=1000000, step=10000)
    v4_style = st.selectbox("V4 技術回測策略", ["趨勢續抱型", "穩健保利型"])
    slippage_bps = st.number_input("單邊滑價（bps；10 bps = 0.1%）", min_value=0.0, max_value=500.0, value=10.0, step=5.0, help="買進成交價上調、賣出成交價下調；屬情境假設，非真實成交報價。")
    st.markdown("**V4.4 資金管理情境（僅影響新增比較策略）**")
    position_pct = st.slider("單檔最大投入比例", min_value=10, max_value=100, value=30, step=5, format="%d%%")
    risk_pct = st.slider("每筆交易最大預估風險占資金比例", min_value=1, max_value=5, value=2, step=1, format="%d%%")
    stop_buffer_pct = st.slider("支撐均線下方停損參考緩衝", min_value=0, max_value=10, value=2, step=1, format="%d%%")
    submitted = st.form_submit_button("開始回測")

if submitted:
    if start_date >= end_date:
        st.error("回測起始日期必須早於結束日期。")
    elif not stock.isdigit():
        st.error("請輸入數字股票代號，例如 3491。")
    else:
        try:
            with st.spinner("取得資料並計算回測中..."):
                symbol, prices = load_prices(stock, str(start_date), str(end_date))
                trend = simulate(prices, capital, "ma", start_date=start_date, slippage_bps=slippage_bps)
                hold = simulate(prices, capital, "hold", start_date=start_date, slippage_bps=slippage_bps)
                v4_code = "v4_conservative" if v4_style == "穩健保利型" else "v4_trend"
                v4_result = simulate(prices, capital, v4_code, start_date=start_date, slippage_bps=slippage_bps)
                v44_managed = simulate(prices, capital, v4_code, start_date=start_date,
                                       slippage_bps=slippage_bps, max_position_pct=position_pct / 100,
                                       risk_per_trade_pct=risk_pct / 100,
                                       stop_buffer_pct=stop_buffer_pct / 100)
            st.success(f"回測完成：{symbol}｜{len(trend['curve'])} 個交易日｜{trend['curve'].index[0].date()} 至 {trend['curve'].index[-1].date()}")
            st.caption("固定起訖日期，並使用起始日前的歷史資料暖機 MA60；實際起訖以可取得的交易日為準。")
            st.warning("V5 用 Yahoo Finance 未調整開盤價成交、未調整收盤價估值，均線訊號使用調整後收盤價；現金股利按除息日近似入帳，股票分割按事件比例變更持股。**未涵蓋股利實際發放日、稅務、股票股利零股處置或資料商未提供的公司行動**，仍不是可直接交易的精確報酬。")
            st.subheader("🧪 V4 共用技術核心回測（研究版）")
            st.metric("V4 技術策略總報酬率", f"{v4_result['return']:.2%}")
            st.metric("V4 技術策略最大回撤", f"{v4_result['max_drawdown']:.2%}")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("年化報酬率（CAGR）", "無法計算" if v4_result["annualized_return"] is None else f'{v4_result["annualized_return"]:.2%}')
            k2.metric("已完成交易勝率", "無已完成交易" if v4_result["win_rate"] is None else f'{v4_result["win_rate"]:.2%}')
            k3.metric("已完成交易筆數", len(v4_result["completed"]))
            k4.metric("累計手續費＋交易稅", f'{v4_result["fee_total"] + v4_result["tax_total"]:,.0f} 元')
            st.caption(f'單邊滑價假設：{slippage_bps:.0f} bps；已反映於成交價和績效。年化報酬按實際回測日曆天數計算；勝率只計已平倉交易。')
            st.write(f"交易紀錄：{len(v4_result['trades'])} 筆")
            st.line_chart(pd.DataFrame({"V4 技術核心": v4_result["curve"], "買進持有": hold["curve"]}))
            with st.expander("查看 V4 交易紀錄"):
                st.dataframe(pd.DataFrame(v4_result["trades"]), use_container_width=True)
            st.warning("V4 回測只含技術面；訊號用前一交易日收盤、下一日開盤交易。尚未加入財報、估值與實際公告日過濾。")
            st.subheader("🛡️ V4.4 資金管理回測比較（研究版）")
            st.caption("與原 V4 使用相同買賣訊號；只調整每次進場的買進股數。每次重新進場均依當時資產重新計算預算。")
            st.dataframe(pd.DataFrame([
                {"策略": "原 V4（未限制部位）", "總報酬": f"{v4_result['return']:.2%}",
                 "最大回撤": f"{v4_result['max_drawdown']:.2%}", "期末資產（元）": round(v4_result['final_equity']),
                 "已完成交易": len(v4_result['completed'])},
                {"策略": "V4.4（資金管理）", "總報酬": f"{v44_managed['return']:.2%}",
                 "最大回撤": f"{v44_managed['max_drawdown']:.2%}", "期末資產（元）": round(v44_managed['final_equity']),
                 "已完成交易": len(v44_managed['completed'])},
            ]), hide_index=True, use_container_width=True)
            st.line_chart(pd.DataFrame({"原 V4": v4_result["curve"], "V4.4 資金管理": v44_managed["curve"]}))
            with st.expander("查看 V4.4 每次進場的部位計算"):
                st.dataframe(pd.DataFrame(v44_managed["sizing_events"]), hide_index=True, use_container_width=True)
            st.warning("此版的停損價僅用於進場股數估算，不是保證成交的停損單；實際出場仍沿用 V4 技術決策。跳空、跌停、流動性及公司行動資料缺漏可能使實際損失超出預估風險。尚未實作組合層級的多檔部位管理。")
            st.subheader("🏦 公司行動事件帳（資料商提供）")
            a1, a2, a3 = st.columns(3)
            a1.metric("趨勢策略累計現金股利（近似）", f"{trend['dividends_total']:,.0f} 元")
            a2.metric("買進持有累計現金股利（近似）", f"{hold['dividends_total']:,.0f} 元")
            a3.metric("歷史公司行動事件數", len(prices[(prices['Dividends'].fillna(0) != 0) | (prices['Stock Splits'].fillna(0) != 0)]))
            events = pd.DataFrame(trend['action_events'])
            with st.expander("查看趨勢策略實際持有期間的股利與拆股事件"):
                if events.empty:
                    st.info("本策略持有期間沒有記錄到公司行動；不代表資料商一定完整。")
                else:
                    st.dataframe(events, hide_index=True, use_container_width=True)
            with st.expander("查看資料商原始公司行動清單"):
                actions = prices[(prices['Dividends'].fillna(0) != 0) | (prices['Stock Splits'].fillna(0) != 0)][['Dividends','Stock Splits']]
                st.dataframe(actions, use_container_width=True)
            st.subheader("🧪 回測計算一致性稽核")
            audits = []
            for label, result in [("MA20／MA60", trend), ("買進持有", hold), ("V4 技術策略", v4_result), ("V4.4 資金管理", v44_managed)]:
                d = result["daily"]
                reconstructed = d["現金"] + d["持股股數"] * d["收盤價"]
                max_error = float((reconstructed - d["資產淨值"]).abs().max())
                returns_error = abs((result["final_equity"] / capital - 1) - result["return"])
                audits.append({"策略": label, "資產淨值對帳最大誤差（元）": max_error,
                               "報酬率公式誤差": returns_error,
                               "持股股數均非負": bool((d["持股股數"] >= 0).all()),
                               "現金餘額均非負": bool((d["現金"] >= -1e-6).all()),
                               "檢查通過": max_error < 0.01 and returns_error < 1e-10 and bool((d["持股股數"] >= 0).all()) and bool((d["現金"] >= -1e-6).all())})
            st.dataframe(pd.DataFrame(audits), hide_index=True, use_container_width=True)
            first_day = trend["curve"].index[0]
            warmup = prices.index[prices.index < first_day]
            st.caption(f"均線預熱：首次模擬交易日 {first_day.date()}；之前取得 {len(warmup)} 個歷史交易日（至少 60 日才足以形成前日 MA60 訊號）。")
            if len(warmup) < 60 or not all(x["檢查通過"] for x in audits):
                st.error("稽核未通過：請停止解讀績效，先檢查資料或計算。")
            with st.expander("檢視每日現金、持股與資產對帳（最近 30 日）"):
                audit_daily_strategy = st.selectbox(
                    "選擇稽核策略",
                    ["MA20／MA60", "買進持有", "V4 技術策略", "V4.4 資金管理"],
                    key="audit_daily_strategy",
                )
                audit_daily_results = {
                    "MA20／MA60": trend,
                    "買進持有": hold,
                    "V4 技術策略": v4_result,
                    "V4.4 資金管理": v44_managed,
                }
                st.dataframe(audit_daily_results[audit_daily_strategy]["daily"].tail(30), use_container_width=True)
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
                st.caption(f"已完成交易合計已實現損益（含持有期間股利）：{detail['已實現損益'].sum():,.0f} 元；不含期末尚未賣出的部位。")
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
            st.subheader("📌 績效歸因：差距在哪些交易日擴大？")
            attribution = daily_attribution(trend, hold, capital)
            expected_gap = hold["final_equity"] - trend["final_equity"]
            actual_gap = float(attribution["當日績效差額變動"].sum())
            st.metric("每日損益差累計（對帳）", f"{actual_gap:,.0f} 元")
            st.caption(f"與期末資產差額的對帳誤差：{actual_gap - expected_gap:+.6f} 元（應接近零）。每日差額 = 買進持有當日淨值變動 − 趨勢策略當日淨值變動，包含價格與交易成本影響。")
            st.line_chart(attribution[["累積差額"]])
            st.markdown("**讓策略相對落後最多的 10 個交易日**")
            worst = attribution.nlargest(10, "當日績效差額變動").copy()
            worst.index = worst.index.strftime("%Y-%m-%d")
            st.dataframe(worst[["當日績效差額變動", "趨勢每日損益", "持有每日損益", "趨勢當日收盤持股"]].round(0), use_container_width=True)
            st.markdown("**讓趨勢策略相對領先最多的 10 個交易日**")
            best = attribution.nsmallest(10, "當日績效差額變動").copy()
            best.index = best.index.strftime("%Y-%m-%d")
            st.dataframe(best[["當日績效差額變動", "趨勢每日損益", "持有每日損益", "趨勢當日收盤持股"]].round(0), use_container_width=True)
            st.markdown("**各月份對期末績效差額的貢獻**")
            monthly = attribution["當日績效差額變動"].groupby(attribution.index.strftime("%Y-%m")).sum().sort_values(ascending=False)
            st.dataframe(pd.DataFrame({"月份": monthly.index, "當月差額擴大金額（元）": monthly.round(0).values}), hide_index=True, use_container_width=True)
            st.caption("正值表示該期間買進持有相對占優；負值表示趨勢策略相對占優。這是逐日資產差的精確分解，不是單純把空手漲幅相加，也不等於已證明因果。")
            if trend["completed"]:
                trades_df = pd.DataFrame(trend["completed"])
                st.markdown("**最大已實現虧損交易（含交易成本）**")
                st.dataframe(trades_df.nsmallest(5, "已實現損益")[["買進日", "賣出日", "買進價", "賣出價", "股數", "已實現損益"]], hide_index=True, use_container_width=True)
            if trend["flat_periods"]:
                flat_df = pd.DataFrame(trend["flat_periods"])
                st.markdown("**空手期間股價漲幅最高的 5 段**")
                top_flat = flat_df.nlargest(5, "空手期間價格變動率").copy()
                top_flat["空手期間價格變動率"] = top_flat["空手期間價格變動率"].map(lambda x: f"{x:+.2%}")
                st.dataframe(top_flat, hide_index=True, use_container_width=True)
            st.info("此診斷顯示績效差額在何時形成；要精確拆成『進場延遲、出場過早、交易成本』的因果金額，還需要額外建立反事實策略測試，不能直接用這些數字宣稱原因已證實。")
            st.warning("回測限制：使用未調整開盤價成交、收盤價估值；現金股利於除息日近似入帳，非真實入帳日，未計股利稅、二代健保補充保費；股票分割可能產生零股，未模擬零股變現或股票股利特殊處理；Yahoo Finance 公司行動資料可能缺漏。訊號為前日收盤、次日開盤成交；已依輸入值模擬固定單邊滑價，但無漲跌停/流動性限制；手續費 0.1425%（最低 20 元）、賣出稅 0.3%。不包含完整 V3 策略，不能作為直接買賣依據。")
        except Exception as exc:
            st.error(f"回測失敗：{exc}")
