
from datetime import date
from pathlib import Path

from twse_calendar_parser import parse_twse_calendar


def check_twse_trading_day(date_value, csv_path):
    """
    TWSE 上市股票交易日曆 V1。

    使用官方2026年開休市CSV。
    一般平日依年度規則推定。
    不包含臨時停市或最新公告更新。
    """

    result = {
        "date": str(date_value),
        "market": "TWSE",
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": [],
        "source": "TWSE 2026年度開休市CSV",
        "verification": "未驗證即時停市",
    }

    # 1. 驗證日期
    try:
        target = date.fromisoformat(str(date_value))
    except (ValueError, TypeError):
        result["errors"].append(
            "日期格式錯誤，請使用 YYYY-MM-DD"
        )
        return result

    if target.year != 2026:
        result["errors"].append("目前只支援2026年")
        return result

    # 2. 讀取官方CSV
    parsed = parse_twse_calendar(
        Path(csv_path),
        expected_year=2026
    )

    if not parsed["data_valid"]:
        result["errors"].extend(parsed["errors"])
        if not result["errors"]:
            result["errors"].append("官方CSV驗證失敗")
        return result

    # 3. 建立特殊日期索引
    special_dates = {
        record["date"]: record
        for record in parsed["records"]
    }

    target_str = target.isoformat()

    # 4. 優先使用官方特殊日期
    if target_str in special_dates:
        record = special_dates[target_str]

        if record["status"] == "trading":
            result["is_trading_day"] = True
            result["status"] = "交易日"

        elif record["status"] in (
            "holiday",
            "settlement_only"
        ):
            result["is_trading_day"] = False
            result["status"] = "休市日"

        return result

    # 5. 一般週末
    if target.weekday() >= 5:
        result["is_trading_day"] = False
        result["status"] = "休市日"
        return result

    # 6. 一般平日：依年度規則推定
    result["is_trading_day"] = True
    result["status"] = "交易日"

    return result
