
from datetime import date


# TPEx 民國115年（西元2026年）股票市場開休市日期
# 來源：證券櫃檯買賣中心官方年度開休市日期表
# 注意：此資料為年度公告，不包含後續臨時停市更新

TPEX_2026_HOLIDAYS = {
    "2026-01-01",
    "2026-02-12",
    "2026-02-13",
    "2026-02-16",
    "2026-02-17",
    "2026-02-18",
    "2026-02-19",
    "2026-02-20",
    "2026-02-27",
    "2026-04-03",
    "2026-04-06",
    "2026-05-01",
    "2026-06-19",
    "2026-09-25",
    "2026-09-28",
    "2026-10-09",
    "2026-10-26",
    "2026-12-25",
}

TPEX_2026_SPECIAL_TRADING_DAYS = {
    "2026-01-02",
    "2026-02-11",
    "2026-02-23",
}


def check_tpex_trading_day(date_value):
    """
    依2026年TPEx年度開休市表，檢查上櫃股票交易日。

    不含臨時停市公告。
    僅適用2026年。
    """
    result = {
        "date": str(date_value),
        "market": "TPEx",
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": []
    }

    try:
        target = date.fromisoformat(str(date_value))
    except (ValueError, TypeError):
        result["errors"].append("日期格式錯誤，請使用 YYYY-MM-DD")
        return result

    if target.year != 2026:
        result["errors"].append("目前只支援2026年")
        return result

    target_str = target.isoformat()

    if target_str in TPEX_2026_HOLIDAYS:
        result["is_trading_day"] = False
        result["status"] = "休市日"

    elif target_str in TPEX_2026_SPECIAL_TRADING_DAYS:
        result["is_trading_day"] = True
        result["status"] = "交易日"

    elif target.weekday() >= 5:
        result["is_trading_day"] = False
        result["status"] = "休市日"

    else:
        result["is_trading_day"] = True
        result["status"] = "交易日"

    return result
