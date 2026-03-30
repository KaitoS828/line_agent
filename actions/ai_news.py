"""AIニュースダイジェスト — 最新記事を取得してClaudeで要約・解説"""

from datetime import datetime, timedelta, timezone

import anthropic
from config import ANTHROPIC_API_KEY
from actions.web_search import search
from actions.url_extract import fetch_page_content

JST = timezone(timedelta(hours=9))

# アクセスしやすい日本語AIニュースサイト
_GOOD_DOMAINS = [
    "gigazine.net",
    "itmedia.co.jp",
    "impress.co.jp",
    "watch.impress.co.jp",
    "pc.watch.impress.co.jp",
    "techcrunch.com",
    "zenn.dev",
    "qiita.com",
    "gihyo.jp",
    "ascii.jp",
    "atmarkit.itmedia.co.jp",
]


def _is_good_url(url: str) -> bool:
    return any(d in url for d in _GOOD_DOMAINS)


def fetch_ai_news_digest() -> str:
    """今日のAIニュースを検索 → 記事取得 → Claudeで要約・解説"""
    now = datetime.now(JST)
    year_month = now.strftime("%Y年%m月")

    queries = [
        f"生成AI ニュース {year_month} site:gigazine.net OR site:itmedia.co.jp OR site:impress.co.jp",
        f"OpenAI Google AI 発表 {year_month}",
        f"AI LLM 最新情報 {year_month} gigazine OR itmedia OR impress",
    ]

    article_urls: list[str] = []
    for query in queries:
        raw = search(query, max_results=5)
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("http") and line not in article_urls:
                # 良質なドメイン優先
                if _is_good_url(line):
                    article_urls.insert(0, line)
                else:
                    article_urls.append(line)
        if len(article_urls) >= 6:
            break

    if not article_urls:
        return ""

    # 上位5件を試して、内容が取れたものを最大3件使う
    articles = []
    for url in article_urls[:5]:
        content = fetch_page_content(url, max_chars=2000)
        if (
            content
            and len(content) > 200
            and "取得できませんでした" not in content
            and "エラー" not in content[:50]
        ):
            articles.append({"url": url, "content": content})
        if len(articles) >= 3:
            break

    if not articles:
        return ""

    articles_text = "\n\n---\n\n".join(
        f"出典URL: {a['url']}\n{a['content']}" for a in articles
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": f"""以下のAI関連記事をもとに、今日のAIニュースダイジェストを作ってください。

## 絶対ルール
- 記事に書いていないことは絶対に書かない（架空の情報は厳禁）
- LINEのチャットで読みやすい形式にする
- Markdownの見出し（#）は使わない
- 箇条書きは「・」を使う
- 各ニュースに出典URLを必ず含める
- 全体で400〜500文字以内
- 冒頭は「今日のAIニュース」で始める

## 記事内容
{articles_text}"""
        }],
    )

    for block in response.content:
        if hasattr(block, "text"):
            return block.text.strip()
    return ""
