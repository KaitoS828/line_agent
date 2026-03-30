"""会話記憶アクション — 会話履歴の保存・取得・要約"""

from datetime import datetime, timedelta, timezone

import anthropic
from config import ANTHROPIC_API_KEY
from db import get_db

JST = timezone(timedelta(hours=9))


def save_message(user_id: str, role: str, content: str) -> None:
    """メッセージを保存"""
    db = get_db()
    db.table("conversations").insert({
        "user_id": user_id,
        "role": role,
        "content": content[:5000],
    }).execute()


def get_recent_messages(user_id: str, limit: int = 20) -> list[dict]:
    """直近のメッセージを取得"""
    db = get_db()
    result = db.table("conversations") \
        .select("role, content, created_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    return list(reversed(result.data)) if result.data else []


def get_conversation_context(user_id: str) -> str:
    """CEOのsystem promptに注入する会話コンテキストを生成（要約＋直近10件）"""
    db = get_db()

    # 最新の要約を取得
    summary_result = db.table("conversations") \
        .select("content") \
        .eq("user_id", user_id) \
        .eq("role", "summary") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    # 直近10件の通常メッセージを取得
    messages = get_recent_messages(user_id, limit=10)

    lines = []

    if summary_result.data:
        lines.append("【過去の会話要約】")
        lines.append(summary_result.data[0]["content"])

    if messages:
        lines.append("【直近の会話】")
        for msg in messages:
            prefix = "ユーザー" if msg["role"] == "user" else "かんべ"
            lines.append(f"{prefix}: {msg['content'][:200]}")

    return "\n".join(lines) if lines else ""


def summarize_old_messages(user_id: str, keep_recent: int = 30) -> None:
    """古いメッセージを要約して圧縮"""
    db = get_db()

    # 全メッセージ数を確認
    all_msgs = db.table("conversations") \
        .select("id, role, content, created_at") \
        .eq("user_id", user_id) \
        .neq("role", "summary") \
        .order("created_at", desc=False) \
        .execute()

    if not all_msgs.data or len(all_msgs.data) <= keep_recent:
        return

    # 古いメッセージ（要約対象）
    old_msgs = all_msgs.data[:-keep_recent]
    if len(old_msgs) < 10:
        return

    # Claudeで要約
    conversation_text = "\n".join(
        f"{'ユーザー' if m['role'] == 'user' else 'アシスタント'}: {m['content'][:200]}"
        for m in old_msgs
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="あなたは会話要約の専門家です。以下の会話履歴を5つ以内の箇条書きで要約してください。重要な情報・決定事項・ユーザーの好みを中心に。",
        messages=[{"role": "user", "content": conversation_text}],
    )

    summary = ""
    for block in response.content:
        if hasattr(block, "text"):
            summary = block.text
            break

    if summary:
        # 要約を保存
        db.table("conversations").insert({
            "user_id": user_id,
            "role": "summary",
            "content": summary,
        }).execute()

        # 古いメッセージを削除
        old_ids = [m["id"] for m in old_msgs]
        for batch_start in range(0, len(old_ids), 50):
            batch = old_ids[batch_start:batch_start + 50]
            db.table("conversations") \
                .delete() \
                .in_("id", batch) \
                .execute()
