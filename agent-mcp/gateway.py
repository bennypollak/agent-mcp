"""
Agent Gateway
-------------
Single-port server that hosts all agents and MCP SSE endpoints.
Run this instead of the individual agent.py files.

Start:
    python gateway.py          # http://0.0.0.0:8080  (override with GATEWAY_PORT)

Endpoints:
    GET  /                         list all routes
    POST /thermostat/run_task      thermostat agent
    GET  /thermostat/tools         thermostat tools (via MCP)
    GET  /thermostat/health
    GET  /thermostat/mcp/sse       thermostat MCP SSE  ← give this URL to claude.ai
    POST /birthdays/run_task       birthdays agent
    GET  /birthdays/tools          birthdays tools (via MCP)
    GET  /birthdays/health
    GET  /birthdays/mcp/sse        birthdays MCP SSE   ← give this URL to claude.ai
"""
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import uvicorn
from fastapi import FastAPI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

HERE = Path(__file__).parent
PYTHON = sys.executable
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", 8080))
GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", f"http://localhost:{GATEWAY_PORT}")


# ---------------------------------------------------------------------------
# Load sub-project modules by path (no __init__.py needed)
# ---------------------------------------------------------------------------

def _load(module_name: str, path: Path):
    """Load a module from an absolute path, adding its directory to sys.path."""
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load MCP servers (for SSE mounting)
_thermostat_server = _load("thermostat_server", HERE / "thermostat/server.py")
_birthdays_server  = _load("birthdays_server",  HERE / "birthdays/server.py")

# Load agents (for run_agent functions)
_thermostat_agent = _load("thermostat_agent", HERE / "thermostat/agent.py")
_birthdays_agent  = _load("birthdays_agent",  HERE / "birthdays/agent.py")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Gateway",
    version="1.0.0",
    servers=[{"url": GATEWAY_BASE_URL}],
)

# Mount MCP SSE sub-apps — clients connect to /<agent>/mcp/sse
app.mount(
    "/thermostat/mcp",
    _thermostat_server.mcp.sse_app(mount_path="/thermostat/mcp"),
)
app.mount(
    "/birthdays/mcp",
    _birthdays_server.mcp.sse_app(mount_path="/birthdays/mcp"),
)


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

class TaskRequest(BaseModel):
    task: str
    model: str = "claude-sonnet-4-6"


class TaskResponse(BaseModel):
    result: str
    action_log: list[dict]
    model: str


# ---------------------------------------------------------------------------
# Thermostat routes
# ---------------------------------------------------------------------------

@app.post("/thermostat/run_task", response_model=TaskResponse)
async def thermostat_run_task(req: TaskRequest) -> TaskResponse:
    result, log = await _thermostat_agent.run_agent(req.task, req.model)
    return TaskResponse(result=result, action_log=log, model=req.model)


@app.get("/thermostat/tools")
async def thermostat_tools() -> list[dict]:
    async with stdio_client(
        StdioServerParameters(command=PYTHON, args=[_thermostat_agent.SERVER_PATH])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [{"name": t.name, "description": t.description} for t in result.tools]


@app.get("/thermostat/health")
def thermostat_health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Birthdays routes
# ---------------------------------------------------------------------------

@app.post("/birthdays/run_task", response_model=TaskResponse)
async def birthdays_run_task(req: TaskRequest) -> TaskResponse:
    result, log = await _birthdays_agent.run_agent(req.task, req.model)
    return TaskResponse(result=result, action_log=log, model=req.model)


@app.get("/birthdays/tools")
async def birthdays_tools() -> list[dict]:
    async with stdio_client(
        StdioServerParameters(command=PYTHON, args=[_birthdays_agent.SERVER_PATH])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [{"name": t.name, "description": t.description} for t in result.tools]


@app.get("/birthdays/health")
def birthdays_health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root index
# ---------------------------------------------------------------------------

@app.get("/")
def index() -> dict:
    return {
        "agents": ["thermostat", "birthdays"],
        "endpoints": {
            "thermostat": {
                "run_task": "/thermostat/run_task",
                "tools":    "/thermostat/tools",
                "health":   "/thermostat/health",
                "mcp_sse":  "/thermostat/mcp/sse",
            },
            "birthdays": {
                "run_task": "/birthdays/run_task",
                "tools":    "/birthdays/tools",
                "health":   "/birthdays/health",
                "mcp_sse":  "/birthdays/mcp/sse",
            },
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_PORT)
