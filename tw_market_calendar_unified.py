
from tpex_calendar_parser import check_tpex_trading_day


SUPPORTED_MARKETS = {
    "TWSE": "上市",
    "TPEx": "上櫃",
}


def check_market_trading_day(market, date_value):
    """
    台股上市／上櫃共用交易日判斷 V1。

    TPEx：使用2026年官方年度開休市表。
    TWSE：尚未完成全年日曆整合，暫不判斷。
    """

    result = {
        "date": str(date_value),
        "market": market,
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": [],
    }

    if not isinstance(market, str):
        result["errors"].append("市場代碼必須是文字")
        return result

    market = market.strip().upper()

    if market == "TPEX":
        return check_tpex_trading_day(date_value)

    if market == "TWSE":
        result["market"] = "TWSE"
        result["errors"].append(
            "TWSE全年交易日曆尚未完成整合"
        )
        return result

    result["errors"].append(
        "不支援的市場代碼，請使用 TWSE 或 TPEx"
    )
    return result
