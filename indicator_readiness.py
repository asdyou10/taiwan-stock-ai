
import math

import pandas as pd


def check_indicator_readiness(data):
    """檢查技術指標資料是否充足，不產生交易訊號。"""
    result = {
        "data_valid": False,
        "errors": [],
        "indicators": {},
    }

    requirements = {
        "MA20": ("Close", 20),
        "MA60": ("Close", 60),
        "RSI14": ("Close", 15),
        "VOL20": ("Volume", 20),
    }

    if not isinstance(data, pd.DataFrame) or data.empty:
        result["errors"].append("資料為空或格式不正確")
        return result

    for column in ("Close", "Volume"):
        if column not in data.columns:
            result["errors"].append(f"缺少必要欄位：{column}")

    if result["errors"]:
        return result

    valid = {}
    for column in ("Close", "Volume"):
        numbers = pd.to_numeric(data[column], errors="coerce")
        valid[column] = numbers.map(
            lambda x: pd.notna(x)
            and math.isfinite(float(x))
            and (float(x) > 0 if column == "Close" else float(x) >= 0)
        )

    def trailing_count(flags):
        count = 0
        for ok in reversed(flags.tolist()):
            if not ok:
                break
            count += 1
        return count

    close_count = trailing_count(valid["Close"])
    volume_count = trailing_count(valid["Volume"])

    for name, (column, required) in requirements.items():
        count = close_count if column == "Close" else volume_count
        ready = count >= required

        result["indicators"][name] = {
            "valid_count": count,
            "required": required,
            "math_ready": ready,
            "trading_ready": None,
        }

    result["indicators"]["MACD"] = {
        "valid_count": close_count,
        "required": None,
        "math_ready": close_count >= 1,
        "trading_ready": None,
    }

    result["data_valid"] = True
    return result
