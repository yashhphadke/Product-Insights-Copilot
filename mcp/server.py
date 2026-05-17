from fastmcp import FastMCP

import os
import pickle
import base64

from email.mime.text import MIMEText

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# =========================
# MCP SERVER
# =========================
mcp = FastMCP("ProductCopilotServer")


# =========================
# SCOPES
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents"
]


# =========================
# AUTH (shared for all tools)
# =========================
def get_creds():
    creds = None

    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.pkl", "wb") as f:
            pickle.dump(creds, f)

    return creds


# =========================
# TOOL 1: ADDER
# =========================
@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b


# =========================
# TOOL 2: CREATE GMAIL DRAFT
# =========================
@mcp.tool()
def create_email_draft(to: str, subject: str, body: str):
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = {
        "message": {
            "raw": raw
        }
    }

    result = service.users().drafts().create(
        userId="me",
        body=draft
    ).execute()

    return {"Mail in your Draft"}

# =========================
# TOOL 3: APPEND TO GOOGLE DOC
# =========================
@mcp.tool()
def append_to_doc(document_id: str, text: str):
    creds = get_creds()
    service = build("docs", "v1", credentials=creds)

    doc = service.documents().get(documentId=document_id).execute()
    content = doc.get("body", {}).get("content", [])

    end_index = None
    for block in reversed(content):
        if "endIndex" in block:
            end_index = block["endIndex"] - 1
            break

    if end_index is None:
        return {"error": "Could not find document end index"}

    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": text + "\n"
            }
        }
    ]

    service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": requests}
    ).execute()

    return {"Insights Successfully Appended"}


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    mcp.run()