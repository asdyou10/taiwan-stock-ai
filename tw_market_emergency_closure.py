
from datetime import date

from tw_market_calendar_v3 import check_market_trading_day_v3


def check_market_emergency_closure(
    market,
    date_value,
    official_status=None,
    csv_path=None,
):
    """
    台股臨時停市保護機制 V1。

    official_status:
        "OPEN"   = 已取得官方正常交易確認
        "CLOSED" = 已取得官方臨時停市公告
        None     = 尚未取得官方確認

    注意：
    V1不會自動連線交易所。
    official_status必須由外部提供可信的官方資訊。
    """

    calendar = check_market_trading_day_v3(
        market,
        date_value,
        csv_path,
    )

    result = {
        "date": calendar["date"],
        "market": calendar["market"],
        "is_trading_day": calendar["is_trading_day"],
        "status": calendar["status"],
        "calendar_basis": calendar["basis"],
        "official_status": official_status,
        "emergency_verified": False,
        "decision_source": "年度交易日曆",
        "verification": "尚未取得臨時停市官方確認",
        "errors": list(calendar["errors"]),
    }

    # 年度日曆無法判斷時，不允許直接覆蓋
    if calendar["is_trading_day"] is None:
        return result

    # 驗證官方狀態參數
    if official_status not in (None, "OPEN", "CLOSED"):
        result["is_trading_day"] = None
        result["status"] = "無法判斷"
        result["decision_source"] = "無法判斷"
        result["errors"].append(
            "official_status僅支援OPEN、CLOSED或None"
        )
        return result

    # 尚未取得官方公告
    if official_status is None:
        return result

    
    # 外部提供臨時停市狀態
    if official_status == "CLOSED":

        # 年度日曆已經休市，不需要再次覆蓋
        if calendar["is_trading_day"] is False:
            result["verification"] = (
                "年度日曆已休市，未採用外部停市狀態"
            )
            return result

        result["is_trading_day"] = False
        result["status"] = "休市日"
        result["emergency_verified"] = False
        result["decision_source"] = "外部傳入的停市狀態（未核實來源）"
        result["verification"] = "尚未獨立核實官方停市公告"
        return result


    
    # 外部提供正常交易狀態
    if official_status == "OPEN":

        # 不允許將年度休市日改成交易日
        if calendar["is_trading_day"] is False:
            result["errors"].append(
                "年度日曆為休市日，OPEN不能直接覆蓋"
            )
            result["verification"] = (
                "外部OPEN狀態與年度日曆衝突，未採用"
            )
            return result

        # 原定交易日維持交易
        result["is_trading_day"] = True
        result["status"] = "交易日"
        result["emergency_verified"] = False
        result["decision_source"] = (
            "年度交易日曆（外部OPEN狀態未核實）"
        )
        result["verification"] = (
            "尚未獨立核實官方正常交易公告"
        )
        return result
