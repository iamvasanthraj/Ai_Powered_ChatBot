
from datetime import datetime
from typing import Any, Dict, List

DATE_FIELDS = {"eventStartTime", "eventEndTime", "localDateTime"}

def _parse_date_string(val: str) -> Any:
    try:
        # Handle basic ISO format with Z
        # Python fromisoformat doesn't like Z before 3.11
        if val.endswith("Z"):
            val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(val)
    except ValueError:
        return val

def _convert_value_for_date(val: Any) -> Any:
    """
    Helper to convert values knowing they belong to a date field.
    """
    if isinstance(val, str):
        return _parse_date_string(val)
    elif isinstance(val, list):
        # e.g. $in: [...]
        return [_convert_value_for_date(x) for x in val]
    elif isinstance(val, dict):
        # e.g. $gte: ..., $lte: ...
        return {k: _convert_value_for_date(v) for k, v in val.items()}
    return val

def convert_dates(obj: Any) -> Any:
    """
    Recursively scans for specific keys and converts their values to datetime objects.
    """
    if isinstance(obj, list):
        return [convert_dates(item) for item in obj]
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k in DATE_FIELDS:
                new_obj[k] = _convert_value_for_date(v)
            else:
                new_obj[k] = convert_dates(v)
        return new_obj
    return obj

def generate_title(text: str) -> str:
    # Simple title: first 5-7 words, capitalized
    words = text.strip().split()
    title = " ".join(words[:7])
    return title.capitalize()
