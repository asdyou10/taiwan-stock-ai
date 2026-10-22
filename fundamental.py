"""V3 基本面分析模組：保留既有 FinMind 月營收與營收成長判斷。"""

import pandas as pd
import streamlit as st

from data_sources import get_month_revenue


def render_revenue_analysis(stock):
    # V3 FinMind 月營收測試
    with st.expander("📊 V3 FinMind 月營收測試"):
        try:
            result = get_month_revenue(stock)

            if result.get("status") != 200:
                st.warning(
                    f"FinMind 回傳訊息：{result.get('msg', result)}"
                )
            elif result.get("data"):
                revenue_df = pd.DataFrame(result["data"])
                revenue_df = revenue_df.sort_values(
                    ["revenue_year", "revenue_month"]
                )
                st.dataframe(revenue_df.tail(12))
                # V3 基本面第1題：營收成長（月份驗證版）
                st.subheader("基本面第1題：營收成長")

                revenue_df["month_date"] = pd.PeriodIndex(
                    revenue_df["revenue_year"].astype(str)
                    + "-"
                    + revenue_df["revenue_month"].astype(str).str.zfill(2),
                    freq="M"
                )

                revenue_df = revenue_df.drop_duplicates(
                    subset=["month_date"], keep="last"
                ).sort_values("month_date")

                revenue_map = revenue_df.set_index(
                    "month_date"
                )["revenue"]

                latest_month = revenue_map.index[-1]
                yoy_results = []

                for i in range(3):
                    month = latest_month - i
                    last_year = month - 12

                    if month in revenue_map.index and last_year in revenue_map.index:
                        previous = revenue_map.loc[last_year]
                        current = revenue_map.loc[month]

                        if pd.notna(previous) and previous > 0 and pd.notna(current):
                            yoy_results.append(
                                (current / previous - 1) * 100
                            )

                if len(yoy_results) < 3:
                    st.info("最近3個月資料不足，暫不判斷營收趨勢。")
                else:
                    latest_yoy = yoy_results[0]
                    st.write(f"資料月份：{latest_month}")
                    st.write(f"最新月營收年增率：{latest_yoy:.2f}%")

                    if all(y > 0 for y in yoy_results):
                        st.success("初步判斷：連續3個月營收年增")
                    elif all(y < 0 for y in yoy_results):
                        st.warning("初步判斷：連續3個月營收年減")
                    else:
                        st.info("初步判斷：營收成長尚不穩定")
            else:
                st.warning("目前沒有取得月營收資料。")

        except Exception as e:
            st.warning(f"FinMind 查詢失敗：{e}")
