"""Explain source currency under the project's explicit five-day lag assumption."""
import calendar
from datetime import date, timedelta


def _shift_month(month: date, count: int) -> date:
    index = month.year * 12 + month.month - 1 + count
    return date(index // 12, index % 12 + 1, 1)


def assess(last_source_month: str, today: date, assumed_lag_days: int = 5,
           retrieved_at: str | None = None) -> dict:
    source = date.fromisoformat(last_source_month + '-01')
    if assumed_lag_days < 0:
        raise ValueError('assumed_lag_days must be nonnegative')
    next_month = _shift_month(source, 1)
    due = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1]) + timedelta(days=assumed_lag_days)
    remaining = (due - today).days
    status = 'STALE' if remaining < 0 else 'DUE' if remaining <= 7 else 'FRESH'
    return dict(last_source_month=last_source_month,
                next_target_month_supported=_shift_month(source, 2).strftime('%Y-%m'),
                days_until_stale=remaining, status=status, retrieved_at=retrieved_at,
                availability_basis=f'Month end + {assumed_lag_days} days is assumed, not a verified publication timestamp.')
