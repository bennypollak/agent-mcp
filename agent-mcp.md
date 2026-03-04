# Multi-MCP / Agent Monorepo

A general-purpose workspace for building and testing **MCP servers** and **Claude agents**.
Each sub-project follows the same three-file pattern so they can be run standalone or composed.

---

## Project Structure

```
.
├── agent-mcp.md              ← this file
│
├── thermostat/               ← thermostat MCP + agent
│   ├── thermostat.md         spec
│   ├── thermostat_client.py  low-level API client
│   ├── server.py             MCP server  (stdio / SSE)
│   ├── agent.py              FastAPI agent  (POST /run_task)
│   └── requirements.txt
│
└── birthdays/                ← (next) birthday tracker MCP + agent
    ├── birthdays.md          spec  (to be written)
    ├── birthdays_client.py
    ├── server.py
    ├── agent.py
    └── requirements.txt
```

---

## Pattern — how every sub-project is built

```
<name>_client.py   Pure Python functions. No MCP, no HTTP framework.
                   Handles all I/O (file, DB, external API) and data conversion.

server.py          FastMCP wrapper. Imports *_client, exposes tools + resources.
                   Runs over stdio (Claude Desktop) or SSE (network clients).

agent.py           FastAPI + Anthropic SDK. Imports *_client directly.
                   POST /run_task  → natural-language task → action log + result
                   GET  /openai_tools → OpenAI-compatible tool schemas
                   GET  /health
```

---

## 1) Thermostat

Controls a hardware thermostat at `https://yo372002.ngrok.io`.

### Rooms

| Name used in tools | Aliases |
|--------------------|---------|
| `one` | small, bedroom |
| `two` | big, livingroom, living room |

### MCP Tools

| Tool | Description |
|------|-------------|
| `get_status` | Temperatures (°F), set-point, hysteresis, active state |
| `turn_on(room)` | Turn thermostat on |
| `turn_off(room)` | Turn thermostat off |
| `change_temp(room, delta_f)` | Shift set-point by ±°F |
| `set_to_current_temp(room)` | Match set-point to current room temp |
| `toggle_fan(room)` | Toggle fan on/off |
| `adjust_to_turn_fan_on(room)` | Drop set-point so fan activates |
| `adjust_to_turn_fan_off(room)` | Raise set-point so fan stops |

MCP Resource: `thermostat://status` — raw live JSON from device.

### Run

```bash
cd thermostat
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...

# MCP server (Claude Desktop / Alfred MCP)
python server.py

# Agent HTTP endpoint
python agent.py            # → http://localhost:8000
```

### Claude Desktop config

Merge into `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "thermostat": {
      "command": "python",
      "args": ["/Users/benny/dev/ai/thermostat/server.py"]
    }
  }
}
```

### Test the agent

```bash
curl -X POST http://localhost:8000/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "What is the temperature in the bedroom?"}'

curl -X POST http://localhost:8000/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Turn on the big room AC and make it 2 degrees cooler"}'
```

---

## 2) Birthdays *(planned)*

Birthday tracker — store, query, and get reminders for birthdays.

### Planned MCP Tools

| Tool | Description |
|------|-------------|
| `add_birthday(name, date)` | Store a birthday |
| `get_birthday(name)` | Look up a person's birthday |
| `list_birthdays` | All stored birthdays |
| `upcoming_birthdays(days)` | Birthdays within the next N days |
| `delete_birthday(name)` | Remove an entry |

### Planned data store

`birthdays/data/birthdays.json` — simple JSON file, no external DB needed.

### Run (once implemented)

```bash
cd birthdays
pip install -r requirements.txt
python server.py     # MCP
python agent.py      # Agent on :8001
```

---

## Adding a new sub-project

1. Create a folder `<name>/`
2. Write `<name>_client.py` with pure functions and no framework imports
3. Copy `server.py` from thermostat, swap in your tools
4. Copy `agent.py` from thermostat, update `TOOLS`, `dispatch()`, and `SYSTEM_PROMPT`
5. Add to Claude Desktop config under a new key in `mcpServers`
6. Document it in this file

---

## Clients that can use these servers

| Client | How to connect |
|--------|---------------|
| **Claude Desktop** | `claude_desktop_config.json` → MCP stdio |
| **Alfred** | MCP tools or `POST /run_task` HTTP |
| **ChatGPT / OpenAI** | `GET /openai_tools` schemas + any HTTP proxy |
| **curl / scripts** | `POST /run_task` directly |
