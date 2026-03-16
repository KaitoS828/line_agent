from datetime import datetime, timezone
from googleapiclient.discovery import build


class CalendarActions:
    def __init__(self, creds):
        self.service = build("calendar", "v3", credentials=creds)

    def list_events(self, max_results: int = 10, calendar_id: str = "primary") -> str:
        now = datetime.now(timezone.utc).isoformat()
        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        if not events:
            return "予定はありません"
        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            lines.append(f"📅 {e['summary']}\n   開始: {start}\n   ID: {e['id']}")
        return "\n".join(lines)

    def create_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        calendar_id: str = "primary",
    ) -> str:
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start, "timeZone": "Asia/Tokyo"},
            "end": {"dateTime": end, "timeZone": "Asia/Tokyo"},
        }
        result = (
            self.service.events()
            .insert(calendarId=calendar_id, body=event)
            .execute()
        )
        return (
            f"✅ 予定作成: {result['summary']}\n"
            f"開始: {result['start'].get('dateTime', '')}\n"
            f"ID: {result['id']}\n"
            f"URL: {result.get('htmlLink', 'N/A')}"
        )

    def update_event(
        self,
        event_id: str,
        title: str = None,
        start: str = None,
        end: str = None,
        description: str = None,
        calendar_id: str = "primary",
    ) -> str:
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        if title:
            event["summary"] = title
        if description is not None:
            event["description"] = description
        if start:
            event["start"] = {"dateTime": start, "timeZone": "Asia/Tokyo"}
        if end:
            event["end"] = {"dateTime": end, "timeZone": "Asia/Tokyo"}
        result = (
            self.service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        return f"✅ 予定更新: {result['summary']} (ID: {result['id']})"

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> str:
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return f"✅ 予定削除完了 (ID: {event_id})"

    def search_events(self, query: str, calendar_id: str = "primary") -> str:
        events_result = (
            self.service.events()
            .list(calendarId=calendar_id, q=query, maxResults=10, singleEvents=True, orderBy="startTime")
            .execute()
        )
        events = events_result.get("items", [])
        if not events:
            return f"「{query}」に一致する予定はありません"
        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            lines.append(f"📅 {e['summary']}\n   開始: {start}\n   ID: {e['id']}")
        return "\n".join(lines)
