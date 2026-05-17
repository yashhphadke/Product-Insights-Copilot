import asyncio
import json
import os
from groq import Groq
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


SYSTEM_PROMPT = """
You are a tool-calling assistant.

You have access to these tools:

1. add
- Adds two numbers
- args: { "a": int, "b": int }

2. create_email_draft
- Creates a Gmail draft
- args: {
    "to": string,
    "subject": string,
    "body": string
  }

3. append_to_doc
- Appends text to a Google Doc
- args: {
    "document_id": string,
    "text": string
  }

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


def safe_parse_tool_call(text: str):
    """
    Robust JSON parser for LLM output
    """

    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"Invalid JSON from LLM:\n{text}") from e

    tool_name = data.get("tool")

    if not tool_name:
        raise ValueError(f"No tool found in response:\n{data}")

    tool_args = data.get("arguments")

    # fallback: flattened format support
    if tool_args is None:
        tool_args = {
            k: v for k, v in data.items()
            if k != "tool"
        }

    return tool_name, tool_args


async def main():

    transport = PythonStdioTransport("backend/mcp/server.py")
    mcp_client = Client(transport)

    async with mcp_client:

        # -----------------------------
        # INPUT (change anytime)
        # -----------------------------
        # user_input = "Send an email draft to test@gmail.com with subject Hello and body 'MCP works!'"

        user_input = "Append this text 'Weekly insights report updated' to my google document with the document id 1_P5utVK2YFkCBRB-Pyz2QRT9bPJLxX2T0uYoxjNaoOg"
        # user_input = "What is 55 + 88?"

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )

        tool_call_text = response.choices[0].message.content

        print("\n===== RAW LLM OUTPUT =====\n")
        print(tool_call_text)

        # -----------------------------
        # SAFE PARSING
        # -----------------------------
        tool_name, tool_args = safe_parse_tool_call(tool_call_text)

        print("\n===== PARSED TOOL =====\n")
        print("Tool:", tool_name)
        print("Args:", tool_args)

        # -----------------------------
        # MCP CALL
        # -----------------------------
        result = await mcp_client.call_tool(tool_name, tool_args)

        print("\n===== TOOL RESULT =====\n")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())