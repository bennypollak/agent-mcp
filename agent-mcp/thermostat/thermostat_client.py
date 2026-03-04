"""
Low-level client for the thermostat hardware API.

Base URL: https://yo372002.ngrok.io
Rooms:    one = small / bedroom
          two = big   / living room
Temps:    stored in Celsius on the device; this module converts to/from °F
"""
import httpx

BASE_URL = "https://yo372002.ngrok.io"

ROOM_ALIASES: dict[str, str] = {
    "one": "one", "small": "one", "bedroom": "one",
    "two": "two", "big": "two", "livingroom": "two",
    "living room": "two", "living_room": "two",
}


def normalize_room(room: str) -> str:
    key = room.lower().strip()
    mapped = ROOM_ALIASES.get(key)
    if mapped is None:
        raise ValueError(
            f"Unknown room '{room}'. "
            "Use: small/bedroom/one  OR  big/livingroom/two"
        )
    return mapped


def c_to_f(c: float) -> float:
    return round(c * 9 / 5 + 32, 2)


def delta_f_to_c(delta_f: float) -> float:
    """Convert a temperature *delta* from °F to °C (multiply by 5/9)."""
    return round(delta_f * 5 / 9, 4)


def api_get(path: str) -> dict | str:
    with httpx.Client(timeout=10, follow_redirects=True) as client:
        resp = client.get(f"{BASE_URL}{path}")
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """Return a normalised status dict with temperatures in °F."""
    s = api_get("/pi/status")

    def room_view(key: str) -> dict:
        return {
            "current_temp_f": c_to_f(s["latestTemps"][key]),
            "set_temp_f": c_to_f(s["acConfig"]["activeThermos"][key]["temp"]),
            "hysteresis_f": round(s["acConfig"]["activeThermos"][key]["hyst"] * 9 / 5, 4),
            "is_active": bool(s["active"][key]),
        }

    return {
        "small_room": room_view("one"),
        "big_room": room_view("two"),
        "raw": s,
    }


# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------

def turn_on(room: str) -> str:
    r = normalize_room(room)
    api_get(f"/wemo/thermo/{r}/0")
    return f"Turned ON thermostat for {room} room (id={r})"


def turn_off(room: str) -> str:
    r = normalize_room(room)
    api_get(f"/wemo/cycle/{r}/0")
    return f"Turned OFF thermostat for {room} room (id={r})"


def change_temp_f(room: str, delta_f: float) -> str:
    """Shift the set temperature by *delta_f* degrees Fahrenheit."""
    r = normalize_room(room)
    delta_c = delta_f_to_c(delta_f)
    api_get(f"/wemo/thermo/{r}/{delta_c}")
    return f"Changed set temp for {room} room by {delta_f:+.1f}°F ({delta_c:+.4f}°C)"


def set_to_current(room: str) -> str:
    r = normalize_room(room)
    api_get(f"/wemo/thermo/set/{r}")
    return f"Set thermostat for {room} room to current temperature"


def toggle_fan(room: str) -> str:
    r = normalize_room(room)
    api_get(f"/thermo/toggle/{r}")
    return f"Toggled fan for {room} room"


def adjust_turn_on(room: str) -> str:
    """Adjust so the fan turns ON (set temp drops below current)."""
    r = normalize_room(room)
    api_get(f"/thermo/adjust/{r}/on")
    return f"Adjusted thermostat for {room} room → fan will turn ON"


def adjust_turn_off(room: str) -> str:
    """Adjust so the fan turns OFF (set temp rises above current)."""
    r = normalize_room(room)
    api_get(f"/thermo/adjust/{r}/off")
    return f"Adjusted thermostat for {room} room → fan will turn OFF"
