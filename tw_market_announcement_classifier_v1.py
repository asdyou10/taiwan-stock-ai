
SCHEDULED_KEYWORDS = (
    "國定假日",
    "春節",
    "農曆新年",
    "例行休市",
    "補假",
    "和平紀念日",
    "端午節",
    "中秋節",
    "清明節",
    "休市日程",
)

EMERGENCY_KEYWORDS = (
    "颱風",
    "台風",
    "地震",
    "天然災害",
    "緊急停市",
    "臨時停市",
    "停止交易",
    "暫停交易",
)


def classify_announcement(announcement):
    """依公告主旨進行初步分類，不確認實際停市狀態。"""

    result = {
        "category": "UNKNOWN",
        "source_verified": False,
        "status": "UNKNOWN",
        "matched_keywords": [],
    }

    if not isinstance(announcement, dict):
        return result

    subject = announcement.get("subject")

    if not isinstance(subject, str) or not subject.strip():
        return result

    emergency_matches = [
        keyword
        for keyword in EMERGENCY_KEYWORDS
        if keyword in subject
    ]

    scheduled_matches = [
        keyword
        for keyword in SCHEDULED_KEYWORDS
        if keyword in subject
    ]

    
    # 明確表示正常交易、不停市的公告，
    # 不應僅因出現颱風等關鍵字就被標記為緊急停市。
    no_closure_phrases = (
        "不實施緊急停市",
        "不實施臨時停市",
        "正常交易，不停市",
        "正常交易，照常開市",
        "照常開市",
    )

    
    # 如果公告同時包含正常開市與後續緊急停市，
    # 不可直接排除整則公告。
    later_emergency_phrases = (
        "後續因",
        "後續宣布",
        "改為緊急停市",
        "改為臨時停市",
    )

    has_later_emergency = (
        any(phrase in subject for phrase in later_emergency_phrases)
        and any(
            phrase in subject
            for phrase in ("緊急停市", "臨時停市")
        )
    )

    if (
        any(phrase in subject for phrase in no_closure_phrases)
        and not has_later_emergency
    ):
        return result



    # 個股因重大訊息暫停交易，不代表全市場停市。
    individual_stock_terms = (
        "上市公司",
        "上櫃公司",
        "個股",
        "單一股票",
    )

    individual_stock_event = (
        any(term in subject for term in individual_stock_terms)
        and "重大訊息" in subject
        and "暫停交易" in subject
    )

    
    # 只有在沒有明確全市場緊急訊號時，
    # 才排除個股重大訊息暫停交易事件。
    market_emergency_terms = (
        "全市場",
        "集中交易市場",
        "緊急停市",
        "臨時停市",
        "颱風",
        "台風",
        "地震",
        "天然災害",
    )

    has_market_emergency_signal = any(
        term in subject for term in market_emergency_terms
    )

    if individual_stock_event and not has_market_emergency_signal:
        return result


    # 優先標記疑似緊急事件，避免漏掉風險訊號。
    if emergency_matches:

        result["category"] = "EMERGENCY_CANDIDATE"
        result["matched_keywords"] = emergency_matches

    elif scheduled_matches:
        result["category"] = "SCHEDULED"
        result["matched_keywords"] = scheduled_matches

    return result
