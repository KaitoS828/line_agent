"""毎日決まった時間にLINEへ通知を送るスケジューラー"""

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import MORNING_NOTIFY_HOUR, MORNING_NOTIFY_MINUTE, EVENING_NOTIFY_HOUR, EVENING_NOTIFY_MINUTE
from actions.tasks import get_due_tasks

JST = timezone(timedelta(hours=9))


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
        try:
            dt = datetime.fromisoformat(start_raw)
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            time_str = "終日"
        lines.append(f"  • {time_str}  {e['summary']}")
    return "\n".join(lines)


def _build_morning_message(events_text: str | None, tasks_text: str | None) -> str:
    """朝のダイジェストメッセージを組み立てる"""
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日(%a)")
    weekday_ja = {"Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木", "Fri": "金", "Sat": "土", "Sun": "日"}
    for en, ja in weekday_ja.items():
        date_str = date_str.replace(en, ja)

    msg = f"☀️ おはようございます！\n📆 {date_str}\n"

    # カレンダー予定
    if events_text:
        msg += f"\n📋 今日の予定:\n{events_text}"
    else:
        msg += "\n📋 今日の予定はありません"

    # タスク期限通知
    if tasks_text:
        msg += f"\n\n{tasks_text}"

    msg += "\n\n今日も良い一日を！💪"
    return msg


def _build_evening_message(tasks_text: str | None) -> str:
    """夜のリマインダーメッセージ"""
    msg = "🌙 お疲れさまでした！\n"

    if tasks_text:
        msg += f"\n{tasks_text}"
    else:
        msg += "\n✅ 期限が迫っているタスクはありません。ゆっくり休んでください！"

    return msg


# ── ジョブ関数 ─────────────────────────────────────────────────


async def send_morning_digest(send_fn, calendar_actions, user_id: str):
    """朝のダイジェストを送信（カレンダー + タスク期限）"""
    try:
        events_text = _get_today_events(calendar_actions)
        tasks_text = get_due_tasks()
        message = _build_morning_message(events_text, tasks_text)
        await send_fn(user_id, message)
    except Exception as e:
        await send_fn(user_id, f"⚠️ 朝の通知でエラーが発生しました:\n{str(e)}")


async def send_evening_reminder(send_fn, user_id: str):
    """夜のタスクリマインダーを送信"""
    try:
        tasks_text = get_due_tasks()
        message = _build_evening_message(tasks_text)
        await send_fn(user_id, message)
    except Exception as e:
        await send_fn(user_id, f"⚠️ 夜の通知でエラーが発生しました:\n{str(e)}")


# ── スケジューラー作成 ─────────────────────────────────────────


def create_scheduler(send_fn, calendar_actions, user_id: str) -> AsyncIOScheduler:
    """スケジューラーを作成して返す"""
    scheduler = AsyncIOScheduler(timezone=JST)

    # 毎朝のダイジェスト（カレンダー + タスク期限）
    scheduler.add_job(
        send_morning_digest,
        trigger=CronTrigger(hour=MORNING_NOTIFY_HOUR, minute=MORNING_NOTIFY_MINUTE, timezone=JST),
        args=[send_fn, calendar_actions, user_id],
        id="morning_digest",
        name="朝のダイジェスト通知",
        replace_existing=True,
    )

    # 毎晩のタスクリマインダー
    scheduler.add_job(
        send_evening_reminder,
        trigger=CronTrigger(hour=EVENING_NOTIFY_HOUR, minute=EVENING_NOTIFY_MINUTE, timezone=JST),
        args=[send_fn, user_id],
        id="evening_reminder",
        name="夜のタスクリマインダー",
        replace_existing=True,
    )

    return scheduler
