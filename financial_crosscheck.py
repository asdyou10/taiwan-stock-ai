"""V4.2-04 stage 2: read-only, conservative financial cross-check diagnostics.

No official source is fetched or authenticated here. NEVER unlock automatic valuation.
"""
from __future__ import annotations
import math
import pandas as pd


def inspect_periods(income: pd.DataFrame | None, as_of: str) -> tuple[pd.DataFrame, list[str]]:
    columns = ['財報截止日', '季別（僅日期推定）', 'EPS 原始值（元）', '母公司淨利原始值（元）', '資料完整性', '公告時點', '估值資格']
    warnings = ['季別只依財報截止月份推定，無法證明 EPS 為單季、累計或年度。',
                'FinMind 財報截止日不是正式公告日期；沒有官方發布時間，不得用於歷史回測或自動估值。']
    if income is None or income.empty or not {'date', 'type', 'value'}.issubset(income.columns):
        return pd.DataFrame(columns=columns), warnings + ['損益表資料不足']
    df = income[['date', 'type', 'value']].copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['date', 'type', 'value'])
    try:
        cutoff = pd.Timestamp(as_of).normalize()
    except (ValueError, TypeError):
        return pd.DataFrame(columns=columns), warnings + ['分析日期無效']
    quarters = {3:'Q1', 6:'Q2', 9:'Q3', 12:'Q4'}
    rows = []
    for period, group in df.groupby('date', sort=True):
        date = period.normalize()
        if date > cutoff:
            continue
        def one(key):
            vals = group.loc[group['type'].eq(key), 'value']
            return float(vals.iloc[0]) if len(vals) == 1 and math.isfinite(float(vals.iloc[0])) else None
        eps = one('EPS')
        profit = one('EquityAttributableToOwnersOfParent')
        complete = eps is not None and profit is not None
        rows.append({'財報截止日': date.date().isoformat(),
                     '季別（僅日期推定）': quarters.get(date.month, '非標準截止月'),
                     'EPS 原始值（元）': eps, '母公司淨利原始值（元）': profit,
                     '資料完整性': '兩科目存在（口徑未核實）' if complete else '缺漏或重複科目',
                     '公告時點': '未核實', '估值資格': '禁止自動估值'})
    return pd.DataFrame(rows, columns=columns).sort_values('財報截止日', ascending=False).reset_index(drop=True), warnings
