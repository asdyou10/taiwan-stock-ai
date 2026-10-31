"""V4.2 conservative independent verification of documented official filings.

This module DOES NOT scrape filings or certify user-supplied evidence as official.
Only an externally verified, timestamped official filing may be marked verified.
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

OFFICIAL_HOSTS = {'mops.twse.com.tw', 'mopsov.twse.com.tw', 'openapi.twse.com.tw'}


def _decimal(value):
    try:
        d = Decimal(str(value).replace(',', '').strip())
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def validate_quarter(stock, year, quarter, finmind_eps, evidence, tolerance='0.02'):
    """Fail-closed validation; evidence is NOT certified by entering a URL.

    evidence keys: stock, year, quarter, url, announced_at, eps_basis,
    eps, net_income, weighted_shares, verified_source.
    """
    problems = []
    if not isinstance(evidence, dict):
        evidence = {}
    if str(evidence.get('stock', '')) != str(stock):
        problems.append('官方證據股票代號不符')
    if str(evidence.get('year', '')) != str(year) or str(evidence.get('quarter', '')).upper().replace('Q','') != str(quarter).upper().replace('Q',''):
        problems.append('官方證據年度／季度不符')
    try:
        url = urlsplit(str(evidence.get('url', '')))
        if url.scheme != 'https' or (url.hostname or '').lower() not in OFFICIAL_HOSTS or url.username or url.password or url.port not in (None, 443):
            problems.append('未提供有效官方來源網址')
    except ValueError:
        problems.append('官方來源網址無效')
    q = int(str(quarter).upper().replace('Q', '')) if str(quarter).upper().replace('Q','').isdigit() else 0
    y = int(year) if str(year).isdigit() else 0
    end = date(y, q * 3, 1) if y >= 1912 and q in (1,2,3,4) else None
    announced = _date(evidence.get('announced_at'))
    if not announced or not end or announced <= end:
        problems.append('缺少有效的實際財報公告日期')
    if evidence.get('eps_basis') != 'single_quarter':
        problems.append('官方 EPS 尚未確認為同口徑單季數字')
    official_eps, other_eps, tol = _decimal(evidence.get('eps')), _decimal(finmind_eps), _decimal(tolerance)
    if official_eps is None or other_eps is None or tol is None or tol < 0:
        problems.append('EPS 數字缺漏或無效')
    elif abs(official_eps - other_eps) > tol:
        problems.append('EPS 超過容許差異')
    if _decimal(evidence.get('net_income')) is None:
        problems.append('官方母公司淨利尚未核對')
    shares = _decimal(evidence.get('weighted_shares'))
    if shares is None or shares <= 0:
        problems.append('官方加權平均股數尚未核對')
    # No UI/manual input can turn verified_source True: require independent document verification.
    if evidence.get('verified_source') is not True:
        problems.append('尚未獨立驗證官方財報原件與公告時間')
    return {'狀態': '待核實' if problems else '數值核對通過（仍須審核證據取得流程）',
            '問題': problems, '可用於自動估值': False,
            '官方公告日期': announced.isoformat() if announced else None}
