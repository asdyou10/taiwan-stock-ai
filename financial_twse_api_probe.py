"""Read-only, on-demand TWSE OpenAPI connectivity and field diagnostics.

Does not authenticate historical disclosures or permit automated valuation.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ENDPOINTS = {
    '上市公司綜合損益表（一般業）': 'https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci',
    '上市公司資產負債表（一般業）': 'https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci',
    '上市公司重大訊息': 'https://openapi.twse.com.tw/v1/opendata/t187ap04_L',
}
MAX_BYTES = 6_000_000

def probe_twse_api(stock: str, endpoint_name: str) -> dict:
    """Fetch one fixed official URL and show evidence/limitations, without claiming verification."""
    if endpoint_name not in ENDPOINTS:
        return {'狀態': '拒絕', '說明': '未知資料集', '欄位': [], '候選紀錄': []}
    stock = str(stock).strip()
    if not (stock.isdigit() and 4 <= len(stock) <= 6):
        return {'狀態': '拒絕', '說明': '股票代號格式不符', '欄位': [], '候選紀錄': []}
    url = ENDPOINTS[endpoint_name]
    try:
        request = Request(url, headers={'User-Agent': 'TaiwanStockAI/1.0 (read-only diagnostic)', 'Accept': 'application/json'})
        with urlopen(request, timeout=12) as response:
            content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError('回傳資料超過診斷上限（6 MB）')
            payload = json.loads(content.decode('utf-8-sig'))
        if not isinstance(payload, list):
            raise ValueError('API 回傳不是預期的 JSON 陣列')
        sample = next((x for x in payload if isinstance(x, dict)), {})
        fields = list(sample.keys())[:100]
        # Matching is heuristic and must never be treated as verified identity.
        keys = [k for k in fields if any(token in k.lower() for token in ('公司代號', '證券代號', '股票代號', 'stockcode', 'companycode', 'code'))]
        matches = [row for row in payload if isinstance(row, dict) and any(str(row.get(k, '')).strip() == stock for k in keys)]
        return {
            '狀態': '連線成功', '說明': '已取得官方 API 回傳；欄位與候選資料僅供人工檢視，並非逐期公告核實',
            '來源': url, '總紀錄數': len(payload), '欄位': fields, '代號欄位候選': keys,
            '候選紀錄數': len(matches), '候選紀錄': matches[:2],
            '限制': '未驗證歷史公告日、EPS 單季/累計口徑或加權平均股數；不可解鎖自動估值。',
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        return {'狀態': '查詢失敗', '說明': f'{type(exc).__name__}: {str(exc)[:220]}', '來源': url, '欄位': [], '候選紀錄': [],
                '限制': '官方 API 無法取得或解析，不影響既有財報與估值安全攔截。'}
