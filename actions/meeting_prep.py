"""会議前リサーチアクション — カレンダー連動の自動準備"""

import hashlib
from datetime import datetime, timedelta, timezone

import anthropic
from config import ANTHROPIC_API_KEY, SUPABASE_URL
from actions import web_search

JST = timezone(timedelta(hours=9))

# 通知済み会議IDを追跡（メモリ内。再起動でリセットされるが問題なし）
_notified_events: set[str] = set()


def get_upcoming_meetings(calendar_actions, minutes_ahead: int = 45) -> list[dict]:
    """指定時間以内に始まる会議を取得"""
    now = datetime.now(JST)
    cutoff = now + timedelta(minutes=minutes_ahead)

    events_result = (
        calendar_actions.service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=cutoff.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    meetings = []
    for e in events:
        event_id = e.get("id", "")
        if event_id in _notified_events:
            continue
        start_raw = e["start"].get("dateTime")
        if not start_raw:
            continue
        try:
            start_dt = datetime.fromisoformat(start_raw)
            minutes_until = (start_dt - now).total_seconds() / 60
            if 15 <= minutes_until <= minutes_ahead:
                meetings.append({
                    "id": event_id,
                    "title": e.get("summary", "無題の会議"),
                    "description": e.get("description", ""),
                    "start": start_dt.strftime("%H:%M"),
                    "end": e.get("end", {}).get("dateTime", ""),
                    "attendees": [a.get("email", "") for a in e.get("attendees", [])],
                })
        except (ValueError, TypeError):
            continue
    return meetings


def prepare_brief(title: str, description: str = "") -> str:
    """会議トピックをリサーチして概要を作成"""
    # Web検索で関連情報を収集
    search_query = title
    if description:
        search_query += f" {description[:100]}"

    try:
        search_results = web_search.search(search_query, max_results=3)
    except Exception:
        search_results = ""

    # Claudeで簡潔なブリーフィングを生成
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""以下の会議について、簡潔な準備ブリーフィングを作成してください。

会議タイトル: {title}
説明: {description or '(なし)'}

関連Web検索結果:
{search_results[:2000] if search_results else '(検索結果なし)'}

## 出力フォーマット（箇条書きで簡潔に）
- 会議の主要トピック
- 関連する最新情報（あれば）
- 準備すべきポイント"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def check_and_prepare(calendar_actions) -> list[str]:
    """直近の会議をチェックして、ブリーフィングを生成"""
    meetings = get_upcoming_meetings(calendar_actions, minutes_ahead=45)
    briefs = []

    for meeting in meetings:
        brief_content = prepare_brief(meeting["title"], meeting["description"])
        if brief_content:
            end_str = ""
            if meeting["end"]:
                try:
                    end_dt = datetime.fromisoformat(meeting["end"])
                    end_str = f"-{end_dt.strftime('%H:%M')}"
                except (ValueError, TypeError):
                    pass

            msg = (
                f"🔔 まもなく会議があります\n\n"
                f"📋 {meeting['title']} ({meeting['start']}{end_str})\n\n"
                f"📊 準備ブリーフィング:\n{brief_content}"
            )
            briefs.append(msg)
            _notified_events.add(meeting["id"])

    return briefs
