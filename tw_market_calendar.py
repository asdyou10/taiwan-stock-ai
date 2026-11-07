
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


def check_trading_day_v2(
    date,
    trading_dates,
    start_date,
    end_date,
    calendar_verified=False
):
    """
    檢查台股交易日、休市日或無法判斷。

    calendar_verified=True 表示：
    交易日清單已經與官方完整日曆核對，
    且涵蓋 start_date 到 end_date 的全部日期。
    """
    result = {
        "date": str(date),
        "is_trading_day": None,
        "status": "無法判斷",
        "errors": []
    }

    if not calendar_verified:
        result["errors"].append("交易日曆尚未完整驗證")
        return result

    if trading_dates is None:
        result["errors"].append("尚未提供交易日曆")
        return result

    try:
        def parse_date(value):
            timestamp = pd.Timestamp(value)

            if pd.isna(timestamp):
                raise ValueError("包含無效日期")

            if timestamp.tz is not None:
                timestamp = timestamp.tz_convert(
                    "Asia/Taipei"
                ).tz_localize(None)

            return timestamp.normalize()

        target = parse_date(date)
        start = parse_date(start_date)
        end = parse_date(end_date)

        if start > end:
            raise ValueError("日曆開始日期晚於結束日期")

        calendar = pd.DatetimeIndex(
            [parse_date(d) for d in trading_dates]
        )

        if calendar.has_duplicates:
            raise ValueError("交易日曆包含重複日期")

        if any(d < start or d > end for d in calendar):
            raise ValueError("交易日期超出日曆涵蓋範圍")

        if target < start or target > end:
            result["errors"].append(
                "查詢日期超出已驗證日曆範圍"
            )
            return result

        if target in calendar:
            result["is_trading_day"] = True
            result["status"] = "交易日"
        else:
            result["is_trading_day"] = False
            result["status"] = "休市日"

    except (ValueError, TypeError, OverflowError) as exc:
        result["errors"].append(
            f"交易日曆資料錯誤：{exc}"
        )

    return result
