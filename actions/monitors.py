"""監視アクション — Webサイト変更検知・キーワードアラート"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from db import get_db
from actions import web_search

JST = timezone(timedelta(hours=9))


def add_monitor(name: str, monitor_type: str, config: dict) -> str:
    """監視対象を追加"""
    db = get_db()
    monitor_id = str(uuid.uuid4())[:8]

    db.table("monitors").insert({
        "id": monitor_id,
        "name": name,
        "type": monitor_type,
        "config": config,
        "enabled": True,
    }).execute()

    type_label = "Webサイト変更検知" if monitor_type == "website_change" else "キーワードアラート"
    return f"✅ 監視追加: 「{name}」({type_label}) [ID: {monitor_id}]"


def list_monitors() -> str:
    """監視対象一覧"""
    db = get_db()
    result = db.table("monitors") \
        .select("*") \
        .eq("enabled", True) \
        .order("created_at", desc=False) \
        .execute()

    monitors = result.data or []
    if not monitors:
        return "📡 有効な監視対象はありません"

    lines = [f"📡 監視一覧 — {len(monitors)}件"]
    for m in monitors:
        type_icon = "🌐" if m["type"] == "website_change" else "🔍"
        config = m["config"] if isinstance(m["config"], dict) else json.loads(m["config"])
        target = config.get("url", config.get("keyword", ""))
        last = m.get("last_checked", "未チェック")
        lines.append(f"  {type_icon} {m['name']}: {target}")
        lines.append(f"     最終チェック: {last}  (ID: {m['id']})")
    return "\n".join(lines)


def remove_monitor(monitor_id: str) -> str:
    """監視を停止"""
    db = get_db()
    result = db.table("monitors") \
        .update({"enabled": False}) \
        .eq("id", monitor_id) \
        .execute()

    if result.data:
        return f"🛑 監視停止: {result.data[0]['name']}"
    return f"❌ 監視ID {monitor_id} が見つかりません"


def check_single_monitor(monitor: dict) -> str | None:
    """単一の監視対象をチェック。変更があればアラート文を返す"""
    db = get_db()
    config = monitor["config"] if isinstance(monitor["config"], dict) else json.loads(monitor["config"])
    now = datetime.now(JST).isoformat()

    if monitor["type"] == "website_change":
        url = config.get("url", "")
        if not url:
            return None
        try:
            content = web_search.get_page_content(url)
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            db.table("monitors") \
                .update({"last_checked": now, "last_hash": content_hash}) \
                .eq("id", monitor["id"]) \
                .execute()

            if monitor.get("last_hash") and monitor["last_hash"] != content_hash:
                return (
                    f"🔔 Webサイト変更検知！\n"
                    f"📡 {monitor['name']}\n"
                    f"🌐 {url}\n"
                    f"内容が更新されました。"
                )
        except Exception:
            pass

    elif monitor["type"] == "keyword_alert":
        keyword = config.get("keyword", "")
        if not keyword:
            return None
        try:
            results = web_search.search(keyword, max_results=3)
            results_hash = hashlib.sha256(results.encode()).hexdigest()

            db.table("monitors") \
                .update({"last_checked": now, "last_hash": results_hash}) \
                .eq("id", monitor["id"]) \
                .execute()

            if monitor.get("last_hash") and monitor["last_hash"] != results_hash:
                return (
                    f"🔔 キーワードアラート！\n"
                    f"🔍 「{keyword}」に新しい情報があります\n\n"
                    f"{results[:1000]}"
                )
        except Exception:
            pass

    return None


def check_all_monitors() -> list[str]:
    """全監視対象をチェック。アラートのリストを返す"""
    db = get_db()
    result = db.table("monitors") \
        .select("*") \
        .eq("enabled", True) \
        .execute()

    monitors = result.data or []
    alerts = []
    for m in monitors:
        alert = check_single_monitor(m)
        if alert:
            alerts.append(alert)
    return alerts
