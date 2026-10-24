"""Read-only official/FinMind quarter alignment. No valuation eligibility is granted."""
from __future__ import annotations
import pandas as pd
from financial_eps_period_probe import inspect_official_eps_period

COLS = ['財報季度','FinMind EPS（元）','官方 EPS 原始值（元）','官方資料來源','配對狀態','EPS 數值比較','母公司淨利比較','可信度','說明']


def _float(value):
    try:
        number = float(value)
        return number if pd.notna(number) else None
    except (ValueError, TypeError):
        return None


def crosscheck_financial_sources(stock: str, history: pd.DataFrame, official_result: dict | None = None):
    """Pair by fiscal year and quarter; compare only after verified accounting basis (not yet available)."""
    official_result = official_result if official_result is not None else inspect_official_eps_period(stock)
    warnings = list(official_result.get('錯誤', []))
    raw = official_result.get('紀錄', [])
    matches = {}
    for item in raw:
        try:
            year = int(str(item.get('年度（民國）', '')).strip()) + 1911
            q = int(str(item.get('季別', '')).strip().replace('Q',''))
            if q not in (1,2,3,4):
                continue
            matches.setdefault((year, q), []).append(item)
        except (ValueError, TypeError):
            warnings.append('官方資料含無法解析的年度或季別，已排除')
    if history is None or history.empty:
        return pd.DataFrame(columns=COLS), warnings + ['請先讀取 FinMind 歷史季度財報']
    rows = []
    for _, h in history.iterrows():
        try:
            year = int(h['年度'])
            quarter = int(str(h['季度']).replace('Q',''))
        except (KeyError, ValueError, TypeError):
            warnings.append('FinMind 歷史季度格式不符，已略過')
            continue
        candidates = matches.get((year, quarter), [])
        fin_eps = _float(h.get('EPS 原始值（元）'))
        if len(candidates) == 1:
            official = candidates[0]
            official_eps = _float(official.get('官方EPS原始值（元）'))
            match_state = '同公司／年度／季度已配對'
            explanation = 'EPS 單季／累計及股數基準未核實，不能判定兩來源數值是否一致'
        elif len(candidates) > 1:
            official = None
            official_eps = None
            match_state = '官方候選重複／衝突'
            explanation = '同一季度存在多筆官方候選，需先排除重複或資料集差異'
        else:
            official = None
            official_eps = None
            match_state = '無同季官方候選'
            explanation = '官方即時資料集可能僅涵蓋最新季度，不代表歷史資料不存在'
        rows.append({'財報季度': f'{year}Q{quarter}', 'FinMind EPS（元）': fin_eps,
                     '官方 EPS 原始值（元）': official_eps,
                     '官方資料來源': official.get('官方來源','') if official else '',
                     '配對狀態': match_state,
                     'EPS 數值比較': '暫緩：口徑與股數基準未核實',
                     '母公司淨利比較': '暫緩：官方欄位定義／單位與期間口徑未核實',
                     '可信度': '待核實／禁止自動估值', '說明': explanation})
    warnings.extend(['官方資料集可能僅提供最新一期；歷史季度未配對不等於財報不存在。',
                     '財報截止日不是正式公告日，不能將這些資料用於未驗證的歷史時點回測。',
                     '尚未取得同口徑 EPS、官方公告日期及加權平均股數的完整證據，禁止自動估值。'])
    return pd.DataFrame(rows, columns=COLS), warnings
