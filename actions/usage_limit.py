"""利用回数制限 — 日次の利用上限管理"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
DATA_DIR = Path(__file__).parent.parent / "data"
USAGE_FILE = DATA_DIR / "usage.json"

# デフォルト上限（0 = 無制限）
DEFAULT_DAILY_LIMIT = 0


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USAGE_FILE.exists():
        USAGE_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict:
    _ensure()
    return json.loads(USAGE_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    _ensure()
    USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _today() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def _get_user(data: dict, user_id: str) -> dict:
    if user_id not in data:
        data[user_id] = {
            "daily_limit": DEFAULT_DAILY_LIMIT,
            "tier": "owner",
            "last_date": "",
            "count": 0,
        }
    # Reset count if new day
    today = _today()
    if data[user_id]["last_date"] != today:
        data[user_id]["last_date"] = today
        data[user_id]["count"] = 0
    return data[user_id]


def check_and_increment(user_id: str) -> tuple[bool, str]:
    """利用可能かチェックし、可能ならカウントを増やす。
    Returns: (allowed: bool, message: str)
    """
    data = _load()
    user = _get_user(data, user_id)
    limit = user["daily_limit"]

    # 0 = unlimited
    if limit == 0:
        user["count"] += 1
        _save(data)
        return True, ""

    if user["count"] >= limit:
        remaining = 0
        return False, f"⚠️ 今日の利用上限（{limit}回）に達しました。明日またお使いください！\n現在: {user['count']}/{limit}回"

    user["count"] += 1
    _save(data)
    remaining = limit - user["count"]
    return True, ""


def get_usage_status(user_id: str) -> str:
    """利用状況を返す"""
    data = _load()
    user = _get_user(data, user_id)
    _save(data)
    limit = user["daily_limit"]
    count = user["count"]
    tier = user["tier"]

    if limit == 0:
        return f"📊 利用状況\n  今日の利用: {count}回\n  上限: 無制限\n  プラン: {tier}"

    remaining = max(0, limit - count)
    return f"📊 利用状況\n  今日の利用: {count}/{limit}回\n  残り: {remaining}回\n  プラン: {tier}"


def set_user_limit(user_id: str, limit: int) -> str:
    """ユーザーの日次上限を設定（0=無制限）"""
    data = _load()
    user = _get_user(data, user_id)
    user["daily_limit"] = limit
    _save(data)
    limit_str = "無制限" if limit == 0 else f"{limit}回/日"
    return f"✅ {user_id} の上限を {limit_str} に設定しました"


def set_user_tier(user_id: str, tier: str) -> str:
    """ユーザーのティアを設定"""
    data = _load()
    user = _get_user(data, user_id)
    user["tier"] = tier
    # Set default limits based on tier
    if tier == "free":
        user["daily_limit"] = 10
    elif tier == "pro":
        user["daily_limit"] = 50
    elif tier == "owner":
        user["daily_limit"] = 0  # unlimited
    _save(data)
    limit_str = "無制限" if user["daily_limit"] == 0 else f"{user['daily_limit']}回/日"
    return f"✅ {user_id} → {tier}プラン（{limit_str}）"
