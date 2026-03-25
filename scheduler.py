"""毎日決まった時間にLINEへ通知を送るスケジューラー"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

JST = timezone(timedelta(hours=9))

# 通知時刻（環境変数で変更可。デフォルト 07:00 JST）
MORNING_HOUR = int(os.environ.get("MORNING_NOTIFY_HOUR", "7"))
MORNING_MINUTE = int(os.environ.get("MORNING_NOTIFY_MINUTE", "0"))


def _get_today_events(calendar_actions) -> str:
    """当日の予定を取得してフォーマットする"""
    now = datetime.now(JST)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    events_result = (
        calendar_actions.service.events()
        .list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    if not events:
        return None

    lines = []
    for e in events:
        start_raw = e["start"].get("dateTime", e["start"].get("date", ""))
        # 時刻を見やすくフォーマット
        try:
            dt = datetime.fromisoformat(start_raw)
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            time_str = "終日"
        lines.append(f"  • {time_str}  {e['summary']}")
    return "\n".join(lines)


def _build_morning_message(events_text: str | None) -> str:
    """朝の挨拶メッセージを組み立てる"""
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日(%a)")
    weekday_ja = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木", "Fri": "金", "Sat": "土", "Sun": "日"}
    for en, ja in weekday_ja.items():
        date_str = date_str.replace(en, ja)

    msg = f"☀️ おはようございます！\n📆 {date_str}\n"

    if events_text:
        msg += f"\n📋 今日の予定:\n{events_text}"
    else:
        msg += "\n📋 今日の予定はありません。自由な一日ですね！"

    msg += "\n\n今日も良い一日を！💪"
    return msg


async def send_morning_digest(send_fn, calendar_actions, user_id: str):
    """朝のダイジェストを送信"""
    try:
        events_text = _get_today_events(calendar_actions)
        message = _build_morning_message(events_text)
        await send_fn(user_id, message)
    except Exception as e:
        await send_fn(user_id, f"⚠️ 朝の通知でエラーが発生しました:\n{str(e)}")


def create_scheduler(send_fn, calendar_actions, user_id: str) -> AsyncIOScheduler:
    """スケジューラーを作成して返す"""
    scheduler = AsyncIOScheduler(timezone=JST)

    # 毎朝の通知
    scheduler.add_job(
        send_morning_digest,
        trigger=CronTrigger(hour=MORNING_HOUR, minute=MORNING_MINUTE, timezone=JST),
        args=[send_fn, calendar_actions, user_id],
        id="morning_digest",
        name="朝のダイジェスト通知",
        replace_existing=True,
    )

    return scheduler
