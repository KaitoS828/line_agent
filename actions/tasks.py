"""タスク管理アクション — JSONファイルベースのシンプルなタスク管理"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"


def _ensure_file():
    """タスクファイルが無ければ作成"""
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]", encoding="utf-8")


def _load() -> list:
    _ensure_file()
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def _save(tasks: list):
    _ensure_file()
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(title: str, due_date: str = "", priority: str = "medium", category: str = "") -> str:
    """タスクを追加"""
    tasks = _load()
    task = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "status": "pending",
        "priority": priority,
        "category": category,
        "due_date": due_date,
        "created_at": datetime.now(JST).isoformat(),
        "completed_at": None,
    }
    tasks.append(task)
    _save(tasks)
    due_str = f" (期限: {due_date})" if due_date else ""
    return f"✅ タスク追加: 「{title}」{due_str} [ID: {task['id']}]"


def complete_task(task_id: str) -> str:
    """タスクを完了にする"""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "completed"
            t["completed_at"] = datetime.now(JST).isoformat()
            _save(tasks)
            return f"✅ 完了: 「{t['title']}」"
    return f"❌ タスクID {task_id} が見つかりません"


def delete_task(task_id: str) -> str:
    """タスクを削除"""
    tasks = _load()
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            removed = tasks.pop(i)
            _save(tasks)
            return f"🗑️ 削除: 「{removed['title']}」"
    return f"❌ タスクID {task_id} が見つかりません"


def list_tasks(status: str = "pending", category: str = "") -> str:
    """タスク一覧を取得"""
    tasks = _load()
    filtered = [t for t in tasks if t["status"] == status]
    if category:
        filtered = [t for t in filtered if t.get("category") == category]

    if not filtered:
        label = "未完了" if status == "pending" else status
        return f"📋 {label}のタスクはありません"

    # 優先度でソート
    priority_order = {"high": 0, "medium": 1, "low": 2}
    filtered.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

    lines = [f"📋 タスク一覧 ({status}) — {len(filtered)}件"]
    for t in filtered:
        pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "⚪")
        due = f" 📅{t['due_date']}" if t.get("due_date") else ""
        cat = f" [{t['category']}]" if t.get("category") else ""
        lines.append(f"  {pri_icon} {t['title']}{due}{cat}  (ID: {t['id']})")
    return "\n".join(lines)


def update_task(task_id: str, title: str = "", priority: str = "", due_date: str = "", category: str = "") -> str:
    """タスクを更新"""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            if title:
                t["title"] = title
            if priority:
                t["priority"] = priority
            if due_date:
                t["due_date"] = due_date
            if category:
                t["category"] = category
            _save(tasks)
            return f"✏️ 更新: 「{t['title']}」"
    return f"❌ タスクID {task_id} が見つかりません"


def get_due_tasks() -> str:
    """期限が今日または過ぎているタスクを取得"""
    tasks = _load()
    today = datetime.now(JST).strftime("%Y-%m-%d")

    overdue = []
    due_today = []
    for t in tasks:
        if t["status"] != "pending" or not t.get("due_date"):
            continue
        if t["due_date"] < today:
            overdue.append(t)
        elif t["due_date"] == today:
            due_today.append(t)

    lines = []
    if overdue:
        lines.append(f"⚠️ 期限超過 ({len(overdue)}件):")
        for t in overdue:
            lines.append(f"  🔴 {t['title']} (期限: {t['due_date']})")
    if due_today:
        lines.append(f"📅 今日が期限 ({len(due_today)}件):")
        for t in due_today:
            lines.append(f"  🟡 {t['title']}")
    if not lines:
        return None
    return "\n".join(lines)
