"""V4.2-02 scenario valuation. Research calculator, NOT an earnings forecast.

All inputs must be independently sourced/verified by the user. No market data is
silently inferred from the Yahoo Finance metadata or monthly revenue alone.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite

SCENARIOS = ('保守', '基準', '樂觀')

@dataclass(frozen=True)
class ValuationInput:
    annual_revenue: float  # TWD millions
    growth_pct: float
    operating_margin_pct: float
    net_to_operating_pct: float  # net income / operating profit; assumption
    shares_millions: float
    pe: float


def evaluate_scenario(item: ValuationInput) -> dict:
    """One-year forward, simplified, hypothetical model.

    Annual revenue and shares in millions cancel to give EPS in TWD/share.
    net_to_operating_pct is an explicit assumption, not a substitute for tax
    and non-operating items in a full financial forecast.
    """
    values = vars(item)
    if not all(isfinite(float(x)) for x in values.values()):
        raise ValueError('輸入不得為空值、NaN 或無限大')
    if item.annual_revenue <= 0 or item.shares_millions <= 0:
        raise ValueError('營收及流通股數必須大於零')
    if not -100 <= item.growth_pct <= 500:
        raise ValueError('營收成長率超出研究工具允許範圍')
    if not -100 <= item.operating_margin_pct <= 100:
        raise ValueError('營業利益率必須介於 -100% 與 100%')
    if not 0 <= item.net_to_operating_pct <= 200:
        raise ValueError('淨利／營業利益轉換率必須介於 0% 與 200%')
    if not 0 < item.pe <= 100:
        raise ValueError('本益比必須介於 0 與 100 倍')
    revenue = item.annual_revenue * (1 + item.growth_pct / 100)
    operating_profit = revenue * item.operating_margin_pct / 100
    net_profit = operating_profit * item.net_to_operating_pct / 100
    eps = net_profit / item.shares_millions
    # Negative EPS must not be multiplied by PE to claim a valid valuation.
    fair_value = eps * item.pe if eps > 0 else None
    return {'revenue_millions': revenue, 'operating_profit_millions': operating_profit,
            'net_profit_millions': net_profit, 'eps': eps, 'fair_value': fair_value}


def safety_margin(price: float, fair_value: float | None) -> float | None:
    if not isfinite(float(price)) or price <= 0:
        raise ValueError('股價必須大於零')
    if fair_value is None or not isfinite(float(fair_value)) or fair_value <= 0:
        return None
    return (fair_value - price) / fair_value * 100


def validate_scenarios(scenarios: dict) -> list[str]:
    """Warnings rather than silently modifying the user's hypotheses."""
    warnings = []
    if not all(s in scenarios for s in SCENARIOS):
        return ['缺少保守、基準或樂觀情境']
    if not (scenarios['保守'].growth_pct <= scenarios['基準'].growth_pct <= scenarios['樂觀'].growth_pct):
        warnings.append('三情境的營收成長率沒有依保守→基準→樂觀排序')
    if not (scenarios['保守'].operating_margin_pct <= scenarios['基準'].operating_margin_pct <= scenarios['樂觀'].operating_margin_pct):
        warnings.append('三情境的營業利益率沒有依保守→基準→樂觀排序')
    if not (scenarios['保守'].pe <= scenarios['基準'].pe <= scenarios['樂觀'].pe):
        warnings.append('三情境的本益比沒有依保守→基準→樂觀排序')
    return warnings
