"""Fail-closed completeness audit of quarterly EPS candidate evidence.

Does not fetch or independently validate filings, release timestamps or shares.
All output is diagnostic and must not unlock valuation or backtests.
"""
from __future__ import annotations
import pandas as pd

REQUIRED = ('公告日期', 'EPS 口徑', '淨利（已核實）', '加權平均股數（已核實）')
UNKNOWN = {'', '未核實', '未驗證', '未知', '無', 'none', 'nan', 'null', 'n/a'}

def _provided(value):
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() not in UNKNOWN
    return True

def audit_eps_evidence(candidates: pd.DataFrame):
    """Conservative status: even filled-in columns aren't source-verified."""
    rows = []
    for _, record in candidates.iterrows():
        missing = [field for field in REQUIRED if field not in record.index or not _provided(record[field])]
        source_status = str(record.get('官方查詢狀態', ''))
        official_candidate = '找到官方彙總表候選紀錄' in source_status
        if not official_candidate:
            missing.insert(0, '官方候選紀錄')
        rows.append({
            '年度': record.get('年度'), '季度': record.get('季度'),
            '候選資料': '有' if official_candidate else '缺少或不唯一',
            '缺少的核實證據': '、'.join(missing) if missing else '欄位有值，但來源真實性仍未核實',
            '財報驗證狀態': '資料不足' if missing else '待來源核實',
            '可用於歷史時點回測': '否', '自動估值資格': '禁止',
        })
    return pd.DataFrame(rows), [
        '本階段只稽核證據欄位是否具備；不會把 EPS 數值相近視為正式驗證。',
        '公告日期必須有可追溯的正式揭露來源；淨利及加權平均股數必須核對財報原件。即使欄位有值，未查證前仍禁止估值及時點回測。',
    ]
