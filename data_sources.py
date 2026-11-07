"""台股資料來源：僅負責取得資料，不負責交易決策。"""

import requests
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_history(symbol, period):
    """取得 Yahoo Finance 歷史股價，保留原本 15 分鐘快取。"""
    return yf.Ticker(symbol).history(period=period)


def get_company_info(symbol):
    """取得 Yahoo Finance 公司資訊。"""
    return yf.Ticker(symbol).info


def get_month_revenue(stock, start_date="2025-01-01"):
    """取得 FinMind 月營收 API 原始回應，交由主程式判斷狀態。"""
    response = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params={
            "dataset": "TaiwanStockMonthRevenue",
            "data_id": stock,
            "start_date": start_date,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()

def check_stock_history_quality(data):
    """檢查歷史資料是否為空、缺欄或包含不合理數值。"""
    errors = []

    if data is None or data.empty:
        errors.append("股票歷史資料為空")
        return {"data_valid": False, "errors": errors}

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    for column in required_columns:
        if column not in data.columns:
            errors.append(f"缺少必要欄位：{column}")

    numeric_values = {}
    for column in required_columns:
        if column not in data.columns:
            continue

        values = []
        invalid_count = 0
        for value in data[column]:
            try:
                if isinstance(value, bool):
                    raise ValueError
                number = float(value)
                if number != number or number in (float("inf"), float("-inf")):
                    raise ValueError
                if column == "Volume" and number < 0:
                    raise ValueError
                if column != "Volume" and number <= 0:
                    raise ValueError
                values.append(number)
            except (TypeError, ValueError, OverflowError):
                values.append(None)
                invalid_count += 1

        numeric_values[column] = values
        if invalid_count:
            rule = "須為有效且大於 0 的數值" if column != "Volume" else "須為有效且不小於 0 的數值"
            errors.append(f"{column} 欄有 {invalid_count} 筆無效資料（{rule}）")

    ohlc_columns = ["Open", "High", "Low", "Close"]
    if all(column in numeric_values for column in ohlc_columns):
        invalid_high = 0
        invalid_low = 0

        for opening, high, low, close in zip(
            numeric_values["Open"],
            numeric_values["High"],
            numeric_values["Low"],
            numeric_values["Close"],
        ):
            if None in (opening, high, low, close):
                continue
            if high < max(opening, close, low):
                invalid_high += 1
            if low > min(opening, close, high):
                invalid_low += 1

        if invalid_high:
            errors.append(f"High 欄有 {invalid_high} 筆低於 Open、Close 或 Low")
        if invalid_low:
            errors.append(f"Low 欄有 {invalid_low} 筆高於 Open、Close 或 High")

    return {
        "data_valid": len(errors) == 0,
        "errors": errors,
    }
