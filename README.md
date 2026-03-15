# agent-mcp

A multi-MCP / Claude agent monorepo. Each sub-project exposes a domain as both an **MCP server** (for Claude Desktop and any MCP client) and a **FastAPI HTTP agent** (for curl, ChatGPT, and HTTP clients).

> Architecture spec & roadmap: [agent-mcp.md](agent-mcp.md)

---

## Project layout

```
agent-mcp/
├── gateway.py                        ← single-port server (all agents + MCP SSE) :8080
├── claude_desktop_config.json        ← stdio transport (Claude Desktop)
├── claude_desktop_config_sse.json    ← SSE via mcp-remote (remote testing)
├── thermostat/                       ← see thermostat/README.md
│   ├── thermostat_client.py
│   ├── server.py
│   ├── agent.py
│   └── openapi.yaml
└── birthdays/                        ← see birthdays/README.md
    ├── birthdays_client.py
    ├── server.py
    ├── agent.py
    ├── openapi.yaml
    └── data/birthdays.json
```

---

## Sub-projects

| Sub-project | Description | Standalone port | README |
|-------------|-------------|-----------------|--------|
| **thermostat** | Hardware thermostat controller | :8000 | [thermostat/README.md](agent-mcp/thermostat/README.md) |
| **birthdays** | Birthday tracker (JSON-backed) | :8001 | [birthdays/README.md](agent-mcp/birthdays/README.md) |

---

## Pattern

Every sub-project follows the same three-file pattern:

```
<name>_client.py   Pure functions — all I/O, no framework
server.py          FastMCP — MCP tools + resources (stdio or SSE transport)
agent.py           FastAPI + model-agnostic agent loop — POST /run_task
```

Supported models: any Anthropic (`claude-*`) or OpenAI (`gpt-*`, `o1`, `o3`, `o4`) model.

---

## Quick start

```bash
# Copy and fill in credentials + config
cp .env.example .env

# Create venv and install dependencies
uv venv --python 3.13
uv pip install -r requirements.txt
```

### Gateway — single port for everything

```bash
python agent-mcp/gateway.py      # http://0.0.0.0:8080
```

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/thermostat/run_task` | Thermostat agent |
| `GET`  | `/thermostat/tools` | List thermostat MCP tools |
| `GET`  | `/thermostat/mcp/sse` | Thermostat MCP SSE (claude.ai connector) |
| `POST` | `/birthdays/run_task` | Birthdays agent |
| `GET`  | `/birthdays/tools` | List birthdays MCP tools |
| `GET`  | `/birthdays/mcp/sse` | Birthdays MCP SSE (claude.ai connector) |

### Claude Desktop (stdio)

Merge `agent-mcp/claude_desktop_config.json` into
`~/Library/Application Support/Claude/claude_desktop_config.json`.

### Claude Desktop (SSE via mcp-remote)

Use `agent-mcp/claude_desktop_config_sse.json` — requires the gateway running and ngrok tunneling port 8080.

---

## Adding a new sub-project

1. Create `agent-mcp/<name>/` with the three-file pattern above.
2. Add its `mcp` object and `run_agent` function to `gateway.py`.
3. Add ports and URLs to `.env` / `.env.example`.
4. Write a `<name>/README.md`.

See [agent-mcp.md](agent-mcp.md) for the full spec.
