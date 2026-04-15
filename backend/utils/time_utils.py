from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def current_time() -> datetime:
    return datetime.now().astimezone()


def current_time_iso() -> str:
    return current_time().isoformat()


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    local_tz = current_time().tzinfo
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(local_tz)
