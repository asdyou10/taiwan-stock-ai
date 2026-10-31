"""Read-only MOPS historical income-statement *candidate* lookup.

MOPS legacy HTML endpoints may change or block automated requests. A returned
row is NOT an independently verified filing, filing date or EPS convention.
Fail closed: never authorizes valuation.
"""
from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import re

ENDPOINT = 'https://mopsov.twse.com.tw/mops/web/ajax_t163sb04'
FALLBACK_ENDPOINT = 'https://mops.twse.com.tw/mops/web/ajax_t163sb04'
MARKETS = {'上市': 'sii', '上櫃': 'otc'}

class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []; self.table = None; self.row = None; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table = []; self.tables.append(self.table)
        elif self.table is not None and tag == 'tr':
            self.row = []; self.table.append(self.row)
        elif self.row is not None and tag in ('td','th'):
            self.cell = []; self.row.append('')
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row[-1] = re.sub(r'\s+', ' ', ''.join(self.cell)).strip(); self.cell = None
        elif tag == 'tr':
            self.row = None
        elif tag == 'table':
            self.table = None

def _download(market, roc_year, quarter, endpoint=ENDPOINT):
    form = {'encodeURIComponent':'1','step':'1','firstin':'1','off':'1','isQuery':'Y',
            'TYPEK':market,'year':str(roc_year),'season':f'{quarter:02d}'}
    request = Request(endpoint, data=urlencode(form).encode('ascii'), headers={
        'User-Agent':'Mozilla/5.0 (compatible; TaiwanStockResearch/1.0)',
        'Content-Type':'application/x-www-form-urlencoded',
        'Referer':endpoint.replace('ajax_t163sb04', 't163sb04')})
    with urlopen(request, timeout=15) as response:
        data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('官方回應超過大小限制')
        encoding = response.headers.get_content_charset() or 'utf-8'
        return data.decode(encoding, errors='replace')

def query_historical_income(stock: str, year: int, quarter: int, market: str, fetcher=None):
    """Returns source-attributed raw values only, not verified financial evidence."""
    stock = str(stock).strip()
    try:
        year, quarter = int(year), int(quarter)
    except (ValueError, TypeError):
        return {'狀態':'參數錯誤','原因':'年度或季度無效','紀錄':[],'可用於自動估值':False}
    if not (stock.isdigit() and 4 <= len(stock) <= 6 and 2013 <= year <= 2100 and quarter in (1,2,3,4) and market in MARKETS):
        return {'狀態':'參數錯誤','原因':'股票代號、年度、季度或市場別無效','紀錄':[],'可用於自動估值':False}
    result = {'狀態':'未取得','股票':stock,'年度':year,'季度':f'Q{quarter}',
              '市場':market,'來源':ENDPOINT,'紀錄':[],'可用於自動估值':False,
              '限制':'官方彙總表候選值；尚未核對財報原件、公告日期、EPS 單季／累計及股數。'}
    try:
        html = (fetcher or _download)(MARKETS[market], year-1911, quarter)
        if not isinstance(html, str):
            raise ValueError('回應不是 HTML 文字')
        parser = _Tables(); parser.feed(html)
        for table in parser.tables:
            for i, row in enumerate(table):
                if not row or not any('公司代號' in x for x in row):
                    continue
                headers = row
                code_index = next((j for j,x in enumerate(headers) if '公司代號' in x), None)
                eps_index = next((j for j,x in enumerate(headers) if '基本每股盈餘' in x), None)
                if code_index is None or eps_index is None:
                    continue
                for record in table[i+1:]:
                    if len(record) <= max(code_index,eps_index):
                        continue
                    if record[code_index].strip() == stock:
                        result['紀錄'].append({'股票代號':stock,'年度':year,'季度':f'Q{quarter}',
                            'EPS 原始文字':record[eps_index], 'EPS 欄名':headers[eps_index],
                            '來源':ENDPOINT,'EPS 口徑':'未核實','公告日期':'未核實'})
        if len(result['紀錄']) == 1:
            result['狀態']='找到官方彙總表候選紀錄（尚未驗證）'
        elif len(result['紀錄']) > 1:
            result['狀態']='找到多筆候選紀錄（需人工排除衝突）'
        else:
            result['狀態']='未找到候選紀錄'
            result['原因']='可能是網站格式改變、資料未提供、公司市場別不符或存取受限；不能推定財報不存在'
    except Exception as exc:
        result['狀態']='查詢失敗'
        result['原因']=f'{type(exc).__name__}: {str(exc)[:160]}'
    return result
