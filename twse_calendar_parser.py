
import csv
import re
from pathlib import Path
from datetime import date


def parse_twse_calendar(file_path, expected_year=2026):
    """
    解析 TWSE 官方年度開休市 CSV。

    使用 CP950 編碼。
    回傳官方特殊日期及其交易狀態。
    不修改原始 CSV。
    """

    result = {
        "data_valid": False,
        "year": expected_year,
        "source": "TWSE",
        "encoding": "cp950",
        "row_count": 0,
        "records": [],
        "errors": []
    }

    path = Path(file_path)

    if not path.is_file():
        result["errors"].append("找不到官方 CSV 檔案")
        return result

    try:
        with path.open(
            "r",
            encoding="cp950",
            newline=""
        ) as file:
            rows = list(csv.reader(file))

        if len(rows) < 3:
            result["errors"].append("CSV 資料不足")
            return result

        title = rows[0][0].strip()

        year_match = re.search(r"115年", title)

        if not year_match or expected_year != 2026:
            result["errors"].append("CSV 年度與預期年度不符")
            return result

        headers = rows[1]

        if len(headers) != 4 or headers[0] != "日期":
            result["errors"].append("CSV 欄位格式不正確")
            return result

        for row_number, row in enumerate(rows[2:], start=3):

            if len(row) != 4:
                result["errors"].append(
                    f"第 {row_number} 行欄位數錯誤"
                )
                continue

            raw_date, name, description, marker = [
                value.strip() for value in row
            ]

            match = re.match(r"^(\d+)月(\d+)日", raw_date)

            if not match:
                result["errors"].append(
                    f"第 {row_number} 行日期格式錯誤"
                )
                continue

            month = int(match.group(1))
            day = int(match.group(2))

            try:
                parsed_date = date(expected_year, month, day)
            except ValueError:
                result["errors"].append(
                    f"第 {row_number} 行日期無效"
                )
                continue

            if marker not in ("", "o", "*"):
                result["errors"].append(
                    f"第 {row_number} 行交易標記不明"
                )
                continue

            if marker == "o":
                status = "trading"
            elif marker == "*":
                status = "settlement_only"
            else:
                status = "holiday"

            result["records"].append({
                "date": parsed_date.isoformat(),
                "name": name,
                "description": description,
                "marker": marker,
                "status": status
            })

        result["row_count"] = len(result["records"])

        dates = [
            record["date"]
            for record in result["records"]
        ]

        if len(dates) != len(set(dates)):
            result["errors"].append("官方資料包含重複日期")

        if not result["errors"] and result["row_count"] > 0:
            result["data_valid"] = True

    except (OSError, UnicodeError, csv.Error) as exc:
        result["errors"].append(
            f"CSV 讀取失敗：{exc}"
        )

    return result
