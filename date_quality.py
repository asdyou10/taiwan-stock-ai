
import pandas as pd


def check_date_quality(data):
    """檢查股票歷史資料的日期結構，不修改原始資料。"""
    result = {
        "date_valid": False,
        "errors": [],
        "row_count": 0,
    }

    if not isinstance(data, pd.DataFrame) or data.empty:
        result["errors"].append("資料為空或格式不正確")
        return result

    result["row_count"] = len(data)
    index = data.index

    if not isinstance(index, pd.DatetimeIndex):
        result["errors"].append("日期索引不是 DatetimeIndex")
        return result

    if index.hasnans:
        result["errors"].append("日期索引包含無效日期 NaT")

    if not index.is_monotonic_increasing:
        result["errors"].append("日期未依照由舊到新排序")

    # 以交易日期檢查重複，避免同一天被重複計算
    if index.normalize().duplicated().any():
        result["errors"].append("存在重複交易日期")

    result["date_valid"] = len(result["errors"]) == 0
    return result
