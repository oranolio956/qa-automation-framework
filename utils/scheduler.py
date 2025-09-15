#!/usr/bin/env python3
"""
Circadian scheduler and warm-up caps.

Provides:
- is_within_user_window(user_id): respects quiet hours per region/tenant
- get_daily_caps(user_id): per-day cap and ramp schedule
"""

import os
import time
from datetime import datetime, timedelta
from typing import Tuple


def _get_timezone_offset_minutes(region: str) -> int:
    # Minimal mapping; in production, use pytz/zoneinfo
    mapping = {
        'US/Eastern': -4 * 60,
        'US/Central': -5 * 60,
        'US/Mountain': -6 * 60,
        'US/Pacific': -7 * 60,
        'EU/Central': 1 * 60,
    }
    return mapping.get(region, 0)


def is_within_user_window(user_region: str, now_utc: datetime = None) -> bool:
    now_utc = now_utc or datetime.utcnow()
    offset = timedelta(minutes=_get_timezone_offset_minutes(user_region))
    local = now_utc + offset
    # Quiet hours 00:00–06:00 local
    return not (0 <= local.hour < 6)


def get_daily_caps(day_index: int) -> Tuple[int, int]:
    # day_index 0-based since account creation
    # ramp: day0: 2, day1: 5, day2: 10, day3+: 15
    if day_index <= 0:
        return (2, 2)
    if day_index == 1:
        return (5, 3)
    if day_index == 2:
        return (10, 5)
    return (15, 6)


