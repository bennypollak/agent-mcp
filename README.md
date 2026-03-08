# agent-mcp

A multi-MCP / Claude agent monorepo. Each sub-project exposes a domain as both an **MCP server** (for Claude Desktop, Alfred, and any MCP client) and a **FastAPI HTTP agent** (for curl, OpenAI, and Alfred HTTP).

---

## Project layout

```
.
├── README.md                     ← you are here
├── agent-mcp.md                  ← architecture spec & roadmap
│
├── thermostat.md                 ← thermostat hardware spec
├── thermostat0.md                ← original thermostat spec (reference)
├── thermostat_client.py          ← standalone thermostat client (root)
├── server.py                     ← standalone MCP server (root)
├── agent.py                      ← standalone agent service (root, :8000)
├── requirements.txt
├── claude_desktop_config.json    ← single-server Claude Desktop snippet
│
└── agent-mcp/                    ← structured multi-project layout
    ├── gateway.py                ← single-port server (all agents + MCP SSE) :8080
    ├── claude_desktop_config.json      ← stdio transport (local)
    ├── claude_desktop_config_sse.json  ← SSE via mcp-remote (remote test)
    ├── thermostat/               ← thermostat sub-project
    │   ├── thermostat_client.py
    │   ├── server.py             MCP stdio / SSE
    │   ├── agent.py              HTTP :8000 (standalone)
    │   └── openapi.yaml
    └── birthdays/                ← birthday tracker sub-project
        ├── birthdays_client.py
        ├── server.py             MCP stdio / SSE
        ├── agent.py              HTTP :8001 (standalone)
        ├── openapi.yaml
        └── data/
            └── birthdays.json    persisted birthday data
```

---

## Sub-projects

### 1) Thermostat

Controls a hardware thermostat over HTTP via an ngrok tunnel.

> Spec: [thermostat.md](thermostat.md)

**Rooms**

| ID | Aliases |
|----|---------|
| `one` | small, bedroom |
| `two` | big, livingroom, living room |

**MCP tools**

| Tool | Description |
|------|-------------|
| `get_status` | Current temps (°F), set-point, hysteresis, on/off state |
| `turn_on(room)` | Turn thermostat on |
| `turn_off(room)` | Turn thermostat off |
| `change_temp(room, delta_f)` | Shift set-point by ±°F |
| `set_to_current_temp(room)` | Match set-point to current room temp |
| `toggle_fan(room)` | Toggle fan on/off |
| `adjust_to_turn_fan_on(room)` | Lower set-point so fan activates |
| `adjust_to_turn_fan_off(room)` | Raise set-point so fan stops |

**MCP resource:** `thermostat://status` — raw live JSON from device

---

### 2) Birthdays

Birthday tracker backed by a local JSON file.

**MCP tools**

| Tool | Description |
|------|-------------|
| `add_birthday(name, date, notes?)` | Store a birthday (`YYYY-MM-DD` or `MM-DD`) |
| `get_birthday(name)` | Look up date + days until next occurrence |
| `list_birthdays()` | All entries sorted soonest-first |
| `upcoming_birthdays(days=7)` | Birthdays within the next N days |
| `delete_birthday(name)` | Remove an entry |

**MCP resource:** `birthdays://all` — all birthdays as JSON

---

## Architecture

See [agent-mcp.md](agent-mcp.md) for the full architecture spec and roadmap.

Every sub-project follows this three-file pattern:

```
<name>_client.py   Pure functions — all I/O, no framework
server.py          FastMCP wrapper — MCP tools + resources
agent.py           FastAPI + Claude agent loop — POST /run_task
```

---

## Quick start

### Prerequisites

```bash
pip install -r requirements.txt        # root (thermostat standalone)
# or
pip install -r agent-mcp/thermostat/requirements.txt
pip install -r agent-mcp/birthdays/requirements.txt

export ANTHROPIC_API_KEY=sk-...
```

### Run MCP servers (Claude Desktop / Alfred MCP)

```bash
# Thermostat
python agent-mcp/thermostat/server.py

# Birthdays
python agent-mcp/birthdays/server.py
```

### Run the gateway (single port for everything)

```bash
# All agents + MCP SSE  →  http://localhost:8080
python agent-mcp/gateway.py
```

Routes served by the gateway:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/thermostat/run_task` | Thermostat agent |
| `GET`  | `/thermostat/tools` | List thermostat tools |
| `GET`  | `/thermostat/mcp/sse` | Thermostat MCP SSE (for claude.ai) |
| `POST` | `/birthdays/run_task` | Birthdays agent |
| `GET`  | `/birthdays/tools` | List birthday tools |
| `GET`  | `/birthdays/mcp/sse` | Birthdays MCP SSE (for claude.ai) |

### Run individual agent services (standalone)

```bash
# Thermostat agent  →  http://localhost:8000
python agent-mcp/thermostat/agent.py

# Birthdays agent   →  http://localhost:8001
python agent-mcp/birthdays/agent.py
```

### Claude Desktop

Merge `agent-mcp/claude_desktop_config.json` into:
`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "thermostat": {
      "command": "python",
      "args": ["/path/to/agent-mcp/thermostat/server.py"]
    },
    "birthdays": {
      "command": "python",
      "args": ["/path/to/agent-mcp/birthdays/server.py"]
    }
  }
}
```

---

## Example agent calls

```bash
# Via gateway (port 8080)
curl -X POST http://localhost:8080/thermostat/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "What is the temperature in the bedroom?"}'

curl -X POST http://localhost:8080/birthdays/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Who has a birthday in the next 30 days?"}'

# Via standalone agents
curl -X POST http://localhost:8000/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Turn on the big room AC and make it 2 degrees cooler"}'

curl -X POST http://localhost:8001/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Add Alice, birthday March 15 1990, she loves chocolate cake"}'
```

---

## Compatible clients

| Client | How to connect |
|--------|----------------|
| **Claude Desktop** | `claude_desktop_config.json` → MCP stdio |
| **Alfred** | MCP tools or `POST /run_task` HTTP |
| **ChatGPT / OpenAI** | `GET /openai_tools` schemas |
| **curl / scripts** | `POST /run_task` directly |
