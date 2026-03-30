"""Twitter/X読み取りアクション — Exa API（プライマリ）/ Jina Reader（URL閲覧）"""

import re
import httpx
from config import EXA_API_KEY

_EXA_SEARCH_URL = "https://api.exa.ai/search"


def search_tweets(query: str, max_results: int = 10) -> str:
    """Exa APIでTwitter/Xのツイートを検索"""
    if not EXA_API_KEY:
        return "❌ EXA_API_KEY が設定されていません。Railway の環境変数に追加してください（exa.ai で無料登録）"

    try:
        resp = httpx.post(
            _EXA_SEARCH_URL,
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json={
                "query": query,
                "numResults": max_results,
                "includeDomains": ["x.com", "twitter.com"],
                "type": "neural",
                "contents": {"text": {"maxCharacters": 500}},
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return "該当するツイートが見つかりませんでした。"

        lines = []
        for r in results:
            lines.append(f"🐦 {r.get('title', '')}")
            lines.append(f"   {r.get('url', '')}")
            text = r.get("text", "")
            if text:
                lines.append(f"   {text[:300]}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Twitter検索エラー: {e}"


def get_tweet(url: str, max_chars: int = 2000) -> str:
    """ツイートのURLから内容を取得（Jina Reader経由）"""
    from actions.url_extract import fetch_page_content
    return fetch_page_content(url, max_chars)


def is_twitter_url(url: str) -> bool:
    return bool(re.search(r"(x\.com|twitter\.com)", url))
