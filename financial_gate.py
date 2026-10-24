"""V4.2-04 stage 1: conservative automated valuation eligibility audit.

This is a readiness report, NOT official disclosure verification or a valuation engine.
No combination of manually entered fields can unlock automatic valuation.
"""
from __future__ import annotations
import math
import pandas as pd


def audit_valuation_readiness(income: pd.DataFrame | None,
                              periods: pd.DataFrame | None,
                              evidence: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    checks: list[tuple[str, str, str]] = []
    def add(name: str, ok: bool, explanation: str):
        checks.append((name, '已有資料（未核實）' if ok else '缺少／未核實', explanation))

    raw_ok = income is not None and not income.empty and {'date','type','value'}.issubset(income.columns)
    add('損益表原始資料', raw_ok, 'FinMind 原始科目僅供核對，非官方公告驗證')
    periods_ok = periods is not None and not periods.empty and '財報截止日' in periods.columns
    add('財報期間', periods_ok, '截止日不等於實際公告日')
    eps_ok = False
    profit_ok = False
    if raw_ok:
        numeric = pd.to_numeric(income['value'], errors='coerce')
        types = income['type'].astype(str)
        eps_ok = bool(((types == 'EPS') & numeric.map(math.isfinite)).any())
        profit_ok = bool(((types == 'EquityAttributableToOwnersOfParent') & numeric.map(math.isfinite)).any())
    add('EPS 原始科目', eps_ok, '尚未驗證單季、累計或年度口徑')
    add('母公司淨利原始科目', profit_ok, '尚未與相同期間 EPS 交叉核對')
    add('正式公告日期', False, '尚未連接可獨立核實的官方公告日期資料源')
    add('EPS 期間口徑', False, '不能依 FinMind 財報截止日自動推斷')
    add('官方加權平均股數', False, '淨利／EPS 推得的隱含股數不能代替官方股數')
    manual_ok = bool(evidence and evidence.get('格式與時點檢查', '').startswith('通過'))
    add('人工佐證格式', manual_ok, '即使格式通過，仍未驗證來源真偽及公告內容')
    add('歷史時點可用性', False, '尚未建立經驗證的逐筆公告發布時間紀錄')
    add('合理本益比依據', False, '尚未建立產業估值依據與情境校準')
    rows = pd.DataFrame(checks, columns=['檢查項目', '目前狀態', '說明'])
    reasons = [f'{name}：{desc}' for name, state, desc in checks if state == '缺少／未核實']
    return rows, reasons
