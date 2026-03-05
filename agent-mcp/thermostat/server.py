"""
Thermostat MCP Server
---------------------
Exposes all thermostat controls as MCP tools and a live-status resource.

Run (stdio transport, for Claude Desktop / MCP clients):
    python server.py

Run (SSE transport, for claude.ai connector / network clients):
    python server.py --transport sse --port 9000
    → give claude.ai: https://9000yo372002.ngrok.io/sse
"""
import json
from mcp.server.fastmcp import FastMCP
import thermostat_client as tc

mcp = FastMCP("Thermostat")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("thermostat://status")
def status_resource() -> str:
    """Live thermostat status (raw JSON from device)."""
    raw = tc.api_get("/pi/status")
    return json.dumps(raw, indent=2)


# ---------------------------------------------------------------------------
# Tools – read
# ---------------------------------------------------------------------------

@mcp.tool()
def get_status() -> dict:
    """Get current thermostat status for both rooms.

    Returns temperatures (°F), set-point, hysteresis, and on/off state
    for the small room (bedroom) and big room (living room).
    """
    return tc.get_status()


# ---------------------------------------------------------------------------
# Tools – control
# ---------------------------------------------------------------------------

@mcp.tool()
def turn_on(room: str) -> str:
    """Turn the thermostat ON for a room.

    Args:
        room: Room identifier – small / bedroom / one  OR  big / livingroom / two
    """
    return tc.turn_on(room)


@mcp.tool()
def turn_off(room: str) -> str:
    """Turn the thermostat OFF for a room.

    Args:
        room: Room identifier – small / bedroom / one  OR  big / livingroom / two
    """
    return tc.turn_off(room)


@mcp.tool()
def change_temp(room: str, delta_f: float) -> str:
    """Shift the thermostat set-point by a number of degrees Fahrenheit.

    Positive delta_f makes it warmer; negative makes it cooler.

    Args:
        room:    small / bedroom / one  OR  big / livingroom / two
        delta_f: Degrees °F to add (e.g. +2 or -2)
    """
    return tc.change_temp_f(room, delta_f)


@mcp.tool()
def set_to_current_temp(room: str) -> str:
    """Set the thermostat target to the current room temperature.

    This effectively pauses cooling/heating until the temperature drifts.

    Args:
        room: small / bedroom / one  OR  big / livingroom / two
    """
    return tc.set_to_current(room)


@mcp.tool()
def toggle_fan(room: str) -> str:
    """Toggle the fan on/off for a room.

    Args:
        room: small / bedroom / one  OR  big / livingroom / two
    """
    return tc.toggle_fan(room)


@mcp.tool()
def adjust_to_turn_fan_on(room: str) -> str:
    """Adjust the thermostat set-point so the fan turns ON.

    Lowers the set-point below the current temperature so cooling activates.

    Args:
        room: small / bedroom / one  OR  big / livingroom / two
    """
    return tc.adjust_turn_on(room)


@mcp.tool()
def adjust_to_turn_fan_off(room: str) -> str:
    """Adjust the thermostat set-point so the fan turns OFF.

    Raises the set-point above the current temperature so cooling stops.

    Args:
        room: small / bedroom / one  OR  big / livingroom / two
    """
    return tc.adjust_turn_off(room)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
