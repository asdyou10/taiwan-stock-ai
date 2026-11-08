
# 台股臨時停市 V3
# 第一階段：官方公告來源設定
# 目前不連線、不抓取公告、不判定實際休市

OFFICIAL_SOURCES = {
    "TWSE": {
        "name": "臺灣證券交易所",
        "url": "https://dsp.twse.com.tw/official/search",
        "source_type": "official_announcement_page",
    },
  
"TPEX": {
    "name": "證券櫃檯買賣中心",
    "url": "https://www.tpex.org.tw/zh-tw/index.html",
    "source_type": "official_website",
},

}


def get_emergency_source(market):
    """取得官方公告來源設定，不代表已查證公告。"""

    result = {
        "market": market,
        "status": "UNKNOWN",
        "source_url": None,
        "source_verified": False,
        "errors": [],
    }

    if not isinstance(market, str):
        result["errors"].append("市場代碼必須是文字")
        return result

    market_code = market.strip().upper()

    if market_code not in OFFICIAL_SOURCES:
        result["errors"].append("不支援的市場代碼")
        return result

    source = OFFICIAL_SOURCES[market_code]

    result["market"] = (
        "TPEx" if market_code == "TPEX" else "TWSE"
    )
    result["source_url"] = source["url"]

    return result

def check_official_connection(market):
    """檢查官方網站是否可連線，不驗證公告內容。"""

    import requests

    result = get_emergency_source(market)
    result["connection_ok"] = False
    result["http_status"] = None

    # 市場代碼不正確時，不進行網路連線
    if result["errors"]:
        return result

    try:
        response = requests.get(
            result["source_url"],
            timeout=10,
            allow_redirects=False,
        )

        result["http_status"] = response.status_code

        if response.status_code == 200:
            result["connection_ok"] = True
        else:
            result["errors"].append(
                f"官方網站回應狀態：{response.status_code}"
            )

    except requests.RequestException as error:
        result["errors"].append(
            f"官方網站連線失敗：{type(error).__name__}"
        )

    # 網站可連線，不代表公告已核實
    result["status"] = "UNKNOWN"
    result["source_verified"] = False

    return result

def check_official_connection(market):
    """檢查官方網站是否可連線，不驗證公告內容。"""

    import requests

    result = get_emergency_source(market)
    result["connection_ok"] = False
    result["http_status"] = None

    # 市場代碼不正確時，不進行網路連線
    if result["errors"]:
        return result

    try:
        response = requests.get(
            result["source_url"],
            timeout=10,
            allow_redirects=False,
        )

        result["http_status"] = response.status_code

        if response.status_code == 200:
            result["connection_ok"] = True
        else:
            result["errors"].append(
                f"官方網站回應狀態：{response.status_code}"
            )

    except requests.RequestException as error:
        result["errors"].append(
            f"官方網站連線失敗：{type(error).__name__}"
        )

    # 網站可連線，不代表公告已核實
    result["status"] = "UNKNOWN"
    result["source_verified"] = False

    return result


def check_official_connection(market):
    """檢查官方網站是否可連線，不驗證公告內容。"""

    import requests

    result = get_emergency_source(market)
    result["connection_ok"] = False
    result["http_status"] = None

    # 市場代碼不正確時，不進行網路連線
    if result["errors"]:
        return result

    try:
        response = requests.get(
            result["source_url"],
            timeout=10,
            allow_redirects=False,
        )

        result["http_status"] = response.status_code

        if response.status_code == 200:
            result["connection_ok"] = True
        else:
            result["errors"].append(
                f"官方網站回應狀態：{response.status_code}"
            )

    except requests.RequestException as error:
        result["errors"].append(
            f"官方網站連線失敗：{type(error).__name__}"
        )

    # 網站可連線，不代表公告已核實
    result["status"] = "UNKNOWN"
    result["source_verified"] = False

    return result


def check_official_connection(market):
    """檢查官方網站是否可連線，不驗證公告內容。"""

    import requests

    result = get_emergency_source(market)
    result["connection_ok"] = False
    result["http_status"] = None

    # 市場代碼不正確時，不進行網路連線
    if result["errors"]:
        return result

    try:
        response = requests.get(
            result["source_url"],
            timeout=10,
            allow_redirects=False,
        )

        result["http_status"] = response.status_code

        if response.status_code == 200:
            result["connection_ok"] = True
        else:
            result["errors"].append(
                f"官方網站回應狀態：{response.status_code}"
            )

    except requests.RequestException as error:
        result["errors"].append(
            f"官方網站連線失敗：{type(error).__name__}"
        )

    # 網站可連線，不代表公告已核實
    result["status"] = "UNKNOWN"
    result["source_verified"] = False

    return result



def check_official_connection(market):
    """檢查官方網站是否可連線，不驗證公告內容。"""

    import requests

    result = get_emergency_source(market)
    result["connection_ok"] = False
    result["http_status"] = None

    # 市場代碼不正確時，不進行網路連線
    if result["errors"]:
        return result

    try:
        response = requests.get(
            result["source_url"],
            timeout=10,
            allow_redirects=False,
        )

        result["http_status"] = response.status_code

        if response.status_code == 200:
            result["connection_ok"] = True
        else:
            result["errors"].append(
                f"官方網站回應狀態：{response.status_code}"
            )

    except requests.RequestException as error:
        result["errors"].append(
            f"官方網站連線失敗：{type(error).__name__}"
        )

    # 網站可連線，不代表公告已核實
    result["status"] = "UNKNOWN"
    result["source_verified"] = False

    return result
