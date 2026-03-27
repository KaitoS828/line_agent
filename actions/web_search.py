"""Web検索アクション — Tavily APIを使ったリアルタイムWeb検索"""

import time
import httpx
from config import TAVILY_API_KEY

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

# 同一クエリ連打時の体感速度を上げるため、短時間キャッシュを使う
_CACHE_TTL_SECONDS = 120
_CACHE: dict[tuple[str, int], tuple[float, str]] = {}
_PAGE_CACHE: dict[str, tuple[float, str]] = {}

_CLIENT = httpx.Client(
    timeout=httpx.Timeout(connect=5.0, read=12.0, write=8.0, pool=5.0),
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    http2=True,
)


def _get_cached(cache: dict, key):
    item = cache.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL_SECONDS:
        cache.pop(key, None)
        return None
    return value


def search(query: str, max_results: int = 3) -> str:
    """Tavilyでウェブ検索を実行"""
    if not TAVILY_API_KEY:
        return "❌ TAVILY_API_KEY が設定されていません"

    cache_key = (query.strip(), max_results)
    cached = _get_cached(_CACHE, cache_key)
    if cached:
        return cached

    resp = _CLIENT.post(
        TAVILY_SEARCH_URL,
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            # 回答生成をオフにして検索速度優先
            "include_answer": False,
            "search_depth": "basic",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    lines = []

    # AI生成の要約回答
    if data.get("answer"):
        lines.append(f"📝 要約: {data['answer']}\n")

    # 検索結果一覧
    for i, r in enumerate(data.get("results", []), 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r.get("content"):
            snippet = r["content"][:200]
            lines.append(f"   {snippet}...")
        lines.append("")

    result = "\n".join(lines) if lines else "検索結果が見つかりませんでした。"
    _CACHE[cache_key] = (time.time(), result)
    return result


def get_page_content(url: str) -> str:
    """指定URLのページ内容を取得（Tavily Extract）"""
    if not TAVILY_API_KEY:
        return "❌ TAVILY_API_KEY が設定されていません"

    normalized_url = url.strip()
    cached = _get_cached(_PAGE_CACHE, normalized_url)
    if cached:
        return cached

    resp = _CLIENT.post(
        TAVILY_EXTRACT_URL,
        json={
            "api_key": TAVILY_API_KEY,
            "urls": [normalized_url],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if results:
        content = results[0].get("raw_content", "")[:3000]
        result = content if content else "ページ内容を取得できませんでした。"
        _PAGE_CACHE[normalized_url] = (time.time(), result)
        return result
    return "ページ内容を取得できませんでした。"
