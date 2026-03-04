"""
Low-level client for the birthday tracker.

Data is persisted in data/birthdays.json (relative to this file).
Dates are stored as YYYY-MM-DD; year 1900 is used when only MM-DD is given.
"""
import json
from datetime import date, datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "birthdays.json"


def _load() -> dict:
    DATA_FILE.parent.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}")
    return json.loads(DATA_FILE.read_text())


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, sort_keys=True))


def _parse_date(date_str: str) -> date:
    """Accept YYYY-MM-DD, MM-DD, MM/DD/YYYY, or MM/DD."""
    for fmt in ("%Y-%m-%d", "%m-%d", "%m/%d/%Y", "%m/%d"):
        try:
            d = datetime.strptime(date_str.strip(), fmt).date()
            if fmt in ("%m-%d", "%m/%d"):
                d = d.replace(year=1900)  # placeholder when no year given
            return d
        except ValueError:
            continue
    raise ValueError(
        f"Cannot parse date '{date_str}'. Use YYYY-MM-DD or MM-DD."
    )


def _next_birthday(bday: date, today: date) -> date:
    """Next annual occurrence of bday on or after today."""
    candidate = bday.replace(year=today.year)
    if candidate < today:
        candidate = bday.replace(year=today.year + 1)
    return candidate


def _entry_view(name: str, entry: dict, today: date) -> dict:
    d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
    next_bday = _next_birthday(d, today)
    has_year = d.year != 1900
    return {
        "name": name,
        "date": entry["date"] if has_year else d.strftime("%m-%d"),
        "notes": entry.get("notes", ""),
        "next_birthday": next_bday.strftime("%Y-%m-%d"),
        "days_until": (next_bday - today).days,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_birthday(name: str, date_str: str, notes: str = "") -> str:
    data = _load()
    key = name.strip()
    d = _parse_date(date_str)
    data[key] = {"date": d.strftime("%Y-%m-%d"), "notes": notes}
    _save(data)
    label = d.strftime("%B %-d, %Y") if d.year != 1900 else d.strftime("%B %-d")
    return f"Saved birthday for {key}: {label}"


def get_birthday(name: str) -> dict:
    data = _load()
    key = name.strip()
    entry = data.get(key)
    if entry is None:
        return {"found": False, "name": key}
    view = _entry_view(key, entry, date.today())
    view["found"] = True
    return view


def list_birthdays() -> list[dict]:
    data = _load()
    today = date.today()
    results = [_entry_view(name, entry, today) for name, entry in data.items()]
    results.sort(key=lambda x: x["days_until"])
    return results


def upcoming_birthdays(days: int = 7) -> list[dict]:
    return [b for b in list_birthdays() if b["days_until"] <= days]


def delete_birthday(name: str) -> str:
    data = _load()
    key = name.strip()
    if key not in data:
        return f"No birthday found for '{key}'"
    del data[key]
    _save(data)
    return f"Deleted birthday for '{key}'"
