"""Read-only market membership probe using fixed official income-statement datasets.

Membership is evidence of a row in the selected dataset, not authoritative
listing status, historical disclosure verification, or valuation eligibility.
"""
from __future__ import annotations
import csv
import io
import json
from urllib.request import Request, urlopen

SOURCES = {
    '上市｜證交所一般業損益表': ('json', 'https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci'),
    '上櫃｜官方一般業損益表': ('csv', 'https://mopsfin.twse.com.tw/opendata/t187ap06_O_ci.csv'),
}
MAX_BYTES = 8_000_000


def _fetch(kind: str, url: str):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 TaiwanStockAI-readonly', 'Accept': 'application/json,text/csv,*/*'})
    with urlopen(req, timeout=15) as resp:
        raw = resp.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('資料超過 8 MB 安全上限')
    content = raw.decode('utf-8-sig')
    if kind == 'json':
        records = json.loads(content)
    else:
        records = list(csv.DictReader(io.StringIO(content)))
    if not isinstance(records, list) or (records and not isinstance(records[0], dict)):
        raise ValueError('官方資料格式不符預期')
    return records


def inspect_market_sources(stock: str, fetcher=None) -> dict:
    """Run both probes; never infer market solely from a failed request."""
    stock = str(stock).strip()
    if not (stock.isdigit() and 4 <= len(stock) <= 6):
        return {'市場判定': '無法判定', '結果': [], '說明': '股票代號格式不符'}
    fetcher = fetcher or _fetch
    output = []
    for name, (kind, url) in SOURCES.items():
        item = {'資料集': name, '來源': url, '連線': '失敗', '總筆數': None, '符合筆數': 0, '候選資料': [], '錯誤': ''}
        try:
            records = fetcher(kind, url)
            item['連線'] = '成功'
            item['總筆數'] = len(records)
            matched = [r for r in records if str(r.get('公司代號', '')).strip() == stock]
            item['符合筆數'] = len(matched)
            item['候選資料'] = matched[:2]
        except Exception as exc:
            item['錯誤'] = f'{type(exc).__name__}: {str(exc)[:180]}'
        output.append(item)
    if any(r['連線'] != '成功' for r in output):
        market = '無法判定（部分官方來源連線失敗）'
    elif output[0]['符合筆數'] and not output[1]['符合筆數']:
        market = '上市（一般業資料集候選）'
    elif output[1]['符合筆數'] and not output[0]['符合筆數']:
        market = '上櫃（一般業資料集候選）'
    elif output[0]['符合筆數'] and output[1]['符合筆數']:
        market = '資料衝突，需人工核實'
    else:
        market = '無法判定（兩個一般業資料集皆無資料）'
    return {'市場判定': market, '結果': output, '說明': '此為目前一般業財報資料集的代號比對；不代表正式市場別認證、歷史公告日、EPS 口徑或加權平均股數已驗證。'}
