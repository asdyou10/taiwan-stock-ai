
from datetime import datetime, date, timezone, timedelta
from urllib.parse import urlparse


OFFICIAL_DOMAINS = {
    "TWSE": "www.twse.com.tw",
    "TPEX": "www.tpex.org.tw",
}


def validate_emergency_source(
    market,
    date_value,
    announcement,
):
    """
    臨時停市 V2：公告資料格式與一致性檢查。

    announcement 範例：
    {
        "market": "TWSE",
        "date": "2026-11-09",
        "status": "CLOSED",
        "url": "https://www.twse.com.tw/...",
        "published_at": "2026-11-08T20:00:00"
    }

    本函式不會連線驗證網址或公告內容。
    """

    result = {
        "market": market,
        "date": str(date_value),
        "status": None,
        "data_valid": False,
        "source_verified": False,
        "errors": [],
    }

    # 1. 驗證市場
    if not isinstance(market, str):
        result["errors"].append("市場代碼必須是文字")
        return result

    market_code = market.strip().upper()

    if market_code not in OFFICIAL_DOMAINS:
        result["errors"].append("不支援的市場代碼")
        return result

    result["market"] = (
        "TPEx" if market_code == "TPEX" else "TWSE"
    )

    # 2. 驗證查詢日期
    try:
        target_date = date.fromisoformat(str(date_value))
    except (ValueError, TypeError):
        result["errors"].append("查詢日期格式錯誤")
        return result

    if target_date.year != 2026:
        result["errors"].append("目前只支援2026年")
        return result

    # 3. 驗證公告資料
    if not isinstance(announcement, dict):
        result["errors"].append("公告資料必須是字典")
        return result

    required_fields = [
        "market",
        "date",
        "status",
        "url",
        "published_at",
    ]

    for field in required_fields:
        if field not in announcement:
            result["errors"].append(
                f"缺少公告欄位：{field}"
            )

    if result["errors"]:
        return result

    # 4. 驗證公告市場
    announced_market = announcement["market"]

    if not isinstance(announced_market, str):
        result["errors"].append("公告市場格式錯誤")
    elif announced_market.strip().upper() != market_code:
        result["errors"].append("公告市場與查詢市場不一致")

    # 5. 驗證公告日期
    try:
        announced_date = date.fromisoformat(
            str(announcement["date"])
        )
        if announced_date != target_date:
            result["errors"].append(
                "公告日期與查詢日期不一致"
            )
    except (ValueError, TypeError):
        result["errors"].append("公告日期格式錯誤")

    # 6. 驗證公告狀態
    if announcement["status"] not in ("OPEN", "CLOSED"):
        result["errors"].append(
            "公告狀態僅支援OPEN或CLOSED"
        )
    else:
        result["status"] = announcement["status"]

    # 7. 驗證網址格式與網域
    url = announcement["url"]

    if not isinstance(url, str):
        result["errors"].append("公告網址格式錯誤")
    else:
        try:
            parsed_url = urlparse(url)

            if parsed_url.scheme != "https":
                result["errors"].append(
                    "公告網址必須使用HTTPS"
                )

            if (
                parsed_url.hostname
                != OFFICIAL_DOMAINS[market_code]
            ):
                result["errors"].append(
                    "公告網址不是指定市場的官方網域"
                )

            if parsed_url.username or parsed_url.password:
                result["errors"].append(
                    "公告網址不可包含登入資訊"
                )

        except ValueError:
            result["errors"].append("公告網址格式錯誤")

    
    # 8. 驗證發布時間與台灣時區
    published_at = announcement["published_at"]

    if not isinstance(published_at, str):
        result["errors"].append("發布時間格式錯誤")
    else:
        try:
            published_time = datetime.fromisoformat(
                published_at
            )

            # 必須提供明確時區
            if (
                published_time.tzinfo is None
                or published_time.utcoffset() is None
            ):
                result["errors"].append(
                    "發布時間必須包含時區資訊"
                )
            else:
                taiwan_timezone = timezone(
                    timedelta(hours=8)
                )

                taiwan_time = published_time.astimezone(
                    taiwan_timezone
                )

                if taiwan_time.date() > target_date:
                    result["errors"].append(
                        "公告發布日期晚於適用日期（台灣時間）"
                    )

        except (ValueError, TypeError, OverflowError):
            result["errors"].append("發布時間格式錯誤")


    # 9. 統一回傳
    result["data_valid"] = not result["errors"]

    # 不連線驗證官方公告，因此固定False
    result["source_verified"] = False

    return result
