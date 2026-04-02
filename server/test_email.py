"""Test Gmail API — read latest email."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import config
from auth.gmail_oauth import GmailAuth
import base64
from email.header import decode_header


def decode_mime_header(value):
    if value is None:
        return ""
    decoded = decode_header(value)
    parts = []
    for data, charset in decoded:
        if isinstance(data, bytes):
            parts.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(data)
    return "".join(parts)


def get_body(service, msg_id):
    msg = (
        service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    )
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    subject = ""
    from_addr = ""
    date = ""
    for h in headers:
        if h["name"] == "Subject":
            subject = decode_mime_header(h["value"])
        elif h["name"] == "From":
            from_addr = decode_mime_header(h["value"])
        elif h["name"] == "Date":
            date = h["value"]

    # Extract body
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "body" in part:
                data = part["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
                    break
            elif part.get("mimeType") == "text/html" and "body" in part:
                data = part["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
    elif "body" in payload:
        data = payload["body"].get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    print(f"\n{'=' * 60}")
    print(f"From:    {from_addr}")
    print(f"Date:    {date}")
    print(f"Subject: {subject}")
    print(f"{'=' * 60}")
    print(body[:500] if len(body) > 500 else body)
    print(f"{'=' * 60}")


async def main():
    print("Testing Gmail API...")
    gmail = GmailAuth(config.email.credentials_path, config.email.token_path)
    await gmail.authenticate()
    service = gmail._service

    # List latest 5 emails
    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=5, labelIds=["INBOX"])
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        print("No emails found.")
        return

    print(f"Found {len(messages)} recent emails.\n")

    for i, msg in enumerate(messages):
        msg_id = msg["id"]
        thread_id = msg.get("threadId", "")
        detail = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            )
            .execute()
        )
        headers = detail.get("payload", {}).get("headers", [])
        subject = from_addr = date = ""
        for h in headers:
            if h["name"] == "Subject":
                subject = decode_mime_header(h["value"])
            elif h["name"] == "From":
                from_addr = decode_mime_header(h["value"])
            elif h["name"] == "Date":
                date = h["value"]
        print(f"[{i + 1}] {subject}")
        print(f"    From: {from_addr}")
        print(f"    Date: {date}")
        print()

    # Read the latest email body
    print("Reading latest email body...")
    get_body(service, messages[0]["id"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
