"""Threads投稿アクション — Meta Threads API経由"""

import time
import httpx
from config import THREADS_USER_ID, THREADS_ACCESS_TOKEN

BASE_URL = "https://graph.threads.net/v1.0"


def _post(path: str, data: dict) -> dict:
    resp = httpx.post(
        f"{BASE_URL}{path}",
        params={"access_token": THREADS_ACCESS_TOKEN},
        json=data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def post_text(text: str) -> str:
    """テキストをThreadsに投稿（500文字制限）"""
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        return "❌ THREADS_ACCESS_TOKEN または THREADS_USER_ID が設定されていません"

    if len(text) > 500:
        return f"❌ 文字数オーバー（{len(text)}文字）。500文字以内にしてください"

    try:
        # ステップ1: コンテナ作成
        container = _post(f"/{THREADS_USER_ID}/threads", {
            "media_type": "TEXT",
            "text": text,
        })
        creation_id = container.get("id")
        if not creation_id:
            return f"❌ コンテナ作成失敗: {container}"

        # ステップ2: 公開（Meta推奨の待機）
        time.sleep(3)
        result = _post(f"/{THREADS_USER_ID}/threads_publish", {
            "creation_id": creation_id,
        })
        post_id = result.get("id")
        if post_id:
            return f"投稿したよ！\nhttps://www.threads.net/post/{post_id}"
        return f"❌ 公開失敗: {result}"

    except httpx.HTTPStatusError as e:
        return f"❌ APIエラー ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"❌ 投稿エラー: {e}"


def post_image(text: str, image_url: str) -> str:
    """画像付きでThreadsに投稿"""
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        return "❌ THREADS_ACCESS_TOKEN または THREADS_USER_ID が設定されていません"

    try:
        container = _post(f"/{THREADS_USER_ID}/threads", {
            "media_type": "IMAGE",
            "text": text,
            "image_url": image_url,
        })
        creation_id = container.get("id")
        if not creation_id:
            return f"❌ コンテナ作成失敗: {container}"

        time.sleep(5)
        result = _post(f"/{THREADS_USER_ID}/threads_publish", {
            "creation_id": creation_id,
        })
        post_id = result.get("id")
        if post_id:
            return f"投稿したよ！\nhttps://www.threads.net/post/{post_id}"
        return f"❌ 公開失敗: {result}"

    except httpx.HTTPStatusError as e:
        return f"❌ APIエラー ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"❌ 投稿エラー: {e}"
