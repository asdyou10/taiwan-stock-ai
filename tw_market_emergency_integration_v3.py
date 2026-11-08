
from twse_official_announcement_parser import parse_twse_announcements


def integrate_twse_announcements(html):
    """整合 TWSE 公告列表，不直接判定臨時停市。"""

    result = {
        "market": "TWSE",
        "status": "UNKNOWN",
        "source_verified": False,
        "announcement_count": 0,
        "announcements": [],
        "errors": [],
    }

    if not isinstance(html, str) or not html.strip():
        result["errors"].append("公告 HTML 資料為空或格式錯誤")
        return result

    try:
        announcements = parse_twse_announcements(html)

        result["announcement_count"] = len(announcements)
        result["announcements"] = announcements

        if not announcements:
            result["errors"].append("未解析到有效公告資料")

    except Exception as error:
        result["errors"].append(
            f"公告解析失敗：{type(error).__name__}"
        )

    return result
