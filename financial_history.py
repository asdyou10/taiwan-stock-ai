"""Conservative FinMind historical quarterly completeness checks; not point-in-time verified."""
from __future__ import annotations
import calendar
import pandas as pd

FIELDS = {'EPS': 'EPS 原始值（元）', 'EquityAttributableToOwnersOfParent': '母公司淨利原始值（元）'}
COLUMNS = ['財報截止日','年度','季度',*FIELDS.values(),'資料狀態','EPS 口徑','公告日期','估值資格']
QUARTER_ENDS = {(3,31):1,(6,30):2,(9,30):3,(12,31):4}


def _period_end(year, quarter):
    month = quarter * 3
    return pd.Timestamp(year, month, calendar.monthrange(year, month)[1])


def _disclosure_deadline(year, quarter):
    # General Taiwan listed/OTC non-financial issuer reporting deadlines, calendar-year fiscal year.
    # These are only heuristic dates, NOT verified filing dates or proof of a filing obligation.
    if quarter == 1:
        return pd.Timestamp(year, 5, 15)
    if quarter == 2:
        return pd.Timestamp(year, 8, 14)
    if quarter == 3:
        return pd.Timestamp(year, 11, 14)
    return pd.Timestamp(year + 1, 3, 31)


def inspect_history_quality(table: pd.DataFrame, years: int = 5, as_of: str | None = None):
    """Return display summary and missing-period diagnostics, never asserting actual filing status."""
    cutoff = pd.Timestamp(as_of or pd.Timestamp.now(tz='Asia/Taipei').date()).normalize()
    first_year = cutoff.year - years + 1
    summary = {'查詢起日':f'{first_year}-01-01','分析日期':cutoff.date().isoformat(),
               '實得季度數':len(table), '最早季度':'無', '最新季度':'無',
               'EPS 有值季度':0,'淨利有值季度':0,'EPS 與淨利皆有值季度':0}
    if not table.empty:
        ordered = table.sort_values('財報截止日')
        summary['最早季度'] = f"{int(ordered.iloc[0]['年度'])}{ordered.iloc[0]['季度']}"
        summary['最新季度'] = f"{int(ordered.iloc[-1]['年度'])}{ordered.iloc[-1]['季度']}"
        eps = table[FIELDS['EPS']].notna()
        profit = table[FIELDS['EquityAttributableToOwnersOfParent']].notna()
        summary['EPS 有值季度'] = int(eps.sum())
        summary['淨利有值季度'] = int(profit.sum())
        summary['EPS 與淨利皆有值季度'] = int((eps & profit).sum())
    present = set(zip(table['年度'].astype(int),table['季度'])) if not table.empty else set()
    gaps = []
    for year in range(first_year, cutoff.year + 1):
        for q in range(1,5):
            end = _period_end(year,q)
            if end > cutoff or (year,f'Q{q}') in present:
                continue
            deadline = _disclosure_deadline(year,q)
            if cutoff < deadline:
                status = '等待公告／待取得（未達一般申報期限）'
            else:
                status = '逾期未取得（需官方核對）'
            gaps.append({'缺漏季度':f'{year}Q{q}', '財報截止日':end.date().isoformat(),
                         '一般申報期限參考':deadline.date().isoformat(), '分類':status})
    gap_table = pd.DataFrame(gaps,columns=['缺漏季度','財報截止日','一般申報期限參考','分類'])
    summary['等待公告／待取得季度'] = int(gap_table['分類'].str.startswith('等待公告').sum())
    summary['逾期未取得季度'] = int(gap_table['分類'].str.startswith('逾期未取得').sum())
    summary['來源完整性判斷'] = '有逾期未取得季度，待核對' if summary['逾期未取得季度'] else '無逾期未取得季度（不代表官方查證通過）'
    return summary, gap_table


def build_quarterly_history(records: list[dict], years: int = 5, as_of: str | None = None):
    issues = []
    df = pd.DataFrame(records)
    if df.empty or not {'date','type','value'}.issubset(df.columns):
        return pd.DataFrame(columns=COLUMNS), ['缺少有效財報資料或必要欄位']
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['date','type','value'])
    df = df[df['type'].isin(FIELDS)]
    cutoff = pd.Timestamp(as_of or pd.Timestamp.now(tz='Asia/Taipei').date())
    df = df[(df['date'] <= cutoff) & df['date'].dt.year.between(cutoff.year-years+1,cutoff.year)]
    rows = []
    for period, grp in df.groupby('date'):
        q = QUARTER_ENDS.get((period.month,period.day))
        if q is None:
            issues.append(f'{period.date()}: 非標準季末，排除')
            continue
        row = {'財報截止日':period.date().isoformat(),'年度':period.year,'季度':f'Q{q}',
               'EPS 口徑':'未核實','公告日期':'未核實','估值資格':'禁止自動估值'}
        missing=[]
        for key, name in FIELDS.items():
            vals = grp.loc[grp['type']==key,'value']
            row[name] = float(vals.iloc[0]) if len(vals)==1 else None
            if len(vals)!=1:
                missing.append(f'{name}{"重複" if len(vals)>1 else "缺漏"}')
        row['資料狀態'] = '完整原始科目（未驗證口徑）' if not missing else '；'.join(missing)
        rows.append(row)
    out = pd.DataFrame(rows,columns=COLUMNS)
    if not out.empty:
        out = out.sort_values('財報截止日',ascending=False).reset_index(drop=True)
    _, gaps = inspect_history_quality(out,years=years,as_of=cutoff.date().isoformat())
    if not gaps.empty:
        due = int(gaps['分類'].str.startswith('已過').sum())
        pending = len(gaps)-due
        issues.append(f'未取得季度：{len(gaps)} 季（已過一般申報期限但來源缺漏 {due} 季；尚未達一般期限 {pending} 季）。期限僅供分類參考，非正式公告日。')
    issues.append('財報截止日不等於公告日；原始 EPS 口徑、官方股數未核實，禁止自動估值與歷史時點回測')
    return out, issues
