"""
Thermostat Agent Service
------------------------
HTTP endpoint that accepts natural-language tasks, runs a Claude agent
loop with thermostat tools, and returns an action log + final answer.

Start:
    python agent.py          # runs on http://0.0.0.0:8000

Invoke:
    curl -X POST http://localhost:8000/run_task \
         -H "Content-Type: application/json" \
         -d '{"task": "Turn on the bedroom AC and set it 2 degrees cooler"}'

OpenAI-compatible tool schema available at GET /openai_tools
"""
import json
import os
import uvicorn
import anthropic
from fastapi import FastAPI
from pydantic import BaseModel
import thermostat_client as tc

app = FastAPI(title="Thermostat Agent", version="1.0.0")
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ---------------------------------------------------------------------------
# Tool definitions (Claude / OpenAI format)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "get_status",
        "description": (
            "Get current thermostat status: temperatures in °F, set-point, "
            "hysteresis, and active state for both rooms."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "turn_on",
        "description": "Turn the thermostat ON for a room.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
    {
        "name": "turn_off",
        "description": "Turn the thermostat OFF for a room.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
    {
        "name": "change_temp",
        "description": (
            "Shift the thermostat set-point by delta_f degrees Fahrenheit. "
            "Positive = warmer, negative = cooler."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"},
                "delta_f": {"type": "number", "description": "Degrees °F to add (e.g. +2 or -2)"},
            },
            "required": ["room", "delta_f"],
        },
    },
    {
        "name": "set_to_current_temp",
        "description": "Set thermostat target to the current room temperature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
    {
        "name": "toggle_fan",
        "description": "Toggle the fan on/off for a room.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
    {
        "name": "adjust_to_turn_fan_on",
        "description": "Adjust thermostat set-point so the fan turns ON (lowers target below current temp).",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
    {
        "name": "adjust_to_turn_fan_off",
        "description": "Adjust thermostat set-point so the fan turns OFF (raises target above current temp).",
        "input_schema": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "small/bedroom/one  OR  big/livingroom/two"}
            },
            "required": ["room"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a smart thermostat controller. You manage two rooms:
- small room  (synonyms: bedroom, one)
- big room    (synonyms: living room, livingroom, two)

Temperatures are always in Fahrenheit.

When given a task:
1. Check status first if you need context.
2. Call the appropriate tool(s) to fulfil the request.
3. Confirm the outcome in plain language.
"""


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def dispatch(name: str, args: dict) -> str:
    try:
        match name:
            case "get_status":
                return json.dumps(tc.get_status(), indent=2)
            case "turn_on":
                return tc.turn_on(args["room"])
            case "turn_off":
                return tc.turn_off(args["room"])
            case "change_temp":
                return tc.change_temp_f(args["room"], args["delta_f"])
            case "set_to_current_temp":
                return tc.set_to_current(args["room"])
            case "toggle_fan":
                return tc.toggle_fan(args["room"])
            case "adjust_to_turn_fan_on":
                return tc.adjust_turn_on(args["room"])
            case "adjust_to_turn_fan_off":
                return tc.adjust_turn_off(args["room"])
            case _:
                return f"Unknown tool: {name}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(task: str, max_turns: int = 10) -> tuple[str, list[dict]]:
    messages = [{"role": "user", "content": task}]
    action_log: list[dict] = []

    for _ in range(max_turns):
        resp = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            final = next(
                (b.text for b in resp.content if hasattr(b, "text")), "Done."
            )
            return final, action_log

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = dispatch(block.name, block.input)
                action_log.append({"tool": block.name, "args": block.input, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

    return "Agent reached maximum iterations.", action_log


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

class TaskRequest(BaseModel):
    task: str


class TaskResponse(BaseModel):
    result: str
    action_log: list[dict]


@app.post("/run_task", response_model=TaskResponse)
def run_task(req: TaskRequest) -> TaskResponse:
    """Run a natural-language thermostat task via the Claude agent."""
    result, log = run_agent(req.task)
    return TaskResponse(result=result, action_log=log)


@app.get("/openai_tools")
def openai_tools() -> list[dict]:
    """Return tool schemas in OpenAI function-calling format."""
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOLS
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
