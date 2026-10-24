"""Read-only diagnostic of official EPS periods; never grants valuation eligibility.

Official general-industry statement feeds may be a latest-quarter snapshot, not
historical archives. Their EPS field is not assumed to be standalone-quarter EPS.
"""
from __future__ import annotations
import math
from financial_market_probe import SOURCES, _fetch


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    s = str(value).strip().replace(',', '')
    if not s or s in {'--', '-', 'N/A', 'nan'}:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None


def inspect_official_eps_period(stock: str, fetcher=None) -> dict:
    """Check quarter availability and compare raw EPS; no verified EPS convention."""
    stock = str(stock).strip()
    if not (stock.isdigit() and 4 <= len(stock) <= 6):
        return {'狀態': '代號格式錯誤', '紀錄': [], '警示': ['股票代號格式不符'], '可用於估值': False}
    fetcher = fetcher or _fetch
    rows, notices, errors = [], [], []
    for label, (kind, url) in SOURCES.items():
        try:
            data = fetcher(kind, url)
            for record in data:
                if str(record.get('公司代號', '')).strip() != stock:
                    continue
                year = str(record.get('年度', '')).strip()
                quarter = str(record.get('季別', '')).strip().replace('Q', '')
                eps = _number(record.get('基本每股盈餘（元）'))
                if eps is None:
                    # Some feeds use alternate punctuation / whitespace.
                    candidates = [v for k, v in record.items() if '基本每股盈餘' in str(k)]
                    eps = _number(candidates[0]) if len(candidates) == 1 else None
                rows.append({'官方資料集': label, '年度（民國）': year, '季別': quarter,
                             '官方EPS原始值（元）': eps, 'EPS口徑': '未核實',
                             '官方來源': url, '公告日期': '未核實'})
        except Exception as exc:
            errors.append(f'{label}：{type(exc).__name__}: {str(exc)[:120]}')
    if errors:
        notices.append('部分官方來源查詢失敗，不得依未查得資料推斷季度不存在。')
    if not rows:
        notices.append('官方資料集中未找到對應股票；可能是期間、產業分類或連線限制。')
    else:
        by_year = {}
        for row in rows:
            by_year.setdefault((row['官方資料集'], row['年度（民國）']), set()).add(row['季別'])
        for (source, year), quarters in by_year.items():
            missing = sorted({'1', '2', '3', '4'} - quarters)
            if missing:
                notices.append(f'{source} 民國{year}年：此查詢僅取得季度 {"、".join(sorted(quarters))}；其他季度未取得，不能推算單季 EPS。')
            else:
                notices.append(f'{source} 民國{year}年：四季紀錄均存在，但仍須驗證各季 EPS 是否為累計口徑及股本調整。')
    notices.append('官方損益表 API 的「年度／季別」不等於 EPS 單季口徑；不得直接將 Q2 原始 EPS 減去 Q1。')
    notices.append('FinMind EPS 與官方 EPS 只有在期間、口徑、資料可得時間與股數基礎一致後才可數值比對。')
    notices.append('公告日期、正式 EPS 口徑及加權平均股數尚未獨立核實；禁止自動估值。')
    return {'狀態': '部分來源失敗' if errors else '查詢完成', '紀錄': rows[:24], '警示': notices,
            '錯誤': errors, '可用於估值': False}
