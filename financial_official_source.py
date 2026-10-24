"""V4.2-04 stage 3a: official-source URL precheck, not document verification.

Only recognizes official Taiwan disclosure hosts. It does not fetch or verify a
filing, publication time, EPS basis or weighted-average shares. Never unlocks valuation.
"""
from __future__ import annotations
from urllib.parse import urlsplit
import pandas as pd

OFFICIAL_HOSTS = frozenset({
    'mops.twse.com.tw',
    'mopsov.twse.com.tw',
    'openapi.twse.com.tw',
    'www.twse.com.tw',
    'www.tpex.org.tw',
})
OFFICIAL_PORTALS = (
    ('公開資訊觀測站（MOPS）', 'https://mops.twse.com.tw/'),
    ('證交所公開資料 API 入口', 'https://openapi.twse.com.tw/'),
    ('臺灣證券交易所', 'https://www.twse.com.tw/'),
    ('證券櫃檯買賣中心', 'https://www.tpex.org.tw/'),
)

def check_official_url(raw_url: str) -> tuple[str, str]:
    """Check URL structure and official host only; never fetch external URLs."""
    if not isinstance(raw_url, str) or not raw_url.strip():
        return '未提供', '尚未輸入財報公告連結'
    if any(c.isspace() for c in raw_url) or any(ord(c) < 32 for c in raw_url):
        return '不接受', '連結包含空白或控制字元'
    try:
        parsed = urlsplit(raw_url.strip())
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return '不接受', '連結格式不正確'
    if parsed.scheme != 'https' or not host or parsed.username or parsed.password or port not in (None, 443):
        return '不接受', '只接受無帳密、無非標準連接埠的 HTTPS 連結'
    if host.lower().rstrip('.') not in OFFICIAL_HOSTS:
        return '非官方白名單', '網域不在目前的官方來源白名單（不代表連結必然不可信）'
    return '官方網域格式符合', '僅確認網址所屬網域；尚未讀取公告內容、公司、期間或公告時間'


def source_precheck_table(periods: pd.DataFrame | None) -> pd.DataFrame:
    columns = ['財報截止日', '官方公告連結', '公告日期', 'EPS 口徑', '加權平均股數', '估值資格']
    if periods is None or periods.empty or '財報截止日' not in periods.columns:
        return pd.DataFrame(columns=columns)
    dates = periods['財報截止日'].dropna().astype(str).drop_duplicates().head(12)
    return pd.DataFrame([{
        '財報截止日': d, '官方公告連結': '尚未逐期匹配', '公告日期': '未核實',
        'EPS 口徑': '未核實', '加權平均股數': '未核實', '估值資格': '禁止自動估值'
    } for d in dates], columns=columns)
