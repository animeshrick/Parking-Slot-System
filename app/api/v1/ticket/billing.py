"""
Pure billing logic. No DB, no FastAPI — easy to unit-test and
swap for a more sophisticated rule (tiered, weekend, etc.) later.
"""
import math
from datetime import datetime


def compute_fee(
    entry_time: datetime,
    exit_time: datetime,
    rate_per_hour: int,
    grace_minutes: int,
) -> int:
    """
    Fee rules:
      - If total duration is strictly less than `grace_minutes`, fee = 0.
      - Otherwise bill the ceiling of the elapsed hours at `rate_per_hour`.
        (30 minutes past the grace period still bills as 1 full hour.)

    Returns an integer rupee amount.
    """
    if exit_time < entry_time:
        # Defensive: clock skew or bad input. Treat as zero duration.
        return 0

    total_seconds = (exit_time - entry_time).total_seconds()

    if total_seconds < grace_minutes * 60:
        return 0

    hours = math.ceil(total_seconds / 3600)
    return hours * rate_per_hour
