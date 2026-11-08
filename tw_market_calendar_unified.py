
from tpex_calendar_parser import check_tpex_trading_day
from twse_trading_calendar import check_twse_trading_day


def check_market_trading_day(market, date_value, csv_path=None):
    """
    台股上市／上櫃共用交易日曆 V2。

    TWSE：讀取2026年官方年度CSV。
    TPEx：使用2026年年度開休市資料。

    不包含臨時停市的即時驗證。
    """

    result = {
        "date": str(date_value),
        "market": market,
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": [],
    }

    # 1. 驗證市場代碼
    if not isinstance(market, str):
        result["errors"].append("市場代碼必須是文字")
        return result

    market_code = market.strip().upper()

    # 2. 上櫃市場
    if market_code == "TPEX":
        return check_tpex_trading_day(date_value)

    # 3. 上市市場
    if market_code == "TWSE":
        if csv_path is None or not str(csv_path).strip():
            result["market"] = "TWSE"
            result["errors"].append("尚未提供TWSE官方CSV路徑")
            return result

        return check_twse_trading_day(date_value, csv_path)

    # 4. 不支援的市場
    result["errors"].append(
        "不支援的市場代碼，請使用 TWSE 或 TPEx"
    )
    return result
