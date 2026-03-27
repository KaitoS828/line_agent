"""Web検索アクション — Tavily APIを使ったリアルタイムWeb検索"""

import os
import httpx

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 5) -> str:
    """Tavilyでウェブ検索を実行"""
    if not TAVILY_API_KEY:
        return "❌ TAVILY_API_KEY が設定されていません"

    resp = httpx.post(
        TAVILY_SEARCH_URL,
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        },
        timeout=30,
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

    return "\n".join(lines) if lines else "検索結果が見つかりませんでした。"


def get_page_content(url: str) -> str:
    """指定URLのページ内容を取得（Tavily Extract）"""
    if not TAVILY_API_KEY:
        return "❌ TAVILY_API_KEY が設定されていません"

    resp = httpx.post(
        "https://api.tavily.com/extract",
        json={
            "api_key": TAVILY_API_KEY,
            "urls": [url],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if results:
        content = results[0].get("raw_content", "")[:3000]
        return content if content else "ページ内容を取得できませんでした。"
    return "ページ内容を取得できませんでした。"
