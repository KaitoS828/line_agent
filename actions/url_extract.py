"""URL内容取得アクション — メッセージ中のURLからコンテンツを抽出"""

import re
import httpx

URL_PATTERN = re.compile(r'https?://[^\s<>\"\']+')


def extract_urls(text: str) -> list[str]:
    """テキストからURLを抽出"""
    return URL_PATTERN.findall(text)


def fetch_page_content(url: str, max_chars: int = 3000) -> str:
    """URLのページ内容をテキストで取得"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LINE-Agent/1.0)"
        }
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return f"[バイナリコンテンツ: {content_type}]"

            text = resp.text
            # Simple HTML tag removal
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return text[:max_chars] if text else "ページ内容を取得できませんでした。"
    except Exception as e:
        return f"URL取得エラー: {e}"


def fetch_all_urls(text: str) -> str:
    """テキスト中の全URLの内容を取得してまとめる"""
    urls = extract_urls(text)
    if not urls:
        return ""

    results = []
    for url in urls[:3]:  # Max 3 URLs
        content = fetch_page_content(url)
        results.append(f"📎 {url}\n{content}")

    return "\n\n".join(results)
