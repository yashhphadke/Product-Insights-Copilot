import base64
import os
import pickle

from email.mime.text import MIMEText

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, "..", "..")  
TOKEN_PATH = os.path.join(ROOT_DIR, "token.pkl")
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def create_draft(to, subject, body):
    service = get_gmail_service()

    message = MIMEText(body)

    message["to"] = to
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    draft_body = {
        "message": {
            "raw": raw_message
        }
    }

    draft = (
        service.users()
        .drafts()
        .create(userId="me", body=draft_body)
        .execute()
    )

    print("Draft created!")
    print("Draft ID:", draft["id"])