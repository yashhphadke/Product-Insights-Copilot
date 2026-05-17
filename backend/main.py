import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from dotenv import load_dotenv

from backend.pulse_generation.pulsegenerator import get_pulse

BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(BASE_DIR / ".env")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a tool-calling assistant.

You have access to these tools:

1. add
   - Adds two numbers
   - args: { "a": int, "b": int }

2. create_email_draft
   - Creates a Gmail draft
   - args: { "to": string, "subject": string, "body": string }

3. append_to_doc
   - Appends text to a Google Doc
   - args: { "document_id": string, "text": string }

RULES:
- Respond ONLY in JSON
- Choose exactly ONE tool
- Format MUST be:
{
  "tool": "...",
  "arguments": { ... }
}
- No extra text
"""

app = FastAPI(title="Pulse + MCP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No StaticFiles — frontend/index.html is opened directly in the browser.


# ── Pydantic models ──────────────────────────────────────────────────────────
class Numbers(BaseModel):
    num1: float
    num2: float
    num3: float

class ChatRequest(BaseModel):
    message: str

class DocRequest(BaseModel):
    document_id: str
    text: str

class EmailRequest(BaseModel):
    to: str
    body: str


# ── helpers ──────────────────────────────────────────────────────────────────
def _make_mcp_client() -> Client:
    server_path = str(BASE_DIR.parent /"backend"/ "mcp" / "server.py")
    return Client(PythonStdioTransport(server_path))

def _parse_tool_call(text: str):
    try:
        data = json.loads(text)
    except Exception as exc:
        raise ValueError(f"LLM returned invalid JSON:\n{text}") from exc
    tool_name = data.get("tool")
    if not tool_name:
        raise ValueError(f"No 'tool' key in LLM response:\n{data}")
    tool_args = data.get("arguments") or {k: v for k, v in data.items() if k != "tool"}
    return tool_name, tool_args

def _serialize(result) -> list:
    blocks = result.content if hasattr(result, "content") else result
    return [block.model_dump() if hasattr(block, "model_dump") else str(block) for block in blocks]

result_pulse = None

# ── pulse endpoint ───────────────────────────────────────────────────────────
@app.post("/get_pulse_data")
def add_numbers(data: Numbers):
    result_pulse = get_pulse(data.num1, data.num2, data.num3)
    return {"sum": result_pulse}


# ── MCP: list tools ──────────────────────────────────────────────────────────
@app.get("/mcp/tools")
async def list_tools():
    async with _make_mcp_client() as mcp:
        tools = await mcp.list_tools()
    return {"tools": [t.model_dump() for t in tools]}


# ── MCP: natural-language chat ───────────────────────────────────────────────
@app.post("/mcp/chat")
async def mcp_chat(req: ChatRequest):
    llm_resp = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": req.message},
        ],
        temperature=0,
    )
    raw = llm_resp.choices[0].message.content
    try:
        tool_name, tool_args = _parse_tool_call(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    async with _make_mcp_client() as mcp:
        result = await mcp.call_tool(tool_name, tool_args)
    return {"tool": tool_name, "arguments": tool_args, "result": _serialize(result)}


# ── MCP: direct endpoints ────────────────────────────────────────────────────
@app.post("/mcp/append_to_doc")
async def append_to_doc(req: DocRequest):
    async with _make_mcp_client() as mcp:
        result = await mcp.call_tool("append_to_doc", {"document_id": req.document_id, "text": req.text})
    return {"result": _serialize(result)}


@app.post("/mcp/create_email_draft")
async def create_email_draft(req: EmailRequest):
    async with _make_mcp_client() as mcp:
        result = await mcp.call_tool("create_email_draft", {"to": req.to, "subject": "Weekly Pulse Report + Fee Clarification", "body": req.body})
    return {"result": _serialize(result)}