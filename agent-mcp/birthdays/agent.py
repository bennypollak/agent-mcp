"""
Birthdays Agent Service
-----------------------
HTTP endpoint that accepts natural-language birthday tasks, runs a Claude
agent loop with birthday tools, and returns an action log + final answer.

Start:
    python agent.py          # runs on http://0.0.0.0:8001

Invoke:
    curl -X POST http://localhost:8001/run_task \
         -H "Content-Type: application/json" \
         -d '{"task": "Add Alice birthday on March 15 1990"}'

    curl -X POST http://localhost:8001/run_task \
         -H "Content-Type: application/json" \
         -d '{"task": "Who has a birthday this week?"}'

OpenAI-compatible tool schema available at GET /openai_tools
"""
import json
import os
import uvicorn
import anthropic
from fastapi import FastAPI
from pydantic import BaseModel
import birthdays_client as bc

app = FastAPI(title="Birthdays Agent", version="1.0.0")
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "add_birthday",
        "description": "Add or update a person's birthday.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's name"},
                "date": {"type": "string", "description": "Birthday in YYYY-MM-DD or MM-DD format"},
                "notes": {"type": "string", "description": "Optional notes about the person"},
            },
            "required": ["name", "date"],
        },
    },
    {
        "name": "get_birthday",
        "description": "Look up a person's birthday and days until their next one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_birthdays",
        "description": "List all stored birthdays sorted by soonest upcoming.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "upcoming_birthdays",
        "description": "List birthdays coming up within the next N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Look-ahead window in days (default 7)"},
            },
            "required": [],
        },
    },
    {
        "name": "delete_birthday",
        "description": "Remove a birthday entry by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's name"},
            },
            "required": ["name"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a helpful birthday tracker assistant. You can store, look up, and remind
about birthdays. Today's date is available via the system clock.

When given a task:
1. Call the appropriate tool(s) to fulfil the request.
2. Respond in a friendly, natural tone.
3. For upcoming birthdays, mention how many days away they are.
"""


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def dispatch(name: str, args: dict) -> str:
    try:
        match name:
            case "add_birthday":
                return bc.add_birthday(args["name"], args["date"], args.get("notes", ""))
            case "get_birthday":
                return json.dumps(bc.get_birthday(args["name"]), indent=2)
            case "list_birthdays":
                return json.dumps(bc.list_birthdays(), indent=2)
            case "upcoming_birthdays":
                return json.dumps(bc.upcoming_birthdays(args.get("days", 7)), indent=2)
            case "delete_birthday":
                return bc.delete_birthday(args["name"])
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
    """Run a natural-language birthday task via the Claude agent."""
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
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
