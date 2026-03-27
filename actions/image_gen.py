"""画像生成アクション — OpenAI Images APIでURLを生成"""

import httpx

from config import GEMINI_API_KEY

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


def generate_image_url(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
) -> str:
    """画像を生成してURLを返す"""
    if not GEMINI_API_KEY:
        return "❌ GEMINI_API_KEY が設定されていません"

    payload = {
        "model": "nanobanana",
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "response_format": "url",
    }
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(OPENAI_IMAGES_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    images = data.get("data", [])
    if not images:
        return "❌ 画像を生成できませんでした"

    image_url = images[0].get("url", "")
    if not image_url:
        return "❌ 画像URLを取得できませんでした"
    return image_url
