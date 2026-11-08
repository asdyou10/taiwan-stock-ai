
from datetime import date

from tw_market_calendar_unified import check_market_trading_day
from twse_calendar_parser import parse_twse_calendar
from tpex_calendar_parser import (
    TPEX_2026_HOLIDAYS,
    TPEX_2026_SPECIAL_TRADING_DAYS,
)


def check_market_trading_day_v3(market, date_value, csv_path=None):
    """
    台股上市櫃共用交易日曆 V3。

    統一TWSE與TPEx輸出格式。
    標示判斷依據與年度資料驗證限制。
    不代表即時交易所確認。
    """

    base = check_market_trading_day(
        market, date_value, csv_path
    )

    market_code = (
        market.strip().upper()
        if isinstance(market, str)
        else market
    )

    result = {
        "date": str(date_value),
        "market": (
            "TPEx" if market_code == "TPEX"
            else "TWSE" if market_code == "TWSE"
            else market
        ),
        "is_trading_day": base["is_trading_day"],
        "status": base["status"],
        "errors": list(base["errors"]),
        "source": None,
        "year": 2026,
        "basis": "無法判斷",
        "verification": "未驗證即時停市",
    }

    if market_code == "TWSE":
        result["source"] = "TWSE 2026年度開休市CSV"
    elif market_code == "TPEX":
        result["source"] = "TPEx 2026年度開休市表"

    # 原始判斷失敗，不再推定判斷依據
    if base["is_trading_day"] is None:
        return result

    try:
        target = date.fromisoformat(str(date_value))
    except (ValueError, TypeError):
        result["errors"].append("日期格式錯誤")
        result["is_trading_day"] = None
        result["status"] = "無法判斷"
        return result

    target_str = target.isoformat()

    # TWSE：從CSV找出官方特殊日期
    if market_code == "TWSE":
        parsed = parse_twse_calendar(
            csv_path, expected_year=2026
        )

        if not parsed["data_valid"]:
            result["errors"].extend(parsed["errors"])
            result["is_trading_day"] = None
            result["status"] = "無法判斷"
            return result

        special_dates = {
            record["date"]
            for record in parsed["records"]
        }

        if target_str in special_dates:
            result["basis"] = "官方特殊日期"
        elif target.weekday() >= 5:
            result["basis"] = "一般週末規則"
        else:
            result["basis"] = "一般平日推定"

    # TPEx：從年度日期集合判斷
    elif market_code == "TPEX":
        if (
            target_str in TPEX_2026_HOLIDAYS
            or target_str in TPEX_2026_SPECIAL_TRADING_DAYS
        ):
            result["basis"] = "官方特殊日期"
        elif target.weekday() >= 5:
            result["basis"] = "一般週末規則"
        else:
            result["basis"] = "一般平日推定"

    return result
