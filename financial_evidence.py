"""Stage 4: explicit evidence ledger. No automated assertion of official verification."""
from __future__ import annotations
from datetime import date
from urllib.parse import urlparse
import math
import pandas as pd

KINDS = ('單季', '年初至今累計', '全年')

def validate_evidence(period_end: str, release_date: str, eps_kind: str,
                      weighted_shares_m: float, source_url: str, as_of: str,
                      eps: float | None = None, parent_profit_twd: float | None = None) -> dict:
    """Check manually supplied evidence for internal plausibility, not authenticity."""
    problems = []
    try:
        period = date.fromisoformat(period_end)
        release = date.fromisoformat(release_date)
        cutoff = date.fromisoformat(as_of)
        if release <= period:
            problems.append('公告日期必須晚於財報截止日')
        if release > cutoff:
            problems.append('公告日期晚於分析日期，禁止使用未來資料')
    except (TypeError, ValueError):
        problems.append('日期格式錯誤，必須為 YYYY-MM-DD')
    if eps_kind not in KINDS:
        problems.append('EPS 口徑必須明確選擇單季、累計或全年')
    try:
        shares = float(weighted_shares_m)
        if not math.isfinite(shares) or shares <= 0:
            problems.append('加權平均股數必須為正數（百萬股）')
    except (TypeError, ValueError):
        problems.append('加權平均股數格式不合法')
        shares = float('nan')
    url = urlparse(source_url.strip()) if isinstance(source_url, str) else urlparse('')
    if url.scheme != 'https' or not url.netloc or '.' not in url.netloc or url.username or url.password:
        problems.append('請提供可核對的 HTTPS 公告來源連結')
    if eps is not None and parent_profit_twd is not None:
        try:
            e, p = float(eps), float(parent_profit_twd)
            if not math.isfinite(e) or not math.isfinite(p):
                problems.append('EPS 或母公司淨利非有限數值')
            elif abs(e) >= 0.01 and math.isfinite(shares) and shares > 0:
                implied_eps = p / (shares * 1_000_000)
                # Diagnostic only: earnings numerator/denominator and EPS basis may differ.
                if abs(implied_eps - e) > max(0.1, abs(e) * 0.15):
                    problems.append('淨利／股數與 EPS 差異偏大，需核對期間及股數口徑')
        except (ValueError, TypeError):
            problems.append('EPS 或淨利格式不合法')
    return {
        '格式與時點檢查': '通過（僅檢查輸入，未核實來源真偽）' if not problems else '未通過',
        '問題': problems,
        '來源真偽': '尚未獨立核實',
        '自動估值資格': '禁止自動估值',
    }


def period_matches_income(income: pd.DataFrame, period_end: str) -> bool:
    if income is None or income.empty or 'date' not in income.columns:
        return False
    dates = pd.to_datetime(income['date'], errors='coerce')
    return bool((dates.dt.strftime('%Y-%m-%d') == period_end).any())
