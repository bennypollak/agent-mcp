# Thermostat Reference (MCP + Agent) — thermostat.md

This document specifies a tiny “thermostat” system with:
1) an **MCP server** that exposes deterministic thermostat tools, and resou
2) an **Agent layer** that uses those tools to fulfill natural-language goals.

Goal: Implement a working reference system that can be invoked from:
- Claude Desktop (MCP client)
- ChatGPT/OpenAI (as tool calls)
- Alfred (your client) via the same MCP tools and/or the agent endpoint

The tool connects to an ant point in the server that provides all the information and acts to turn on off and other adjustments to the actual the thermostat
---

## 0) Definitions

### Rooms (fixed set)
Use these canonical room IDs:
- `livingroom` and synonyms like big, "living room" two
- `bedroom` add synonyms small one
### Units
Use Fahrenheit (`temp_f`) everywhere.

---
##  URL four connection to the thermometer and controller https://yo372002.ngrok.io
### endpoint for status /pi/status
- Store result in status
- the rooms are small and big
- current room temperature in status.latestTemps[<room>]
- temperature currently configured to in status.acConfig.activeThermos[<room>]['temp']
- temperature hysterisis configured to in status.acConfig.activeThermos[<room>]['hyst']
- on off status for each thermal in status.active[<room>] values are 1 and 0

### and point for controlling
- turn on /wemo/thermo/<room>/0
- turn off /wemo/cycle/<room>/0
- change the temperature by <value> /wemo/thermo/<room>/<value>
- set the thermostat to the current room temperature /wemo/thermo/set/<room>
- toggle the on off stages of the fan /thermo/toggle/<room>
- adjust the thermostat setting so that it turns on the fan /thermo/adjust/<room>/on
- adjust the thermostat setting so that it turns off the fan /thermo/adjust/<room>/off

### A) Thermostat Core
- Owns the **source of truth state**
- Persists state in a local file (e.g., `data/status.json`)
- Provides pure functions for reading/updating state

### B) MCP Server (Capabilities)
Expose deterministic tools over MCP. These are the primitives for direct control.

### C) Agent Service (Orchestrator)
Expose one high-level tool/endpoint: `thermostat.run_task`.
The agent:
- reads state via MCP tools
- decides steps
- calls MCP tools
- verifies outcomes
- returns an action log + final state

---

## 2) Data Model (persisted)
{
"status": "ok",
"temperature-one": 27.3,
"temperature-two": 27.78,
"weatherInfo": {
"timestamp": "3:00:06 PM",
"by_location": {
"ny": 33,
"santiago": 88.1
}
},
"wemo": {
"one": "1",
"two": "0"
},
"active": {
"one": "thermo",
"two": ""
},
"latestTemps": {
"one": 27.3,
"two": 27.78
},
"acConfig": {
"activeThermos": {
"two": {
"temp": 27.64,
"hyst": 0.05
},
"one": {
"temp": 29.240000000000002,
"hyst": 0.05
}
},
"activeCycles": {
"one": {},
"two": {}
},
"ac": 0,
"useWemo": false
}
}