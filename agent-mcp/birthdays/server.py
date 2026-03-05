"""
Birthdays MCP Server
--------------------
Exposes birthday CRUD tools and a live resource over MCP.

Run (stdio transport, for Claude Desktop / MCP clients):
    python server.py

Run (SSE transport, for claude.ai connector / network clients):
    python server.py --transport sse --port 9001
    → give claude.ai: https://9001yo372002.ngrok.io/sse
"""
import json
from mcp.server.fastmcp import FastMCP
import birthdays_client as bc

mcp = FastMCP("Birthdays")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("birthdays://all")
def all_birthdays_resource() -> str:
    """All stored birthdays sorted by soonest upcoming."""
    return json.dumps(bc.list_birthdays(), indent=2)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def add_birthday(name: str, date: str, notes: str = "") -> str:
    """Add or update a birthday.

    Args:
        name:  Person's name
        date:  Birthday in YYYY-MM-DD or MM-DD format
        notes: Optional note (e.g. "likes chocolate cake")
    """
    return bc.add_birthday(name, date, notes)


@mcp.tool()
def get_birthday(name: str) -> dict:
    """Look up a person's birthday and days until their next one.

    Args:
        name: Person's name
    """
    return bc.get_birthday(name)


@mcp.tool()
def list_birthdays() -> list:
    """List all stored birthdays sorted by soonest upcoming."""
    return bc.list_birthdays()


@mcp.tool()
def upcoming_birthdays(days: int = 7) -> list:
    """List birthdays coming up within the next N days.

    Args:
        days: Look-ahead window in days (default 7)
    """
    return bc.upcoming_birthdays(days)


@mcp.tool()
def delete_birthday(name: str) -> str:
    """Remove a birthday entry.

    Args:
        name: Person's name
    """
    return bc.delete_birthday(name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
