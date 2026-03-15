# Birthdays

Birthday tracker backed by a local JSON file (`data/birthdays.json`).

---

## MCP tools

| Tool | Args | Description |
|------|------|-------------|
| `add_birthday` | `name, date, notes?` | Store a birthday (`YYYY-MM-DD` or `MM-DD`) |
| `get_birthday` | `name` | Look up date + days until next occurrence |
| `list_birthdays` | — | All entries sorted soonest-first |
| `upcoming_birthdays` | `days=7` | Birthdays within the next N days |
| `delete_birthday` | `name` | Remove an entry |

**Resource:** `birthdays://all` — all birthdays as JSON

---

## Run

### Via gateway (recommended)

```bash
python ../gateway.py       # serves at http://0.0.0.0:8080/birthdays/*
```

### Standalone agent

```bash
python agent.py            # http://0.0.0.0:8001
```

### MCP server only (stdio — Claude Desktop)

```bash
python server.py
```

### MCP server only (SSE — claude.ai / network clients)

```bash
python server.py --transport sse --port 9001
# give claude.ai: https://9001yo372002.ngrok.io/sse
```

---

## Claude Desktop config (stdio)

```json
{
  "mcpServers": {
    "birthdays": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/agent-mcp/birthdays/server.py"]
    }
  }
}
```

---

## HTTP API

```
POST /run_task   { "task": "...", "model": "claude-sonnet-4-6" }
GET  /tools      list tools from the MCP server
GET  /health
```

### Example calls

```bash
# Add a birthday
curl -X POST http://localhost:8001/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Add Alice, birthday March 15 1990, she loves chocolate cake"}'

# Upcoming
curl -X POST http://localhost:8001/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Who has a birthday in the next 30 days?"}'

# Via gateway
curl -X POST http://localhost:8080/birthdays/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "List all birthdays"}'
```

---

## Date formats

| Format | Example | Notes |
|--------|---------|-------|
| `YYYY-MM-DD` | `1990-03-15` | Full date with year |
| `MM-DD` | `03-15` | Annual recurrence, no year |

---

## Files

| File | Description |
|------|-------------|
| `birthdays_client.py` | CRUD functions — JSON persistence, date parsing, next-birthday calc |
| `server.py` | FastMCP server — exposes tools and resource |
| `agent.py` | FastAPI HTTP service — model-agnostic agent loop |
| `openapi.yaml` | OpenAPI 3.1.0 spec for ChatGPT Custom GPT Actions |
| `data/birthdays.json` | Persisted birthday data |
