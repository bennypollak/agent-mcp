"""
Birthdays Agent Service
-----------------------
Model-agnostic. Tools are loaded dynamically from server.py (MCP) —
no duplicate tool definitions.

Start:
    python agent.py          # http://0.0.0.0:8001  (override with BIRTHDAYS_PORT)

Endpoints:
    POST /run_task   { "task": "...", "model": "claude-sonnet-4-6" }
    GET  /tools      list tools loaded live from the MCP server
    GET  /health

Supported models:
    Anthropic  claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5, ...
    OpenAI     gpt-4o, gpt-4o-mini, o3-mini, ...
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

SERVER_PATH = str(Path(__file__).parent / "server.py")
PYTHON = sys.executable  # venv python that launched this process

SYSTEM_PROMPT = """\
You are a helpful birthday tracker assistant.
You can store, look up, and remind about birthdays.
When listing upcoming birthdays, always mention how many days away they are.
Respond in a friendly, natural tone.
"""

app = FastAPI(title="Birthdays Agent", version="2.0.0")


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def is_openai_model(model: str) -> bool:
    return model.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-"))


# ---------------------------------------------------------------------------
# Agent loops
# ---------------------------------------------------------------------------

async def _run_anthropic(
    task: str, model: str, mcp_tools, session
) -> tuple[str, list[dict]]:
    import anthropic

    client = anthropic.Anthropic()
    tools = [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
    ]
    messages = [{"role": "user", "content": task}]
    action_log: list[dict] = []

    for _ in range(10):
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
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
                mcp_result = await session.call_tool(block.name, block.input)
                content = mcp_result.content[0].text if mcp_result.content else ""
                action_log.append({"tool": block.name, "args": block.input, "result": content})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached.", action_log


async def _run_openai(
    task: str, model: str, mcp_tools, session
) -> tuple[str, list[dict]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    action_log: list[dict] = []

    for _ in range(10):
        resp = await client.chat.completions.create(
            model=model, tools=tools, messages=messages
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content or "Done.", action_log

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            mcp_result = await session.call_tool(tc.function.name, args)
            content = mcp_result.content[0].text if mcp_result.content else ""
            action_log.append({"tool": tc.function.name, "args": args, "result": content})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})

    return "Max iterations reached.", action_log


async def run_agent(task: str, model: str) -> tuple[str, list[dict]]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async with stdio_client(
        StdioServerParameters(command=PYTHON, args=[SERVER_PATH])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()

            if is_openai_model(model):
                return await _run_openai(task, model, tools_result.tools, session)
            else:
                return await _run_anthropic(task, model, tools_result.tools, session)


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

class TaskRequest(BaseModel):
    task: str
    model: str = "claude-sonnet-4-6"


class TaskResponse(BaseModel):
    result: str
    action_log: list[dict]
    model: str


@app.post("/run_task", response_model=TaskResponse)
async def run_task(req: TaskRequest) -> TaskResponse:
    """Run a natural-language birthday task via an Anthropic or OpenAI agent."""
    result, log = await run_agent(req.task, req.model)
    return TaskResponse(result=result, action_log=log, model=req.model)


@app.get("/tools")
async def list_tools() -> list[dict]:
    """List tools available from the MCP server."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async with stdio_client(
        StdioServerParameters(command=PYTHON, args=[SERVER_PATH])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [{"name": t.name, "description": t.description} for t in result.tools]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("BIRTHDAYS_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
