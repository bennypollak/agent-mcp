# Thermostat

Controls a hardware thermostat over HTTP via an ngrok tunnel.

> Hardware spec: [thermostat.md](../../thermostat.md)

---

## Rooms

| ID | Aliases |
|----|---------|
| `one` | small, bedroom |
| `two` | big, livingroom, living room |

Temperatures are always in **Fahrenheit**.

---

## MCP tools

| Tool | Args | Description |
|------|------|-------------|
| `get_status` | — | Current temps (°F), set-point, hysteresis, on/off state |
| `turn_on` | `room` | Turn thermostat on |
| `turn_off` | `room` | Turn thermostat off |
| `change_temp` | `room, delta_f` | Shift set-point by ±°F |
| `set_to_current_temp` | `room` | Match set-point to current room temp |
| `toggle_fan` | `room` | Toggle fan on/off |
| `adjust_to_turn_fan_on` | `room` | Lower set-point so fan activates |
| `adjust_to_turn_fan_off` | `room` | Raise set-point so fan stops |

**Resource:** `thermostat://status` — raw live JSON from the device

---

## Run

### Via gateway (recommended)

```bash
python ../gateway.py       # serves at http://0.0.0.0:8080/thermostat/*
```

### Standalone agent

```bash
python agent.py            # http://0.0.0.0:8000
```

### MCP server only (stdio — Claude Desktop)

```bash
python server.py
```

### MCP server only (SSE — claude.ai / network clients)

```bash
python server.py --transport sse --port 9000
# give claude.ai: https://9000yo372002.ngrok.io/sse
```

---

## Claude Desktop config (stdio)

```json
{
  "mcpServers": {
    "thermostat": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/agent-mcp/thermostat/server.py"]
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
# Status
curl -X POST http://localhost:8000/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "What is the temperature in both rooms?"}'

# Control
curl -X POST http://localhost:8000/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Turn on the bedroom AC and make it 2 degrees cooler"}'

# Via gateway
curl -X POST http://localhost:8080/thermostat/run_task \
     -H "Content-Type: application/json" \
     -d '{"task": "Turn off the big room fan"}'
```

---

## Files

| File | Description |
|------|-------------|
| `thermostat_client.py` | Low-level API client — room normalization, unit conversion, all controls |
| `server.py` | FastMCP server — exposes tools and resource |
| `agent.py` | FastAPI HTTP service — model-agnostic agent loop |
| `openapi.yaml` | OpenAPI 3.1.0 spec for ChatGPT Custom GPT Actions |
