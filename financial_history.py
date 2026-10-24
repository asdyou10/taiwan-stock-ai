"""Conservative historical FinMind quarterly statement index (not PIT verified)."""
from __future__ import annotations
import pandas as pd

FIELDS = {'EPS': 'EPS 原始值（元）', 'EquityAttributableToOwnersOfParent': '母公司淨利原始值（元）'}
COLUMNS = ['財報截止日','年度','季度',*FIELDS.values(),'資料狀態','EPS 口徑','公告日期','估值資格']

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
    if as_of:
        cutoff = pd.Timestamp(as_of)
        df = df[df['date'] <= cutoff]
        last_year = cutoff.year
    else:
        last_year = pd.Timestamp.today().year
    df = df[df['date'].dt.year.between(last_year-years+1,last_year)]
    quarter_ends = {(3,31):1,(6,30):2,(9,30):3,(12,31):4}
    rows = []
    for period, grp in df.groupby('date'):
        q = quarter_ends.get((period.month,period.day))
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
    expected = [(y,q) for y in range(last_year-years+1,last_year+1) for q in range(1,5)
                if pd.Timestamp(y,q*3,1)+pd.offsets.MonthEnd(0) <= pd.Timestamp(as_of or pd.Timestamp.today().date())]
    present = set(zip(out['年度'],out['季度'])) if not out.empty else set()
    missing_quarters = [f'{y}Q{q}' for y,q in expected if (y,f'Q{q}') not in present]
    if missing_quarters:
        issues.append('缺少季度紀錄（可能尚未公告或來源缺漏）：'+', '.join(missing_quarters))
    issues.append('財報截止日不等於公告日；原始 EPS 口徑、官方股數未核實，禁止自動估值與歷史時點回測')
    return out, issues
