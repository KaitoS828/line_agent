"""URL読み取り担当エージェント — URLの内容を取得・要約"""

import anthropic
from config import ANTHROPIC_API_KEY
from actions.url_extract import extract_urls, fetch_page_content


class URLReaderAgent:
    """URLの内容を取得して要約するエージェント"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.name = "URLReaderAgent"
        self.role = "URLの内容取得・要約の専門家。「このURL見て」「このページ要約して」「リンクの内容教えて」に対応"

    def run(self, task: str) -> str:
        urls = extract_urls(task)
        if not urls:
            return "❌ URLが見つかりませんでした。URLを含むメッセージを送ってください。"

        contents = []
        for url in urls[:3]:
            content = fetch_page_content(url)
            contents.append(f"URL: {url}\n内容:\n{content}")

        all_content = "\n\n---\n\n".join(contents)

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""あなたはURLの内容を分析・要約する専門家です。
取得したページ内容を元に、ユーザーの指示に従って処理してください。

## ルール
- 日本語で簡潔にまとめる
- 重要なポイントを箇条書きで整理
- ページが取得できなかった場合はその旨を伝える
- URLが複数ある場合はそれぞれ分けてまとめる""",
            messages=[{"role": "user", "content": f"以下のURLの内容を処理してください。\n\nユーザーの指示: {task}\n\n取得した内容:\n{all_content}"}],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "URLの分析に失敗しました。"
