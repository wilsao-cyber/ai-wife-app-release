"""Test Google Calendar API — create a reminder at 4/8 10:30."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import config
from auth.google_calendar_oauth import GoogleCalendarAuth
from datetime import datetime, timedelta


async def main():
    print("Testing Google Calendar API...")
    cal = GoogleCalendarAuth(
        config.calendar.credentials_path,
        config.calendar.token_path,
    )
    await cal.authenticate()
    service = cal._service

    # Step 1: Show upcoming events
    print("\nUpcoming events (next 7 days):")
    now = datetime.utcnow().isoformat() + "Z"
    later = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            timeMax=later,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    if not events:
        print("  No upcoming events found.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"  {start} — {event.get('summary', '(no title)')}")

    # Step 2: Create a reminder at 2026-04-08 10:30
    reminder_time = datetime(2026, 4, 8, 10, 30)
    end_time = reminder_time + timedelta(minutes=30)

    event_body = {
        "summary": "工作提醒 (AI Wife)",
        "description": "由 AI 老婆建立的工作提醒",
        "start": {"dateTime": reminder_time.isoformat(), "timeZone": "Asia/Taipei"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Taipei"},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 10},
            ],
        },
    }

    print(f"\nCreating reminder at {reminder_time.strftime('%Y-%m-%d %H:%M')}...")
    created = service.events().insert(calendarId="primary", body=event_body).execute()
    print(f"  Created! ID: {created['id']}")
    print(f"  Link: {created.get('htmlLink', 'N/A')}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
