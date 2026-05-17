import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, "..", "..")  
TOKEN_PATH = os.path.join(ROOT_DIR, "token.pkl")
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")

# If you already use Gmail too, combine scopes like this:
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents"
]


# ---------- AUTH ----------
def get_creds():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(CREDENTIALS_PATH),
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return creds


# ---------- DOC SERVICE ----------
def get_docs_service(creds):
    return build("docs", "v1", credentials=creds)


# ---------- APPEND FUNCTION ----------
def append_to_doc(service, document_id, text):
    doc = service.documents().get(documentId=document_id).execute()

    content = doc.get("body", {}).get("content", [])

    # Find last valid index safely
    end_index = None

    for block in reversed(content):
        if "endIndex" in block:
            end_index = block["endIndex"] - 1
            break

    if end_index is None:
        raise Exception("Could not determine document end index")

    requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index
                },
                "text": text + "\n"
            }
        }
    ]

    service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": requests}
    ).execute()

    print("✅ Text appended successfully")


# ---------- MAIN ----------
if __name__ == "__main__":
    creds = get_creds()
    # docs_service = get_docs_service(creds)

    # DOCUMENT_ID = "1_P5utVK2YFkCBRB-Pyz2QRT9bPJLxX2T0uYoxjNaoOg"

    # append_to_doc(
    #     docs_service,
    #     DOCUMENT_ID,
    #     "Hello! This line was appended via Google Docs API 🚀"
    # )