
import pandas as pd


def check_trading_day(date, trading_dates):
    """
    檢查指定日期是否為已確認的台股交易日。

    date: 要檢查的日期
    trading_dates: 已驗證的官方交易日期清單
    """
    result = {
        "date": str(date),
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": []
    }

    try:
        target = pd.Timestamp(date).normalize()

        if pd.isna(target):
            raise ValueError("無效日期")

        if trading_dates is None:
            result["errors"].append("尚未提供交易日曆")
            return result

        calendar = pd.DatetimeIndex(trading_dates)

        if calendar.hasnans:
            result["errors"].append("交易日曆包含無效日期")
            return result

        if target.tz is not None:
            target = target.tz_localize(None)

        if calendar.tz is not None:
            calendar = calendar.tz_localize(None)

        calendar = calendar.normalize()

        if target in calendar:
            result["is_trading_day"] = True
            result["status"] = "交易日"
        else:
            result["status"] = "無法判斷"
            result["errors"].append(
                "日期不在已提供的交易日清單中，不能直接判定為休市"
            )

    except (ValueError, TypeError, OverflowError) as exc:
        result["errors"].append(f"日期或交易日曆格式錯誤：{exc}")

    return result
