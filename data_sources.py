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
