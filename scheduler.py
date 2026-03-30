"""スケジューラー — 能動的通知の中枢"""

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    MORNING_NOTIFY_HOUR, MORNING_NOTIFY_MINUTE,
    EVENING_NOTIFY_HOUR, EVENING_NOTIFY_MINUTE,
    SUPABASE_URL,
)
from actions.tasks import get_due_tasks
from actions.weather import get_weather

JST = timezone(timedelta(hours=9))


# ── 天気 & メール取得ヘルパー ─────────────────────────────────


def _get_weather_text() -> str:
    """天気情報を安全に取得"""
    try:
        return get_weather()
    except Exception:
        return ""


def _get_email_summary(gmail_actions) -> str:
    """未読メールのサマリーを取得"""
    if not gmail_actions:
        return ""
    try:
        result = gmail_actions.service.users().messages().list(
            userId="me", q="is:unread", maxResults=5
        ).execute()
        messages = result.get("messages", [])
        total = result.get("resultSizeEstimate", 0)
        if not messages:
            return ""

        lines = [f"📧 未読メール: {total}件"]
        for msg_info in messages[:5]:
            msg = gmail_actions.service.users().messages().get(
                userId="me", id=msg_info["id"], format="metadata",
                metadataHeaders=["Subject", "From"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            sender = headers.get("From", "不明").split("<")[0].strip()
            subject = headers.get("Subject", "(件名なし)")
            lines.append(f"  • {sender}: {subject}")
        return "\n".join(lines)
    except Exception:
        return ""


# ── カレンダー予定取得 ─────────────────────────────────────────


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


# ── メッセージ構築 ─────────────────────────────────────────────


def _build_morning_message(
    events_text: str | None,
    tasks_text: str | None,
    weather_text: str = "",
) -> str:
    """朝のダイジェストメッセージ"""
    now = datetime.now(JST)
    weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
    date_str = now.strftime("%Y年%m月%d日") + f"({weekday_ja[now.weekday()]})"

    msg = f"おはよー！\n{date_str}\n"

    if weather_text:
        msg += f"\n{weather_text}\n"

    if events_text:
        msg += f"\n今日の予定:\n{events_text}"
    else:
        msg += "\n今日は予定なしだよ"

    if tasks_text:
        msg += f"\n\n{tasks_text}"

    msg += "\n\n今日もいってらっしゃい！"
    return msg


def _build_evening_message(tasks_text: str | None) -> str:
    """夜のリマインダーメッセージ"""
    msg = "おつかれ！\n"
    if tasks_text:
        msg += f"\n{tasks_text}"
    else:
        msg += "\n期限が迫ってるタスクはないよ。ゆっくり休んで！"
    return msg


# ── ジョブ関数 ─────────────────────────────────────────────────


async def send_morning_digest(send_fn, services: dict, user_id: str):
    """朝のダイジェスト（カレンダー + タスク + 天気）"""
    try:
        events_text = _get_today_events(services["calendar"])
        tasks_text = get_due_tasks()
        weather_text = _get_weather_text()
        message = _build_morning_message(events_text, tasks_text, weather_text)
        await send_fn(user_id, message)
    except Exception as e:
        await send_fn(user_id, f"朝の通知でエラーが出たわ:\n{str(e)}")


async def send_evening_reminder(send_fn, user_id: str):
    """夜のタスクリマインダー"""
    try:
        tasks_text = get_due_tasks()
        message = _build_evening_message(tasks_text)
        await send_fn(user_id, message)
    except Exception as e:
        await send_fn(user_id, f"⚠️ 夜の通知でエラーが発生しました:\n{str(e)}")


async def check_monitors_job(send_fn, user_id: str):
    """監視対象を定期チェック"""
    try:
        from actions.monitors import check_all_monitors
        alerts = check_all_monitors()
        for alert in alerts:
            await send_fn(user_id, alert)
    except Exception:
        pass


async def check_meeting_prep_job(send_fn, services: dict, user_id: str):
    """会議前リサーチを自動実行"""
    try:
        from actions.meeting_prep import check_and_prepare
        briefs = check_and_prepare(services["calendar"])
        for brief in briefs:
            await send_fn(user_id, brief)
    except Exception:
        pass


async def send_end_of_work_notification(send_fn, user_id: str):
    """平日17:15の定時通知"""
    try:
        await send_fn(user_id, "おつかれー定時だよー🕔")
    except Exception as e:
        await send_fn(user_id, f"⚠️ 定時通知でエラーが発生しました:\n{str(e)}")


async def summarize_conversations_job():
    """古い会話履歴を要約して圧縮"""
    if not SUPABASE_URL:
        return
    try:
        from actions.memory import summarize_old_messages
        from config import LINE_AUTHORIZED_USER_ID
        summarize_old_messages(LINE_AUTHORIZED_USER_ID)
    except Exception:
        pass


# ── スケジューラー作成 ─────────────────────────────────────────


def create_scheduler(send_fn, services: dict, user_id: str) -> AsyncIOScheduler:
    """スケジューラーを作成して返す"""
    scheduler = AsyncIOScheduler(timezone=JST)

    # 毎朝のダイジェスト
    scheduler.add_job(
        send_morning_digest,
        trigger=CronTrigger(hour=MORNING_NOTIFY_HOUR, minute=MORNING_NOTIFY_MINUTE, timezone=JST),
        args=[send_fn, services, user_id],
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

    # 監視チェック（30分間隔）
    if SUPABASE_URL:
        scheduler.add_job(
            check_monitors_job,
            trigger=IntervalTrigger(minutes=30),
            args=[send_fn, user_id],
            id="monitor_check",
            name="監視チェック",
            replace_existing=True,
        )

    # 会議前リサーチ（15分間隔）
    scheduler.add_job(
        check_meeting_prep_job,
        trigger=IntervalTrigger(minutes=15),
        args=[send_fn, services, user_id],
        id="meeting_prep_check",
        name="会議前リサーチチェック",
        replace_existing=True,
    )

    # 平日17:15の定時通知
    scheduler.add_job(
        send_end_of_work_notification,
        trigger=CronTrigger(day_of_week="mon-fri", hour=17, minute=15, timezone=JST),
        args=[send_fn, user_id],
        id="end_of_work",
        name="定時通知",
        replace_existing=True,
    )

    # 会話履歴の要約（深夜3時）
    if SUPABASE_URL:
        scheduler.add_job(
            summarize_conversations_job,
            trigger=CronTrigger(hour=3, minute=0, timezone=JST),
            id="conversation_summary",
            name="会話履歴の要約",
            replace_existing=True,
        )

    return scheduler
