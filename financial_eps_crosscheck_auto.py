"""Read-only, fail-closed historical EPS convention diagnostic.

A MOPS quarterly income-statement summary often reports year-to-date EPS, but
this module does NOT infer the actual filing convention from numerical matches.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import pandas as pd
from financial_mops_history import query_historical_income
from financial_auto import fetch_dataset


def _number(raw):
    try:
        value = Decimal(str(raw).strip().replace(',', ''))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _finmind_eps(records, year):
    """Only unique EPS observations on exact quarter-end dates; no convention assumed."""
    values = {}
    for rec in records:
        if rec.get('type') != 'EPS':
            continue
        date = str(rec.get('date', ''))[:10]
        for quarter, ending in enumerate(('03-31', '06-30', '09-30', '12-31'), 1):
            if date == f'{year}-{ending}':
                values.setdefault(quarter, []).append(_number(rec.get('value')))
    return {q: vals[0] if len(vals) == 1 else None for q, vals in values.items()}


def build_eps_diagnostic(stock, year, market, official_fetch=query_historical_income, finmind_fetch=fetch_dataset, token=''):
    """Fetch 4 official quarters and FinMind EPS; output candidates, never validation."""
    if not (str(stock).isdigit() and 4 <= len(str(stock)) <= 6 and 2013 <= int(year) <= 2100 and market in ('上市','上櫃')):
        raise ValueError('股票、年度或市場別無效')
    year = int(year)
    notices = []
    try:
        records = finmind_fetch(str(stock), 'TaiwanStockFinancialStatements', f'{year}-01-01', token)
        finmind = _finmind_eps(records, year)
    except Exception as exc:
        finmind = {}
        notices.append(f'FinMind 讀取失敗：{type(exc).__name__}: {str(exc)[:120]}')
    rows = []
    prev = None
    for q in range(1, 5):
        try:
            response = official_fetch(str(stock), year, q, market)
        except Exception as exc:
            response = {'狀態':f'查詢失敗：{type(exc).__name__}', '紀錄':[]}
        matches = response.get('紀錄') or []
        raw = _number(matches[0].get('EPS 原始文字')) if len(matches) == 1 else None
        # Hypothetical only: EPS differences can diverge from standalone EPS
        # due to weighted average share counts, rounding and restatements.
        standalone = raw - prev if raw is not None and prev is not None and q > 1 else (raw if q == 1 else None)
        fm = finmind.get(q)
        difference = abs(standalone - fm) if standalone is not None and fm is not None else None
        rows.append({
            '年度':year, '季度':f'Q{q}',
            '官方彙總表 EPS 候選值':float(raw) if raw is not None else None,
            '假設年初累計口徑換算值':float(standalone) if standalone is not None else None,
            'FinMind EPS 原始值':float(fm) if fm is not None else None,
            '兩者差額（絕對值）':float(difference) if difference is not None else None,
            '比對提示': ('無法比較' if difference is None else '數值接近（不代表口徑已驗證）' if difference <= Decimal('0.02') else '數值差異，需查核'),
            '官方查詢狀態':response.get('狀態','未知'),
            'EPS 口徑':'未核實', '公告日期':'未核實', '估值資格':'禁止自動估值',
        })
        prev = raw  # Missing prior quarter means no inferred standalone value.
    notices.append('單季換算欄只是假設官方 EPS 為年初累計時的算術差值；非已驗證單季 EPS。')
    notices.append('EPS 可能因加權平均股數、四捨五入或重編而無法直接相減；數值相近不能證明期間口徑。')
    notices.append('未核實正式公告日期、財報原件、淨利與加權平均股數；一律禁止自動估值及歷史時點回測。')
    return pd.DataFrame(rows), notices
