"""V4.2-03: cautious FinMind current-data ingestion; never claim PIT availability."""
from __future__ import annotations
import math
import pandas as pd
import requests

API = 'https://api.finmindtrade.com/api/v4/data'


def fetch_dataset(stock: str, dataset: str, start_date: str, token: str = '') -> list[dict]:
    if not (stock.isdigit() and 4 <= len(stock) <= 6):
        raise ValueError('股票代號必須是 4 至 6 位數字')
    params = {'dataset': dataset, 'data_id': stock, 'start_date': start_date}
    if token:
        params['token'] = token
    response = requests.get(API, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get('status') != 200:
        raise ValueError(f"FinMind 回應：{payload.get('msg', '查詢失敗')}")
    records = payload.get('data')
    if not isinstance(records, list):
        raise ValueError('FinMind 回應缺少有效 data 清單')
    return records


def complete_annual_revenues(records: list[dict], as_of: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Only 12 distinct valid months make a complete annual total; amounts are TWD."""
    issues = []
    df = pd.DataFrame(records)
    required = {'revenue_year', 'revenue_month', 'revenue'}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame(columns=['年度', '完整月份', '年度營收（百萬元）']), ['缺少可用月營收欄位']
    df = df.copy()
    for c in required:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    invalid = df[list(required)].isna().any(axis=1) | ~df['revenue_month'].between(1, 12) | (df['revenue'] < 0)
    if invalid.any():
        issues.append(f'排除 {int(invalid.sum())} 筆缺漏、月份錯誤或負營收紀錄')
    df = df.loc[~invalid].copy()
    df['revenue_year'] = df['revenue_year'].astype(int)
    df['revenue_month'] = df['revenue_month'].astype(int)
    # Exclude months beyond the requested date; period month is NOT a publication date.
    if as_of:
        cutoff = pd.Timestamp(as_of)
        df = df.loc[(df['revenue_year'] * 100 + df['revenue_month']) <= cutoff.year * 100 + cutoff.month]
    dup = df.duplicated(['revenue_year', 'revenue_month'], keep=False)
    if dup.any():
        issues.append('偵測到重複月份；有衝突的年度不納入自動基準')
    conflicting_years = set(df.loc[dup, 'revenue_year'])
    df = df.loc[~df['revenue_year'].isin(conflicting_years)]
    if df.empty:
        return pd.DataFrame(columns=['年度', '完整月份', '年度營收（百萬元）']), issues + ['沒有完整年度營收']
    summary = df.groupby('revenue_year').agg(months=('revenue_month', 'nunique'), revenue=('revenue', 'sum'))
    summary = summary.loc[summary['months'] == 12].sort_index()
    result = pd.DataFrame({'年度': summary.index.astype(int), '完整月份': summary['months'].astype(int).values,
                           '年度營收（百萬元）': (summary['revenue'] / 1_000_000).values})
    if result.empty:
        issues.append('目前沒有完整 12 個月份的年度營收')
    issues.append('月營收月份不是正式公告日期；不得直接用於歷史時點回測')
    return result.reset_index(drop=True), issues


def audit_income_statements(records: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Inspect raw line items without assuming quarter-vs-YTD or field semantics."""
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(), ['未取得損益表資料，無法驗證 EPS 或獲利率']
    required = {'date', 'type', 'value'}
    if not required.issubset(df.columns):
        return df, ['損益表欄位與預期不同，禁止自動推算 EPS']
    out = df.copy()
    out['date'] = pd.to_datetime(out['date'], errors='coerce')
    out['value'] = pd.to_numeric(out['value'], errors='coerce')
    warnings = []
    if out['date'].isna().any() or out['value'].isna().any():
        warnings.append('部分損益表日期或金額無法解析')
    warnings.append('尚未驗證各損益表科目的定義、季報累計口徑、公告日期與股數；不自動宣稱 EPS 或合理價')
    return out.sort_values('date', ascending=False), warnings


def review_financial_periods(records: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Display reported raw EPS/profit by statement date, with conservative quality flags.

    FinMind statement date is the period end, not the disclosure date. Raw EPS
    is deliberately not annualized or classified as standalone/YTD.
    """
    columns = ['財報截止日', 'EPS 原始值（元）', '歸屬母公司淨利原始值（元）', 'EPS 口徑', '公告日期', '估值資格']
    df = pd.DataFrame(records)
    if df.empty or not {'date', 'type', 'value'}.issubset(df.columns):
        return pd.DataFrame(columns=columns), ['缺少財報日期、科目或數值，無法建立財報期間摘要']
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['date', 'type', 'value'])
    if df.empty:
        return pd.DataFrame(columns=columns), ['沒有有效的財報科目']
    issues = []
    rows = []
    for period, grp in df.groupby('date', sort=True):
        def unique_item(key):
            values = grp.loc[grp['type'] == key, 'value']
            if len(values) != 1:
                if len(values) > 1:
                    issues.append(f'{period.date()} 的 {key} 有重複紀錄，已拒絕採用')
                return None
            return float(values.iloc[0])
        eps = unique_item('EPS')
        profit = unique_item('EquityAttributableToOwnersOfParent')
        rows.append({'財報截止日': period.date().isoformat(), 'EPS 原始值（元）': eps,
                     '歸屬母公司淨利原始值（元）': profit,
                     'EPS 口徑': '未核實（單季／累計／年度）', '公告日期': '未核實',
                     '估值資格': '禁止自動估值'})
    issues.append('財報截止日不是公告日；EPS 口徑與股數尚未核實，不得自動推算合理價')
    return pd.DataFrame(rows, columns=columns).sort_values('財報截止日', ascending=False).reset_index(drop=True), issues


# Stage 3: diagnostics only. Financial period end dates are NOT release dates.
def audit_eps_profit_consistency(records: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Check EPS/profit consistency without pretending to verify share counts.

    The ratio profit / EPS is an *implied* share count, not an official
    weighted-average share count. FinMind EPS may be cumulative or quarterly.
    """
    cols = ['財報截止日', 'EPS 原始值（元）', '母公司淨利原始值（元）',
            '隱含股數（百萬股，僅供診斷）', '初步檢查', '公告日期驗證', '估值資格']
    periods, issues = review_financial_periods(records)
    if periods.empty:
        return pd.DataFrame(columns=cols), issues
    rows = []
    for _, r in periods.iterrows():
        eps = r['EPS 原始值（元）']
        profit = r['歸屬母公司淨利原始值（元）']
        implied = None
        if eps is None or profit is None or pd.isna(eps) or pd.isna(profit):
            status = 'EPS 或母公司淨利缺漏'
        elif not math.isfinite(eps) or not math.isfinite(profit):
            status = '數值不合法'
        elif abs(eps) < 0.01:
            status = 'EPS 接近零，無法可靠反推股數'
        elif eps * profit < 0:
            status = 'EPS 與淨利符號不一致，需核對口徑'
        else:
            implied = profit / eps / 1_000_000
            if implied <= 0 or not math.isfinite(implied):
                implied = None
                status = '隱含股數無效'
            else:
                status = '僅供診斷；尚未核對正式加權平均股數'
        rows.append({'財報截止日': r['財報截止日'], 'EPS 原始值（元）': eps,
                     '母公司淨利原始值（元）': profit,
                     '隱含股數（百萬股，僅供診斷）': round(implied, 3) if implied is not None else None,
                     '初步檢查': status, '公告日期驗證': '未驗證（截止日不等於公告日）',
                     '估值資格': '禁止自動估值'})
    issues.append('隱含股數是淨利除以 EPS 的診斷值，非正式加權平均股數；不得用於估值。')
    issues.append('未取得可核實的公開公告日期及 EPS 單季／累計口徑，禁止歷史時點回測與自動估值。')
    return pd.DataFrame(rows, columns=cols), issues
