"""Conservative, read-only historical MOPS disclosure-date discovery.

A date returned here is a CANDIDATE, never a verified filing timestamp.
The MOPS interface may change. No fallback to statutory deadlines or quarter ends.
"""
from __future__ import annotations
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import re

URL = 'https://mopsov.twse.com.tw/mops/web/ajax_t163sb01'
MARKET = {'上市': 'sii', '上櫃': 'otc'}
DATE_FIELDS = ('公告日期時間', '公告日期', '申報日期時間', '申報日期', '上傳日期時間', '上傳日期')

class _HTMLTables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []; self.table = None; self.row = None; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table = []; self.tables.append(self.table)
        elif tag == 'tr' and self.table is not None:
            self.row = []; self.table.append(self.row)
        elif tag in ('th', 'td') and self.row is not None:
            self.cell = []; self.row.append('')
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('th', 'td') and self.cell is not None:
            self.row[-1] = re.sub(r'\s+', ' ', ''.join(self.cell)).strip(); self.cell = None
        elif tag == 'tr':
            self.row = None
        elif tag == 'table':
            self.table = None

def _fetch(market, roc_year, quarter):
    form = {'encodeURIComponent':'1', 'step':'1', 'firstin':'1', 'off':'1',
            'isQuery':'Y', 'TYPEK':MARKET[market], 'year':str(roc_year),
            'season':f'{quarter:02d}'}
    request = Request(URL, data=urlencode(form).encode('ascii'), headers={
        'User-Agent':'Mozilla/5.0', 'Content-Type':'application/x-www-form-urlencoded',
        'Referer':URL.replace('ajax_t163sb01', 't163sb01')})
    with urlopen(request, timeout=12) as response:
        payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError('回應超過限制')
        return payload.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')

def _parse_date(raw):
    raw = str(raw).strip()
    match = re.fullmatch(r'(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?', raw)
    if not match:
        return None
    y, m, d, hh, mm, ss = match.groups()
    y = int(y) + (1911 if len(y) <= 3 else 0)
    try:
        return datetime(y, int(m), int(d), int(hh or 0), int(mm or 0), int(ss or 0)).isoformat(sep=' ')
    except ValueError:
        return None

def lookup_announcement_candidate(stock, year, quarter, market, fetcher=None):
    result = {'狀態':'無法確認公告日期', '公告日期候選':'未取得', '來源':URL,
              '核實狀態':'未核實', '可用於回測':False, '可用於估值':False}
    if not (str(stock).isdigit() and 4 <= len(str(stock)) <= 6 and
            isinstance(year, int) and 2013 <= year <= 2100 and
            quarter in (1, 2, 3, 4) and market in MARKET):
        result['狀態'] = '參數錯誤'; return result
    # t163sb01 is a financial summary table, not an authoritative filing timestamp feed.
    # Do not silently treat an absent date column as a missing filing.
    # Preserve injected fetcher support for offline parser tests only.
    if fetcher is None:
        result['狀態'] = '資料來源不適用：財報彙總表未提供可核實的申報時間；需改接財報公告紀錄'
        result['來源限制'] = 't163sb01 僅供彙總財報查詢，不能作為歷史公告時間證據'
        return result
    try:
        html = (fetcher or _fetch)(market, year-1911, quarter)
        parser = _HTMLTables(); parser.feed(html)
        matches = []
        for table in parser.tables:
            for i, header in enumerate(table):
                code_col = next((j for j, v in enumerate(header) if '公司代號' in v), None)
                date_col = next((j for j, v in enumerate(header) if any(x in v for x in DATE_FIELDS)), None)
                if code_col is None or date_col is None:
                    continue
                for row in table[i+1:]:
                    if len(row) <= max(code_col, date_col) or row[code_col].strip() != str(stock):
                        continue
                    parsed = _parse_date(row[date_col])
                    if parsed:
                        matches.append((parsed, header[date_col]))
        matches = list(set(matches))
        if len(matches) == 1:
            result.update({'狀態':'找到單筆公告日期候選（尚未核實所屬財報及版本）',
                           '公告日期候選':matches[0][0], '日期欄名':matches[0][1]})
        elif len(matches) > 1:
            result['狀態'] = '多筆日期候選，無法唯一判定'
        else:
            result['狀態'] = '未找到可辨識的官方日期欄位／紀錄'
    except Exception as exc:
        result['狀態'] = f'官方查詢失敗：{type(exc).__name__}: {str(exc)[:100]}'
    return result
