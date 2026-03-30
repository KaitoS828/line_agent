"""URL内容取得アクション — Jina Reader経由でクリーンなMarkdownを取得"""

import re
import httpx

URL_PATTERN = re.compile(r'https?://[^\s<>\"\']+')

JINA_BASE = "https://r.jina.ai/"

_CLIENT = httpx.Client(
    timeout=httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0),
    follow_redirects=True,
    headers={"Accept": "text/plain", "X-Return-Format": "markdown"},
)


def extract_urls(text: str) -> list[str]:
    """テキストからURLを抽出"""
    return URL_PATTERN.findall(text)


def fetch_page_content(url: str, max_chars: int = 4000) -> str:
    """Jina Reader経由でURLのページ内容をMarkdownで取得。失敗時はHTTPフォールバック"""
    try:
        resp = _CLIENT.get(JINA_BASE + url.strip())
        resp.raise_for_status()
        text = resp.text.strip()
        return text[:max_chars] if text else "ページ内容を取得できませんでした。"
    except Exception:
        pass

    # フォールバック: 直接HTTP取得 + HTML除去
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LINE-Agent/1.0)"},
        )
        resp.raise_for_status()
        text = resp.text
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
    for url in urls[:3]:
        content = fetch_page_content(url)
        results.append(f"📎 {url}\n{content}")

    return "\n\n".join(results)
