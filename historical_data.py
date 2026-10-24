"""V4.2-01: point-in-time-safe financial record normalization and validation.

Important: a fiscal period is NOT a public release date. Never infer a release
 date from a month/quarter end when deciding historical availability.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
import pandas as pd

REQUIRED = ('stock_id', 'metric', 'period_end', 'value', 'source', 'published_at')


def normalize_records(records, retrieved_at: Optional[str] = None) -> pd.DataFrame:
    """Normalize records; missing publication timestamps remain unknown (NaT).

    Required input fields: stock_id, metric, period_end, value, source.
    Optional: published_at (actual source-confirmed publication timestamp).
    """
    df = pd.DataFrame(records).copy()
    for name in REQUIRED:
        if name not in df.columns:
            df[name] = None
    if df.empty:
        df['retrieved_at'] = pd.Series(dtype='datetime64[ns, UTC]')
        df['eligible_for_backtest'] = pd.Series(dtype=bool)
        return df
    df['stock_id'] = df['stock_id'].astype('string').str.strip()
    df['metric'] = df['metric'].astype('string').str.strip()
    df['source'] = df['source'].astype('string').str.strip()
    df['period_end'] = pd.to_datetime(df['period_end'], errors='coerce', utc=True)
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['retrieved_at'] = pd.to_datetime(retrieved_at or pd.Timestamp.now(tz='UTC'), utc=True)
    df['eligible_for_backtest'] = (
        df['stock_id'].notna() & df['stock_id'].ne('') &
        df['metric'].notna() & df['metric'].ne('') &
        df['source'].notna() & df['source'].ne('') &
        df['period_end'].notna() & df['published_at'].notna() &
        df['value'].notna() & (df['published_at'] >= df['period_end']) &
        (df['published_at'] <= df['retrieved_at'])
    )
    return df


def as_of_records(records: pd.DataFrame, decision_at: str) -> pd.DataFrame:
    """Return only information confirmed public by the decision timestamp.

    The latest eligible version of a metric/period is retained. Historical
    revisions need their own real published_at timestamps to be replayed.
    """
    decision = pd.to_datetime(decision_at, utc=True)
    if pd.isna(decision):
        raise ValueError('decision_at must be a valid timestamp')
    eligible = records.loc[
        records['eligible_for_backtest'].fillna(False) &
        records['published_at'].le(decision) &
        records['retrieved_at'].ge(records['published_at'])
    ].copy()
    return (eligible.sort_values(['published_at', 'retrieved_at'])
            .drop_duplicates(['stock_id', 'metric', 'period_end'], keep='last')
            .reset_index(drop=True))


def audit_records(records: pd.DataFrame) -> dict:
    total = len(records)
    if not total:
        return {'total': 0, 'eligible': 0, 'missing_publication': 0,
                'invalid_period': 0, 'invalid_value': 0, 'duplicates': 0}
    return {
        'total': total,
        'eligible': int(records['eligible_for_backtest'].sum()),
        'missing_publication': int(records['published_at'].isna().sum()),
        'invalid_period': int(records['period_end'].isna().sum()),
        'invalid_value': int(records['value'].isna().sum()),
        'duplicates': int(records.duplicated(['stock_id', 'metric', 'period_end', 'published_at']).sum()),
    }


def normalize_finmind_month_revenue(data: list, stock_id: str) -> pd.DataFrame:
    """Import FinMind monthly revenue WITHOUT inventing announcement dates.

    FinMind `date` is not assumed to be the actual release timestamp. Only an
    independently confirmed publication field may authorize PIT backtesting.
    """
    rows = []
    for item in data:
        try:
            year, month = int(item['revenue_year']), int(item['revenue_month'])
            period = pd.Period(f'{year}-{month:02d}', freq='M')
            rows.append({'stock_id': str(stock_id), 'metric': 'monthly_revenue',
                         'period_end': period.end_time.date().isoformat(),
                         'value': item.get('revenue'), 'source': 'FinMind:TaiwanStockMonthRevenue',
                         'published_at': None})
        except (KeyError, ValueError, TypeError):
            rows.append({'stock_id': str(stock_id), 'metric': 'monthly_revenue',
                         'period_end': None, 'value': item.get('revenue'),
                         'source': 'FinMind:TaiwanStockMonthRevenue', 'published_at': None})
    return normalize_records(rows)
