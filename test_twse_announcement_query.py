
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://dsp.twse.com.tw/official/search"
RESULT_URL = "https://dsp.twse.com.tw/official/result"

with requests.Session() as session:
    # 先取得官方查詢頁面及動態 Token
    response = session.get(SEARCH_URL, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", id="form_others")

    if form is None:
        raise RuntimeError("找不到官方分類查詢表單")

    token_input = form.find("input", attrs={"name": "SYNCHRONIZER_TOKEN"})
    uri_input = form.find("input", attrs={"name": "SYNCHRONIZER_URI"})

    if token_input is None or uri_input is None:
        raise RuntimeError("找不到必要的表單驗證欄位")

    data = {
        "SYNCHRONIZER_TOKEN": token_input.get("value", ""),
        "SYNCHRONIZER_URI": uri_input.get("value", ""),
        "queryby": "others",
        "kind": "j",
    }

    # 送出官方「市場休市」分類查詢
    result = session.post(RESULT_URL, data=data, timeout=15)
    result.raise_for_status()

    page = BeautifulSoup(result.text, "html.parser")

    print("HTTP:", result.status_code)
    print("結果網址:", result.url)
    print("頁面標題:", page.title.get_text(strip=True) if page.title else "無")
    print("表格數量:", len(page.find_all("table")))
    print("PDF連結數量:", len(page.select('a[href$=".pdf"]')))
    print("頁面文字預覽:")
    print(page.get_text(" ", strip=True)[:500])
